"""
Database migration script to create shareable_reports table.

This creates the shareable_reports table with columns:
- id (primary key)
- user_id (indexed)
- shareable_id (unique, indexed for public URL lookups)
- config (JSON for report configuration)
- image_url (URL to generated image)
- format (twitter, linkedin, generic)
- savings_data (JSON snapshot of savings at creation time)
- created_at (timestamp)
- expires_at (optional expiration)

Run with: python -m src.migrations.add_shareable_reports
"""
import logging
from sqlalchemy import text, inspect
from src.config.database import engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute database migration to create shareable_reports table."""

    conn = engine.connect()
    inspector = inspect(engine)

    try:
        # Check if table already exists
        tables = inspector.get_table_names()

        if 'shareable_reports' not in tables:
            logger.info("Creating shareable_reports table...")
            conn.execute(text("""
                CREATE TABLE shareable_reports (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    shareable_id VARCHAR(20) NOT NULL UNIQUE,
                    config JSON NOT NULL,
                    image_url VARCHAR(500),
                    format VARCHAR(20) NOT NULL DEFAULT 'generic',
                    savings_data JSON,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("✓ Created shareable_reports table")

            # Create indexes
            logger.info("Creating indexes on shareable_reports...")

            conn.execute(text(
                "CREATE INDEX idx_shareable_reports_user_id ON shareable_reports (user_id)"
            ))
            conn.commit()
            logger.info("✓ Created index on user_id")

            conn.execute(text(
                "CREATE INDEX idx_shareable_reports_shareable_id ON shareable_reports (shareable_id)"
            ))
            conn.commit()
            logger.info("✓ Created index on shareable_id")

            conn.execute(text(
                "CREATE INDEX idx_shareable_reports_created_at ON shareable_reports (created_at)"
            ))
            conn.commit()
            logger.info("✓ Created index on created_at")

            conn.execute(text(
                "CREATE INDEX idx_user_shareable_reports ON shareable_reports (user_id, created_at)"
            ))
            conn.commit()
            logger.info("✓ Created composite index on user_id, created_at")

        else:
            logger.info("Table shareable_reports already exists, skipping creation")

            # Check for any missing columns and add them if needed
            columns = [c['name'] for c in inspector.get_columns('shareable_reports')]

            # Add format column if not exists
            if 'format' not in columns:
                logger.info("Adding format to shareable_reports...")
                conn.execute(text(
                    "ALTER TABLE shareable_reports ADD COLUMN format VARCHAR(20) NOT NULL DEFAULT 'generic'"
                ))
                conn.commit()
                logger.info("✓ Added format")

            # Add savings_data column if not exists
            if 'savings_data' not in columns:
                logger.info("Adding savings_data to shareable_reports...")
                conn.execute(text(
                    "ALTER TABLE shareable_reports ADD COLUMN savings_data JSON"
                ))
                conn.commit()
                logger.info("✓ Added savings_data")

            # Add expires_at column if not exists
            if 'expires_at' not in columns:
                logger.info("Adding expires_at to shareable_reports...")
                conn.execute(text(
                    "ALTER TABLE shareable_reports ADD COLUMN expires_at TIMESTAMP"
                ))
                conn.commit()
                logger.info("✓ Added expires_at")

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
