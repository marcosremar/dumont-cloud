#!/usr/bin/env python3
"""
End-to-End Integration Test for Full Referral Flow

Tests the complete referral flow:
1. User A logs in and gets referral code
2. User B signs up with User A's code
3. Verify User B receives $10 credit (after email verification)
4. Simulate User B spending $50
5. Verify User A receives $25 credit
6. Check affiliate dashboard shows correct metrics

Usage:
    pytest tests/backend/e2e/test_referral_flow_e2e.py -v
"""

import os
import sys
import pytest
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Use SQLite for isolated testing
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config.database import Base
from src.models.referral import (
    ReferralCode, Referral, CreditTransaction, AffiliateTracking,
    TransactionType, ReferralStatus
)
from src.services.referral_service import ReferralService
from src.services.credit_service import CreditService, EmailNotVerifiedError
from src.services.spend_monitor_service import SpendMonitorService
from src.services.affiliate_service import AffiliateService


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    # Create engine with in-memory SQLite
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create only referral-related tables (avoid JSONB issues with other tables)
    from src.models.referral import (
        ReferralCode, Referral, CreditTransaction, AffiliateTracking
    )
    tables_to_create = [
        ReferralCode.__table__,
        Referral.__table__,
        CreditTransaction.__table__,
        AffiliateTracking.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables_to_create)

    # Create session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create session
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def referral_service(test_db):
    """Create ReferralService with test database."""
    return ReferralService(test_db)


@pytest.fixture
def credit_service(test_db):
    """Create CreditService with test database."""
    return CreditService(test_db)


@pytest.fixture
def spend_monitor_service(test_db):
    """Create SpendMonitorService with test database."""
    return SpendMonitorService(test_db)


@pytest.fixture
def affiliate_service(test_db):
    """Create AffiliateService with test database."""
    return AffiliateService(test_db)


# =============================================================================
# E2E TEST: FULL REFERRAL FLOW
# =============================================================================

class TestReferralFlowE2E:
    """End-to-end tests for the complete referral flow."""

    # Test user IDs
    USER_A_ID = "user-a-referrer-123"
    USER_B_ID = "user-b-referred-456"
    USER_C_ID = "user-c-another-789"

    def test_complete_referral_flow(
        self,
        test_db,
        referral_service,
        credit_service,
        spend_monitor_service,
        affiliate_service
    ):
        """
        Test the complete referral flow from code generation to reward.

        Steps:
        1. User A gets referral code
        2. User B signs up with User A's code
        3. Verify referral relationship created
        4. Verify email, User B receives $10 credit
        5. Simulate User B spending $50
        6. Verify User A receives $25 credit
        7. Check affiliate dashboard metrics
        """

        # =====================================================================
        # STEP 1: User A logs in and gets referral code
        # =====================================================================
        print("\n=== STEP 1: User A gets referral code ===")

        # Generate referral code for User A
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)

        assert user_a_code is not None, "Referral code should be created"
        assert user_a_code.code is not None, "Code should have a value"
        assert len(user_a_code.code) >= 8, "Code should be at least 8 characters"
        assert len(user_a_code.code) <= 12, "Code should be at most 12 characters"
        assert user_a_code.is_active, "Code should be active"
        assert user_a_code.is_usable, "Code should be usable"
        assert user_a_code.user_id == self.USER_A_ID, "Code should belong to User A"
        assert user_a_code.total_signups == 0, "No signups yet"
        assert user_a_code.total_conversions == 0, "No conversions yet"

        print(f"✓ User A referral code: {user_a_code.code}")

        # =====================================================================
        # STEP 2: User B signs up with User A's code
        # =====================================================================
        print("\n=== STEP 2: User B signs up with User A's code ===")

        # Record a click on the referral code (simulating link click)
        click_recorded = referral_service.record_click(user_a_code.code)
        assert click_recorded, "Click should be recorded"

        # Refresh to see updated stats
        test_db.refresh(user_a_code)
        assert user_a_code.total_clicks == 1, "Total clicks should be 1"

        # Apply referral code for User B (skip fraud check for testing)
        apply_result = referral_service.apply_code(
            referred_user_id=self.USER_B_ID,
            code=user_a_code.code,
            referred_ip="192.168.1.100",
            skip_fraud_check=True
        )

        assert apply_result["success"], f"Apply should succeed: {apply_result.get('error')}"
        assert apply_result["referral"] is not None, "Referral object should be created"
        assert apply_result["welcome_credit"] == 10.0, "Welcome credit should be $10"

        referral = apply_result["referral"]
        assert referral.referrer_id == self.USER_A_ID, "Referrer should be User A"
        assert referral.referred_id == self.USER_B_ID, "Referred should be User B"
        assert referral.status == ReferralStatus.PENDING.value, "Status should be pending"
        assert not referral.email_verified, "Email should not be verified yet"
        assert not referral.welcome_credit_granted, "Welcome credit not granted yet"
        assert not referral.reward_granted, "Referrer reward not granted yet"

        # Refresh referral code stats
        test_db.refresh(user_a_code)
        assert user_a_code.total_signups == 1, "Total signups should be 1"

        print(f"✓ User B referred by User A, referral ID: {referral.id}")

        # =====================================================================
        # STEP 3: Verify User B receives $10 credit after email verification
        # =====================================================================
        print("\n=== STEP 3: Verify User B receives $10 credit ===")

        # Before email verification, User B should have $0 balance
        user_b_balance_before = credit_service.get_balance(self.USER_B_ID)
        assert user_b_balance_before == 0.0, "User B should have $0 before verification"

        # Simulate email verification
        referral.email_verified = True
        referral.email_verified_at = datetime.utcnow()
        test_db.commit()

        # Grant welcome credit after verification
        welcome_tx = credit_service.grant_welcome_credit(referral)

        assert welcome_tx is not None, "Welcome credit transaction should be created"
        assert welcome_tx.amount == 10.0, "Welcome credit should be $10"
        assert welcome_tx.transaction_type == TransactionType.WELCOME_CREDIT.value
        assert welcome_tx.balance_after == 10.0, "Balance should be $10 after welcome credit"

        # Verify User B's new balance
        user_b_balance_after = credit_service.get_balance(self.USER_B_ID)
        assert user_b_balance_after == 10.0, "User B should have $10 after welcome credit"

        # Refresh referral to verify state
        test_db.refresh(referral)
        assert referral.welcome_credit_granted, "Welcome credit should be marked as granted"
        assert referral.status == ReferralStatus.ACTIVE.value, "Status should be active"

        print(f"✓ User B received $10 welcome credit, balance: ${user_b_balance_after}")

        # =====================================================================
        # STEP 4: Simulate User B spending $50
        # =====================================================================
        print("\n=== STEP 4: Simulate User B spending $50 ===")

        # Check initial spend status
        initial_status = spend_monitor_service.check_threshold_for_user(self.USER_B_ID)
        assert initial_status["is_referred"], "User B should be marked as referred"
        assert initial_status["total_spend"] == 0.0, "Initial spend should be $0"
        assert not initial_status["threshold_reached"], "Threshold not reached initially"

        # Record first spend: $25
        spend_result_1 = spend_monitor_service.record_spend(
            user_id=self.USER_B_ID,
            amount=25.0,
            reference_id="billing-001",
            reference_type="billing"
        )

        assert spend_result_1["success"], "First spend should succeed"
        assert spend_result_1["is_referred"], "User B is referred"
        assert spend_result_1["new_spend"] == 25.0, "New spend should be $25"
        assert not spend_result_1["threshold_reached"], "Threshold not reached yet"
        assert not spend_result_1["referrer_rewarded"], "Referrer not rewarded yet"

        print(f"✓ User B spent $25, total: ${spend_result_1['new_spend']}")

        # Record second spend: $25 more (total $50 - reaches threshold)
        spend_result_2 = spend_monitor_service.record_spend(
            user_id=self.USER_B_ID,
            amount=25.0,
            reference_id="billing-002",
            reference_type="billing"
        )

        assert spend_result_2["success"], "Second spend should succeed"
        assert spend_result_2["new_spend"] == 50.0, "New spend should be $50"
        assert spend_result_2["threshold_reached"], "Threshold should be reached"
        assert spend_result_2["threshold_just_crossed"], "Threshold just crossed"
        assert spend_result_2["referrer_rewarded"], "Referrer should be rewarded"

        print(f"✓ User B spent $25 more, total: ${spend_result_2['new_spend']} (threshold reached)")

        # =====================================================================
        # STEP 5: Verify User A receives $25 credit
        # =====================================================================
        print("\n=== STEP 5: Verify User A receives $25 credit ===")

        # Check User A's balance
        user_a_balance = credit_service.get_balance(self.USER_A_ID)
        assert user_a_balance == 25.0, f"User A should have $25, got ${user_a_balance}"

        # Verify the reward transaction was created
        user_a_transactions = credit_service.get_transaction_history(self.USER_A_ID)
        assert len(user_a_transactions) == 1, "User A should have 1 transaction"

        reward_tx = user_a_transactions[0]
        assert reward_tx.amount == 25.0, "Reward should be $25"
        assert reward_tx.transaction_type == TransactionType.REFERRAL_BONUS.value
        assert reward_tx.referral_id == referral.id, "Should reference correct referral"

        # Refresh referral to verify state
        test_db.refresh(referral)
        assert referral.reward_granted, "Reward should be marked as granted"
        assert referral.reward_granted_at is not None, "Reward timestamp should be set"
        assert referral.status == ReferralStatus.COMPLETED.value, "Status should be completed"

        # Refresh code to check conversion stats
        test_db.refresh(user_a_code)
        assert user_a_code.total_conversions == 1, "Total conversions should be 1"
        assert user_a_code.total_earnings == 25.0, "Total earnings should be $25"

        print(f"✓ User A received $25 referrer reward, balance: ${user_a_balance}")

        # =====================================================================
        # STEP 6: Check affiliate dashboard shows correct metrics
        # =====================================================================
        print("\n=== STEP 6: Check affiliate dashboard metrics ===")

        # Get referrer stats from ReferralService
        referrer_stats = referral_service.get_referrer_stats(self.USER_A_ID)

        assert referrer_stats["has_code"], "User A should have code"
        assert referrer_stats["code"] == user_a_code.code, "Code should match"
        assert referrer_stats["total_referrals"] == 1, "Total referrals should be 1"
        assert referrer_stats["completed_referrals"] == 1, "Completed referrals should be 1"
        assert referrer_stats["pending_referrals"] == 0, "Pending referrals should be 0"
        assert referrer_stats["total_earnings"] == 25.0, "Total earnings should be $25"

        print(f"✓ Referrer stats: {referrer_stats}")

        # Get spend monitor stats
        monitor_stats = spend_monitor_service.get_referrer_stats(self.USER_A_ID)

        assert monitor_stats["total_referrals"] == 1, "Total referrals should be 1"
        assert monitor_stats["completed_referrals"] == 1, "Completed referrals should be 1"
        assert monitor_stats["total_referred_spend"] == 50.0, "Total spend should be $50"
        assert monitor_stats["rewards_granted"] == 1, "Rewards granted should be 1"
        assert monitor_stats["total_rewards"] == 25.0, "Total rewards should be $25"

        print(f"✓ Spend monitor stats: {monitor_stats}")

        # Get recent conversions
        recent_conversions = spend_monitor_service.get_recent_conversions(limit=5)

        assert len(recent_conversions) == 1, "Should have 1 recent conversion"
        conversion = recent_conversions[0]
        assert conversion["referrer_id"] == self.USER_A_ID
        assert conversion["referred_id"] == self.USER_B_ID
        assert conversion["total_spend"] == 50.0
        assert conversion["reward_amount"] == 25.0

        print(f"✓ Recent conversions: {recent_conversions}")

        # Get User B's credit summary
        user_b_summary = credit_service.get_user_credit_summary(self.USER_B_ID)

        assert user_b_summary["balance"] == 10.0, "User B balance should be $10"
        assert user_b_summary["total_credits"] == 10.0, "Total credits should be $10"
        assert TransactionType.WELCOME_CREDIT.value in user_b_summary["breakdown"]

        print(f"✓ User B credit summary: {user_b_summary}")

        # Get User A's credit summary
        user_a_summary = credit_service.get_user_credit_summary(self.USER_A_ID)

        assert user_a_summary["balance"] == 25.0, "User A balance should be $25"
        assert user_a_summary["total_credits"] == 25.0, "Total credits should be $25"
        assert TransactionType.REFERRAL_BONUS.value in user_a_summary["breakdown"]

        print(f"✓ User A credit summary: {user_a_summary}")

        print("\n✅ COMPLETE REFERRAL FLOW TEST PASSED!")

    def test_self_referral_prevention(self, referral_service):
        """Test that users cannot use their own referral code."""
        print("\n=== Test: Self-Referral Prevention ===")

        # Create referral code for User A
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)

        # Try to validate User A's code for User A (self-referral)
        validation = referral_service.validate_code(user_a_code.code, self.USER_A_ID)

        assert not validation["valid"], "Self-referral should not be valid"
        assert "own referral code" in validation["error"].lower(), "Error should mention own code"

        print(f"✓ Self-referral correctly blocked: {validation['error']}")

    def test_duplicate_referral_prevention(self, referral_service):
        """Test that users can only be referred once."""
        print("\n=== Test: Duplicate Referral Prevention ===")

        # Create referral codes for User A and C
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)
        user_c_code = referral_service.get_or_create_code(self.USER_C_ID)

        # Apply User A's code for User B
        result_1 = referral_service.apply_code(
            referred_user_id=self.USER_B_ID,
            code=user_a_code.code,
            skip_fraud_check=True
        )

        assert result_1["success"], "First referral should succeed"

        # Try to apply User C's code for User B (already referred)
        validation = referral_service.validate_code(user_c_code.code, self.USER_B_ID)

        assert not validation["valid"], "Duplicate referral should not be valid"
        assert "already has a referrer" in validation["error"].lower(), "Error should mention existing referrer"

        print(f"✓ Duplicate referral correctly blocked: {validation['error']}")

    def test_invalid_code_handling(self, referral_service):
        """Test handling of invalid referral codes."""
        print("\n=== Test: Invalid Code Handling ===")

        # Try to validate non-existent code
        validation = referral_service.validate_code("INVALIDCODE", self.USER_B_ID)

        assert not validation["valid"], "Invalid code should not be valid"
        assert "invalid" in validation["error"].lower(), "Error should mention invalid"

        print(f"✓ Invalid code correctly rejected: {validation['error']}")

    def test_email_verification_required_for_credit_use(
        self,
        test_db,
        referral_service,
        credit_service
    ):
        """Test that email verification is required before using credits."""
        print("\n=== Test: Email Verification Required ===")

        # Create referral code for User A and apply for User B
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)
        result = referral_service.apply_code(
            referred_user_id=self.USER_B_ID,
            code=user_a_code.code,
            skip_fraud_check=True
        )

        assert result["success"], "Referral should succeed"
        referral = result["referral"]

        # Try to use credits without email verification
        is_verified, error = credit_service.is_email_verified(self.USER_B_ID)

        assert not is_verified, "Email should not be verified"
        assert error is not None, "Error message should be present"

        # Verify exception is raised when trying to use credits
        with pytest.raises(EmailNotVerifiedError):
            credit_service.require_email_verification(self.USER_B_ID)

        print(f"✓ Email verification correctly enforced")

        # Now verify email and try again
        referral.email_verified = True
        referral.email_verified_at = datetime.utcnow()
        test_db.commit()

        is_verified, error = credit_service.is_email_verified(self.USER_B_ID)

        assert is_verified, "Email should now be verified"
        assert error is None, "No error after verification"

        print(f"✓ Credits can be used after email verification")

    def test_idempotent_reward_granting(
        self,
        test_db,
        referral_service,
        credit_service,
        spend_monitor_service
    ):
        """Test that rewards are only granted once (idempotency)."""
        print("\n=== Test: Idempotent Reward Granting ===")

        # Set up referral
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)
        result = referral_service.apply_code(
            referred_user_id=self.USER_B_ID,
            code=user_a_code.code,
            skip_fraud_check=True
        )

        referral = result["referral"]
        referral.email_verified = True
        referral.email_verified_at = datetime.utcnow()
        test_db.commit()

        # Grant welcome credit
        tx1 = credit_service.grant_welcome_credit(referral)
        assert tx1 is not None, "First grant should succeed"

        # Try to grant again (should return None)
        test_db.refresh(referral)
        tx2 = credit_service.grant_welcome_credit(referral)
        assert tx2 is None, "Second grant should return None"

        # Verify balance is still $10
        balance = credit_service.get_balance(self.USER_B_ID)
        assert balance == 10.0, "Balance should still be $10"

        print(f"✓ Welcome credit idempotency verified")

        # Simulate reaching threshold
        spend_monitor_service.record_spend(self.USER_B_ID, 50.0)

        # Verify User A balance is $25
        user_a_balance = credit_service.get_balance(self.USER_A_ID)
        assert user_a_balance == 25.0, "User A should have $25"

        # Try to record more spend (should not grant another reward)
        spend_monitor_service.record_spend(self.USER_B_ID, 50.0)

        # Verify balance is still $25
        user_a_balance_after = credit_service.get_balance(self.USER_A_ID)
        assert user_a_balance_after == 25.0, "User A should still have $25"

        print(f"✓ Referrer reward idempotency verified")

    def test_multiple_referrals_by_same_referrer(
        self,
        test_db,
        referral_service,
        credit_service,
        spend_monitor_service
    ):
        """Test that a referrer can have multiple successful referrals."""
        print("\n=== Test: Multiple Referrals ===")

        # Create referral code for User A
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)

        # Refer multiple users
        referred_users = [
            "referred-user-1",
            "referred-user-2",
            "referred-user-3"
        ]

        for i, user_id in enumerate(referred_users):
            # Apply referral
            result = referral_service.apply_code(
                referred_user_id=user_id,
                code=user_a_code.code,
                skip_fraud_check=True
            )
            assert result["success"], f"Referral for user {i+1} should succeed"

            # Verify email and grant welcome credit
            referral = result["referral"]
            referral.email_verified = True
            referral.email_verified_at = datetime.utcnow()
            test_db.commit()

            tx = credit_service.grant_welcome_credit(referral)
            assert tx is not None, f"Welcome credit for user {i+1} should be granted"

            # Record spend to reach threshold
            spend_result = spend_monitor_service.record_spend(user_id, 50.0)
            assert spend_result["referrer_rewarded"], f"Referrer should be rewarded for user {i+1}"

        # Verify User A's total earnings
        user_a_balance = credit_service.get_balance(self.USER_A_ID)
        expected_balance = 25.0 * len(referred_users)
        assert user_a_balance == expected_balance, f"User A should have ${expected_balance}"

        # Verify referral code stats
        test_db.refresh(user_a_code)
        assert user_a_code.total_signups == len(referred_users)
        assert user_a_code.total_conversions == len(referred_users)
        assert user_a_code.total_earnings == expected_balance

        # Verify referrer stats
        stats = referral_service.get_referrer_stats(self.USER_A_ID)
        assert stats["total_referrals"] == len(referred_users)
        assert stats["completed_referrals"] == len(referred_users)
        assert stats["total_earnings"] == expected_balance

        print(f"✓ Multiple referrals verified: {len(referred_users)} referrals, ${expected_balance} earned")

    def test_spend_progress_tracking(
        self,
        test_db,
        referral_service,
        spend_monitor_service
    ):
        """Test that spend progress is tracked correctly."""
        print("\n=== Test: Spend Progress Tracking ===")

        # Set up referral
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)
        result = referral_service.apply_code(
            referred_user_id=self.USER_B_ID,
            code=user_a_code.code,
            skip_fraud_check=True
        )

        referral = result["referral"]

        # Record incremental spends and check progress
        spend_amounts = [10, 15, 10, 10, 5]  # Total: $50
        expected_totals = [10, 25, 35, 45, 50]
        expected_progress = [0.2, 0.5, 0.7, 0.9, 1.0]

        for i, amount in enumerate(spend_amounts):
            spend_result = spend_monitor_service.record_spend(self.USER_B_ID, amount)

            assert spend_result["success"]
            assert spend_result["new_spend"] == expected_totals[i]

            # Check progress via threshold check
            status = spend_monitor_service.check_threshold_for_user(self.USER_B_ID)

            if i < len(spend_amounts) - 1:
                assert not status["threshold_reached"]
                assert abs(status["progress"] - expected_progress[i]) < 0.01
            else:
                assert status["threshold_reached"]

            print(f"  After ${amount} spend: total=${expected_totals[i]}, progress={expected_progress[i]*100}%")

        print(f"✓ Spend progress tracking verified")


# =============================================================================
# AFFILIATE DASHBOARD TESTS
# =============================================================================

class TestAffiliateDashboard:
    """Tests for affiliate dashboard functionality."""

    USER_A_ID = "affiliate-user-a"
    USER_B_ID = "affiliate-user-b"

    def test_affiliate_tracking_metrics(
        self,
        test_db,
        referral_service,
        affiliate_service,
        credit_service,
        spend_monitor_service
    ):
        """Test that affiliate tracking records correct metrics."""
        print("\n=== Test: Affiliate Tracking Metrics ===")

        # Create referral code
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)

        # Record clicks
        affiliate_service.record_click(
            affiliate_id=self.USER_A_ID,
            referral_code_id=user_a_code.id,
            is_unique=True
        )
        affiliate_service.record_click(
            affiliate_id=self.USER_A_ID,
            referral_code_id=user_a_code.id,
            is_unique=False
        )

        # Record signup
        affiliate_service.record_signup(
            affiliate_id=self.USER_A_ID,
            referral_code_id=user_a_code.id,
            is_verified=False
        )

        # Record email verification
        affiliate_service.record_email_verification(
            affiliate_id=self.USER_A_ID,
            referral_code_id=user_a_code.id
        )

        # Record conversion
        affiliate_service.record_conversion(
            affiliate_id=self.USER_A_ID,
            referral_code_id=user_a_code.id,
            revenue=50.0,
            credits_earned=25.0
        )

        # Get stats
        stats = affiliate_service.get_affiliate_stats(self.USER_A_ID, period="month")

        assert stats["metrics"]["total_clicks"] == 2
        assert stats["metrics"]["unique_clicks"] == 1
        assert stats["metrics"]["total_signups"] == 1
        assert stats["metrics"]["verified_signups"] == 1
        assert stats["metrics"]["total_conversions"] == 1
        assert stats["earnings"]["total_revenue"] == 50.0
        assert stats["earnings"]["total_earnings"] == 25.0

        print(f"✓ Affiliate stats: {stats}")

    def test_daily_metrics_generation(
        self,
        test_db,
        referral_service,
        affiliate_service
    ):
        """Test that daily metrics are generated correctly."""
        print("\n=== Test: Daily Metrics Generation ===")

        # Create referral code
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)

        # Record some activity
        for _ in range(5):
            affiliate_service.record_click(
                affiliate_id=self.USER_A_ID,
                referral_code_id=user_a_code.id,
                is_unique=True
            )

        affiliate_service.record_signup(
            affiliate_id=self.USER_A_ID,
            referral_code_id=user_a_code.id
        )

        # Get daily metrics
        daily_metrics = affiliate_service.get_daily_metrics(self.USER_A_ID, days=7)

        assert len(daily_metrics) >= 1, "Should have at least 1 day of metrics"

        # Today should have data
        today_key = datetime.utcnow().strftime("%Y-%m-%d")
        today_data = next((d for d in daily_metrics if d["date"] == today_key), None)

        if today_data:
            assert today_data["clicks"] == 5, "Today should have 5 clicks"
            assert today_data["unique_clicks"] == 5, "Today should have 5 unique clicks"
            assert today_data["signups"] == 1, "Today should have 1 signup"

        print(f"✓ Daily metrics: {len(daily_metrics)} days of data")

    def test_export_to_csv(
        self,
        test_db,
        referral_service,
        credit_service,
        spend_monitor_service,
        affiliate_service
    ):
        """Test CSV export for tax reporting."""
        print("\n=== Test: CSV Export ===")

        # Set up referral with conversion
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)
        result = referral_service.apply_code(
            referred_user_id=self.USER_B_ID,
            code=user_a_code.code,
            skip_fraud_check=True
        )

        referral = result["referral"]
        referral.email_verified = True
        referral.email_verified_at = datetime.utcnow()
        test_db.commit()

        # Record spend to trigger reward
        spend_monitor_service.record_spend(self.USER_B_ID, 50.0)

        # Export to CSV
        csv_content = affiliate_service.export_to_csv(self.USER_A_ID)

        assert csv_content is not None
        assert "Transaction ID" in csv_content
        assert "referral_bonus" in csv_content
        assert "25" in csv_content  # Reward amount

        print(f"✓ CSV export generated: {len(csv_content)} bytes")

    def test_lifetime_stats(
        self,
        test_db,
        referral_service,
        affiliate_service
    ):
        """Test lifetime statistics for affiliates."""
        print("\n=== Test: Lifetime Stats ===")

        # Create referral code
        user_a_code = referral_service.get_or_create_code(self.USER_A_ID)

        # Record activity
        for _ in range(10):
            affiliate_service.record_click(
                affiliate_id=self.USER_A_ID,
                referral_code_id=user_a_code.id,
                is_unique=True
            )
            referral_service.record_click(user_a_code.code)

        # Sync tracking
        affiliate_service.sync_tracking_with_referral_code(self.USER_A_ID)

        # Get lifetime stats
        lifetime = affiliate_service.get_lifetime_stats(self.USER_A_ID)

        assert lifetime["has_code"]
        assert lifetime["code"] == user_a_code.code
        assert lifetime["total_clicks"] >= 10

        print(f"✓ Lifetime stats: {lifetime}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
