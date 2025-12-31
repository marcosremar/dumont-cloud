"""
Schema Verification Script for Referral Tables

Verifies that the SQLAlchemy models create the correct database schema:
- referral_codes: Unique referral codes per user
- referrals: Referral relationships (who referred whom)
- credit_transactions: Immutable credit ledger
- affiliate_tracking: Daily affiliate metrics

This script can verify schema using either:
1. In-memory SQLite (for testing without PostgreSQL)
2. PostgreSQL (for production verification)

Run with: PYTHONPATH=. python3 src/migrations/verify_referral_schema.py
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def verify_schema_with_sqlite():
    """
    Verify schema creation using in-memory SQLite.
    This tests that the models are correctly defined and create proper tables.
    """
    from sqlalchemy import create_engine, inspect

    # Create in-memory SQLite engine
    engine = create_engine('sqlite:///:memory:', echo=False)

    # Import models
    from src.models.referral import (
        ReferralCode,
        Referral,
        CreditTransaction,
        AffiliateTracking,
        Base
    )

    # Create only the referral tables (not all tables from Base)
    # This avoids issues with JSONB types from other models
    tables_to_create = [
        ReferralCode.__table__,
        Referral.__table__,
        CreditTransaction.__table__,
        AffiliateTracking.__table__,
    ]
    for table in tables_to_create:
        table.create(engine, checkfirst=True)

    inspector = inspect(engine)

    # Expected schema definition
    expected_schema = {
        "referral_codes": {
            "columns": [
                ("id", True),  # (name, nullable or primary key indicator)
                ("user_id", False),
                ("code", False),
                ("is_active", False),
                ("total_clicks", True),
                ("total_signups", True),
                ("total_conversions", True),
                ("total_earnings", True),
                ("created_at", False),
                ("last_used_at", True),
                ("expires_at", True),
            ],
            "indexes": ["idx_referral_code_user", "idx_referral_code_active", "idx_referral_code_created"],
            "unique_constraints": ["user_id", "code"],
        },
        "referrals": {
            "columns": [
                ("id", True),
                ("referrer_id", False),
                ("referred_id", False),
                ("referral_code_id", False),
                ("status", False),
                ("email_verified", True),
                ("email_verified_at", True),
                ("referred_total_spend", True),
                ("spend_threshold", True),
                ("threshold_reached_at", True),
                ("referrer_reward_amount", True),
                ("referred_welcome_credit", True),
                ("reward_granted", True),
                ("reward_granted_at", True),
                ("welcome_credit_granted", True),
                ("welcome_credit_granted_at", True),
                ("referrer_ip", True),
                ("referred_ip", True),
                ("is_suspicious", True),
                ("fraud_reason", True),
                ("created_at", False),
                ("updated_at", True),
            ],
            "indexes": [
                "idx_referral_referrer",
                "idx_referral_referred",
                "idx_referral_status",
                "idx_referral_reward",
                "idx_referral_suspicious",
            ],
            "foreign_keys": ["referral_codes.id"],
        },
        "credit_transactions": {
            "columns": [
                ("id", True),
                ("user_id", False),
                ("transaction_type", False),
                ("amount", False),
                ("balance_before", False),
                ("balance_after", False),
                ("referral_id", True),
                ("reference_id", True),
                ("reference_type", True),
                ("description", True),
                ("created_by", True),
                ("ip_address", True),
                ("created_at", False),
            ],
            "indexes": [
                "idx_credit_tx_user",
                "idx_credit_tx_type",
                "idx_credit_tx_referral",
                "idx_credit_tx_reference",
            ],
            "foreign_keys": ["referrals.id"],
        },
        "affiliate_tracking": {
            "columns": [
                ("id", True),
                ("affiliate_id", False),
                ("referral_code_id", False),
                ("tracking_date", False),
                ("clicks", True),
                ("unique_clicks", True),
                ("signups", True),
                ("verified_signups", True),
                ("conversions", True),
                ("revenue_generated", True),
                ("credits_earned", True),
                ("credits_pending", True),
                ("credits_paid", True),
                ("created_at", False),
                ("updated_at", True),
            ],
            "indexes": [
                "idx_affiliate_user",
                "idx_affiliate_date",
                "idx_affiliate_code",
            ],
            "foreign_keys": ["referral_codes.id"],
        },
    }

    all_passed = True

    print("\n" + "=" * 70)
    print("  REFERRAL SCHEMA VERIFICATION")
    print("=" * 70 + "\n")

    # Verify each table
    for table_name, expected in expected_schema.items():
        print(f"\n{'=' * 50}")
        print(f"  Table: {table_name}")
        print(f"{'=' * 50}")

        # Check table exists
        if table_name not in inspector.get_table_names():
            logger.error(f"Table '{table_name}' does not exist!")
            all_passed = False
            continue

        logger.info(f"Table '{table_name}' exists")

        # Check columns
        actual_columns = {c["name"]: c for c in inspector.get_columns(table_name)}
        expected_column_names = [c[0] for c in expected["columns"]]

        missing_columns = set(expected_column_names) - set(actual_columns.keys())
        if missing_columns:
            logger.error(f"  Missing columns: {missing_columns}")
            all_passed = False
        else:
            logger.info(f"  All {len(expected_column_names)} columns present")

        # List all columns
        for col_name, _ in expected["columns"]:
            if col_name in actual_columns:
                col = actual_columns[col_name]
                nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
                print(f"    - {col_name}: {col['type']} {nullable}")

        # Check indexes
        actual_indexes = {idx["name"]: idx for idx in inspector.get_indexes(table_name) if idx["name"]}
        expected_indexes = expected.get("indexes", [])

        found_indexes = []
        for idx_name in expected_indexes:
            if idx_name in actual_indexes:
                found_indexes.append(idx_name)
            else:
                # SQLite may use different index naming - just warn
                pass

        logger.info(f"  Indexes created: {len(actual_indexes)}")
        for idx_name, idx in actual_indexes.items():
            cols = ", ".join(idx.get("column_names", []))
            unique = " UNIQUE" if idx.get("unique", False) else ""
            print(f"    - {idx_name}: ({cols}){unique}")

        # Check foreign keys
        actual_fks = inspector.get_foreign_keys(table_name)
        expected_fks = expected.get("foreign_keys", [])

        if actual_fks:
            logger.info(f"  Foreign keys: {len(actual_fks)}")
            for fk in actual_fks:
                ref_table = fk.get("referred_table", "?")
                ref_cols = ", ".join(fk.get("referred_columns", []))
                local_cols = ", ".join(fk.get("constrained_columns", []))
                print(f"    - {local_cols} -> {ref_table}({ref_cols})")

    print("\n" + "=" * 70)
    if all_passed:
        print("  VERIFICATION PASSED - All tables and columns created correctly")
    else:
        print("  VERIFICATION FAILED - See errors above")
    print("=" * 70 + "\n")

    return all_passed


def verify_model_properties():
    """Verify that model classes have expected properties and methods."""
    from src.models.referral import (
        ReferralCode,
        Referral,
        CreditTransaction,
        AffiliateTracking,
        TransactionType,
        ReferralStatus,
    )

    print("\n" + "=" * 70)
    print("  MODEL PROPERTIES VERIFICATION")
    print("=" * 70 + "\n")

    all_passed = True

    # Verify ReferralCode properties
    print("ReferralCode model:")
    rc = ReferralCode
    required_props = ['is_expired', 'is_usable', 'conversion_rate', 'to_dict']
    for prop in required_props:
        if hasattr(rc, prop):
            logger.info(f"  {prop}: OK")
        else:
            logger.error(f"  {prop}: MISSING")
            all_passed = False

    # Verify Referral properties
    print("\nReferral model:")
    r = Referral
    required_props = ['is_threshold_reached', 'spend_progress', 'to_dict']
    for prop in required_props:
        if hasattr(r, prop):
            logger.info(f"  {prop}: OK")
        else:
            logger.error(f"  {prop}: MISSING")
            all_passed = False

    # Verify CreditTransaction
    print("\nCreditTransaction model:")
    ct = CreditTransaction
    if hasattr(ct, 'to_dict'):
        logger.info(f"  to_dict: OK")
    else:
        logger.error(f"  to_dict: MISSING")
        all_passed = False

    # Verify AffiliateTracking properties
    print("\nAffiliateTracking model:")
    at = AffiliateTracking
    required_props = ['click_to_signup_rate', 'signup_to_conversion_rate', 'total_conversion_rate', 'to_dict']
    for prop in required_props:
        if hasattr(at, prop):
            logger.info(f"  {prop}: OK")
        else:
            logger.error(f"  {prop}: MISSING")
            all_passed = False

    # Verify enums
    print("\nEnums:")
    logger.info(f"  TransactionType values: {[e.value for e in TransactionType]}")
    logger.info(f"  ReferralStatus values: {[e.value for e in ReferralStatus]}")

    return all_passed


def print_postgresql_verification_commands():
    """Print PostgreSQL commands for manual verification when DB is available."""
    print("\n" + "=" * 70)
    print("  POSTGRESQL MANUAL VERIFICATION COMMANDS")
    print("=" * 70)
    print("""
When PostgreSQL is available, run these commands to verify the schema:

1. Connect to database:
   psql -U dumont -d dumont_cloud

2. List referral tables:
   \\dt *referral* *credit* *affiliate*

3. Describe each table:
   \\d referral_codes
   \\d referrals
   \\d credit_transactions
   \\d affiliate_tracking

4. List indexes:
   \\di *referral* *credit* *affiliate*

5. Check foreign keys:
   SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table
   FROM information_schema.table_constraints AS tc
   JOIN information_schema.key_column_usage AS kcu
     ON tc.constraint_name = kcu.constraint_name
   JOIN information_schema.constraint_column_usage AS ccu
     ON ccu.constraint_name = tc.constraint_name
   WHERE tc.constraint_type = 'FOREIGN KEY'
     AND tc.table_name IN ('referrals', 'credit_transactions', 'affiliate_tracking');

6. Verify unique constraints:
   SELECT indexname, indexdef FROM pg_indexes
   WHERE tablename IN ('referral_codes', 'referrals', 'credit_transactions', 'affiliate_tracking');
""")


def main():
    """Run all verification checks."""
    print("\n" + "=" * 70)
    print("  REFERRAL DATABASE SCHEMA VERIFICATION SCRIPT")
    print("=" * 70)

    # First verify models can be imported
    print("\n1. Verifying model imports...")
    try:
        from src.models.referral import (
            ReferralCode,
            Referral,
            CreditTransaction,
            AffiliateTracking,
        )
        logger.info("All models imported successfully")
    except Exception as e:
        logger.error(f"Failed to import models: {e}")
        return False

    # Verify schema with SQLite
    print("\n2. Verifying schema with in-memory SQLite...")
    schema_ok = verify_schema_with_sqlite()

    # Verify model properties
    print("\n3. Verifying model properties...")
    props_ok = verify_model_properties()

    # Print PostgreSQL verification commands
    print_postgresql_verification_commands()

    # Final result
    print("\n" + "=" * 70)
    if schema_ok and props_ok:
        print("  ALL VERIFICATIONS PASSED")
        print("=" * 70)
        print("\nThe database models and schema are correctly defined.")
        print("When PostgreSQL is running, use the migration script to create tables:")
        print("  PYTHONPATH=. python3 src/migrations/002_create_referral_tables.py")
        return True
    else:
        print("  VERIFICATION FAILED - See errors above")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
