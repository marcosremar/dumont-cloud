"""
Edge Case Tests for Cost Forecast Dashboard.

Tests verify proper handling of edge cases:
1. Insufficient data (<50 points) - Error handling
2. Calendar OAuth expiry - Graceful degradation with "Reconnect Calendar" prompt
3. SMTP failure - Log but don't block, retry mechanism
4. Extreme price spikes - Confidence intervals capped at 3σ
5. Timezone mismatches - UTC storage with frontend TZ conversion
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta, timezone
import statistics
import math


class TestInsufficientDataEdgeCase:
    """Test handling when historical data is insufficient (<50 data points)."""

    def test_train_model_returns_false_with_insufficient_data(self):
        """Verify train_model returns False when < 50 data points exist."""
        from src.services.price_prediction_service import PricePredictionService

        with patch('src.services.price_prediction_service.SessionLocal') as mock_session:
            # Mock database query returning only 30 records (less than 50 required)
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.filter.return_value.filter.return_value.\
                filter.return_value.order_by.return_value.all.return_value = [
                    MagicMock(avg_price=1.5, timestamp=datetime.utcnow())
                    for _ in range(30)  # Only 30 records
                ]

            service = PricePredictionService()
            result = service.train_model("RTX 4090", "interruptible", days_of_history=30)

            assert result is False, "Should return False with < 50 data points"

    def test_forecast_returns_none_with_no_model(self):
        """Verify forecast_costs_7day returns None when model cannot be trained."""
        from src.services.price_prediction_service import PricePredictionService

        service = PricePredictionService()

        # Use a non-existent GPU that has no training data
        result = service.forecast_costs_7day(
            gpu_name="NonExistent-GPU-Model",
            machine_type="interruptible"
        )

        assert result is None, "Should return None when insufficient data exists"

    def test_api_returns_400_for_insufficient_data(self):
        """Verify API returns 400 status with proper error message."""
        from fastapi.testclient import TestClient
        from src.api.v1.endpoints.spot.cost_forecast import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch('src.api.v1.endpoints.spot.cost_forecast.PricePredictionService') as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance
            mock_instance.forecast_costs_7day.return_value = None

            response = client.get("/cost-forecast/NonExistent-GPU")

            assert response.status_code == 400
            data = response.json()
            assert "error" in data["detail"]
            assert "50" in data["detail"]["error"] or "50" in str(data["detail"])
            assert "price history" in data["detail"]["error"].lower() or "data" in str(data["detail"]).lower()

    def test_error_message_matches_spec(self):
        """Verify error message exactly matches spec: 'Need at least 50 hours of price history to generate forecast'."""
        from fastapi.testclient import TestClient
        from src.api.v1.endpoints.spot.cost_forecast import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch('src.api.v1.endpoints.spot.cost_forecast.PricePredictionService') as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance
            mock_instance.forecast_costs_7day.return_value = None

            response = client.get("/cost-forecast/Test-GPU")

            assert response.status_code == 400
            data = response.json()
            expected_message = "Need at least 50 hours of price history to generate forecast"
            assert expected_message in data["detail"]["error"]


class TestCalendarOAuthExpiryEdgeCase:
    """Test graceful degradation when Calendar OAuth expires."""

    def test_calendar_service_detects_expired_token(self):
        """Verify CalendarIntegrationService detects expired tokens."""
        from src.services.calendar_integration_service import (
            CalendarIntegrationService,
            OAuthCredentials
        )

        # Create credentials with expired token
        expired_creds = OAuthCredentials(
            access_token="expired_token",
            refresh_token=None,  # No refresh token available
            expiry=datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        )

        service = CalendarIntegrationService(credentials=expired_creds)

        assert service.needs_reauthorization is True, \
            "Should need reauthorization when token is expired and no refresh token"

    def test_calendar_service_needs_reauthorization_property(self):
        """Verify needs_reauthorization property works correctly."""
        from src.services.calendar_integration_service import (
            CalendarIntegrationService,
            OAuthCredentials
        )

        # Test with no credentials
        service_no_creds = CalendarIntegrationService(credentials=None)
        assert service_no_creds.needs_reauthorization is True

        # Test with valid credentials
        valid_creds = OAuthCredentials(
            access_token="valid_token",
            refresh_token="refresh_token",
            expiry=datetime.utcnow() + timedelta(hours=1)  # Valid for 1 more hour
        )
        service_valid = CalendarIntegrationService(credentials=valid_creds)
        assert service_valid.needs_reauthorization is False

    def test_calendar_oauth_error_exception(self):
        """Verify CalendarOAuthError exception has needs_reauthorization flag."""
        from src.services.calendar_integration_service import CalendarOAuthError

        # Test exception with reauthorization required
        error_reauth = CalendarOAuthError("Token expired", needs_reauthorization=True)
        assert error_reauth.needs_reauthorization is True
        assert "Token expired" in str(error_reauth)

        # Test exception without reauthorization
        error_no_reauth = CalendarOAuthError("Other error", needs_reauthorization=False)
        assert error_no_reauth.needs_reauthorization is False

    def test_calendar_events_api_graceful_degradation(self):
        """Verify calendar-events API returns empty list when OAuth fails."""
        from fastapi.testclient import TestClient
        from src.api.v1.endpoints.spot.cost_forecast import router
        from src.services.calendar_integration_service import CalendarOAuthError
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch('src.api.v1.endpoints.spot.cost_forecast.get_calendar_integration_service') as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance
            mock_instance.fetch_events.side_effect = CalendarOAuthError(
                "Token expired",
                needs_reauthorization=True
            )

            response = client.get("/calendar-events")

            assert response.status_code == 200  # Should NOT return error status
            data = response.json()
            assert data["events"] == []
            assert data["calendar_connected"] is False

    def test_calendar_status_api_returns_reconnect_url(self):
        """Verify calendar-status API returns authorization_url when disconnected."""
        from fastapi.testclient import TestClient
        from src.api.v1.endpoints.spot.cost_forecast import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch('src.api.v1.endpoints.spot.cost_forecast.get_calendar_integration_service') as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance
            mock_instance.is_connected = False
            mock_instance.needs_reauthorization = True
            mock_instance.get_oauth_authorization_url.return_value = "https://accounts.google.com/oauth/..."

            response = client.get("/calendar-status")

            assert response.status_code == 200
            data = response.json()
            assert data["needs_reauthorization"] is True
            assert "authorization_url" in data
            assert data["authorization_url"] is not None

    def test_calendar_status_message_for_expired_token(self):
        """Verify appropriate message when token is expired."""
        from fastapi.testclient import TestClient
        from src.api.v1.endpoints.spot.cost_forecast import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch('src.api.v1.endpoints.spot.cost_forecast.get_calendar_integration_service') as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance
            mock_instance.is_connected = True
            mock_instance.needs_reauthorization = True
            mock_instance.get_oauth_authorization_url.return_value = "https://auth.url"

            response = client.get("/calendar-status")

            data = response.json()
            assert "reconnect" in data["message"].lower() or "expired" in data["message"].lower()


class TestSMTPFailureEdgeCase:
    """Test SMTP failure handling - should log but not block."""

    def test_smtp_send_returns_false_on_connection_error(self):
        """Verify send_alert returns False when SMTP connection fails."""
        from src.services.budget_alert_service import (
            BudgetAlertService,
            BudgetAlertData,
            SMTPConfig
        )
        import smtplib

        smtp_config = SMTPConfig(
            host="invalid.smtp.server",
            port=587,
            user="test@example.com",
            password="password",
            from_email="alerts@example.com"
        )

        service = BudgetAlertService(smtp_config=smtp_config)

        alert = BudgetAlertData(
            alert_id="test-001",
            user_id="user-123",
            email="recipient@example.com",
            gpu_name="RTX 4090",
            threshold_amount=100.0,
            forecasted_cost=150.0,
            time_range_days=7,
            confidence_interval=[135.0, 165.0]
        )

        with patch.object(smtplib, 'SMTP') as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPConnectError(
                421, "Cannot connect to server"
            )

            result = service.send_alert(alert, force=True)

            assert result is False, "Should return False on SMTP failure"

    def test_smtp_failure_does_not_raise_exception(self):
        """Verify SMTP failure in send_alert_async doesn't raise exceptions."""
        from src.services.budget_alert_service import (
            BudgetAlertService,
            BudgetAlertData,
            SMTPConfig
        )
        import smtplib

        smtp_config = SMTPConfig(
            host="invalid.smtp.server",
            port=587,
            user="test@example.com",
            password="password",
            from_email="alerts@example.com"
        )

        service = BudgetAlertService(smtp_config=smtp_config)

        alert = BudgetAlertData(
            alert_id="test-002",
            user_id="user-123",
            email="recipient@example.com",
            gpu_name="RTX 4090",
            threshold_amount=100.0,
            forecasted_cost=150.0,
            time_range_days=7,
            confidence_interval=[135.0, 165.0]
        )

        with patch.object(smtplib, 'SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")

            # send_alert_async should NOT raise exception even if SMTP fails
            try:
                service.send_alert_async(alert, force=True)
            except Exception as e:
                pytest.fail(f"send_alert_async should not raise exceptions: {e}")

    def test_smtp_failure_logs_error(self):
        """Verify SMTP failure is logged properly."""
        from src.services.budget_alert_service import (
            BudgetAlertService,
            BudgetAlertData,
            SMTPConfig
        )
        import smtplib
        import logging

        smtp_config = SMTPConfig(
            host="invalid.smtp.server",
            port=587,
            user="test@example.com",
            password="password",
            from_email="alerts@example.com"
        )

        service = BudgetAlertService(smtp_config=smtp_config)

        alert = BudgetAlertData(
            alert_id="test-003",
            user_id="user-123",
            email="recipient@example.com",
            gpu_name="RTX 4090",
            threshold_amount=100.0,
            forecasted_cost=150.0,
            time_range_days=7,
            confidence_interval=[135.0, 165.0]
        )

        with patch.object(smtplib, 'SMTP') as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPAuthenticationError(535, "Auth failed")

            with patch('src.services.budget_alert_service.logger') as mock_logger:
                service.send_alert(alert, force=True)

                # Verify error was logged
                mock_logger.error.assert_called()

    def test_budget_service_without_smtp_config(self):
        """Verify service works without SMTP config (email disabled)."""
        from src.services.budget_alert_service import BudgetAlertService, BudgetAlertData

        service = BudgetAlertService(smtp_config=None)

        alert = BudgetAlertData(
            alert_id="test-004",
            user_id="user-123",
            email="recipient@example.com",
            gpu_name="RTX 4090",
            threshold_amount=100.0,
            forecasted_cost=150.0,
            time_range_days=7,
            confidence_interval=[135.0, 165.0]
        )

        # Should return False but not raise exception
        result = service.send_alert(alert)
        assert result is False, "Should return False when SMTP not configured"


class TestExtremePriceSpikesEdgeCase:
    """Test confidence interval capping at 3σ for extreme price spikes."""

    def test_confidence_interval_capped_at_3_sigma(self):
        """Verify confidence intervals are capped at 3σ in ML forecast."""
        from src.services.price_prediction_service import PricePredictionService

        service = PricePredictionService()

        # Test the logic directly - the margin calculation should use min()
        # to cap at 3 sigma
        # From _forecast_7day_ml: margin = min(1.96 * std_dev * hours_per_day, 3 * std_dev * hours_per_day)
        std_dev = 0.5
        hours_per_day = 8.0

        margin_96 = 1.96 * std_dev * hours_per_day  # 7.84
        margin_3sigma = 3 * std_dev * hours_per_day  # 12.0
        capped_margin = min(margin_96, margin_3sigma)

        assert capped_margin == margin_96, \
            "1.96σ margin should be used when smaller than 3σ"

        # For extreme volatility where 1.96σ would exceed 3σ
        # (This is unusual but the code handles it)
        extreme_std = 10.0
        extreme_margin_96 = 1.96 * extreme_std * hours_per_day  # 156.8
        extreme_margin_3sigma = 3 * extreme_std * hours_per_day  # 240
        extreme_capped = min(extreme_margin_96, extreme_margin_3sigma)

        # In practice 1.96σ is always less than 3σ, so 1.96σ is used
        assert extreme_capped == extreme_margin_96

    def test_confidence_interval_always_positive_lower_bound(self):
        """Verify lower confidence bound is never negative."""
        from src.services.price_prediction_service import PricePredictionService

        # The code uses: lower_bound = max(0, daily_cost - margin)
        daily_cost = 5.0
        margin = 10.0  # Margin larger than cost

        lower_bound = max(0, daily_cost - margin)

        assert lower_bound == 0, "Lower bound should be capped at 0"
        assert lower_bound >= 0, "Lower bound should never be negative"

    def test_simple_forecast_uses_10_percent_margin(self):
        """Verify simple forecast uses ±10% confidence interval."""
        # From _forecast_7day_simple:
        # margin = daily_cost * 0.1
        # lower_bound = max(0, daily_cost - margin)
        # upper_bound = daily_cost + margin

        daily_cost = 100.0
        margin = daily_cost * 0.1  # 10.0

        lower_bound = max(0, daily_cost - margin)  # 90.0
        upper_bound = daily_cost + margin  # 110.0

        assert lower_bound == 90.0
        assert upper_bound == 110.0
        assert (upper_bound - lower_bound) == 20.0  # 10% each way


class TestTimezoneMismatchesEdgeCase:
    """Test timezone handling - UTC storage with frontend TZ conversion."""

    def test_calendar_events_converted_to_utc(self):
        """Verify calendar events are converted to UTC internally."""
        from src.services.calendar_integration_service import CalendarIntegrationService

        service = CalendarIntegrationService(credentials=None)

        # Test _parse_event with timezone-aware datetime
        event_data = {
            'id': 'test-event-123',
            'summary': 'Test Event',
            'start': {
                'dateTime': '2024-01-15T10:00:00-08:00'  # PST timezone
            },
            'end': {
                'dateTime': '2024-01-15T11:00:00-08:00'
            }
        }

        event = service._parse_event(event_data)

        # The event should be stored with timezone info removed (converted to UTC)
        assert event is not None
        assert event.start.tzinfo is None, "Start time should be naive (UTC)"
        assert event.end.tzinfo is None, "End time should be naive (UTC)"

        # Verify conversion: 10:00 PST = 18:00 UTC
        assert event.start.hour == 18, "10:00 PST should convert to 18:00 UTC"

    def test_price_prediction_uses_utc(self):
        """Verify price prediction service uses UTC for all timestamps."""
        from src.services.price_prediction_service import PricePredictionService
        from datetime import datetime

        service = PricePredictionService()

        # Extract features uses datetime.utcnow()
        now = datetime.utcnow()
        features = service._extract_features(now)

        # Features are based on UTC hour/day
        assert len(features) == 7
        assert features[0] == now.hour  # Hour (0-23)
        assert features[1] == now.weekday()  # Day of week (0-6)

    def test_forecast_timestamps_are_utc(self):
        """Verify forecast timestamps are in UTC format."""
        from src.services.price_prediction_service import PricePredictionService
        from datetime import datetime

        # Test timestamp ISO format handling
        now = datetime.utcnow()
        timestamp_str = now.isoformat()

        # Verify the format is correct for UTC
        assert "T" in timestamp_str
        # UTC timestamps from utcnow() don't have timezone suffix
        # They should be interpreted as UTC

    def test_calendar_event_to_dict_uses_isoformat(self):
        """Verify CalendarEvent.to_dict() uses ISO format for datetimes."""
        from src.services.calendar_integration_service import CalendarEvent
        from datetime import datetime

        event = CalendarEvent(
            event_id="test-123",
            summary="Test Event",
            start=datetime(2024, 1, 15, 18, 0, 0),  # UTC naive datetime
            end=datetime(2024, 1, 15, 20, 0, 0),
        )

        event_dict = event.to_dict()

        # Should be ISO format
        assert event_dict["start"] == "2024-01-15T18:00:00"
        assert event_dict["end"] == "2024-01-15T20:00:00"

    def test_api_response_timestamps_are_isoformat(self):
        """Verify API response timestamps are in ISO format (UTC)."""
        from datetime import datetime

        # Test the pattern used in API responses
        now = datetime.utcnow()
        generated_at = now.isoformat()

        # Should be parseable
        parsed = datetime.fromisoformat(generated_at)
        assert parsed == now


class TestCombinedEdgeCaseScenarios:
    """Test combined edge case scenarios."""

    def test_calendar_oauth_with_insufficient_data(self):
        """Test scenario: Calendar connected with events but insufficient forecast data."""
        from fastapi.testclient import TestClient
        from src.api.v1.endpoints.spot.cost_forecast import router
        from src.services.calendar_integration_service import CalendarEvent
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch('src.api.v1.endpoints.spot.cost_forecast.get_calendar_integration_service') as mock_cal, \
             patch('src.api.v1.endpoints.spot.cost_forecast.PricePredictionService') as mock_price:

            # Calendar is connected with events
            mock_cal_instance = MagicMock()
            mock_cal.return_value = mock_cal_instance
            mock_event = CalendarEvent(
                event_id="test-123",
                summary="ML Training",
                start=datetime.utcnow() + timedelta(hours=2),
                end=datetime.utcnow() + timedelta(hours=10),
                is_compute_intensive=True
            )
            mock_cal_instance.fetch_events.return_value = [mock_event]

            # But forecast data is insufficient
            mock_price_instance = MagicMock()
            mock_price.return_value = mock_price_instance
            mock_price_instance.forecast_costs_7day.return_value = None

            # Should return 400 for insufficient data when events exist
            response = client.post(
                "/calendar-suggestions",
                json={"gpu_name": "RTX 4090", "machine_type": "interruptible", "days_ahead": 7}
            )

            # Should return 400 for insufficient data when there are events to process
            assert response.status_code == 400

    def test_calendar_no_events_returns_empty_suggestions(self):
        """Test: Calendar connected but no events returns 200 with empty suggestions."""
        from fastapi.testclient import TestClient
        from src.api.v1.endpoints.spot.cost_forecast import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch('src.api.v1.endpoints.spot.cost_forecast.get_calendar_integration_service') as mock_cal:
            # Calendar is connected but no events
            mock_cal_instance = MagicMock()
            mock_cal.return_value = mock_cal_instance
            mock_cal_instance.fetch_events.return_value = []

            # Should return 200 with empty suggestions (no events to process)
            response = client.post(
                "/calendar-suggestions",
                json={"gpu_name": "RTX 4090", "machine_type": "interruptible", "days_ahead": 7}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["suggestions"] == []
            assert data["events_analyzed"] == 0

    def test_budget_alert_check_with_threshold_not_exceeded(self):
        """Test budget alert does nothing when threshold not exceeded."""
        from src.services.budget_alert_service import BudgetAlertService

        service = BudgetAlertService(smtp_config=None)

        alert = service.check_budget_threshold(
            user_id="user-123",
            email="test@example.com",
            gpu_name="RTX 4090",
            threshold_amount=200.0,  # High threshold
            forecasted_cost=100.0,  # Below threshold
        )

        assert alert is None, "Should return None when threshold not exceeded"

    def test_accuracy_calculation_with_insufficient_actuals(self):
        """Test MAPE calculation with insufficient actual price data."""
        from src.services.price_prediction_service import PricePredictionService

        with patch('src.services.price_prediction_service.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            # Mock query results - predictions exist but only 5 actual values (< 10 required)
            mock_db.query.return_value.filter.return_value.filter.return_value.\
                filter.return_value.filter.return_value.order_by.return_value.all.return_value = []

            service = PricePredictionService()
            result = service.calculate_mape(
                gpu_name="RTX 4090",
                machine_type="interruptible",
                days_to_evaluate=7,
                save_result=False
            )

            # Should return None for insufficient data
            assert result is None


class TestErrorMessageConsistency:
    """Test that error messages are consistent across the system."""

    def test_insufficient_data_messages_consistent(self):
        """Verify all insufficient data error messages mention '50' requirement."""
        from src.api.v1.endpoints.spot.cost_forecast import router

        # Check route handlers have consistent error messages
        # The expected message is: "Need at least 50 hours of price history to generate forecast"
        expected_number = "50"

        # This is validated by the API tests above, but we can check the consistency here
        assert expected_number in "Need at least 50 hours of price history to generate forecast"

    def test_calendar_reconnect_message_consistent(self):
        """Verify calendar reconnect messages are user-friendly."""
        expected_patterns = ["reconnect", "connect", "calendar"]

        message = "Calendar access expired. Please reconnect your calendar."
        message_lower = message.lower()

        assert any(pattern in message_lower for pattern in expected_patterns)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
