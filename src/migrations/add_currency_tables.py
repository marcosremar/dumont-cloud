"""
Database migration script to add currency tables for multi-currency pricing.

This creates:
- exchange_rates: Stores daily exchange rates from USD to EUR, GBP, BRL
- user_currency_preferences: Stores user's preferred display currency

Run with: python -m src.migrations.add_currency_tables
"""
import logging
from sqlalchemy import text, inspect
from src.config.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute database migration to add currency tables."""

    conn = engine.connect()
    inspector = inspect(engine)

    try:
        tables = inspector.get_table_names()

        # Create exchange_rates table if not exists
        if 'exchange_rates' not in tables:
            logger.info("Creating exchange_rates table...")
            conn.execute(text("""
                CREATE TABLE exchange_rates (
                    id SERIAL PRIMARY KEY,
                    from_currency VARCHAR(3) NOT NULL,
                    to_currency VARCHAR(3) NOT NULL,
                    rate NUMERIC(18, 6) NOT NULL,
                    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Created exchange_rates table")

            # Create indexes for exchange_rates
            logger.info("Creating indexes for exchange_rates...")
            conn.execute(text("""
                CREATE INDEX idx_exchange_rates_from_currency
                ON exchange_rates (from_currency)
            """))
            conn.commit()

            conn.execute(text("""
                CREATE INDEX idx_exchange_rates_to_currency
                ON exchange_rates (to_currency)
            """))
            conn.commit()

            conn.execute(text("""
                CREATE INDEX idx_latest_rate
                ON exchange_rates (from_currency, to_currency, fetched_at)
            """))
            conn.commit()

            conn.execute(text("""
                CREATE INDEX idx_exchange_rate_fetched
                ON exchange_rates (fetched_at)
            """))
            conn.commit()
            logger.info("Created indexes for exchange_rates")
        else:
            logger.info("exchange_rates table already exists, skipping creation")

        # Create user_currency_preferences table if not exists
        if 'user_currency_preferences' not in tables:
            logger.info("Creating user_currency_preferences table...")
            conn.execute(text("""
                CREATE TABLE user_currency_preferences (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL UNIQUE,
                    currency_code VARCHAR(3) NOT NULL DEFAULT 'USD',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Created user_currency_preferences table")

            # Create indexes for user_currency_preferences
            logger.info("Creating indexes for user_currency_preferences...")
            conn.execute(text("""
                CREATE INDEX idx_user_currency_email
                ON user_currency_preferences (user_email)
            """))
            conn.commit()
            logger.info("Created indexes for user_currency_preferences")
        else:
            logger.info("user_currency_preferences table already exists, skipping creation")

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
