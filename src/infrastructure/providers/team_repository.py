"""
SQLAlchemy Team Repository Implementation
Implements ITeamRepository interface (Dependency Inversion Principle)
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ...core.exceptions import NotFoundException, ValidationException
from ...domain.repositories import ITeamRepository
from ...models.rbac import Team, TeamMember, TeamInvitation, TeamQuota, Role

logger = logging.getLogger(__name__)


class SQLAlchemyTeamRepository(ITeamRepository):
    """
    SQLAlchemy implementation of ITeamRepository.
    Stores teams, members, invitations, and quotas in PostgreSQL.
    """

    def __init__(self, session: Session):
        """
        Initialize SQLAlchemy team repository

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    # Team CRUD operations

    def get_team(self, team_id: int) -> Optional[Team]:
        """Get team by ID"""
        return self.session.query(Team).filter(
            Team.id == team_id,
            Team.deleted_at.is_(None)
        ).first()

    def get_team_by_slug(self, slug: str) -> Optional[Team]:
        """Get team by URL-friendly slug"""
        return self.session.query(Team).filter(
            Team.slug == slug,
            Team.deleted_at.is_(None)
        ).first()

    def get_team_by_name(self, name: str) -> Optional[Team]:
        """Get team by name"""
        return self.session.query(Team).filter(
            Team.name == name,
            Team.deleted_at.is_(None)
        ).first()

    def create_team(
        self,
        name: str,
        slug: str,
        owner_user_id: str,
        description: Optional[str] = None
    ) -> Team:
        """Create a new team"""
        if not name or not slug or not owner_user_id:
            raise ValidationException("Name, slug, and owner_user_id are required")

        # Check for duplicate name or slug
        existing = self.session.query(Team).filter(
            or_(Team.name == name, Team.slug == slug),
            Team.deleted_at.is_(None)
        ).first()

        if existing:
            if existing.name == name:
                raise ValidationException(f"Team with name '{name}' already exists")
            raise ValidationException(f"Team with slug '{slug}' already exists")

        team = Team(
            name=name,
            slug=slug,
            owner_user_id=owner_user_id,
            description=description,
            is_active=True
        )

        self.session.add(team)
        self.session.flush()  # Get the ID without committing
        logger.info(f"Team '{name}' created with ID {team.id}")

        return team

    def update_team(self, team_id: int, updates: Dict[str, Any]) -> Team:
        """Update team information"""
        team = self.get_team(team_id)
        if not team:
            raise NotFoundException(f"Team with ID {team_id} not found")

        # Update allowed fields
        if "name" in updates:
            # Check for duplicate name
            existing = self.session.query(Team).filter(
                Team.name == updates["name"],
                Team.id != team_id,
                Team.deleted_at.is_(None)
            ).first()
            if existing:
                raise ValidationException(f"Team with name '{updates['name']}' already exists")
            team.name = updates["name"]

        if "slug" in updates:
            # Check for duplicate slug
            existing = self.session.query(Team).filter(
                Team.slug == updates["slug"],
                Team.id != team_id,
                Team.deleted_at.is_(None)
            ).first()
            if existing:
                raise ValidationException(f"Team with slug '{updates['slug']}' already exists")
            team.slug = updates["slug"]

        if "description" in updates:
            team.description = updates["description"]

        if "is_active" in updates:
            team.is_active = updates["is_active"]

        if "owner_user_id" in updates:
            team.owner_user_id = updates["owner_user_id"]

        team.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Team {team_id} updated")

        return team

    def delete_team(self, team_id: int) -> bool:
        """Soft delete a team (sets deleted_at timestamp)"""
        team = self.get_team(team_id)
        if not team:
            return False

        team.deleted_at = datetime.utcnow()
        team.is_active = False
        self.session.flush()
        logger.info(f"Team {team_id} soft deleted")

        return True

    def list_teams(
        self,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Team]:
        """List all teams with pagination"""
        query = self.session.query(Team)

        if not include_deleted:
            query = query.filter(Team.deleted_at.is_(None))

        return query.order_by(Team.created_at.desc()).offset(offset).limit(limit).all()

    def get_teams_for_user(self, user_id: str) -> List[Team]:
        """Get all teams where user is a member"""
        return self.session.query(Team).join(TeamMember).filter(
            TeamMember.user_id == user_id,
            TeamMember.is_active == True,
            TeamMember.removed_at.is_(None),
            Team.deleted_at.is_(None)
        ).all()

    # Team member operations

    def add_member(
        self,
        team_id: int,
        user_id: str,
        role_id: int,
        invited_by_user_id: Optional[str] = None,
        invited_at: Optional[datetime] = None
    ) -> TeamMember:
        """Add a member to the team"""
        # Check if team exists
        team = self.get_team(team_id)
        if not team:
            raise NotFoundException(f"Team with ID {team_id} not found")

        # Check if user is already a member
        existing = self.session.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.is_active == True,
            TeamMember.removed_at.is_(None)
        ).first()

        if existing:
            raise ValidationException(f"User {user_id} is already a member of team {team_id}")

        # Check if role exists
        role = self.session.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise NotFoundException(f"Role with ID {role_id} not found")

        member = TeamMember(
            team_id=team_id,
            user_id=user_id,
            role_id=role_id,
            invited_by_user_id=invited_by_user_id,
            invited_at=invited_at or datetime.utcnow(),
            joined_at=datetime.utcnow(),
            is_active=True
        )

        self.session.add(member)
        self.session.flush()
        logger.info(f"User {user_id} added to team {team_id} with role {role_id}")

        return member

    def remove_member(
        self,
        team_id: int,
        user_id: str,
        removed_by_user_id: Optional[str] = None
    ) -> bool:
        """Soft delete a team member (sets removed_at timestamp)"""
        member = self.session.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.is_active == True,
            TeamMember.removed_at.is_(None)
        ).first()

        if not member:
            return False

        member.removed_at = datetime.utcnow()
        member.removed_by_user_id = removed_by_user_id
        member.is_active = False
        self.session.flush()
        logger.info(f"User {user_id} removed from team {team_id}")

        return True

    def get_member(self, team_id: int, user_id: str) -> Optional[TeamMember]:
        """Get a specific team member"""
        return self.session.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.is_active == True,
            TeamMember.removed_at.is_(None)
        ).first()

    def get_members(
        self,
        team_id: int,
        include_removed: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[TeamMember]:
        """Get all members of a team with pagination"""
        query = self.session.query(TeamMember).filter(TeamMember.team_id == team_id)

        if not include_removed:
            query = query.filter(
                TeamMember.is_active == True,
                TeamMember.removed_at.is_(None)
            )

        return query.order_by(TeamMember.joined_at.asc()).offset(offset).limit(limit).all()

    def update_member_role(
        self,
        team_id: int,
        user_id: str,
        role_id: int
    ) -> TeamMember:
        """Update a member's role"""
        member = self.get_member(team_id, user_id)
        if not member:
            raise NotFoundException(f"Member {user_id} not found in team {team_id}")

        # Check if role exists
        role = self.session.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise NotFoundException(f"Role with ID {role_id} not found")

        member.role_id = role_id
        member.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"User {user_id} role updated to {role_id} in team {team_id}")

        return member

    def is_member(self, team_id: int, user_id: str) -> bool:
        """Check if user is an active member of the team"""
        member = self.get_member(team_id, user_id)
        return member is not None

    def get_member_count(self, team_id: int) -> int:
        """Get count of active members in a team"""
        return self.session.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.is_active == True,
            TeamMember.removed_at.is_(None)
        ).count()

    def get_admin_count(self, team_id: int) -> int:
        """Get count of admins in a team (prevents removing last admin)"""
        # Get the admin role
        admin_role = self.session.query(Role).filter(
            Role.name == 'admin',
            Role.is_system == True
        ).first()

        if not admin_role:
            return 0

        return self.session.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.role_id == admin_role.id,
            TeamMember.is_active == True,
            TeamMember.removed_at.is_(None)
        ).count()

    # Invitation operations

    def create_invitation(
        self,
        team_id: int,
        email: str,
        role_id: int,
        invited_by_user_id: str,
        token: str,
        expires_at: datetime
    ) -> TeamInvitation:
        """Create a team invitation"""
        # Check if team exists
        team = self.get_team(team_id)
        if not team:
            raise NotFoundException(f"Team with ID {team_id} not found")

        # Check for existing pending invitation for same email/team
        existing = self.session.query(TeamInvitation).filter(
            TeamInvitation.team_id == team_id,
            TeamInvitation.email == email,
            TeamInvitation.status == 'pending'
        ).first()

        if existing:
            raise ValidationException(f"Pending invitation already exists for {email} to team {team_id}")

        invitation = TeamInvitation(
            team_id=team_id,
            email=email,
            role_id=role_id,
            invited_by_user_id=invited_by_user_id,
            token=token,
            expires_at=expires_at,
            status='pending'
        )

        self.session.add(invitation)
        self.session.flush()
        logger.info(f"Invitation created for {email} to team {team_id}")

        return invitation

    def get_invitation_by_token(self, token: str) -> Optional[TeamInvitation]:
        """Get invitation by token"""
        return self.session.query(TeamInvitation).filter(
            TeamInvitation.token == token
        ).first()

    def get_invitations_for_team(
        self,
        team_id: int,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TeamInvitation]:
        """Get all invitations for a team"""
        query = self.session.query(TeamInvitation).filter(TeamInvitation.team_id == team_id)

        if status:
            query = query.filter(TeamInvitation.status == status)

        return query.order_by(TeamInvitation.created_at.desc()).offset(offset).limit(limit).all()

    def get_pending_invitations_for_email(self, email: str) -> List[TeamInvitation]:
        """Get all pending invitations for an email"""
        now = datetime.utcnow()
        return self.session.query(TeamInvitation).filter(
            TeamInvitation.email == email,
            TeamInvitation.status == 'pending',
            TeamInvitation.expires_at > now
        ).all()

    def accept_invitation(
        self,
        invitation_id: int,
        accepted_by_user_id: str
    ) -> TeamInvitation:
        """Accept an invitation"""
        invitation = self.session.query(TeamInvitation).filter(
            TeamInvitation.id == invitation_id
        ).first()

        if not invitation:
            raise NotFoundException(f"Invitation with ID {invitation_id} not found")

        if invitation.status != 'pending':
            raise ValidationException(f"Invitation is not pending (status: {invitation.status})")

        now = datetime.utcnow()
        if invitation.expires_at < now:
            invitation.status = 'expired'
            self.session.flush()
            raise ValidationException("Invitation has expired")

        invitation.status = 'accepted'
        invitation.accepted_at = now
        invitation.accepted_by_user_id = accepted_by_user_id
        self.session.flush()
        logger.info(f"Invitation {invitation_id} accepted by user {accepted_by_user_id}")

        return invitation

    def revoke_invitation(self, invitation_id: int) -> bool:
        """Revoke an invitation"""
        invitation = self.session.query(TeamInvitation).filter(
            TeamInvitation.id == invitation_id,
            TeamInvitation.status == 'pending'
        ).first()

        if not invitation:
            return False

        invitation.status = 'revoked'
        invitation.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Invitation {invitation_id} revoked")

        return True

    def expire_invitations(self) -> int:
        """Mark expired invitations as expired (returns count of updated)"""
        now = datetime.utcnow()
        result = self.session.query(TeamInvitation).filter(
            TeamInvitation.status == 'pending',
            TeamInvitation.expires_at < now
        ).update(
            {'status': 'expired', 'updated_at': now},
            synchronize_session='fetch'
        )
        self.session.flush()
        if result > 0:
            logger.info(f"Expired {result} invitations")

        return result

    # Quota operations

    def get_quota(self, team_id: int) -> Optional[TeamQuota]:
        """Get team quota"""
        return self.session.query(TeamQuota).filter(
            TeamQuota.team_id == team_id
        ).first()

    def create_or_update_quota(
        self,
        team_id: int,
        max_gpu_hours_per_month: Optional[float] = None,
        max_concurrent_instances: Optional[int] = None,
        max_monthly_budget_usd: Optional[float] = None
    ) -> TeamQuota:
        """Create or update team quota"""
        # Check if team exists
        team = self.get_team(team_id)
        if not team:
            raise NotFoundException(f"Team with ID {team_id} not found")

        quota = self.get_quota(team_id)

        if quota:
            # Update existing quota
            if max_gpu_hours_per_month is not None:
                quota.max_gpu_hours_per_month = max_gpu_hours_per_month
            if max_concurrent_instances is not None:
                quota.max_concurrent_instances = max_concurrent_instances
            if max_monthly_budget_usd is not None:
                quota.max_monthly_budget_usd = max_monthly_budget_usd
            quota.updated_at = datetime.utcnow()
            logger.info(f"Quota updated for team {team_id}")
        else:
            # Create new quota
            quota = TeamQuota(
                team_id=team_id,
                max_gpu_hours_per_month=max_gpu_hours_per_month,
                max_concurrent_instances=max_concurrent_instances,
                max_monthly_budget_usd=max_monthly_budget_usd
            )
            self.session.add(quota)
            logger.info(f"Quota created for team {team_id}")

        self.session.flush()
        return quota

    def update_quota_usage(
        self,
        team_id: int,
        gpu_hours_delta: float = 0,
        instances_delta: int = 0,
        spend_delta: float = 0
    ) -> TeamQuota:
        """Update quota usage counters"""
        quota = self.get_quota(team_id)
        if not quota:
            raise NotFoundException(f"Quota for team {team_id} not found")

        quota.current_gpu_hours_used += gpu_hours_delta
        quota.current_concurrent_instances += instances_delta
        quota.current_monthly_spend_usd += spend_delta
        quota.updated_at = datetime.utcnow()

        self.session.flush()
        logger.info(f"Quota usage updated for team {team_id}")

        return quota

    def check_quota_available(
        self,
        team_id: int,
        gpu_hours_needed: float = 0,
        instances_needed: int = 0,
        budget_needed: float = 0
    ) -> Dict[str, Any]:
        """Check if quota is available for requested resources"""
        quota = self.get_quota(team_id)

        result = {
            'available': True,
            'quota_exists': quota is not None,
            'violations': []
        }

        if not quota:
            # No quota set means unlimited
            return result

        # Check GPU hours
        if quota.max_gpu_hours_per_month is not None:
            if quota.current_gpu_hours_used + gpu_hours_needed > quota.max_gpu_hours_per_month:
                result['available'] = False
                result['violations'].append({
                    'type': 'gpu_hours',
                    'current': quota.current_gpu_hours_used,
                    'limit': quota.max_gpu_hours_per_month,
                    'requested': gpu_hours_needed
                })

        # Check concurrent instances
        if quota.max_concurrent_instances is not None:
            if quota.current_concurrent_instances + instances_needed > quota.max_concurrent_instances:
                result['available'] = False
                result['violations'].append({
                    'type': 'concurrent_instances',
                    'current': quota.current_concurrent_instances,
                    'limit': quota.max_concurrent_instances,
                    'requested': instances_needed
                })

        # Check budget
        if quota.max_monthly_budget_usd is not None:
            if quota.current_monthly_spend_usd + budget_needed > quota.max_monthly_budget_usd:
                result['available'] = False
                result['violations'].append({
                    'type': 'monthly_budget',
                    'current': quota.current_monthly_spend_usd,
                    'limit': quota.max_monthly_budget_usd,
                    'requested': budget_needed
                })

        return result
