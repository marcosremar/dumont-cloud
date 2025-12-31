"""
Add user_region_preferences table.

Revision ID: add_user_region_preferences
Create Date: 2025-12-31
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base

# revision identifiers, used by Alembic (if used)
revision = 'add_user_region_preferences'
down_revision = None
branch_labels = None
depends_on = None

Base = declarative_base()


def get_table_definition():
    """Return the SQLAlchemy table definition for reference."""
    from src.models.user_region_preference import UserRegionPreference
    return UserRegionPreference


def get_sql_upgrade():
    """SQL statements to create the table."""
    return """
    CREATE TABLE IF NOT EXISTS user_region_preferences (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(100) NOT NULL UNIQUE,
        preferred_region VARCHAR(100) NOT NULL,
        fallback_regions JSONB,
        data_residency_requirement VARCHAR(50),
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_user_region_preferences_user_id ON user_region_preferences (user_id);
    CREATE INDEX IF NOT EXISTS idx_user_region_residency ON user_region_preferences (user_id, data_residency_requirement);
    """


def get_sql_downgrade():
    """SQL statements to drop the table."""
    return """
    DROP INDEX IF EXISTS idx_user_region_residency;
    DROP INDEX IF EXISTS idx_user_region_preferences_user_id;
    DROP TABLE IF EXISTS user_region_preferences;
    """


# Alembic-style upgrade/downgrade functions (if Alembic is used)
def upgrade():
    """Upgrade database schema."""
    from sqlalchemy import create_engine, text
    import os

    database_url = os.getenv('DATABASE_URL', 'postgresql://dumont:dumont123@localhost:5432/dumont_cloud')
    engine = create_engine(database_url)

    with engine.connect() as conn:
        conn.execute(text(get_sql_upgrade()))
        conn.commit()


def downgrade():
    """Downgrade database schema."""
    from sqlalchemy import create_engine, text
    import os

    database_url = os.getenv('DATABASE_URL', 'postgresql://dumont:dumont123@localhost:5432/dumont_cloud')
    engine = create_engine(database_url)

    with engine.connect() as conn:
        conn.execute(text(get_sql_downgrade()))
        conn.commit()
