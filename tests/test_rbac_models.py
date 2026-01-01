"""
Tests for RBAC Database Models

Tests for SQLAlchemy models for Team, Role, Permission, TeamMember,
TeamInvitation, TeamQuota, and AuditLog.
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models.rbac import (
    Team,
    Role,
    Permission,
    TeamMember,
    TeamInvitation,
    TeamQuota,
    AuditLog,
    SYSTEM_ROLES,
    PERMISSIONS,
    ROLE_PERMISSIONS,
    AUDIT_ACTIONS,
    set_audit_context,
    get_audit_context,
    clear_audit_context,
)


class TestTeamModel:
    """Tests for Team model"""

    def test_team_creation(self):
        """Verify team can be created with required fields"""
        team = Team(
            name="Test Team",
            slug="test-team",
            owner_user_id="user123",
            description="A test team",
        )

        assert team.name == "Test Team"
        assert team.slug == "test-team"
        assert team.owner_user_id == "user123"
        assert team.description == "A test team"

    def test_team_default_values(self):
        """Verify default values are set correctly"""
        team = Team(
            name="Test Team",
            slug="test-team",
            owner_user_id="user123",
        )

        # is_active defaults to True via Column default
        assert Team.is_active.default.arg == True
        assert team.deleted_at is None

    def test_team_to_dict(self):
        """Verify to_dict method returns correct structure"""
        now = datetime.utcnow()
        team = Team(
            id=1,
            name="Test Team",
            slug="test-team",
            owner_user_id="user123",
            description="A test team",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        result = team.to_dict()

        assert result['id'] == 1
        assert result['name'] == "Test Team"
        assert result['slug'] == "test-team"
        assert result['owner_user_id'] == "user123"
        assert result['description'] == "A test team"
        assert result['is_active'] == True
        assert result['created_at'] == now.isoformat()
        assert result['updated_at'] == now.isoformat()

    def test_team_repr(self):
        """Verify __repr__ method"""
        team = Team(id=1, name="Test Team", slug="test-team")
        assert "id=1" in repr(team)
        assert "name=Test Team" in repr(team)
        assert "slug=test-team" in repr(team)


class TestRoleModel:
    """Tests for Role model"""

    def test_role_creation(self):
        """Verify role can be created with required fields"""
        role = Role(
            name="admin",
            display_name="Admin",
            description="Full control",
            is_system=True,
        )

        assert role.name == "admin"
        assert role.display_name == "Admin"
        assert role.description == "Full control"
        assert role.is_system == True

    def test_role_custom_team(self):
        """Verify custom team role fields"""
        role = Role(
            name="custom-developer",
            display_name="Custom Developer",
            description="Custom role for team",
            is_system=False,
            team_id=1,
        )

        assert role.is_system == False
        assert role.team_id == 1

    def test_role_default_values(self):
        """Verify default values are set correctly"""
        # Default is_system is False via Column default
        assert Role.is_system.default.arg == False

    def test_role_to_dict_basic(self):
        """Verify to_dict method returns correct structure"""
        now = datetime.utcnow()
        role = Role(
            id=1,
            name="admin",
            display_name="Admin",
            description="Full control",
            is_system=True,
            team_id=None,
            created_at=now,
            updated_at=now,
        )

        result = role.to_dict()

        assert result['id'] == 1
        assert result['name'] == "admin"
        assert result['display_name'] == "Admin"
        assert result['description'] == "Full control"
        assert result['is_system'] == True
        assert result['team_id'] is None
        assert 'permissions' not in result

    def test_role_to_dict_with_permissions(self):
        """Verify to_dict with include_permissions=True"""
        role = Role(
            id=1,
            name="admin",
            display_name="Admin",
            description="Full control",
            is_system=True,
        )
        # Mock permissions list
        role.permissions = []

        result = role.to_dict(include_permissions=True)

        assert 'permissions' in result
        assert result['permissions'] == []

    def test_role_repr(self):
        """Verify __repr__ method"""
        role = Role(id=1, name="admin", is_system=True)
        assert "id=1" in repr(role)
        assert "name=admin" in repr(role)
        assert "is_system=True" in repr(role)


class TestPermissionModel:
    """Tests for Permission model"""

    def test_permission_creation(self):
        """Verify permission can be created with required fields"""
        permission = Permission(
            name="gpu.provision",
            display_name="Provision GPU",
            description="Create and provision GPU instances",
            category="gpu",
        )

        assert permission.name == "gpu.provision"
        assert permission.display_name == "Provision GPU"
        assert permission.description == "Create and provision GPU instances"
        assert permission.category == "gpu"

    def test_permission_to_dict(self):
        """Verify to_dict method returns correct structure"""
        permission = Permission(
            id=1,
            name="gpu.provision",
            display_name="Provision GPU",
            description="Create and provision GPU instances",
            category="gpu",
        )

        result = permission.to_dict()

        assert result['id'] == 1
        assert result['name'] == "gpu.provision"
        assert result['display_name'] == "Provision GPU"
        assert result['description'] == "Create and provision GPU instances"
        assert result['category'] == "gpu"

    def test_permission_repr(self):
        """Verify __repr__ method"""
        permission = Permission(id=1, name="gpu.provision")
        assert "id=1" in repr(permission)
        assert "name=gpu.provision" in repr(permission)


class TestTeamMemberModel:
    """Tests for TeamMember model"""

    def test_team_member_creation(self):
        """Verify team member can be created with required fields"""
        now = datetime.utcnow()
        member = TeamMember(
            user_id="user123",
            team_id=1,
            role_id=1,
            invited_by_user_id="admin123",
            invited_at=now,
            joined_at=now,
        )

        assert member.user_id == "user123"
        assert member.team_id == 1
        assert member.role_id == 1
        assert member.invited_by_user_id == "admin123"

    def test_team_member_default_values(self):
        """Verify default values are set correctly"""
        # is_active defaults to True via Column default
        assert TeamMember.is_active.default.arg == True

    def test_team_member_to_dict_basic(self):
        """Verify to_dict method returns correct structure"""
        now = datetime.utcnow()
        member = TeamMember(
            id=1,
            user_id="user123",
            team_id=1,
            role_id=1,
            invited_by_user_id="admin123",
            invited_at=now,
            joined_at=now,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        result = member.to_dict()

        assert result['id'] == 1
        assert result['user_id'] == "user123"
        assert result['team_id'] == 1
        assert result['role_id'] == 1
        assert result['invited_by_user_id'] == "admin123"
        assert result['is_active'] == True
        assert 'role' not in result

    def test_team_member_to_dict_with_role(self):
        """Verify to_dict with include_role=True"""
        now = datetime.utcnow()
        member = TeamMember(
            id=1,
            user_id="user123",
            team_id=1,
            role_id=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        # Mock role
        member.role = Role(id=1, name="admin", display_name="Admin", is_system=True)

        result = member.to_dict(include_role=True)

        assert 'role' in result
        assert result['role']['name'] == "admin"

    def test_team_member_repr(self):
        """Verify __repr__ method"""
        member = TeamMember(id=1, user_id="user123", team_id=1, role_id=1)
        assert "id=1" in repr(member)
        assert "user_id=user123" in repr(member)
        assert "team_id=1" in repr(member)
        assert "role_id=1" in repr(member)


class TestTeamInvitationModel:
    """Tests for TeamInvitation model"""

    def test_invitation_creation(self):
        """Verify invitation can be created with required fields"""
        expires = datetime.utcnow() + timedelta(days=7)
        invitation = TeamInvitation(
            team_id=1,
            email="newuser@test.com",
            role_id=2,
            invited_by_user_id="admin123",
            token="abc123xyz",
            expires_at=expires,
            status='pending',
        )

        assert invitation.team_id == 1
        assert invitation.email == "newuser@test.com"
        assert invitation.role_id == 2
        assert invitation.invited_by_user_id == "admin123"
        assert invitation.token == "abc123xyz"
        assert invitation.status == 'pending'

    def test_invitation_default_status(self):
        """Verify default status is 'pending'"""
        assert TeamInvitation.status.default.arg == 'pending'

    def test_invitation_to_dict_basic(self):
        """Verify to_dict method returns correct structure"""
        now = datetime.utcnow()
        expires = now + timedelta(days=7)
        invitation = TeamInvitation(
            id=1,
            team_id=1,
            email="newuser@test.com",
            role_id=2,
            invited_by_user_id="admin123",
            token="abc123xyz",
            expires_at=expires,
            status='pending',
            created_at=now,
            updated_at=now,
        )

        result = invitation.to_dict()

        assert result['id'] == 1
        assert result['team_id'] == 1
        assert result['email'] == "newuser@test.com"
        assert result['role_id'] == 2
        assert result['status'] == 'pending'
        assert 'role' not in result

    def test_invitation_to_dict_with_role(self):
        """Verify to_dict with include_role=True"""
        now = datetime.utcnow()
        expires = now + timedelta(days=7)
        invitation = TeamInvitation(
            id=1,
            team_id=1,
            email="newuser@test.com",
            role_id=2,
            invited_by_user_id="admin123",
            token="abc123xyz",
            expires_at=expires,
            status='pending',
            created_at=now,
            updated_at=now,
        )
        # Mock role
        invitation.role = Role(id=2, name="developer", display_name="Developer", is_system=True)

        result = invitation.to_dict(include_role=True)

        assert 'role' in result
        assert result['role']['name'] == "developer"

    def test_invitation_repr(self):
        """Verify __repr__ method"""
        invitation = TeamInvitation(id=1, email="test@test.com", team_id=1, status='pending')
        assert "id=1" in repr(invitation)
        assert "email=test@test.com" in repr(invitation)
        assert "team_id=1" in repr(invitation)
        assert "status=pending" in repr(invitation)


class TestTeamQuotaModel:
    """Tests for TeamQuota model"""

    def test_quota_creation(self):
        """Verify quota can be created with required fields"""
        quota = TeamQuota(
            team_id=1,
            max_gpu_hours_per_month=100.0,
            max_concurrent_instances=5,
            max_monthly_budget_usd=500.0,
        )

        assert quota.team_id == 1
        assert quota.max_gpu_hours_per_month == 100.0
        assert quota.max_concurrent_instances == 5
        assert quota.max_monthly_budget_usd == 500.0

    def test_quota_default_values(self):
        """Verify default values are set correctly"""
        assert TeamQuota.current_gpu_hours_used.default.arg == 0.0
        assert TeamQuota.current_concurrent_instances.default.arg == 0
        assert TeamQuota.current_monthly_spend_usd.default.arg == 0.0
        assert TeamQuota.warn_at_gpu_hours_percent.default.arg == 80.0
        assert TeamQuota.warn_at_budget_percent.default.arg == 80.0
        assert TeamQuota.notify_on_warning.default.arg == True
        assert TeamQuota.notify_on_limit_reached.default.arg == True

    def test_quota_is_gpu_hours_exceeded_not_exceeded(self):
        """Verify is_gpu_hours_exceeded returns False when under limit"""
        quota = TeamQuota(
            team_id=1,
            max_gpu_hours_per_month=100.0,
            current_gpu_hours_used=50.0,
        )

        assert quota.is_gpu_hours_exceeded() == False

    def test_quota_is_gpu_hours_exceeded_exceeded(self):
        """Verify is_gpu_hours_exceeded returns True when over limit"""
        quota = TeamQuota(
            team_id=1,
            max_gpu_hours_per_month=100.0,
            current_gpu_hours_used=100.0,
        )

        assert quota.is_gpu_hours_exceeded() == True

    def test_quota_is_gpu_hours_exceeded_unlimited(self):
        """Verify is_gpu_hours_exceeded returns False when unlimited"""
        quota = TeamQuota(
            team_id=1,
            max_gpu_hours_per_month=None,
            current_gpu_hours_used=1000.0,
        )

        assert quota.is_gpu_hours_exceeded() == False

    def test_quota_is_concurrent_instances_exceeded(self):
        """Verify is_concurrent_instances_exceeded"""
        quota = TeamQuota(
            team_id=1,
            max_concurrent_instances=5,
            current_concurrent_instances=5,
        )

        assert quota.is_concurrent_instances_exceeded() == True

    def test_quota_is_budget_exceeded(self):
        """Verify is_budget_exceeded"""
        quota = TeamQuota(
            team_id=1,
            max_monthly_budget_usd=500.0,
            current_monthly_spend_usd=600.0,
        )

        assert quota.is_budget_exceeded() == True

    def test_quota_is_any_quota_exceeded(self):
        """Verify is_any_quota_exceeded"""
        quota = TeamQuota(
            team_id=1,
            max_gpu_hours_per_month=100.0,
            current_gpu_hours_used=50.0,
            max_concurrent_instances=5,
            current_concurrent_instances=3,
            max_monthly_budget_usd=500.0,
            current_monthly_spend_usd=600.0,  # Exceeded
        )

        assert quota.is_any_quota_exceeded() == True

    def test_quota_get_gpu_hours_percent_used(self):
        """Verify get_gpu_hours_percent_used"""
        quota = TeamQuota(
            team_id=1,
            max_gpu_hours_per_month=100.0,
            current_gpu_hours_used=50.0,
        )

        assert quota.get_gpu_hours_percent_used() == 50.0

    def test_quota_get_gpu_hours_percent_used_unlimited(self):
        """Verify get_gpu_hours_percent_used returns 0 when unlimited"""
        quota = TeamQuota(
            team_id=1,
            max_gpu_hours_per_month=None,
            current_gpu_hours_used=50.0,
        )

        assert quota.get_gpu_hours_percent_used() == 0.0

    def test_quota_get_budget_percent_used(self):
        """Verify get_budget_percent_used"""
        quota = TeamQuota(
            team_id=1,
            max_monthly_budget_usd=500.0,
            current_monthly_spend_usd=250.0,
        )

        assert quota.get_budget_percent_used() == 50.0

    def test_quota_should_warn_gpu_hours(self):
        """Verify should_warn_gpu_hours"""
        quota = TeamQuota(
            team_id=1,
            max_gpu_hours_per_month=100.0,
            current_gpu_hours_used=85.0,
            warn_at_gpu_hours_percent=80.0,
        )

        assert quota.should_warn_gpu_hours() == True

    def test_quota_should_warn_budget(self):
        """Verify should_warn_budget"""
        quota = TeamQuota(
            team_id=1,
            max_monthly_budget_usd=500.0,
            current_monthly_spend_usd=400.0,
            warn_at_budget_percent=80.0,
        )

        assert quota.should_warn_budget() == True

    def test_quota_to_dict(self):
        """Verify to_dict method returns correct structure"""
        now = datetime.utcnow()
        quota = TeamQuota(
            id=1,
            team_id=1,
            max_gpu_hours_per_month=100.0,
            max_concurrent_instances=5,
            max_monthly_budget_usd=500.0,
            current_gpu_hours_used=50.0,
            current_concurrent_instances=2,
            current_monthly_spend_usd=200.0,
            warn_at_gpu_hours_percent=80.0,
            warn_at_budget_percent=80.0,
            notify_on_warning=True,
            notify_on_limit_reached=True,
            created_at=now,
            updated_at=now,
        )

        result = quota.to_dict()

        assert result['id'] == 1
        assert result['team_id'] == 1
        assert result['limits']['max_gpu_hours_per_month'] == 100.0
        assert result['limits']['max_concurrent_instances'] == 5
        assert result['limits']['max_monthly_budget_usd'] == 500.0
        assert result['usage']['gpu_hours_used'] == 50.0
        assert result['usage']['concurrent_instances'] == 2
        assert result['usage']['monthly_spend_usd'] == 200.0
        assert result['warnings']['warn_at_gpu_hours_percent'] == 80.0
        assert result['notifications']['notify_on_warning'] == True

    def test_quota_repr(self):
        """Verify __repr__ method"""
        quota = TeamQuota(
            id=1,
            team_id=1,
            max_gpu_hours_per_month=100.0,
            current_gpu_hours_used=50.0,
        )
        assert "id=1" in repr(quota)
        assert "team_id=1" in repr(quota)


class TestAuditLogModel:
    """Tests for AuditLog model"""

    def test_audit_log_creation(self):
        """Verify audit log can be created with required fields"""
        log = AuditLog(
            user_id="user123",
            team_id=1,
            action="member.added",
            resource_type="team_member",
            resource_id="42",
            status='success',
        )

        assert log.user_id == "user123"
        assert log.team_id == 1
        assert log.action == "member.added"
        assert log.resource_type == "team_member"
        assert log.resource_id == "42"
        assert log.status == 'success'

    def test_audit_log_default_status(self):
        """Verify default status is 'success'"""
        assert AuditLog.status.default.arg == 'success'

    def test_audit_log_to_dict(self):
        """Verify to_dict method returns correct structure"""
        now = datetime.utcnow()
        log = AuditLog(
            id=1,
            user_id="user123",
            team_id=1,
            action="member.added",
            resource_type="team_member",
            resource_id="42",
            details='{"key": "value"}',
            old_value=None,
            new_value='{"user_id": "user456"}',
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            status='success',
            error_message=None,
            created_at=now,
        )

        result = log.to_dict()

        assert result['id'] == 1
        assert result['user_id'] == "user123"
        assert result['team_id'] == 1
        assert result['action'] == "member.added"
        assert result['resource_type'] == "team_member"
        assert result['resource_id'] == "42"
        assert result['ip_address'] == "192.168.1.1"
        assert result['status'] == 'success'

    def test_audit_log_repr(self):
        """Verify __repr__ method"""
        log = AuditLog(id=1, user_id="user123", action="member.added", resource_type="team_member")
        assert "id=1" in repr(log)
        assert "user_id=user123" in repr(log)
        assert "action=member.added" in repr(log)


class TestSystemRolesConstants:
    """Tests for SYSTEM_ROLES constant"""

    def test_admin_role_defined(self):
        """Verify admin role is defined"""
        assert 'admin' in SYSTEM_ROLES
        assert SYSTEM_ROLES['admin']['name'] == 'admin'
        assert SYSTEM_ROLES['admin']['display_name'] == 'Admin'

    def test_developer_role_defined(self):
        """Verify developer role is defined"""
        assert 'developer' in SYSTEM_ROLES
        assert SYSTEM_ROLES['developer']['name'] == 'developer'
        assert SYSTEM_ROLES['developer']['display_name'] == 'Developer'

    def test_viewer_role_defined(self):
        """Verify viewer role is defined"""
        assert 'viewer' in SYSTEM_ROLES
        assert SYSTEM_ROLES['viewer']['name'] == 'viewer'
        assert SYSTEM_ROLES['viewer']['display_name'] == 'Viewer'


class TestPermissionsConstants:
    """Tests for PERMISSIONS constant"""

    def test_gpu_permissions_defined(self):
        """Verify GPU permissions are defined"""
        assert 'gpu.provision' in PERMISSIONS
        assert 'gpu.delete' in PERMISSIONS
        assert 'gpu.view' in PERMISSIONS

    def test_cost_permissions_defined(self):
        """Verify cost permissions are defined"""
        assert 'cost.view' in PERMISSIONS
        assert 'cost.view_own' in PERMISSIONS
        assert 'cost.export' in PERMISSIONS

    def test_team_permissions_defined(self):
        """Verify team permissions are defined"""
        assert 'team.invite' in PERMISSIONS
        assert 'team.remove' in PERMISSIONS
        assert 'team.manage' in PERMISSIONS

    def test_settings_permissions_defined(self):
        """Verify settings permissions are defined"""
        assert 'settings.view' in PERMISSIONS
        assert 'settings.manage' in PERMISSIONS

    def test_audit_permissions_defined(self):
        """Verify audit permissions are defined"""
        assert 'audit.view' in PERMISSIONS

    def test_permission_structure(self):
        """Verify permission structure contains required fields"""
        for name, perm in PERMISSIONS.items():
            assert 'display_name' in perm, f"Permission {name} missing display_name"
            assert 'description' in perm, f"Permission {name} missing description"
            assert 'category' in perm, f"Permission {name} missing category"


class TestRolePermissionsConstants:
    """Tests for ROLE_PERMISSIONS constant"""

    def test_admin_has_all_permissions(self):
        """Verify admin role has all permissions"""
        admin_perms = ROLE_PERMISSIONS['admin']
        assert 'gpu.provision' in admin_perms
        assert 'gpu.delete' in admin_perms
        assert 'cost.view' in admin_perms
        assert 'team.manage' in admin_perms
        assert 'settings.manage' in admin_perms
        assert 'audit.view' in admin_perms

    def test_developer_permissions(self):
        """Verify developer role has correct permissions"""
        dev_perms = ROLE_PERMISSIONS['developer']
        assert 'gpu.provision' in dev_perms
        assert 'gpu.view' in dev_perms
        assert 'cost.view_own' in dev_perms
        # Developer should not have admin permissions
        assert 'team.manage' not in dev_perms
        assert 'gpu.delete' not in dev_perms

    def test_viewer_permissions(self):
        """Verify viewer role has minimal permissions"""
        viewer_perms = ROLE_PERMISSIONS['viewer']
        assert 'gpu.view' in viewer_perms
        assert 'cost.view_own' in viewer_perms
        # Viewer should not have write permissions
        assert 'gpu.provision' not in viewer_perms
        assert 'gpu.delete' not in viewer_perms
        assert 'team.invite' not in viewer_perms


class TestAuditActionsConstants:
    """Tests for AUDIT_ACTIONS constant"""

    def test_member_actions_defined(self):
        """Verify member actions are defined"""
        assert 'member.added' in AUDIT_ACTIONS
        assert 'member.removed' in AUDIT_ACTIONS
        assert 'member.role_changed' in AUDIT_ACTIONS

    def test_role_actions_defined(self):
        """Verify role actions are defined"""
        assert 'role.created' in AUDIT_ACTIONS
        assert 'role.updated' in AUDIT_ACTIONS
        assert 'role.deleted' in AUDIT_ACTIONS

    def test_gpu_actions_defined(self):
        """Verify GPU actions are defined"""
        assert 'gpu.provisioned' in AUDIT_ACTIONS
        assert 'gpu.deleted' in AUDIT_ACTIONS
        assert 'gpu.hibernated' in AUDIT_ACTIONS
        assert 'gpu.woke' in AUDIT_ACTIONS

    def test_team_actions_defined(self):
        """Verify team actions are defined"""
        assert 'team.created' in AUDIT_ACTIONS
        assert 'team.updated' in AUDIT_ACTIONS
        assert 'team.deleted' in AUDIT_ACTIONS

    def test_invitation_actions_defined(self):
        """Verify invitation actions are defined"""
        assert 'invitation.sent' in AUDIT_ACTIONS
        assert 'invitation.accepted' in AUDIT_ACTIONS
        assert 'invitation.revoked' in AUDIT_ACTIONS
        assert 'invitation.expired' in AUDIT_ACTIONS

    def test_quota_actions_defined(self):
        """Verify quota actions are defined"""
        assert 'quota.updated' in AUDIT_ACTIONS
        assert 'quota.exceeded' in AUDIT_ACTIONS


class TestAuditContext:
    """Tests for audit context functions"""

    def test_set_and_get_audit_context(self):
        """Verify set_audit_context and get_audit_context work"""
        set_audit_context(
            user_id="user123",
            team_id=1,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        ctx = get_audit_context()

        assert ctx is not None
        assert ctx['user_id'] == "user123"
        assert ctx['team_id'] == 1
        assert ctx['ip_address'] == "192.168.1.1"
        assert ctx['user_agent'] == "Mozilla/5.0"

        # Clean up
        clear_audit_context()

    def test_clear_audit_context(self):
        """Verify clear_audit_context works"""
        set_audit_context(user_id="user123")
        clear_audit_context()

        ctx = get_audit_context()
        assert ctx is None

    def test_audit_context_without_optional_fields(self):
        """Verify audit context works with minimal fields"""
        set_audit_context(user_id="user123")

        ctx = get_audit_context()

        assert ctx is not None
        assert ctx['user_id'] == "user123"
        assert ctx['team_id'] is None
        assert ctx['ip_address'] is None

        clear_audit_context()
