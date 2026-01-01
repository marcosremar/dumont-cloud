"""
E2E Test: Unsubscribe Flow

Complete end-to-end tests for the unsubscribe functionality:
1. Click unsubscribe link in email (simulate)
2. Verify confirmation page displays
3. Verify database unsubscribed=true
4. Verify user excluded from next send batch

This test file covers the full unsubscribe journey from email link
to database state change and batch exclusion verification.
"""

import pytest
import httpx
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import services for testing
try:
    from src.services.email_composer import EmailComposer
    from src.models.email_preferences import EmailPreference
    from src.config.database import SessionLocal, Base, engine
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    EmailComposer = None
    EmailPreference = None
    SessionLocal = None


# Test configuration
BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
TEST_USER_ID = "test-unsubscribe-user-001"
TEST_USER_EMAIL = "test-unsubscribe@example.com"


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def http_client():
    """HTTP client without authentication."""
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        yield client


@pytest.fixture
def db_session():
    """Database session for direct database verification."""
    if not HAS_DATABASE:
        pytest.skip("Database not available")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def email_composer():
    """Email composer instance for token generation."""
    if not HAS_DATABASE:
        pytest.skip("EmailComposer not available")
    return EmailComposer()


@pytest.fixture
def test_user_preference(db_session):
    """Create a test user preference for unsubscribe testing."""
    if not HAS_DATABASE:
        pytest.skip("Database not available")

    # Check if user already exists
    existing = db_session.query(EmailPreference).filter(
        EmailPreference.user_id == TEST_USER_ID
    ).first()

    if existing:
        # Reset to subscribed state
        existing.unsubscribed = False
        existing.frequency = "weekly"
        db_session.commit()
        db_session.refresh(existing)
        yield existing
    else:
        # Create new user preference
        preference = EmailPreference(
            user_id=TEST_USER_ID,
            email=TEST_USER_EMAIL,
            frequency="weekly",
            unsubscribed=False,
            timezone="UTC",
        )
        db_session.add(preference)
        db_session.commit()
        db_session.refresh(preference)
        yield preference

    # Cleanup: Reset state (don't delete, might be used in other tests)
    db_session.rollback()


# ============================================================
# Unit Tests: Token Generation and Verification
# ============================================================

@pytest.mark.e2e_unsubscribe
class TestUnsubscribeTokens:
    """Tests for unsubscribe token generation and verification."""

    def test_generate_token_returns_string(self, email_composer):
        """Token generation should return a non-empty string."""
        token = email_composer.generate_unsubscribe_token(TEST_USER_ID)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 20  # Should be a reasonable length
        print(f"  Generated token length: {len(token)}")

    def test_verify_valid_token(self, email_composer):
        """Valid token should return the original user_id."""
        # Generate a token
        token = email_composer.generate_unsubscribe_token(TEST_USER_ID)

        # Verify it
        result = email_composer.verify_unsubscribe_token(token)

        assert result == TEST_USER_ID
        print(f"  Token verified for user: {result}")

    def test_verify_invalid_token(self, email_composer):
        """Invalid token should return None."""
        result = email_composer.verify_unsubscribe_token("invalid_token_abc123")

        assert result is None
        print("  Invalid token correctly rejected")

    def test_verify_tampered_token(self, email_composer):
        """Tampered token should return None."""
        # Generate a valid token
        token = email_composer.generate_unsubscribe_token(TEST_USER_ID)

        # Tamper with it (change a character)
        tampered = token[:-1] + ("X" if token[-1] != "X" else "Y")

        result = email_composer.verify_unsubscribe_token(tampered)

        assert result is None
        print("  Tampered token correctly rejected")

    def test_token_contains_user_id(self, email_composer):
        """Different users should get different tokens."""
        token1 = email_composer.generate_unsubscribe_token("user-001")
        token2 = email_composer.generate_unsubscribe_token("user-002")

        assert token1 != token2
        print("  Different users get different tokens")


# ============================================================
# API Tests: Unsubscribe Endpoint
# ============================================================

@pytest.mark.e2e_unsubscribe
class TestUnsubscribeEndpoint:
    """Tests for the unsubscribe API endpoint."""

    def test_get_unsubscribe_returns_html(self, http_client):
        """GET /api/v1/unsubscribe should return HTML page."""
        response = http_client.get(
            "/api/v1/unsubscribe",
            params={"token": "test_html_response"}
        )

        # Should return 200 with HTML content
        assert response.status_code == 200

        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type

        html = response.text
        assert "<!DOCTYPE html>" in html
        print("  GET endpoint returns HTML")

    def test_post_unsubscribe_returns_json(self, http_client):
        """POST /api/v1/unsubscribe should return JSON."""
        response = http_client.post(
            "/api/v1/unsubscribe",
            params={"token": "test_json_response"}
        )

        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

        data = response.json()
        assert "detail" in data  # Error response for invalid token
        print("  POST endpoint returns JSON")

    def test_unsubscribe_no_auth_required(self, http_client):
        """Unsubscribe should work without authentication (GDPR/CAN-SPAM)."""
        # GET request
        get_response = http_client.get(
            "/api/v1/unsubscribe",
            params={"token": "test_no_auth"}
        )

        assert get_response.status_code not in [401, 403]

        # POST request
        post_response = http_client.post(
            "/api/v1/unsubscribe",
            params={"token": "test_no_auth"}
        )

        assert post_response.status_code not in [401, 403]
        print("  No authentication required (GDPR/CAN-SPAM compliant)")

    def test_unsubscribe_missing_token(self, http_client):
        """Missing token should return 422."""
        response = http_client.get("/api/v1/unsubscribe")

        assert response.status_code == 422  # FastAPI validation error
        print("  Missing token returns 422")

    def test_unsubscribe_error_page_content(self, http_client):
        """Error page should have correct content."""
        response = http_client.get(
            "/api/v1/unsubscribe",
            params={"token": "invalid_token_for_content_test"}
        )

        assert response.status_code == 200  # Returns error page, not error status

        html = response.text.lower()

        # Should contain error indication
        assert any(word in html for word in ["error", "failed", "invalid"])

        # Should contain DumontCloud branding
        assert "dumontcloud" in html

        # Should have link to settings
        assert "/settings/email-preferences" in html

        print("  Error page has correct content")


# ============================================================
# E2E Tests: Complete Unsubscribe Flow with Database
# ============================================================

@pytest.mark.e2e_unsubscribe
class TestUnsubscribeE2EFlow:
    """Complete end-to-end tests for unsubscribe flow."""

    def test_unsubscribe_with_valid_token(self, http_client, db_session, email_composer, test_user_preference):
        """Complete flow: valid token -> confirmation page -> database updated."""
        # Step 1: Verify user starts as subscribed
        assert test_user_preference.unsubscribed == False
        assert test_user_preference.frequency == "weekly"
        user_id = test_user_preference.user_id
        print(f"  Step 1: User {user_id} starts as subscribed")

        # Step 2: Generate valid unsubscribe token
        token = email_composer.generate_unsubscribe_token(user_id)
        assert token is not None
        print(f"  Step 2: Generated token (length={len(token)})")

        # Step 3: Click unsubscribe link (GET request)
        response = http_client.get(
            "/api/v1/unsubscribe",
            params={"token": token}
        )

        # Step 4: Verify confirmation page displays
        assert response.status_code == 200

        html = response.text.lower()
        # Should show success message
        assert any(word in html for word in ["unsubscribed", "removed", "success"])
        print("  Step 3-4: Confirmation page displayed")

        # Step 5: Verify database updated
        db_session.expire_all()  # Refresh from database
        updated_pref = db_session.query(EmailPreference).filter(
            EmailPreference.user_id == user_id
        ).first()

        assert updated_pref is not None
        assert updated_pref.unsubscribed == True
        assert updated_pref.frequency == "none"
        print(f"  Step 5: Database updated - unsubscribed={updated_pref.unsubscribed}, frequency={updated_pref.frequency}")

        print("  Complete unsubscribe flow successful!")

    def test_unsubscribe_idempotent(self, http_client, db_session, email_composer, test_user_preference):
        """Clicking unsubscribe twice should not cause errors."""
        user_id = test_user_preference.user_id
        token = email_composer.generate_unsubscribe_token(user_id)

        # First unsubscribe
        response1 = http_client.get(
            "/api/v1/unsubscribe",
            params={"token": token}
        )
        assert response1.status_code == 200
        print("  First unsubscribe: success")

        # Refresh database state
        db_session.expire_all()
        pref = db_session.query(EmailPreference).filter(
            EmailPreference.user_id == user_id
        ).first()
        assert pref.unsubscribed == True

        # Second unsubscribe (same token)
        response2 = http_client.get(
            "/api/v1/unsubscribe",
            params={"token": token}
        )
        assert response2.status_code == 200
        print("  Second unsubscribe: success (idempotent)")

        # Should show "already unsubscribed" message
        html = response2.text.lower()
        assert any(word in html for word in ["already", "unsubscribed", "no action"])
        print("  Shows 'already unsubscribed' message")

        # Database state should remain unchanged
        db_session.expire_all()
        pref = db_session.query(EmailPreference).filter(
            EmailPreference.user_id == user_id
        ).first()
        assert pref.unsubscribed == True
        print("  Database state remains unsubscribed")


# ============================================================
# E2E Tests: Batch Exclusion After Unsubscribe
# ============================================================

@pytest.mark.e2e_unsubscribe
class TestBatchExclusionAfterUnsubscribe:
    """Verify unsubscribed users are excluded from email batches."""

    def test_unsubscribed_user_not_in_eligible_users(self, db_session, email_composer, test_user_preference):
        """Unsubscribed user should not appear in eligible users query."""
        user_id = test_user_preference.user_id

        # Unsubscribe the user directly in database
        test_user_preference.unsubscribed = True
        test_user_preference.frequency = "none"
        db_session.commit()
        print(f"  Unsubscribed user {user_id}")

        # Query eligible users (same query used by scheduler)
        eligible_users = db_session.query(EmailPreference).filter(
            EmailPreference.frequency == "weekly",
            EmailPreference.unsubscribed == False,
        ).all()

        # User should NOT be in the list
        eligible_user_ids = [u.user_id for u in eligible_users]
        assert user_id not in eligible_user_ids
        print(f"  User {user_id} correctly excluded from eligible users")

    def test_subscribed_user_in_eligible_users(self, db_session, test_user_preference):
        """Subscribed user should appear in eligible users query."""
        user_id = test_user_preference.user_id

        # Ensure user is subscribed
        test_user_preference.unsubscribed = False
        test_user_preference.frequency = "weekly"
        db_session.commit()
        print(f"  User {user_id} is subscribed with frequency=weekly")

        # Query eligible users
        eligible_users = db_session.query(EmailPreference).filter(
            EmailPreference.frequency == "weekly",
            EmailPreference.unsubscribed == False,
        ).all()

        # User SHOULD be in the list
        eligible_user_ids = [u.user_id for u in eligible_users]
        assert user_id in eligible_user_ids
        print(f"  User {user_id} correctly included in eligible users")

    def test_should_receive_email_method(self, test_user_preference):
        """EmailPreference.should_receive_email() should work correctly."""
        # When subscribed
        test_user_preference.unsubscribed = False
        test_user_preference.frequency = "weekly"

        assert test_user_preference.should_receive_email("weekly") == True
        assert test_user_preference.should_receive_email("monthly") == False
        print("  Subscribed: should_receive_email('weekly') = True")

        # When unsubscribed
        test_user_preference.unsubscribed = True

        assert test_user_preference.should_receive_email("weekly") == False
        assert test_user_preference.should_receive_email("monthly") == False
        print("  Unsubscribed: should_receive_email() = False")

        # When frequency is 'none'
        test_user_preference.unsubscribed = False
        test_user_preference.frequency = "none"

        assert test_user_preference.should_receive_email("weekly") == False
        print("  Frequency='none': should_receive_email() = False")

    def test_unsubscribe_updates_both_flags(self, http_client, db_session, email_composer, test_user_preference):
        """Unsubscribe should set both unsubscribed=True AND frequency='none'."""
        user_id = test_user_preference.user_id

        # Ensure user starts subscribed
        test_user_preference.unsubscribed = False
        test_user_preference.frequency = "weekly"
        db_session.commit()

        # Generate token and unsubscribe
        token = email_composer.generate_unsubscribe_token(user_id)
        http_client.get("/api/v1/unsubscribe", params={"token": token})

        # Verify both flags updated
        db_session.expire_all()
        pref = db_session.query(EmailPreference).filter(
            EmailPreference.user_id == user_id
        ).first()

        assert pref.unsubscribed == True
        assert pref.frequency == "none"
        print("  Both unsubscribed=True AND frequency='none' set correctly")


# ============================================================
# E2E Tests: Resubscribe After Unsubscribe
# ============================================================

@pytest.mark.e2e_unsubscribe
class TestResubscribeAfterUnsubscribe:
    """Tests for resubscribing after unsubscribe via settings page."""

    def test_can_resubscribe_via_api(self, http_client, db_session, email_composer, test_user_preference):
        """User can resubscribe after unsubscribing."""
        user_id = test_user_preference.user_id

        # First, unsubscribe
        token = email_composer.generate_unsubscribe_token(user_id)
        http_client.get("/api/v1/unsubscribe", params={"token": token})

        db_session.expire_all()
        pref = db_session.query(EmailPreference).filter(
            EmailPreference.user_id == user_id
        ).first()
        assert pref.unsubscribed == True
        print("  User unsubscribed successfully")

        # Resubscribe via direct database update (simulating settings page)
        pref.unsubscribed = False
        pref.frequency = "weekly"
        db_session.commit()

        db_session.expire_all()
        pref = db_session.query(EmailPreference).filter(
            EmailPreference.user_id == user_id
        ).first()

        assert pref.unsubscribed == False
        assert pref.frequency == "weekly"
        print("  User resubscribed successfully")

        # Should now be eligible for emails again
        eligible_users = db_session.query(EmailPreference).filter(
            EmailPreference.frequency == "weekly",
            EmailPreference.unsubscribed == False,
        ).all()

        eligible_user_ids = [u.user_id for u in eligible_users]
        assert user_id in eligible_user_ids
        print("  Resubscribed user now eligible for emails")


# ============================================================
# Pytest Configuration
# ============================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "e2e_unsubscribe: End-to-end unsubscribe flow tests"
    )


# ============================================================
# Standalone Test Runner
# ============================================================

if __name__ == "__main__":
    """Allow running tests directly with: python test_e2e_unsubscribe_flow.py"""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "-s", "--tb=short"],
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    sys.exit(result.returncode)
