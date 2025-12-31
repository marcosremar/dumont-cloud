"""
Webhook management API endpoints

Provides CRUD operations for webhook configurations and a test endpoint
for verifying webhook delivery.
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, HttpUrl

from ..dependencies import require_auth, get_current_user_email
from src.config.database import SessionLocal
from src.models.webhook_config import WebhookConfig, WebhookLog
from src.services.webhook_service import get_webhook_service, VALID_EVENT_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"], dependencies=[Depends(require_auth)])


# --------------------------------------------------
# Pydantic Schemas
# --------------------------------------------------

class WebhookCreateRequest(BaseModel):
    """Request body for creating a webhook."""
    name: str = Field(..., min_length=1, max_length=200, description="Webhook name")
    url: str = Field(..., min_length=1, max_length=500, description="Webhook URL")
    events: List[str] = Field(..., min_length=1, description="Event types to subscribe to")
    secret: Optional[str] = Field(None, max_length=100, description="Optional HMAC secret for signature")
    enabled: bool = Field(True, description="Whether the webhook is enabled")


class WebhookUpdateRequest(BaseModel):
    """Request body for updating a webhook."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Webhook name")
    url: Optional[str] = Field(None, min_length=1, max_length=500, description="Webhook URL")
    events: Optional[List[str]] = Field(None, min_length=1, description="Event types to subscribe to")
    secret: Optional[str] = Field(None, max_length=100, description="Optional HMAC secret for signature")
    enabled: Optional[bool] = Field(None, description="Whether the webhook is enabled")


class WebhookResponse(BaseModel):
    """Response for a single webhook configuration."""
    id: int
    user_id: str
    name: str
    url: str
    events: List[str]
    secret: Optional[str] = None  # Redacted in responses
    enabled: bool
    created_at: str
    updated_at: str


class WebhookListResponse(BaseModel):
    """Response for listing webhooks."""
    webhooks: List[WebhookResponse]
    count: int


class WebhookLogResponse(BaseModel):
    """Response for a webhook delivery log entry."""
    id: int
    webhook_id: int
    event_type: str
    payload: dict
    status_code: Optional[int] = None
    response: Optional[str] = None
    attempt: int
    error: Optional[str] = None
    created_at: str


class WebhookLogsListResponse(BaseModel):
    """Response for listing webhook logs."""
    logs: List[WebhookLogResponse]
    count: int


class WebhookTestResponse(BaseModel):
    """Response for webhook test delivery."""
    status: str
    status_code: Optional[int] = None
    response: Optional[str] = None
    error: Optional[str] = None
    attempt: int


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: Optional[str] = None


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def _get_db():
    """Get database session."""
    return SessionLocal()


def _validate_events(events: List[str]) -> None:
    """Validate event types against whitelist."""
    # Remove 'test' from valid events for subscription (test is internal only)
    valid_subscription_events = VALID_EVENT_TYPES - {"test"}

    invalid_events = set(events) - valid_subscription_events
    if invalid_events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event types: {list(invalid_events)}. "
                   f"Valid events are: {list(valid_subscription_events)}"
        )


def _validate_url(url: str) -> None:
    """Validate webhook URL format."""
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL must start with http:// or https://"
        )


def _webhook_to_response(webhook: WebhookConfig) -> WebhookResponse:
    """Convert WebhookConfig model to response schema."""
    return WebhookResponse(
        id=webhook.id,
        user_id=webhook.user_id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events or [],
        secret="***" if webhook.secret else None,  # Redact secret
        enabled=webhook.enabled,
        created_at=webhook.created_at.isoformat() if webhook.created_at else "",
        updated_at=webhook.updated_at.isoformat() if webhook.updated_at else "",
    )


def _log_to_response(log: WebhookLog) -> WebhookLogResponse:
    """Convert WebhookLog model to response schema."""
    return WebhookLogResponse(
        id=log.id,
        webhook_id=log.webhook_id,
        event_type=log.event_type,
        payload=log.payload or {},
        status_code=log.status_code,
        response=log.response,
        attempt=log.attempt,
        error=log.error,
        created_at=log.created_at.isoformat() if log.created_at else "",
    )


# --------------------------------------------------
# API Endpoints
# --------------------------------------------------

@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: WebhookCreateRequest,
    user_email: str = Depends(get_current_user_email),
):
    """
    Create a new webhook configuration.

    Subscribe to event types:
    - instance.started: Fires when a GPU instance starts
    - instance.stopped: Fires when a GPU instance stops
    - snapshot.completed: Fires when a snapshot is completed
    - failover.triggered: Fires when failover is triggered
    - cost.threshold: Fires when cost threshold is exceeded

    The optional `secret` field enables HMAC-SHA256 signature verification.
    When set, each webhook request will include an X-Webhook-Signature header.
    """
    # Validate inputs
    _validate_events(request.events)
    _validate_url(request.url)

    db = _get_db()
    try:
        webhook = WebhookConfig(
            user_id=user_email,
            name=request.name,
            url=request.url,
            events=request.events,
            secret=request.secret,
            enabled=request.enabled,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(webhook)
        db.commit()
        db.refresh(webhook)

        logger.info(f"Created webhook {webhook.id} for user {user_email}: {webhook.name}")

        return _webhook_to_response(webhook)

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create webhook: {str(e)}"
        )
    finally:
        db.close()


@router.get("/", response_model=WebhookListResponse)
async def list_webhooks(
    enabled_only: bool = Query(False, description="Only return enabled webhooks"),
    user_email: str = Depends(get_current_user_email),
):
    """
    List all webhooks for the current user.

    Secrets are redacted in the response for security.
    """
    db = _get_db()
    try:
        query = db.query(WebhookConfig).filter(
            WebhookConfig.user_id == user_email
        )

        if enabled_only:
            query = query.filter(WebhookConfig.enabled == True)

        webhooks = query.order_by(WebhookConfig.created_at.desc()).all()

        return WebhookListResponse(
            webhooks=[_webhook_to_response(w) for w in webhooks],
            count=len(webhooks),
        )

    finally:
        db.close()


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Get a specific webhook by ID.

    Secrets are redacted in the response for security.
    """
    db = _get_db()
    try:
        webhook = db.query(WebhookConfig).filter(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == user_email,
        ).first()

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )

        return _webhook_to_response(webhook)

    finally:
        db.close()


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    request: WebhookUpdateRequest,
    user_email: str = Depends(get_current_user_email),
):
    """
    Update a webhook configuration.

    Only provided fields will be updated.
    """
    db = _get_db()
    try:
        webhook = db.query(WebhookConfig).filter(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == user_email,
        ).first()

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )

        # Validate and update fields
        if request.events is not None:
            _validate_events(request.events)
            webhook.events = request.events

        if request.url is not None:
            _validate_url(request.url)
            webhook.url = request.url

        if request.name is not None:
            webhook.name = request.name

        if request.secret is not None:
            webhook.secret = request.secret

        if request.enabled is not None:
            webhook.enabled = request.enabled

        webhook.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(webhook)

        logger.info(f"Updated webhook {webhook_id} for user {user_email}")

        return _webhook_to_response(webhook)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update webhook: {str(e)}"
        )
    finally:
        db.close()


@router.delete("/{webhook_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def delete_webhook(
    webhook_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Delete a webhook configuration.

    This will also delete all associated delivery logs.
    """
    db = _get_db()
    try:
        webhook = db.query(WebhookConfig).filter(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == user_email,
        ).first()

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )

        # Delete associated logs first
        db.query(WebhookLog).filter(
            WebhookLog.webhook_id == webhook_id
        ).delete()

        # Delete the webhook
        db.delete(webhook)
        db.commit()

        logger.info(f"Deleted webhook {webhook_id} for user {user_email}")

        return SuccessResponse(success=True, message=f"Webhook {webhook_id} deleted")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete webhook: {str(e)}"
        )
    finally:
        db.close()


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Send a test payload to a webhook.

    This endpoint sends a sample payload to verify the webhook URL
    is reachable and responding correctly. The test delivery is logged
    just like real event deliveries.

    The test payload includes:
    - event: "test"
    - data: {message, webhook_id, webhook_name}
    - timestamp: Current UTC time
    """
    db = _get_db()
    try:
        webhook = db.query(WebhookConfig).filter(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == user_email,
        ).first()

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )

        # Get webhook service and send test
        webhook_service = get_webhook_service()
        result = await webhook_service.test_webhook(webhook)

        return WebhookTestResponse(
            status=result.get("status", "unknown"),
            status_code=result.get("status_code"),
            response=result.get("response"),
            error=result.get("error"),
            attempt=result.get("attempt", 1),
        )

    finally:
        db.close()


@router.get("/{webhook_id}/logs", response_model=WebhookLogsListResponse)
async def get_webhook_logs(
    webhook_id: int,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    user_email: str = Depends(get_current_user_email),
):
    """
    Get delivery logs for a specific webhook.

    Returns the most recent delivery attempts, ordered by creation time (newest first).
    Each log entry includes the event type, payload, status code, response, and any errors.
    """
    db = _get_db()
    try:
        # Verify webhook belongs to user
        webhook = db.query(WebhookConfig).filter(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == user_email,
        ).first()

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )

        # Get logs
        logs = db.query(WebhookLog).filter(
            WebhookLog.webhook_id == webhook_id
        ).order_by(
            WebhookLog.created_at.desc()
        ).offset(offset).limit(limit).all()

        # Get total count
        total_count = db.query(WebhookLog).filter(
            WebhookLog.webhook_id == webhook_id
        ).count()

        return WebhookLogsListResponse(
            logs=[_log_to_response(log) for log in logs],
            count=total_count,
        )

    finally:
        db.close()


@router.get("/events/types", response_model=dict)
async def get_event_types(
    user_email: str = Depends(get_current_user_email),
):
    """
    Get list of available event types.

    Returns all event types that can be subscribed to, along with descriptions.
    """
    event_descriptions = {
        "instance.started": "Fires when a GPU instance starts successfully",
        "instance.stopped": "Fires when a GPU instance is stopped or destroyed",
        "snapshot.completed": "Fires when a snapshot operation completes",
        "failover.triggered": "Fires when automatic failover is triggered",
        "cost.threshold": "Fires when cost threshold is exceeded",
    }

    return {
        "events": list(event_descriptions.keys()),
        "descriptions": event_descriptions,
    }
