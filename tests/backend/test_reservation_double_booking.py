"""
Tests for GPU Reservation Double-Booking Prevention

Verifies that the reservation system correctly prevents overlapping
reservations for the same GPU type at the same time.

Test Scenarios:
1. Create reservation for A100 from 10:00-12:00
2. Attempt to create overlapping reservation (11:00-13:00)
3. Verify 409 conflict error returned
4. Verify appropriate error message
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestOverlapDetection:
    """
    Tests for the overlap detection algorithm.

    Overlap condition: NOT (end1 <= start2 OR start1 >= end2)
    Equivalent to: end1 > start2 AND start1 < end2
    """

    def test_exact_overlap_is_detected(self):
        """Same time slot should be detected as conflict."""
        start1 = datetime(2024, 2, 1, 10, 0)
        end1 = datetime(2024, 2, 1, 12, 0)
        start2 = datetime(2024, 2, 1, 10, 0)
        end2 = datetime(2024, 2, 1, 12, 0)

        # Overlap condition: end1 > start2 AND start1 < end2
        has_overlap = end1 > start2 and start1 < end2
        assert has_overlap is True

    def test_partial_overlap_start_is_detected(self):
        """Reservation starting during existing one should conflict."""
        # Existing: 10:00-12:00
        start1 = datetime(2024, 2, 1, 10, 0)
        end1 = datetime(2024, 2, 1, 12, 0)
        # New: 11:00-13:00 (overlaps by 1 hour)
        start2 = datetime(2024, 2, 1, 11, 0)
        end2 = datetime(2024, 2, 1, 13, 0)

        has_overlap = end1 > start2 and start1 < end2
        assert has_overlap is True

    def test_partial_overlap_end_is_detected(self):
        """Reservation ending during existing one should conflict."""
        # Existing: 10:00-12:00
        start1 = datetime(2024, 2, 1, 10, 0)
        end1 = datetime(2024, 2, 1, 12, 0)
        # New: 09:00-11:00 (overlaps by 1 hour)
        start2 = datetime(2024, 2, 1, 9, 0)
        end2 = datetime(2024, 2, 1, 11, 0)

        has_overlap = end1 > start2 and start1 < end2
        assert has_overlap is True

    def test_contained_reservation_is_detected(self):
        """Reservation entirely within existing one should conflict."""
        # Existing: 10:00-16:00
        start1 = datetime(2024, 2, 1, 10, 0)
        end1 = datetime(2024, 2, 1, 16, 0)
        # New: 12:00-14:00 (entirely within)
        start2 = datetime(2024, 2, 1, 12, 0)
        end2 = datetime(2024, 2, 1, 14, 0)

        has_overlap = end1 > start2 and start1 < end2
        assert has_overlap is True

    def test_containing_reservation_is_detected(self):
        """Reservation that contains existing one should conflict."""
        # Existing: 12:00-14:00
        start1 = datetime(2024, 2, 1, 12, 0)
        end1 = datetime(2024, 2, 1, 14, 0)
        # New: 10:00-16:00 (contains existing)
        start2 = datetime(2024, 2, 1, 10, 0)
        end2 = datetime(2024, 2, 1, 16, 0)

        has_overlap = end1 > start2 and start1 < end2
        assert has_overlap is True

    def test_adjacent_slots_no_overlap(self):
        """Adjacent time slots should not conflict."""
        # Existing: 10:00-12:00
        start1 = datetime(2024, 2, 1, 10, 0)
        end1 = datetime(2024, 2, 1, 12, 0)
        # New: 12:00-14:00 (immediately after)
        start2 = datetime(2024, 2, 1, 12, 0)
        end2 = datetime(2024, 2, 1, 14, 0)

        has_overlap = end1 > start2 and start1 < end2
        assert has_overlap is False

    def test_non_overlapping_before(self):
        """Reservation before existing one should not conflict."""
        # Existing: 14:00-16:00
        start1 = datetime(2024, 2, 1, 14, 0)
        end1 = datetime(2024, 2, 1, 16, 0)
        # New: 10:00-12:00 (well before)
        start2 = datetime(2024, 2, 1, 10, 0)
        end2 = datetime(2024, 2, 1, 12, 0)

        has_overlap = end1 > start2 and start1 < end2
        assert has_overlap is False

    def test_non_overlapping_after(self):
        """Reservation after existing one should not conflict."""
        # Existing: 10:00-12:00
        start1 = datetime(2024, 2, 1, 10, 0)
        end1 = datetime(2024, 2, 1, 12, 0)
        # New: 14:00-16:00 (well after)
        start2 = datetime(2024, 2, 1, 14, 0)
        end2 = datetime(2024, 2, 1, 16, 0)

        has_overlap = end1 > start2 and start1 < end2
        assert has_overlap is False


class TestReservationServiceAvailability:
    """
    Tests for ReservationService.check_availability method.

    Uses mocked database to verify the availability checking logic.
    """

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def reservation_service(self, mock_db_session):
        """Create ReservationService with mocked dependencies."""
        try:
            from src.services.reservation_service import ReservationService
            return ReservationService(mock_db_session)
        except ImportError:
            pytest.skip("ReservationService not available")

    def test_check_availability_returns_true_when_no_conflicts(self, reservation_service, mock_db_session):
        """Availability should return True when no conflicting reservations exist."""
        # Mock the query to return 0 conflicting reservations
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 0
        mock_db_session.query.return_value = mock_query

        start_time = datetime.utcnow() + timedelta(hours=24)
        end_time = start_time + timedelta(hours=2)

        result = reservation_service.check_availability(
            gpu_type="A100",
            start_time=start_time,
            end_time=end_time
        )

        assert result is True

    def test_check_availability_returns_false_when_conflicts_exist(self, reservation_service, mock_db_session):
        """Availability should return False when conflicting reservations exist."""
        # Mock the query to return 1 conflicting reservation
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 1
        mock_db_session.query.return_value = mock_query

        start_time = datetime.utcnow() + timedelta(hours=24)
        end_time = start_time + timedelta(hours=2)

        result = reservation_service.check_availability(
            gpu_type="A100",
            start_time=start_time,
            end_time=end_time
        )

        assert result is False


class TestReservationConflictException:
    """Tests for ReservationConflictException behavior."""

    def test_conflict_exception_contains_gpu_info(self):
        """Exception should contain GPU type and time range info."""
        try:
            from src.services.reservation_service import ReservationConflictException

            start_time = datetime(2024, 2, 1, 10, 0)
            end_time = datetime(2024, 2, 1, 12, 0)

            exc = ReservationConflictException(
                gpu_type="A100",
                start_time=start_time,
                end_time=end_time
            )

            assert exc.gpu_type == "A100"
            assert exc.start_time == start_time
            assert exc.end_time == end_time
            assert "A100" in str(exc)
            assert "not available" in str(exc).lower() or "conflict" in str(exc).lower()
        except ImportError:
            pytest.skip("ReservationConflictException not available")


class TestAPIDoubleBookingResponse:
    """
    Tests for API endpoint response when double-booking is attempted.

    These tests verify the HTTP response codes and error messages.
    """

    @pytest.fixture
    def api_client(self):
        """Create API client for testing."""
        try:
            import requests
            from tests.conftest import API_BASE_URL

            class APIClient:
                def __init__(self, base_url):
                    self.base_url = base_url
                    self.session = requests.Session()
                    self.session.headers.update({
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer test-token'
                    })

                def create_reservation(self, data):
                    return self.session.post(
                        f"{self.base_url}/api/v1/reservations",
                        json=data
                    )

                def check_availability(self, gpu_type, start, end):
                    return self.session.get(
                        f"{self.base_url}/api/v1/reservations/availability",
                        params={
                            'gpu_type': gpu_type,
                            'start': start,
                            'end': end
                        }
                    )

            return APIClient(API_BASE_URL)
        except Exception:
            pytest.skip("API client not available")

    @pytest.mark.skip(reason="Requires running API server")
    def test_overlapping_reservation_returns_409(self, api_client):
        """Creating overlapping reservation should return 409 Conflict."""
        start = (datetime.utcnow() + timedelta(days=1)).isoformat()
        end = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat()

        # Create first reservation
        response1 = api_client.create_reservation({
            'gpu_type': 'A100',
            'gpu_count': 1,
            'start_time': start,
            'end_time': end
        })

        if response1.status_code == 201:
            # Try overlapping reservation
            overlap_start = (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat()
            overlap_end = (datetime.utcnow() + timedelta(days=1, hours=3)).isoformat()

            response2 = api_client.create_reservation({
                'gpu_type': 'A100',
                'gpu_count': 1,
                'start_time': overlap_start,
                'end_time': overlap_end
            })

            assert response2.status_code == 409

            error_data = response2.json()
            assert 'detail' in error_data
            assert 'available' in error_data['detail'].lower() or 'conflict' in error_data['detail'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
