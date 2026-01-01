"""
Calendar Integration Service - Google Calendar Integration for Dumont Cloud

Integrates with Google Calendar API to fetch scheduled events and suggest
optimal timing adjustments based on cost forecasts.

OAuth flow following Google API patterns with secure token management.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# Google API scopes required for calendar integration
CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
]


@dataclass
class CalendarEvent:
    """Represents a Google Calendar event"""
    event_id: str
    summary: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    all_day: bool = False
    is_compute_intensive: bool = False
    suggested_start: Optional[datetime] = None
    potential_savings: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Converts to dict for API responses"""
        return {
            'event_id': self.event_id,
            'summary': self.summary,
            'start': self.start.isoformat() if self.start else None,
            'end': self.end.isoformat() if self.end else None,
            'description': self.description,
            'location': self.location,
            'all_day': self.all_day,
            'is_compute_intensive': self.is_compute_intensive,
            'suggested_start': self.suggested_start.isoformat() if self.suggested_start else None,
            'potential_savings': self.potential_savings,
            'duration_hours': self._calculate_duration_hours(),
            'metadata': self.metadata,
        }

    def _calculate_duration_hours(self) -> float:
        """Calculates event duration in hours"""
        if self.start and self.end:
            delta = self.end - self.start
            return delta.total_seconds() / 3600
        return 0.0


@dataclass
class CalendarSuggestion:
    """Represents a scheduling suggestion for an event"""
    event_id: str
    original_start: datetime
    suggested_start: datetime
    suggested_end: datetime
    potential_savings: float
    savings_percentage: float
    reason: str
    confidence: float = 0.8

    def to_dict(self) -> dict:
        """Converts to dict for API responses"""
        return {
            'event_id': self.event_id,
            'original_start': self.original_start.isoformat(),
            'suggested_start': self.suggested_start.isoformat(),
            'suggested_end': self.suggested_end.isoformat(),
            'potential_savings': round(self.potential_savings, 2),
            'savings_percentage': round(self.savings_percentage, 1),
            'reason': self.reason,
            'confidence': self.confidence,
        }


@dataclass
class OAuthCredentials:
    """Google OAuth credentials wrapper"""
    access_token: str
    refresh_token: Optional[str] = None
    token_uri: str = 'https://oauth2.googleapis.com/token'
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    expiry: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        """Checks if the access token is expired"""
        if not self.expiry:
            return False
        return datetime.utcnow() >= self.expiry

    @property
    def needs_refresh(self) -> bool:
        """Checks if token should be refreshed (5 min before expiry)"""
        if not self.expiry:
            return False
        return datetime.utcnow() >= (self.expiry - timedelta(minutes=5))


class CalendarOAuthError(Exception):
    """Raised when OAuth authentication fails"""
    def __init__(self, message: str, needs_reauthorization: bool = False):
        super().__init__(message)
        self.needs_reauthorization = needs_reauthorization


class CalendarIntegrationService:
    """
    Service for Google Calendar integration.

    Provides functionality to:
    - Fetch calendar events for a given time range
    - Identify compute-intensive scheduled tasks
    - Suggest optimal timing adjustments based on cost forecasts
    - Handle OAuth token refresh and expiry

    Uses Google Calendar API with the following scopes:
    - calendar.readonly: Read calendar events
    - calendar.events: Create/update suggestions

    Example:
        service = CalendarIntegrationService()
        events = await service.fetch_events(
            time_min=datetime.utcnow(),
            time_max=datetime.utcnow() + timedelta(days=7)
        )
    """

    # Keywords indicating compute-intensive tasks
    COMPUTE_KEYWORDS = [
        'gpu', 'training', 'inference', 'ml', 'machine learning',
        'deep learning', 'batch job', 'render', 'rendering',
        'compute', 'processing', 'analytics', 'etl', 'pipeline',
        'model training', 'fine-tuning', 'benchmark', 'simulation',
    ]

    def __init__(self, credentials: Optional[OAuthCredentials] = None):
        """
        Initializes the Calendar Integration Service.

        Args:
            credentials: OAuth credentials. If not provided, attempts to
                        load from environment variables.
        """
        self._credentials = credentials
        self._service = None
        self._google_api_available = self._check_google_api_available()

        if not self._credentials:
            self._credentials = self._load_credentials_from_env()

        if self._credentials:
            logger.info("CalendarIntegrationService initialized with credentials")
        else:
            logger.warning(
                "CalendarIntegrationService initialized without credentials - "
                "calendar features disabled"
            )

    def _check_google_api_available(self) -> bool:
        """Checks if Google API client library is available."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            return True
        except ImportError:
            logger.warning(
                "google-api-python-client not available. "
                "Install with: pip install google-api-python-client google-auth"
            )
            return False

    def _load_credentials_from_env(self) -> Optional[OAuthCredentials]:
        """Loads OAuth credentials from environment variables or token file."""
        token_path = os.getenv('GOOGLE_CALENDAR_TOKEN_JSON')
        credentials_path = os.getenv('GOOGLE_CALENDAR_CREDENTIALS_JSON')

        if not token_path:
            logger.debug("GOOGLE_CALENDAR_TOKEN_JSON not set")
            return None

        try:
            token_file = Path(token_path)
            if not token_file.exists():
                logger.warning(f"Token file not found: {token_path}")
                return None

            with open(token_file, 'r') as f:
                token_data = json.load(f)

            # Load client credentials if available
            client_id = None
            client_secret = None
            if credentials_path:
                cred_file = Path(credentials_path)
                if cred_file.exists():
                    with open(cred_file, 'r') as f:
                        cred_data = json.load(f)
                        installed = cred_data.get('installed', cred_data.get('web', {}))
                        client_id = installed.get('client_id')
                        client_secret = installed.get('client_secret')

            # Parse expiry
            expiry = None
            if 'expiry' in token_data:
                try:
                    expiry = datetime.fromisoformat(
                        token_data['expiry'].replace('Z', '+00:00')
                    )
                except (ValueError, TypeError):
                    pass

            return OAuthCredentials(
                access_token=token_data.get('token', token_data.get('access_token', '')),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=client_id or token_data.get('client_id'),
                client_secret=client_secret or token_data.get('client_secret'),
                expiry=expiry,
            )

        except Exception as e:
            logger.error(f"Failed to load credentials from {token_path}: {e}")
            return None

    def _get_google_credentials(self):
        """Converts OAuthCredentials to Google Credentials object."""
        if not self._google_api_available:
            raise CalendarOAuthError(
                "Google API client not available",
                needs_reauthorization=False
            )

        if not self._credentials:
            raise CalendarOAuthError(
                "No credentials configured. Please connect your Google Calendar.",
                needs_reauthorization=True
            )

        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=self._credentials.access_token,
            refresh_token=self._credentials.refresh_token,
            token_uri=self._credentials.token_uri,
            client_id=self._credentials.client_id,
            client_secret=self._credentials.client_secret,
            scopes=CALENDAR_SCOPES,
        )

        return creds

    def _refresh_token_if_needed(self, creds) -> bool:
        """
        Refreshes the OAuth token if expired or close to expiry.

        Returns:
            True if refresh was successful or not needed.
        """
        if not self._credentials or not self._credentials.needs_refresh:
            return True

        if not self._credentials.refresh_token:
            raise CalendarOAuthError(
                "Token expired and no refresh token available. Please reconnect your calendar.",
                needs_reauthorization=True
            )

        try:
            from google.auth.transport.requests import Request

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

                # Update stored credentials
                self._credentials.access_token = creds.token
                if hasattr(creds, 'expiry'):
                    self._credentials.expiry = creds.expiry

                # Save updated token to file
                self._save_token_to_file()

                logger.info("OAuth token refreshed successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to refresh OAuth token: {e}")
            raise CalendarOAuthError(
                f"Failed to refresh token: {str(e)}. Please reconnect your calendar.",
                needs_reauthorization=True
            )

        return True

    def _save_token_to_file(self) -> bool:
        """Saves updated token back to the token file."""
        token_path = os.getenv('GOOGLE_CALENDAR_TOKEN_JSON')
        if not token_path or not self._credentials:
            return False

        try:
            token_data = {
                'token': self._credentials.access_token,
                'refresh_token': self._credentials.refresh_token,
                'token_uri': self._credentials.token_uri,
                'client_id': self._credentials.client_id,
                'client_secret': self._credentials.client_secret,
                'scopes': CALENDAR_SCOPES,
            }

            if self._credentials.expiry:
                token_data['expiry'] = self._credentials.expiry.isoformat()

            with open(token_path, 'w') as f:
                json.dump(token_data, f)

            logger.debug(f"Token saved to {token_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save token: {e}")
            return False

    def _build_calendar_service(self):
        """Builds and returns the Google Calendar API service."""
        if self._service:
            return self._service

        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        creds = self._get_google_credentials()
        self._refresh_token_if_needed(creds)

        try:
            self._service = build('calendar', 'v3', credentials=creds)
            return self._service
        except HttpError as e:
            if e.resp.status in [401, 403]:
                raise CalendarOAuthError(
                    "Calendar access denied. Please reconnect your calendar.",
                    needs_reauthorization=True
                )
            raise

    @property
    def is_connected(self) -> bool:
        """Checks if calendar integration is properly configured."""
        return (
            self._google_api_available and
            self._credentials is not None and
            bool(self._credentials.access_token)
        )

    @property
    def needs_reauthorization(self) -> bool:
        """Checks if the user needs to reauthorize calendar access."""
        if not self._credentials:
            return True
        if not self._credentials.refresh_token and self._credentials.is_expired:
            return True
        return False

    def fetch_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        calendar_id: str = 'primary',
        max_results: int = 50,
        identify_compute_intensive: bool = True,
    ) -> List[CalendarEvent]:
        """
        Fetches calendar events for the specified time range.

        Args:
            time_min: Start of time range (default: now)
            time_max: End of time range (default: 7 days from now)
            calendar_id: Calendar ID to fetch from (default: primary)
            max_results: Maximum number of events to return
            identify_compute_intensive: Whether to analyze events for compute intensity

        Returns:
            List of CalendarEvent objects

        Raises:
            CalendarOAuthError: If authentication fails or token is expired
        """
        if not self._google_api_available:
            logger.warning("Google API not available, returning empty event list")
            return []

        if not self.is_connected:
            raise CalendarOAuthError(
                "Calendar not connected. Please connect your Google Calendar.",
                needs_reauthorization=True
            )

        # Set default time range
        if time_min is None:
            time_min = datetime.utcnow()
        if time_max is None:
            time_max = time_min + timedelta(days=7)

        try:
            service = self._build_calendar_service()

            # Format times for Google API (RFC3339)
            time_min_str = time_min.isoformat() + 'Z' if time_min.tzinfo is None else time_min.isoformat()
            time_max_str = time_max.isoformat() + 'Z' if time_max.tzinfo is None else time_max.isoformat()

            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min_str,
                timeMax=time_max_str,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
            ).execute()

            events_data = events_result.get('items', [])
            events = []

            for event_data in events_data:
                event = self._parse_event(event_data)
                if event:
                    if identify_compute_intensive:
                        event.is_compute_intensive = self._is_compute_intensive(event)
                    events.append(event)

            logger.info(f"Fetched {len(events)} calendar events")
            return events

        except CalendarOAuthError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch calendar events: {e}")
            # Check if it's an auth error
            error_str = str(e).lower()
            if 'unauthorized' in error_str or 'invalid_grant' in error_str:
                raise CalendarOAuthError(
                    "Calendar authentication failed. Please reconnect your calendar.",
                    needs_reauthorization=True
                )
            raise

    def _parse_event(self, event_data: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Parses a Google Calendar API event into a CalendarEvent object."""
        try:
            event_id = event_data.get('id', '')
            summary = event_data.get('summary', '(No title)')

            # Parse start time
            start_data = event_data.get('start', {})
            end_data = event_data.get('end', {})

            all_day = 'date' in start_data

            if all_day:
                start = datetime.strptime(start_data['date'], '%Y-%m-%d')
                end = datetime.strptime(end_data['date'], '%Y-%m-%d')
            else:
                start_str = start_data.get('dateTime', '')
                end_str = end_data.get('dateTime', '')

                # Parse ISO format with timezone
                start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))

                # Convert to UTC for internal storage
                if start.tzinfo:
                    start = start.replace(tzinfo=None) - start.utcoffset()
                if end.tzinfo:
                    end = end.replace(tzinfo=None) - end.utcoffset()

            return CalendarEvent(
                event_id=event_id,
                summary=summary,
                start=start,
                end=end,
                description=event_data.get('description'),
                location=event_data.get('location'),
                all_day=all_day,
                metadata={
                    'creator': event_data.get('creator', {}),
                    'htmlLink': event_data.get('htmlLink'),
                    'status': event_data.get('status'),
                    'attendees_count': len(event_data.get('attendees', [])),
                },
            )

        except Exception as e:
            logger.warning(f"Failed to parse event: {e}")
            return None

    def _is_compute_intensive(self, event: CalendarEvent) -> bool:
        """
        Determines if an event is likely compute-intensive based on keywords.

        Args:
            event: CalendarEvent to analyze

        Returns:
            True if the event appears to be compute-intensive
        """
        text_to_analyze = ' '.join([
            event.summary or '',
            event.description or '',
        ]).lower()

        for keyword in self.COMPUTE_KEYWORDS:
            if keyword in text_to_analyze:
                return True

        return False

    def create_suggestion(
        self,
        event: CalendarEvent,
        optimal_windows: List[Dict[str, Any]],
        current_cost: float = 0.0,
    ) -> Optional[CalendarSuggestion]:
        """
        Creates a scheduling suggestion for an event based on optimal cost windows.

        Args:
            event: The calendar event to suggest rescheduling for
            optimal_windows: List of optimal time windows from cost forecast
            current_cost: Estimated cost at current scheduled time

        Returns:
            CalendarSuggestion if a better time is available, None otherwise
        """
        if not optimal_windows:
            return None

        duration_hours = event._calculate_duration_hours()
        if duration_hours <= 0:
            return None

        # Find the best window that can accommodate the event
        for window in optimal_windows:
            window_start_str = window.get('start_time', window.get('start'))
            window_end_str = window.get('end_time', window.get('end'))
            window_cost = window.get('estimated_cost', window.get('cost', 0))
            savings = window.get('savings_amount', window.get('savings', 0))

            if not window_start_str:
                continue

            try:
                # Parse window times
                if isinstance(window_start_str, str):
                    window_start = datetime.fromisoformat(window_start_str.replace('Z', '+00:00'))
                    if window_start.tzinfo:
                        window_start = window_start.replace(tzinfo=None)
                else:
                    window_start = window_start_str

                if isinstance(window_end_str, str):
                    window_end = datetime.fromisoformat(window_end_str.replace('Z', '+00:00'))
                    if window_end.tzinfo:
                        window_end = window_end.replace(tzinfo=None)
                else:
                    window_end = window_start + timedelta(hours=duration_hours)

                # Check if window can fit the event
                window_duration = (window_end - window_start).total_seconds() / 3600
                if window_duration >= duration_hours:
                    suggested_end = window_start + timedelta(hours=duration_hours)

                    # Calculate savings
                    if current_cost > 0 and savings <= 0:
                        savings = current_cost - window_cost
                    savings_percentage = (savings / current_cost * 100) if current_cost > 0 else 0

                    # Only suggest if there are meaningful savings
                    if savings > 0:
                        return CalendarSuggestion(
                            event_id=event.event_id,
                            original_start=event.start,
                            suggested_start=window_start,
                            suggested_end=suggested_end,
                            potential_savings=savings,
                            savings_percentage=savings_percentage,
                            reason=self._generate_suggestion_reason(
                                event, window_start, savings, savings_percentage
                            ),
                            confidence=0.8 if savings_percentage > 10 else 0.6,
                        )

            except Exception as e:
                logger.warning(f"Failed to process window: {e}")
                continue

        return None

    def _generate_suggestion_reason(
        self,
        event: CalendarEvent,
        suggested_start: datetime,
        savings: float,
        savings_percentage: float,
    ) -> str:
        """Generates a human-readable reason for the suggestion."""
        time_str = suggested_start.strftime('%A at %I:%M %p')

        if savings_percentage > 30:
            return f"Moving to {time_str} could save ${savings:.2f} ({savings_percentage:.0f}% lower cost during off-peak hours)"
        elif savings_percentage > 15:
            return f"Scheduling for {time_str} offers ${savings:.2f} in savings due to lower demand"
        else:
            return f"Consider {time_str} for a modest ${savings:.2f} cost reduction"

    def get_suggestions_for_events(
        self,
        events: List[CalendarEvent],
        optimal_windows: List[Dict[str, Any]],
        hourly_prices: Optional[Dict[str, float]] = None,
    ) -> List[CalendarSuggestion]:
        """
        Generates scheduling suggestions for a list of events.

        Args:
            events: List of CalendarEvent objects
            optimal_windows: Optimal time windows from cost forecast
            hourly_prices: Optional dict of hour -> price for cost estimation

        Returns:
            List of CalendarSuggestion objects for events that can be optimized
        """
        suggestions = []

        for event in events:
            if not event.is_compute_intensive:
                continue

            # Estimate current cost based on event timing
            current_cost = 0.0
            if hourly_prices and event.start:
                hour_key = str(event.start.hour)
                hourly_rate = hourly_prices.get(hour_key, 0)
                duration = event._calculate_duration_hours()
                current_cost = hourly_rate * duration

            suggestion = self.create_suggestion(event, optimal_windows, current_cost)
            if suggestion:
                suggestions.append(suggestion)

        # Sort by potential savings (highest first)
        suggestions.sort(key=lambda s: s.potential_savings, reverse=True)

        return suggestions

    def get_oauth_authorization_url(
        self,
        redirect_uri: str,
        state: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generates an OAuth authorization URL for connecting Google Calendar.

        Args:
            redirect_uri: URI to redirect to after authorization
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL string, or None if credentials not configured
        """
        credentials_path = os.getenv('GOOGLE_CALENDAR_CREDENTIALS_JSON')
        if not credentials_path:
            logger.error("GOOGLE_CALENDAR_CREDENTIALS_JSON not configured")
            return None

        try:
            with open(credentials_path, 'r') as f:
                cred_data = json.load(f)

            installed = cred_data.get('installed', cred_data.get('web', {}))
            client_id = installed.get('client_id')
            auth_uri = installed.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth')

            if not client_id:
                logger.error("client_id not found in credentials file")
                return None

            # Build authorization URL
            from urllib.parse import urlencode

            params = {
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': ' '.join(CALENDAR_SCOPES),
                'access_type': 'offline',
                'prompt': 'consent',
            }

            if state:
                params['state'] = state

            return f"{auth_uri}?{urlencode(params)}"

        except Exception as e:
            logger.error(f"Failed to generate OAuth URL: {e}")
            return None

    def disconnect(self) -> bool:
        """
        Disconnects the calendar integration by clearing credentials.

        Returns:
            True if disconnection was successful
        """
        self._credentials = None
        self._service = None

        # Optionally remove token file
        token_path = os.getenv('GOOGLE_CALENDAR_TOKEN_JSON')
        if token_path:
            try:
                token_file = Path(token_path)
                if token_file.exists():
                    token_file.unlink()
                    logger.info(f"Removed token file: {token_path}")
            except Exception as e:
                logger.warning(f"Failed to remove token file: {e}")

        logger.info("Calendar integration disconnected")
        return True


# Singleton instance
_calendar_service: Optional[CalendarIntegrationService] = None


def get_calendar_integration_service(
    credentials: Optional[OAuthCredentials] = None,
) -> CalendarIntegrationService:
    """
    Returns singleton instance of CalendarIntegrationService.

    Args:
        credentials: Optional OAuth credentials (uses env vars if not provided)
    """
    global _calendar_service

    if _calendar_service is None:
        _calendar_service = CalendarIntegrationService(credentials=credentials)

    return _calendar_service


# Helper function for testing
def create_mock_calendar_service() -> CalendarIntegrationService:
    """Creates a calendar service instance without credentials for testing."""
    return CalendarIntegrationService(credentials=None)


if __name__ == "__main__":
    # Example usage
    import sys
    logging.basicConfig(level=logging.INFO)

    print("\nTesting CalendarIntegrationService...\n")

    service = CalendarIntegrationService()

    print(f"Connected: {service.is_connected}")
    print(f"Needs reauthorization: {service.needs_reauthorization}")
    print(f"Google API available: {service._google_api_available}")

    # Test creating a mock event
    event = CalendarEvent(
        event_id="test-123",
        summary="GPU Training Job - Model Fine-tuning",
        start=datetime.utcnow() + timedelta(hours=2),
        end=datetime.utcnow() + timedelta(hours=10),
        description="Fine-tuning BERT model on custom dataset",
    )

    print(f"\nTest event: {event.summary}")
    print(f"Is compute intensive: {service._is_compute_intensive(event)}")
    print(f"Duration: {event._calculate_duration_hours():.1f} hours")

    # Test suggestion creation
    optimal_windows = [
        {
            'start_time': (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat(),
            'end_time': (datetime.utcnow() + timedelta(days=1, hours=14)).isoformat(),
            'estimated_cost': 45.00,
            'savings_amount': 15.00,
        }
    ]

    suggestion = service.create_suggestion(event, optimal_windows, current_cost=60.00)
    if suggestion:
        print(f"\nSuggestion: {suggestion.reason}")
        print(f"Savings: ${suggestion.potential_savings:.2f}")
    else:
        print("\nNo suggestion generated")

    print("\nTest completed!")
