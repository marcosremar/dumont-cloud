"""
Tests for Role Repository

Tests for SQLAlchemyRoleRepository with database operations.
Requires a running PostgreSQL database.

Run with: pytest tests/test_role_repository.py -v -n 0
Skip with: pytest -m "not integration"
"""

import pytest
from datetime import datetime
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
from src.infrastructure.providers.role_repository import SQLAlchemyRoleRepository
from src.infrastructure.providers.team_repository import SQLAlchemyTeamRepository
from src.models.rbac import Role, Permission, Team, TeamMember
from src.core.exceptions import NotFoundException, ValidationException


@pytest.fixture(scope="module")
def db_session():
    """Create database session for tests"""
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def role_repo(db_session):
    """Create role repository for tests"""
    return SQLAlchemyRoleRepository(db_session)


@pytest.fixture
def team_repo(db_session):
    """Create team repository for tests"""
    return SQLAlchemyTeamRepository(db_session)


@pytest.fixture
def unique_id():
    """Generate unique ID for test isolation"""
    return uuid.uuid4().hex[:8]


@pytest.fixture
def test_team(team_repo, unique_id):
    """Create a test team"""
    return team_repo.create_team(
        name=f"Role Test Team {unique_id}",
        slug=f"role-test-team-{unique_id}",
        owner_user_id=f"owner_{unique_id}"
    )


@pytest.fixture
def test_permission(db_session):
    """Get or create a test permission"""
    permission = db_session.query(Permission).filter(
        Permission.name == 'gpu.provision'
    ).first()

    if not permission:
        permission = Permission(
            name='gpu.provision',
            display_name='Provision GPU',
            description='Create GPU instances',
            category='gpu'
        )
        db_session.add(permission)
        db_session.flush()

    return permission


@pytest.fixture
def test_permissions(db_session):
    """Get or create test permissions"""
    permission_names = ['gpu.provision', 'gpu.view', 'gpu.delete']
    permissions = []

    for name in permission_names:
        permission = db_session.query(Permission).filter(
            Permission.name == name
        ).first()

        if not permission:
            permission = Permission(
                name=name,
                display_name=name.replace('.', ' ').title(),
                description=f'Permission for {name}',
                category='gpu'
            )
            db_session.add(permission)

        permissions.append(permission)

    db_session.flush()
    return permissions


class TestRoleCRUD:
    """Tests for Role CRUD operations"""

    def test_create_role(self, role_repo, test_team, unique_id):
        """Should create custom role correctly"""
        role = role_repo.create_role(
            name=f"custom-role-{unique_id}",
            display_name=f"Custom Role {unique_id}",
            description="A custom role for testing",
            team_id=test_team.id,
            is_system=False
        )

        assert role is not None
        assert role.id is not None
        assert role.name == f"custom-role-{unique_id}"
        assert role.team_id == test_team.id
        assert role.is_system == False

    def test_create_system_role(self, role_repo, unique_id):
        """Should create system role correctly"""
        role = role_repo.create_role(
            name=f"system-role-{unique_id}",
            display_name=f"System Role {unique_id}",
            description="A system role",
            is_system=True
        )

        assert role.is_system == True
        assert role.team_id is None

    def test_create_role_duplicate_name(self, role_repo, test_team, unique_id):
        """Should reject duplicate role name in same scope"""
        name = f"dup-role-{unique_id}"

        role_repo.create_role(
            name=name,
            display_name=f"Dup Role {unique_id}",
            team_id=test_team.id
        )

        with pytest.raises(ValidationException) as excinfo:
            role_repo.create_role(
                name=name,
                display_name=f"Another Dup Role {unique_id}",
                team_id=test_team.id
            )

        assert "already exists" in str(excinfo.value)

    def test_create_role_missing_fields(self, role_repo):
        """Should reject role without required fields"""
        with pytest.raises(ValidationException):
            role_repo.create_role(name="", display_name="")

    def test_get_role(self, role_repo, test_team, unique_id):
        """Should get role by ID"""
        role = role_repo.create_role(
            name=f"get-role-{unique_id}",
            display_name=f"Get Role {unique_id}",
            team_id=test_team.id
        )

        fetched = role_repo.get_role(role.id)

        assert fetched is not None
        assert fetched.id == role.id
        assert fetched.name == role.name

    def test_get_role_by_name_custom(self, role_repo, test_team, unique_id):
        """Should get custom role by name and team"""
        name = f"name-role-{unique_id}"
        role_repo.create_role(
            name=name,
            display_name=f"Name Role {unique_id}",
            team_id=test_team.id
        )

        fetched = role_repo.get_role_by_name(name, team_id=test_team.id)

        assert fetched is not None
        assert fetched.name == name

    def test_get_role_by_name_system(self, role_repo, db_session):
        """Should get system role by name"""
        # Ensure admin system role exists
        admin = db_session.query(Role).filter(
            Role.name == 'admin',
            Role.is_system == True
        ).first()

        if not admin:
            admin = Role(
                name='admin',
                display_name='Admin',
                description='Administrator',
                is_system=True
            )
            db_session.add(admin)
            db_session.flush()

        fetched = role_repo.get_role_by_name('admin', team_id=None)

        assert fetched is not None
        assert fetched.is_system == True

    def test_update_role(self, role_repo, test_team, unique_id):
        """Should update custom role"""
        role = role_repo.create_role(
            name=f"update-role-{unique_id}",
            display_name=f"Update Role {unique_id}",
            team_id=test_team.id
        )

        updated = role_repo.update_role(
            role.id,
            {'display_name': 'Updated Display Name', 'description': 'Updated description'}
        )

        assert updated.display_name == 'Updated Display Name'
        assert updated.description == 'Updated description'

    def test_update_system_role_rejected(self, role_repo, db_session):
        """Should reject updates to system roles"""
        # Create or get system role
        system_role = db_session.query(Role).filter(Role.is_system == True).first()

        if not system_role:
            system_role = Role(
                name='test-system',
                display_name='Test System',
                is_system=True
            )
            db_session.add(system_role)
            db_session.flush()

        with pytest.raises(ValidationException) as excinfo:
            role_repo.update_role(system_role.id, {'display_name': 'Modified'})

        assert "system roles" in str(excinfo.value)

    def test_delete_role(self, role_repo, test_team, unique_id):
        """Should delete custom role without members"""
        role = role_repo.create_role(
            name=f"delete-role-{unique_id}",
            display_name=f"Delete Role {unique_id}",
            team_id=test_team.id
        )

        result = role_repo.delete_role(role.id)

        assert result == True

        # Role should not exist
        fetched = role_repo.get_role(role.id)
        assert fetched is None

    def test_delete_system_role_rejected(self, role_repo, db_session):
        """Should reject deletion of system roles"""
        system_role = db_session.query(Role).filter(Role.is_system == True).first()

        if not system_role:
            system_role = Role(
                name='delete-system-test',
                display_name='Delete System Test',
                is_system=True
            )
            db_session.add(system_role)
            db_session.flush()

        with pytest.raises(ValidationException) as excinfo:
            role_repo.delete_role(system_role.id)

        assert "system roles" in str(excinfo.value)

    def test_delete_role_with_members_rejected(self, role_repo, team_repo, test_team, unique_id):
        """Should reject deletion of role with active members"""
        role = role_repo.create_role(
            name=f"with-members-{unique_id}",
            display_name=f"With Members {unique_id}",
            team_id=test_team.id
        )

        # Add a member with this role
        team_repo.add_member(
            team_id=test_team.id,
            user_id=f"member_{unique_id}",
            role_id=role.id
        )

        with pytest.raises(ValidationException) as excinfo:
            role_repo.delete_role(role.id)

        assert "active members" in str(excinfo.value)


class TestRoleLists:
    """Tests for role listing operations"""

    def test_list_system_roles(self, role_repo, db_session):
        """Should list all system roles"""
        # Ensure at least one system role exists
        if not db_session.query(Role).filter(Role.is_system == True).first():
            db_session.add(Role(
                name='list-system-admin',
                display_name='List System Admin',
                is_system=True
            ))
            db_session.flush()

        roles = role_repo.list_system_roles()

        assert len(roles) >= 1
        assert all(r.is_system for r in roles)

    def test_list_team_roles(self, role_repo, test_team, unique_id):
        """Should list custom roles for team"""
        # Create custom roles
        for i in range(3):
            role_repo.create_role(
                name=f"team-role-{unique_id}-{i}",
                display_name=f"Team Role {unique_id} {i}",
                team_id=test_team.id
            )

        roles = role_repo.list_team_roles(test_team.id)

        assert len(roles) >= 3
        assert all(r.team_id == test_team.id for r in roles)
        assert all(not r.is_system for r in roles)

    def test_list_available_roles(self, role_repo, test_team, db_session, unique_id):
        """Should list system roles plus team custom roles"""
        # Ensure system role exists
        if not db_session.query(Role).filter(Role.is_system == True).first():
            db_session.add(Role(
                name='available-system',
                display_name='Available System',
                is_system=True
            ))
            db_session.flush()

        # Create custom role
        role_repo.create_role(
            name=f"available-custom-{unique_id}",
            display_name=f"Available Custom {unique_id}",
            team_id=test_team.id
        )

        roles = role_repo.list_available_roles(test_team.id)

        # Should have both system and custom roles
        assert len(roles) >= 2
        has_system = any(r.is_system for r in roles)
        has_custom = any(r.team_id == test_team.id for r in roles)
        assert has_system
        assert has_custom


class TestPermissions:
    """Tests for permission operations"""

    def test_get_permission(self, role_repo, test_permission):
        """Should get permission by ID"""
        fetched = role_repo.get_permission(test_permission.id)

        assert fetched is not None
        assert fetched.id == test_permission.id

    def test_get_permission_by_name(self, role_repo, test_permission):
        """Should get permission by name"""
        fetched = role_repo.get_permission_by_name(test_permission.name)

        assert fetched is not None
        assert fetched.name == test_permission.name

    def test_list_permissions(self, role_repo, test_permissions):
        """Should list all permissions"""
        permissions = role_repo.list_permissions()

        assert len(permissions) >= len(test_permissions)

    def test_list_permissions_by_category(self, role_repo, test_permissions):
        """Should list permissions filtered by category"""
        permissions = role_repo.list_permissions(category='gpu')

        assert len(permissions) >= 1
        assert all(p.category == 'gpu' for p in permissions)

    def test_get_permissions_for_role(self, role_repo, test_team, test_permissions, unique_id):
        """Should get permissions assigned to a role"""
        role = role_repo.create_role(
            name=f"perms-role-{unique_id}",
            display_name=f"Perms Role {unique_id}",
            team_id=test_team.id
        )

        # Assign permissions
        for perm in test_permissions:
            role_repo.assign_permission_to_role(role.id, perm.id)

        role_perms = role_repo.get_permissions_for_role(role.id)

        assert len(role_perms) == len(test_permissions)


class TestRolePermissionAssignment:
    """Tests for role-permission assignment operations"""

    def test_assign_permission_to_role(self, role_repo, test_team, test_permission, unique_id):
        """Should assign permission to custom role"""
        role = role_repo.create_role(
            name=f"assign-perm-{unique_id}",
            display_name=f"Assign Perm {unique_id}",
            team_id=test_team.id
        )

        result = role_repo.assign_permission_to_role(role.id, test_permission.id)

        assert result == True

        # Verify assignment
        perms = role_repo.get_permissions_for_role(role.id)
        assert any(p.id == test_permission.id for p in perms)

    def test_assign_permission_already_assigned(self, role_repo, test_team, test_permission, unique_id):
        """Should return False when permission already assigned"""
        role = role_repo.create_role(
            name=f"dup-assign-{unique_id}",
            display_name=f"Dup Assign {unique_id}",
            team_id=test_team.id
        )

        role_repo.assign_permission_to_role(role.id, test_permission.id)
        result = role_repo.assign_permission_to_role(role.id, test_permission.id)

        assert result == False

    def test_assign_permission_to_system_role_rejected(self, role_repo, db_session, test_permission):
        """Should reject assigning permission to system role"""
        system_role = db_session.query(Role).filter(Role.is_system == True).first()

        if not system_role:
            system_role = Role(
                name='assign-system',
                display_name='Assign System',
                is_system=True
            )
            db_session.add(system_role)
            db_session.flush()

        with pytest.raises(ValidationException) as excinfo:
            role_repo.assign_permission_to_role(system_role.id, test_permission.id)

        assert "system roles" in str(excinfo.value)

    def test_remove_permission_from_role(self, role_repo, test_team, test_permission, unique_id):
        """Should remove permission from custom role"""
        role = role_repo.create_role(
            name=f"remove-perm-{unique_id}",
            display_name=f"Remove Perm {unique_id}",
            team_id=test_team.id
        )

        role_repo.assign_permission_to_role(role.id, test_permission.id)
        result = role_repo.remove_permission_from_role(role.id, test_permission.id)

        assert result == True

        # Verify removal
        perms = role_repo.get_permissions_for_role(role.id)
        assert not any(p.id == test_permission.id for p in perms)

    def test_remove_permission_not_assigned(self, role_repo, test_team, test_permission, unique_id):
        """Should return False when permission not assigned"""
        role = role_repo.create_role(
            name=f"not-assigned-{unique_id}",
            display_name=f"Not Assigned {unique_id}",
            team_id=test_team.id
        )

        result = role_repo.remove_permission_from_role(role.id, test_permission.id)

        assert result == False

    def test_set_role_permissions(self, role_repo, test_team, test_permissions, unique_id):
        """Should replace all permissions for a role"""
        role = role_repo.create_role(
            name=f"set-perms-{unique_id}",
            display_name=f"Set Perms {unique_id}",
            team_id=test_team.id
        )

        # Assign initial permission
        role_repo.assign_permission_to_role(role.id, test_permissions[0].id)

        # Replace with different set
        new_perm_ids = [p.id for p in test_permissions[1:]]
        updated = role_repo.set_role_permissions(role.id, new_perm_ids)

        role_perms = role_repo.get_permissions_for_role(role.id)

        assert len(role_perms) == len(new_perm_ids)
        assert not any(p.id == test_permissions[0].id for p in role_perms)


class TestRoleValidation:
    """Tests for role validation operations"""

    def test_has_members_assigned(self, role_repo, team_repo, test_team, unique_id):
        """Should check if role has members assigned"""
        role = role_repo.create_role(
            name=f"has-members-{unique_id}",
            display_name=f"Has Members {unique_id}",
            team_id=test_team.id
        )

        # Initially no members
        assert role_repo.has_members_assigned(role.id) == False

        # Add member
        team_repo.add_member(
            team_id=test_team.id,
            user_id=f"check_member_{unique_id}",
            role_id=role.id
        )

        # Now has members
        assert role_repo.has_members_assigned(role.id) == True

    def test_is_system_role(self, role_repo, test_team, db_session, unique_id):
        """Should check if role is system role"""
        # System role
        system_role = db_session.query(Role).filter(Role.is_system == True).first()

        if not system_role:
            system_role = Role(
                name='is-system-check',
                display_name='Is System Check',
                is_system=True
            )
            db_session.add(system_role)
            db_session.flush()

        assert role_repo.is_system_role(system_role.id) == True

        # Custom role
        custom_role = role_repo.create_role(
            name=f"is-custom-{unique_id}",
            display_name=f"Is Custom {unique_id}",
            team_id=test_team.id
        )

        assert role_repo.is_system_role(custom_role.id) == False


class TestUserPermissions:
    """Tests for user permission checking operations"""

    def test_get_user_permissions(self, role_repo, team_repo, test_team, test_permissions, unique_id):
        """Should get all permissions for a user in a team"""
        role = role_repo.create_role(
            name=f"user-perms-{unique_id}",
            display_name=f"User Perms {unique_id}",
            team_id=test_team.id
        )

        # Assign permissions to role
        for perm in test_permissions:
            role_repo.assign_permission_to_role(role.id, perm.id)

        # Add user to team with this role
        user_id = f"perm_user_{unique_id}"
        team_repo.add_member(test_team.id, user_id, role.id)

        perms = role_repo.get_user_permissions(user_id, test_team.id)

        assert len(perms) == len(test_permissions)
        assert all(p in [tp.name for tp in test_permissions] for p in perms)

    def test_get_user_permissions_not_member(self, role_repo, test_team, unique_id):
        """Should return empty list for non-member"""
        perms = role_repo.get_user_permissions(f"nonmember_{unique_id}", test_team.id)

        assert perms == []

    def test_user_has_permission(self, role_repo, team_repo, test_team, test_permission, unique_id):
        """Should check if user has specific permission"""
        role = role_repo.create_role(
            name=f"has-perm-{unique_id}",
            display_name=f"Has Perm {unique_id}",
            team_id=test_team.id
        )

        role_repo.assign_permission_to_role(role.id, test_permission.id)

        user_id = f"has_perm_user_{unique_id}"
        team_repo.add_member(test_team.id, user_id, role.id)

        assert role_repo.user_has_permission(user_id, test_team.id, test_permission.name) == True
        assert role_repo.user_has_permission(user_id, test_team.id, 'nonexistent.perm') == False

    def test_get_user_role(self, role_repo, team_repo, test_team, unique_id):
        """Should get user's role in a team"""
        role = role_repo.create_role(
            name=f"get-user-role-{unique_id}",
            display_name=f"Get User Role {unique_id}",
            team_id=test_team.id
        )

        user_id = f"role_user_{unique_id}"
        team_repo.add_member(test_team.id, user_id, role.id)

        user_role = role_repo.get_user_role(user_id, test_team.id)

        assert user_role is not None
        assert user_role.id == role.id
        assert user_role.name == role.name

    def test_get_user_role_not_member(self, role_repo, test_team, unique_id):
        """Should return None for non-member"""
        user_role = role_repo.get_user_role(f"nonmember_{unique_id}", test_team.id)

        assert user_role is None
