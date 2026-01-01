"""
Database migration script to seed predefined RBAC roles and permissions.

This creates:
- All permissions defined in PERMISSIONS constant
- Three predefined system roles: Admin, Developer, Viewer
- Role-Permission associations based on ROLE_PERMISSIONS mapping

This migration is idempotent - safe to run multiple times.
It will skip creating records that already exist.

Run with: python src/migrations/seed_predefined_roles.py
"""
import logging
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from src.config.database import engine, SessionLocal
from src.models.rbac import (
    Permission,
    Role,
    PERMISSIONS,
    SYSTEM_ROLES,
    ROLE_PERMISSIONS,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_permissions(db: Session) -> dict[str, Permission]:
    """
    Seed all permissions from the PERMISSIONS constant.

    Returns a dictionary mapping permission names to Permission objects.
    """
    permission_map = {}
    created_count = 0
    existing_count = 0

    for perm_name, perm_data in PERMISSIONS.items():
        # Check if permission already exists
        existing = db.query(Permission).filter_by(name=perm_name).first()

        if existing:
            permission_map[perm_name] = existing
            existing_count += 1
        else:
            # Create new permission
            permission = Permission(
                name=perm_name,
                display_name=perm_data['display_name'],
                description=perm_data['description'],
                category=perm_data['category'],
            )
            db.add(permission)
            db.flush()  # Get the ID
            permission_map[perm_name] = permission
            created_count += 1

    if created_count > 0:
        logger.info(f"Created {created_count} new permissions")
    if existing_count > 0:
        logger.info(f"Found {existing_count} existing permissions")

    return permission_map


def seed_system_roles(db: Session, permission_map: dict[str, Permission]) -> int:
    """
    Seed the three predefined system roles with their permissions.

    Returns the number of system roles created.
    """
    created_count = 0

    for role_key, role_data in SYSTEM_ROLES.items():
        # Check if role already exists
        existing = db.query(Role).filter_by(
            name=role_data['name'],
            is_system=True
        ).first()

        if existing:
            logger.info(f"System role '{role_data['name']}' already exists")
            # Update permissions if needed
            role_permission_names = ROLE_PERMISSIONS.get(role_key, [])
            expected_permissions = {permission_map[p] for p in role_permission_names if p in permission_map}
            current_permissions = set(existing.permissions)

            if expected_permissions != current_permissions:
                existing.permissions = list(expected_permissions)
                logger.info(f"  Updated permissions for '{role_data['name']}'")
        else:
            # Create new system role
            role = Role(
                name=role_data['name'],
                display_name=role_data['display_name'],
                description=role_data['description'],
                is_system=True,
                team_id=None,  # System roles don't belong to a specific team
            )

            # Add permissions to the role
            role_permission_names = ROLE_PERMISSIONS.get(role_key, [])
            for perm_name in role_permission_names:
                if perm_name in permission_map:
                    role.permissions.append(permission_map[perm_name])

            db.add(role)
            created_count += 1
            logger.info(f"Created system role '{role_data['name']}' with {len(role.permissions)} permissions")

    return created_count


def run_migration():
    """Execute database migration to seed predefined roles and permissions."""

    # Check if tables exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    required_tables = ['permissions', 'roles', 'role_permissions']
    missing_tables = [t for t in required_tables if t not in existing_tables]

    if missing_tables:
        logger.error(f"Required tables do not exist: {', '.join(missing_tables)}")
        logger.error("Please run create_rbac_tables.py first")
        raise RuntimeError(f"Missing required tables: {missing_tables}")

    db = SessionLocal()

    try:
        logger.info("Starting seed migration for predefined roles and permissions...")

        # Step 1: Seed all permissions
        logger.info("Seeding permissions...")
        permission_map = seed_permissions(db)

        # Step 2: Seed system roles with their permissions
        logger.info("Seeding system roles...")
        roles_created = seed_system_roles(db, permission_map)

        # Commit all changes
        db.commit()

        # Verify seeding
        system_roles_count = db.query(Role).filter_by(is_system=True).count()
        permissions_count = db.query(Permission).count()

        logger.info("=" * 50)
        logger.info("Seed migration completed successfully!")
        logger.info(f"  Total permissions in database: {permissions_count}")
        logger.info(f"  Total system roles in database: {system_roles_count}")

        # List the system roles with their permissions
        system_roles = db.query(Role).filter_by(is_system=True).all()
        for role in system_roles:
            perm_names = [p.name for p in role.permissions]
            logger.info(f"  - {role.display_name}: {len(role.permissions)} permissions")

        if system_roles_count != 3:
            logger.warning(f"Expected 3 system roles, but found {system_roles_count}")

        logger.info("=" * 50)

    except Exception as e:
        db.rollback()
        logger.error(f"Seed migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
