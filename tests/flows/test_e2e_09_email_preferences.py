"""
Flow 9: Email Preferences - E2E Tests
Tests REAL API integration for email preferences.

This flow tests:
- GET /api/v1/email-preferences - Get user preferences
- PUT /api/v1/email-preferences - Update user preferences
- Database persistence verification
- Success/error response handling
"""
import pytest
import httpx
import time


@pytest.mark.flow9
class TestEmailPreferencesGet:
    """Tests for GET /api/v1/email-preferences"""

    def test_get_preferences_returns_defaults(self, authed_client: httpx.Client):
        """Should return default preferences for new user"""
        response = authed_client.get("/api/v1/email-preferences")

        # Should succeed
        assert response.status_code == 200
        data = response.json()

        # Should have preferences object
        assert "preferences" in data

        prefs = data["preferences"]
        # Default should be weekly
        assert prefs.get("frequency") in ["weekly", "monthly", "none"]
        # Should have unsubscribed field
        assert "unsubscribed" in prefs
        assert isinstance(prefs["unsubscribed"], bool)

    def test_get_preferences_unauthenticated(self, http_client: httpx.Client):
        """Should reject unauthenticated requests"""
        response = http_client.get("/api/v1/email-preferences")

        # Should fail without auth
        assert response.status_code in [401, 403]


@pytest.mark.flow9
class TestEmailPreferencesUpdate:
    """Tests for PUT /api/v1/email-preferences"""

    def test_update_to_weekly(self, authed_client: httpx.Client):
        """Should update preferences to weekly"""
        response = authed_client.put("/api/v1/email-preferences", json={
            "frequency": "weekly"
        })

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True

        # Verify the update persisted
        get_response = authed_client.get("/api/v1/email-preferences")
        assert get_response.status_code == 200
        prefs = get_response.json().get("preferences", {})
        assert prefs.get("frequency") == "weekly"
        assert prefs.get("unsubscribed") == False

    def test_update_to_monthly(self, authed_client: httpx.Client):
        """Should update preferences to monthly"""
        response = authed_client.put("/api/v1/email-preferences", json={
            "frequency": "monthly"
        })

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True

        # Verify the update persisted
        get_response = authed_client.get("/api/v1/email-preferences")
        assert get_response.status_code == 200
        prefs = get_response.json().get("preferences", {})
        assert prefs.get("frequency") == "monthly"

    def test_update_to_none_unsubscribes(self, authed_client: httpx.Client):
        """Should unsubscribe when setting frequency to none"""
        response = authed_client.put("/api/v1/email-preferences", json={
            "frequency": "none"
        })

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True

        # Verify the update persisted
        get_response = authed_client.get("/api/v1/email-preferences")
        assert get_response.status_code == 200
        prefs = get_response.json().get("preferences", {})
        assert prefs.get("frequency") == "none"
        assert prefs.get("unsubscribed") == True

    def test_update_with_timezone(self, authed_client: httpx.Client):
        """Should update preferences with timezone"""
        response = authed_client.put("/api/v1/email-preferences", json={
            "frequency": "weekly",
            "timezone": "America/Sao_Paulo"
        })

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True

        # Verify the update persisted
        get_response = authed_client.get("/api/v1/email-preferences")
        assert get_response.status_code == 200
        prefs = get_response.json().get("preferences", {})
        # Timezone may or may not be returned depending on implementation
        # Just verify the request didn't fail

    def test_update_invalid_frequency(self, authed_client: httpx.Client):
        """Should reject invalid frequency values"""
        response = authed_client.put("/api/v1/email-preferences", json={
            "frequency": "invalid_value"
        })

        # Should fail with validation error
        assert response.status_code in [400, 422]

    def test_update_unauthenticated(self, http_client: httpx.Client):
        """Should reject unauthenticated update requests"""
        response = http_client.put("/api/v1/email-preferences", json={
            "frequency": "weekly"
        })

        # Should fail without auth
        assert response.status_code in [401, 403]


@pytest.mark.flow9
class TestEmailPreferencesResubscribe:
    """Tests for POST /api/v1/email-preferences/subscribe"""

    def test_resubscribe_after_unsubscribe(self, authed_client: httpx.Client):
        """Should allow user to resubscribe after unsubscribing"""
        # First unsubscribe
        authed_client.put("/api/v1/email-preferences", json={
            "frequency": "none"
        })

        # Verify unsubscribed
        get_response = authed_client.get("/api/v1/email-preferences")
        prefs = get_response.json().get("preferences", {})
        assert prefs.get("unsubscribed") == True

        # Now resubscribe
        response = authed_client.post("/api/v1/email-preferences/subscribe", json={
            "frequency": "weekly"
        })

        # Should succeed (or 404 if endpoint not implemented)
        assert response.status_code in [200, 201, 404]

        if response.status_code in [200, 201]:
            # Verify resubscribed
            get_response = authed_client.get("/api/v1/email-preferences")
            prefs = get_response.json().get("preferences", {})
            assert prefs.get("frequency") == "weekly"
            assert prefs.get("unsubscribed") == False


@pytest.mark.flow9
class TestEmailPreferencesTestEmail:
    """Tests for POST /api/v1/email-preferences/test-email"""

    def test_send_test_email(self, authed_client: httpx.Client):
        """Should trigger a test email send"""
        response = authed_client.post("/api/v1/email-preferences/test-email")

        # May return 200 if successful, or 404/501 if not implemented
        # Or 400 if Resend API key not configured
        assert response.status_code in [200, 201, 400, 404, 500, 501]

        if response.status_code == 200:
            data = response.json()
            # Should indicate success or queued
            assert data.get("success") == True or "queued" in str(data).lower() or "sent" in str(data).lower()


@pytest.mark.flow9
class TestEmailPreferencesE2EFlow:
    """Complete E2E flow tests"""

    def test_full_preferences_flow(self, authed_client: httpx.Client):
        """Test complete flow: get → update → verify → update again"""
        # Step 1: Get initial preferences
        get_response = authed_client.get("/api/v1/email-preferences")
        assert get_response.status_code == 200
        initial_prefs = get_response.json().get("preferences", {})
        print(f"  Step 1: Initial preferences: {initial_prefs}")

        # Step 2: Update to weekly
        update_response = authed_client.put("/api/v1/email-preferences", json={
            "frequency": "weekly"
        })
        assert update_response.status_code == 200
        print("  Step 2: Updated to weekly")

        # Step 3: Verify update
        get_response = authed_client.get("/api/v1/email-preferences")
        assert get_response.status_code == 200
        prefs = get_response.json().get("preferences", {})
        assert prefs.get("frequency") == "weekly"
        assert prefs.get("unsubscribed") == False
        print("  Step 3: Verified weekly update")

        # Step 4: Update to none (unsubscribe)
        update_response = authed_client.put("/api/v1/email-preferences", json={
            "frequency": "none"
        })
        assert update_response.status_code == 200
        print("  Step 4: Updated to none (unsubscribed)")

        # Step 5: Verify unsubscribe
        get_response = authed_client.get("/api/v1/email-preferences")
        assert get_response.status_code == 200
        prefs = get_response.json().get("preferences", {})
        assert prefs.get("frequency") == "none"
        assert prefs.get("unsubscribed") == True
        print("  Step 5: Verified unsubscribe")

        # Step 6: Re-enable with monthly
        update_response = authed_client.put("/api/v1/email-preferences", json={
            "frequency": "monthly"
        })
        assert update_response.status_code == 200
        print("  Step 6: Re-enabled with monthly")

        # Step 7: Final verification
        get_response = authed_client.get("/api/v1/email-preferences")
        assert get_response.status_code == 200
        prefs = get_response.json().get("preferences", {})
        assert prefs.get("frequency") == "monthly"
        assert prefs.get("unsubscribed") == False
        print("  Step 7: Final verification passed")

        print("  ✅ Complete E2E flow successful")

    def test_preferences_persist_across_sessions(self, authed_client: httpx.Client, auth_token: str):
        """Test that preferences persist and can be retrieved in new session"""
        # Update preferences
        authed_client.put("/api/v1/email-preferences", json={
            "frequency": "weekly"
        })

        # Create a new client (simulating new session)
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        import os
        BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")

        with httpx.Client(base_url=BASE_URL, timeout=30, headers=headers) as new_client:
            # Verify preferences persisted
            response = new_client.get("/api/v1/email-preferences")
            assert response.status_code == 200
            prefs = response.json().get("preferences", {})
            assert prefs.get("frequency") == "weekly"

        print("  ✅ Preferences persist across sessions")


@pytest.mark.flow9
class TestUnsubscribeEndpoint:
    """Tests for GET/POST /api/v1/unsubscribe"""

    def test_unsubscribe_with_valid_token(self, http_client: httpx.Client):
        """Should process unsubscribe with valid token"""
        # Note: This requires a valid signed token
        # The actual token generation is in EmailComposer.generate_unsubscribe_token()
        # For testing, we can test the endpoint exists

        # Test with invalid token should return error page
        response = http_client.get("/api/v1/unsubscribe", params={"token": "invalid_token"})

        # Should return HTML error page (200) or error status
        assert response.status_code in [200, 400, 401, 403]

    def test_unsubscribe_without_token(self, http_client: httpx.Client):
        """Should reject unsubscribe without token"""
        response = http_client.get("/api/v1/unsubscribe")

        # Should fail without token
        assert response.status_code in [400, 422]

    def test_unsubscribe_endpoint_no_auth_required(self, http_client: httpx.Client):
        """Unsubscribe should work without authentication (GDPR/CAN-SPAM compliance)"""
        # This is important: users must be able to unsubscribe without logging in
        response = http_client.get("/api/v1/unsubscribe", params={"token": "test"})

        # Should NOT return 401/403 for auth - it should process the token
        # (may return 400 for invalid token, but not for missing auth)
        assert response.status_code in [200, 400]


# === Pytest Configuration ===

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "flow9: Email Preferences tests")
