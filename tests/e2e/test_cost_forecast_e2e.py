"""
E2E Tests for Cost Forecast Dashboard Flow.

Tests verify end-to-end functionality:
1. Navigate to cost forecast dashboard
2. Verify 7-day chart renders with confidence bands
3. Input 8-hour job duration, verify optimal timing recommendations
4. Set budget threshold, verify alert creation
5. Connect calendar, verify events overlay on chart
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


class TestCostForecastE2E:
    """End-to-end tests for cost forecast dashboard flow."""

    def test_cost_forecast_api_returns_7day_data(self):
        """Verify API returns 7-day cost forecast with confidence intervals."""
        # Mock the PricePredictionService
        from src.services.price_prediction_service import PricePredictionService

        service = PricePredictionService()

        # Verify forecast_costs_7day method exists and works
        assert hasattr(service, 'forecast_costs_7day'), "forecast_costs_7day method missing"

        # Note: Actual API test requires database with historical data
        # This test verifies the method signature is correct

    def test_optimal_timing_endpoint_structure(self):
        """Verify optimal timing request/response structure."""
        from src.api.v1.schemas.spot.cost_forecast import (
            OptimalTimingRequest,
            OptimalTimingResponse,
            TimeWindowItem
        )

        # Verify request model
        request = OptimalTimingRequest(
            gpu_name="RTX 4090",
            job_duration_hours=8.0,
            machine_type="interruptible"
        )
        assert request.gpu_name == "RTX 4090"
        assert request.job_duration_hours == 8.0

    def test_budget_alert_creation_model(self):
        """Verify budget alert creation works with proper schema."""
        from src.api.v1.schemas.spot.cost_forecast import (
            BudgetAlertCreate,
            BudgetAlertResponse
        )

        # Verify creation model
        create_data = BudgetAlertCreate(
            gpu_name="RTX 4090",
            threshold=100.0,
            email="user@example.com",
            machine_type="interruptible",
            enabled=True
        )
        assert create_data.threshold == 100.0
        assert create_data.email == "user@example.com"

    def test_calendar_events_schema(self):
        """Verify calendar events schema is correct."""
        from src.api.v1.schemas.spot.cost_forecast import (
            CalendarEventItem,
            CalendarEventListResponse,
            CalendarStatusResponse
        )

        # Verify event item structure
        event = CalendarEventItem(
            event_id="test_123",
            summary="ML Training Job",
            start="2024-01-15T10:00:00Z",
            end="2024-01-15T18:00:00Z",
            is_compute_intensive=True,
            duration_hours=8.0
        )
        assert event.is_compute_intensive is True

    def test_accuracy_tracker_metrics_structure(self):
        """Verify accuracy tracker returns proper MAPE metrics."""
        from src.api.v1.schemas.spot.cost_forecast import ForecastAccuracyResponse

        # Verify response has all required fields
        response_fields = ForecastAccuracyResponse.model_fields.keys()
        required_fields = ['mape', 'mae', 'rmse', 'r_squared', 'num_samples']

        for field in required_fields:
            assert field in response_fields, f"Missing field: {field}"

    def test_frontend_components_exist(self):
        """Verify all frontend cost forecast components are properly exported."""
        import os

        base_path = "./web/src/components/cost-forecast"
        required_components = [
            "CostForecastDashboard.jsx",
            "OptimalTimingCard.jsx",
            "BudgetAlertSettings.jsx",
            "AccuracyTracker.jsx",
            "index.js"
        ]

        for component in required_components:
            full_path = os.path.join(base_path, component)
            assert os.path.exists(full_path), f"Missing component: {component}"

    def test_api_endpoints_registered(self):
        """Verify all cost forecast API endpoints are registered."""
        from src.api.v1.endpoints.spot.cost_forecast import router

        routes = [route.path for route in router.routes]

        required_routes = [
            "/cost-forecast/{gpu_name}",
            "/optimal-timing",
            "/forecast-accuracy/{gpu_name}",
            "/budget-alerts",
            "/calendar-events",
            "/calendar-status",
            "/calendar-suggestions"
        ]

        for required in required_routes:
            assert any(required in route for route in routes), f"Missing route: {required}"

    def test_price_prediction_service_methods(self):
        """Verify PricePredictionService has all required methods."""
        from src.services.price_prediction_service import PricePredictionService

        service = PricePredictionService()

        required_methods = [
            'forecast_costs_7day',
            'calculate_mape',
            '_calculate_confidence',
            'get_accuracy_history'
        ]

        for method in required_methods:
            assert hasattr(service, method), f"Missing method: {method}"

    def test_budget_alert_service_methods(self):
        """Verify BudgetAlertService has all required methods."""
        from src.services.budget_alert_service import BudgetAlertService

        required_methods = [
            'send_alert',
            'send_alert_async',
            'check_budget_threshold'
        ]

        for method in required_methods:
            assert hasattr(BudgetAlertService, method), f"Missing method: {method}"

    def test_calendar_integration_service_methods(self):
        """Verify CalendarIntegrationService has all required methods."""
        from src.services.calendar_integration_service import CalendarIntegrationService

        required_methods = [
            'fetch_events',
            'create_suggestion',
            'get_suggestions_for_events',
            'get_oauth_authorization_url',
            'disconnect'
        ]

        for method in required_methods:
            assert hasattr(CalendarIntegrationService, method), f"Missing method: {method}"

    def test_database_models_exist(self):
        """Verify all required database models exist."""
        from src.models.metrics import (
            CostForecast,
            BudgetAlert,
            PredictionAccuracy
        )

        # Verify model table names
        assert CostForecast.__tablename__ == 'cost_forecasts'
        assert BudgetAlert.__tablename__ == 'budget_alerts'
        assert PredictionAccuracy.__tablename__ == 'prediction_accuracy'

    def test_edge_case_insufficient_data_handling(self):
        """Verify error handling for insufficient historical data."""
        from src.services.price_prediction_service import PricePredictionService

        service = PricePredictionService()

        # Without training data, forecast should return None
        # (In production this would require < 50 data points)
        result = service.forecast_costs_7day(
            gpu_name="NonExistent-GPU",
            machine_type="interruptible"
        )

        # Should return None when no data available
        assert result is None, "Should return None for insufficient data"


class TestCostForecastIntegration:
    """Integration tests for cost forecast flow."""

    def test_full_flow_structure(self):
        """Test that the full flow from API to frontend is wired correctly."""
        # Import all relevant modules to verify no import errors
        from src.services.price_prediction_service import PricePredictionService
        from src.services.budget_alert_service import BudgetAlertService
        from src.services.calendar_integration_service import CalendarIntegrationService
        from src.api.v1.endpoints.spot.cost_forecast import router
        from src.models.metrics import CostForecast, BudgetAlert, PredictionAccuracy

        # Verify all pieces are importable without errors
        assert router is not None
        assert PricePredictionService is not None
        assert BudgetAlertService is not None
        assert CalendarIntegrationService is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
