#!/usr/bin/env python3
"""
Apply NPS database migration.

This script applies the NPS tables migration using SQLAlchemy.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text

# Database configuration
DB_USER = os.getenv('DB_USER', 'dumont')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'dumont123')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'dumont_cloud')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def apply_migration():
    """Apply the NPS migration SQL file."""
    migration_file = project_root / "migrations" / "002_create_nps_tables.sql"

    if not migration_file.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        return False

    print(f"Reading migration file: {migration_file}")
    migration_sql = migration_file.read_text()

    print(f"Connecting to database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Execute the migration
            print("Applying migration...")
            conn.execute(text(migration_sql))
            conn.commit()
            print("Migration applied successfully!")

            # Verify tables exist
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('nps_responses', 'nps_survey_config', 'nps_user_interactions')
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]

            print(f"\nTables found: {tables}")

            if len(tables) == 3:
                print("\n✅ All NPS tables created successfully!")
                return True
            else:
                print(f"\n❌ Expected 3 tables, found {len(tables)}")
                return False

    except Exception as e:
        print(f"ERROR: Failed to apply migration: {e}")
        return False


if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
