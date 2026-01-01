"""
Database migration script to add caller location fields to lifecycle events.

This adds:
- caller_file_path to instance_lifecycle_events
- caller_line_number to instance_lifecycle_events

These fields enable complete audit trails showing exactly WHERE (file:line)
status changes were initiated.

Run with: python -m src.migrations.add_caller_location_fields
"""
import logging
from sqlalchemy import text, inspect
from src.config.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute database migration to add caller location fields."""

    conn = engine.connect()
    inspector = inspect(engine)

    try:
        # Check if table exists
        tables = inspector.get_table_names()

        if 'instance_lifecycle_events' in tables:
            columns = [c['name'] for c in inspector.get_columns('instance_lifecycle_events')]

            # Add caller_file_path if not exists
            if 'caller_file_path' not in columns:
                logger.info("Adding caller_file_path to instance_lifecycle_events...")
                conn.execute(text(
                    "ALTER TABLE instance_lifecycle_events ADD COLUMN caller_file_path VARCHAR(500)"
                ))
                conn.commit()
                logger.info("Added caller_file_path")
            else:
                logger.info("caller_file_path already exists, skipping")

            # Add caller_line_number if not exists
            if 'caller_line_number' not in columns:
                logger.info("Adding caller_line_number to instance_lifecycle_events...")
                conn.execute(text(
                    "ALTER TABLE instance_lifecycle_events ADD COLUMN caller_line_number INTEGER"
                ))
                conn.commit()
                logger.info("Added caller_line_number")
            else:
                logger.info("caller_line_number already exists, skipping")
        else:
            logger.warning("Table instance_lifecycle_events does not exist, skipping migration")

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
