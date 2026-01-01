"""
Email composer service for weekly GPU reports.

Renders HTML email templates with user-specific data including:
- Weekly usage metrics
- Week-over-week comparisons
- GPU breakdown
- AI recommendations
- Unsubscribe links with secure tokens
"""

import os
import hmac
import hashlib
import base64
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)


@dataclass
class EmailContent:
    """Represents composed email content ready for sending."""

    subject: str
    html_body: str
    user_id: str
    user_email: str
    week_start: datetime
    week_end: datetime
    has_usage: bool
    is_first_week: bool

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'subject': self.subject,
            'html_body': self.html_body,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'week_start': self.week_start.isoformat(),
            'week_end': self.week_end.isoformat(),
            'has_usage': self.has_usage,
            'is_first_week': self.is_first_week,
        }


class EmailComposer:
    """
    Composes weekly GPU report emails using Jinja2 templates.

    Integrates:
    - Analytics aggregator for usage metrics
    - Recommendation generator for optimization tips
    - HMAC-signed unsubscribe tokens for security
    """

    # Template directory relative to this file
    TEMPLATE_DIR = Path(__file__).parent.parent / 'templates' / 'email'

    def __init__(
        self,
        base_url: Optional[str] = None,
        unsubscribe_secret_key: Optional[str] = None,
    ):
        """
        Initialize the email composer.

        Args:
            base_url: Base URL for links in email (default: from env or localhost)
            unsubscribe_secret_key: Secret key for HMAC token generation
        """
        self.base_url = base_url or os.getenv('BASE_URL', 'https://app.dumontcloud.com')
        self.unsubscribe_secret_key = unsubscribe_secret_key or os.getenv(
            'UNSUBSCRIBE_SECRET_KEY',
            'default-secret-key-change-in-production'
        )

        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.TEMPLATE_DIR)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom filters
        self.jinja_env.filters['abs'] = abs

    def generate_unsubscribe_token(self, user_id: str) -> str:
        """
        Generate a secure HMAC-signed token for unsubscribe links.

        The token includes the user_id and a timestamp for expiration checking.

        Args:
            user_id: The user's unique identifier

        Returns:
            Base64-encoded signed token
        """
        # Include timestamp for potential expiration (optional future enhancement)
        timestamp = int(datetime.utcnow().timestamp())
        payload = f"{user_id}:{timestamp}"

        # Create HMAC signature
        signature = hmac.new(
            self.unsubscribe_secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).digest()

        # Combine payload and signature, encode as base64
        token_data = f"{payload}:{base64.b64encode(signature).decode('utf-8')}"
        return base64.urlsafe_b64encode(token_data.encode('utf-8')).decode('utf-8')

    def verify_unsubscribe_token(self, token: str) -> Optional[str]:
        """
        Verify an unsubscribe token and extract the user_id.

        Args:
            token: The base64-encoded signed token

        Returns:
            The user_id if valid, None if invalid or tampered
        """
        try:
            # Decode the token
            token_data = base64.urlsafe_b64decode(token.encode('utf-8')).decode('utf-8')
            parts = token_data.split(':')

            if len(parts) != 3:
                return None

            user_id, timestamp_str, encoded_signature = parts

            # Reconstruct the payload
            payload = f"{user_id}:{timestamp_str}"

            # Verify the signature
            expected_signature = hmac.new(
                self.unsubscribe_secret_key.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).digest()

            provided_signature = base64.b64decode(encoded_signature.encode('utf-8'))

            if hmac.compare_digest(expected_signature, provided_signature):
                return user_id

            return None
        except Exception as e:
            logger.warning(f"Failed to verify unsubscribe token: {e}")
            return None

    def generate_subject(
        self,
        week_end: datetime,
        has_usage: bool,
        is_first_week: bool
    ) -> str:
        """
        Generate the email subject line.

        Args:
            week_end: End date of the reporting week
            has_usage: Whether the user had GPU usage
            is_first_week: Whether this is the user's first week

        Returns:
            Formatted subject line
        """
        week_ending = week_end.strftime('%B %d')

        if is_first_week:
            return f"Welcome! Your First Weekly GPU Report - Week of {week_ending}"
        elif not has_usage:
            return f"We Missed You This Week - DumontCloud Report ({week_ending})"
        else:
            return f"Your Weekly GPU Report - Week Ending {week_ending}"

    def compose(
        self,
        user_id: str,
        user_email: str,
        user_name: Optional[str],
        current_week: Dict,
        week_over_week: Dict,
        gpu_breakdown: list,
        recommendations: list,
    ) -> EmailContent:
        """
        Compose a complete weekly report email.

        Args:
            user_id: User's unique identifier
            user_email: User's email address
            user_name: User's display name (optional)
            current_week: Current week metrics from analytics aggregator
            week_over_week: Week-over-week comparison data
            gpu_breakdown: List of GPU usage breakdowns
            recommendations: List of AI recommendations

        Returns:
            EmailContent with subject and rendered HTML body
        """
        # Parse dates from the current_week data
        week_start = datetime.fromisoformat(current_week['week_start'])
        week_end = datetime.fromisoformat(current_week['week_end'])
        has_usage = current_week.get('has_usage', False)
        is_first_week = current_week.get('is_first_week', False)

        # Generate secure unsubscribe token
        unsubscribe_token = self.generate_unsubscribe_token(user_id)
        unsubscribe_url = f"{self.base_url}/api/v1/unsubscribe?token={unsubscribe_token}"

        # Generate view in browser URL (could be a web-hosted version)
        view_in_browser_url = f"{self.base_url}/reports/weekly?token={unsubscribe_token}"

        # Prepare template context
        context = {
            # User info
            'user_id': user_id,
            'user_name': user_name,

            # Week data
            'current_week': current_week,
            'week_over_week': week_over_week,
            'gpu_breakdown': gpu_breakdown,
            'recommendations': recommendations,

            # URLs
            'base_url': self.base_url,
            'unsubscribe_url': unsubscribe_url,
            'view_in_browser_url': view_in_browser_url,

            # Meta
            'current_year': datetime.utcnow().year,
        }

        # Load and render template
        try:
            template = self.jinja_env.get_template('weekly_report.html')
            html_body = template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render email template: {e}")
            raise

        # Generate subject line
        subject = self.generate_subject(week_end, has_usage, is_first_week)

        return EmailContent(
            subject=subject,
            html_body=html_body,
            user_id=user_id,
            user_email=user_email,
            week_start=week_start,
            week_end=week_end,
            has_usage=has_usage,
            is_first_week=is_first_week,
        )


def compose_weekly_report(
    user_id: str,
    user_email: str,
    user_name: Optional[str],
    analytics_data: Dict,
    recommendations: Optional[list] = None,
    base_url: Optional[str] = None,
) -> EmailContent:
    """
    Convenience function to compose a weekly report email.

    This is the main entry point for the email composition service.
    It integrates analytics data and recommendations into a complete email.

    Args:
        user_id: User's unique identifier
        user_email: User's email address
        user_name: User's display name (optional)
        analytics_data: Output from aggregate_user_usage() containing:
            - current_week: Dict with weekly metrics
            - week_over_week: Dict with comparison data
            - gpu_breakdown: List of GPU breakdowns
        recommendations: List of recommendation dicts (optional)
        base_url: Base URL for links (optional, uses env default)

    Returns:
        EmailContent object with subject and HTML body

    Example:
        >>> from src.services.email_analytics_aggregator import aggregate_user_usage
        >>> from src.services.email_recommendations import generate_recommendations
        >>>
        >>> analytics = aggregate_user_usage(db, user_id)
        >>> recs = generate_recommendations(
        ...     analytics['current_week'],
        ...     analytics['previous_week'],
        ...     analytics['week_over_week'],
        ...     analytics['gpu_breakdown']
        ... )
        >>>
        >>> email = compose_weekly_report(
        ...     user_id='user-123',
        ...     user_email='user@example.com',
        ...     user_name='John',
        ...     analytics_data=analytics,
        ...     recommendations=recs
        ... )
        >>>
        >>> # Send the email
        >>> send_email(email.user_email, email.subject, email.html_body)
    """
    composer = EmailComposer(base_url=base_url)

    # Extract data from analytics
    current_week = analytics_data.get('current_week', {})
    week_over_week = analytics_data.get('week_over_week', {})
    gpu_breakdown = analytics_data.get('gpu_breakdown', [])

    # Use provided recommendations or empty list
    if recommendations is None:
        recommendations = []

    return composer.compose(
        user_id=user_id,
        user_email=user_email,
        user_name=user_name,
        current_week=current_week,
        week_over_week=week_over_week,
        gpu_breakdown=gpu_breakdown,
        recommendations=recommendations,
    )


# Singleton instance for convenience
_default_composer: Optional[EmailComposer] = None


def get_email_composer() -> EmailComposer:
    """
    Get the default email composer singleton.

    Returns:
        EmailComposer instance
    """
    global _default_composer
    if _default_composer is None:
        _default_composer = EmailComposer()
    return _default_composer
