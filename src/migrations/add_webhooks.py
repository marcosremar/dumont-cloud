"""
Database migration script to create webhook configuration and log tables.

This creates:
- webhook_configs: Stores user webhook configurations
- webhook_logs: Stores webhook delivery attempts and results

Run with: python -m src.migrations.add_webhooks
"""
import logging
from sqlalchemy import text, inspect
from src.config.database import engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_webhook_tables():
    """Create webhook tables using SQLAlchemy models."""
    # Import models to register them with Base.metadata
    from src.models.webhook_config import WebhookConfig, WebhookLog

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    tables_to_create = []

    # Check if webhook_configs table exists
    if 'webhook_configs' not in tables:
        tables_to_create.append('webhook_configs')

    # Check if webhook_logs table exists
    if 'webhook_logs' not in tables:
        tables_to_create.append('webhook_logs')

    if tables_to_create:
        logger.info(f"Creating tables: {', '.join(tables_to_create)}")

        # Create only the webhook tables (not all tables)
        # This ensures we don't interfere with other models
        Base.metadata.create_all(
            bind=engine,
            tables=[
                WebhookConfig.__table__,
                WebhookLog.__table__
            ]
        )

        logger.info(f"Successfully created webhook tables: {', '.join(tables_to_create)}")
    else:
        logger.info("Webhook tables already exist, skipping creation")

    return tables_to_create


def run_migration():
    """Execute database migration to create webhook tables."""
    conn = engine.connect()
    inspector = inspect(engine)

    try:
        # Create tables using SQLAlchemy models
        created_tables = create_webhook_tables()

        # Verify tables were created
        tables = inspector.get_table_names()

        if 'webhook_configs' in tables:
            logger.info("Verified: webhook_configs table exists")
            columns = [c['name'] for c in inspector.get_columns('webhook_configs')]
            logger.info(f"  Columns: {', '.join(columns)}")

        if 'webhook_logs' in tables:
            logger.info("Verified: webhook_logs table exists")
            columns = [c['name'] for c in inspector.get_columns('webhook_logs')]
            logger.info(f"  Columns: {', '.join(columns)}")

        # Verify indexes
        if 'webhook_configs' in tables:
            indexes = inspector.get_indexes('webhook_configs')
            index_names = [idx['name'] for idx in indexes]
            logger.info(f"  Indexes on webhook_configs: {', '.join(index_names)}")

        if 'webhook_logs' in tables:
            indexes = inspector.get_indexes('webhook_logs')
            index_names = [idx['name'] for idx in indexes]
            logger.info(f"  Indexes on webhook_logs: {', '.join(index_names)}")

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
