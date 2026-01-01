"""
SQLAlchemy Role Repository Implementation
Implements IRoleRepository interface (Dependency Inversion Principle)
"""
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ...core.exceptions import NotFoundException, ValidationException
from ...domain.repositories import IRoleRepository
from ...models.rbac import Role, Permission, TeamMember, role_permissions

logger = logging.getLogger(__name__)


class SQLAlchemyRoleRepository(IRoleRepository):
    """
    SQLAlchemy implementation of IRoleRepository.
    Stores roles and permissions in PostgreSQL.
    """

    def __init__(self, session: Session):
        """
        Initialize SQLAlchemy role repository

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    # Role CRUD operations

    def get_role(self, role_id: int) -> Optional[Role]:
        """Get role by ID"""
        return self.session.query(Role).filter(Role.id == role_id).first()

    def get_role_by_name(self, name: str, team_id: Optional[int] = None) -> Optional[Role]:
        """Get role by name (and optionally team for custom roles)"""
        query = self.session.query(Role).filter(Role.name == name)

        if team_id is not None:
            # Looking for custom team role
            query = query.filter(Role.team_id == team_id)
        else:
            # Looking for system role
            query = query.filter(Role.is_system == True)

        return query.first()

    def create_role(
        self,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        team_id: Optional[int] = None,
        is_system: bool = False
    ) -> Role:
        """Create a new role"""
        if not name or not display_name:
            raise ValidationException("Name and display_name are required")

        # Check for duplicate name in same scope
        if is_system:
            existing = self.session.query(Role).filter(
                Role.name == name,
                Role.is_system == True
            ).first()
        else:
            existing = self.session.query(Role).filter(
                Role.name == name,
                Role.team_id == team_id
            ).first()

        if existing:
            raise ValidationException(f"Role with name '{name}' already exists in this scope")

        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            team_id=team_id,
            is_system=is_system
        )

        self.session.add(role)
        self.session.flush()
        logger.info(f"Role '{name}' created with ID {role.id}")

        return role

    def update_role(self, role_id: int, updates: Dict[str, Any]) -> Role:
        """Update role information (not allowed for system roles)"""
        role = self.get_role(role_id)
        if not role:
            raise NotFoundException(f"Role with ID {role_id} not found")

        if role.is_system:
            raise ValidationException("Cannot modify system roles")

        # Update allowed fields
        if "name" in updates:
            # Check for duplicate name
            existing = self.session.query(Role).filter(
                Role.name == updates["name"],
                Role.id != role_id,
                Role.team_id == role.team_id
            ).first()
            if existing:
                raise ValidationException(f"Role with name '{updates['name']}' already exists")
            role.name = updates["name"]

        if "display_name" in updates:
            role.display_name = updates["display_name"]

        if "description" in updates:
            role.description = updates["description"]

        self.session.flush()
        logger.info(f"Role {role_id} updated")

        return role

    def delete_role(self, role_id: int) -> bool:
        """Delete a role (not allowed for system roles or roles with members)"""
        role = self.get_role(role_id)
        if not role:
            return False

        if role.is_system:
            raise ValidationException("Cannot delete system roles")

        if self.has_members_assigned(role_id):
            raise ValidationException("Cannot delete role with active members")

        self.session.delete(role)
        self.session.flush()
        logger.info(f"Role {role_id} deleted")

        return True

    def list_system_roles(self) -> List[Role]:
        """List all system (predefined) roles"""
        return self.session.query(Role).filter(Role.is_system == True).all()

    def list_team_roles(self, team_id: int) -> List[Role]:
        """List all custom roles for a team"""
        return self.session.query(Role).filter(
            Role.team_id == team_id,
            Role.is_system == False
        ).all()

    def list_available_roles(self, team_id: int) -> List[Role]:
        """List all roles available for a team (system + custom)"""
        return self.session.query(Role).filter(
            or_(
                Role.is_system == True,
                Role.team_id == team_id
            )
        ).all()

    # Permission operations

    def get_permission(self, permission_id: int) -> Optional[Permission]:
        """Get permission by ID"""
        return self.session.query(Permission).filter(
            Permission.id == permission_id
        ).first()

    def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name (e.g., 'gpu.provision')"""
        return self.session.query(Permission).filter(
            Permission.name == name
        ).first()

    def list_permissions(self, category: Optional[str] = None) -> List[Permission]:
        """List all permissions, optionally filtered by category"""
        query = self.session.query(Permission)

        if category:
            query = query.filter(Permission.category == category)

        return query.order_by(Permission.category, Permission.name).all()

    def get_permissions_for_role(self, role_id: int) -> List[Permission]:
        """Get all permissions assigned to a role"""
        role = self.get_role(role_id)
        if not role:
            raise NotFoundException(f"Role with ID {role_id} not found")

        return list(role.permissions)

    # Role-Permission assignment

    def assign_permission_to_role(self, role_id: int, permission_id: int) -> bool:
        """Assign a permission to a role"""
        role = self.get_role(role_id)
        if not role:
            raise NotFoundException(f"Role with ID {role_id} not found")

        if role.is_system:
            raise ValidationException("Cannot modify permissions of system roles")

        permission = self.get_permission(permission_id)
        if not permission:
            raise NotFoundException(f"Permission with ID {permission_id} not found")

        if permission not in role.permissions:
            role.permissions.append(permission)
            self.session.flush()
            logger.info(f"Permission {permission_id} assigned to role {role_id}")
            return True

        return False  # Already assigned

    def remove_permission_from_role(self, role_id: int, permission_id: int) -> bool:
        """Remove a permission from a role"""
        role = self.get_role(role_id)
        if not role:
            raise NotFoundException(f"Role with ID {role_id} not found")

        if role.is_system:
            raise ValidationException("Cannot modify permissions of system roles")

        permission = self.get_permission(permission_id)
        if not permission:
            raise NotFoundException(f"Permission with ID {permission_id} not found")

        if permission in role.permissions:
            role.permissions.remove(permission)
            self.session.flush()
            logger.info(f"Permission {permission_id} removed from role {role_id}")
            return True

        return False  # Not assigned

    def set_role_permissions(self, role_id: int, permission_ids: List[int]) -> Role:
        """Set all permissions for a role (replaces existing)"""
        role = self.get_role(role_id)
        if not role:
            raise NotFoundException(f"Role with ID {role_id} not found")

        if role.is_system:
            raise ValidationException("Cannot modify permissions of system roles")

        # Get all permissions
        permissions = self.session.query(Permission).filter(
            Permission.id.in_(permission_ids)
        ).all()

        if len(permissions) != len(permission_ids):
            found_ids = {p.id for p in permissions}
            missing_ids = set(permission_ids) - found_ids
            raise NotFoundException(f"Permissions not found: {missing_ids}")

        # Replace all permissions
        role.permissions = permissions
        self.session.flush()
        logger.info(f"Role {role_id} permissions set to {permission_ids}")

        return role

    # Role validation

    def has_members_assigned(self, role_id: int) -> bool:
        """Check if any members are assigned to this role"""
        count = self.session.query(TeamMember).filter(
            TeamMember.role_id == role_id,
            TeamMember.is_active == True,
            TeamMember.removed_at.is_(None)
        ).count()

        return count > 0

    def is_system_role(self, role_id: int) -> bool:
        """Check if role is a system (predefined) role"""
        role = self.get_role(role_id)
        if not role:
            return False
        return role.is_system

    # User permission checking

    def get_user_permissions(self, user_id: str, team_id: int) -> List[str]:
        """Get all permission names for a user in a team"""
        # Get the user's role in the team
        member = self.session.query(TeamMember).filter(
            TeamMember.user_id == user_id,
            TeamMember.team_id == team_id,
            TeamMember.is_active == True,
            TeamMember.removed_at.is_(None)
        ).first()

        if not member:
            return []

        # Get all permissions for the role
        role = self.get_role(member.role_id)
        if not role:
            return []

        return [p.name for p in role.permissions]

    def user_has_permission(
        self,
        user_id: str,
        team_id: int,
        permission_name: str
    ) -> bool:
        """Check if user has a specific permission in a team"""
        permissions = self.get_user_permissions(user_id, team_id)
        return permission_name in permissions

    def get_user_role(self, user_id: str, team_id: int) -> Optional[Role]:
        """Get user's role in a team"""
        member = self.session.query(TeamMember).filter(
            TeamMember.user_id == user_id,
            TeamMember.team_id == team_id,
            TeamMember.is_active == True,
            TeamMember.removed_at.is_(None)
        ).first()

        if not member:
            return None

        return self.get_role(member.role_id)
