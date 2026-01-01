"""
Database migration script to create email-related tables.

This creates:
- email_preferences: User email preferences and subscription settings
- email_delivery_log: Tracking log for sent emails

Run with: python -m src.migrations.add_email_tables
"""
import logging
from sqlalchemy import text, inspect
from src.config.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute database migration to create email tables."""

    conn = engine.connect()
    inspector = inspect(engine)

    try:
        # Check existing tables
        tables = inspector.get_table_names()

        # Create email_preferences table if not exists
        if 'email_preferences' not in tables:
            logger.info("Creating email_preferences table...")
            conn.execute(text("""
                CREATE TABLE email_preferences (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL,
                    frequency VARCHAR(20) NOT NULL DEFAULT 'weekly',
                    unsubscribed BOOLEAN NOT NULL DEFAULT FALSE,
                    unsubscribe_token VARCHAR(100) UNIQUE,
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Created email_preferences table")

            # Create indexes
            logger.info("Creating indexes for email_preferences...")
            conn.execute(text(
                "CREATE INDEX idx_email_preferences_user_id ON email_preferences(user_id)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_preferences_unsubscribe_token ON email_preferences(unsubscribe_token)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_frequency ON email_preferences(frequency, unsubscribed)"
            ))
            conn.commit()
            logger.info("Created indexes for email_preferences")
        else:
            logger.info("email_preferences table already exists, skipping creation")

        # Create email_delivery_log table if not exists
        if 'email_delivery_log' not in tables:
            logger.info("Creating email_delivery_log table...")
            conn.execute(text("""
                CREATE TABLE email_delivery_log (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    email_id VARCHAR(100),
                    report_type VARCHAR(20) NOT NULL DEFAULT 'weekly',
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    week_start TIMESTAMP,
                    week_end TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Created email_delivery_log table")

            # Create indexes
            logger.info("Creating indexes for email_delivery_log...")
            conn.execute(text(
                "CREATE INDEX idx_email_delivery_log_user_id ON email_delivery_log(user_id)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_delivery_log_sent_at ON email_delivery_log(sent_at)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_delivery_log_email_id ON email_delivery_log(email_id)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_delivery_log_status ON email_delivery_log(status)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_user_sent_at ON email_delivery_log(user_id, sent_at)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_status_sent_at ON email_delivery_log(status, sent_at)"
            ))
            conn.commit()
            logger.info("Created indexes for email_delivery_log")
        else:
            logger.info("email_delivery_log table already exists, skipping creation")

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def rollback_migration():
    """Rollback the migration by dropping the email tables."""

    conn = engine.connect()

    try:
        logger.info("Rolling back email tables migration...")

        # Drop tables if they exist (order matters for foreign keys)
        conn.execute(text("DROP TABLE IF EXISTS email_delivery_log CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS email_preferences CASCADE"))
        conn.commit()

        logger.info("Rollback completed successfully!")

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        run_migration()
