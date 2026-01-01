"""
Database migration script for the GPU reservation system.

This creates the tables needed for GPU reservations with guaranteed availability:
- reservations: Main reservation records with GPU type, timing, credits, and status
- reservation_credits: Credit tracking with 30-day rollover and expiration

Run with: python -m src.migrations.add_reservation_system
"""
import logging
from sqlalchemy import text, inspect
from src.config.database import engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute database migration to create reservation system tables."""

    conn = engine.connect()
    inspector = inspect(engine)

    try:
        tables = inspector.get_table_names()

        # Create reservations table if not exists
        if 'reservations' not in tables:
            logger.info("Creating reservations table...")
            conn.execute(text("""
                CREATE TABLE reservations (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    gpu_type VARCHAR(100) NOT NULL,
                    gpu_count INTEGER DEFAULT 1 NOT NULL,
                    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                    credits_used FLOAT DEFAULT 0.0 NOT NULL,
                    credits_refunded FLOAT DEFAULT 0.0 NOT NULL,
                    discount_rate INTEGER DEFAULT 15 NOT NULL,
                    spot_price_per_hour FLOAT,
                    reserved_price_per_hour FLOAT,
                    instance_id VARCHAR(100),
                    provider VARCHAR(50),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    cancelled_at TIMESTAMP WITH TIME ZONE,
                    cancellation_reason VARCHAR(500),
                    failure_reason VARCHAR(500)
                )
            """))
            conn.commit()
            logger.info("✓ Created reservations table")

            # Create indexes for reservations table
            logger.info("Creating indexes for reservations table...")

            conn.execute(text("CREATE INDEX idx_reservations_id ON reservations (id)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservations_user_id ON reservations (user_id)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservations_gpu_type ON reservations (gpu_type)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservations_start_time ON reservations (start_time)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservations_end_time ON reservations (end_time)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservations_status ON reservations (status)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservations_instance_id ON reservations (instance_id)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservation_user_status ON reservations (user_id, status)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservation_gpu_time ON reservations (gpu_type, start_time, end_time)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservation_time_range ON reservations (start_time, end_time)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservation_status_time ON reservations (status, start_time)"))
            conn.commit()

            logger.info("✓ Created indexes for reservations table")
        else:
            logger.info("reservations table already exists, skipping creation")

        # Create reservation_credits table if not exists
        if 'reservation_credits' not in tables:
            logger.info("Creating reservation_credits table...")
            conn.execute(text("""
                CREATE TABLE reservation_credits (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    amount FLOAT NOT NULL,
                    original_amount FLOAT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    expired_at TIMESTAMP WITH TIME ZONE,
                    status VARCHAR(20) DEFAULT 'available' NOT NULL,
                    reservation_id INTEGER REFERENCES reservations(id),
                    transaction_type VARCHAR(20) DEFAULT 'purchase' NOT NULL,
                    parent_credit_id INTEGER REFERENCES reservation_credits(id),
                    description VARCHAR(500),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("✓ Created reservation_credits table")

            # Create indexes for reservation_credits table
            logger.info("Creating indexes for reservation_credits table...")

            conn.execute(text("CREATE INDEX idx_reservation_credits_id ON reservation_credits (id)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservation_credits_user_id ON reservation_credits (user_id)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservation_credits_expires_at ON reservation_credits (expires_at)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservation_credits_status ON reservation_credits (status)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_reservation_credits_reservation_id ON reservation_credits (reservation_id)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_credit_user_status ON reservation_credits (user_id, status)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_credit_user_expiration ON reservation_credits (user_id, expires_at)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_credit_status_expiration ON reservation_credits (status, expires_at)"))
            conn.commit()

            conn.execute(text("CREATE INDEX idx_credit_reservation ON reservation_credits (reservation_id)"))
            conn.commit()

            logger.info("✓ Created indexes for reservation_credits table")
        else:
            logger.info("reservation_credits table already exists, skipping creation")

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
