"""
Email Service for Dumont Cloud

Handles email sending for verification and trial notifications
using fastapi-mail with BackgroundTasks pattern.
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from jinja2 import Environment, FileSystemLoader

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# Template directory path
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "emails"


def get_email_config() -> ConnectionConfig:
    """Get email connection configuration from settings."""
    settings = get_settings()
    return ConnectionConfig(
        MAIL_USERNAME=settings.mail.username,
        MAIL_PASSWORD=settings.mail.password,
        MAIL_FROM=settings.mail.mail_from,
        MAIL_PORT=settings.mail.port,
        MAIL_SERVER=settings.mail.server,
        MAIL_STARTTLS=settings.mail.starttls,
        MAIL_SSL_TLS=settings.mail.ssl_tls,
        USE_CREDENTIALS=bool(settings.mail.username and settings.mail.password),
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=str(TEMPLATE_DIR),
    )


class EmailService:
    """
    Service for sending emails.

    Uses fastapi-mail for SMTP delivery and Jinja2 for templating.
    Designed to work with FastAPI BackgroundTasks for async sending.
    """

    def __init__(self):
        self.settings = get_settings()
        self._fast_mail: Optional[FastMail] = None
        self._jinja_env: Optional[Environment] = None

    @property
    def fast_mail(self) -> FastMail:
        """Lazy initialization of FastMail instance."""
        if self._fast_mail is None:
            config = get_email_config()
            self._fast_mail = FastMail(config)
        return self._fast_mail

    @property
    def jinja_env(self) -> Environment:
        """Lazy initialization of Jinja2 environment."""
        if self._jinja_env is None:
            self._jinja_env = Environment(
                loader=FileSystemLoader(str(TEMPLATE_DIR)),
                autoescape=True,
            )
        return self._jinja_env

    def _render_template(self, template_name: str, context: dict) -> str:
        """Render a Jinja2 template with the given context."""
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(
            self.settings.mail.username and
            self.settings.mail.password and
            self.settings.mail.server
        )

    async def send_verification_email(
        self,
        email: EmailStr,
        token: str,
        username: Optional[str] = None
    ) -> bool:
        """
        Send email verification link to a new user.

        Args:
            email: The recipient's email address
            token: The verification token
            username: Optional username for personalization

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning(
                f"Email service not configured. "
                f"Skipping verification email to {email}"
            )
            return False

        try:
            # Build verification URL
            frontend_url = self.settings.mail.frontend_url.rstrip("/")
            verification_url = f"{frontend_url}/verify-email?token={token}"

            # Render template
            html_content = self._render_template(
                "verification.html",
                {
                    "username": username or email.split("@")[0],
                    "verification_url": verification_url,
                    "email": email,
                    "support_email": "support@dumontcloud.com",
                }
            )

            # Create message
            message = MessageSchema(
                subject="Verify your Dumont Cloud account",
                recipients=[email],
                body=html_content,
                subtype=MessageType.html,
            )

            # Send email
            await self.fast_mail.send_message(message)
            logger.info(f"Verification email sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e}")
            return False

    async def send_trial_notification(
        self,
        email: EmailStr,
        percentage: int,
        remaining_hours: float,
        username: Optional[str] = None
    ) -> bool:
        """
        Send trial usage notification email.

        Args:
            email: The recipient's email address
            percentage: The usage percentage threshold (75, 90, or 100)
            remaining_hours: Hours of GPU time remaining
            username: Optional username for personalization

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning(
                f"Email service not configured. "
                f"Skipping trial notification to {email}"
            )
            return False

        try:
            # Determine subject and urgency based on percentage
            if percentage >= 100:
                subject = "Your Dumont Cloud trial has ended"
                urgency = "expired"
            elif percentage >= 90:
                subject = "Your Dumont Cloud trial is almost over (90% used)"
                urgency = "critical"
            else:
                subject = f"You've used {percentage}% of your Dumont Cloud trial"
                urgency = "warning"

            # Build upgrade URL
            frontend_url = self.settings.mail.frontend_url.rstrip("/")
            upgrade_url = f"{frontend_url}/upgrade"

            # Format remaining time
            if remaining_hours >= 1:
                remaining_text = f"{remaining_hours:.1f} hours"
            else:
                remaining_minutes = int(remaining_hours * 60)
                remaining_text = f"{remaining_minutes} minutes"

            # Render template
            html_content = self._render_template(
                "trial_notification.html",
                {
                    "username": username or email.split("@")[0],
                    "percentage": percentage,
                    "remaining_time": remaining_text,
                    "urgency": urgency,
                    "upgrade_url": upgrade_url,
                    "support_email": "support@dumontcloud.com",
                }
            )

            # Create message
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=html_content,
                subtype=MessageType.html,
            )

            # Send email
            await self.fast_mail.send_message(message)
            logger.info(f"Trial notification ({percentage}%) sent to {email}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to send trial notification ({percentage}%) to {email}: {e}"
            )
            return False

    async def send_welcome_email(
        self,
        email: EmailStr,
        username: Optional[str] = None
    ) -> bool:
        """
        Send welcome email after email verification.

        Args:
            email: The recipient's email address
            username: Optional username for personalization

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning(
                f"Email service not configured. "
                f"Skipping welcome email to {email}"
            )
            return False

        try:
            frontend_url = self.settings.mail.frontend_url.rstrip("/")
            dashboard_url = f"{frontend_url}/dashboard"
            docs_url = f"{frontend_url}/docs"

            # Simple welcome email (inline HTML)
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Welcome to Dumont Cloud</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: #2563eb;">Welcome to Dumont Cloud!</h1>
    </div>
    <p>Hi {username or email.split("@")[0]},</p>
    <p>Your email has been verified and your trial is now active!</p>
    <p>You now have access to:</p>
    <ul>
        <li><strong>2 hours of free GPU time</strong> - Perfect for trying out fine-tuning and inference</li>
        <li><strong>Full dashboard access</strong> - Manage instances, monitor usage, and more</li>
        <li><strong>All features</strong> - Experience Dumont Cloud without limitations</li>
    </ul>
    <div style="text-align: center; padding: 20px;">
        <a href="{dashboard_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Go to Dashboard</a>
    </div>
    <p>Need help getting started? Check out our <a href="{docs_url}">documentation</a>.</p>
    <p>Happy computing!</p>
    <p style="color: #6b7280; font-size: 14px;">The Dumont Cloud Team</p>
</body>
</html>
"""

            message = MessageSchema(
                subject="Welcome to Dumont Cloud - Your trial is active!",
                recipients=[email],
                body=html_content,
                subtype=MessageType.html,
            )

            await self.fast_mail.send_message(message)
            logger.info(f"Welcome email sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {e}")
            return False


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the EmailService singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
