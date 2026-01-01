"""
Abstract interface for team storage (Dependency Inversion Principle)
Allows swapping between different storage implementations
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class ITeamRepository(ABC):
    """Abstract interface for team storage"""

    # Team CRUD operations
    @abstractmethod
    def get_team(self, team_id: int) -> Optional[Any]:
        """Get team by ID"""
        pass

    @abstractmethod
    def get_team_by_slug(self, slug: str) -> Optional[Any]:
        """Get team by URL-friendly slug"""
        pass

    @abstractmethod
    def get_team_by_name(self, name: str) -> Optional[Any]:
        """Get team by name"""
        pass

    @abstractmethod
    def create_team(
        self,
        name: str,
        slug: str,
        owner_user_id: str,
        description: Optional[str] = None
    ) -> Any:
        """Create a new team"""
        pass

    @abstractmethod
    def update_team(self, team_id: int, updates: Dict[str, Any]) -> Any:
        """Update team information"""
        pass

    @abstractmethod
    def delete_team(self, team_id: int) -> bool:
        """Soft delete a team (sets deleted_at timestamp)"""
        pass

    @abstractmethod
    def list_teams(
        self,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """List all teams with pagination"""
        pass

    @abstractmethod
    def get_teams_for_user(self, user_id: str) -> List[Any]:
        """Get all teams where user is a member"""
        pass

    # Team member operations
    @abstractmethod
    def add_member(
        self,
        team_id: int,
        user_id: str,
        role_id: int,
        invited_by_user_id: Optional[str] = None,
        invited_at: Optional[datetime] = None
    ) -> Any:
        """Add a member to the team"""
        pass

    @abstractmethod
    def remove_member(
        self,
        team_id: int,
        user_id: str,
        removed_by_user_id: Optional[str] = None
    ) -> bool:
        """Soft delete a team member (sets removed_at timestamp)"""
        pass

    @abstractmethod
    def get_member(self, team_id: int, user_id: str) -> Optional[Any]:
        """Get a specific team member"""
        pass

    @abstractmethod
    def get_members(
        self,
        team_id: int,
        include_removed: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """Get all members of a team with pagination"""
        pass

    @abstractmethod
    def update_member_role(
        self,
        team_id: int,
        user_id: str,
        role_id: int
    ) -> Any:
        """Update a member's role"""
        pass

    @abstractmethod
    def is_member(self, team_id: int, user_id: str) -> bool:
        """Check if user is an active member of the team"""
        pass

    @abstractmethod
    def get_member_count(self, team_id: int) -> int:
        """Get count of active members in a team"""
        pass

    @abstractmethod
    def get_admin_count(self, team_id: int) -> int:
        """Get count of admins in a team (prevents removing last admin)"""
        pass

    # Invitation operations
    @abstractmethod
    def create_invitation(
        self,
        team_id: int,
        email: str,
        role_id: int,
        invited_by_user_id: str,
        token: str,
        expires_at: datetime
    ) -> Any:
        """Create a team invitation"""
        pass

    @abstractmethod
    def get_invitation_by_token(self, token: str) -> Optional[Any]:
        """Get invitation by token"""
        pass

    @abstractmethod
    def get_invitations_for_team(
        self,
        team_id: int,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """Get all invitations for a team"""
        pass

    @abstractmethod
    def get_pending_invitations_for_email(self, email: str) -> List[Any]:
        """Get all pending invitations for an email"""
        pass

    @abstractmethod
    def accept_invitation(
        self,
        invitation_id: int,
        accepted_by_user_id: str
    ) -> Any:
        """Accept an invitation"""
        pass

    @abstractmethod
    def revoke_invitation(self, invitation_id: int) -> bool:
        """Revoke an invitation"""
        pass

    @abstractmethod
    def expire_invitations(self) -> int:
        """Mark expired invitations as expired (returns count of updated)"""
        pass

    # Quota operations
    @abstractmethod
    def get_quota(self, team_id: int) -> Optional[Any]:
        """Get team quota"""
        pass

    @abstractmethod
    def create_or_update_quota(
        self,
        team_id: int,
        max_gpu_hours_per_month: Optional[float] = None,
        max_concurrent_instances: Optional[int] = None,
        max_monthly_budget_usd: Optional[float] = None
    ) -> Any:
        """Create or update team quota"""
        pass

    @abstractmethod
    def update_quota_usage(
        self,
        team_id: int,
        gpu_hours_delta: float = 0,
        instances_delta: int = 0,
        spend_delta: float = 0
    ) -> Any:
        """Update quota usage counters"""
        pass

    @abstractmethod
    def check_quota_available(
        self,
        team_id: int,
        gpu_hours_needed: float = 0,
        instances_needed: int = 0,
        budget_needed: float = 0
    ) -> Dict[str, Any]:
        """Check if quota is available for requested resources"""
        pass
