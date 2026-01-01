"""
Permission constants for Role-Based Access Control (RBAC).

These constants should be used throughout the codebase instead of hardcoded
permission strings to ensure consistency and prevent typos.

Usage:
    from src.core.permissions import GPU_PROVISION, COST_VIEW

    @app.get("/instances")
    async def list_instances(user = Depends(require_permission(GPU_VIEW))):
        ...
"""

# GPU Permissions
GPU_PROVISION = "gpu.provision"
GPU_DELETE = "gpu.delete"
GPU_VIEW = "gpu.view"

# Cost Permissions
COST_VIEW = "cost.view"
COST_VIEW_OWN = "cost.view_own"
COST_EXPORT = "cost.export"

# Team Management Permissions
TEAM_INVITE = "team.invite"
TEAM_REMOVE = "team.remove"
TEAM_MANAGE = "team.manage"

# Settings Permissions
SETTINGS_VIEW = "settings.view"
SETTINGS_MANAGE = "settings.manage"

# Audit Permissions
AUDIT_VIEW = "audit.view"


# Permission groups for convenience
GPU_PERMISSIONS = [GPU_PROVISION, GPU_DELETE, GPU_VIEW]
COST_PERMISSIONS = [COST_VIEW, COST_VIEW_OWN, COST_EXPORT]
TEAM_PERMISSIONS = [TEAM_INVITE, TEAM_REMOVE, TEAM_MANAGE]
SETTINGS_PERMISSIONS = [SETTINGS_VIEW, SETTINGS_MANAGE]
AUDIT_PERMISSIONS = [AUDIT_VIEW]

# All permissions list
ALL_PERMISSIONS = (
    GPU_PERMISSIONS +
    COST_PERMISSIONS +
    TEAM_PERMISSIONS +
    SETTINGS_PERMISSIONS +
    AUDIT_PERMISSIONS
)

# Permission categories mapping
PERMISSION_CATEGORIES = {
    "gpu": GPU_PERMISSIONS,
    "cost": COST_PERMISSIONS,
    "team": TEAM_PERMISSIONS,
    "settings": SETTINGS_PERMISSIONS,
    "audit": AUDIT_PERMISSIONS,
}

# Predefined role permission sets (mirrors ROLE_PERMISSIONS in src/models/rbac.py)
ADMIN_PERMISSIONS = ALL_PERMISSIONS.copy()
DEVELOPER_PERMISSIONS = [GPU_PROVISION, GPU_VIEW, COST_VIEW_OWN]
VIEWER_PERMISSIONS = [GPU_VIEW, COST_VIEW_OWN]

ROLE_PERMISSION_SETS = {
    "admin": ADMIN_PERMISSIONS,
    "developer": DEVELOPER_PERMISSIONS,
    "viewer": VIEWER_PERMISSIONS,
}
