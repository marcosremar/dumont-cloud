"""
Database migration script to add tables for reliability scoring.

This adds:
- user_machine_ratings table for user ratings of machines
- machine_uptime_history table for daily uptime tracking

Run with: python -m src.migrations.add_reliability_models
"""
import logging
from sqlalchemy import text, inspect
from src.config.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute database migration to add reliability model tables."""

    conn = engine.connect()
    inspector = inspect(engine)

    try:
        # Check existing tables
        tables = inspector.get_table_names()

        # ================================================================
        # Create user_machine_ratings table
        # ================================================================
        if 'user_machine_ratings' not in tables:
            logger.info("Creating user_machine_ratings table...")
            conn.execute(text("""
                CREATE TABLE user_machine_ratings (
                    id SERIAL PRIMARY KEY,
                    provider VARCHAR(50) NOT NULL,
                    machine_id VARCHAR(100) NOT NULL,
                    user_id VARCHAR(100) NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    rental_duration_hours FLOAT,
                    instance_id VARCHAR(100),
                    gpu_name VARCHAR(100),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("  Created user_machine_ratings table")

            # Create indexes for user_machine_ratings
            logger.info("Creating indexes for user_machine_ratings...")

            conn.execute(text("""
                CREATE INDEX idx_rating_provider_machine
                ON user_machine_ratings (provider, machine_id)
            """))
            conn.commit()

            conn.execute(text("""
                CREATE INDEX idx_rating_user
                ON user_machine_ratings (user_id)
            """))
            conn.commit()

            conn.execute(text("""
                CREATE INDEX idx_rating_created
                ON user_machine_ratings (created_at)
            """))
            conn.commit()

            conn.execute(text("""
                CREATE UNIQUE INDEX idx_rating_unique_user_machine
                ON user_machine_ratings (provider, machine_id, user_id)
            """))
            conn.commit()

            logger.info("  Created all indexes for user_machine_ratings")
        else:
            logger.info("user_machine_ratings table already exists, skipping...")

        # ================================================================
        # Create machine_uptime_history table
        # ================================================================
        if 'machine_uptime_history' not in tables:
            logger.info("Creating machine_uptime_history table...")
            conn.execute(text("""
                CREATE TABLE machine_uptime_history (
                    id SERIAL PRIMARY KEY,
                    provider VARCHAR(50) NOT NULL,
                    machine_id VARCHAR(100) NOT NULL,
                    date TIMESTAMP NOT NULL,
                    uptime_percentage FLOAT NOT NULL DEFAULT 0.0,
                    uptime_seconds INTEGER,
                    total_seconds INTEGER,
                    interruption_count INTEGER DEFAULT 0,
                    avg_interruption_duration_seconds FLOAT,
                    total_attempts INTEGER DEFAULT 0,
                    successful_attempts INTEGER DEFAULT 0,
                    failed_attempts INTEGER DEFAULT 0,
                    gpu_name VARCHAR(100),
                    price_per_hour FLOAT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("  Created machine_uptime_history table")

            # Create indexes for machine_uptime_history
            logger.info("Creating indexes for machine_uptime_history...")

            conn.execute(text("""
                CREATE INDEX idx_uptime_history_provider_machine_date
                ON machine_uptime_history (provider, machine_id, date)
            """))
            conn.commit()

            conn.execute(text("""
                CREATE UNIQUE INDEX idx_uptime_history_unique_day
                ON machine_uptime_history (provider, machine_id, date)
            """))
            conn.commit()

            conn.execute(text("""
                CREATE INDEX idx_uptime_history_date
                ON machine_uptime_history (date)
            """))
            conn.commit()

            conn.execute(text("""
                CREATE INDEX idx_uptime_history_provider
                ON machine_uptime_history (provider)
            """))
            conn.commit()

            conn.execute(text("""
                CREATE INDEX idx_uptime_history_machine_id
                ON machine_uptime_history (machine_id)
            """))
            conn.commit()

            logger.info("  Created all indexes for machine_uptime_history")
        else:
            logger.info("machine_uptime_history table already exists, skipping...")

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
