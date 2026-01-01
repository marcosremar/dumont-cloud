"""
Email sender service for Resend API integration.

Provides email sending capabilities with:
- Resend API integration
- Exponential backoff retry logic (3 attempts)
- Delivery logging to EmailDeliveryLog model
- Error handling and rate limit management
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import resend

from src.models.email_delivery_log import EmailDeliveryLog

logger = logging.getLogger(__name__)

# Maximum retry attempts for failed sends
MAX_RETRIES = 3

# Base delay for exponential backoff (in seconds)
BASE_RETRY_DELAY = 1.0

# Rate limit delay between sends (in seconds)
RATE_LIMIT_DELAY = 0.1


@dataclass
class EmailResult:
    """Result of an email send attempt."""

    success: bool
    email_id: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'email_id': self.email_id,
            'error': self.error,
            'attempts': self.attempts,
        }


class EmailSender:
    """
    Email sender service using Resend API.

    Handles sending emails with retry logic, rate limiting,
    and delivery logging for tracking purposes.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_address: Optional[str] = None,
        from_name: Optional[str] = None,
    ):
        """
        Initialize the email sender.

        Args:
            api_key: Resend API key (default: from RESEND_API_KEY env var)
            from_address: Sender email address (default: from EMAIL_FROM_ADDRESS env var)
            from_name: Sender display name (default: from EMAIL_FROM_NAME env var)
        """
        self.api_key = api_key or os.getenv('RESEND_API_KEY')
        self.from_address = from_address or os.getenv('EMAIL_FROM_ADDRESS', 'reports@dumontcloud.com')
        self.from_name = from_name or os.getenv('EMAIL_FROM_NAME', 'DumontCloud')

        if not self.api_key:
            logger.warning("RESEND_API_KEY not configured. Email sending will fail.")
        else:
            # Configure resend with API key
            resend.api_key = self.api_key

    @property
    def from_email(self) -> str:
        """Get formatted from email address."""
        return f"{self.from_name} <{self.from_address}>"

    def is_configured(self) -> bool:
        """Check if the email sender is properly configured."""
        return bool(self.api_key)

    def send(
        self,
        to: str,
        subject: str,
        html: str,
        reply_to: Optional[str] = None,
    ) -> EmailResult:
        """
        Send an email via Resend API with retry logic.

        Args:
            to: Recipient email address
            subject: Email subject line
            html: HTML email body
            reply_to: Optional reply-to address

        Returns:
            EmailResult with success status and email_id or error
        """
        if not self.is_configured():
            return EmailResult(
                success=False,
                error="Email sender not configured: RESEND_API_KEY is missing"
            )

        last_error = None
        attempts = 0

        for attempt in range(1, MAX_RETRIES + 1):
            attempts = attempt
            try:
                # Build email parameters
                params = {
                    'from_': self.from_email,
                    'to': [to] if isinstance(to, str) else to,
                    'subject': subject,
                    'html': html,
                }

                if reply_to:
                    params['reply_to'] = reply_to

                # Send via Resend API
                response = resend.Emails.send(**params)

                # Extract email ID from response
                email_id = None
                if isinstance(response, dict):
                    email_id = response.get('id')
                elif hasattr(response, 'id'):
                    email_id = response.id

                logger.info(f"Email sent successfully to {to}, id={email_id}")

                return EmailResult(
                    success=True,
                    email_id=email_id,
                    attempts=attempts,
                )

            except resend.ResendError as e:
                last_error = str(e)
                logger.warning(
                    f"Resend API error on attempt {attempt}/{MAX_RETRIES}: {last_error}"
                )

                # Check if it's a rate limit error
                if 'rate' in last_error.lower() or '429' in last_error:
                    # Longer delay for rate limits
                    delay = BASE_RETRY_DELAY * (2 ** attempt) * 2
                else:
                    # Exponential backoff
                    delay = BASE_RETRY_DELAY * (2 ** (attempt - 1))

                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)

            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Unexpected error on attempt {attempt}/{MAX_RETRIES}: {last_error}"
                )

                if attempt < MAX_RETRIES:
                    delay = BASE_RETRY_DELAY * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)

        # All retries exhausted
        logger.error(f"Failed to send email to {to} after {MAX_RETRIES} attempts: {last_error}")

        return EmailResult(
            success=False,
            error=last_error,
            attempts=attempts,
        )

    def send_with_logging(
        self,
        db_session,
        user_id: str,
        to: str,
        subject: str,
        html: str,
        week_start: Optional[datetime] = None,
        week_end: Optional[datetime] = None,
        report_type: str = 'weekly',
        reply_to: Optional[str] = None,
    ) -> EmailResult:
        """
        Send an email and log the delivery to the database.

        Args:
            db_session: SQLAlchemy database session
            user_id: User identifier for logging
            to: Recipient email address
            subject: Email subject line
            html: HTML email body
            week_start: Start of reporting period (optional)
            week_end: End of reporting period (optional)
            report_type: Type of report ('weekly' or 'monthly')
            reply_to: Optional reply-to address

        Returns:
            EmailResult with success status, email_id or error
        """
        # Create delivery log entry
        delivery_log = EmailDeliveryLog(
            user_id=user_id,
            email=to,
            report_type=report_type,
            status='pending',
            week_start=week_start,
            week_end=week_end,
        )

        try:
            db_session.add(delivery_log)
            db_session.commit()
        except Exception as e:
            logger.error(f"Failed to create delivery log: {e}")
            db_session.rollback()
            # Continue without logging

        # Send the email
        result = self.send(to, subject, html, reply_to)

        # Update delivery log with result
        try:
            if result.success:
                delivery_log.mark_sent(result.email_id or '')
            else:
                delivery_log.mark_failed(result.error or 'Unknown error')

            delivery_log.retry_count = result.attempts - 1
            db_session.commit()
        except Exception as e:
            logger.error(f"Failed to update delivery log: {e}")
            db_session.rollback()

        return result


# Singleton instance for convenience
_default_sender: Optional[EmailSender] = None


def get_email_sender() -> EmailSender:
    """
    Get the default email sender singleton.

    Returns:
        EmailSender instance
    """
    global _default_sender
    if _default_sender is None:
        _default_sender = EmailSender()
    return _default_sender


def send_email(
    to: str,
    subject: str,
    html: str,
    reply_to: Optional[str] = None,
) -> EmailResult:
    """
    Convenience function to send an email using the default sender.

    Args:
        to: Recipient email address
        subject: Email subject line
        html: HTML email body
        reply_to: Optional reply-to address

    Returns:
        EmailResult with success status and email_id or error

    Example:
        >>> from src.services.email_sender import send_email
        >>> result = send_email(
        ...     to='user@example.com',
        ...     subject='Your Weekly Report',
        ...     html='<h1>Report</h1><p>Content here...</p>'
        ... )
        >>> if result.success:
        ...     print(f"Email sent! ID: {result.email_id}")
        ... else:
        ...     print(f"Failed: {result.error}")
    """
    sender = get_email_sender()
    return sender.send(to, subject, html, reply_to)


def send_weekly_report(
    db_session,
    user_id: str,
    to: str,
    subject: str,
    html: str,
    week_start: datetime,
    week_end: datetime,
) -> EmailResult:
    """
    Send a weekly report email with delivery logging.

    This is the main entry point for sending weekly report emails.
    It combines email sending with database logging for tracking.

    Args:
        db_session: SQLAlchemy database session
        user_id: User identifier for logging
        to: Recipient email address
        subject: Email subject line
        html: HTML email body
        week_start: Start of reporting period
        week_end: End of reporting period

    Returns:
        EmailResult with success status, email_id or error

    Example:
        >>> from src.services.email_sender import send_weekly_report
        >>> from src.services.email_composer import compose_weekly_report
        >>> from datetime import datetime, timedelta
        >>>
        >>> # Compose the email
        >>> email = compose_weekly_report(user_id, user_email, user_name, analytics)
        >>>
        >>> # Send with logging
        >>> result = send_weekly_report(
        ...     db_session=session,
        ...     user_id=user_id,
        ...     to=email.user_email,
        ...     subject=email.subject,
        ...     html=email.html_body,
        ...     week_start=email.week_start,
        ...     week_end=email.week_end,
        ... )
    """
    sender = get_email_sender()
    return sender.send_with_logging(
        db_session=db_session,
        user_id=user_id,
        to=to,
        subject=subject,
        html=html,
        week_start=week_start,
        week_end=week_end,
        report_type='weekly',
    )
