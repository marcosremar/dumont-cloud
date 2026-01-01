"""
Database migration script to import existing file-based users to the database.

This reads users from the file-based storage (config.json) and creates
corresponding User records in the PostgreSQL database.

Features:
- Preserves password hashes (no re-hashing needed)
- Preserves settings as JSON
- Preserves vast_api_key
- Idempotent - safe to run multiple times (skips existing users)

Run with: python src/migrations/migrate_users_to_db.py
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import inspect
from sqlalchemy.orm import Session
from src.config.database import engine, SessionLocal
from src.domain.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_file_users(config_file: str = "config.json") -> Dict[str, Dict[str, Any]]:
    """
    Load users from the file-based storage (config.json).

    Args:
        config_file: Path to the config file (relative to project root)

    Returns:
        Dictionary mapping email to user data
    """
    if not os.path.exists(config_file):
        logger.warning(f"Config file not found: {config_file}")
        return {}

    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            return config.get("users", {})
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {config_file}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error reading {config_file}: {e}")
        return {}


def migrate_user_to_db(
    db: Session,
    email: str,
    user_data: Dict[str, Any]
) -> Optional[User]:
    """
    Migrate a single user from file storage to database.

    Args:
        db: Database session
        email: User's email address
        user_data: User data from file storage

    Returns:
        Created User object, or None if user already exists
    """
    # Check if user already exists in database
    existing_user = db.query(User).filter_by(email=email).first()

    if existing_user:
        logger.info(f"  User '{email}' already exists in database, skipping")
        return None

    # Extract data from file storage format
    password_hash = user_data.get("password", "")
    vast_api_key = user_data.get("vast_api_key")
    settings = user_data.get("settings", {})

    # Create User ORM instance
    user = User(
        email=email,
        password_hash=password_hash,
        vast_api_key=vast_api_key,
        settings_json=json.dumps(settings) if settings else "{}",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(user)
    logger.info(f"  Migrated user '{email}' to database")

    return user


def run_migration(config_file: str = "config.json"):
    """
    Execute database migration to import file-based users.

    Args:
        config_file: Path to the config file containing users
    """
    # Check if users table exists
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "users" not in existing_tables:
        logger.error("Users table does not exist in database")
        logger.error("Please run create_rbac_tables.py first")
        raise RuntimeError("Users table not found. Run create_rbac_tables.py first.")

    # Load users from file storage
    logger.info(f"Loading users from file: {config_file}")
    file_users = load_file_users(config_file)

    if not file_users:
        logger.info("No users found in file storage. Nothing to migrate.")
        return

    logger.info(f"Found {len(file_users)} users in file storage")

    db = SessionLocal()

    try:
        logger.info("Starting user migration...")

        migrated_count = 0
        skipped_count = 0

        for email, user_data in file_users.items():
            result = migrate_user_to_db(db, email, user_data)
            if result:
                migrated_count += 1
            else:
                skipped_count += 1

        # Commit all changes
        db.commit()

        # Verify migration
        total_users = db.query(User).count()

        logger.info("=" * 50)
        logger.info("User migration completed successfully!")
        logger.info(f"  Users migrated: {migrated_count}")
        logger.info(f"  Users skipped (already exist): {skipped_count}")
        logger.info(f"  Total users in database: {total_users}")
        logger.info("=" * 50)

    except Exception as e:
        db.rollback()
        logger.error(f"User migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
