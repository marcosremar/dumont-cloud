"""
Unit Tests for Credit Service

Tests for:
- Transaction ledger operations (add_credit, get_transaction_history)
- Balance calculations (get_balance, has_sufficient_balance)
- Welcome credit granting (grant_welcome_credit)
- Referrer reward granting (grant_referrer_reward)
- Credit retraction (retract_credit)
- Manual adjustments (manual_adjustment)
- Email verification (is_email_verified, require_email_verification)
- Spend tracking (update_referred_spend)
- Credit usage (use_credits)

Usage:
    pytest tests/test_credit_service.py -v
"""

import os
import sys
import pytest
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
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
from src.services.credit_service import (
    CreditService, EmailNotVerifiedError,
    REFERRER_REWARD_AMOUNT, REFERRED_WELCOME_CREDIT, SPEND_THRESHOLD
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create only referral-related tables
    tables_to_create = [
        ReferralCode.__table__,
        Referral.__table__,
        CreditTransaction.__table__,
        AffiliateTracking.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables_to_create)

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def credit_service(test_db):
    """Create CreditService with test database."""
    return CreditService(test_db)


@pytest.fixture
def sample_referral_code(test_db):
    """Create a sample referral code."""
    code = ReferralCode(
        user_id="referrer-user-123",
        code="TESTCODE1",
        is_active=True,
        total_clicks=0,
        total_signups=0,
        total_conversions=0,
        total_earnings=0.0
    )
    test_db.add(code)
    test_db.commit()
    test_db.refresh(code)
    return code


@pytest.fixture
def sample_referral(test_db, sample_referral_code):
    """Create a sample referral relationship."""
    referral = Referral(
        referrer_id="referrer-user-123",
        referred_id="referred-user-456",
        referral_code_id=sample_referral_code.id,
        status=ReferralStatus.PENDING.value,
        email_verified=False,
        referred_total_spend=0.0,
        spend_threshold=SPEND_THRESHOLD,
        referrer_reward_amount=REFERRER_REWARD_AMOUNT,
        referred_welcome_credit=REFERRED_WELCOME_CREDIT,
        reward_granted=False,
        welcome_credit_granted=False
    )
    test_db.add(referral)
    test_db.commit()
    test_db.refresh(referral)
    return referral


@pytest.fixture
def verified_referral(test_db, sample_referral):
    """Create a referral with verified email."""
    sample_referral.email_verified = True
    sample_referral.email_verified_at = datetime.utcnow()
    sample_referral.status = ReferralStatus.ACTIVE.value
    test_db.commit()
    test_db.refresh(sample_referral)
    return sample_referral


# =============================================================================
# TEST: TRANSACTION LEDGER - ADD CREDIT
# =============================================================================

class TestAddCredit:
    """Tests for add_credit functionality."""

    USER_ID = "ledger-user-001"

    def test_add_credit_creates_transaction(self, credit_service):
        """Test that add_credit creates a new transaction."""
        tx = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=10.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value,
            description="Test credit"
        )

        assert tx is not None
        assert tx.id is not None
        assert tx.user_id == self.USER_ID
        assert tx.amount == 10.0
        assert tx.transaction_type == TransactionType.WELCOME_CREDIT.value

    def test_add_credit_calculates_balance(self, credit_service):
        """Test that add_credit correctly calculates balance_after."""
        # First transaction - balance starts at 0
        tx1 = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=50.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        assert tx1.balance_before == 0.0
        assert tx1.balance_after == 50.0

        # Second transaction - should use previous balance
        tx2 = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )

        assert tx2.balance_before == 50.0
        assert tx2.balance_after == 75.0

    def test_add_credit_negative_amount(self, credit_service):
        """Test adding negative credit (debit)."""
        # First add some credit
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=100.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        # Then debit
        tx = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=-30.0,
            transaction_type=TransactionType.AFFILIATE_PAYOUT.value
        )

        assert tx.balance_before == 100.0
        assert tx.balance_after == 70.0

    def test_add_credit_zero_amount_raises_error(self, credit_service):
        """Test that zero amount raises ValueError."""
        with pytest.raises(ValueError, match="cannot be zero"):
            credit_service.add_credit(
                user_id=self.USER_ID,
                amount=0,
                transaction_type=TransactionType.MANUAL_ADJUSTMENT.value
            )

    def test_add_credit_rounds_to_two_decimals(self, credit_service):
        """Test that amounts are rounded to 2 decimal places."""
        tx = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=10.12345,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        assert tx.amount == 10.12
        assert tx.balance_after == 10.12

    def test_add_credit_with_referral_id(self, credit_service, sample_referral):
        """Test add_credit with referral_id."""
        tx = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value,
            referral_id=sample_referral.id
        )

        assert tx.referral_id == sample_referral.id

    def test_add_credit_with_reference(self, credit_service):
        """Test add_credit with external reference."""
        tx = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=10.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value,
            reference_id="billing-123",
            reference_type="billing"
        )

        assert tx.reference_id == "billing-123"
        assert tx.reference_type == "billing"

    def test_add_credit_with_ip_address(self, credit_service):
        """Test add_credit records IP address."""
        tx = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=10.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value,
            ip_address="192.168.1.100"
        )

        assert tx.ip_address == "192.168.1.100"


# =============================================================================
# TEST: BALANCE CALCULATIONS
# =============================================================================

class TestBalanceCalculations:
    """Tests for balance calculation methods."""

    USER_ID = "balance-user-001"

    def test_get_balance_no_transactions(self, credit_service):
        """Test balance is 0 when no transactions exist."""
        balance = credit_service.get_balance(self.USER_ID)
        assert balance == 0.0

    def test_get_balance_single_transaction(self, credit_service):
        """Test balance after single transaction."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=50.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        balance = credit_service.get_balance(self.USER_ID)
        assert balance == 50.0

    def test_get_balance_multiple_transactions(self, credit_service):
        """Test balance after multiple transactions."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=100.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=-50.0,
            transaction_type=TransactionType.AFFILIATE_PAYOUT.value
        )

        balance = credit_service.get_balance(self.USER_ID)
        assert balance == 75.0

    def test_has_sufficient_balance_true(self, credit_service):
        """Test has_sufficient_balance returns True when balance is enough."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=100.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        assert credit_service.has_sufficient_balance(self.USER_ID, 50.0) is True
        assert credit_service.has_sufficient_balance(self.USER_ID, 100.0) is True

    def test_has_sufficient_balance_false(self, credit_service):
        """Test has_sufficient_balance returns False when balance is insufficient."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=50.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        assert credit_service.has_sufficient_balance(self.USER_ID, 100.0) is False

    def test_has_sufficient_balance_zero_balance(self, credit_service):
        """Test has_sufficient_balance with zero balance."""
        assert credit_service.has_sufficient_balance(self.USER_ID, 10.0) is False
        assert credit_service.has_sufficient_balance(self.USER_ID, 0.0) is True


# =============================================================================
# TEST: TRANSACTION HISTORY
# =============================================================================

class TestTransactionHistory:
    """Tests for transaction history retrieval."""

    USER_ID = "history-user-001"

    def test_get_transaction_history_empty(self, credit_service):
        """Test getting history when no transactions exist."""
        history = credit_service.get_transaction_history(self.USER_ID)
        assert history == []

    def test_get_transaction_history_returns_transactions(self, credit_service):
        """Test getting transaction history."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=10.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )

        history = credit_service.get_transaction_history(self.USER_ID)

        assert len(history) == 2
        # Should be ordered by created_at descending
        assert history[0].amount == 25.0
        assert history[1].amount == 10.0

    def test_get_transaction_history_with_limit(self, credit_service):
        """Test getting transaction history with limit."""
        for i in range(5):
            credit_service.add_credit(
                user_id=self.USER_ID,
                amount=10.0,
                transaction_type=TransactionType.WELCOME_CREDIT.value
            )

        history = credit_service.get_transaction_history(self.USER_ID, limit=3)

        assert len(history) == 3

    def test_get_transaction_history_with_offset(self, credit_service):
        """Test getting transaction history with offset."""
        for i in range(5):
            credit_service.add_credit(
                user_id=self.USER_ID,
                amount=float(i + 1),
                transaction_type=TransactionType.WELCOME_CREDIT.value
            )

        history = credit_service.get_transaction_history(self.USER_ID, offset=2)

        assert len(history) == 3

    def test_get_transaction_history_filter_by_type(self, credit_service):
        """Test filtering transaction history by type."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=10.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )

        history = credit_service.get_transaction_history(
            self.USER_ID,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )

        assert len(history) == 1
        assert history[0].transaction_type == TransactionType.REFERRAL_BONUS.value

    def test_get_transaction_count(self, credit_service):
        """Test getting transaction count."""
        for i in range(5):
            credit_service.add_credit(
                user_id=self.USER_ID,
                amount=10.0,
                transaction_type=TransactionType.WELCOME_CREDIT.value
            )

        count = credit_service.get_transaction_count(self.USER_ID)
        assert count == 5

    def test_get_transaction_count_by_type(self, credit_service):
        """Test getting transaction count filtered by type."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=10.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )

        count = credit_service.get_transaction_count(
            self.USER_ID,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )
        assert count == 2


# =============================================================================
# TEST: EMAIL VERIFICATION
# =============================================================================

class TestEmailVerification:
    """Tests for email verification functionality."""

    def test_is_email_verified_non_referred_user(self, credit_service):
        """Test that non-referred users are considered verified."""
        is_verified, error = credit_service.is_email_verified("non-referred-user")

        assert is_verified is True
        assert error is None

    def test_is_email_verified_unverified_referral(self, credit_service, sample_referral):
        """Test that unverified referred users return False."""
        is_verified, error = credit_service.is_email_verified(sample_referral.referred_id)

        assert is_verified is False
        assert error is not None
        assert "verification required" in error.lower()

    def test_is_email_verified_verified_referral(self, credit_service, verified_referral):
        """Test that verified referred users return True."""
        is_verified, error = credit_service.is_email_verified(verified_referral.referred_id)

        assert is_verified is True
        assert error is None

    def test_require_email_verification_raises_for_unverified(self, credit_service, sample_referral):
        """Test that require_email_verification raises error for unverified users."""
        with pytest.raises(EmailNotVerifiedError):
            credit_service.require_email_verification(sample_referral.referred_id)

    def test_require_email_verification_passes_for_verified(self, credit_service, verified_referral):
        """Test that require_email_verification passes for verified users."""
        # Should not raise
        credit_service.require_email_verification(verified_referral.referred_id)

    def test_require_email_verification_passes_for_non_referred(self, credit_service):
        """Test that require_email_verification passes for non-referred users."""
        # Should not raise
        credit_service.require_email_verification("non-referred-user")


# =============================================================================
# TEST: WELCOME CREDIT
# =============================================================================

class TestWelcomeCredit:
    """Tests for welcome credit granting."""

    def test_grant_welcome_credit_success(self, test_db, credit_service, sample_referral):
        """Test successfully granting welcome credit."""
        # Verify email first
        sample_referral.email_verified = True
        sample_referral.email_verified_at = datetime.utcnow()
        test_db.commit()

        tx = credit_service.grant_welcome_credit(sample_referral)

        assert tx is not None
        assert tx.amount == REFERRED_WELCOME_CREDIT
        assert tx.transaction_type == TransactionType.WELCOME_CREDIT.value
        assert tx.user_id == sample_referral.referred_id

        # Check referral was updated
        test_db.refresh(sample_referral)
        assert sample_referral.welcome_credit_granted is True
        assert sample_referral.welcome_credit_granted_at is not None

    def test_grant_welcome_credit_email_not_verified(self, credit_service, sample_referral):
        """Test that welcome credit is not granted without email verification."""
        tx = credit_service.grant_welcome_credit(sample_referral)

        assert tx is None
        assert sample_referral.welcome_credit_granted is False

    def test_grant_welcome_credit_already_granted(self, test_db, credit_service, sample_referral):
        """Test that welcome credit is not granted twice."""
        # Verify email and grant first time
        sample_referral.email_verified = True
        sample_referral.email_verified_at = datetime.utcnow()
        test_db.commit()

        tx1 = credit_service.grant_welcome_credit(sample_referral)
        assert tx1 is not None

        # Try to grant again
        tx2 = credit_service.grant_welcome_credit(sample_referral)
        assert tx2 is None

    def test_grant_welcome_credit_suspicious_blocked(self, test_db, credit_service, sample_referral):
        """Test that welcome credit is blocked for suspicious referrals."""
        sample_referral.email_verified = True
        sample_referral.is_suspicious = True
        test_db.commit()

        tx = credit_service.grant_welcome_credit(sample_referral)

        assert tx is None

    def test_grant_welcome_credit_fraud_blocked(self, test_db, credit_service, sample_referral):
        """Test that welcome credit is blocked for fraud referrals."""
        sample_referral.email_verified = True
        sample_referral.status = ReferralStatus.FRAUD.value
        test_db.commit()

        tx = credit_service.grant_welcome_credit(sample_referral)

        assert tx is None

    def test_grant_welcome_credit_updates_status(self, test_db, credit_service, sample_referral):
        """Test that welcome credit updates referral status to ACTIVE."""
        sample_referral.email_verified = True
        sample_referral.email_verified_at = datetime.utcnow()
        sample_referral.status = ReferralStatus.PENDING.value
        test_db.commit()

        credit_service.grant_welcome_credit(sample_referral)

        test_db.refresh(sample_referral)
        assert sample_referral.status == ReferralStatus.ACTIVE.value


# =============================================================================
# TEST: REFERRER REWARD
# =============================================================================

class TestReferrerReward:
    """Tests for referrer reward granting."""

    def test_grant_referrer_reward_success(self, test_db, credit_service, sample_referral, sample_referral_code):
        """Test successfully granting referrer reward."""
        sample_referral.referred_total_spend = 60.0  # Above threshold
        sample_referral.email_verified = True
        test_db.commit()

        tx = credit_service.grant_referrer_reward(sample_referral)

        assert tx is not None
        assert tx.amount == REFERRER_REWARD_AMOUNT
        assert tx.transaction_type == TransactionType.REFERRAL_BONUS.value
        assert tx.user_id == sample_referral.referrer_id

        # Check referral was updated
        test_db.refresh(sample_referral)
        assert sample_referral.reward_granted is True
        assert sample_referral.reward_granted_at is not None
        assert sample_referral.status == ReferralStatus.COMPLETED.value

    def test_grant_referrer_reward_threshold_not_reached(self, credit_service, sample_referral):
        """Test that reward is not granted if threshold not reached."""
        sample_referral.referred_total_spend = 40.0  # Below threshold

        tx = credit_service.grant_referrer_reward(sample_referral)

        assert tx is None

    def test_grant_referrer_reward_already_granted(self, test_db, credit_service, sample_referral, sample_referral_code):
        """Test that reward is not granted twice."""
        sample_referral.referred_total_spend = 60.0
        sample_referral.email_verified = True
        test_db.commit()

        tx1 = credit_service.grant_referrer_reward(sample_referral)
        assert tx1 is not None

        tx2 = credit_service.grant_referrer_reward(sample_referral)
        assert tx2 is None

    def test_grant_referrer_reward_suspicious_blocked(self, test_db, credit_service, sample_referral):
        """Test that reward is blocked for suspicious referrals."""
        sample_referral.referred_total_spend = 60.0
        sample_referral.is_suspicious = True
        test_db.commit()

        tx = credit_service.grant_referrer_reward(sample_referral)

        assert tx is None

    def test_grant_referrer_reward_updates_code_stats(self, test_db, credit_service, sample_referral, sample_referral_code):
        """Test that reward updates referral code statistics."""
        sample_referral.referred_total_spend = 60.0
        sample_referral.email_verified = True
        test_db.commit()

        initial_conversions = sample_referral_code.total_conversions
        initial_earnings = sample_referral_code.total_earnings

        credit_service.grant_referrer_reward(sample_referral)

        test_db.refresh(sample_referral_code)
        assert sample_referral_code.total_conversions == initial_conversions + 1
        assert sample_referral_code.total_earnings == initial_earnings + REFERRER_REWARD_AMOUNT


# =============================================================================
# TEST: CREDIT RETRACTION
# =============================================================================

class TestCreditRetraction:
    """Tests for credit retraction functionality."""

    USER_ID = "retraction-user-001"

    def test_retract_credit_success(self, credit_service):
        """Test successfully retracting a credit."""
        original_tx = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )

        retraction = credit_service.retract_credit(
            user_id=self.USER_ID,
            original_transaction_id=original_tx.id,
            reason="Fraud detected"
        )

        assert retraction is not None
        assert retraction.amount == -25.0
        assert retraction.transaction_type == TransactionType.CREDIT_RETRACTION.value
        assert retraction.reference_id == str(original_tx.id)
        assert retraction.reference_type == "credit_retraction"

    def test_retract_credit_updates_balance(self, credit_service):
        """Test that retraction correctly updates balance."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=50.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )
        original_tx = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )

        assert credit_service.get_balance(self.USER_ID) == 75.0

        credit_service.retract_credit(
            user_id=self.USER_ID,
            original_transaction_id=original_tx.id,
            reason="Refund requested"
        )

        assert credit_service.get_balance(self.USER_ID) == 50.0

    def test_retract_credit_invalid_transaction(self, credit_service):
        """Test retracting non-existent transaction returns None."""
        retraction = credit_service.retract_credit(
            user_id=self.USER_ID,
            original_transaction_id=99999,
            reason="Test"
        )

        assert retraction is None

    def test_retract_credit_wrong_user(self, credit_service):
        """Test retracting transaction from different user returns None."""
        original_tx = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )

        retraction = credit_service.retract_credit(
            user_id="different-user",
            original_transaction_id=original_tx.id,
            reason="Test"
        )

        assert retraction is None

    def test_retract_credit_duplicate_prevented(self, credit_service):
        """Test that same credit cannot be retracted twice."""
        original_tx = credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )

        # First retraction
        r1 = credit_service.retract_credit(
            user_id=self.USER_ID,
            original_transaction_id=original_tx.id,
            reason="First retraction"
        )
        assert r1 is not None

        # Second retraction should fail
        r2 = credit_service.retract_credit(
            user_id=self.USER_ID,
            original_transaction_id=original_tx.id,
            reason="Duplicate retraction"
        )
        assert r2 is None


# =============================================================================
# TEST: MANUAL ADJUSTMENT
# =============================================================================

class TestManualAdjustment:
    """Tests for manual credit adjustments."""

    USER_ID = "adjustment-user-001"
    ADMIN_ID = "admin-001"

    def test_manual_adjustment_positive(self, credit_service):
        """Test positive manual adjustment."""
        tx = credit_service.manual_adjustment(
            user_id=self.USER_ID,
            amount=50.0,
            reason="Customer service credit",
            adjusted_by=self.ADMIN_ID
        )

        assert tx is not None
        assert tx.amount == 50.0
        assert tx.transaction_type == TransactionType.MANUAL_ADJUSTMENT.value
        assert tx.created_by == self.ADMIN_ID
        assert "Customer service credit" in tx.description

    def test_manual_adjustment_negative(self, credit_service):
        """Test negative manual adjustment."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=100.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        tx = credit_service.manual_adjustment(
            user_id=self.USER_ID,
            amount=-30.0,
            reason="Correction for error",
            adjusted_by=self.ADMIN_ID
        )

        assert tx is not None
        assert tx.amount == -30.0
        assert credit_service.get_balance(self.USER_ID) == 70.0


# =============================================================================
# TEST: SPEND TRACKING
# =============================================================================

class TestSpendTracking:
    """Tests for referred user spend tracking."""

    def test_update_referred_spend_increments(self, test_db, credit_service, sample_referral):
        """Test that spend is correctly incremented."""
        sample_referral.status = ReferralStatus.ACTIVE.value
        test_db.commit()

        credit_service.update_referred_spend(sample_referral.referred_id, 20.0)

        test_db.refresh(sample_referral)
        assert sample_referral.referred_total_spend == 20.0

    def test_update_referred_spend_accumulates(self, test_db, credit_service, sample_referral):
        """Test that multiple spends accumulate."""
        sample_referral.status = ReferralStatus.ACTIVE.value
        test_db.commit()

        credit_service.update_referred_spend(sample_referral.referred_id, 20.0)
        credit_service.update_referred_spend(sample_referral.referred_id, 15.0)

        test_db.refresh(sample_referral)
        assert sample_referral.referred_total_spend == 35.0

    def test_update_referred_spend_triggers_reward(self, test_db, credit_service, sample_referral, sample_referral_code):
        """Test that reaching threshold triggers referrer reward."""
        sample_referral.status = ReferralStatus.ACTIVE.value
        sample_referral.email_verified = True
        test_db.commit()

        reward_tx = credit_service.update_referred_spend(sample_referral.referred_id, 55.0)

        assert reward_tx is not None
        assert reward_tx.amount == REFERRER_REWARD_AMOUNT
        assert reward_tx.user_id == sample_referral.referrer_id

    def test_update_referred_spend_no_referral(self, credit_service):
        """Test that non-referred user returns None."""
        result = credit_service.update_referred_spend("non-referred-user", 100.0)
        assert result is None

    def test_update_referred_spend_completed_referral(self, test_db, credit_service, sample_referral):
        """Test that completed referral is not updated."""
        sample_referral.status = ReferralStatus.COMPLETED.value
        test_db.commit()

        result = credit_service.update_referred_spend(sample_referral.referred_id, 100.0)
        assert result is None


# =============================================================================
# TEST: USE CREDITS
# =============================================================================

class TestUseCredits:
    """Tests for using credits."""

    USER_ID = "use-credits-user-001"

    def test_use_credits_success(self, credit_service):
        """Test successfully using credits."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=100.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        tx = credit_service.use_credits(
            user_id=self.USER_ID,
            amount=30.0,
            description="Instance payment"
        )

        assert tx is not None
        assert tx.amount == -30.0
        assert credit_service.get_balance(self.USER_ID) == 70.0

    def test_use_credits_insufficient_balance(self, credit_service):
        """Test using credits with insufficient balance."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=20.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        tx = credit_service.use_credits(
            user_id=self.USER_ID,
            amount=50.0,
            description="Large payment"
        )

        assert tx is None
        # Balance unchanged
        assert credit_service.get_balance(self.USER_ID) == 20.0

    def test_use_credits_requires_verification(self, credit_service, sample_referral):
        """Test that use_credits requires email verification for referred users."""
        credit_service.add_credit(
            user_id=sample_referral.referred_id,
            amount=100.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        with pytest.raises(EmailNotVerifiedError):
            credit_service.use_credits(
                user_id=sample_referral.referred_id,
                amount=10.0,
                description="Test"
            )

    def test_use_credits_skip_verification(self, credit_service, sample_referral):
        """Test that skip_verification bypasses email check."""
        credit_service.add_credit(
            user_id=sample_referral.referred_id,
            amount=100.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )

        tx = credit_service.use_credits(
            user_id=sample_referral.referred_id,
            amount=10.0,
            description="Test",
            skip_verification=True
        )

        assert tx is not None

    def test_use_credits_negative_amount_raises(self, credit_service):
        """Test that negative amount raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            credit_service.use_credits(
                user_id=self.USER_ID,
                amount=-10.0,
                description="Test"
            )

    def test_use_credits_zero_amount_raises(self, credit_service):
        """Test that zero amount raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            credit_service.use_credits(
                user_id=self.USER_ID,
                amount=0.0,
                description="Test"
            )


# =============================================================================
# TEST: CREDIT SUMMARY
# =============================================================================

class TestCreditSummary:
    """Tests for user credit summary."""

    USER_ID = "summary-user-001"

    def test_get_user_credit_summary_empty(self, credit_service):
        """Test summary for user with no transactions."""
        summary = credit_service.get_user_credit_summary(self.USER_ID)

        assert summary["balance"] == 0.0
        assert summary["total_credits"] == 0.0
        assert summary["total_debits"] == 0.0
        assert summary["transaction_count"] == 0
        assert summary["breakdown"] == {}

    def test_get_user_credit_summary_with_transactions(self, credit_service):
        """Test summary with various transactions."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=100.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=50.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=-30.0,
            transaction_type=TransactionType.AFFILIATE_PAYOUT.value
        )

        summary = credit_service.get_user_credit_summary(self.USER_ID)

        assert summary["balance"] == 120.0
        assert summary["total_credits"] == 150.0
        assert summary["total_debits"] == 30.0
        assert summary["transaction_count"] == 3
        assert TransactionType.WELCOME_CREDIT.value in summary["breakdown"]
        assert TransactionType.REFERRAL_BONUS.value in summary["breakdown"]

    def test_get_user_credit_summary_breakdown(self, credit_service):
        """Test that breakdown includes count and total per type."""
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=10.0,
            transaction_type=TransactionType.WELCOME_CREDIT.value
        )
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )
        credit_service.add_credit(
            user_id=self.USER_ID,
            amount=25.0,
            transaction_type=TransactionType.REFERRAL_BONUS.value
        )

        summary = credit_service.get_user_credit_summary(self.USER_ID)

        assert summary["breakdown"][TransactionType.WELCOME_CREDIT.value]["count"] == 1
        assert summary["breakdown"][TransactionType.WELCOME_CREDIT.value]["total"] == 10.0
        assert summary["breakdown"][TransactionType.REFERRAL_BONUS.value]["count"] == 2
        assert summary["breakdown"][TransactionType.REFERRAL_BONUS.value]["total"] == 50.0


# =============================================================================
# TEST: PENDING REFERRER REWARDS
# =============================================================================

class TestPendingReferrerRewards:
    """Tests for pending referrer rewards retrieval."""

    REFERRER_ID = "pending-referrer-001"

    def test_get_pending_referrer_rewards_empty(self, credit_service):
        """Test getting pending rewards when none exist."""
        result = credit_service.get_pending_referrer_rewards(self.REFERRER_ID)

        assert result["pending_count"] == 0
        assert result["potential_earnings"] == 0.0
        assert result["referrals"] == []

    def test_get_pending_referrer_rewards_with_pending(self, test_db, credit_service, sample_referral_code):
        """Test getting pending rewards with active referrals."""
        # Create referral for our referrer
        sample_referral_code.user_id = self.REFERRER_ID
        test_db.commit()

        referral = Referral(
            referrer_id=self.REFERRER_ID,
            referred_id="pending-referred-001",
            referral_code_id=sample_referral_code.id,
            status=ReferralStatus.ACTIVE.value,
            email_verified=True,
            referred_total_spend=30.0,
            spend_threshold=SPEND_THRESHOLD,
            referrer_reward_amount=REFERRER_REWARD_AMOUNT,
            referred_welcome_credit=REFERRED_WELCOME_CREDIT,
            reward_granted=False
        )
        test_db.add(referral)
        test_db.commit()

        result = credit_service.get_pending_referrer_rewards(self.REFERRER_ID)

        assert result["pending_count"] == 1
        assert result["potential_earnings"] == REFERRER_REWARD_AMOUNT
        assert len(result["referrals"]) == 1
        assert result["referrals"][0]["current_spend"] == 30.0
        assert result["referrals"][0]["threshold"] == SPEND_THRESHOLD

    def test_get_pending_referrer_rewards_excludes_completed(self, test_db, credit_service, sample_referral_code):
        """Test that completed referrals are excluded."""
        sample_referral_code.user_id = self.REFERRER_ID
        test_db.commit()

        # Completed referral
        completed = Referral(
            referrer_id=self.REFERRER_ID,
            referred_id="completed-referred-001",
            referral_code_id=sample_referral_code.id,
            status=ReferralStatus.COMPLETED.value,
            reward_granted=True,
            referred_total_spend=60.0,
            spend_threshold=SPEND_THRESHOLD,
            referrer_reward_amount=REFERRER_REWARD_AMOUNT
        )
        test_db.add(completed)
        test_db.commit()

        result = credit_service.get_pending_referrer_rewards(self.REFERRER_ID)

        assert result["pending_count"] == 0

    def test_get_pending_referrer_rewards_average_progress(self, test_db, credit_service, sample_referral_code):
        """Test that average progress is calculated correctly."""
        sample_referral_code.user_id = self.REFERRER_ID
        test_db.commit()

        # Two pending referrals at different progress levels
        for i, spend in enumerate([25.0, 40.0]):
            ref = Referral(
                referrer_id=self.REFERRER_ID,
                referred_id=f"progress-referred-{i}",
                referral_code_id=sample_referral_code.id,
                status=ReferralStatus.ACTIVE.value,
                reward_granted=False,
                referred_total_spend=spend,
                spend_threshold=SPEND_THRESHOLD,
                referrer_reward_amount=REFERRER_REWARD_AMOUNT
            )
            test_db.add(ref)
        test_db.commit()

        result = credit_service.get_pending_referrer_rewards(self.REFERRER_ID)

        # Average progress: (25/50 + 40/50) / 2 = (0.5 + 0.8) / 2 = 0.65
        assert result["average_progress"] == 0.65
        assert result["pending_count"] == 2
        assert result["potential_earnings"] == REFERRER_REWARD_AMOUNT * 2


# =============================================================================
# TEST: GET REFERRAL BY REFERRED
# =============================================================================

class TestGetReferralByReferred:
    """Tests for getting referral by referred user ID."""

    def test_get_referral_by_referred_found(self, credit_service, sample_referral):
        """Test finding referral by referred user ID."""
        referral = credit_service.get_referral_by_referred(sample_referral.referred_id)

        assert referral is not None
        assert referral.id == sample_referral.id
        assert referral.referred_id == sample_referral.referred_id

    def test_get_referral_by_referred_not_found(self, credit_service):
        """Test returns None when referral not found."""
        referral = credit_service.get_referral_by_referred("non-existent-user")

        assert referral is None


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
