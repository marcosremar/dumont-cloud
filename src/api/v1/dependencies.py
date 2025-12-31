"""
FastAPI Dependencies (Dependency Injection)
"""
from typing import Optional, Generator, Callable, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.jwt import create_access_token, verify_token, decode_token
from ...domain.services import InstanceService, SnapshotService, AuthService, MigrationService, SyncService
from ...domain.repositories import IGpuProvider, ISnapshotProvider, IUserRepository
from ...infrastructure.providers import VastProvider, ResticProvider, FileUserRepository
from ...config.database import get_db
from ...infrastructure.providers import SQLAlchemyRoleRepository

# Security
security = HTTPBearer(auto_error=False)


# JWT-based Session Management
class SessionManager:
    """JWT-based session manager (stateless)"""

    def create_session(self, user_email: str) -> str:
        """Create a new JWT token for user"""
        return create_access_token(user_email)

    def get_user_email(self, token: str) -> Optional[str]:
        """Verify JWT and get user email"""
        return verify_token(token)

    def destroy_session(self, user_email: str):
        """JWT tokens are stateless - logout is handled client-side"""
        pass


# Global session manager instance
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get session manager instance"""
    return _session_manager


# Repository Dependencies

def get_user_repository() -> Generator[IUserRepository, None, None]:
    """Get user repository instance"""
    settings = get_settings()
    repo = FileUserRepository(config_file=settings.app.config_file)
    yield repo


# Authentication Dependencies (must be defined before service dependencies)

def get_current_user_email_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_manager: SessionManager = Depends(get_session_manager),
) -> Optional[str]:
    """Get current user email (returns None if not authenticated)"""
    # Check for demo mode (from env or query param)
    settings = get_settings()
    demo_param = request.query_params.get("demo", "").lower() == "true"

    if settings.app.demo_mode or demo_param:
        return "marcosremar@gmail.com"

    # Check Authorization header
    if credentials:
        token = credentials.credentials
        user_email = session_manager.get_user_email(token)
        if user_email:
            return user_email

    # Check session cookie (for compatibility with Flask)
    if hasattr(request.state, "user_email"):
        return request.state.user_email

    return None


def get_current_user_email(
    user_email: Optional[str] = Depends(get_current_user_email_optional),
) -> str:
    """Get current user email (raises exception if not authenticated)"""
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_email


def get_current_user(
    user_email: str = Depends(get_current_user_email),
    user_repo: IUserRepository = Depends(get_user_repository),
) -> any:
    """Get current user object (raises exception if not found)"""
    user = user_repo.get_user(user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def require_auth(
    user_email: str = Depends(get_current_user_email),
) -> str:
    """Require authentication (dependency for router)"""
    return user_email


# RBAC Dependencies - Permission and Role checking

def get_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Get the decoded JWT token payload.
    Returns None if no token or invalid token.
    """
    if not credentials:
        return None
    return decode_token(credentials.credentials)


def get_current_team_id(
    request: Request,
    token_payload: Optional[dict] = Depends(get_token_payload),
) -> Optional[int]:
    """
    Get the current team ID from JWT token or request header.
    Returns None if no team context is set.
    """
    # First try to get from JWT token payload
    if token_payload and "team_id" in token_payload:
        return token_payload["team_id"]

    # Fallback to request header (for team context switching)
    team_id_header = request.headers.get("X-Team-ID")
    if team_id_header:
        try:
            return int(team_id_header)
        except ValueError:
            pass

    return None


def get_role_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemyRoleRepository:
    """Get role repository instance"""
    return SQLAlchemyRoleRepository(session=db)


def require_permission(permission: str) -> Callable:
    """
    Factory function that creates a dependency requiring a specific permission.

    Usage:
        @router.post("/instances")
        async def create_instance(
            user_email: str = Depends(require_permission("gpu.provision"))
        ):
            ...

    Args:
        permission: The permission name required (e.g., "gpu.provision")

    Returns:
        A FastAPI dependency function that validates the permission
    """
    def permission_dependency(
        user_email: str = Depends(get_current_user_email),
        team_id: Optional[int] = Depends(get_current_team_id),
        role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    ) -> str:
        """Check if user has the required permission"""
        # If no team context, permission check fails
        if team_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No team context. Please select a team or include team_id in token.",
            )

        # Check if user has the required permission in the team
        has_permission = role_repo.user_has_permission(
            user_id=user_email,
            team_id=team_id,
            permission_name=permission,
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {permission}",
            )

        return user_email

    return permission_dependency


def require_permissions(permissions: List[str], require_all: bool = True) -> Callable:
    """
    Factory function that creates a dependency requiring multiple permissions.

    Usage:
        @router.delete("/instances/{id}")
        async def delete_instance(
            user_email: str = Depends(require_permissions(["gpu.view", "gpu.delete"]))
        ):
            ...

    Args:
        permissions: List of permission names required
        require_all: If True, user must have ALL permissions. If False, user needs at least one.

    Returns:
        A FastAPI dependency function that validates the permissions
    """
    def permissions_dependency(
        user_email: str = Depends(get_current_user_email),
        team_id: Optional[int] = Depends(get_current_team_id),
        role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    ) -> str:
        """Check if user has the required permissions"""
        # If no team context, permission check fails
        if team_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No team context. Please select a team or include team_id in token.",
            )

        # Get user's permissions
        user_permissions = role_repo.get_user_permissions(
            user_id=user_email,
            team_id=team_id,
        )

        if require_all:
            # User must have ALL permissions
            missing = [p for p in permissions if p not in user_permissions]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Missing permissions: {', '.join(missing)}",
                )
        else:
            # User needs at least one permission
            has_any = any(p in user_permissions for p in permissions)
            if not has_any:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required one of: {', '.join(permissions)}",
                )

        return user_email

    return permissions_dependency


def require_role(role_name: str) -> Callable:
    """
    Factory function that creates a dependency requiring a specific role.

    Usage:
        @router.post("/teams/{team_id}/settings")
        async def update_settings(
            user_email: str = Depends(require_role("admin"))
        ):
            ...

    Args:
        role_name: The role name required (e.g., "admin", "developer", "viewer")

    Returns:
        A FastAPI dependency function that validates the role
    """
    def role_dependency(
        user_email: str = Depends(get_current_user_email),
        team_id: Optional[int] = Depends(get_current_team_id),
        role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    ) -> str:
        """Check if user has the required role"""
        # If no team context, role check fails
        if team_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No team context. Please select a team or include team_id in token.",
            )

        # Get user's role in the team
        user_role = role_repo.get_user_role(
            user_id=user_email,
            team_id=team_id,
        )

        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team.",
            )

        # Check if role matches (case-insensitive comparison)
        if user_role.name.lower() != role_name.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role denied. Required role: {role_name}, your role: {user_role.name}",
            )

        return user_email

    return role_dependency


def require_roles(role_names: List[str]) -> Callable:
    """
    Factory function that creates a dependency requiring one of the specified roles.

    Usage:
        @router.post("/instances")
        async def create_instance(
            user_email: str = Depends(require_roles(["admin", "developer"]))
        ):
            ...

    Args:
        role_names: List of acceptable role names (user must have one of them)

    Returns:
        A FastAPI dependency function that validates the role
    """
    def roles_dependency(
        user_email: str = Depends(get_current_user_email),
        team_id: Optional[int] = Depends(get_current_team_id),
        role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
    ) -> str:
        """Check if user has one of the required roles"""
        # If no team context, role check fails
        if team_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No team context. Please select a team or include team_id in token.",
            )

        # Get user's role in the team
        user_role = role_repo.get_user_role(
            user_id=user_email,
            team_id=team_id,
        )

        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team.",
            )

        # Check if role matches any of the allowed roles (case-insensitive)
        role_names_lower = [r.lower() for r in role_names]
        if user_role.name.lower() not in role_names_lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role denied. Required one of: {', '.join(role_names)}, your role: {user_role.name}",
            )

        return user_email

    return roles_dependency


def require_team_membership(
    user_email: str = Depends(get_current_user_email),
    team_id: Optional[int] = Depends(get_current_team_id),
    role_repo: SQLAlchemyRoleRepository = Depends(get_role_repository),
) -> str:
    """
    Dependency that requires user to be a member of the current team.
    Does not check for specific permissions or roles.

    Usage:
        @router.get("/teams/{team_id}/details")
        async def get_team_details(
            user_email: str = Depends(require_team_membership)
        ):
            ...
    """
    if team_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No team context. Please select a team or include team_id in token.",
        )

    user_role = role_repo.get_user_role(
        user_id=user_email,
        team_id=team_id,
    )

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team.",
        )

    return user_email


# Service Dependencies

def get_auth_service(
    user_repo: IUserRepository = Depends(get_user_repository),
) -> AuthService:
    """Get authentication service"""
    return AuthService(user_repository=user_repo)


def get_instance_service(
    user_email: str = Depends(get_current_user_email),
) -> InstanceService:
    """Get instance service"""
    import logging
    logger = logging.getLogger(__name__)

    settings = get_settings()

    # In demo mode, use demo provider that returns mock data
    if settings.app.demo_mode:
        from ...infrastructure.providers.demo_provider import DemoProvider
        gpu_provider = DemoProvider()
        return InstanceService(gpu_provider=gpu_provider)

    # Get user's vast API key, fallback to env var
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    # Try user's key first, then fall back to system key from .env
    user_api_key = user.vast_api_key if user else None
    system_api_key = settings.vast.api_key
    api_key = user_api_key or system_api_key

    logger.info(f"get_instance_service: user={user_email}, user_key={user_api_key[:10] if user_api_key else 'empty'}..., system_key={system_api_key[:10] if system_api_key else 'empty'}...")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured. Please update settings.",
        )

    gpu_provider = VastProvider(api_key=api_key)
    return InstanceService(gpu_provider=gpu_provider)


def get_snapshot_service(
    user_email: str = Depends(get_current_user_email),
) -> SnapshotService:
    """Get snapshot service"""
    # Get user's settings
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get R2 credentials from user settings or use defaults
    settings = get_settings()
    repo = user.settings.get("restic_repo") or settings.r2.restic_repo
    password = user.settings.get("restic_password") or settings.restic.password
    access_key = user.settings.get("r2_access_key") or settings.r2.access_key
    secret_key = user.settings.get("r2_secret_key") or settings.r2.secret_key

    if not repo or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restic repository not configured. Please update settings.",
        )

    snapshot_provider = ResticProvider(
        repo=repo,
        password=password,
        access_key=access_key,
        secret_key=secret_key,
    )
    return SnapshotService(snapshot_provider=snapshot_provider)


def get_snapshot_service_for_user(user_email: str) -> SnapshotService:
    """Get snapshot service for a specific user (callable without Depends)"""
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    settings = get_settings()
    repo = user.settings.get("restic_repo") or settings.r2.restic_repo
    password = user.settings.get("restic_password") or settings.restic.password
    access_key = user.settings.get("r2_access_key") or settings.r2.access_key
    secret_key = user.settings.get("r2_secret_key") or settings.r2.secret_key

    if not repo or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restic repository not configured. Please update settings.",
        )

    snapshot_provider = ResticProvider(
        repo=repo,
        password=password,
        access_key=access_key,
        secret_key=secret_key,
    )
    return SnapshotService(snapshot_provider=snapshot_provider)


def get_migration_service(
    user_email: str = Depends(get_current_user_email),
) -> MigrationService:
    """Get migration service"""
    from ...services.gpu.vast import VastService

    # Get user's settings
    settings = get_settings()
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    # Try user's key first, then fall back to system key from .env
    api_key = (user.vast_api_key if user else None) or settings.vast.api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured. Please update settings.",
        )

    # Get settings for snapshot provider
    repo = (user.settings.get("restic_repo") if user else None) or settings.r2.restic_repo
    password = (user.settings.get("restic_password") if user else None) or settings.restic.password
    access_key = (user.settings.get("r2_access_key") if user else None) or settings.r2.access_key
    secret_key = (user.settings.get("r2_secret_key") if user else None) or settings.r2.secret_key

    # Create services
    gpu_provider = VastProvider(api_key=api_key)
    instance_service = InstanceService(gpu_provider=gpu_provider)

    snapshot_provider = ResticProvider(
        repo=repo,
        password=password,
        access_key=access_key,
        secret_key=secret_key,
    )
    snapshot_service = SnapshotService(snapshot_provider=snapshot_provider)

    # Direct vast service for CPU operations
    vast_service = VastService(api_key=api_key)

    return MigrationService(
        instance_service=instance_service,
        snapshot_service=snapshot_service,
        vast_service=vast_service,
    )


# Global sync service instance (to maintain state across requests)
_sync_service_instance: Optional[SyncService] = None


def get_sync_service(
    user_email: str = Depends(get_current_user_email),
) -> SyncService:
    """Get sync service (singleton to maintain sync state)"""
    global _sync_service_instance

    # Get user's settings
    settings = get_settings()
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    # Try user's key first, then fall back to system key from .env
    api_key = (user.vast_api_key if user else None) or settings.vast.api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured. Please update settings.",
        )

    # Get settings for providers
    repo = (user.settings.get("restic_repo") if user else None) or settings.r2.restic_repo
    password = (user.settings.get("restic_password") if user else None) or settings.restic.password
    access_key = (user.settings.get("r2_access_key") if user else None) or settings.r2.access_key
    secret_key = (user.settings.get("r2_secret_key") if user else None) or settings.r2.secret_key

    # Create services
    gpu_provider = VastProvider(api_key=api_key)
    instance_service = InstanceService(gpu_provider=gpu_provider)

    snapshot_provider = ResticProvider(
        repo=repo,
        password=password,
        access_key=access_key,
        secret_key=secret_key,
    )
    snapshot_service = SnapshotService(snapshot_provider=snapshot_provider)

    # Create or reuse sync service
    if _sync_service_instance is None:
        _sync_service_instance = SyncService(
            snapshot_service=snapshot_service,
            instance_service=instance_service,
        )

    return _sync_service_instance


def get_job_manager(
    request: Request,
    user_email: str = Depends(get_current_user_email),
):
    """Get job manager service"""
    from ...services.job import JobManager
    import logging
    logger = logging.getLogger(__name__)

    settings = get_settings()

    # Check for demo mode (from env or query param)
    demo_param = request.query_params.get("demo", "").lower() == "true"
    is_demo = settings.app.demo_mode or demo_param
    logger.info(f"get_job_manager: demo_param={demo_param}, is_demo={is_demo}")

    # In demo mode, use demo provider
    if is_demo:
        logger.info("Using demo mode for JobManager")
        return JobManager(vast_api_key="demo", demo_mode=True)

    # Get user's vast API key, fallback to env var
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    # Try user's key first, then fall back to system key from .env
    api_key = (user.vast_api_key if user else None) or settings.vast.api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured. Please update settings.",
        )

    return JobManager(vast_api_key=api_key)
