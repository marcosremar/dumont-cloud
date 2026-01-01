"""
Database migration script to create RBAC (Role-Based Access Control) tables.

This creates the following tables:
- users (if not exists)
- teams
- permissions
- roles
- role_permissions (association table)
- team_members
- team_invitations
- audit_logs
- team_quotas

This migration is idempotent - safe to run multiple times.

Run with: python src/migrations/create_rbac_tables.py
"""
import logging
from sqlalchemy import inspect
from src.config.database import engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute database migration to create all RBAC tables."""

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Import all models to register them with Base.metadata
    # This ensures all tables are known to SQLAlchemy
    from src.domain.models.user import User
    from src.models.rbac import (
        Team,
        Permission,
        Role,
        TeamMember,
        TeamInvitation,
        AuditLog,
        TeamQuota,
        role_permissions,
    )

    # Tables that should be created by this migration
    rbac_tables = [
        'users',
        'teams',
        'permissions',
        'roles',
        'role_permissions',
        'team_members',
        'team_invitations',
        'audit_logs',
        'team_quotas',
    ]

    try:
        # Check which tables already exist
        tables_to_create = [t for t in rbac_tables if t not in existing_tables]
        already_exist = [t for t in rbac_tables if t in existing_tables]

        if already_exist:
            logger.info(f"Tables already exist: {', '.join(already_exist)}")

        if tables_to_create:
            logger.info(f"Creating tables: {', '.join(tables_to_create)}")
        else:
            logger.info("All RBAC tables already exist. Nothing to do.")
            return

        # Create all tables that don't exist yet
        # SQLAlchemy will skip tables that already exist
        Base.metadata.create_all(bind=engine)

        # Verify creation
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()

        created_tables = []
        for table in rbac_tables:
            if table in new_tables:
                if table in tables_to_create:
                    created_tables.append(table)
                    logger.info(f"  Created table: {table}")

        if created_tables:
            logger.info(f"Successfully created {len(created_tables)} tables: {', '.join(created_tables)}")

        # Verify all required tables exist
        missing_tables = [t for t in rbac_tables if t not in new_tables]
        if missing_tables:
            logger.error(f"ERROR: Some tables were not created: {', '.join(missing_tables)}")
            raise RuntimeError(f"Failed to create tables: {missing_tables}")

        logger.info("RBAC tables migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
