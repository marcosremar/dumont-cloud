"""
Unsubscribe API endpoint for email reports

Handles one-click unsubscribe functionality with secure token validation.
No authentication required per GDPR/CAN-SPAM compliance.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ....config.database import get_db
from ....models.email_preferences import EmailPreference
from ....services.email_composer import EmailComposer
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/unsubscribe", tags=["Unsubscribe"])


class UnsubscribeResponse(BaseModel):
    """Response schema for unsubscribe API"""
    success: bool
    message: str


# HTML template for unsubscribe confirmation page
UNSUBSCRIBE_SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unsubscribed - DumontCloud</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            padding: 48px;
            max-width: 480px;
            text-align: center;
        }
        .icon {
            width: 64px;
            height: 64px;
            background-color: #10b981;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
        }
        .icon svg {
            width: 32px;
            height: 32px;
            color: white;
        }
        h1 {
            color: #1e293b;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        p {
            color: #64748b;
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 24px;
        }
        .email {
            color: #334155;
            font-weight: 500;
        }
        .resubscribe-link {
            display: inline-block;
            color: #6366f1;
            text-decoration: none;
            font-size: 14px;
            transition: color 0.2s;
        }
        .resubscribe-link:hover {
            color: #4f46e5;
            text-decoration: underline;
        }
        .logo {
            margin-top: 32px;
            color: #94a3b8;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
        </div>
        <h1>You've been unsubscribed</h1>
        <p>
            <span class="email">{email}</span> has been removed from our email list.
            You will no longer receive weekly GPU usage reports.
        </p>
        <a href="{base_url}/settings/email-preferences" class="resubscribe-link">
            Changed your mind? Update your email preferences
        </a>
        <div class="logo">DumontCloud</div>
    </div>
</body>
</html>
"""

UNSUBSCRIBE_ERROR_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unsubscribe Error - DumontCloud</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            padding: 48px;
            max-width: 480px;
            text-align: center;
        }
        .icon {
            width: 64px;
            height: 64px;
            background-color: #ef4444;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
        }
        .icon svg {
            width: 32px;
            height: 32px;
            color: white;
        }
        h1 {
            color: #1e293b;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        p {
            color: #64748b;
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 24px;
        }
        .error-detail {
            color: #94a3b8;
            font-size: 14px;
            font-style: italic;
        }
        .settings-link {
            display: inline-block;
            background-color: #6366f1;
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            transition: background-color 0.2s;
        }
        .settings-link:hover {
            background-color: #4f46e5;
        }
        .logo {
            margin-top: 32px;
            color: #94a3b8;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </div>
        <h1>Unsubscribe Failed</h1>
        <p>
            We couldn't process your unsubscribe request.
            The link may be invalid or expired.
        </p>
        <p class="error-detail">{error_message}</p>
        <a href="{base_url}/settings/email-preferences" class="settings-link">
            Manage Email Preferences
        </a>
        <div class="logo">DumontCloud</div>
    </div>
</body>
</html>
"""

ALREADY_UNSUBSCRIBED_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Already Unsubscribed - DumontCloud</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            padding: 48px;
            max-width: 480px;
            text-align: center;
        }
        .icon {
            width: 64px;
            height: 64px;
            background-color: #3b82f6;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
        }
        .icon svg {
            width: 32px;
            height: 32px;
            color: white;
        }
        h1 {
            color: #1e293b;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        p {
            color: #64748b;
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 24px;
        }
        .email {
            color: #334155;
            font-weight: 500;
        }
        .resubscribe-link {
            display: inline-block;
            color: #6366f1;
            text-decoration: none;
            font-size: 14px;
            transition: color 0.2s;
        }
        .resubscribe-link:hover {
            color: #4f46e5;
            text-decoration: underline;
        }
        .logo {
            margin-top: 32px;
            color: #94a3b8;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
        </div>
        <h1>Already Unsubscribed</h1>
        <p>
            <span class="email">{email}</span> is already unsubscribed from our email list.
            No further action is needed.
        </p>
        <a href="{base_url}/settings/email-preferences" class="resubscribe-link">
            Want to re-subscribe? Update your email preferences
        </a>
        <div class="logo">DumontCloud</div>
    </div>
</body>
</html>
"""


def _get_base_url() -> str:
    """Get base URL from environment or default."""
    import os
    return os.getenv('BASE_URL', 'https://app.dumontcloud.com')


@router.get("", response_class=HTMLResponse)
async def unsubscribe(
    token: str = Query(..., description="Secure unsubscribe token from email"),
    db: Session = Depends(get_db),
):
    """
    One-click unsubscribe endpoint

    Validates the HMAC-signed token and updates user's email preferences
    to mark them as unsubscribed. Returns an HTML confirmation page.

    No authentication required per GDPR/CAN-SPAM compliance requirements.
    """
    base_url = _get_base_url()

    # Validate token
    composer = EmailComposer()
    user_id = composer.verify_unsubscribe_token(token)

    if not user_id:
        logger.warning(f"Invalid unsubscribe token attempted: {token[:20]}...")
        return HTMLResponse(
            content=UNSUBSCRIBE_ERROR_HTML.format(
                error_message="Invalid or expired unsubscribe link",
                base_url=base_url
            ),
            status_code=200  # Return 200 to show the error page properly
        )

    try:
        # Find user's email preferences
        preference = db.query(EmailPreference).filter(
            EmailPreference.user_id == user_id
        ).first()

        if not preference:
            logger.warning(f"Unsubscribe attempted for non-existent user: {user_id}")
            return HTMLResponse(
                content=UNSUBSCRIBE_ERROR_HTML.format(
                    error_message="User preferences not found",
                    base_url=base_url
                ),
                status_code=200
            )

        # Check if already unsubscribed (idempotent operation)
        if preference.unsubscribed:
            logger.info(f"User {user_id} already unsubscribed")
            return HTMLResponse(
                content=ALREADY_UNSUBSCRIBED_HTML.format(
                    email=preference.email,
                    base_url=base_url
                ),
                status_code=200
            )

        # Update preference to unsubscribed
        preference.unsubscribed = True
        preference.frequency = "none"
        db.commit()

        logger.info(f"User {user_id} unsubscribed successfully via email link")

        return HTMLResponse(
            content=UNSUBSCRIBE_SUCCESS_HTML.format(
                email=preference.email,
                base_url=base_url
            ),
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error processing unsubscribe for {user_id}: {e}")
        db.rollback()
        return HTMLResponse(
            content=UNSUBSCRIBE_ERROR_HTML.format(
                error_message="An unexpected error occurred. Please try again later.",
                base_url=base_url
            ),
            status_code=200
        )


@router.post("", response_model=UnsubscribeResponse)
async def unsubscribe_api(
    token: str = Query(..., description="Secure unsubscribe token from email"),
    db: Session = Depends(get_db),
):
    """
    Unsubscribe API endpoint (JSON response)

    Alternative to the HTML endpoint for programmatic access.
    Validates the HMAC-signed token and updates user's email preferences.

    No authentication required per GDPR/CAN-SPAM compliance requirements.
    """
    # Validate token
    composer = EmailComposer()
    user_id = composer.verify_unsubscribe_token(token)

    if not user_id:
        logger.warning(f"Invalid unsubscribe token in API call: {token[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired unsubscribe token"
        )

    try:
        # Find user's email preferences
        preference = db.query(EmailPreference).filter(
            EmailPreference.user_id == user_id
        ).first()

        if not preference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found"
            )

        # Check if already unsubscribed (idempotent - return success)
        if preference.unsubscribed:
            return UnsubscribeResponse(
                success=True,
                message="Already unsubscribed from email reports"
            )

        # Update preference to unsubscribed
        preference.unsubscribed = True
        preference.frequency = "none"
        db.commit()

        logger.info(f"User {user_id} unsubscribed via API")

        return UnsubscribeResponse(
            success=True,
            message="Successfully unsubscribed from email reports"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing unsubscribe API for {user_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unsubscribe: {str(e)}"
        )
