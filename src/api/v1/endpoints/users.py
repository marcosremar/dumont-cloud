"""
User Profile and Team Context API endpoints

Endpoints for user profile management and team context switching.
- GET /users/me - Get current user profile
- GET /users/me/teams - Get user's teams
- POST /users/me/switch-team - Switch team context (generate new JWT)
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..dependencies import (
    get_current_user_email,
    get_current_user,
    get_token_payload,
)
from ....config.database import get_db
from ....core.jwt import create_access_token
from ....infrastructure.providers import SQLAlchemyTeamRepository, SQLAlchemyRoleRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


# Helper functions

def get_team_repository(db: Session = Depends(get_db)) -> SQLAlchemyTeamRepository:
    """Get team repository instance"""
    return SQLAlchemyTeamRepository(session=db)


def get_role_repository(db: Session = Depends(get_db)) -> SQLAlchemyRoleRepository:
    """Get role repository instance"""
    return SQLAlchemyRoleRepository(session=db)


# Request/Response models

class SwitchTeamRequest(BaseModel):
    """Request to switch team context"""
    team_id: int = Field(..., description="ID of the team to switch to")


class SwitchTeamResponse(BaseModel):
    """Response with new access token after team switch"""
    access_token: str = Field(..., description="New JWT access token with updated team context")
    token_type: str = Field(default="bearer", description="Token type")
    team_id: int = Field(..., description="Current team ID")
    team_name: str = Field(..., description="Current team name")
    role: str = Field(..., description="User's role in the team")
    permissions: List[str] = Field(..., description="User's permissions in the team")


class UserTeamResponse(BaseModel):
    """User's team with role info"""
    id: int
    name: str
    slug: str
    role: str
    role_id: int
    is_current: bool = False


class UserTeamsListResponse(BaseModel):
    """List of user's teams"""
    teams: List[UserTeamResponse]
    count: int
    current_team_id: Optional[int] = None


class UserProfileResponse(BaseModel):
    """User profile response"""
    email: str
    current_team_id: Optional[int] = None
    current_team_name: Optional[str] = None
    current_role: Optional[str] = None


# Endpoints

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    user_email: str = Depends(get_current_user_email),
    token_payload: Optional[dict] = Depends(get_token_payload),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
):
    """
    Get current user profile

    Returns the logged-in user's profile information including current team context.
    """
    current_team_id = token_payload.get("team_id") if token_payload else None
    current_team_name = None
    current_role = token_payload.get("role") if token_payload else None

    if current_team_id:
        team = team_repo.get_team(current_team_id)
        if team:
            current_team_name = team.name

    return UserProfileResponse(
        email=user_email,
        current_team_id=current_team_id,
        current_team_name=current_team_name,
        current_role=current_role,
    )


@router.get("/me/teams", response_model=UserTeamsListResponse)
async def get_user_teams(
    user_email: str = Depends(get_current_user_email),
    token_payload: Optional[dict] = Depends(get_token_payload),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
):
    """
    Get all teams for the current user

    Returns a list of teams where the user is an active member,
    including their role in each team.
    """
    current_team_id = token_payload.get("team_id") if token_payload else None

    # Get all teams for the user
    teams = team_repo.get_teams_for_user(user_email)

    team_responses = []
    for team in teams:
        # Get user's role in this team
        user_role = role_repo.get_user_role(user_email, team.id)
        role_name = user_role.name if user_role else "Unknown"
        role_id = user_role.id if user_role else 0

        team_responses.append(UserTeamResponse(
            id=team.id,
            name=team.name,
            slug=team.slug,
            role=role_name,
            role_id=role_id,
            is_current=team.id == current_team_id,
        ))

    return UserTeamsListResponse(
        teams=team_responses,
        count=len(team_responses),
        current_team_id=current_team_id,
    )


@router.post("/me/switch-team", response_model=SwitchTeamResponse)
async def switch_team(
    request: SwitchTeamRequest,
    user_email: str = Depends(get_current_user_email),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
):
    """
    Switch team context

    Switches the user's active team context by generating a new JWT token
    with the specified team_id, role, and permissions embedded.

    The user must be an active member of the target team.

    Returns a new access token that should be used for subsequent API calls.
    The frontend should store this token and include it in the Authorization header.
    """
    target_team_id = request.team_id

    # Verify the team exists
    team = team_repo.get_team(target_team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {target_team_id} not found",
        )

    # Verify the user is a member of the team
    member = team_repo.get_member(target_team_id, user_email)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not a member of team '{team.name}'",
        )

    # Get the user's role in the team
    user_role = role_repo.get_user_role(user_email, target_team_id)
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to determine user role in team",
        )

    # Get the user's permissions in the team
    permissions = role_repo.get_user_permissions(user_email, target_team_id)

    # Generate a new JWT token with the updated team context
    access_token = create_access_token(
        email=user_email,
        team_id=target_team_id,
        role=user_role.name,
        permissions=permissions,
    )

    logger.info(f"User {user_email} switched to team {target_team_id} ({team.name}) with role {user_role.name}")

    return SwitchTeamResponse(
        access_token=access_token,
        token_type="bearer",
        team_id=target_team_id,
        team_name=team.name,
        role=user_role.name,
        permissions=permissions,
    )
