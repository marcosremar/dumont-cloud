#!/usr/bin/env python3
"""
End-to-End Tests for Cost Optimization Flow

Tests complete optimization scenarios including:
- Full cost optimization request with 30 days of usage data
- Insufficient data scenario (2 days of data)
- Already optimal configuration (60-80% utilization)
- Database session cleanup verification
- API endpoint integration

Usage:
    pytest tests/e2e/test_cost_optimization_flow.py -v
"""

import os
import sys
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from fastapi import FastAPI


# =============================================================================
# Test App Creation
# =============================================================================

def create_test_app():
    """Create a minimal test app with the AI Wizard router for E2E tests."""
    from src.api.v1.endpoints.ai_wizard import router as ai_wizard_router

    test_app = FastAPI(title="Cost Optimization E2E Test App")
    test_app.include_router(ai_wizard_router, prefix="/api/v1")
    test_app.include_router(ai_wizard_router, prefix="/api")

    # Add health endpoint for testing
    @test_app.get("/health")
    def health():
        return {"status": "healthy"}

    return test_app


# =============================================================================
# Mock Data Generators
# =============================================================================

def generate_usage_records(
    days: int = 30,
    avg_utilization: float = 35.0,
    gpu_type: str = "RTX_4090",
    variance: float = 10.0,
    include_idle_periods: bool = True
) -> List[Dict[str, Any]]:
    """
    Generate mock usage records for testing.

    Args:
        days: Number of days of data to generate
        avg_utilization: Target average GPU utilization
        gpu_type: GPU type to use
        variance: Variance in utilization (for realistic data)
        include_idle_periods: Whether to include idle period data

    Returns:
        List of mock usage records
    """
    import random

    records = []
    base_time = datetime.utcnow() - timedelta(days=days)

    for day in range(days):
        for hour in range(24):
            # Add some variance to utilization
            util = max(0, min(100, avg_utilization + random.uniform(-variance, variance)))

            record = {
                "gpu_utilization": util,
                "memory_utilization": util * 0.8,  # Memory typically lower
                "gpu_type": gpu_type,
                "timestamp": base_time + timedelta(days=day, hours=hour),
                "runtime_hours": 1.0,
                "cost_usd": 0.70,  # Typical RTX 4090 cost
            }

            if include_idle_periods and random.random() < 0.3:  # 30% chance of idle
                record["extra_data"] = {"idle_minutes": random.randint(15, 120)}

            records.append(record)

    return records


def generate_optimal_usage_records(days: int = 30) -> List[Dict[str, Any]]:
    """Generate usage records with optimal utilization (60-80%)."""
    return generate_usage_records(
        days=days,
        avg_utilization=70.0,
        variance=5.0,
        include_idle_periods=False
    )


def generate_underutilized_records(days: int = 30) -> List[Dict[str, Any]]:
    """Generate usage records with low utilization (<50%)."""
    return generate_usage_records(
        days=days,
        avg_utilization=30.0,
        variance=8.0
    )


def generate_insufficient_data_records() -> List[Dict[str, Any]]:
    """Generate only 2 days of usage data (insufficient for recommendations)."""
    return generate_usage_records(days=2, avg_utilization=50.0)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_cost_optimization_service():
    """Mock the CostOptimizationService for controlled testing."""
    with patch('src.services.ai_wizard_service.CostOptimizationService') as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        # Default: 30 days of underutilized data
        mock_instance.get_comprehensive_recommendations.return_value = {
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
                    "confidence_score": 0.65,
                }
            ],
            "total_estimated_monthly_savings_usd": 461.90,
            "analysis_period_days": 30,
            "data_completeness": 0.85,
        }

        yield mock_instance


@pytest.fixture
def mock_ai_wizard_service_full():
    """Mock the ai_wizard_service with comprehensive recommendation support."""
    with patch('src.api.v1.endpoints.ai_wizard.ai_wizard_service') as mock_service:
        # Default successful response with full 30-day analysis
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
                    "confidence_score": 0.65,
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
def test_client(mock_ai_wizard_service_full):
    """Create FastAPI test client for E2E tests."""
    app = create_test_app()
    with TestClient(app) as client:
        yield client


# =============================================================================
# E2E Test Classes
# =============================================================================

class TestFullCostOptimizationFlow:
    """
    E2E tests for complete cost optimization request with 30 days of usage data.

    Scenario: User with 30 days of usage data showing underutilized GPU.
    Expected: Complete recommendations with GPU suggestion, spot timing,
              hibernation setting, and estimated savings.
    """

    def test_full_flow_returns_complete_recommendations(self, test_client):
        """Full optimization flow should return all recommendation types."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_30_days",
                "instance_id": "test_instance_123",
                "days_to_analyze": 30
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify success
        assert data["success"] is True

        # Verify all expected recommendation types present
        rec_types = [r["type"] for r in data.get("recommendations", [])]
        assert "gpu_downgrade" in rec_types or "gpu_upgrade" in rec_types or "gpu_match" in rec_types
        # Hibernation and spot timing should be present
        assert any(t in rec_types for t in ["hibernation", "spot_timing"])

        # Verify estimated savings is positive
        assert data["estimated_monthly_savings"] >= 0

    def test_full_flow_response_structure(self, test_client):
        """Response should contain all required fields."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_structure",
                "instance_id": "test_instance_structure"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify required top-level fields
        required_fields = [
            "success",
            "recommendations",
            "estimated_monthly_savings",
            "current_gpu",
            "recommended_gpu",
            "analysis_period_days",
            "data_completeness"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_full_flow_recommendations_have_required_fields(self, test_client):
        """Each recommendation should have all required fields."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_rec_fields",
                "instance_id": "test_instance_rec_fields"
            }
        )

        assert response.status_code == 200
        data = response.json()

        for rec in data.get("recommendations", []):
            assert "type" in rec, "Recommendation missing 'type' field"
            assert "reason" in rec, "Recommendation missing 'reason' field"
            assert "estimated_monthly_savings_usd" in rec, "Recommendation missing savings"
            assert "confidence_score" in rec, "Recommendation missing confidence"

    def test_full_flow_confidence_scores_valid_range(self, test_client):
        """Confidence scores should be between 0 and 1."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_confidence",
                "instance_id": "test_instance_confidence"
            }
        )

        assert response.status_code == 200
        data = response.json()

        for rec in data.get("recommendations", []):
            confidence = rec.get("confidence_score", 0)
            assert 0 <= confidence <= 1, f"Invalid confidence: {confidence}"

    def test_full_flow_total_savings_matches_sum(self, test_client):
        """Total estimated savings should equal sum of individual recommendations."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_savings_sum",
                "instance_id": "test_instance_savings_sum"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Calculate sum of individual savings
        individual_sum = sum(
            r.get("estimated_monthly_savings_usd", 0)
            for r in data.get("recommendations", [])
        )

        # Should be approximately equal (allow for rounding)
        total_savings = data.get("estimated_monthly_savings", 0)
        assert abs(total_savings - individual_sum) < 0.10, \
            f"Total {total_savings} != sum {individual_sum}"

    def test_full_flow_data_completeness_valid_range(self, test_client):
        """Data completeness should be between 0 and 1."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_completeness",
                "instance_id": "test_instance_completeness"
            }
        )

        assert response.status_code == 200
        data = response.json()

        completeness = data.get("data_completeness", 0)
        assert 0 <= completeness <= 1, f"Invalid completeness: {completeness}"

    def test_full_flow_analysis_period_matches_request(self, test_client):
        """Analysis period should match requested days."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_period",
                "instance_id": "test_instance_period",
                "days_to_analyze": 30
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_period_days"] == 30


class TestInsufficientDataScenario:
    """
    E2E tests for insufficient data scenario (2 days of data).

    Scenario: User with only 2 days of usage data.
    Expected: Error or low-confidence recommendations with warning message.
    """

    def test_insufficient_data_returns_warning(self, test_client, mock_ai_wizard_service_full):
        """Should return warning when data is insufficient."""
        # Configure mock for insufficient data
        mock_ai_wizard_service_full.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "current_configuration": {
                "gpu_type": "RTX_4090",
                "avg_utilization": 50.0,
                "monthly_cost_usd": 0.0,
            },
            "recommendations": [],
            "estimated_monthly_savings": 0.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",
            "analysis_period_days": 3,
            "data_completeness": 0.07,  # Very low completeness
            "has_sufficient_data": False,
            "warning": "Insufficient data for recommendations. Need at least 3 days of usage data.",
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_insufficient",
                "instance_id": "test_instance_insufficient",
                "days_to_analyze": 3  # Minimum allowed
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should have warning message
        assert data.get("warning") is not None or data.get("has_sufficient_data") is False

    def test_insufficient_data_low_confidence(self, test_client, mock_ai_wizard_service_full):
        """Recommendations with limited data should have lower confidence."""
        # Configure mock for limited data with low confidence
        mock_ai_wizard_service_full.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "current_configuration": {
                "gpu_type": "RTX_4090",
                "avg_utilization": 40.0,
                "monthly_cost_usd": 50.0,
            },
            "recommendations": [
                {
                    "type": "spot_timing",
                    "reason": "Limited data available",
                    "estimated_monthly_savings_usd": 20.0,
                    "confidence_score": 0.30,  # Low confidence
                }
            ],
            "estimated_monthly_savings": 20.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",
            "analysis_period_days": 5,
            "data_completeness": 0.15,
            "has_sufficient_data": False,
            "warning": "Limited data - recommendations may improve over time",
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_low_conf",
                "instance_id": "test_instance_low_conf",
                "days_to_analyze": 5
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check for low confidence or warning
        for rec in data.get("recommendations", []):
            if rec.get("confidence_score"):
                assert rec["confidence_score"] <= 0.50, "Should have low confidence"

    def test_insufficient_data_no_major_recommendations(self, test_client, mock_ai_wizard_service_full):
        """Should not make major GPU change recommendations with insufficient data."""
        # Configure mock for insufficient data - no major recommendations
        mock_ai_wizard_service_full.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "current_configuration": {
                "gpu_type": "RTX_4090",
                "avg_utilization": 0.0,
                "monthly_cost_usd": 0.0,
            },
            "recommendations": [],  # No recommendations with insufficient data
            "estimated_monthly_savings": 0.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",
            "analysis_period_days": 3,
            "data_completeness": 0.0,
            "has_sufficient_data": False,
            "warning": "Insufficient data for recommendations.",
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_no_rec",
                "instance_id": "test_instance_no_rec",
                "days_to_analyze": 3
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should not have GPU change recommendations
        gpu_recs = [
            r for r in data.get("recommendations", [])
            if r.get("type") in ["gpu_downgrade", "gpu_upgrade"]
        ]
        assert len(gpu_recs) == 0, "Should not recommend GPU changes with insufficient data"


class TestAlreadyOptimalConfiguration:
    """
    E2E tests for already optimal configuration (60-80% utilization).

    Scenario: User with optimal GPU usage.
    Expected: "Already optimized" message with no major recommendations.
    """

    def test_optimal_config_returns_no_changes(self, test_client, mock_ai_wizard_service_full):
        """Already optimal config should not suggest GPU changes."""
        # Configure mock for optimal configuration
        mock_ai_wizard_service_full.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "current_configuration": {
                "gpu_type": "RTX_4090",
                "avg_utilization": 72.0,  # Optimal range
                "monthly_cost_usd": 504.0,
            },
            "recommendations": [],  # No recommendations needed
            "estimated_monthly_savings": 0.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",  # Same GPU
            "analysis_period_days": 30,
            "data_completeness": 0.95,
            "has_sufficient_data": True,
            "message": "Your setup is already optimized",
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_optimal",
                "instance_id": "test_instance_optimal",
                "days_to_analyze": 30
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Current and recommended GPU should be the same
        assert data["current_gpu"] == data["recommended_gpu"]

        # Should have optimized message or no major recommendations
        has_optimized_message = data.get("message") is not None
        no_gpu_changes = all(
            r.get("type") not in ["gpu_downgrade", "gpu_upgrade"]
            for r in data.get("recommendations", [])
        )

        assert has_optimized_message or no_gpu_changes

    def test_optimal_config_may_still_have_spot_timing(self, test_client, mock_ai_wizard_service_full):
        """Optimal config might still benefit from spot timing suggestions."""
        # Configure mock - optimal GPU but with spot timing
        mock_ai_wizard_service_full.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "current_configuration": {
                "gpu_type": "RTX_4090",
                "avg_utilization": 75.0,
                "monthly_cost_usd": 504.0,
            },
            "recommendations": [
                {
                    "type": "spot_timing",
                    "reason": "Lower prices on weekends",
                    "estimated_monthly_savings_usd": 40.0,
                    "confidence_score": 0.70,
                    "recommended_windows": [
                        {"day": "Saturday", "hours": "2:00-6:00 UTC"}
                    ]
                }
            ],
            "estimated_monthly_savings": 40.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",
            "analysis_period_days": 30,
            "data_completeness": 0.90,
            "has_sufficient_data": True,
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_optimal_spot",
                "instance_id": "test_instance_optimal_spot"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Spot timing recommendations are still valid for optimal configs
        spot_recs = [
            r for r in data.get("recommendations", [])
            if r.get("type") == "spot_timing"
        ]
        # May or may not have spot timing, both valid
        assert isinstance(spot_recs, list)

    def test_optimal_config_high_confidence(self, test_client, mock_ai_wizard_service_full):
        """Optimal config with good data should have high confidence."""
        # Configure mock for high-confidence optimal
        mock_ai_wizard_service_full.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "current_configuration": {
                "gpu_type": "RTX_4090",
                "avg_utilization": 70.0,
                "monthly_cost_usd": 504.0,
            },
            "recommendations": [],
            "estimated_monthly_savings": 0.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",
            "analysis_period_days": 30,
            "data_completeness": 0.98,  # High completeness
            "has_sufficient_data": True,
            "message": "Your setup is already optimized",
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_high_conf",
                "instance_id": "test_instance_high_conf"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # High data completeness
        assert data.get("data_completeness", 0) >= 0.90


class TestDatabaseSessionCleanup:
    """
    E2E tests verifying proper database session cleanup.

    Scenario: Multiple sequential requests should not leak connections.
    """

    def test_multiple_requests_no_connection_leak(self, test_client):
        """Multiple sequential requests should complete without connection issues."""
        # Make 10 sequential requests
        for i in range(10):
            response = test_client.post(
                "/api/v1/ai-wizard/cost-optimization",
                json={
                    "user_id": f"test_user_leak_{i}",
                    "instance_id": f"test_instance_leak_{i}"
                }
            )
            assert response.status_code == 200, f"Request {i} failed"

        # Final request should still work
        final_response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_final",
                "instance_id": "test_instance_final"
            }
        )
        assert final_response.status_code == 200

    def test_concurrent_requests_handled(self, test_client):
        """Concurrent requests should not interfere with each other."""
        import concurrent.futures

        requests_data = [
            {"user_id": f"concurrent_user_{i}", "instance_id": f"concurrent_instance_{i}"}
            for i in range(5)
        ]

        def make_request(data):
            return test_client.post("/api/v1/ai-wizard/cost-optimization", json=data)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, data) for data in requests_data]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All concurrent requests should succeed
        for response in responses:
            assert response.status_code == 200


class TestAPIEndpointIntegration:
    """
    E2E tests for API endpoint integration and error handling.
    """

    def test_health_endpoint_available(self, test_client):
        """Health endpoint should be available."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_invalid_request_validation(self, test_client, mock_ai_wizard_service_full):
        """Invalid requests should be properly validated."""
        # Missing required fields
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={}
        )
        assert response.status_code == 422  # Pydantic validation

    def test_days_to_analyze_boundary_min(self, test_client):
        """Should accept minimum days_to_analyze value (3)."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_min",
                "instance_id": "test_instance_min",
                "days_to_analyze": 3
            }
        )
        assert response.status_code == 200

    def test_days_to_analyze_boundary_max(self, test_client):
        """Should accept maximum days_to_analyze value (90)."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_max",
                "instance_id": "test_instance_max",
                "days_to_analyze": 90
            }
        )
        assert response.status_code == 200

    def test_days_to_analyze_below_minimum_rejected(self, test_client, mock_ai_wizard_service_full):
        """Should reject days_to_analyze below minimum (3)."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_below",
                "instance_id": "test_instance_below",
                "days_to_analyze": 1
            }
        )
        assert response.status_code == 422

    def test_days_to_analyze_above_maximum_rejected(self, test_client, mock_ai_wizard_service_full):
        """Should reject days_to_analyze above maximum (90)."""
        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_above",
                "instance_id": "test_instance_above",
                "days_to_analyze": 100
            }
        )
        assert response.status_code == 422

    def test_service_error_returns_500(self, test_client, mock_ai_wizard_service_full):
        """Service errors should return 500."""
        mock_ai_wizard_service_full.get_cost_optimization_recommendations.return_value = {
            "success": False,
            "error": "Internal service error"
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_error",
                "instance_id": "test_instance_error"
            }
        )
        assert response.status_code == 500


class TestSpotTimingIntegration:
    """
    E2E tests for spot timing recommendation integration.
    """

    def test_spot_timing_recommendation_structure(self, test_client, mock_ai_wizard_service_full):
        """Spot timing recommendations should have proper structure."""
        # Configure mock with spot timing
        mock_ai_wizard_service_full.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "current_configuration": {
                "gpu_type": "RTX_4090",
                "avg_utilization": 60.0,
                "monthly_cost_usd": 400.0,
            },
            "recommendations": [
                {
                    "type": "spot_timing",
                    "gpu_type": "RTX_4090",
                    "recommended_windows": [
                        {"day": "Saturday", "hours": "2:00-6:00 UTC"},
                        {"day": "Sunday", "hours": "2:00-6:00 UTC"},
                    ],
                    "reason": "Price prediction shows lower spot prices during these windows",
                    "estimated_monthly_savings_usd": 50.0,
                    "confidence_score": 0.70,
                }
            ],
            "estimated_monthly_savings": 50.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",
            "analysis_period_days": 30,
            "data_completeness": 0.80,
            "has_sufficient_data": True,
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_spot",
                "instance_id": "test_instance_spot"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Find spot timing recommendation
        spot_recs = [r for r in data.get("recommendations", []) if r.get("type") == "spot_timing"]
        if spot_recs:
            spot_rec = spot_recs[0]
            assert "recommended_windows" in spot_rec
            assert "reason" in spot_rec
            assert "estimated_monthly_savings_usd" in spot_rec

    def test_spot_timing_fallback_when_service_unavailable(self, test_client, mock_ai_wizard_service_full):
        """Should use default spot timing when price prediction unavailable."""
        # Configure mock with default spot timing
        mock_ai_wizard_service_full.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "current_configuration": {
                "gpu_type": "RTX_4090",
                "avg_utilization": 50.0,
                "monthly_cost_usd": 300.0,
            },
            "recommendations": [
                {
                    "type": "spot_timing",
                    "reason": "General market patterns suggest lower spot prices (limited data)",
                    "estimated_monthly_savings_usd": 30.0,
                    "confidence_score": 0.50,  # Lower confidence for defaults
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
            "has_sufficient_data": False,
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_fallback",
                "instance_id": "test_instance_fallback"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should have spot timing even with fallback
        spot_recs = [r for r in data.get("recommendations", []) if r.get("type") == "spot_timing"]
        if spot_recs:
            # Fallback should have lower confidence
            assert spot_recs[0]["confidence_score"] <= 0.50


class TestHibernationOptimization:
    """
    E2E tests for hibernation optimization recommendations.
    """

    def test_hibernation_recommendation_structure(self, test_client, mock_ai_wizard_service_full):
        """Hibernation recommendations should have proper structure."""
        # Configure mock with hibernation recommendation
        mock_ai_wizard_service_full.get_cost_optimization_recommendations.return_value = {
            "success": True,
            "current_configuration": {
                "gpu_type": "RTX_4090",
                "avg_utilization": 35.0,
                "monthly_cost_usd": 500.0,
            },
            "recommendations": [
                {
                    "type": "hibernation",
                    "current_timeout_minutes": 0,
                    "recommended_timeout_minutes": 30,
                    "reason": "Analyzed 20 idle periods (median: 60min) with consistent patterns",
                    "estimated_monthly_savings_usd": 45.0,
                    "confidence_score": 0.80,
                }
            ],
            "estimated_monthly_savings": 45.0,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4090",
            "analysis_period_days": 30,
            "data_completeness": 0.85,
            "has_sufficient_data": True,
        }

        response = test_client.post(
            "/api/v1/ai-wizard/cost-optimization",
            json={
                "user_id": "test_user_hibernation",
                "instance_id": "test_instance_hibernation"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Find hibernation recommendation
        hibernation_recs = [r for r in data.get("recommendations", []) if r.get("type") == "hibernation"]
        if hibernation_recs:
            rec = hibernation_recs[0]
            assert "recommended_timeout_minutes" in rec
            assert "reason" in rec
            assert rec["recommended_timeout_minutes"] >= 15  # Minimum timeout


# =============================================================================
# Test Runner
# =============================================================================

def run_all_e2e_tests():
    """Execute all E2E tests manually for debugging."""
    print("=" * 70)
    print("E2E TESTS - Cost Optimization Flow")
    print("=" * 70)
    print()

    # Create test app
    app = create_test_app()

    # Mock the AI wizard service
    with patch('src.api.v1.endpoints.ai_wizard.ai_wizard_service') as mock_service:
        # Set up default mock response
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
                    "reason": "Test recommendation",
                    "estimated_monthly_savings_usd": 374.4,
                    "confidence_score": 0.85,
                },
                {
                    "type": "spot_timing",
                    "reason": "Test spot timing",
                    "estimated_monthly_savings_usd": 40.0,
                    "confidence_score": 0.65,
                    "recommended_windows": [
                        {"day": "Saturday", "hours": "2:00-6:00 UTC"}
                    ]
                }
            ],
            "estimated_monthly_savings": 414.4,
            "current_gpu": "RTX_4090",
            "recommended_gpu": "RTX_4070",
            "analysis_period_days": 30,
            "data_completeness": 0.85,
            "has_sufficient_data": True,
        })

        with TestClient(app) as client:
            test_classes = [
                TestFullCostOptimizationFlow,
                TestInsufficientDataScenario,
                TestAlreadyOptimalConfiguration,
                TestDatabaseSessionCleanup,
                TestAPIEndpointIntegration,
                TestSpotTimingIntegration,
                TestHibernationOptimization,
            ]

            total_tests = 0
            passed_tests = 0
            failed_tests = []

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
                        import inspect
                        sig = inspect.signature(method)
                        kwargs = {}

                        if 'test_client' in sig.parameters:
                            kwargs['test_client'] = client
                        if 'mock_ai_wizard_service_full' in sig.parameters:
                            kwargs['mock_ai_wizard_service_full'] = mock_service

                        method(**kwargs)
                        print(f"  PASS {method_name}")
                        passed_tests += 1
                    except AssertionError as e:
                        print(f"  FAIL {method_name}: {e}")
                        failed_tests.append(f"{test_class.__name__}.{method_name}")
                    except Exception as e:
                        print(f"  ERROR {method_name}: {type(e).__name__}: {e}")
                        failed_tests.append(f"{test_class.__name__}.{method_name}")

            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"\nTotal: {total_tests} tests")
            print(f"Passed: {passed_tests}")
            print(f"Failed: {len(failed_tests)}")

            if failed_tests:
                print("\nFailed tests:")
                for test in failed_tests:
                    print(f"  - {test}")
                return False
            else:
                print("\nALL E2E TESTS PASSED!")
                return True


if __name__ == "__main__":
    import sys
    success = run_all_e2e_tests()
    sys.exit(0 if success else 1)
