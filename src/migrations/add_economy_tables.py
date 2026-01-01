"""
Database migration script to add economy widget tables.

This adds:
- savings_history table for tracking user savings over time
- provider_pricing table for AWS/GCP/Azure baseline pricing

Run with: python -m src.migrations.add_economy_tables
"""
import logging
from sqlalchemy import text, inspect
from src.config.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute database migration to add economy tables."""

    conn = engine.connect()
    inspector = inspect(engine)

    try:
        tables = inspector.get_table_names()

        # Create savings_history table if not exists
        if 'savings_history' not in tables:
            logger.info("Creating savings_history table...")
            conn.execute(text("""
                CREATE TABLE savings_history (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    snapshot_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    provider VARCHAR(20) NOT NULL DEFAULT 'AWS',
                    period_type VARCHAR(20) NOT NULL DEFAULT 'daily',
                    gpu_type VARCHAR(100) NOT NULL,
                    hours_used FLOAT NOT NULL DEFAULT 0.0,
                    cost_dumont FLOAT NOT NULL DEFAULT 0.0,
                    cost_provider FLOAT NOT NULL DEFAULT 0.0,
                    savings_amount FLOAT NOT NULL DEFAULT 0.0,
                    savings_percentage FLOAT NOT NULL DEFAULT 0.0,
                    usage_record_id INTEGER,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("✓ Created savings_history table")

            # Create indexes
            logger.info("Creating indexes for savings_history...")
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_savings_history_user_id ON savings_history(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_savings_history_snapshot_date ON savings_history(snapshot_date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_savings_history_user_provider ON savings_history(user_id, provider)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_savings_history_user_period ON savings_history(user_id, snapshot_date, period_type)"))
            conn.commit()
            logger.info("✓ Created savings_history indexes")
        else:
            logger.info("savings_history table already exists, skipping...")

        # Create provider_pricing table if not exists
        if 'provider_pricing' not in tables:
            logger.info("Creating provider_pricing table...")
            conn.execute(text("""
                CREATE TABLE provider_pricing (
                    id SERIAL PRIMARY KEY,
                    provider VARCHAR(20) NOT NULL,
                    gpu_type VARCHAR(100) NOT NULL,
                    gpu_name VARCHAR(200),
                    vram_gb INTEGER,
                    price_per_hour FLOAT NOT NULL,
                    instance_type VARCHAR(100),
                    region VARCHAR(50) DEFAULT 'us-east-1',
                    pricing_type VARCHAR(30) DEFAULT 'on-demand',
                    effective_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    effective_until TIMESTAMP,
                    source VARCHAR(200),
                    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT true
                )
            """))
            conn.commit()
            logger.info("✓ Created provider_pricing table")

            # Create indexes
            logger.info("Creating indexes for provider_pricing...")
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_provider_pricing_provider ON provider_pricing(provider)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_provider_pricing_gpu_type ON provider_pricing(gpu_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_provider_pricing_active ON provider_pricing(is_active)"))
            conn.commit()
            logger.info("✓ Created provider_pricing indexes")

            # Seed initial pricing data
            logger.info("Seeding provider pricing data...")
            seed_pricing_data(conn)
            logger.info("✓ Seeded provider pricing data")
        else:
            logger.info("provider_pricing table already exists, skipping...")

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def seed_pricing_data(conn):
    """Seed initial provider pricing data."""

    # AWS pricing
    aws_pricing = [
        ('AWS', 'RTX 4090', 'NVIDIA RTX 4090', 24, 4.50, 'g6.xlarge', 'us-east-1', 'on-demand', 'AWS public pricing'),
        ('AWS', 'A100', 'NVIDIA A100 80GB', 80, 8.50, 'p4d.24xlarge', 'us-east-1', 'on-demand', 'AWS public pricing'),
        ('AWS', 'A10G', 'NVIDIA A10G', 24, 1.50, 'g5.xlarge', 'us-east-1', 'on-demand', 'AWS public pricing'),
        ('AWS', 'H100', 'NVIDIA H100 80GB', 80, 12.00, 'p5.48xlarge', 'us-east-1', 'on-demand', 'AWS public pricing'),
        ('AWS', 'RTX 3090', 'NVIDIA RTX 3090', 24, 3.50, 'g4dn.xlarge', 'us-east-1', 'on-demand', 'AWS public pricing'),
    ]

    # GCP pricing
    gcp_pricing = [
        ('GCP', 'RTX 4090', 'NVIDIA RTX 4090', 24, 4.20, 'n1-standard-8', 'us-central1', 'on-demand', 'GCP public pricing'),
        ('GCP', 'A100', 'NVIDIA A100 80GB', 80, 7.80, 'a2-highgpu-1g', 'us-central1', 'on-demand', 'GCP public pricing'),
        ('GCP', 'A10G', 'NVIDIA A10G', 24, 1.35, 'n1-standard-4', 'us-central1', 'on-demand', 'GCP public pricing'),
        ('GCP', 'H100', 'NVIDIA H100 80GB', 80, 11.00, 'a3-highgpu-8g', 'us-central1', 'on-demand', 'GCP public pricing'),
        ('GCP', 'RTX 3090', 'NVIDIA RTX 3090', 24, 3.20, 'n1-standard-8', 'us-central1', 'on-demand', 'GCP public pricing'),
    ]

    # Azure pricing
    azure_pricing = [
        ('Azure', 'RTX 4090', 'NVIDIA RTX 4090', 24, 4.80, 'NC24ads_A100_v4', 'eastus', 'on-demand', 'Azure public pricing'),
        ('Azure', 'A100', 'NVIDIA A100 80GB', 80, 9.00, 'NC96ads_A100_v4', 'eastus', 'on-demand', 'Azure public pricing'),
        ('Azure', 'A10G', 'NVIDIA A10G', 24, 1.60, 'NC8as_T4_v3', 'eastus', 'on-demand', 'Azure public pricing'),
        ('Azure', 'H100', 'NVIDIA H100 80GB', 80, 13.00, 'NC96ads_H100_v5', 'eastus', 'on-demand', 'Azure public pricing'),
        ('Azure', 'RTX 3090', 'NVIDIA RTX 3090', 24, 3.80, 'NC12s_v3', 'eastus', 'on-demand', 'Azure public pricing'),
    ]

    # Dumont pricing
    dumont_pricing = [
        ('Dumont', 'RTX 4090', 'NVIDIA RTX 4090', 24, 1.14, 'standard', 'global', 'on-demand', 'Dumont Cloud pricing'),
        ('Dumont', 'A100', 'NVIDIA A100 80GB', 80, 2.50, 'standard', 'global', 'on-demand', 'Dumont Cloud pricing'),
        ('Dumont', 'A10G', 'NVIDIA A10G', 24, 0.50, 'standard', 'global', 'on-demand', 'Dumont Cloud pricing'),
        ('Dumont', 'H100', 'NVIDIA H100 80GB', 80, 4.50, 'standard', 'global', 'on-demand', 'Dumont Cloud pricing'),
        ('Dumont', 'RTX 3090', 'NVIDIA RTX 3090', 24, 0.89, 'standard', 'global', 'on-demand', 'Dumont Cloud pricing'),
    ]

    all_pricing = aws_pricing + gcp_pricing + azure_pricing + dumont_pricing

    for pricing in all_pricing:
        conn.execute(text("""
            INSERT INTO provider_pricing
            (provider, gpu_type, gpu_name, vram_gb, price_per_hour, instance_type, region, pricing_type, source)
            VALUES (:provider, :gpu_type, :gpu_name, :vram_gb, :price_per_hour, :instance_type, :region, :pricing_type, :source)
        """), {
            'provider': pricing[0],
            'gpu_type': pricing[1],
            'gpu_name': pricing[2],
            'vram_gb': pricing[3],
            'price_per_hour': pricing[4],
            'instance_type': pricing[5],
            'region': pricing[6],
            'pricing_type': pricing[7],
            'source': pricing[8],
        })

    conn.commit()


if __name__ == "__main__":
    run_migration()
