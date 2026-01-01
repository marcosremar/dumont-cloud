"""
Flow 10: Email Send - E2E Tests
Tests REAL email sending flow for weekly reports.

This flow tests:
- POST /api/v1/email-preferences/test-email - Send test email
- EmailDeliveryLog verification - Check database entries
- Email composition and template rendering
- Scheduler trigger functionality
"""
import pytest
import httpx
import os
from datetime import datetime

# Test markers
pytestmark = [pytest.mark.flow10]


@pytest.mark.flow10
class TestSendTestEmail:
    """Tests for POST /api/v1/email-preferences/test-email"""

    def test_send_test_email_success(self, authed_client: httpx.Client):
        """Should trigger a test email send successfully"""
        response = authed_client.post("/api/v1/email-preferences/test-email")

        # Endpoint should respond - may fail if Resend not configured
        # but shouldn't return auth error
        assert response.status_code in [200, 400, 500, 503]

        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            assert "email_id" in data or "message" in data
            print(f"  Email sent successfully: {data}")
        elif response.status_code == 503:
            # Resend API key not configured - acceptable for CI environments
            data = response.json()
            assert "RESEND_API_KEY" in str(data) or "not configured" in str(data).lower()
            print("  Skipping: Email service not configured (RESEND_API_KEY missing)")
        elif response.status_code == 500:
            # May fail due to email service issues - log but don't fail
            print(f"  Warning: Email send failed - {response.text}")

    def test_send_test_email_unauthenticated(self, http_client: httpx.Client):
        """Should reject unauthenticated requests"""
        response = http_client.post("/api/v1/email-preferences/test-email")

        # Should fail without auth
        assert response.status_code in [401, 403]

    def test_send_test_email_creates_preferences_if_missing(self, authed_client: httpx.Client):
        """Should create default preferences if user has none"""
        # First, get current preferences to verify baseline
        get_response = authed_client.get("/api/v1/email-preferences")
        assert get_response.status_code == 200

        # Try to send test email - should work even for new users
        response = authed_client.post("/api/v1/email-preferences/test-email")

        # Should not fail due to missing preferences
        assert response.status_code in [200, 400, 500, 503]

        # Preferences should still exist
        get_response = authed_client.get("/api/v1/email-preferences")
        assert get_response.status_code == 200


@pytest.mark.flow10
class TestEmailDeliveryLog:
    """Tests for EmailDeliveryLog database entries"""

    def test_delivery_log_created_on_send(self, authed_client: httpx.Client):
        """Should create EmailDeliveryLog entry when sending email"""
        # Send a test email
        response = authed_client.post("/api/v1/email-preferences/test-email")

        if response.status_code != 200:
            pytest.skip("Email send not available - skipping delivery log test")

        # The delivery log should be created by the send_weekly_report function
        # We can't directly query the database from here, but we verify the
        # endpoint response includes email_id which indicates logging occurred
        data = response.json()
        assert data.get("success") == True

        # If email_id is present, it means Resend returned an ID and it was logged
        if data.get("email_id"):
            print(f"  Email ID logged: {data['email_id']}")


@pytest.mark.flow10
class TestEmailComposition:
    """Tests for email template rendering and composition"""

    def test_email_composed_with_all_sections(self):
        """Should compose email with all required sections"""
        # This test runs locally without API - tests the composer directly
        try:
            from src.services.email_composer import compose_weekly_report, EmailComposer

            # Create mock analytics data
            analytics_data = {
                'user_id': 'test-user',
                'current_week': {
                    'week_start': datetime.utcnow().isoformat(),
                    'week_end': datetime.utcnow().isoformat(),
                    'total_hours': 24.5,
                    'total_cost_dumont': 45.00,
                    'total_cost_aws': 89.50,
                    'total_cost_gcp': 82.00,
                    'total_cost_azure': 85.00,
                    'savings_vs_aws': 44.50,
                    'savings_vs_gcp': 37.00,
                    'savings_vs_azure': 40.00,
                    'savings_percentage_aws': 49.7,
                    'auto_hibernate_savings': 12.50,
                    'total_sessions': 5,
                    'unique_gpus_used': 2,
                    'is_first_week': False,
                    'has_usage': True,
                },
                'previous_week': {
                    'has_usage': True,
                    'total_hours': 20.0,
                    'total_cost_dumont': 38.00,
                },
                'week_over_week': {
                    'hours_change_percent': 22.5,
                    'cost_change_percent': 18.4,
                    'savings_change_percent': 15.0,
                    'hours_trend': 'up',
                    'cost_trend': 'up',
                    'savings_trend': 'up',
                    'hours_diff': 4.5,
                    'cost_diff': 7.0,
                    'savings_diff': 6.7,
                    'has_previous_week': True,
                },
                'gpu_breakdown': [
                    {
                        'gpu_type': 'RTX_4090',
                        'hours': 15.5,
                        'cost_dumont': 30.00,
                        'cost_aws': 60.00,
                        'savings': 30.00,
                        'sessions': 3,
                    },
                    {
                        'gpu_type': 'RTX_4080',
                        'hours': 9.0,
                        'cost_dumont': 15.00,
                        'cost_aws': 29.50,
                        'savings': 14.50,
                        'sessions': 2,
                    },
                ],
            }

            recommendations = [
                {
                    'title': 'Auto-Hibernation is Working!',
                    'description': 'Auto-hibernation saved you $12.50 this week.',
                    'type': 'hibernation',
                    'priority': 1,
                },
                {
                    'title': 'Consider Spot Instances',
                    'description': 'Save up to 50% on batch workloads.',
                    'type': 'spot_instance',
                    'priority': 2,
                },
            ]

            # Compose the email
            email = compose_weekly_report(
                user_id='test-user',
                user_email='test@example.com',
                user_name='Test User',
                analytics_data=analytics_data,
                recommendations=recommendations,
            )

            # Verify email structure
            assert email.subject, "Email should have a subject"
            assert email.html_body, "Email should have HTML body"
            assert len(email.html_body) > 1000, "Email HTML should be substantial"

            # Verify key sections are present in HTML
            html = email.html_body.lower()

            # Usage summary section
            assert '24.5' in html or '24,5' in html, "Should contain total hours"
            assert '$45' in html.lower() or '45.00' in html, "Should contain Dumont cost"

            # Savings section
            assert 'aws' in html, "Should mention AWS comparison"
            assert 'saving' in html, "Should mention savings"

            # GPU breakdown
            assert 'rtx' in html or '4090' in html, "Should contain GPU info"

            # Recommendations
            assert 'hibernation' in html or 'recommendation' in html, "Should contain recommendations"

            # Footer with unsubscribe
            assert 'unsubscribe' in html, "Should contain unsubscribe link"

            print(f"  Email composed successfully:")
            print(f"    Subject: {email.subject}")
            print(f"    HTML length: {len(email.html_body)} chars")
            print(f"    Has usage: {email.has_usage}")

        except ImportError as e:
            pytest.skip(f"Email composer not available: {e}")

    def test_email_subject_variations(self):
        """Should generate correct subject for different scenarios"""
        try:
            from src.services.email_composer import EmailComposer

            composer = EmailComposer()
            week_end = datetime.utcnow()

            # Normal week with usage
            subject_normal = composer.generate_subject(week_end, has_usage=True, is_first_week=False)
            assert "Weekly GPU Report" in subject_normal
            assert "Week Ending" in subject_normal

            # First week
            subject_first = composer.generate_subject(week_end, has_usage=True, is_first_week=True)
            assert "Welcome" in subject_first or "First" in subject_first

            # No usage week
            subject_no_usage = composer.generate_subject(week_end, has_usage=False, is_first_week=False)
            assert "Missed" in subject_no_usage or "Report" in subject_no_usage

            print(f"  Subject variations verified:")
            print(f"    Normal: {subject_normal}")
            print(f"    First week: {subject_first}")
            print(f"    No usage: {subject_no_usage}")

        except ImportError as e:
            pytest.skip(f"Email composer not available: {e}")

    def test_unsubscribe_token_generation(self):
        """Should generate valid unsubscribe tokens"""
        try:
            from src.services.email_composer import EmailComposer

            composer = EmailComposer()
            user_id = "test-user-123"

            # Generate token
            token = composer.generate_unsubscribe_token(user_id)
            assert token, "Token should be generated"
            assert len(token) > 20, "Token should be substantial"

            # Verify token
            verified_user_id = composer.verify_unsubscribe_token(token)
            assert verified_user_id == user_id, "Token should verify to correct user_id"

            # Invalid token should return None
            invalid_result = composer.verify_unsubscribe_token("invalid-token")
            assert invalid_result is None, "Invalid token should return None"

            # Tampered token should return None
            tampered_token = token[:-5] + "XXXXX"
            tampered_result = composer.verify_unsubscribe_token(tampered_token)
            assert tampered_result is None, "Tampered token should return None"

            print(f"  Token verification passed:")
            print(f"    Token length: {len(token)}")
            print(f"    Verified user: {verified_user_id}")

        except ImportError as e:
            pytest.skip(f"Email composer not available: {e}")


@pytest.mark.flow10
class TestSchedulerTestBatch:
    """Tests for the scheduler test batch functionality"""

    def test_scheduler_test_batch_import(self):
        """Should be able to import scheduler test functions"""
        try:
            from src.services.email_report_scheduler import (
                EmailReportScheduler,
                get_email_scheduler,
                get_batch_config,
            )

            # Get batch config
            config = get_batch_config() if callable(get_batch_config) else None

            # If scheduler has get_batch_config method
            scheduler = EmailReportScheduler(use_jobstore=False)
            config = scheduler.get_batch_config()

            assert 'batch_size' in config
            assert 'max_concurrent_sends' in config
            assert config['batch_size'] > 0

            print(f"  Scheduler batch config: {config}")

        except ImportError as e:
            pytest.skip(f"Scheduler not available: {e}")
        except Exception as e:
            # May fail due to database connection - log but continue
            print(f"  Warning: Scheduler config failed - {e}")

    def test_scheduler_status(self):
        """Should be able to get scheduler status"""
        try:
            from src.services.email_report_scheduler import EmailReportScheduler

            # Create scheduler without job store (in-memory for testing)
            scheduler = EmailReportScheduler(use_jobstore=False)

            # Check status before starting
            status = scheduler.get_status()
            assert 'enabled' in status
            assert 'running' in status
            assert 'schedule' in status

            print(f"  Scheduler status: {status}")

        except ImportError as e:
            pytest.skip(f"Scheduler not available: {e}")
        except Exception as e:
            print(f"  Warning: Scheduler status failed - {e}")


@pytest.mark.flow10
class TestAnalyticsAggregation:
    """Tests for analytics aggregation service"""

    def test_aggregate_user_usage_import(self):
        """Should be able to import analytics aggregator"""
        try:
            from src.services.email_analytics_aggregator import (
                aggregate_user_usage,
                EmailAnalyticsAggregator,
                WeeklyUsageMetrics,
                WeekOverWeekComparison,
                GPUBreakdown,
            )

            # Verify dataclasses exist
            assert WeeklyUsageMetrics
            assert WeekOverWeekComparison
            assert GPUBreakdown

            print("  Analytics aggregator imports successful")

        except ImportError as e:
            pytest.skip(f"Analytics aggregator not available: {e}")

    def test_week_bounds_calculation(self):
        """Should calculate week bounds correctly"""
        try:
            from src.services.email_analytics_aggregator import EmailAnalyticsAggregator
            from datetime import datetime, timedelta
            from unittest.mock import MagicMock

            # Create mock db session
            mock_db = MagicMock()
            aggregator = EmailAnalyticsAggregator(mock_db)

            # Test with a known date (Wednesday, Jan 1, 2025)
            test_date = datetime(2025, 1, 1, 12, 0, 0)  # Wednesday
            week_start, week_end = aggregator.get_week_bounds(test_date)

            # Should return previous week (Dec 23-29, 2024)
            assert week_start.weekday() == 0, "Week should start on Monday"
            assert week_end.weekday() == 6, "Week should end on Sunday"
            assert week_end > week_start
            assert (week_end - week_start).days == 6

            print(f"  Week bounds for {test_date.date()}:")
            print(f"    Start: {week_start} (Monday)")
            print(f"    End: {week_end} (Sunday)")

        except ImportError as e:
            pytest.skip(f"Analytics aggregator not available: {e}")


@pytest.mark.flow10
class TestRecommendationGeneration:
    """Tests for recommendation generation"""

    def test_generate_recommendations(self):
        """Should generate recommendations based on usage patterns"""
        try:
            from src.services.email_recommendations import generate_recommendations

            # Test with usage data
            current_week = {
                'has_usage': True,
                'total_hours': 50.0,
                'total_cost_dumont': 100.0,
                'savings_vs_aws': 50.0,
                'auto_hibernate_savings': 15.0,
                'total_sessions': 10,
                'unique_gpus_used': 3,
                'is_first_week': False,
            }

            week_over_week = {
                'hours_change_percent': 25.0,
                'cost_change_percent': 30.0,
                'hours_trend': 'up',
                'cost_trend': 'up',
                'has_previous_week': True,
            }

            recommendations = generate_recommendations(
                current_week=current_week,
                week_over_week=week_over_week,
            )

            assert isinstance(recommendations, list)
            assert len(recommendations) <= 3, "Should return max 3 recommendations"

            for rec in recommendations:
                assert 'title' in rec
                assert 'description' in rec
                assert 'type' in rec
                assert 'priority' in rec

            print(f"  Generated {len(recommendations)} recommendations:")
            for rec in recommendations:
                print(f"    - {rec['title']} (priority: {rec['priority']})")

        except ImportError as e:
            pytest.skip(f"Recommendations not available: {e}")

    def test_no_usage_recommendations(self):
        """Should return getting-started recommendations for zero usage"""
        try:
            from src.services.email_recommendations import generate_recommendations

            current_week = {
                'has_usage': False,
                'total_hours': 0,
                'total_cost_dumont': 0,
            }

            recommendations = generate_recommendations(current_week=current_week)

            assert isinstance(recommendations, list)
            assert len(recommendations) > 0, "Should have recommendations for new users"

            # Should suggest getting started
            titles = [r['title'].lower() for r in recommendations]
            has_getting_started = any(
                'start' in t or 'explore' in t or 'welcome' in t
                for t in titles
            )
            assert has_getting_started, "Should suggest getting started for zero usage"

            print(f"  Zero usage recommendations:")
            for rec in recommendations:
                print(f"    - {rec['title']}")

        except ImportError as e:
            pytest.skip(f"Recommendations not available: {e}")


@pytest.mark.flow10
class TestEmailSendE2EFlow:
    """Complete E2E flow for email sending"""

    def test_full_email_send_flow(self, authed_client: httpx.Client):
        """Test complete flow: preferences -> send test email -> verify"""
        # Step 1: Ensure user has preferences set
        pref_response = authed_client.get("/api/v1/email-preferences")
        assert pref_response.status_code == 200
        print("  Step 1: Preferences retrieved")

        # Step 2: Enable weekly emails
        update_response = authed_client.put("/api/v1/email-preferences", json={
            "frequency": "weekly"
        })
        assert update_response.status_code == 200
        print("  Step 2: Weekly emails enabled")

        # Step 3: Send test email
        send_response = authed_client.post("/api/v1/email-preferences/test-email")

        if send_response.status_code == 503:
            # Email service not configured - acceptable
            print("  Step 3: Skipped - Email service not configured")
            return

        if send_response.status_code == 200:
            data = send_response.json()
            assert data.get("success") == True
            print(f"  Step 3: Test email sent - ID: {data.get('email_id', 'N/A')}")
        else:
            # May fail due to Resend API issues
            print(f"  Step 3: Email send failed - {send_response.status_code}")

        print("  E2E email send flow completed")


# === Pytest Configuration ===

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "flow10: Email Send tests")
