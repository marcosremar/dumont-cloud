"""
Abstract interface for role storage (Dependency Inversion Principle)
Allows swapping between different storage implementations
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class IRoleRepository(ABC):
    """Abstract interface for role storage"""

    # Role CRUD operations
    @abstractmethod
    def get_role(self, role_id: int) -> Optional[Any]:
        """Get role by ID"""
        pass

    @abstractmethod
    def get_role_by_name(self, name: str, team_id: Optional[int] = None) -> Optional[Any]:
        """Get role by name (and optionally team for custom roles)"""
        pass

    @abstractmethod
    def create_role(
        self,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        team_id: Optional[int] = None,
        is_system: bool = False
    ) -> Any:
        """Create a new role"""
        pass

    @abstractmethod
    def update_role(self, role_id: int, updates: Dict[str, Any]) -> Any:
        """Update role information (not allowed for system roles)"""
        pass

    @abstractmethod
    def delete_role(self, role_id: int) -> bool:
        """Delete a role (not allowed for system roles or roles with members)"""
        pass

    @abstractmethod
    def list_system_roles(self) -> List[Any]:
        """List all system (predefined) roles"""
        pass

    @abstractmethod
    def list_team_roles(self, team_id: int) -> List[Any]:
        """List all custom roles for a team"""
        pass

    @abstractmethod
    def list_available_roles(self, team_id: int) -> List[Any]:
        """List all roles available for a team (system + custom)"""
        pass

    # Permission operations
    @abstractmethod
    def get_permission(self, permission_id: int) -> Optional[Any]:
        """Get permission by ID"""
        pass

    @abstractmethod
    def get_permission_by_name(self, name: str) -> Optional[Any]:
        """Get permission by name (e.g., 'gpu.provision')"""
        pass

    @abstractmethod
    def list_permissions(self, category: Optional[str] = None) -> List[Any]:
        """List all permissions, optionally filtered by category"""
        pass

    @abstractmethod
    def get_permissions_for_role(self, role_id: int) -> List[Any]:
        """Get all permissions assigned to a role"""
        pass

    # Role-Permission assignment
    @abstractmethod
    def assign_permission_to_role(self, role_id: int, permission_id: int) -> bool:
        """Assign a permission to a role"""
        pass

    @abstractmethod
    def remove_permission_from_role(self, role_id: int, permission_id: int) -> bool:
        """Remove a permission from a role"""
        pass

    @abstractmethod
    def set_role_permissions(self, role_id: int, permission_ids: List[int]) -> Any:
        """Set all permissions for a role (replaces existing)"""
        pass

    # Role validation
    @abstractmethod
    def has_members_assigned(self, role_id: int) -> bool:
        """Check if any members are assigned to this role"""
        pass

    @abstractmethod
    def is_system_role(self, role_id: int) -> bool:
        """Check if role is a system (predefined) role"""
        pass

    # User permission checking
    @abstractmethod
    def get_user_permissions(self, user_id: str, team_id: int) -> List[str]:
        """Get all permission names for a user in a team"""
        pass

    @abstractmethod
    def user_has_permission(
        self,
        user_id: str,
        team_id: int,
        permission_name: str
    ) -> bool:
        """Check if user has a specific permission in a team"""
        pass

    @abstractmethod
    def get_user_role(self, user_id: str, team_id: int) -> Optional[Any]:
        """Get user's role in a team"""
        pass
