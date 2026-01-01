"""
Integration Tests for RBAC API Endpoints

Tests for the RBAC API endpoints including:
- Team CRUD operations
- Member management (invite → accept → assign role → remove)
- Role management (list, create custom, delete)
- Permission enforcement (403 responses)
- Quota management
- Audit log verification

These tests use FastAPI TestClient with database fixtures.
Requires a running PostgreSQL database.

Run with: pytest tests/test_rbac_api_integration.py -v
"""

import pytest
from datetime import datetime, timedelta
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from fastapi.testclient import TestClient

# Mark all tests in this module as integration tests requiring database
pytestmark = [pytest.mark.integration]


def _check_database_connection():
    """Check if database connection is available"""
    try:
        from src.config.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# Skip all tests if database is not available
if not _check_database_connection():
    pytest.skip("Database connection not available", allow_module_level=True)


from src.config.database import engine, SessionLocal, get_db
from src.infrastructure.providers.team_repository import SQLAlchemyTeamRepository
from src.infrastructure.providers.role_repository import SQLAlchemyRoleRepository
from src.models.rbac import Team, TeamMember, TeamInvitation, TeamQuota, Role, Permission, AuditLog
from src.core.jwt import create_access_token
from src.core.permissions import (
    GPU_PROVISION,
    GPU_VIEW,
    TEAM_MANAGE,
    TEAM_INVITE,
    TEAM_REMOVE,
    AUDIT_VIEW,
)


# Import the FastAPI app from src.main
from src.main import create_app


@pytest.fixture(scope="module")
def app():
    """Create FastAPI application"""
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    """Create test client"""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="function")
def db_session():
    """Create database session for tests"""
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def team_repo(db_session):
    """Create team repository for tests"""
    return SQLAlchemyTeamRepository(db_session)


@pytest.fixture
def role_repo(db_session):
    """Create role repository for tests"""
    return SQLAlchemyRoleRepository(db_session)


@pytest.fixture
def unique_id():
    """Generate unique ID for test isolation"""
    return uuid.uuid4().hex[:8]


@pytest.fixture
def admin_role(db_session):
    """Get or create admin role for tests"""
    role = db_session.query(Role).filter(
        Role.name == 'admin',
        Role.is_system == True
    ).first()

    if not role:
        role = Role(
            name='admin',
            display_name='Admin',
            description='Full control',
            is_system=True
        )
        db_session.add(role)
        db_session.flush()

    return role


@pytest.fixture
def developer_role(db_session):
    """Get or create developer role for tests"""
    role = db_session.query(Role).filter(
        Role.name == 'developer',
        Role.is_system == True
    ).first()

    if not role:
        role = Role(
            name='developer',
            display_name='Developer',
            description='Can provision GPUs',
            is_system=True
        )
        db_session.add(role)
        db_session.flush()

    return role


@pytest.fixture
def viewer_role(db_session):
    """Get or create viewer role for tests"""
    role = db_session.query(Role).filter(
        Role.name == 'viewer',
        Role.is_system == True
    ).first()

    if not role:
        role = Role(
            name='viewer',
            display_name='Viewer',
            description='Read-only access',
            is_system=True
        )
        db_session.add(role)
        db_session.flush()

    return role


def create_auth_token(
    email: str,
    team_id: int = None,
    role: str = None,
    permissions: list = None,
) -> str:
    """Create an auth token for testing"""
    return create_access_token(
        email=email,
        team_id=team_id,
        role=role,
        permissions=permissions,
    )


def auth_headers(token: str) -> dict:
    """Create authorization headers"""
    return {"Authorization": f"Bearer {token}"}


class TestTeamCRUDAPI:
    """Tests for Team CRUD API endpoints"""

    def test_create_team(self, client, unique_id, db_session):
        """POST /api/v1/teams - Should create team successfully"""
        email = f"owner_{unique_id}@test.com"
        token = create_auth_token(email)

        response = client.post(
            "/api/v1/teams",
            json={"name": f"Test Team {unique_id}", "description": "A test team"},
            headers=auth_headers(token),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == f"Test Team {unique_id}"
        assert data["owner_user_id"] == email
        assert data["is_active"] == True
        assert data["member_count"] == 1

    def test_create_team_unauthenticated(self, client):
        """POST /api/v1/teams - Should fail without authentication"""
        response = client.post(
            "/api/v1/teams",
            json={"name": "Unauthorized Team"},
        )

        assert response.status_code == 401

    def test_list_teams(self, client, team_repo, admin_role, unique_id, db_session):
        """GET /api/v1/teams - Should list user's teams"""
        email = f"list_user_{unique_id}@test.com"

        # Create a team and add user as member
        team = team_repo.create_team(
            name=f"List Teams {unique_id}",
            slug=f"list-teams-{unique_id}",
            owner_user_id=email,
        )
        team_repo.add_member(team.id, email, admin_role.id)
        db_session.commit()

        token = create_auth_token(email, team_id=team.id)

        response = client.get(
            "/api/v1/teams",
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "teams" in data
        assert data["count"] >= 1

    def test_get_team_details(self, client, team_repo, admin_role, unique_id, db_session):
        """GET /api/v1/teams/{team_id} - Should return team details"""
        email = f"detail_user_{unique_id}@test.com"

        # Create team and add user
        team = team_repo.create_team(
            name=f"Detail Team {unique_id}",
            slug=f"detail-team-{unique_id}",
            owner_user_id=email,
        )
        team_repo.add_member(team.id, email, admin_role.id)
        db_session.commit()

        token = create_auth_token(email, team_id=team.id, role="admin")

        response = client.get(
            f"/api/v1/teams/{team.id}",
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == team.id
        assert data["name"] == f"Detail Team {unique_id}"
        assert "members" in data
        assert len(data["members"]) >= 1

    def test_get_team_not_member(self, client, team_repo, unique_id, db_session):
        """GET /api/v1/teams/{team_id} - Should return 403 for non-member"""
        owner_email = f"owner_{unique_id}@test.com"
        other_email = f"other_{unique_id}@test.com"

        # Create team
        team = team_repo.create_team(
            name=f"Private Team {unique_id}",
            slug=f"private-team-{unique_id}",
            owner_user_id=owner_email,
        )
        db_session.commit()

        # Try to access with non-member
        token = create_auth_token(other_email)

        response = client.get(
            f"/api/v1/teams/{team.id}",
            headers=auth_headers(token),
        )

        assert response.status_code == 403

    def test_update_team(self, client, team_repo, admin_role, unique_id, db_session):
        """PUT /api/v1/teams/{team_id} - Should update team with team.manage permission"""
        email = f"update_user_{unique_id}@test.com"

        # Create team and add user
        team = team_repo.create_team(
            name=f"Update Team {unique_id}",
            slug=f"update-team-{unique_id}",
            owner_user_id=email,
        )
        team_repo.add_member(team.id, email, admin_role.id)
        db_session.commit()

        # Create token with team.manage permission
        token = create_auth_token(
            email,
            team_id=team.id,
            role="admin",
            permissions=[TEAM_MANAGE],
        )

        response = client.put(
            f"/api/v1/teams/{team.id}",
            json={"description": "Updated description"},
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    def test_update_team_without_permission(self, client, team_repo, viewer_role, unique_id, db_session):
        """PUT /api/v1/teams/{team_id} - Should return 403 without team.manage permission"""
        email = f"viewer_{unique_id}@test.com"

        # Create team and add user as viewer
        team = team_repo.create_team(
            name=f"Viewer Team {unique_id}",
            slug=f"viewer-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}@test.com",
        )
        team_repo.add_member(team.id, email, viewer_role.id)
        db_session.commit()

        # Create token without team.manage permission
        token = create_auth_token(
            email,
            team_id=team.id,
            role="viewer",
            permissions=[GPU_VIEW],  # Viewer only has view permissions
        )

        response = client.put(
            f"/api/v1/teams/{team.id}",
            json={"description": "Should fail"},
            headers=auth_headers(token),
        )

        assert response.status_code == 403

    def test_delete_team_owner_only(self, client, team_repo, admin_role, unique_id, db_session):
        """DELETE /api/v1/teams/{team_id} - Only owner can delete"""
        owner_email = f"owner_{unique_id}@test.com"
        admin_email = f"admin_{unique_id}@test.com"

        # Create team
        team = team_repo.create_team(
            name=f"Delete Team {unique_id}",
            slug=f"delete-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        team_repo.add_member(team.id, admin_email, admin_role.id)
        db_session.commit()

        # Non-owner admin should fail
        admin_token = create_auth_token(
            admin_email,
            team_id=team.id,
            role="admin",
            permissions=[TEAM_MANAGE],
        )

        response = client.delete(
            f"/api/v1/teams/{team.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 403

        # Owner should succeed
        owner_token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[TEAM_MANAGE],
        )

        response = client.delete(
            f"/api/v1/teams/{team.id}",
            headers=auth_headers(owner_token),
        )

        assert response.status_code == 204


class TestMemberManagementAPI:
    """Tests for Team Member Management API endpoints"""

    def test_invite_member_flow(self, client, team_repo, admin_role, unique_id, db_session):
        """POST /api/v1/teams/{id}/invitations - Should create invitation"""
        owner_email = f"owner_{unique_id}@test.com"
        invitee_email = f"invitee_{unique_id}@test.com"

        # Create team and add owner
        team = team_repo.create_team(
            name=f"Invite Team {unique_id}",
            slug=f"invite-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        db_session.commit()

        # Create token with team.invite permission
        token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[TEAM_INVITE],
        )

        response = client.post(
            f"/api/v1/teams/{team.id}/invitations",
            json={"email": invitee_email, "role_id": admin_role.id},
            headers=auth_headers(token),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == invitee_email
        assert data["status"] == "pending"
        assert "token" in data
        assert data["expires_at"] is not None

    def test_accept_invitation_flow(self, client, team_repo, admin_role, unique_id, db_session):
        """POST /api/v1/teams/{id}/invitations/{token}/accept - Should accept invitation"""
        owner_email = f"owner_{unique_id}@test.com"
        invitee_email = f"accepter_{unique_id}@test.com"

        # Create team and add owner
        team = team_repo.create_team(
            name=f"Accept Team {unique_id}",
            slug=f"accept-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)

        # Create invitation
        invitation_token = f"accept_token_{unique_id}"
        invitation = team_repo.create_invitation(
            team_id=team.id,
            email=invitee_email,
            role_id=admin_role.id,
            invited_by_user_id=owner_email,
            token=invitation_token,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.commit()

        # Accept invitation (as invitee)
        invitee_token = create_auth_token(invitee_email)

        response = client.post(
            f"/api/v1/teams/{team.id}/invitations/{invitation_token}/accept",
            headers=auth_headers(invitee_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == invitee_email
        assert data["team_id"] == team.id
        assert data["is_active"] == True

    def test_list_team_members(self, client, team_repo, admin_role, unique_id, db_session):
        """GET /api/v1/teams/{id}/members - Should list team members"""
        owner_email = f"owner_{unique_id}@test.com"
        member_email = f"member_{unique_id}@test.com"

        # Create team with multiple members
        team = team_repo.create_team(
            name=f"Members Team {unique_id}",
            slug=f"members-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        team_repo.add_member(team.id, member_email, admin_role.id)
        db_session.commit()

        token = create_auth_token(owner_email, team_id=team.id)

        response = client.get(
            f"/api/v1/teams/{team.id}/members",
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 2
        assert len(data["members"]) >= 2

    def test_update_member_role(self, client, team_repo, admin_role, developer_role, unique_id, db_session):
        """PUT /api/v1/teams/{id}/members/{user_id}/role - Should update member role"""
        owner_email = f"owner_{unique_id}@test.com"
        member_email = f"member_{unique_id}@test.com"

        # Create team with members
        team = team_repo.create_team(
            name=f"Role Update Team {unique_id}",
            slug=f"role-update-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        team_repo.add_member(team.id, member_email, admin_role.id)
        db_session.commit()

        token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[TEAM_MANAGE],
        )

        response = client.put(
            f"/api/v1/teams/{team.id}/members/{member_email}/role",
            json={"role_id": developer_role.id},
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role_id"] == developer_role.id

    def test_prevent_demoting_last_admin(self, client, team_repo, admin_role, developer_role, unique_id, db_session):
        """PUT /api/v1/teams/{id}/members/{user_id}/role - Should prevent demoting last admin"""
        owner_email = f"owner_{unique_id}@test.com"

        # Create team with single admin
        team = team_repo.create_team(
            name=f"Last Admin Team {unique_id}",
            slug=f"last-admin-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        db_session.commit()

        token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[TEAM_MANAGE],
        )

        # Try to demote self (last admin)
        response = client.put(
            f"/api/v1/teams/{team.id}/members/{owner_email}/role",
            json={"role_id": developer_role.id},
            headers=auth_headers(token),
        )

        assert response.status_code == 400
        assert "last admin" in response.json()["detail"].lower()

    def test_remove_member(self, client, team_repo, admin_role, unique_id, db_session):
        """DELETE /api/v1/teams/{id}/members/{user_id} - Should soft remove member"""
        owner_email = f"owner_{unique_id}@test.com"
        member_email = f"to_remove_{unique_id}@test.com"

        # Create team with members
        team = team_repo.create_team(
            name=f"Remove Member Team {unique_id}",
            slug=f"remove-member-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        team_repo.add_member(team.id, member_email, admin_role.id)
        db_session.commit()

        token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[TEAM_REMOVE],
        )

        response = client.delete(
            f"/api/v1/teams/{team.id}/members/{member_email}",
            headers=auth_headers(token),
        )

        assert response.status_code == 204

    def test_leave_team(self, client, team_repo, admin_role, developer_role, unique_id, db_session):
        """POST /api/v1/teams/{id}/leave - Should allow member to leave team"""
        owner_email = f"owner_{unique_id}@test.com"
        member_email = f"leaver_{unique_id}@test.com"

        # Create team with members
        team = team_repo.create_team(
            name=f"Leave Team {unique_id}",
            slug=f"leave-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        team_repo.add_member(team.id, member_email, developer_role.id)
        db_session.commit()

        token = create_auth_token(member_email, team_id=team.id)

        response = client.post(
            f"/api/v1/teams/{team.id}/leave",
            headers=auth_headers(token),
        )

        assert response.status_code == 204


class TestRoleManagementAPI:
    """Tests for Role Management API endpoints"""

    def test_list_permissions(self, client, unique_id):
        """GET /api/v1/permissions - Should list all permissions"""
        email = f"user_{unique_id}@test.com"
        token = create_auth_token(email)

        response = client.get(
            "/api/v1/permissions",
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "permissions" in data
        assert "categories" in data
        assert data["count"] > 0

    def test_list_system_roles(self, client, unique_id):
        """GET /api/v1/roles - Should list predefined system roles"""
        email = f"user_{unique_id}@test.com"
        token = create_auth_token(email)

        response = client.get(
            "/api/v1/roles",
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "roles" in data

        # Should have admin, developer, viewer
        role_names = [r["name"] for r in data["roles"]]
        assert "admin" in role_names
        assert "developer" in role_names
        assert "viewer" in role_names

    def test_get_role_details(self, client, admin_role, unique_id):
        """GET /api/v1/roles/{role_id} - Should return role with permissions"""
        email = f"user_{unique_id}@test.com"
        token = create_auth_token(email)

        response = client.get(
            f"/api/v1/roles/{admin_role.id}?include_permissions=true",
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "admin"
        assert data["is_system"] == True
        assert "permissions" in data

    def test_create_custom_role(self, client, team_repo, admin_role, role_repo, unique_id, db_session):
        """POST /api/v1/teams/{id}/roles - Should create custom role"""
        owner_email = f"owner_{unique_id}@test.com"

        # Create team
        team = team_repo.create_team(
            name=f"Custom Role Team {unique_id}",
            slug=f"custom-role-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        db_session.commit()

        # Get a permission ID
        permissions = role_repo.list_permissions()
        perm_ids = [p.id for p in permissions[:2]]

        token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[TEAM_MANAGE],
        )

        response = client.post(
            f"/api/v1/teams/{team.id}/roles",
            json={
                "name": f"custom-role-{unique_id}",
                "display_name": f"Custom Role {unique_id}",
                "description": "A custom role for testing",
                "permission_ids": perm_ids,
            },
            headers=auth_headers(token),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == f"custom-role-{unique_id}"
        assert data["is_system"] == False
        assert data["team_id"] == team.id
        assert len(data["permissions"]) == len(perm_ids)

    def test_delete_custom_role_blocked_with_members(self, client, team_repo, admin_role, role_repo, unique_id, db_session):
        """DELETE /api/v1/roles/{role_id} - Should block deletion if members assigned"""
        owner_email = f"owner_{unique_id}@test.com"
        member_email = f"member_{unique_id}@test.com"

        # Create team
        team = team_repo.create_team(
            name=f"Blocked Delete Team {unique_id}",
            slug=f"blocked-delete-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)

        # Create custom role
        custom_role = role_repo.create_role(
            name=f"blocked-role-{unique_id}",
            display_name=f"Blocked Role {unique_id}",
            description="Role that cannot be deleted",
            team_id=team.id,
            is_system=False,
        )

        # Assign member to custom role
        team_repo.add_member(team.id, member_email, custom_role.id)
        db_session.commit()

        token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[TEAM_MANAGE],
        )

        # Try to delete role with member assigned
        response = client.delete(
            f"/api/v1/roles/{custom_role.id}",
            headers=auth_headers(token),
        )

        assert response.status_code == 400
        assert "active members" in response.json()["detail"].lower()


class TestQuotaManagementAPI:
    """Tests for Team Quota Management API endpoints"""

    def test_get_team_quota(self, client, team_repo, admin_role, unique_id, db_session):
        """GET /api/v1/teams/{id}/quota - Should return team quota"""
        owner_email = f"owner_{unique_id}@test.com"

        # Create team with quota
        team = team_repo.create_team(
            name=f"Quota Team {unique_id}",
            slug=f"quota-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        team_repo.create_or_update_quota(
            team_id=team.id,
            max_gpu_hours_per_month=100.0,
            max_concurrent_instances=5,
            max_monthly_budget_usd=500.0,
        )
        db_session.commit()

        token = create_auth_token(owner_email, team_id=team.id)

        response = client.get(
            f"/api/v1/teams/{team.id}/quota",
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limits"]["max_gpu_hours_per_month"] == 100.0
        assert data["limits"]["max_concurrent_instances"] == 5
        assert data["limits"]["max_monthly_budget_usd"] == 500.0

    def test_update_team_quota(self, client, team_repo, admin_role, unique_id, db_session):
        """PUT /api/v1/teams/{id}/quota - Should update team quota"""
        owner_email = f"owner_{unique_id}@test.com"

        # Create team
        team = team_repo.create_team(
            name=f"Update Quota Team {unique_id}",
            slug=f"update-quota-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        db_session.commit()

        token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[TEAM_MANAGE],
        )

        response = client.put(
            f"/api/v1/teams/{team.id}/quota",
            json={
                "max_gpu_hours_per_month": 200.0,
                "max_concurrent_instances": 10,
            },
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limits"]["max_gpu_hours_per_month"] == 200.0
        assert data["limits"]["max_concurrent_instances"] == 10


class TestAuditLogAPI:
    """Tests for Audit Log API endpoints"""

    def test_get_audit_logs(self, client, team_repo, admin_role, unique_id, db_session):
        """GET /api/v1/teams/{id}/audit-logs - Should return audit logs"""
        owner_email = f"owner_{unique_id}@test.com"

        # Create team
        team = team_repo.create_team(
            name=f"Audit Team {unique_id}",
            slug=f"audit-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        db_session.commit()

        token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[AUDIT_VIEW],
        )

        response = client.get(
            f"/api/v1/teams/{team.id}/audit-logs",
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "count" in data
        assert "total" in data

    def test_audit_logs_require_permission(self, client, team_repo, viewer_role, unique_id, db_session):
        """GET /api/v1/teams/{id}/audit-logs - Should require audit.view permission"""
        viewer_email = f"viewer_{unique_id}@test.com"

        # Create team
        team = team_repo.create_team(
            name=f"Audit Perm Team {unique_id}",
            slug=f"audit-perm-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}@test.com",
        )
        team_repo.add_member(team.id, viewer_email, viewer_role.id)
        db_session.commit()

        # Token without audit.view permission
        token = create_auth_token(
            viewer_email,
            team_id=team.id,
            role="viewer",
            permissions=[GPU_VIEW],  # Viewer doesn't have audit.view
        )

        response = client.get(
            f"/api/v1/teams/{team.id}/audit-logs",
            headers=auth_headers(token),
        )

        assert response.status_code == 403


class TestPermissionEnforcement:
    """Tests for permission enforcement across API endpoints"""

    def test_no_team_context_returns_403(self, client, unique_id):
        """Protected endpoints should return 403 without team context"""
        email = f"no_team_{unique_id}@test.com"

        # Token without team_id
        token = create_auth_token(email)

        # Try to update a team (requires team.manage)
        response = client.put(
            "/api/v1/teams/1",
            json={"description": "Should fail"},
            headers=auth_headers(token),
        )

        assert response.status_code == 403
        assert "no team context" in response.json()["detail"].lower()

    def test_permission_denied_returns_403(self, client, team_repo, viewer_role, unique_id, db_session):
        """Endpoints should return 403 when user lacks required permission"""
        viewer_email = f"viewer_{unique_id}@test.com"

        # Create team and add viewer
        team = team_repo.create_team(
            name=f"Perm Denied Team {unique_id}",
            slug=f"perm-denied-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}@test.com",
        )
        team_repo.add_member(team.id, viewer_email, viewer_role.id)
        db_session.commit()

        # Create token with viewer permissions (no team.invite)
        token = create_auth_token(
            viewer_email,
            team_id=team.id,
            role="viewer",
            permissions=[GPU_VIEW],
        )

        # Try to invite member (requires team.invite)
        response = client.post(
            f"/api/v1/teams/{team.id}/invitations",
            json={"email": "newuser@test.com", "role_id": 1},
            headers=auth_headers(token),
        )

        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()


class TestCompleteRBACFlow:
    """Integration tests for complete RBAC workflows"""

    def test_full_team_member_crud_flow(self, client, team_repo, admin_role, developer_role, unique_id, db_session):
        """
        Complete flow: Create team → invite member → accept invitation →
        assign role → check permissions → verify audit log
        """
        admin_email = f"admin_{unique_id}@test.com"
        dev_email = f"dev_{unique_id}@test.com"

        # 1. Create team
        admin_token = create_auth_token(admin_email)
        response = client.post(
            "/api/v1/teams",
            json={"name": f"CRUD Flow Team {unique_id}"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 201
        team_id = response.json()["id"]

        # Refresh token with team context
        admin_token = create_auth_token(
            admin_email,
            team_id=team_id,
            role="admin",
            permissions=[TEAM_INVITE, TEAM_MANAGE, TEAM_REMOVE, AUDIT_VIEW],
        )

        # 2. Invite member
        response = client.post(
            f"/api/v1/teams/{team_id}/invitations",
            json={"email": dev_email, "role_id": developer_role.id},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 201
        invitation_token = response.json()["token"]

        # 3. Accept invitation
        dev_token = create_auth_token(dev_email)
        response = client.post(
            f"/api/v1/teams/{team_id}/invitations/{invitation_token}/accept",
            headers=auth_headers(dev_token),
        )
        assert response.status_code == 200

        # 4. Verify member appears in list
        response = client.get(
            f"/api/v1/teams/{team_id}/members",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        members = response.json()["members"]
        dev_member = next((m for m in members if m["user_id"] == dev_email), None)
        assert dev_member is not None
        assert dev_member["role_id"] == developer_role.id

        # 5. Update member role to admin
        response = client.put(
            f"/api/v1/teams/{team_id}/members/{dev_email}/role",
            json={"role_id": admin_role.id},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        assert response.json()["role_id"] == admin_role.id

        # 6. Check audit logs (requires audit.view)
        response = client.get(
            f"/api/v1/teams/{team_id}/audit-logs",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        # Audit logs should exist (created by SQLAlchemy event listeners)

        # 7. Remove member
        response = client.delete(
            f"/api/v1/teams/{team_id}/members/{dev_email}",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 204

    def test_role_based_access_control(self, client, team_repo, admin_role, developer_role, viewer_role, unique_id, db_session):
        """
        Verify role-based access:
        - Admin can manage team and view audit
        - Developer can provision GPUs (not tested here, but has permission)
        - Viewer can only view (all write operations fail)
        """
        owner_email = f"owner_{unique_id}@test.com"
        viewer_email = f"viewer_{unique_id}@test.com"

        # Create team
        team = team_repo.create_team(
            name=f"RBAC Test Team {unique_id}",
            slug=f"rbac-test-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        team_repo.add_member(team.id, viewer_email, viewer_role.id)
        db_session.commit()

        # Viewer token (only gpu.view and cost.view_own)
        viewer_token = create_auth_token(
            viewer_email,
            team_id=team.id,
            role="viewer",
            permissions=[GPU_VIEW],
        )

        # Viewer should NOT be able to update team
        response = client.put(
            f"/api/v1/teams/{team.id}",
            json={"description": "Should fail"},
            headers=auth_headers(viewer_token),
        )
        assert response.status_code == 403

        # Viewer should NOT be able to invite members
        response = client.post(
            f"/api/v1/teams/{team.id}/invitations",
            json={"email": "test@test.com", "role_id": viewer_role.id},
            headers=auth_headers(viewer_token),
        )
        assert response.status_code == 403

        # Viewer should NOT be able to view audit logs
        response = client.get(
            f"/api/v1/teams/{team.id}/audit-logs",
            headers=auth_headers(viewer_token),
        )
        assert response.status_code == 403

        # But viewer CAN get team details (member access)
        response = client.get(
            f"/api/v1/teams/{team.id}",
            headers=auth_headers(viewer_token),
        )
        assert response.status_code == 200
