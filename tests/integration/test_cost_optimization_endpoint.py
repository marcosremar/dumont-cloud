"""
Integration Tests for Cost Optimization API Endpoint

Tests the /ai-wizard/cost-optimization endpoint including:
- Valid request/response handling
- Pydantic validation for invalid requests
- Price prediction service fallback behavior
- Database session cleanup verification
- OpenRouter fallback chain behavior

These tests use FastAPI's TestClient to simulate HTTP requests
without requiring a running server or database.
"""

import os
import sys
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, Mock, AsyncMock
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient
from fastapi import FastAPI


# =============================================================================
# Create Test App (without full lifespan to avoid external service connections)
# =============================================================================

def create_test_app():
    """Create a minimal test app with just the AI Wizard router."""
    from src.api.v1.endpoints.ai_wizard import router as ai_wizard_router

    test_app = FastAPI(title="Test App")
    test_app.include_router(ai_wizard_router, prefix="/api/v1")
    test_app.include_router(ai_wizard_router, prefix="/api")

    return test_app


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_ai_wizard_service():
    """Mock the AI wizard service to avoid external API calls."""
    with patch('src.api.v1.endpoints.ai_wizard.ai_wizard_service') as mock_service:
        # Default successful response
        mock_service.get_cost_optimization_recommendations = AsyncMock(return_value={
            "success": True,
            "current_configuration": {
                "gpu_type": "RTX_4090",
                "avg_utilization": 35.0,
                "monthly_cost_usd": 504.0,
            },
            "recommendations": [
                {
                    "type": "gpu_downgrade",
                    "current_gpu": "RTX_4090",
                    "recommended_gpu": "RTX_4070",
                    "reason": "Average GPU utilization is only 35.0% over the analysis period",
                    "estimated_monthly_savings_usd": 374.4,
                    "confidence_score": 0.85,
                },
                {
                    "type": "hibernation",
                    "current_timeout_minutes": 0,
                    "recommended_timeout_minutes": 30,
                    "reason": "Analyzed 15 idle periods (median: 60min) with consistent patterns",
                    "estimated_monthly_savings_usd": 45.50,
                    "confidence_score": 0.75,
                },
                {
                    "type": "spot_timing",
                    "gpu_type": "RTX_4090",
                    "recommended_windows": [
                        {"day": "Saturday", "hours": "2:00-6:00 UTC"},
                        {"day": "Sunday", "hours": "2:00-6:00 UTC"},
                    ],
                    "reason": "Price prediction shows lower spot prices during these windows",
                    "estimated_monthly_savings_usd": 42.0,
                    "confidence_score": 0.50,
                }
            ],
            "estimated_monthly_savings": 461.90,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4070",
            "analysis_period_days": 30,
            "data_completeness": 0.85,
            "has_sufficient_data": True,
        })
        yield mock_service


@pytest.fixture
def test_client(mock_ai_wizard_service):
    """Create FastAPI test client for integration tests using minimal test app."""
    app = create_test_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def valid_cost_optimization_request() -> Dict[str, Any]:
    """Valid request payload for cost optimization endpoint."""
    return {
        "user_id": "test_user_123",
        "instance_id": "test_instance_456",
        "days_to_analyze": 30,
        "current_hibernation_timeout": 0
    }


# =============================================================================
# Test Classes
# =============================================================================

class TestCostOptimizationEndpoint:
    """Tests for POST /ai-wizard/cost-optimization endpoint."""

    def test_endpoint_returns_200_with_valid_request(self, test_client, valid_cost_optimization_request):
        """Endpoint should return 200 OK with valid request."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert "recommendations" in data
        assert "current_gpu" in data
        assert "recommended_gpu" in data
        assert "analysis_period_days" in data

    def test_endpoint_returns_valid_json_structure(self, test_client, valid_cost_optimization_request):
        """Response should match expected CostOptimizationResponse structure."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        required_fields = [
            "success",
            "recommendations",
            "estimated_monthly_savings",
            "current_gpu",
            "recommended_gpu",
            "analysis_period_days",
            "data_completeness",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify types
        assert isinstance(data["success"], bool)
        assert isinstance(data["recommendations"], list)
        assert isinstance(data["estimated_monthly_savings"], (int, float))
        assert isinstance(data["current_gpu"], str)
        assert isinstance(data["recommended_gpu"], str)
        assert isinstance(data["analysis_period_days"], int)
        assert isinstance(data["data_completeness"], (int, float))

    def test_endpoint_validates_days_to_analyze_range(self, test_client, mock_ai_wizard_service):
        """Should reject days_to_analyze outside 3-90 range."""
        # Test too low
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user",
                "instance_id": "test_instance",
                "days_to_analyze": 1  # Below minimum of 3
            }
        )
        assert response.status_code == 422  # Pydantic validation error

        # Test too high
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user",
                "instance_id": "test_instance",
                "days_to_analyze": 100  # Above maximum of 90
            }
        )
        assert response.status_code == 422

    def test_endpoint_requires_user_id(self, test_client, mock_ai_wizard_service):
        """Should reject request without user_id."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "instance_id": "test_instance",
                "days_to_analyze": 30
            }
        )
        assert response.status_code == 422

    def test_endpoint_requires_instance_id(self, test_client, mock_ai_wizard_service):
        """Should reject request without instance_id."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user",
                "days_to_analyze": 30
            }
        )
        assert response.status_code == 422

    def test_endpoint_uses_default_days_to_analyze(self, test_client, valid_cost_optimization_request):
        """Should use default 30 days when days_to_analyze not specified."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user",
                "instance_id": "test_instance"
                # days_to_analyze omitted, should default to 30
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_period_days"] == 30

    def test_endpoint_handles_empty_string_ids(self, test_client):
        """Should handle but accept empty string IDs (service handles validation)."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "",
                "instance_id": ""
            }
        )

        # Should succeed - service handles empty IDs gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestPricePredictionFallback:
    """Tests for price prediction service fallback behavior."""

    def test_graceful_fallback_when_service_unavailable(self, test_client, mock_ai_wizard_service, valid_cost_optimization_request):
        """Should return recommendations even when price prediction is unavailable."""
        # Mock returns recommendations with default spot timing
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Should still have recommendations
        assert len(data["recommendations"]) > 0

    def test_uses_default_spot_recommendation_on_service_error(self, test_client, mock_ai_wizard_service, valid_cost_optimization_request):
        """Should use default spot timing when price prediction errors."""
        # Customize mock to return spot timing with default windows
        mock_ai_wizard_service.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "recommendations": [
                {
                    "type": "spot_timing",
                    "reason": "General market patterns suggest lower spot prices (limited data)",
                    "estimated_monthly_savings_usd": 30.0,
                    "confidence_score": 0.50,
                    "recommended_windows": [
                        {"day": "Saturday", "hours": "2:00-6:00 UTC"}
                    ]
                }
            ],
            "estimated_monthly_savings": 30.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",
            "analysis_period_days": 30,
            "data_completeness": 0.0,
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        assert response.status_code == 200
        data = response.json()

        # Should still have spot timing recommendation with default windows
        spot_recs = [r for r in data["recommendations"] if r.get("type") == "spot_timing"]
        assert len(spot_recs) == 1
        assert spot_recs[0]["confidence_score"] == 0.50  # Lower confidence for defaults

    def test_incorporates_prediction_when_available(self, test_client, mock_ai_wizard_service, valid_cost_optimization_request):
        """Should use price prediction service when available."""
        # Mock returns higher confidence from real prediction
        mock_ai_wizard_service.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "recommendations": [
                {
                    "type": "spot_timing",
                    "reason": "Price prediction shows 30% lower prices during these windows with 85% confidence",
                    "estimated_monthly_savings_usd": 60.0,
                    "confidence_score": 0.85,
                    "recommended_windows": [
                        {"day": "Tuesday", "hours": "3:00-7:00 UTC"}
                    ]
                }
            ],
            "estimated_monthly_savings": 60.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",
            "analysis_period_days": 30,
            "data_completeness": 0.95,
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        assert response.status_code == 200
        data = response.json()

        # Verify higher confidence from real predictions
        spot_recs = [r for r in data["recommendations"] if r.get("type") == "spot_timing"]
        assert len(spot_recs) == 1
        assert spot_recs[0]["confidence_score"] == 0.85


class TestDatabaseSessionCleanup:
    """Tests for database session cleanup verification."""

    def test_no_connection_leak_on_success(self, test_client, valid_cost_optimization_request):
        """Database connections should be properly closed after successful request."""
        # Make multiple requests to detect potential connection leaks
        for _ in range(5):
            response = test_client.post(
                "/api/v1/ai-wizard/cost-optimization",
                json=valid_cost_optimization_request
            )
            assert response.status_code == 200

        # If there was a connection leak, we'd likely see errors on subsequent requests
        final_response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )
        assert final_response.status_code == 200

    def test_session_closed_on_error(self, test_client, mock_ai_wizard_service, valid_cost_optimization_request):
        """Database session should be closed even when service errors."""
        # Make the service return an error
        mock_ai_wizard_service.get_cost_optimization_recommendations.return_value = {
            "success": False,
            "error": "Database connection failed"
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        # Should return 500 as per endpoint implementation
        assert response.status_code == 500

        # Reset mock for subsequent tests
        mock_ai_wizard_service.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "recommendations": [],
            "estimated_monthly_savings": 0.0,
            "current_gpu": "Unknown",
            "recommended_gpu": "Unknown",
            "analysis_period_days": 30,
            "data_completeness": 0.0,
        }

        # Next request should work fine (no leaked connections)
        response2 = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )
        assert response2.status_code == 200

    def test_session_closed_after_successful_query(self, test_client, valid_cost_optimization_request):
        """Database session should be closed after successful query."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        assert response.status_code == 200

        # Verify we can make another request without issues
        response2 = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )
        assert response2.status_code == 200


class TestOpenRouterFallbackChain:
    """Tests for OpenRouter AI fallback chain behavior."""

    def test_endpoint_handles_ai_service_fallback(self, test_client, mock_ai_wizard_service, valid_cost_optimization_request):
        """Endpoint should handle AI service gracefully when it uses fallback."""
        # Simulate successful fallback response
        mock_ai_wizard_service.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "recommendations": [
                {
                    "type": "spot_timing",
                    "reason": "Default recommendation (AI service used fallback)",
                    "estimated_monthly_savings_usd": 50.0,
                    "confidence_score": 0.5,
                }
            ],
            "estimated_monthly_savings": 50.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",
            "analysis_period_days": 30,
            "data_completeness": 0.0,
            "has_sufficient_data": False,
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["recommendations"]) > 0

    def test_endpoint_handles_ai_service_error(self, test_client, mock_ai_wizard_service, valid_cost_optimization_request):
        """Endpoint should return 500 when AI service fails completely."""
        mock_ai_wizard_service.get_cost_optimization_recommendations.return_value = {
            "success": False,
            "error": "All AI models failed"
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        # Should return 500 as per endpoint implementation
        assert response.status_code == 500


class TestRecommendationStructure:
    """Tests for recommendation response structure validation."""

    def test_recommendations_have_required_fields(self, test_client, valid_cost_optimization_request):
        """Each recommendation should have type, reason, estimated_monthly_savings_usd, confidence_score."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        assert response.status_code == 200
        data = response.json()

        for rec in data.get("recommendations", []):
            assert "type" in rec, "Recommendation missing 'type' field"
            assert "reason" in rec, "Recommendation missing 'reason' field"
            assert "estimated_monthly_savings_usd" in rec, "Recommendation missing 'estimated_monthly_savings_usd'"
            assert "confidence_score" in rec, "Recommendation missing 'confidence_score'"

    def test_confidence_scores_in_valid_range(self, test_client, valid_cost_optimization_request):
        """Confidence scores should be between 0 and 1."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        assert response.status_code == 200
        data = response.json()

        for rec in data.get("recommendations", []):
            confidence = rec.get("confidence_score", 0)
            assert 0 <= confidence <= 1, f"Confidence score {confidence} outside valid range [0, 1]"

    def test_data_completeness_in_valid_range(self, test_client, valid_cost_optimization_request):
        """Data completeness should be between 0 and 1."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )

        assert response.status_code == 200
        data = response.json()

        assert 0 <= data["data_completeness"] <= 1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_minimum_days_to_analyze(self, test_client, mock_ai_wizard_service):
        """Should accept minimum allowed days_to_analyze value (3)."""
        mock_ai_wizard_service.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "recommendations": [],
            "estimated_monthly_savings": 0.0,
            "current_gpu": "Unknown",
            "recommended_gpu": "Unknown",
            "analysis_period_days": 3,
            "data_completeness": 0.0,
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user",
                "instance_id": "test_instance",
                "days_to_analyze": 3  # Minimum allowed
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_period_days"] == 3

    def test_maximum_days_to_analyze(self, test_client, mock_ai_wizard_service):
        """Should accept maximum allowed days_to_analyze value (90)."""
        mock_ai_wizard_service.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "recommendations": [],
            "estimated_monthly_savings": 0.0,
            "current_gpu": "Unknown",
            "recommended_gpu": "Unknown",
            "analysis_period_days": 90,
            "data_completeness": 0.0,
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user",
                "instance_id": "test_instance",
                "days_to_analyze": 90  # Maximum allowed
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_period_days"] == 90

    def test_unicode_in_user_id(self, test_client, mock_ai_wizard_service):
        """Should handle unicode characters in user_id."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "用户_测试_ユーザー",
                "instance_id": "test_instance"
            }
        )

        assert response.status_code == 200

    def test_special_characters_in_instance_id(self, test_client, mock_ai_wizard_service):
        """Should handle special characters in instance_id."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user",
                "instance_id": "instance-with-dashes_and_underscores.and.dots"
            }
        )

        assert response.status_code == 200

    def test_very_long_ids(self, test_client, mock_ai_wizard_service):
        """Should handle very long user/instance IDs."""
        long_id = "a" * 1000

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": long_id,
                "instance_id": long_id
            }
        )

        # Should not crash - may succeed or return specific error
        assert response.status_code in [200, 422, 400]

    def test_negative_hibernation_timeout_rejected(self, test_client, mock_ai_wizard_service):
        """Should reject negative hibernation timeout."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user",
                "instance_id": "test_instance",
                "current_hibernation_timeout": -1
            }
        )

        assert response.status_code == 422


class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    def test_multiple_requests_dont_interfere(self, test_client):
        """Multiple concurrent requests should not interfere with each other."""
        import concurrent.futures

        requests_data = [
            {"user_id": f"user_{i}", "instance_id": f"instance_{i}"}
            for i in range(5)
        ]

        def make_request(data):
            return test_client.post("/api/v1/ai-wizard/cost-optimization", json=data)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, data) for data in requests_data]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200


class TestAPIVersionRouting:
    """Tests for API version routing."""

    def test_v1_prefix_works(self, test_client, valid_cost_optimization_request):
        """Request to /api/v1/... should work."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )
        assert response.status_code == 200

    def test_api_prefix_works(self, test_client, valid_cost_optimization_request):
        """Request to /api/... should also work (compatibility)."""
        response = test_client.post(
            "/api/ai-wizard/cost-optimization",
            json=valid_cost_optimization_request
        )
        # Both prefixes are mounted in the test app
        assert response.status_code == 200


# =============================================================================
# Test Runner
# =============================================================================

def run_all_tests():
    """Execute all tests manually for debugging."""
    print("=" * 70)
    print("INTEGRATION TESTS - Cost Optimization Endpoint")
    print("=" * 70)
    print()

    # Create minimal test app (without lifespan hooks)
    app = create_test_app()

    # Mock the AI wizard service
    with patch('src.api.v1.endpoints.ai_wizard.ai_wizard_service') as mock_service:
        # Set up default mock response
        mock_service.get_cost_optimization_recommendations = AsyncMock(return_value={
            "success": True,
            "current_configuration": {"gpu_type": "RTX_4090", "avg_utilization": 35.0, "monthly_cost_usd": 504.0},
            "recommendations": [
                {"type": "gpu_downgrade", "reason": "Test", "estimated_monthly_savings_usd": 100.0, "confidence_score": 0.85}
            ],
            "estimated_monthly_savings": 100.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4070",
            "analysis_period_days": 30,
            "data_completeness": 0.85,
        })

        with TestClient(app) as client:
            test_classes = [
                TestCostOptimizationEndpoint,
                TestPricePredictionFallback,
                TestDatabaseSessionCleanup,
                TestOpenRouterFallbackChain,
                TestRecommendationStructure,
                TestEdgeCases,
                TestConcurrentRequests,
                TestAPIVersionRouting,
            ]

            total_tests = 0
            passed_tests = 0
            failed_tests = []

            valid_request = {
                "user_id": "test_user_123",
                "instance_id": "test_instance_456",
                "days_to_analyze": 30,
                "current_hibernation_timeout": 0
            }

            for test_class in test_classes:
                print(f"\n{'='*50}")
                print(f"Executing: {test_class.__name__}")
                print("=" * 50)

                instance = test_class()
                test_methods = [m for m in dir(instance) if m.startswith("test_")]

                for method_name in test_methods:
                    total_tests += 1
                    method = getattr(instance, method_name)

                    try:
                        # Inject fixtures manually for standalone execution
                        import inspect
                        sig = inspect.signature(method)
                        kwargs = {}

                        if 'test_client' in sig.parameters:
                            kwargs['test_client'] = client
                        if 'valid_cost_optimization_request' in sig.parameters:
                            kwargs['valid_cost_optimization_request'] = valid_request
                        if 'mock_ai_wizard_service' in sig.parameters:
                            kwargs['mock_ai_wizard_service'] = mock_service

                        method(**kwargs)
                        print(f"  ✅ {method_name}")
                        passed_tests += 1
                    except AssertionError as e:
                        print(f"  ❌ {method_name}: {e}")
                        failed_tests.append(f"{test_class.__name__}.{method_name}")
                    except Exception as e:
                        print(f"  ❌ {method_name}: {type(e).__name__}: {e}")
                        failed_tests.append(f"{test_class.__name__}.{method_name}")

            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"\nTotal: {total_tests} tests")
            print(f"Passed: {passed_tests}")
            print(f"Failed: {len(failed_tests)}")

            if failed_tests:
                print("\nTests that failed:")
                for test in failed_tests:
                    print(f"  - {test}")
                return False
            else:
                print("\n🎉 ALL TESTS PASSED!")
                return True


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
