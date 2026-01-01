"""
Migration 002: Create Referral Tables

Creates the database tables for the referral and affiliate program:
- referral_codes: Unique referral codes per user
- referrals: Referral relationships (who referred whom)
- credit_transactions: Immutable credit ledger
- affiliate_tracking: Daily affiliate metrics

Run with: python src/migrations/002_create_referral_tables.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import logging
from sqlalchemy import text, inspect
from src.config.database import engine, Base
from src.models.referral import (
    ReferralCode,
    Referral,
    CreditTransaction,
    AffiliateTracking,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_exists(inspector, table_name: str) -> bool:
    """Check if a table already exists in the database."""
    return table_name in inspector.get_table_names()


def create_tables():
    """Create all referral tables if they don't exist."""
    inspector = inspect(engine)

    # Define tables to create in order (respecting foreign key dependencies)
    tables = [
        ("referral_codes", ReferralCode.__table__),
        ("referrals", Referral.__table__),
        ("credit_transactions", CreditTransaction.__table__),
        ("affiliate_tracking", AffiliateTracking.__table__),
    ]

    for table_name, table in tables:
        if check_table_exists(inspector, table_name):
            logger.info(f"Table '{table_name}' already exists, skipping...")
        else:
            logger.info(f"Creating table '{table_name}'...")
            table.create(engine, checkfirst=True)
            logger.info(f"  Created table '{table_name}'")


def verify_tables():
    """Verify all tables were created with correct columns."""
    inspector = inspect(engine)

    expected_tables = {
        "referral_codes": [
            "id", "user_id", "code", "is_active", "total_clicks",
            "total_signups", "total_conversions", "total_earnings",
            "created_at", "last_used_at", "expires_at"
        ],
        "referrals": [
            "id", "referrer_id", "referred_id", "referral_code_id", "status",
            "email_verified", "email_verified_at", "referred_total_spend",
            "spend_threshold", "threshold_reached_at", "referrer_reward_amount",
            "referred_welcome_credit", "reward_granted", "reward_granted_at",
            "welcome_credit_granted", "welcome_credit_granted_at",
            "referrer_ip", "referred_ip", "is_suspicious", "fraud_reason",
            "created_at", "updated_at"
        ],
        "credit_transactions": [
            "id", "user_id", "transaction_type", "amount", "balance_before",
            "balance_after", "referral_id", "reference_id", "reference_type",
            "description", "created_by", "ip_address", "created_at"
        ],
        "affiliate_tracking": [
            "id", "affiliate_id", "referral_code_id", "tracking_date",
            "clicks", "unique_clicks", "signups", "verified_signups",
            "conversions", "revenue_generated", "credits_earned",
            "credits_pending", "credits_paid", "created_at", "updated_at"
        ],
    }

    all_verified = True

    for table_name, expected_columns in expected_tables.items():
        if not check_table_exists(inspector, table_name):
            logger.error(f"Table '{table_name}' does not exist!")
            all_verified = False
            continue

        actual_columns = [c["name"] for c in inspector.get_columns(table_name)]
        missing_columns = set(expected_columns) - set(actual_columns)

        if missing_columns:
            logger.error(f"Table '{table_name}' is missing columns: {missing_columns}")
            all_verified = False
        else:
            logger.info(f"  Verified table '{table_name}' ({len(actual_columns)} columns)")

    return all_verified


def verify_indexes():
    """Verify indexes were created."""
    inspector = inspect(engine)

    tables_to_check = ["referral_codes", "referrals", "credit_transactions", "affiliate_tracking"]

    for table_name in tables_to_check:
        if not check_table_exists(inspector, table_name):
            continue

        indexes = inspector.get_indexes(table_name)
        logger.info(f"  Table '{table_name}' has {len(indexes)} indexes")


def verify_foreign_keys():
    """Verify foreign keys were created."""
    inspector = inspect(engine)

    # Check referrals table has FK to referral_codes
    if check_table_exists(inspector, "referrals"):
        fks = inspector.get_foreign_keys("referrals")
        if fks:
            logger.info(f"  Table 'referrals' has {len(fks)} foreign key(s)")
        else:
            logger.warning("  Table 'referrals' has no foreign keys")

    # Check credit_transactions table has FK to referrals
    if check_table_exists(inspector, "credit_transactions"):
        fks = inspector.get_foreign_keys("credit_transactions")
        if fks:
            logger.info(f"  Table 'credit_transactions' has {len(fks)} foreign key(s)")

    # Check affiliate_tracking table has FK to referral_codes
    if check_table_exists(inspector, "affiliate_tracking"):
        fks = inspector.get_foreign_keys("affiliate_tracking")
        if fks:
            logger.info(f"  Table 'affiliate_tracking' has {len(fks)} foreign key(s)")


def run_migration():
    """Execute the complete migration."""
    print("\n" + "=" * 60)
    print("  MIGRATION 002: Create Referral Tables")
    print("=" * 60 + "\n")

    try:
        # Step 1: Create tables
        logger.info("Step 1: Creating tables...")
        create_tables()
        print()

        # Step 2: Verify tables and columns
        logger.info("Step 2: Verifying tables and columns...")
        tables_ok = verify_tables()
        print()

        # Step 3: Verify indexes
        logger.info("Step 3: Verifying indexes...")
        verify_indexes()
        print()

        # Step 4: Verify foreign keys
        logger.info("Step 4: Verifying foreign keys...")
        verify_foreign_keys()
        print()

        if tables_ok:
            print("=" * 60)
            print("  MIGRATION COMPLETE")
            print("=" * 60)
            logger.info("Migration completed successfully!")
            return True
        else:
            logger.error("Migration completed with errors")
            return False

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
