"""
Role Management API endpoints

CRUD operations for roles and permissions, including:
- List all available permissions
- List predefined system roles
- Create custom team roles
- List team's custom roles
- Delete custom roles (blocked if members are assigned)
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from ..dependencies import (
    get_current_user_email,
    require_permission,
)
from ....config.database import get_db
from ....core.permissions import TEAM_MANAGE, AUDIT_VIEW
from ....core.exceptions import NotFoundException, ValidationException
from ....infrastructure.providers import SQLAlchemyRoleRepository, SQLAlchemyTeamRepository
from ....models.rbac import Role, Permission

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Roles & Permissions"])


# Helper functions

def get_role_repository(db: Session = Depends(get_db)) -> SQLAlchemyRoleRepository:
    """Get role repository instance"""
    return SQLAlchemyRoleRepository(session=db)


def get_team_repository(db: Session = Depends(get_db)) -> SQLAlchemyTeamRepository:
    """Get team repository instance"""
    return SQLAlchemyTeamRepository(session=db)


# Request/Response models

class PermissionResponse(BaseModel):
    """Permission response"""
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    category: str

    class Config:
        from_attributes = True


class PermissionListResponse(BaseModel):
    """Permission list response"""
    permissions: List[PermissionResponse]
    count: int
    categories: List[str]


class RoleResponse(BaseModel):
    """Role response"""
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    is_system: bool
    team_id: Optional[int] = None
    permissions: Optional[List[PermissionResponse]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    """Role list response"""
    roles: List[RoleResponse]
    count: int


class CreateRoleRequest(BaseModel):
    """Create custom role request"""
    name: str = Field(..., min_length=1, max_length=100, description="Role name (unique within team)")
    display_name: str = Field(..., min_length=1, max_length=100, description="Display name for the role")
    description: Optional[str] = Field(None, max_length=500, description="Role description")
    permission_ids: List[int] = Field(..., min_length=1, description="List of permission IDs to assign")


class UpdateRoleRequest(BaseModel):
    """Update custom role request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Role name")
    display_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Display name")
    description: Optional[str] = Field(None, max_length=500, description="Role description")
    permission_ids: Optional[List[int]] = Field(None, description="List of permission IDs to assign")


# Permission Endpoints

@router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions(
    user_email: str = Depends(get_current_user_email),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    category: Optional[str] = Query(None, description="Filter by category: gpu, cost, team, settings, audit"),
):
    """
    List all available permissions

    Returns all permissions that can be assigned to roles. Optionally filter by category.
    """
    permissions = role_repo.list_permissions(category=category)

    # Get unique categories
    all_permissions = role_repo.list_permissions()
    categories = sorted(list(set(p.category for p in all_permissions)))

    permission_responses = [
        PermissionResponse(
            id=p.id,
            name=p.name,
            display_name=p.display_name,
            description=p.description,
            category=p.category,
        )
        for p in permissions
    ]

    return PermissionListResponse(
        permissions=permission_responses,
        count=len(permission_responses),
        categories=categories,
    )


@router.get("/permissions/categories", response_model=List[str])
async def list_permission_categories(
    user_email: str = Depends(get_current_user_email),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
):
    """
    List all permission categories

    Returns unique categories for permissions (gpu, cost, team, settings, audit).
    """
    permissions = role_repo.list_permissions()
    categories = sorted(list(set(p.category for p in permissions)))
    return categories


# Role Endpoints

@router.get("/roles", response_model=RoleListResponse)
async def list_system_roles(
    user_email: str = Depends(get_current_user_email),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    include_permissions: bool = Query(False, description="Include permissions for each role"),
):
    """
    List predefined system roles

    Returns the predefined roles (Admin, Developer, Viewer) that are available globally.
    """
    roles = role_repo.list_system_roles()

    role_responses = []
    for role in roles:
        role_permissions = None
        if include_permissions:
            perms = role_repo.get_permissions_for_role(role.id)
            role_permissions = [
                PermissionResponse(
                    id=p.id,
                    name=p.name,
                    display_name=p.display_name,
                    description=p.description,
                    category=p.category,
                )
                for p in perms
            ]

        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            is_system=role.is_system,
            team_id=role.team_id,
            permissions=role_permissions,
            created_at=role.created_at,
            updated_at=role.updated_at,
        ))

    return RoleListResponse(
        roles=role_responses,
        count=len(role_responses),
    )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    user_email: str = Depends(get_current_user_email),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    include_permissions: bool = Query(True, description="Include permissions for the role"),
):
    """
    Get role details by ID

    Returns detailed information about a specific role including its permissions.
    """
    role = role_repo.get_role(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    role_permissions = None
    if include_permissions:
        perms = role_repo.get_permissions_for_role(role.id)
        role_permissions = [
            PermissionResponse(
                id=p.id,
                name=p.name,
                display_name=p.display_name,
                description=p.description,
                category=p.category,
            )
            for p in perms
        ]

    return RoleResponse(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        is_system=role.is_system,
        team_id=role.team_id,
        permissions=role_permissions,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


# Team Custom Role Endpoints

@router.get("/teams/{team_id}/roles", response_model=RoleListResponse)
async def list_team_roles(
    team_id: int,
    user_email: str = Depends(get_current_user_email),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    include_system: bool = Query(True, description="Include system roles in the list"),
    include_permissions: bool = Query(False, description="Include permissions for each role"),
):
    """
    List roles available for a team

    Returns custom team roles and optionally the system roles.
    Requires team membership.
    """
    # Check if user is a member of the team
    member = team_repo.get_member(team_id, user_email)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    if include_system:
        roles = role_repo.list_available_roles(team_id)
    else:
        roles = role_repo.list_team_roles(team_id)

    role_responses = []
    for role in roles:
        role_permissions = None
        if include_permissions:
            perms = role_repo.get_permissions_for_role(role.id)
            role_permissions = [
                PermissionResponse(
                    id=p.id,
                    name=p.name,
                    display_name=p.display_name,
                    description=p.description,
                    category=p.category,
                )
                for p in perms
            ]

        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            is_system=role.is_system,
            team_id=role.team_id,
            permissions=role_permissions,
            created_at=role.created_at,
            updated_at=role.updated_at,
        ))

    return RoleListResponse(
        roles=role_responses,
        count=len(role_responses),
    )


@router.post("/teams/{team_id}/roles", status_code=status.HTTP_201_CREATED, response_model=RoleResponse)
async def create_custom_role(
    team_id: int,
    request: CreateRoleRequest,
    user_email: str = Depends(require_permission(TEAM_MANAGE)),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Create a custom role for a team

    Creates a new role with the specified permissions. Requires team.manage permission.
    Custom roles are team-specific and cannot modify system roles.
    """
    try:
        # Check if user is a member of the team
        member = team_repo.get_member(team_id, user_email)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team",
            )

        # Validate that all permission IDs exist
        for perm_id in request.permission_ids:
            perm = role_repo.get_permission(perm_id)
            if not perm:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permission with ID {perm_id} not found",
                )

        # Create the role
        role = role_repo.create_role(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            team_id=team_id,
            is_system=False,
        )

        # Assign permissions
        role = role_repo.set_role_permissions(role.id, request.permission_ids)

        db.commit()
        logger.info(f"Custom role '{request.name}' created for team {team_id} by {user_email}")

        # Get permissions for response
        perms = role_repo.get_permissions_for_role(role.id)
        role_permissions = [
            PermissionResponse(
                id=p.id,
                name=p.name,
                display_name=p.display_name,
                description=p.description,
                category=p.category,
            )
            for p in perms
        ]

        return RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            is_system=role.is_system,
            team_id=role.team_id,
            permissions=role_permissions,
            created_at=role.created_at,
            updated_at=role.updated_at,
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
        logger.error(f"Error creating custom role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create custom role: {str(e)}",
        )


@router.put("/teams/{team_id}/roles/{role_id}", response_model=RoleResponse)
async def update_custom_role(
    team_id: int,
    role_id: int,
    request: UpdateRoleRequest,
    user_email: str = Depends(require_permission(TEAM_MANAGE)),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Update a custom role

    Updates the name, description, or permissions of a custom role.
    Requires team.manage permission. System roles cannot be modified.
    """
    try:
        # Check if user is a member of the team
        member = team_repo.get_member(team_id, user_email)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team",
            )

        # Get the role
        role = role_repo.get_role(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found",
            )

        # Verify role belongs to this team
        if role.team_id != team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This role does not belong to this team",
            )

        # Cannot modify system roles
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify system roles",
            )

        # Build updates dict
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.display_name is not None:
            updates["display_name"] = request.display_name
        if request.description is not None:
            updates["description"] = request.description

        # Update role info if there are updates
        if updates:
            role = role_repo.update_role(role_id, updates)

        # Update permissions if provided
        if request.permission_ids is not None:
            # Validate all permission IDs exist
            for perm_id in request.permission_ids:
                perm = role_repo.get_permission(perm_id)
                if not perm:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Permission with ID {perm_id} not found",
                    )
            role = role_repo.set_role_permissions(role_id, request.permission_ids)

        db.commit()
        logger.info(f"Custom role {role_id} updated in team {team_id} by {user_email}")

        # Get permissions for response
        perms = role_repo.get_permissions_for_role(role.id)
        role_permissions = [
            PermissionResponse(
                id=p.id,
                name=p.name,
                display_name=p.display_name,
                description=p.description,
                category=p.category,
            )
            for p in perms
        ]

        return RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            is_system=role.is_system,
            team_id=role.team_id,
            permissions=role_permissions,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )

    except ValidationException as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except NotFoundException as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating custom role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update custom role: {str(e)}",
        )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    user_email: str = Depends(require_permission(TEAM_MANAGE)),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Delete a custom role

    Deletes a custom role. Cannot delete system roles or roles with active members.
    Requires team.manage permission for the team the role belongs to.
    """
    try:
        # Get the role
        role = role_repo.get_role(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found",
            )

        # Cannot delete system roles
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete system roles",
            )

        # Verify user is a member of the team
        if role.team_id:
            member = team_repo.get_member(role.team_id, user_email)
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not a member of the team this role belongs to",
                )

        # Check if role has active members
        if role_repo.has_members_assigned(role_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete role with active members. Reassign members to a different role first.",
            )

        # Delete the role
        success = role_repo.delete_role(role_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete role",
            )

        db.commit()
        logger.info(f"Custom role {role_id} deleted by {user_email}")

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
        logger.error(f"Error deleting role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete role: {str(e)}",
        )


@router.delete("/teams/{team_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_role(
    team_id: int,
    role_id: int,
    user_email: str = Depends(require_permission(TEAM_MANAGE)),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    db: Session = Depends(get_db),
):
    """
    Delete a custom role for a team

    Deletes a custom role from the specified team. Cannot delete system roles or
    roles with active members. Requires team.manage permission.
    """
    try:
        # Check if user is a member of the team
        member = team_repo.get_member(team_id, user_email)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team",
            )

        # Get the role
        role = role_repo.get_role(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found",
            )

        # Verify role belongs to this team
        if role.team_id != team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This role does not belong to this team",
            )

        # Cannot delete system roles
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete system roles",
            )

        # Check if role has active members
        if role_repo.has_members_assigned(role_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete role with active members. Reassign members to a different role first.",
            )

        # Delete the role
        success = role_repo.delete_role(role_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete role",
            )

        db.commit()
        logger.info(f"Custom role {role_id} deleted from team {team_id} by {user_email}")

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
        logger.error(f"Error deleting team role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete team role: {str(e)}",
        )
