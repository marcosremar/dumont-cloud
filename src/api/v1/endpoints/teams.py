"""
Team Management API endpoints

CRUD operations for teams, including:
- Create, read, update, delete teams
- List user's teams
- Team quota management
"""
import re
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..dependencies import (
    get_current_user_email,
    require_permission,
)
from ....config.database import get_db
from ....core.permissions import TEAM_MANAGE
from ....core.exceptions import NotFoundException, ValidationException
from ....infrastructure.providers import SQLAlchemyTeamRepository, SQLAlchemyRoleRepository
from ....models.rbac import Team, TeamMember, Role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teams", tags=["Teams"])


# Helper functions

def slugify(name: str) -> str:
    """Convert team name to URL-friendly slug"""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug


def get_team_repository(db: Session = Depends(get_db)) -> SQLAlchemyTeamRepository:
    """Get team repository instance"""
    return SQLAlchemyTeamRepository(session=db)


def get_role_repository(db: Session = Depends(get_db)) -> SQLAlchemyRoleRepository:
    """Get role repository instance"""
    return SQLAlchemyRoleRepository(session=db)


# Request/Response models (inline for simplicity, can be moved to schemas)

from pydantic import BaseModel, Field
from datetime import datetime


class CreateTeamRequest(BaseModel):
    """Create team request"""
    name: str = Field(..., min_length=1, max_length=100, description="Team name")
    description: Optional[str] = Field(None, max_length=500, description="Team description")
    slug: Optional[str] = Field(None, max_length=100, description="URL-friendly slug (auto-generated if not provided)")


class UpdateTeamRequest(BaseModel):
    """Update team request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Team name")
    description: Optional[str] = Field(None, max_length=500, description="Team description")
    is_active: Optional[bool] = Field(None, description="Team active status")


class TeamQuotaRequest(BaseModel):
    """Team quota request"""
    max_gpu_hours_per_month: Optional[float] = Field(None, ge=0, description="Max GPU hours per month (null = unlimited)")
    max_concurrent_instances: Optional[int] = Field(None, ge=0, description="Max concurrent instances (null = unlimited)")
    max_monthly_budget_usd: Optional[float] = Field(None, ge=0, description="Max monthly budget USD (null = unlimited)")


class TeamMemberResponse(BaseModel):
    """Team member response"""
    id: int
    user_id: str
    team_id: int
    role_id: int
    role_name: Optional[str] = None
    invited_by_user_id: Optional[str] = None
    joined_at: Optional[datetime] = None
    is_active: bool


class TeamResponse(BaseModel):
    """Team response"""
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    owner_user_id: str
    is_active: bool
    member_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeamDetailResponse(TeamResponse):
    """Team detail response with additional info"""
    members: Optional[List[TeamMemberResponse]] = None
    quota: Optional[dict] = None
    user_role: Optional[str] = None


class TeamListResponse(BaseModel):
    """Team list response"""
    teams: List[TeamResponse]
    count: int


class TeamQuotaResponse(BaseModel):
    """Team quota response"""
    team_id: int
    limits: dict
    usage: dict
    warnings: dict


# Team CRUD Endpoints

@router.post("", status_code=status.HTTP_201_CREATED, response_model=TeamResponse)
async def create_team(
    request: CreateTeamRequest,
    user_email: str = Depends(get_current_user_email),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    db: Session = Depends(get_db),
):
    """
    Create a new team

    Creates a team and adds the current user as the owner with Admin role.
    """
    try:
        # Generate slug if not provided
        slug = request.slug if request.slug else slugify(request.name)

        # Create the team
        team = team_repo.create_team(
            name=request.name,
            slug=slug,
            owner_user_id=user_email,
            description=request.description,
        )

        # Get the Admin role (system role, so team_id=None)
        admin_role = role_repo.get_role_by_name("admin", team_id=None)
        if not admin_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin role not found. Please run database migrations.",
            )

        # Add the owner as the first member with Admin role
        team_repo.add_member(
            team_id=team.id,
            user_id=user_email,
            role_id=admin_role.id,
            invited_by_user_id=None,  # Self-added as owner
        )

        # Commit the transaction
        db.commit()

        logger.info(f"Team '{team.name}' created by {user_email}")

        return TeamResponse(
            id=team.id,
            name=team.name,
            slug=team.slug,
            description=team.description,
            owner_user_id=team.owner_user_id,
            is_active=team.is_active,
            member_count=1,
            created_at=team.created_at,
            updated_at=team.updated_at,
        )

    except ValidationException as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create team: {str(e)}",
        )


@router.get("", response_model=TeamListResponse)
async def list_teams(
    user_email: str = Depends(get_current_user_email),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of teams to return"),
    offset: int = Query(0, ge=0, description="Number of teams to skip"),
):
    """
    List all teams for the current user

    Returns teams where the user is an active member.
    """
    teams = team_repo.get_teams_for_user(user_email)

    # Add member count to each team
    team_responses = []
    for team in teams[offset:offset+limit]:
        member_count = team_repo.get_member_count(team.id)
        team_responses.append(TeamResponse(
            id=team.id,
            name=team.name,
            slug=team.slug,
            description=team.description,
            owner_user_id=team.owner_user_id,
            is_active=team.is_active,
            member_count=member_count,
            created_at=team.created_at,
            updated_at=team.updated_at,
        ))

    return TeamListResponse(
        teams=team_responses,
        count=len(teams),
    )


@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: int,
    user_email: str = Depends(get_current_user_email),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
):
    """
    Get team details

    Returns team information including members and quota (if user is a member).
    """
    # Get the team
    team = team_repo.get_team(team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found",
        )

    # Check if user is a member
    member = team_repo.get_member(team_id, user_email)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    # Get member count
    member_count = team_repo.get_member_count(team_id)

    # Get members list
    members_raw = team_repo.get_members(team_id, limit=100)
    members = []
    for m in members_raw:
        role_name = m.role.name if m.role else None
        members.append(TeamMemberResponse(
            id=m.id,
            user_id=m.user_id,
            team_id=m.team_id,
            role_id=m.role_id,
            role_name=role_name,
            invited_by_user_id=m.invited_by_user_id,
            joined_at=m.joined_at,
            is_active=m.is_active,
        ))

    # Get user's role
    user_role = role_repo.get_user_role(user_email, team_id)
    user_role_name = user_role.name if user_role else None

    # Get quota
    quota = team_repo.get_quota(team_id)
    quota_dict = quota.to_dict() if quota else None

    return TeamDetailResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        description=team.description,
        owner_user_id=team.owner_user_id,
        is_active=team.is_active,
        member_count=member_count,
        created_at=team.created_at,
        updated_at=team.updated_at,
        members=members,
        quota=quota_dict,
        user_role=user_role_name,
    )


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    request: UpdateTeamRequest,
    user_email: str = Depends(require_permission(TEAM_MANAGE)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Update team information

    Requires team.manage permission.
    """
    try:
        # Check if user is a member with proper permissions
        member = team_repo.get_member(team_id, user_email)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team",
            )

        # Build updates dict
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.is_active is not None:
            updates["is_active"] = request.is_active

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided",
            )

        # Update the team
        team = team_repo.update_team(team_id, updates)
        db.commit()

        logger.info(f"Team {team_id} updated by {user_email}")

        member_count = team_repo.get_member_count(team_id)

        return TeamResponse(
            id=team.id,
            name=team.name,
            slug=team.slug,
            description=team.description,
            owner_user_id=team.owner_user_id,
            is_active=team.is_active,
            member_count=member_count,
            created_at=team.created_at,
            updated_at=team.updated_at,
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationException as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update team: {str(e)}",
        )


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    user_email: str = Depends(require_permission(TEAM_MANAGE)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Delete (soft delete) a team

    Requires team.manage permission. Only the team owner can delete the team.
    """
    try:
        # Get the team to check ownership
        team = team_repo.get_team(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID {team_id} not found",
            )

        # Only the owner can delete the team
        if team.owner_user_id != user_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the team owner can delete the team",
            )

        # Soft delete the team
        success = team_repo.delete_team(team_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete team",
            )

        db.commit()
        logger.info(f"Team {team_id} deleted by {user_email}")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete team: {str(e)}",
        )


# Team Quota Endpoints

@router.get("/{team_id}/quota", response_model=TeamQuotaResponse)
async def get_team_quota(
    team_id: int,
    user_email: str = Depends(get_current_user_email),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
):
    """
    Get team quota and usage

    Returns the team's resource limits and current usage.
    """
    # Check membership
    member = team_repo.get_member(team_id, user_email)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    quota = team_repo.get_quota(team_id)

    if not quota:
        # Return empty quota (unlimited)
        return TeamQuotaResponse(
            team_id=team_id,
            limits={
                "max_gpu_hours_per_month": None,
                "max_concurrent_instances": None,
                "max_monthly_budget_usd": None,
            },
            usage={
                "gpu_hours_used": 0,
                "concurrent_instances": 0,
                "monthly_spend_usd": 0,
            },
            warnings={
                "warn_at_gpu_hours_percent": 80.0,
                "warn_at_budget_percent": 80.0,
            },
        )

    return TeamQuotaResponse(
        team_id=team_id,
        limits={
            "max_gpu_hours_per_month": quota.max_gpu_hours_per_month,
            "max_concurrent_instances": quota.max_concurrent_instances,
            "max_monthly_budget_usd": quota.max_monthly_budget_usd,
        },
        usage={
            "gpu_hours_used": quota.current_gpu_hours_used,
            "concurrent_instances": quota.current_concurrent_instances,
            "monthly_spend_usd": quota.current_monthly_spend_usd,
        },
        warnings={
            "warn_at_gpu_hours_percent": quota.warn_at_gpu_hours_percent,
            "warn_at_budget_percent": quota.warn_at_budget_percent,
        },
    )


@router.put("/{team_id}/quota", response_model=TeamQuotaResponse)
async def update_team_quota(
    team_id: int,
    request: TeamQuotaRequest,
    user_email: str = Depends(require_permission(TEAM_MANAGE)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Update team quota

    Set or update the team's resource limits. Requires team.manage permission.
    """
    try:
        # Check membership
        member = team_repo.get_member(team_id, user_email)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team",
            )

        quota = team_repo.create_or_update_quota(
            team_id=team_id,
            max_gpu_hours_per_month=request.max_gpu_hours_per_month,
            max_concurrent_instances=request.max_concurrent_instances,
            max_monthly_budget_usd=request.max_monthly_budget_usd,
        )

        db.commit()
        logger.info(f"Team {team_id} quota updated by {user_email}")

        return TeamQuotaResponse(
            team_id=team_id,
            limits={
                "max_gpu_hours_per_month": quota.max_gpu_hours_per_month,
                "max_concurrent_instances": quota.max_concurrent_instances,
                "max_monthly_budget_usd": quota.max_monthly_budget_usd,
            },
            usage={
                "gpu_hours_used": quota.current_gpu_hours_used,
                "concurrent_instances": quota.current_concurrent_instances,
                "monthly_spend_usd": quota.current_monthly_spend_usd,
            },
            warnings={
                "warn_at_gpu_hours_percent": quota.warn_at_gpu_hours_percent,
                "warn_at_budget_percent": quota.warn_at_budget_percent,
            },
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating team quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update team quota: {str(e)}",
        )


# =============================================
# Team Member Management Endpoints
# =============================================

import secrets
from datetime import datetime, timedelta
from ....core.permissions import TEAM_INVITE, TEAM_REMOVE


class InviteMemberRequest(BaseModel):
    """Invite member request"""
    email: str = Field(..., min_length=1, max_length=255, description="Email of the user to invite")
    role_id: int = Field(..., description="Role ID to assign to the invited user")


class UpdateMemberRoleRequest(BaseModel):
    """Update member role request"""
    role_id: int = Field(..., description="New role ID for the member")


class InvitationResponse(BaseModel):
    """Invitation response"""
    id: int
    team_id: int
    email: str
    role_id: int
    role_name: Optional[str] = None
    invited_by_user_id: str
    token: str
    expires_at: datetime
    status: str
    created_at: Optional[datetime] = None


class InvitationListResponse(BaseModel):
    """Invitation list response"""
    invitations: List[InvitationResponse]
    count: int


class MemberListResponse(BaseModel):
    """Member list response"""
    members: List[TeamMemberResponse]
    count: int


# Helper function to generate invitation token
def generate_invitation_token() -> str:
    """Generate a secure random token for invitations"""
    return secrets.token_urlsafe(32)


@router.post("/{team_id}/invitations", status_code=status.HTTP_201_CREATED, response_model=InvitationResponse)
async def invite_member(
    team_id: int,
    request: InviteMemberRequest,
    user_email: str = Depends(require_permission(TEAM_INVITE)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    db: Session = Depends(get_db),
):
    """
    Invite a new member to the team

    Creates a pending invitation that can be accepted by the invitee.
    Requires team.invite permission.
    """
    try:
        # Check if user is a member
        member = team_repo.get_member(team_id, user_email)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team",
            )

        # Check if role exists
        role = role_repo.get_role(request.role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role with ID {request.role_id} not found",
            )

        # Check if user is already a member
        existing_member = team_repo.get_member(team_id, request.email)
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {request.email} is already a member of this team",
            )

        # Generate invitation token and expiration (7 days)
        token = generate_invitation_token()
        expires_at = datetime.utcnow() + timedelta(days=7)

        # Create the invitation
        invitation = team_repo.create_invitation(
            team_id=team_id,
            email=request.email,
            role_id=request.role_id,
            invited_by_user_id=user_email,
            token=token,
            expires_at=expires_at,
        )

        db.commit()
        logger.info(f"Invitation sent to {request.email} for team {team_id} by {user_email}")

        return InvitationResponse(
            id=invitation.id,
            team_id=invitation.team_id,
            email=invitation.email,
            role_id=invitation.role_id,
            role_name=role.name,
            invited_by_user_id=invitation.invited_by_user_id,
            token=invitation.token,
            expires_at=invitation.expires_at,
            status=invitation.status,
            created_at=invitation.created_at,
        )

    except ValidationException as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create invitation: {str(e)}",
        )


@router.get("/{team_id}/invitations", response_model=InvitationListResponse)
async def list_invitations(
    team_id: int,
    user_email: str = Depends(get_current_user_email),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, accepted, expired, revoked"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of invitations to return"),
    offset: int = Query(0, ge=0, description="Number of invitations to skip"),
):
    """
    List team invitations

    Returns all invitations for the team. Requires team membership.
    """
    # Check membership
    member = team_repo.get_member(team_id, user_email)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    invitations_raw = team_repo.get_invitations_for_team(
        team_id=team_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    invitations = []
    for inv in invitations_raw:
        role_name = inv.role.name if inv.role else None
        invitations.append(InvitationResponse(
            id=inv.id,
            team_id=inv.team_id,
            email=inv.email,
            role_id=inv.role_id,
            role_name=role_name,
            invited_by_user_id=inv.invited_by_user_id,
            token=inv.token,
            expires_at=inv.expires_at,
            status=inv.status,
            created_at=inv.created_at,
        ))

    return InvitationListResponse(
        invitations=invitations,
        count=len(invitations),
    )


@router.delete("/{team_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    team_id: int,
    invitation_id: int,
    user_email: str = Depends(require_permission(TEAM_INVITE)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Revoke a pending invitation

    Requires team.invite permission.
    """
    try:
        # Check membership
        member = team_repo.get_member(team_id, user_email)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team",
            )

        # Revoke the invitation
        success = team_repo.revoke_invitation(invitation_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pending invitation with ID {invitation_id} not found",
            )

        db.commit()
        logger.info(f"Invitation {invitation_id} revoked by {user_email}")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error revoking invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke invitation: {str(e)}",
        )


@router.post("/{team_id}/invitations/{token}/accept", status_code=status.HTTP_200_OK, response_model=TeamMemberResponse)
async def accept_invitation(
    team_id: int,
    token: str,
    user_email: str = Depends(get_current_user_email),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Accept a team invitation

    The logged-in user accepts the invitation using the token.
    """
    try:
        # Get the invitation by token
        invitation = team_repo.get_invitation_by_token(token)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found",
            )

        # Check team matches
        if invitation.team_id != team_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation does not match the specified team",
            )

        # Check invitation status
        if invitation.status != 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation is not pending (status: {invitation.status})",
            )

        # Check expiration
        if invitation.expires_at < datetime.utcnow():
            invitation.status = 'expired'
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired",
            )

        # Check if user is already a member
        existing_member = team_repo.get_member(team_id, user_email)
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already a member of this team",
            )

        # Accept the invitation
        team_repo.accept_invitation(invitation.id, user_email)

        # Add user as member
        member = team_repo.add_member(
            team_id=team_id,
            user_id=user_email,
            role_id=invitation.role_id,
            invited_by_user_id=invitation.invited_by_user_id,
            invited_at=invitation.created_at,
        )

        db.commit()
        logger.info(f"User {user_email} accepted invitation and joined team {team_id}")

        role_name = member.role.name if member.role else None

        return TeamMemberResponse(
            id=member.id,
            user_id=member.user_id,
            team_id=member.team_id,
            role_id=member.role_id,
            role_name=role_name,
            invited_by_user_id=member.invited_by_user_id,
            joined_at=member.joined_at,
            is_active=member.is_active,
        )

    except ValidationException as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error accepting invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept invitation: {str(e)}",
        )


@router.get("/{team_id}/members", response_model=MemberListResponse)
async def list_members(
    team_id: int,
    user_email: str = Depends(get_current_user_email),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    include_removed: bool = Query(False, description="Include removed members"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of members to return"),
    offset: int = Query(0, ge=0, description="Number of members to skip"),
):
    """
    List team members

    Returns all active members of the team. Requires team membership.
    """
    # Check membership
    member = team_repo.get_member(team_id, user_email)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    members_raw = team_repo.get_members(
        team_id=team_id,
        include_removed=include_removed,
        limit=limit,
        offset=offset,
    )

    members = []
    for m in members_raw:
        role_name = m.role.name if m.role else None
        members.append(TeamMemberResponse(
            id=m.id,
            user_id=m.user_id,
            team_id=m.team_id,
            role_id=m.role_id,
            role_name=role_name,
            invited_by_user_id=m.invited_by_user_id,
            joined_at=m.joined_at,
            is_active=m.is_active,
        ))

    return MemberListResponse(
        members=members,
        count=len(members),
    )


@router.put("/{team_id}/members/{member_user_id}/role", response_model=TeamMemberResponse)
async def update_member_role(
    team_id: int,
    member_user_id: str,
    request: UpdateMemberRoleRequest,
    user_email: str = Depends(require_permission(TEAM_MANAGE)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    db: Session = Depends(get_db),
):
    """
    Update a team member's role

    Changes the role assigned to a team member. Requires team.manage permission.
    Prevents demoting the last admin (team must have at least one admin).
    """
    try:
        # Check if user is a member
        requester_member = team_repo.get_member(team_id, user_email)
        if not requester_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team",
            )

        # Get the member to update
        target_member = team_repo.get_member(team_id, member_user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member {member_user_id} not found in this team",
            )

        # Check if new role exists
        new_role = role_repo.get_role(request.role_id)
        if not new_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role with ID {request.role_id} not found",
            )

        # Get current role
        current_role = target_member.role

        # Check if we're demoting the last admin
        if current_role and current_role.name.lower() == 'admin':
            # Check if new role is not admin
            if new_role.name.lower() != 'admin':
                admin_count = team_repo.get_admin_count(team_id)
                if admin_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot demote the last admin. Team must have at least one admin.",
                    )

        # Update the role
        member = team_repo.update_member_role(team_id, member_user_id, request.role_id)
        db.commit()

        logger.info(f"Member {member_user_id} role updated to {new_role.name} in team {team_id} by {user_email}")

        return TeamMemberResponse(
            id=member.id,
            user_id=member.user_id,
            team_id=member.team_id,
            role_id=member.role_id,
            role_name=new_role.name,
            invited_by_user_id=member.invited_by_user_id,
            joined_at=member.joined_at,
            is_active=member.is_active,
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating member role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update member role: {str(e)}",
        )


@router.delete("/{team_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    team_id: int,
    member_user_id: str,
    user_email: str = Depends(require_permission(TEAM_REMOVE)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Remove a member from the team (soft delete)

    Requires team.remove permission. Cannot remove yourself or the last admin.
    """
    try:
        # Check if user is a member
        requester_member = team_repo.get_member(team_id, user_email)
        if not requester_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team",
            )

        # Cannot remove yourself via this endpoint
        if member_user_id == user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove yourself. Use leave team endpoint instead.",
            )

        # Get the member to remove
        target_member = team_repo.get_member(team_id, member_user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member {member_user_id} not found in this team",
            )

        # Check if we're removing the last admin
        if target_member.role and target_member.role.name.lower() == 'admin':
            admin_count = team_repo.get_admin_count(team_id)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last admin. Team must have at least one admin.",
                )

        # Soft delete the member
        success = team_repo.remove_member(team_id, member_user_id, removed_by_user_id=user_email)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove member",
            )

        db.commit()
        logger.info(f"Member {member_user_id} removed from team {team_id} by {user_email}")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove member: {str(e)}",
        )


@router.post("/{team_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_team(
    team_id: int,
    user_email: str = Depends(get_current_user_email),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Leave a team

    Allows a user to remove themselves from a team.
    Cannot leave if you're the last admin.
    """
    try:
        # Check if user is a member
        member = team_repo.get_member(team_id, user_email)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You are not a member of this team",
            )

        # Check if we're the last admin
        if member.role and member.role.name.lower() == 'admin':
            admin_count = team_repo.get_admin_count(team_id)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot leave team. You are the last admin. Transfer ownership or delete the team.",
                )

        # Soft delete the member
        success = team_repo.remove_member(team_id, user_email, removed_by_user_id=user_email)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to leave team",
            )

        db.commit()
        logger.info(f"User {user_email} left team {team_id}")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error leaving team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to leave team: {str(e)}",
        )
