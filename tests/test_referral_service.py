"""
Unit Tests for Referral Service

Tests for:
- Code generation (length, format, uniqueness)
- Code validation (active, expired, exists)
- Self-referral prevention
- Duplicate referral prevention
- Apply code functionality

Usage:
    pytest tests/test_referral_service.py -v
"""

import os
import sys
import pytest
import string
from datetime import datetime, timedelta
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
from src.services.referral_service import (
    ReferralService, CODE_LENGTH, CODE_ALPHABET,
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
def referral_service(test_db):
    """Create ReferralService with test database."""
    return ReferralService(test_db)


# =============================================================================
# TEST: CODE GENERATION
# =============================================================================

class TestCodeGeneration:
    """Tests for referral code generation."""

    def test_generate_code_default_length(self):
        """Test that code is generated with default length (8 characters)."""
        code = ReferralService.generate_code()

        assert len(code) == CODE_LENGTH
        assert len(code) >= 8
        assert len(code) <= 12

    def test_generate_code_custom_length(self):
        """Test code generation with custom lengths."""
        # Test various lengths
        for length in [8, 9, 10, 11, 12]:
            code = ReferralService.generate_code(length=length)
            assert len(code) == length, f"Expected length {length}, got {len(code)}"

    def test_generate_code_min_length_enforced(self):
        """Test that minimum length of 8 is enforced."""
        # Try to generate shorter code
        code = ReferralService.generate_code(length=5)
        assert len(code) == 8, "Minimum length should be 8"

    def test_generate_code_max_length_enforced(self):
        """Test that maximum length of 12 is enforced."""
        # Try to generate longer code
        code = ReferralService.generate_code(length=20)
        assert len(code) == 12, "Maximum length should be 12"

    def test_generate_code_alphanumeric_only(self):
        """Test that code contains only uppercase letters and digits."""
        expected_chars = set(CODE_ALPHABET)  # A-Z, 0-9

        # Generate multiple codes to increase confidence
        for _ in range(100):
            code = ReferralService.generate_code()
            for char in code:
                assert char in expected_chars, f"Invalid character '{char}' in code"

    def test_generate_code_uniqueness(self):
        """Test that generated codes are unique (statistical)."""
        codes = set()
        num_codes = 1000

        for _ in range(num_codes):
            code = ReferralService.generate_code()
            codes.add(code)

        # With 36^8 = 2.8 trillion possible codes, collisions should be extremely rare
        # We allow up to 1% collision rate for this test
        collision_rate = (num_codes - len(codes)) / num_codes
        assert collision_rate < 0.01, f"Too many collisions: {collision_rate*100:.2f}%"

    def test_generate_code_is_uppercase(self):
        """Test that all letters in code are uppercase."""
        for _ in range(50):
            code = ReferralService.generate_code()
            assert code == code.upper(), "Code should be uppercase"


class TestCodeCreation:
    """Tests for creating and storing referral codes in database."""

    USER_A_ID = "user-a-test-123"
    USER_B_ID = "user-b-test-456"

    def test_get_or_create_code_new_user(self, referral_service):
        """Test creating a new referral code for a user."""
        code = referral_service.get_or_create_code(self.USER_A_ID)

        assert code is not None
        assert code.user_id == self.USER_A_ID
        assert code.code is not None
        assert len(code.code) >= 8
        assert len(code.code) <= 12
        assert code.is_active is True
        assert code.is_usable is True
        assert code.total_signups == 0
        assert code.total_conversions == 0

    def test_get_or_create_code_existing_user(self, referral_service):
        """Test that the same code is returned for an existing user."""
        code1 = referral_service.get_or_create_code(self.USER_A_ID)
        code2 = referral_service.get_or_create_code(self.USER_A_ID)

        assert code1.id == code2.id
        assert code1.code == code2.code

    def test_different_users_get_different_codes(self, referral_service):
        """Test that different users get different codes."""
        code_a = referral_service.get_or_create_code(self.USER_A_ID)
        code_b = referral_service.get_or_create_code(self.USER_B_ID)

        assert code_a.code != code_b.code
        assert code_a.user_id != code_b.user_id

    def test_get_code_by_user(self, referral_service):
        """Test retrieving code by user ID."""
        # Create code first
        created = referral_service.get_or_create_code(self.USER_A_ID)

        # Retrieve by user
        retrieved = referral_service.get_code_by_user(self.USER_A_ID)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.code == created.code

    def test_get_code_by_user_not_found(self, referral_service):
        """Test retrieving code for non-existent user returns None."""
        result = referral_service.get_code_by_user("non-existent-user")
        assert result is None

    def test_get_code_by_code(self, referral_service):
        """Test retrieving code by the code string."""
        created = referral_service.get_or_create_code(self.USER_A_ID)

        retrieved = referral_service.get_code_by_code(created.code)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_code_by_code_case_insensitive(self, referral_service):
        """Test that code lookup is case-insensitive."""
        created = referral_service.get_or_create_code(self.USER_A_ID)

        # Try lowercase
        retrieved_lower = referral_service.get_code_by_code(created.code.lower())
        assert retrieved_lower is not None
        assert retrieved_lower.id == created.id

    def test_get_code_by_code_not_found(self, referral_service):
        """Test retrieving non-existent code returns None."""
        result = referral_service.get_code_by_code("NONEXISTENT")
        assert result is None


# =============================================================================
# TEST: CODE VALIDATION
# =============================================================================

class TestCodeValidation:
    """Tests for referral code validation."""

    USER_A_ID = "validator-user-a"
    USER_B_ID = "validator-user-b"

    def test_validate_valid_code(self, referral_service):
        """Test validating a valid, active code."""
        # Create code for User A
        code = referral_service.get_or_create_code(self.USER_A_ID)

        # Validate for User B
        result = referral_service.validate_code(code.code, self.USER_B_ID)

        assert result["valid"] is True
        assert result["error"] is None
        assert result["referral_code"] is not None
        assert result["referral_code"].code == code.code

    def test_validate_empty_code(self, referral_service):
        """Test validating empty code returns error."""
        result = referral_service.validate_code("", self.USER_B_ID)

        assert result["valid"] is False
        assert "required" in result["error"].lower()
        assert result["referral_code"] is None

    def test_validate_none_code(self, referral_service):
        """Test validating None code returns error."""
        result = referral_service.validate_code(None, self.USER_B_ID)

        assert result["valid"] is False
        assert "required" in result["error"].lower()

    def test_validate_nonexistent_code(self, referral_service):
        """Test validating non-existent code returns error."""
        result = referral_service.validate_code("NONEXISTENT", self.USER_B_ID)

        assert result["valid"] is False
        assert "invalid" in result["error"].lower()

    def test_validate_inactive_code(self, test_db, referral_service):
        """Test validating inactive code returns error."""
        # Create and deactivate code
        code = referral_service.get_or_create_code(self.USER_A_ID)
        code.is_active = False
        test_db.commit()

        result = referral_service.validate_code(code.code, self.USER_B_ID)

        assert result["valid"] is False
        assert "inactive" in result["error"].lower()

    def test_validate_expired_code(self, test_db, referral_service):
        """Test validating expired code returns error."""
        # Create and expire code
        code = referral_service.get_or_create_code(self.USER_A_ID)
        code.expires_at = datetime.utcnow() - timedelta(days=1)
        test_db.commit()

        result = referral_service.validate_code(code.code, self.USER_B_ID)

        assert result["valid"] is False
        assert "expired" in result["error"].lower()


# =============================================================================
# TEST: SELF-REFERRAL PREVENTION
# =============================================================================

class TestSelfReferralPrevention:
    """Tests for preventing users from using their own referral codes."""

    USER_ID = "self-referral-user"

    def test_self_referral_blocked_in_validation(self, referral_service):
        """Test that self-referral is blocked during validation."""
        # Create code for user
        code = referral_service.get_or_create_code(self.USER_ID)

        # Try to validate own code
        result = referral_service.validate_code(code.code, self.USER_ID)

        assert result["valid"] is False
        assert "own referral code" in result["error"].lower()
        assert result["referral_code"] is None

    def test_self_referral_blocked_in_apply(self, referral_service):
        """Test that self-referral is blocked when applying code."""
        # Create code for user
        code = referral_service.get_or_create_code(self.USER_ID)

        # Try to apply own code
        result = referral_service.apply_code(
            referred_user_id=self.USER_ID,
            code=code.code,
            skip_fraud_check=True
        )

        assert result["success"] is False
        assert "own referral code" in result["error"].lower()
        assert result["referral"] is None

    def test_self_referral_case_insensitive(self, referral_service):
        """Test that self-referral is blocked regardless of case."""
        code = referral_service.get_or_create_code(self.USER_ID)

        # Try with lowercase
        result = referral_service.validate_code(code.code.lower(), self.USER_ID)

        assert result["valid"] is False
        assert "own referral code" in result["error"].lower()


# =============================================================================
# TEST: DUPLICATE REFERRAL PREVENTION
# =============================================================================

class TestDuplicateReferralPrevention:
    """Tests for preventing users from being referred multiple times."""

    USER_A_ID = "referrer-a"
    USER_B_ID = "referrer-b"
    USER_C_ID = "referred-user"

    def test_duplicate_referral_blocked_in_validation(self, referral_service):
        """Test that duplicate referral is blocked during validation."""
        # Create codes for two referrers
        code_a = referral_service.get_or_create_code(self.USER_A_ID)
        code_b = referral_service.get_or_create_code(self.USER_B_ID)

        # Apply first code successfully
        result1 = referral_service.apply_code(
            referred_user_id=self.USER_C_ID,
            code=code_a.code,
            skip_fraud_check=True
        )
        assert result1["success"] is True

        # Try to validate second code for same user
        validation = referral_service.validate_code(code_b.code, self.USER_C_ID)

        assert validation["valid"] is False
        assert "already has a referrer" in validation["error"].lower()

    def test_duplicate_referral_blocked_in_apply(self, referral_service):
        """Test that duplicate referral is blocked when applying code."""
        # Create codes for two referrers
        code_a = referral_service.get_or_create_code(self.USER_A_ID)
        code_b = referral_service.get_or_create_code(self.USER_B_ID)

        # Apply first code successfully
        result1 = referral_service.apply_code(
            referred_user_id=self.USER_C_ID,
            code=code_a.code,
            skip_fraud_check=True
        )
        assert result1["success"] is True

        # Try to apply second code for same user
        result2 = referral_service.apply_code(
            referred_user_id=self.USER_C_ID,
            code=code_b.code,
            skip_fraud_check=True
        )

        assert result2["success"] is False
        assert "already has a referrer" in result2["error"].lower()


# =============================================================================
# TEST: APPLY CODE
# =============================================================================

class TestApplyCode:
    """Tests for applying referral codes."""

    REFERRER_ID = "apply-referrer"
    REFERRED_ID = "apply-referred"

    def test_apply_code_success(self, referral_service):
        """Test successfully applying a referral code."""
        code = referral_service.get_or_create_code(self.REFERRER_ID)

        result = referral_service.apply_code(
            referred_user_id=self.REFERRED_ID,
            code=code.code,
            skip_fraud_check=True
        )

        assert result["success"] is True
        assert result["error"] is None
        assert result["referral"] is not None
        assert result["welcome_credit"] == REFERRED_WELCOME_CREDIT

        # Check referral object
        referral = result["referral"]
        assert referral.referrer_id == self.REFERRER_ID
        assert referral.referred_id == self.REFERRED_ID
        assert referral.status == ReferralStatus.PENDING.value
        assert referral.email_verified is False
        assert referral.reward_granted is False
        assert referral.welcome_credit_granted is False

    def test_apply_code_updates_stats(self, test_db, referral_service):
        """Test that applying code updates referral code statistics."""
        code = referral_service.get_or_create_code(self.REFERRER_ID)

        initial_signups = code.total_signups

        referral_service.apply_code(
            referred_user_id=self.REFERRED_ID,
            code=code.code,
            skip_fraud_check=True
        )

        test_db.refresh(code)

        assert code.total_signups == initial_signups + 1
        assert code.last_used_at is not None

    def test_apply_code_with_ip(self, referral_service):
        """Test applying code with IP address for tracking."""
        code = referral_service.get_or_create_code(self.REFERRER_ID)

        result = referral_service.apply_code(
            referred_user_id=self.REFERRED_ID,
            code=code.code,
            referred_ip="192.168.1.100",
            skip_fraud_check=True
        )

        assert result["success"] is True
        assert result["referral"].referred_ip == "192.168.1.100"

    def test_apply_code_sets_correct_thresholds(self, referral_service):
        """Test that apply code sets correct reward thresholds."""
        code = referral_service.get_or_create_code(self.REFERRER_ID)

        result = referral_service.apply_code(
            referred_user_id=self.REFERRED_ID,
            code=code.code,
            skip_fraud_check=True
        )

        referral = result["referral"]
        assert referral.spend_threshold == SPEND_THRESHOLD
        assert referral.referrer_reward_amount == REFERRER_REWARD_AMOUNT
        assert referral.referred_welcome_credit == REFERRED_WELCOME_CREDIT

    def test_apply_invalid_code(self, referral_service):
        """Test applying invalid code returns error."""
        result = referral_service.apply_code(
            referred_user_id=self.REFERRED_ID,
            code="INVALIDCODE",
            skip_fraud_check=True
        )

        assert result["success"] is False
        assert "invalid" in result["error"].lower()
        assert result["referral"] is None


# =============================================================================
# TEST: RECORD CLICK
# =============================================================================

class TestRecordClick:
    """Tests for recording clicks on referral links."""

    USER_ID = "click-user"

    def test_record_click_success(self, test_db, referral_service):
        """Test recording a click on a referral code."""
        code = referral_service.get_or_create_code(self.USER_ID)
        initial_clicks = code.total_clicks

        result = referral_service.record_click(code.code)

        assert result is True

        test_db.refresh(code)
        assert code.total_clicks == initial_clicks + 1
        assert code.last_used_at is not None

    def test_record_click_invalid_code(self, referral_service):
        """Test recording click on invalid code returns False."""
        result = referral_service.record_click("INVALIDCODE")
        assert result is False

    def test_record_click_case_insensitive(self, test_db, referral_service):
        """Test that click recording works with lowercase code."""
        code = referral_service.get_or_create_code(self.USER_ID)
        initial_clicks = code.total_clicks

        result = referral_service.record_click(code.code.lower())

        assert result is True

        test_db.refresh(code)
        assert code.total_clicks == initial_clicks + 1

    def test_record_click_inactive_code(self, test_db, referral_service):
        """Test recording click on inactive code returns False."""
        code = referral_service.get_or_create_code(self.USER_ID)
        code.is_active = False
        test_db.commit()

        result = referral_service.record_click(code.code)
        assert result is False


# =============================================================================
# TEST: REFERRER STATS
# =============================================================================

class TestReferrerStats:
    """Tests for referrer statistics."""

    REFERRER_ID = "stats-referrer"
    REFERRED_ID = "stats-referred"

    def test_get_stats_no_code(self, referral_service):
        """Test getting stats for user without code."""
        stats = referral_service.get_referrer_stats("no-code-user")

        assert stats["has_code"] is False
        assert stats["code"] is None
        assert stats["total_referrals"] == 0
        assert stats["total_earnings"] == 0.0

    def test_get_stats_with_code_no_referrals(self, referral_service):
        """Test getting stats for user with code but no referrals."""
        code = referral_service.get_or_create_code(self.REFERRER_ID)

        stats = referral_service.get_referrer_stats(self.REFERRER_ID)

        assert stats["has_code"] is True
        assert stats["code"] == code.code
        assert stats["total_referrals"] == 0
        assert stats["pending_referrals"] == 0
        assert stats["completed_referrals"] == 0
        assert stats["total_earnings"] == 0.0

    def test_get_stats_with_referrals(self, referral_service):
        """Test getting stats for user with referrals."""
        code = referral_service.get_or_create_code(self.REFERRER_ID)

        # Apply code
        referral_service.apply_code(
            referred_user_id=self.REFERRED_ID,
            code=code.code,
            skip_fraud_check=True
        )

        stats = referral_service.get_referrer_stats(self.REFERRER_ID)

        assert stats["has_code"] is True
        assert stats["total_referrals"] == 1
        assert stats["pending_referrals"] == 1
        assert stats["completed_referrals"] == 0


# =============================================================================
# TEST: GET REFERRALS
# =============================================================================

class TestGetReferrals:
    """Tests for retrieving referrals."""

    REFERRER_ID = "get-referrer"

    def test_get_referral_by_referred(self, referral_service):
        """Test getting referral by referred user ID."""
        code = referral_service.get_or_create_code(self.REFERRER_ID)
        referred_id = "get-referred-1"

        referral_service.apply_code(
            referred_user_id=referred_id,
            code=code.code,
            skip_fraud_check=True
        )

        referral = referral_service.get_referral_by_referred(referred_id)

        assert referral is not None
        assert referral.referred_id == referred_id
        assert referral.referrer_id == self.REFERRER_ID

    def test_get_referral_by_referred_not_found(self, referral_service):
        """Test getting referral for non-referred user returns None."""
        result = referral_service.get_referral_by_referred("non-referred-user")
        assert result is None

    def test_get_referrals_by_referrer(self, referral_service):
        """Test getting all referrals by referrer."""
        code = referral_service.get_or_create_code(self.REFERRER_ID)

        # Create multiple referrals
        for i in range(3):
            referral_service.apply_code(
                referred_user_id=f"multiple-referred-{i}",
                code=code.code,
                skip_fraud_check=True
            )

        referrals = referral_service.get_referrals_by_referrer(self.REFERRER_ID)

        assert len(referrals) == 3
        for referral in referrals:
            assert referral.referrer_id == self.REFERRER_ID

    def test_get_referrals_by_referrer_empty(self, referral_service):
        """Test getting referrals for referrer with no referrals."""
        referral_service.get_or_create_code(self.REFERRER_ID)

        referrals = referral_service.get_referrals_by_referrer(self.REFERRER_ID)

        assert referrals == []

    def test_get_referrals_by_referrer_with_status_filter(self, test_db, referral_service):
        """Test filtering referrals by status."""
        code = referral_service.get_or_create_code(self.REFERRER_ID)

        # Create referrals
        for i in range(2):
            referral_service.apply_code(
                referred_user_id=f"status-referred-{i}",
                code=code.code,
                skip_fraud_check=True
            )

        # Get only pending referrals
        pending = referral_service.get_referrals_by_referrer(
            self.REFERRER_ID,
            status=ReferralStatus.PENDING.value
        )

        assert len(pending) == 2
        for referral in pending:
            assert referral.status == ReferralStatus.PENDING.value


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
