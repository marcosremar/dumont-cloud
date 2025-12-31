#!/usr/bin/env python3
"""
Database migration runner script.
Executes SQL migration files in order.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment or use default."""
    db_user = os.getenv('DB_USER', 'dumont')
    db_password = os.getenv('DB_PASSWORD', 'dumont123')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'dumont_cloud')
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def run_migrations():
    """Run all SQL migrations in order."""
    database_url = get_database_url()
    logger.info(f"Connecting to database...")

    engine = create_engine(database_url)
    migrations_dir = project_root / 'migrations'

    # Get all SQL migration files sorted by name
    migration_files = sorted(migrations_dir.glob('*.sql'))

    if not migration_files:
        logger.warning("No migration files found")
        return

    logger.info(f"Found {len(migration_files)} migration file(s)")

    with engine.connect() as conn:
        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")

            sql_content = migration_file.read_text()

            # Split by semicolon to execute each statement
            statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

            for statement in statements:
                if statement:
                    try:
                        conn.execute(text(statement))
                    except Exception as e:
                        # Ignore "already exists" errors for idempotent migrations
                        if 'already exists' in str(e).lower():
                            logger.info(f"  Object already exists, skipping...")
                        else:
                            raise

            conn.commit()
            logger.info(f"  Completed: {migration_file.name}")

    logger.info("All migrations completed successfully")


def verify_tables():
    """Verify that expected tables exist."""
    database_url = get_database_url()
    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check user_region_preferences table
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'user_region_preferences'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()

        if columns:
            logger.info("Table 'user_region_preferences' exists with columns:")
            for col_name, col_type in columns:
                logger.info(f"  - {col_name}: {col_type}")

            # Check for user_id column specifically
            col_names = [col[0] for col in columns]
            if 'user_id' in col_names:
                print("OK")
                return True
            else:
                print("FAIL - user_id column not found")
                return False
        else:
            print("FAIL - table not found")
            return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run database migrations')
    parser.add_argument('--verify', action='store_true', help='Verify tables after migration')
    parser.add_argument('--verify-only', action='store_true', help='Only verify, do not run migrations')
    args = parser.parse_args()

    try:
        if not args.verify_only:
            run_migrations()

        if args.verify or args.verify_only:
            verify_tables()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print("FAIL")
        sys.exit(1)
