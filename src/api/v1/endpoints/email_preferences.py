"""
Email Preferences API endpoints

CRUD endpoints for managing user email preferences (weekly/monthly reports).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

from ..dependencies import require_auth, get_current_user_email
from ....config.database import get_db
from ....models.email_preferences import EmailPreference
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-preferences", tags=["Email Preferences"], dependencies=[Depends(require_auth)])


# Request/Response Schemas

class EmailPreferencesResponse(BaseModel):
    """Response schema for email preferences"""
    id: int
    user_id: str
    email: str
    frequency: str
    unsubscribed: bool
    timezone: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdateEmailPreferencesRequest(BaseModel):
    """Request schema for updating email preferences"""
    frequency: Optional[Literal["weekly", "monthly", "none"]] = Field(
        None,
        description="Email frequency: weekly, monthly, or none"
    )
    timezone: Optional[str] = Field(
        None,
        description="User timezone for email delivery (e.g., 'America/New_York', 'UTC')"
    )


class CreateEmailPreferencesRequest(BaseModel):
    """Request schema for creating email preferences"""
    frequency: Literal["weekly", "monthly", "none"] = Field(
        default="weekly",
        description="Email frequency: weekly, monthly, or none"
    )
    timezone: str = Field(
        default="UTC",
        description="User timezone for email delivery"
    )


class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool
    message: str


# Endpoints

@router.get("", response_model=EmailPreferencesResponse)
async def get_email_preferences(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Get current user's email preferences

    Returns the user's email preference settings including frequency,
    unsubscribe status, and timezone configuration.
    """
    try:
        # Find existing preferences for user
        preference = db.query(EmailPreference).filter(
            EmailPreference.user_id == user_email
        ).first()

        if not preference:
            # Create default preferences if none exist
            preference = EmailPreference(
                user_id=user_email,
                email=user_email,
                frequency="weekly",
                timezone="UTC",
                unsubscribed=False,
            )
            db.add(preference)
            db.commit()
            db.refresh(preference)
            logger.info(f"Created default email preferences for user: {user_email}")

        return EmailPreferencesResponse(
            id=preference.id,
            user_id=preference.user_id,
            email=preference.email,
            frequency=preference.frequency,
            unsubscribed=preference.unsubscribed,
            timezone=preference.timezone,
            created_at=preference.created_at,
            updated_at=preference.updated_at,
        )

    except Exception as e:
        logger.error(f"Error fetching email preferences for {user_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch email preferences: {str(e)}"
        )


@router.put("", response_model=EmailPreferencesResponse)
async def update_email_preferences(
    request: UpdateEmailPreferencesRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Update user's email preferences

    Allows updating email frequency (weekly/monthly/none) and timezone settings.
    Setting frequency to 'none' effectively disables email reports.
    """
    try:
        # Find existing preferences
        preference = db.query(EmailPreference).filter(
            EmailPreference.user_id == user_email
        ).first()

        if not preference:
            # Create new preferences with provided values
            preference = EmailPreference(
                user_id=user_email,
                email=user_email,
                frequency=request.frequency or "weekly",
                timezone=request.timezone or "UTC",
                unsubscribed=False,
            )
            db.add(preference)
            logger.info(f"Created email preferences for user: {user_email}")
        else:
            # Update existing preferences
            if request.frequency is not None:
                preference.frequency = request.frequency
                # If user explicitly sets frequency to something other than 'none',
                # clear the unsubscribed flag
                if request.frequency != "none":
                    preference.unsubscribed = False

            if request.timezone is not None:
                preference.timezone = request.timezone

            logger.info(f"Updated email preferences for user: {user_email} - frequency: {request.frequency}, timezone: {request.timezone}")

        db.commit()
        db.refresh(preference)

        return EmailPreferencesResponse(
            id=preference.id,
            user_id=preference.user_id,
            email=preference.email,
            frequency=preference.frequency,
            unsubscribed=preference.unsubscribed,
            timezone=preference.timezone,
            created_at=preference.created_at,
            updated_at=preference.updated_at,
        )

    except Exception as e:
        logger.error(f"Error updating email preferences for {user_email}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update email preferences: {str(e)}"
        )


@router.post("/subscribe", response_model=SuccessResponse)
async def subscribe_to_emails(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Re-subscribe to email reports

    If user was previously unsubscribed, this reactivates their email subscription.
    Sets frequency to 'weekly' by default if it was 'none'.
    """
    try:
        preference = db.query(EmailPreference).filter(
            EmailPreference.user_id == user_email
        ).first()

        if not preference:
            # Create new preferences with weekly frequency
            preference = EmailPreference(
                user_id=user_email,
                email=user_email,
                frequency="weekly",
                timezone="UTC",
                unsubscribed=False,
            )
            db.add(preference)
            message = "Successfully subscribed to weekly email reports"
        else:
            # Reactivate subscription
            preference.unsubscribed = False
            if preference.frequency == "none":
                preference.frequency = "weekly"
            message = "Successfully re-subscribed to email reports"

        db.commit()
        logger.info(f"User {user_email} subscribed to email reports")

        return SuccessResponse(success=True, message=message)

    except Exception as e:
        logger.error(f"Error subscribing {user_email} to emails: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to subscribe: {str(e)}"
        )


@router.post("/test-email")
async def send_test_email(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Send a test email report

    Triggers sending of a test weekly report email to the authenticated user.
    Useful for previewing email content and verifying email delivery works.
    """
    try:
        from ....services.email_sender import send_weekly_report
        from ....services.email_analytics_aggregator import aggregate_user_usage
        from ....services.email_recommendations import generate_recommendations
        from ....services.email_composer import compose_weekly_report

        # Get user preferences
        preference = db.query(EmailPreference).filter(
            EmailPreference.user_id == user_email
        ).first()

        if not preference:
            # Create default preferences
            preference = EmailPreference(
                user_id=user_email,
                email=user_email,
                frequency="weekly",
                timezone="UTC",
                unsubscribed=False,
            )
            db.add(preference)
            db.commit()
            db.refresh(preference)

        # Aggregate usage data - function handles week bounds internally
        analytics_data = aggregate_user_usage(db, user_email)

        # Generate recommendations based on analytics
        recommendations = generate_recommendations(
            current_week=analytics_data.get('current_week', {}),
            previous_week=analytics_data.get('previous_week', {}),
            week_over_week=analytics_data.get('week_over_week', {}),
            gpu_breakdown=analytics_data.get('gpu_breakdown', [])
        )

        # Compose email
        email_content = compose_weekly_report(
            user_id=user_email,
            user_email=user_email,
            user_name=None,  # Could be fetched from user profile
            analytics_data=analytics_data,
            recommendations=recommendations,
        )

        # Send email with logging
        result = send_weekly_report(
            db_session=db,
            user_id=user_email,
            to=user_email,
            subject=email_content.subject,
            html=email_content.html_body,
            week_start=email_content.week_start,
            week_end=email_content.week_end,
        )

        if result.success:
            return {
                "success": True,
                "message": f"Test email sent to {user_email}",
                "email_id": result.email_id,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send test email: {result.error}",
            )

    except ImportError as e:
        # If email services are not available, provide helpful error
        logger.warning(f"Email services not available: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service not configured. Please ensure RESEND_API_KEY is set.",
        )
    except Exception as e:
        logger.error(f"Error sending test email for {user_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test email: {str(e)}"
        )
