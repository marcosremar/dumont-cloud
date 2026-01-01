"""
Database migration script to add SSO support tables.

This creates:
- users table with SSO authentication fields
- sso_configs table for IdP configuration per organization
- sso_user_mappings table for user-IdP identity mappings

Run with: python -m src.migrations.add_sso_support
"""
import logging
from sqlalchemy import text, inspect
from src.config.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute database migration to add SSO support tables."""

    conn = engine.connect()
    inspector = inspect(engine)

    try:
        tables = inspector.get_table_names()

        # Create users table if not exists
        if 'users' not in tables:
            logger.info("Creating users table...")
            conn.execute(text("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255),
                    name VARCHAR(255),
                    vast_api_key VARCHAR(255),
                    settings TEXT,
                    sso_provider VARCHAR(50),
                    sso_external_id VARCHAR(255),
                    sso_enforced BOOLEAN DEFAULT FALSE,
                    last_sso_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_verified BOOLEAN DEFAULT FALSE,
                    organization_id INTEGER,
                    roles VARCHAR(500) DEFAULT 'user',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Created users table")

            # Create indexes for users table
            logger.info("Creating indexes for users table...")
            conn.execute(text("CREATE INDEX ix_users_id ON users (id)"))
            conn.execute(text("CREATE INDEX ix_users_email ON users (email)"))
            conn.execute(text("CREATE INDEX ix_users_sso_provider ON users (sso_provider)"))
            conn.execute(text("CREATE INDEX ix_users_sso_lookup ON users (sso_provider, sso_external_id)"))
            conn.execute(text("CREATE INDEX ix_users_org_active ON users (organization_id, is_active)"))
            conn.commit()
            logger.info("Created indexes for users table")
        else:
            logger.info("Users table already exists, checking for SSO columns...")
            columns = [c['name'] for c in inspector.get_columns('users')]

            # Add SSO columns if they don't exist
            if 'sso_provider' not in columns:
                logger.info("Adding sso_provider to users...")
                conn.execute(text("ALTER TABLE users ADD COLUMN sso_provider VARCHAR(50)"))
                conn.commit()
                logger.info("Added sso_provider")

            if 'sso_external_id' not in columns:
                logger.info("Adding sso_external_id to users...")
                conn.execute(text("ALTER TABLE users ADD COLUMN sso_external_id VARCHAR(255)"))
                conn.commit()
                logger.info("Added sso_external_id")

            if 'sso_enforced' not in columns:
                logger.info("Adding sso_enforced to users...")
                conn.execute(text("ALTER TABLE users ADD COLUMN sso_enforced BOOLEAN DEFAULT FALSE"))
                conn.commit()
                logger.info("Added sso_enforced")

            if 'last_sso_login' not in columns:
                logger.info("Adding last_sso_login to users...")
                conn.execute(text("ALTER TABLE users ADD COLUMN last_sso_login TIMESTAMP"))
                conn.commit()
                logger.info("Added last_sso_login")

            if 'organization_id' not in columns:
                logger.info("Adding organization_id to users...")
                conn.execute(text("ALTER TABLE users ADD COLUMN organization_id INTEGER"))
                conn.commit()
                logger.info("Added organization_id")

            if 'roles' not in columns:
                logger.info("Adding roles to users...")
                conn.execute(text("ALTER TABLE users ADD COLUMN roles VARCHAR(500) DEFAULT 'user'"))
                conn.commit()
                logger.info("Added roles")

            # Try to add SSO lookup index if it doesn't exist
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_sso_lookup ON users (sso_provider, sso_external_id)"))
                conn.commit()
            except Exception:
                pass  # Index may already exist

        # Create sso_configs table if not exists
        if 'sso_configs' not in tables:
            logger.info("Creating sso_configs table...")
            conn.execute(text("""
                CREATE TABLE sso_configs (
                    id SERIAL PRIMARY KEY,
                    organization_id VARCHAR(100) NOT NULL UNIQUE,
                    provider_type VARCHAR(20) NOT NULL,
                    provider_name VARCHAR(50) NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE NOT NULL,
                    client_id VARCHAR(500),
                    client_secret_encrypted TEXT,
                    discovery_url VARCHAR(500),
                    issuer_url VARCHAR(500),
                    scopes VARCHAR(500) DEFAULT 'openid email profile',
                    idp_entity_id VARCHAR(500),
                    idp_sso_url VARCHAR(500),
                    idp_slo_url VARCHAR(500),
                    idp_certificate TEXT,
                    sp_entity_id VARCHAR(500),
                    assertion_consumer_service_url VARCHAR(500),
                    role_mappings TEXT,
                    default_role VARCHAR(50) DEFAULT 'user',
                    group_attribute VARCHAR(100) DEFAULT 'groups',
                    sso_enforced BOOLEAN DEFAULT FALSE,
                    allow_password_fallback BOOLEAN DEFAULT TRUE,
                    allowed_domains VARCHAR(500),
                    domain_verification VARCHAR(500),
                    idp_metadata TEXT,
                    clock_skew_seconds INTEGER DEFAULT 60,
                    session_timeout_minutes INTEGER DEFAULT 480,
                    last_login_at TIMESTAMP,
                    login_count INTEGER DEFAULT 0,
                    last_error VARCHAR(500),
                    last_error_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Created sso_configs table")

            # Create indexes for sso_configs table
            logger.info("Creating indexes for sso_configs table...")
            conn.execute(text("CREATE INDEX ix_sso_configs_id ON sso_configs (id)"))
            conn.execute(text("CREATE INDEX ix_sso_configs_organization_id ON sso_configs (organization_id)"))
            conn.execute(text("CREATE INDEX idx_sso_provider ON sso_configs (provider_type, provider_name)"))
            conn.execute(text("CREATE INDEX idx_sso_enabled ON sso_configs (enabled, sso_enforced)"))
            conn.commit()
            logger.info("Created indexes for sso_configs table")
        else:
            logger.info("sso_configs table already exists")

        # Create sso_user_mappings table if not exists
        if 'sso_user_mappings' not in tables:
            logger.info("Creating sso_user_mappings table...")
            conn.execute(text("""
                CREATE TABLE sso_user_mappings (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    organization_id VARCHAR(100) NOT NULL,
                    sso_provider VARCHAR(50) NOT NULL,
                    sso_external_id VARCHAR(500) NOT NULL,
                    sso_email VARCHAR(255),
                    sso_name VARCHAR(255),
                    sso_groups TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_sync_at TIMESTAMP,
                    provisioned_at TIMESTAMP,
                    deprovisioned_at TIMESTAMP,
                    last_login_at TIMESTAMP,
                    login_count INTEGER DEFAULT 0,
                    current_session_id VARCHAR(100),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Created sso_user_mappings table")

            # Create indexes for sso_user_mappings table
            logger.info("Creating indexes for sso_user_mappings table...")
            conn.execute(text("CREATE INDEX ix_sso_user_mappings_id ON sso_user_mappings (id)"))
            conn.execute(text("CREATE INDEX ix_sso_user_mappings_user_id ON sso_user_mappings (user_id)"))
            conn.execute(text("CREATE INDEX ix_sso_user_mappings_organization_id ON sso_user_mappings (organization_id)"))
            conn.execute(text("CREATE INDEX idx_sso_user_provider ON sso_user_mappings (sso_provider, sso_external_id)"))
            conn.execute(text("CREATE INDEX idx_sso_user_org ON sso_user_mappings (organization_id, user_id)"))
            conn.execute(text("CREATE INDEX idx_sso_user_email ON sso_user_mappings (sso_email)"))
            conn.commit()
            logger.info("Created indexes for sso_user_mappings table")
        else:
            logger.info("sso_user_mappings table already exists")

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
