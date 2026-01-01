"""
Tests for Team Repository

Tests for SQLAlchemyTeamRepository with database operations.
Requires a running PostgreSQL database.

Run with: pytest tests/test_team_repository.py -v -n 0
Skip with: pytest -m "not integration"
"""

import pytest
from datetime import datetime, timedelta
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.orm import Session

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


from src.config.database import engine, SessionLocal
from src.infrastructure.providers.team_repository import SQLAlchemyTeamRepository
from src.infrastructure.providers.role_repository import SQLAlchemyRoleRepository
from src.models.rbac import Team, TeamMember, TeamInvitation, TeamQuota, Role, Permission
from src.core.exceptions import NotFoundException, ValidationException


@pytest.fixture(scope="module")
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


class TestTeamCRUD:
    """Tests for Team CRUD operations"""

    def test_create_team(self, team_repo, unique_id):
        """Should create team correctly"""
        name = f"Test Team {unique_id}"
        slug = f"test-team-{unique_id}"

        team = team_repo.create_team(
            name=name,
            slug=slug,
            owner_user_id=f"owner_{unique_id}",
            description="A test team"
        )

        assert team is not None
        assert team.id is not None
        assert team.name == name
        assert team.slug == slug
        assert team.is_active == True
        assert team.deleted_at is None

    def test_create_team_duplicate_name(self, team_repo, unique_id):
        """Should reject duplicate team name"""
        name = f"Duplicate Team {unique_id}"
        slug1 = f"duplicate-team-{unique_id}-1"
        slug2 = f"duplicate-team-{unique_id}-2"

        team_repo.create_team(
            name=name,
            slug=slug1,
            owner_user_id=f"owner_{unique_id}"
        )

        with pytest.raises(ValidationException) as excinfo:
            team_repo.create_team(
                name=name,
                slug=slug2,
                owner_user_id=f"owner_{unique_id}"
            )

        assert "already exists" in str(excinfo.value)

    def test_create_team_duplicate_slug(self, team_repo, unique_id):
        """Should reject duplicate team slug"""
        slug = f"dup-slug-{unique_id}"

        team_repo.create_team(
            name=f"Team A {unique_id}",
            slug=slug,
            owner_user_id=f"owner_{unique_id}"
        )

        with pytest.raises(ValidationException) as excinfo:
            team_repo.create_team(
                name=f"Team B {unique_id}",
                slug=slug,
                owner_user_id=f"owner_{unique_id}"
            )

        assert "already exists" in str(excinfo.value)

    def test_get_team(self, team_repo, unique_id):
        """Should get team by ID"""
        team = team_repo.create_team(
            name=f"Get Team {unique_id}",
            slug=f"get-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        fetched = team_repo.get_team(team.id)

        assert fetched is not None
        assert fetched.id == team.id
        assert fetched.name == team.name

    def test_get_team_by_slug(self, team_repo, unique_id):
        """Should get team by slug"""
        slug = f"slug-test-{unique_id}"
        team = team_repo.create_team(
            name=f"Slug Team {unique_id}",
            slug=slug,
            owner_user_id=f"owner_{unique_id}"
        )

        fetched = team_repo.get_team_by_slug(slug)

        assert fetched is not None
        assert fetched.slug == slug

    def test_get_team_by_name(self, team_repo, unique_id):
        """Should get team by name"""
        name = f"Name Team {unique_id}"
        team = team_repo.create_team(
            name=name,
            slug=f"name-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        fetched = team_repo.get_team_by_name(name)

        assert fetched is not None
        assert fetched.name == name

    def test_update_team(self, team_repo, unique_id):
        """Should update team information"""
        team = team_repo.create_team(
            name=f"Update Team {unique_id}",
            slug=f"update-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        updated = team_repo.update_team(
            team.id,
            {'description': 'Updated description', 'is_active': False}
        )

        assert updated.description == 'Updated description'
        assert updated.is_active == False

    def test_update_team_not_found(self, team_repo):
        """Should raise error for non-existent team"""
        with pytest.raises(NotFoundException):
            team_repo.update_team(999999, {'description': 'Test'})

    def test_delete_team(self, team_repo, unique_id):
        """Should soft delete team"""
        team = team_repo.create_team(
            name=f"Delete Team {unique_id}",
            slug=f"delete-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        result = team_repo.delete_team(team.id)

        assert result == True

        # Team should not be found by normal get
        fetched = team_repo.get_team(team.id)
        assert fetched is None

    def test_list_teams(self, team_repo, unique_id):
        """Should list teams with pagination"""
        # Create a few teams
        for i in range(3):
            team_repo.create_team(
                name=f"List Team {unique_id} {i}",
                slug=f"list-team-{unique_id}-{i}",
                owner_user_id=f"owner_{unique_id}"
            )

        teams = team_repo.list_teams(limit=2)

        assert len(teams) <= 2

    def test_get_teams_for_user(self, team_repo, admin_role, unique_id):
        """Should get teams where user is a member"""
        user_id = f"member_{unique_id}"

        # Create team and add member
        team = team_repo.create_team(
            name=f"Member Team {unique_id}",
            slug=f"member-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        team_repo.add_member(
            team_id=team.id,
            user_id=user_id,
            role_id=admin_role.id
        )

        teams = team_repo.get_teams_for_user(user_id)

        assert len(teams) >= 1
        assert any(t.id == team.id for t in teams)


class TestTeamMembers:
    """Tests for team member operations"""

    def test_add_member(self, team_repo, admin_role, unique_id):
        """Should add member to team"""
        team = team_repo.create_team(
            name=f"Add Member Team {unique_id}",
            slug=f"add-member-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        member = team_repo.add_member(
            team_id=team.id,
            user_id=f"user_{unique_id}",
            role_id=admin_role.id,
            invited_by_user_id=f"owner_{unique_id}"
        )

        assert member is not None
        assert member.team_id == team.id
        assert member.role_id == admin_role.id
        assert member.is_active == True

    def test_add_member_duplicate(self, team_repo, admin_role, unique_id):
        """Should reject duplicate member"""
        team = team_repo.create_team(
            name=f"Dup Member Team {unique_id}",
            slug=f"dup-member-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        user_id = f"dup_user_{unique_id}"

        team_repo.add_member(
            team_id=team.id,
            user_id=user_id,
            role_id=admin_role.id
        )

        with pytest.raises(ValidationException) as excinfo:
            team_repo.add_member(
                team_id=team.id,
                user_id=user_id,
                role_id=admin_role.id
            )

        assert "already a member" in str(excinfo.value)

    def test_remove_member(self, team_repo, admin_role, unique_id):
        """Should soft remove member from team"""
        team = team_repo.create_team(
            name=f"Remove Member Team {unique_id}",
            slug=f"remove-member-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        user_id = f"remove_user_{unique_id}"
        team_repo.add_member(team.id, user_id, admin_role.id)

        result = team_repo.remove_member(
            team_id=team.id,
            user_id=user_id,
            removed_by_user_id=f"admin_{unique_id}"
        )

        assert result == True

        # Member should not be found
        member = team_repo.get_member(team.id, user_id)
        assert member is None

    def test_get_member(self, team_repo, admin_role, unique_id):
        """Should get specific team member"""
        team = team_repo.create_team(
            name=f"Get Member Team {unique_id}",
            slug=f"get-member-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        user_id = f"get_user_{unique_id}"
        team_repo.add_member(team.id, user_id, admin_role.id)

        member = team_repo.get_member(team.id, user_id)

        assert member is not None
        assert member.user_id == user_id

    def test_get_members(self, team_repo, admin_role, unique_id):
        """Should get all team members"""
        team = team_repo.create_team(
            name=f"List Members Team {unique_id}",
            slug=f"list-members-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        # Add multiple members
        for i in range(3):
            team_repo.add_member(team.id, f"member_{unique_id}_{i}", admin_role.id)

        members = team_repo.get_members(team.id)

        assert len(members) >= 3

    def test_update_member_role(self, team_repo, admin_role, developer_role, unique_id):
        """Should update member's role"""
        team = team_repo.create_team(
            name=f"Update Role Team {unique_id}",
            slug=f"update-role-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        user_id = f"role_user_{unique_id}"
        team_repo.add_member(team.id, user_id, admin_role.id)

        updated = team_repo.update_member_role(team.id, user_id, developer_role.id)

        assert updated.role_id == developer_role.id

    def test_is_member(self, team_repo, admin_role, unique_id):
        """Should check if user is member"""
        team = team_repo.create_team(
            name=f"Is Member Team {unique_id}",
            slug=f"is-member-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        user_id = f"is_member_user_{unique_id}"
        team_repo.add_member(team.id, user_id, admin_role.id)

        assert team_repo.is_member(team.id, user_id) == True
        assert team_repo.is_member(team.id, "nonexistent") == False

    def test_get_member_count(self, team_repo, admin_role, unique_id):
        """Should get member count"""
        team = team_repo.create_team(
            name=f"Count Team {unique_id}",
            slug=f"count-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        for i in range(3):
            team_repo.add_member(team.id, f"count_user_{unique_id}_{i}", admin_role.id)

        count = team_repo.get_member_count(team.id)

        assert count == 3

    def test_get_admin_count(self, team_repo, admin_role, developer_role, unique_id):
        """Should get admin count"""
        team = team_repo.create_team(
            name=f"Admin Count Team {unique_id}",
            slug=f"admin-count-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        # Add admins
        team_repo.add_member(team.id, f"admin1_{unique_id}", admin_role.id)
        team_repo.add_member(team.id, f"admin2_{unique_id}", admin_role.id)
        # Add developer (not admin)
        team_repo.add_member(team.id, f"dev_{unique_id}", developer_role.id)

        admin_count = team_repo.get_admin_count(team.id)

        assert admin_count == 2


class TestTeamInvitations:
    """Tests for team invitation operations"""

    def test_create_invitation(self, team_repo, admin_role, unique_id):
        """Should create invitation"""
        team = team_repo.create_team(
            name=f"Invite Team {unique_id}",
            slug=f"invite-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        invitation = team_repo.create_invitation(
            team_id=team.id,
            email=f"invite_{unique_id}@test.com",
            role_id=admin_role.id,
            invited_by_user_id=f"owner_{unique_id}",
            token=f"token_{unique_id}",
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

        assert invitation is not None
        assert invitation.status == 'pending'
        assert invitation.email == f"invite_{unique_id}@test.com"

    def test_create_invitation_duplicate(self, team_repo, admin_role, unique_id):
        """Should reject duplicate pending invitation"""
        team = team_repo.create_team(
            name=f"Dup Invite Team {unique_id}",
            slug=f"dup-invite-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        email = f"dup_invite_{unique_id}@test.com"

        team_repo.create_invitation(
            team_id=team.id,
            email=email,
            role_id=admin_role.id,
            invited_by_user_id=f"owner_{unique_id}",
            token=f"token1_{unique_id}",
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

        with pytest.raises(ValidationException) as excinfo:
            team_repo.create_invitation(
                team_id=team.id,
                email=email,
                role_id=admin_role.id,
                invited_by_user_id=f"owner_{unique_id}",
                token=f"token2_{unique_id}",
                expires_at=datetime.utcnow() + timedelta(days=7)
            )

        assert "already exists" in str(excinfo.value)

    def test_get_invitation_by_token(self, team_repo, admin_role, unique_id):
        """Should get invitation by token"""
        team = team_repo.create_team(
            name=f"Token Team {unique_id}",
            slug=f"token-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        token = f"unique_token_{unique_id}"

        team_repo.create_invitation(
            team_id=team.id,
            email=f"token_{unique_id}@test.com",
            role_id=admin_role.id,
            invited_by_user_id=f"owner_{unique_id}",
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

        invitation = team_repo.get_invitation_by_token(token)

        assert invitation is not None
        assert invitation.token == token

    def test_get_invitations_for_team(self, team_repo, admin_role, unique_id):
        """Should get invitations for team"""
        team = team_repo.create_team(
            name=f"List Invites Team {unique_id}",
            slug=f"list-invites-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        # Create multiple invitations
        for i in range(3):
            team_repo.create_invitation(
                team_id=team.id,
                email=f"list_{unique_id}_{i}@test.com",
                role_id=admin_role.id,
                invited_by_user_id=f"owner_{unique_id}",
                token=f"list_token_{unique_id}_{i}",
                expires_at=datetime.utcnow() + timedelta(days=7)
            )

        invitations = team_repo.get_invitations_for_team(team.id)

        assert len(invitations) >= 3

    def test_accept_invitation(self, team_repo, admin_role, unique_id):
        """Should accept invitation"""
        team = team_repo.create_team(
            name=f"Accept Team {unique_id}",
            slug=f"accept-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        invitation = team_repo.create_invitation(
            team_id=team.id,
            email=f"accept_{unique_id}@test.com",
            role_id=admin_role.id,
            invited_by_user_id=f"owner_{unique_id}",
            token=f"accept_token_{unique_id}",
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

        accepted = team_repo.accept_invitation(
            invitation.id,
            accepted_by_user_id=f"new_user_{unique_id}"
        )

        assert accepted.status == 'accepted'
        assert accepted.accepted_at is not None

    def test_accept_expired_invitation(self, team_repo, admin_role, unique_id):
        """Should reject expired invitation"""
        team = team_repo.create_team(
            name=f"Expired Team {unique_id}",
            slug=f"expired-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        # Create already expired invitation
        invitation = team_repo.create_invitation(
            team_id=team.id,
            email=f"expired_{unique_id}@test.com",
            role_id=admin_role.id,
            invited_by_user_id=f"owner_{unique_id}",
            token=f"expired_token_{unique_id}",
            expires_at=datetime.utcnow() - timedelta(days=1)  # Already expired
        )

        with pytest.raises(ValidationException) as excinfo:
            team_repo.accept_invitation(
                invitation.id,
                accepted_by_user_id=f"new_user_{unique_id}"
            )

        assert "expired" in str(excinfo.value)

    def test_revoke_invitation(self, team_repo, admin_role, unique_id):
        """Should revoke invitation"""
        team = team_repo.create_team(
            name=f"Revoke Team {unique_id}",
            slug=f"revoke-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        invitation = team_repo.create_invitation(
            team_id=team.id,
            email=f"revoke_{unique_id}@test.com",
            role_id=admin_role.id,
            invited_by_user_id=f"owner_{unique_id}",
            token=f"revoke_token_{unique_id}",
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

        result = team_repo.revoke_invitation(invitation.id)

        assert result == True


class TestTeamQuotas:
    """Tests for team quota operations"""

    def test_create_quota(self, team_repo, unique_id):
        """Should create quota for team"""
        team = team_repo.create_team(
            name=f"Quota Team {unique_id}",
            slug=f"quota-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        quota = team_repo.create_or_update_quota(
            team_id=team.id,
            max_gpu_hours_per_month=100.0,
            max_concurrent_instances=5,
            max_monthly_budget_usd=500.0
        )

        assert quota is not None
        assert quota.max_gpu_hours_per_month == 100.0
        assert quota.max_concurrent_instances == 5
        assert quota.max_monthly_budget_usd == 500.0

    def test_update_quota(self, team_repo, unique_id):
        """Should update existing quota"""
        team = team_repo.create_team(
            name=f"Update Quota Team {unique_id}",
            slug=f"update-quota-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_gpu_hours_per_month=100.0
        )

        updated = team_repo.create_or_update_quota(
            team_id=team.id,
            max_gpu_hours_per_month=200.0
        )

        assert updated.max_gpu_hours_per_month == 200.0

    def test_get_quota(self, team_repo, unique_id):
        """Should get team quota"""
        team = team_repo.create_team(
            name=f"Get Quota Team {unique_id}",
            slug=f"get-quota-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_gpu_hours_per_month=100.0
        )

        quota = team_repo.get_quota(team.id)

        assert quota is not None
        assert quota.max_gpu_hours_per_month == 100.0

    def test_update_quota_usage(self, team_repo, unique_id):
        """Should update quota usage counters"""
        team = team_repo.create_team(
            name=f"Usage Quota Team {unique_id}",
            slug=f"usage-quota-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_gpu_hours_per_month=100.0
        )

        updated = team_repo.update_quota_usage(
            team_id=team.id,
            gpu_hours_delta=10.0,
            instances_delta=1,
            spend_delta=50.0
        )

        assert updated.current_gpu_hours_used == 10.0
        assert updated.current_concurrent_instances == 1
        assert updated.current_monthly_spend_usd == 50.0

    def test_check_quota_available(self, team_repo, unique_id):
        """Should check if quota is available"""
        team = team_repo.create_team(
            name=f"Check Quota Team {unique_id}",
            slug=f"check-quota-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=5
        )

        # Set usage to 4
        team_repo.update_quota_usage(team.id, instances_delta=4)

        # Check if 1 more is available
        result = team_repo.check_quota_available(team.id, instances_needed=1)
        assert result['available'] == True

        # Check if 2 more is available (should fail)
        result = team_repo.check_quota_available(team.id, instances_needed=2)
        assert result['available'] == False
        assert len(result['violations']) > 0

    def test_check_and_reserve_instance_quota(self, team_repo, unique_id):
        """Should atomically check and reserve instance quota"""
        team = team_repo.create_team(
            name=f"Reserve Quota Team {unique_id}",
            slug=f"reserve-quota-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=5
        )

        # Reserve 1 instance
        result = team_repo.check_and_reserve_instance_quota(team.id, instances_needed=1)

        assert result['available'] == True

        # Verify quota was incremented
        quota = team_repo.get_quota(team.id)
        assert quota.current_concurrent_instances == 1

    def test_release_instance_quota(self, team_repo, unique_id):
        """Should release instance quota"""
        team = team_repo.create_team(
            name=f"Release Quota Team {unique_id}",
            slug=f"release-quota-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=5
        )

        team_repo.update_quota_usage(team.id, instances_delta=3)

        quota = team_repo.release_instance_quota(team.id, instances_released=1)

        assert quota.current_concurrent_instances == 2

    def test_no_quota_means_unlimited(self, team_repo, unique_id):
        """Should allow unlimited resources when no quota exists"""
        team = team_repo.create_team(
            name=f"No Quota Team {unique_id}",
            slug=f"no-quota-team-{unique_id}",
            owner_user_id=f"owner_{unique_id}"
        )

        result = team_repo.check_quota_available(
            team.id,
            gpu_hours_needed=1000,
            instances_needed=100,
            budget_needed=10000
        )

        assert result['available'] == True
        assert result['quota_exists'] == False
