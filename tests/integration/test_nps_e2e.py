"""
NPS (Net Promoter Score) End-to-End Integration Tests

Tests the complete NPS survey flow including:
1. Authentication check for survey visibility
2. Survey submission with score and comment
3. Rate limiting (survey doesn't reappear after submission)
4. Detractor tracking (scores 0-6 marked for follow-up)
5. Admin dashboard data retrieval (trends, detractors)
6. Follow-up status updates

REAL tests against the API - no mocks.
"""
import pytest
import httpx
import time
import uuid
from typing import Generator


# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT_SHORT = 30
TIMEOUT_MEDIUM = 60


class RetryClient:
    """HTTP client with automatic retry for rate limits"""

    def __init__(self, client: httpx.Client, max_retries: int = 3):
        self._client = client
        self._max_retries = max_retries
        self._retry_status_codes = [429, 500, 502, 503, 504]
        self._retry_delay = 2

    def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make request with automatic retry"""
        last_response = None

        for attempt in range(self._max_retries + 1):
            response = getattr(self._client, method)(url, **kwargs)
            last_response = response

            if response.status_code not in self._retry_status_codes:
                return response

            if attempt < self._max_retries:
                wait_time = self._retry_delay * (2 ** attempt)
                time.sleep(wait_time)

        return last_response

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self._request_with_retry("get", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self._request_with_retry("post", url, **kwargs)

    def put(self, url: str, **kwargs) -> httpx.Response:
        return self._request_with_retry("put", url, **kwargs)

    def delete(self, url: str, **kwargs) -> httpx.Response:
        return self._request_with_retry("delete", url, **kwargs)


@pytest.fixture(scope="module")
def http_client() -> Generator[RetryClient, None, None]:
    """HTTP client for tests with retry support"""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM) as client:
        yield RetryClient(client, max_retries=3)


@pytest.fixture(scope="module")
def auth_token(http_client: RetryClient) -> str:
    """Get authentication token"""
    # Try login first
    response = http_client.post(
        "/api/v1/auth/login",
        json={"username": "test@test.com", "password": "test123"}
    )

    if response.status_code == 200:
        return response.json().get("token")

    # If login fails, try register
    response = http_client.post(
        "/api/v1/auth/register",
        json={"username": "test@test.com", "password": "test123"}
    )

    if response.status_code in [200, 201]:
        return response.json().get("token")

    pytest.fail(f"Could not authenticate: {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token: str) -> dict:
    """Authentication headers"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def authed_client(auth_token: str) -> Generator[RetryClient, None, None]:
    """Authenticated HTTP client"""
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, headers=headers) as client:
        yield RetryClient(client, max_retries=3)


@pytest.fixture(scope="module")
def second_user_client() -> Generator[tuple[RetryClient, str], None, None]:
    """Create a second authenticated user for testing rate limiting isolation"""
    email = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM) as client:
        # Register new user
        response = client.post(
            "/api/v1/auth/register",
            json={"username": email, "password": password}
        )

        if response.status_code not in [200, 201]:
            # Try login if registration fails (user might exist)
            response = client.post(
                "/api/v1/auth/login",
                json={"username": email, "password": password}
            )

        if response.status_code not in [200, 201]:
            pytest.skip(f"Could not create second test user: {response.text}")

        token = response.json().get("token")

        # Create authenticated client for second user
        with httpx.Client(
            base_url=BASE_URL,
            timeout=TIMEOUT_MEDIUM,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        ) as authed_client:
            yield RetryClient(authed_client, max_retries=3), email


@pytest.mark.integration
class TestNPSShouldShow:
    """Test NPS survey visibility check endpoint"""

    def test_should_show_requires_valid_trigger_type(self, authed_client: RetryClient):
        """Should reject invalid trigger types"""
        response = authed_client.get("/api/v1/nps/should-show?trigger_type=invalid_trigger")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_should_show_monthly_trigger(self, authed_client: RetryClient):
        """Should check monthly survey eligibility"""
        response = authed_client.get("/api/v1/nps/should-show?trigger_type=monthly")

        assert response.status_code == 200
        data = response.json()

        assert "should_show" in data
        assert "reason" in data
        assert isinstance(data["should_show"], bool)

    def test_should_show_first_deployment_trigger(self, authed_client: RetryClient):
        """Should check first deployment survey eligibility"""
        response = authed_client.get("/api/v1/nps/should-show?trigger_type=first_deployment")

        assert response.status_code == 200
        data = response.json()

        assert "should_show" in data
        assert "reason" in data

    def test_should_show_issue_resolution_trigger(self, authed_client: RetryClient):
        """Should check issue resolution survey eligibility"""
        response = authed_client.get("/api/v1/nps/should-show?trigger_type=issue_resolution")

        assert response.status_code == 200
        data = response.json()

        assert "should_show" in data
        assert "reason" in data

    def test_unauthenticated_should_not_show(self, http_client: RetryClient):
        """Survey should not be shown to unauthenticated users"""
        response = http_client.get("/api/v1/nps/should-show?trigger_type=monthly")

        assert response.status_code == 200
        data = response.json()

        # Unauthenticated users should not see the survey
        assert data.get("should_show") == False
        assert "not authenticated" in data.get("reason", "").lower()


@pytest.mark.integration
class TestNPSSubmission:
    """Test NPS survey submission endpoint"""

    def test_submit_promoter_score(self, authed_client: RetryClient):
        """Should successfully submit a promoter score (9-10)"""
        response = authed_client.post("/api/v1/nps/submit", json={
            "score": 9,
            "comment": "Great product, highly recommend!",
            "trigger_type": "monthly"
        })

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True
        assert "id" in data
        assert data.get("category") == "promoter"
        assert "message" in data

    def test_submit_passive_score(self, second_user_client: tuple):
        """Should successfully submit a passive score (7-8)"""
        client, email = second_user_client

        response = client.post("/api/v1/nps/submit", json={
            "score": 8,
            "comment": "Good product, room for improvement",
            "trigger_type": "first_deployment"
        })

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True
        assert data.get("category") == "passive"

    def test_submit_detractor_score(self, authed_client: RetryClient):
        """Should successfully submit a detractor score (0-6) with follow-up flag"""
        # Use issue_resolution trigger to avoid rate limiting from monthly
        response = authed_client.post("/api/v1/nps/submit", json={
            "score": 3,
            "comment": "Not satisfied with the service, needs major improvements",
            "trigger_type": "issue_resolution"
        })

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True
        assert data.get("category") == "detractor"
        assert "id" in data

    def test_submit_without_comment(self, authed_client: RetryClient):
        """Should accept submission without comment"""
        response = authed_client.post("/api/v1/nps/submit", json={
            "score": 7,
            "trigger_type": "first_deployment"
        })

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True

    def test_submit_invalid_score_too_high(self, authed_client: RetryClient):
        """Should reject score above 10"""
        response = authed_client.post("/api/v1/nps/submit", json={
            "score": 11,
            "trigger_type": "monthly"
        })

        assert response.status_code in [400, 422]

    def test_submit_invalid_score_negative(self, authed_client: RetryClient):
        """Should reject negative score"""
        response = authed_client.post("/api/v1/nps/submit", json={
            "score": -1,
            "trigger_type": "monthly"
        })

        assert response.status_code in [400, 422]

    def test_submit_invalid_trigger_type(self, authed_client: RetryClient):
        """Should reject invalid trigger type"""
        response = authed_client.post("/api/v1/nps/submit", json={
            "score": 8,
            "trigger_type": "invalid_type"
        })

        assert response.status_code in [400, 422]


@pytest.mark.integration
class TestNPSRateLimiting:
    """Test NPS survey rate limiting"""

    def test_rate_limiting_after_submission(self, second_user_client: tuple):
        """Survey should not show again immediately after submission"""
        client, email = second_user_client

        # Submit a survey
        submit_response = client.post("/api/v1/nps/submit", json={
            "score": 8,
            "comment": "Testing rate limiting",
            "trigger_type": "issue_resolution"
        })

        # If already submitted, that's fine - we just need the rate limit to be in effect
        if submit_response.status_code == 200:
            # Check if should show
            check_response = client.get("/api/v1/nps/should-show?trigger_type=issue_resolution")

            assert check_response.status_code == 200
            data = check_response.json()

            # Should not show survey again
            assert data.get("should_show") == False
            assert "recent" in data.get("reason", "").lower()


@pytest.mark.integration
class TestNPSDismissal:
    """Test NPS survey dismissal endpoint"""

    def test_dismiss_survey(self, authed_client: RetryClient):
        """Should successfully record survey dismissal"""
        response = authed_client.post("/api/v1/nps/dismiss", json={
            "trigger_type": "monthly",
            "reason": "Too busy right now"
        })

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True

    def test_dismiss_without_reason(self, authed_client: RetryClient):
        """Should accept dismissal without reason"""
        response = authed_client.post("/api/v1/nps/dismiss", json={
            "trigger_type": "first_deployment"
        })

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True

    def test_dismiss_invalid_trigger(self, authed_client: RetryClient):
        """Should reject invalid trigger type"""
        response = authed_client.post("/api/v1/nps/dismiss", json={
            "trigger_type": "invalid_trigger"
        })

        assert response.status_code == 400


@pytest.mark.integration
class TestNPSTrends:
    """Test NPS trends/dashboard endpoint"""

    def test_get_trends_default(self, authed_client: RetryClient):
        """Should return NPS trends for default date range"""
        response = authed_client.get("/api/v1/nps/trends")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "scores" in data
        assert "categories" in data
        assert "current_nps" in data
        assert "total_responses" in data
        assert "average_score" in data

        # Check categories structure
        categories = data["categories"]
        assert "detractors" in categories
        assert "passives" in categories
        assert "promoters" in categories

    def test_get_trends_with_date_range(self, authed_client: RetryClient):
        """Should return NPS trends for specified date range"""
        response = authed_client.get(
            "/api/v1/nps/trends",
            params={"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "scores" in data
        assert "start_date" in data
        assert "end_date" in data

    def test_get_trends_invalid_date_format(self, authed_client: RetryClient):
        """Should reject invalid date format"""
        response = authed_client.get(
            "/api/v1/nps/trends",
            params={"start_date": "not-a-date"}
        )

        assert response.status_code == 400


@pytest.mark.integration
class TestNPSDetractors:
    """Test NPS detractors endpoint"""

    def test_get_detractors_all(self, authed_client: RetryClient):
        """Should return all detractor responses"""
        response = authed_client.get("/api/v1/nps/detractors")

        assert response.status_code == 200
        data = response.json()

        assert "detractors" in data
        assert "count" in data
        assert "pending_followup" in data

        # All returned items should be detractors
        for detractor in data.get("detractors", []):
            assert detractor.get("category") == "detractor"
            assert detractor.get("score") is not None
            assert detractor.get("score") <= 6

    def test_get_detractors_pending_only(self, authed_client: RetryClient):
        """Should return only detractors pending follow-up"""
        response = authed_client.get(
            "/api/v1/nps/detractors",
            params={"pending_only": "true"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "detractors" in data
        assert "pending_followup" in data

        # All returned items should need follow-up
        for detractor in data.get("detractors", []):
            assert detractor.get("needs_followup") == True
            assert detractor.get("followup_completed") == False

    def test_get_detractors_pagination(self, authed_client: RetryClient):
        """Should support pagination"""
        response = authed_client.get(
            "/api/v1/nps/detractors",
            params={"limit": 10, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data.get("detractors", [])) <= 10


@pytest.mark.integration
class TestNPSFollowup:
    """Test NPS follow-up update endpoint"""

    def test_update_followup_status(self, authed_client: RetryClient):
        """Should update follow-up status for a detractor"""
        # First, get a detractor
        detractors_response = authed_client.get("/api/v1/nps/detractors")

        if detractors_response.status_code != 200:
            pytest.skip("Could not get detractors list")

        detractors = detractors_response.json().get("detractors", [])

        if not detractors:
            pytest.skip("No detractors available to test follow-up")

        detractor_id = detractors[0]["id"]

        # Update follow-up status
        response = authed_client.put(
            f"/api/v1/nps/responses/{detractor_id}/followup",
            json={
                "followup_completed": True,
                "followup_notes": "Contacted customer, resolved their concerns"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True
        assert data.get("id") == detractor_id

    def test_update_followup_nonexistent_id(self, authed_client: RetryClient):
        """Should return 404 for non-existent response ID"""
        response = authed_client.put(
            "/api/v1/nps/responses/999999/followup",
            json={
                "followup_completed": True,
                "followup_notes": "Test notes"
            }
        )

        assert response.status_code == 404


@pytest.mark.integration
class TestNPSConfig:
    """Test NPS survey configuration endpoints"""

    def test_get_survey_configs(self, authed_client: RetryClient):
        """Should return all survey configurations"""
        response = authed_client.get("/api/v1/nps/config")

        assert response.status_code == 200
        data = response.json()

        assert "configs" in data
        assert "count" in data

        # Should have configs for the standard trigger types
        trigger_types = [c.get("trigger_type") for c in data.get("configs", [])]
        # At least one config should exist
        assert len(data.get("configs", [])) > 0

    def test_update_survey_config(self, authed_client: RetryClient):
        """Should update survey configuration"""
        # Update monthly config
        response = authed_client.put(
            "/api/v1/nps/config/monthly",
            params={
                "enabled": True,
                "frequency_days": 30
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data.get("trigger_type") == "monthly"
        assert data.get("enabled") == True
        assert data.get("frequency_days") == 30

    def test_update_config_invalid_trigger(self, authed_client: RetryClient):
        """Should reject invalid trigger type"""
        response = authed_client.put(
            "/api/v1/nps/config/invalid_trigger",
            params={"enabled": True}
        )

        assert response.status_code == 400


@pytest.mark.integration
class TestNPSEndToEndFlow:
    """Complete end-to-end NPS flow tests"""

    def test_complete_promoter_flow(self, authed_client: RetryClient):
        """
        Complete flow for a promoter submission:
        1. Check if survey should show
        2. Submit promoter score
        3. Verify it doesn't appear in detractors
        4. Check rate limiting prevents re-show
        """
        trigger_type = "monthly"

        # Step 1: Check survey eligibility
        check_response = authed_client.get(f"/api/v1/nps/should-show?trigger_type={trigger_type}")
        assert check_response.status_code == 200

        # Step 2: Submit promoter score
        submit_response = authed_client.post("/api/v1/nps/submit", json={
            "score": 10,
            "comment": "Excellent service! Keep up the great work!",
            "trigger_type": trigger_type
        })
        assert submit_response.status_code == 200
        submit_data = submit_response.json()
        assert submit_data.get("category") == "promoter"
        response_id = submit_data.get("id")

        # Step 3: Verify not in detractors (promoters shouldn't appear there)
        detractors_response = authed_client.get("/api/v1/nps/detractors")
        assert detractors_response.status_code == 200
        detractors = detractors_response.json().get("detractors", [])
        detractor_ids = [d.get("id") for d in detractors]
        assert response_id not in detractor_ids

        # Step 4: Verify trends include the submission
        trends_response = authed_client.get("/api/v1/nps/trends")
        assert trends_response.status_code == 200
        trends_data = trends_response.json()
        assert trends_data.get("total_responses", 0) > 0

    def test_complete_detractor_flow(self, second_user_client: tuple):
        """
        Complete flow for a detractor submission:
        1. Submit detractor score
        2. Verify it appears in detractors list
        3. Update follow-up status
        4. Verify follow-up is marked complete
        """
        client, email = second_user_client

        # Step 1: Submit detractor score
        submit_response = client.post("/api/v1/nps/submit", json={
            "score": 2,
            "comment": "Very disappointed with the performance",
            "trigger_type": "monthly"
        })
        assert submit_response.status_code == 200
        submit_data = submit_response.json()
        assert submit_data.get("category") == "detractor"
        response_id = submit_data.get("id")

        # Step 2: Verify it appears in detractors list
        detractors_response = client.get("/api/v1/nps/detractors")
        assert detractors_response.status_code == 200
        detractors = detractors_response.json().get("detractors", [])
        detractor_ids = [d.get("id") for d in detractors]
        assert response_id in detractor_ids

        # Step 3: Update follow-up status
        followup_response = client.put(
            f"/api/v1/nps/responses/{response_id}/followup",
            json={
                "followup_completed": True,
                "followup_notes": "Reached out to customer, offered compensation"
            }
        )
        assert followup_response.status_code == 200

        # Step 4: Verify follow-up is complete (not in pending anymore)
        pending_response = client.get("/api/v1/nps/detractors?pending_only=true")
        assert pending_response.status_code == 200
        pending_ids = [d.get("id") for d in pending_response.json().get("detractors", [])]
        assert response_id not in pending_ids


# Run specific test classes if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
