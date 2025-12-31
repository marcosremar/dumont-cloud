"""
WebhookService - Async Webhook Delivery with Retry Logic

This service handles webhook delivery with:
1. Async HTTP delivery using httpx
2. Retry logic with exponential backoff (3 attempts)
3. HMAC-SHA256 signature generation
4. Delivery logging to database
5. Fire-and-forget pattern for non-blocking delivery
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState,
)

from src.config.database import SessionLocal
from src.models.webhook_config import WebhookConfig, WebhookLog
from src.core.security.hmac_signature import generate_signature

logger = logging.getLogger(__name__)

# Webhook delivery configuration
WEBHOOK_TIMEOUT_SECONDS = 10
WEBHOOK_MAX_ATTEMPTS = 3
WEBHOOK_RETRY_MIN_SECONDS = 2
WEBHOOK_RETRY_MAX_SECONDS = 30
WEBHOOK_RETRY_MULTIPLIER = 2

# Maximum response body size to store in logs (prevent abuse)
MAX_RESPONSE_SIZE = 1000

# Valid event types
VALID_EVENT_TYPES = {
    "instance.started",
    "instance.stopped",
    "snapshot.completed",
    "failover.triggered",
    "cost.threshold",
    "test",
}


class WebhookDeliveryError(Exception):
    """Exception raised when webhook delivery fails after all retries."""
    pass


class WebhookService:
    """
    Async webhook delivery service with retry logic.

    Key features:
    - httpx AsyncClient with 10-second timeout
    - Tenacity retry decorator (3 attempts, exponential backoff)
    - HMAC-SHA256 signature in X-Webhook-Signature header
    - Fire-and-forget with asyncio.create_task()
    - All delivery attempts logged to WebhookLog table
    """

    def __init__(self):
        """Initialize the webhook service."""
        self._pending_tasks: Dict[str, asyncio.Task] = {}

    def _get_db_session(self):
        """Get a database session."""
        return SessionLocal()

    def get_active_webhooks_for_event(
        self,
        event_type: str,
        user_id: Optional[str] = None
    ) -> List[WebhookConfig]:
        """
        Get all active webhooks subscribed to an event type.

        Args:
            event_type: The event type to filter by
            user_id: Optional user ID to filter by

        Returns:
            List of active WebhookConfig objects subscribed to the event
        """
        db = self._get_db_session()
        try:
            query = db.query(WebhookConfig).filter(
                WebhookConfig.enabled == True
            )

            if user_id:
                query = query.filter(WebhookConfig.user_id == user_id)

            webhooks = query.all()

            # Filter by event type (events is a JSON array)
            return [
                webhook for webhook in webhooks
                if event_type in (webhook.events or [])
            ]
        finally:
            db.close()

    def get_webhook_by_id(
        self,
        webhook_id: int,
        user_id: Optional[str] = None
    ) -> Optional[WebhookConfig]:
        """
        Get a webhook by ID.

        Args:
            webhook_id: The webhook ID
            user_id: Optional user ID to verify ownership

        Returns:
            WebhookConfig if found, None otherwise
        """
        db = self._get_db_session()
        try:
            query = db.query(WebhookConfig).filter(
                WebhookConfig.id == webhook_id
            )

            if user_id:
                query = query.filter(WebhookConfig.user_id == user_id)

            return query.first()
        finally:
            db.close()

    def _log_delivery_attempt(
        self,
        webhook_id: int,
        event_type: str,
        payload: Dict[str, Any],
        status_code: Optional[int],
        response: Optional[str],
        attempt: int,
        error: Optional[str] = None
    ) -> WebhookLog:
        """
        Log a webhook delivery attempt to the database.

        Args:
            webhook_id: The webhook configuration ID
            event_type: The event type being delivered
            payload: The webhook payload
            status_code: HTTP status code (if received)
            response: Response body (truncated if too large)
            attempt: Attempt number (1, 2, or 3)
            error: Error message if delivery failed

        Returns:
            The created WebhookLog record
        """
        db = self._get_db_session()
        try:
            # Truncate response if too large
            truncated_response = None
            if response:
                truncated_response = response[:MAX_RESPONSE_SIZE]
                if len(response) > MAX_RESPONSE_SIZE:
                    truncated_response += "... (truncated)"

            log = WebhookLog(
                webhook_id=webhook_id,
                event_type=event_type,
                payload=payload,
                status_code=status_code,
                response=truncated_response,
                attempt=attempt,
                error=error,
                created_at=datetime.utcnow(),
            )

            db.add(log)
            db.commit()
            db.refresh(log)

            return log
        except Exception as e:
            logger.error(f"Failed to log webhook delivery: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    async def _send_webhook_request(
        self,
        url: str,
        payload: Dict[str, Any],
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a single webhook HTTP request.

        Args:
            url: The webhook URL
            payload: The payload to send
            secret: Optional secret for HMAC signature

        Returns:
            Dict with status_code and response text

        Raises:
            httpx.HTTPStatusError: If response has 4xx/5xx status
            httpx.TimeoutException: If request times out
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "DumontCloud-Webhook/1.0",
        }

        # Add HMAC signature if secret is provided
        if secret:
            signature = generate_signature(payload, secret)
            headers["X-Webhook-Signature"] = signature

        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()  # Raises HTTPStatusError on 4xx/5xx

            return {
                "status_code": response.status_code,
                "response": response.text,
            }

    async def send_webhook(
        self,
        webhook: WebhookConfig,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a webhook with retry logic.

        This method will retry up to 3 times with exponential backoff
        (2s, 4s, 8s...) on connection errors, timeouts, and 5xx errors.

        Args:
            webhook: The webhook configuration
            event_type: The event type being delivered
            payload: The webhook payload

        Returns:
            Dict with status, status_code, response, and attempt count
        """
        attempt = 0
        last_error = None
        last_status_code = None
        last_response = None

        # Retry loop with exponential backoff
        for attempt in range(1, WEBHOOK_MAX_ATTEMPTS + 1):
            try:
                logger.info(
                    f"[webhook:{webhook.id}] Attempt {attempt}/{WEBHOOK_MAX_ATTEMPTS} "
                    f"to {webhook.url} for event {event_type}"
                )

                result = await self._send_webhook_request(
                    url=webhook.url,
                    payload=payload,
                    secret=webhook.secret
                )

                # Success - log and return
                self._log_delivery_attempt(
                    webhook_id=webhook.id,
                    event_type=event_type,
                    payload=payload,
                    status_code=result["status_code"],
                    response=result["response"],
                    attempt=attempt,
                    error=None
                )

                logger.info(
                    f"[webhook:{webhook.id}] Delivered successfully "
                    f"(status={result['status_code']}, attempt={attempt})"
                )

                return {
                    "status": "delivered",
                    "status_code": result["status_code"],
                    "response": result["response"],
                    "attempt": attempt,
                }

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                last_status_code = e.response.status_code
                last_response = e.response.text

                # Log this attempt
                self._log_delivery_attempt(
                    webhook_id=webhook.id,
                    event_type=event_type,
                    payload=payload,
                    status_code=last_status_code,
                    response=last_response,
                    attempt=attempt,
                    error=last_error
                )

                logger.warning(
                    f"[webhook:{webhook.id}] Attempt {attempt} failed: {last_error}"
                )

            except httpx.TimeoutException as e:
                last_error = f"Request timed out after {WEBHOOK_TIMEOUT_SECONDS}s"
                last_status_code = None
                last_response = None

                # Log this attempt
                self._log_delivery_attempt(
                    webhook_id=webhook.id,
                    event_type=event_type,
                    payload=payload,
                    status_code=None,
                    response=None,
                    attempt=attempt,
                    error=last_error
                )

                logger.warning(
                    f"[webhook:{webhook.id}] Attempt {attempt} timed out"
                )

            except httpx.RequestError as e:
                last_error = f"Connection error: {str(e)}"
                last_status_code = None
                last_response = None

                # Log this attempt
                self._log_delivery_attempt(
                    webhook_id=webhook.id,
                    event_type=event_type,
                    payload=payload,
                    status_code=None,
                    response=None,
                    attempt=attempt,
                    error=last_error
                )

                logger.warning(
                    f"[webhook:{webhook.id}] Attempt {attempt} connection error: {e}"
                )

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                last_status_code = None
                last_response = None

                # Log this attempt
                self._log_delivery_attempt(
                    webhook_id=webhook.id,
                    event_type=event_type,
                    payload=payload,
                    status_code=None,
                    response=None,
                    attempt=attempt,
                    error=last_error
                )

                logger.error(
                    f"[webhook:{webhook.id}] Attempt {attempt} unexpected error: {e}"
                )

            # If not the last attempt, wait before retrying
            if attempt < WEBHOOK_MAX_ATTEMPTS:
                wait_time = min(
                    WEBHOOK_RETRY_MIN_SECONDS * (WEBHOOK_RETRY_MULTIPLIER ** (attempt - 1)),
                    WEBHOOK_RETRY_MAX_SECONDS
                )
                logger.info(
                    f"[webhook:{webhook.id}] Waiting {wait_time}s before retry..."
                )
                await asyncio.sleep(wait_time)

        # All attempts failed
        logger.error(
            f"[webhook:{webhook.id}] All {WEBHOOK_MAX_ATTEMPTS} attempts failed. "
            f"Last error: {last_error}"
        )

        return {
            "status": "failed",
            "status_code": last_status_code,
            "response": last_response,
            "error": last_error,
            "attempt": WEBHOOK_MAX_ATTEMPTS,
        }

    async def _deliver_webhook_with_logging(
        self,
        webhook: WebhookConfig,
        event_type: str,
        payload: Dict[str, Any]
    ):
        """
        Deliver webhook with error handling for fire-and-forget pattern.

        This method wraps send_webhook to catch all exceptions,
        ensuring that webhook errors never propagate to the main application.
        """
        try:
            # Check if webhook is still enabled before delivery
            db = self._get_db_session()
            try:
                current_webhook = db.query(WebhookConfig).filter(
                    WebhookConfig.id == webhook.id,
                    WebhookConfig.enabled == True
                ).first()

                if not current_webhook:
                    logger.info(
                        f"[webhook:{webhook.id}] Skipping delivery - "
                        "webhook disabled or deleted"
                    )
                    return
            finally:
                db.close()

            await self.send_webhook(webhook, event_type, payload)

        except Exception as e:
            # Never let webhook errors propagate
            logger.error(
                f"[webhook:{webhook.id}] Delivery error (suppressed): {e}"
            )

    async def trigger_webhooks(
        self,
        event_type: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """
        Trigger webhooks for an event (fire-and-forget).

        This method finds all active webhooks subscribed to the event type
        and delivers them in parallel without blocking. Errors are logged
        but never propagated.

        Args:
            event_type: The event type (e.g., 'instance.started')
            data: The event data to include in the payload
            user_id: Optional user ID to filter webhooks
        """
        if event_type not in VALID_EVENT_TYPES:
            logger.warning(f"Invalid event type: {event_type}")
            return

        # Build the standard webhook payload
        payload = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Find all active webhooks for this event
        webhooks = self.get_active_webhooks_for_event(event_type, user_id)

        if not webhooks:
            logger.debug(f"No webhooks subscribed to event: {event_type}")
            return

        logger.info(
            f"Triggering {len(webhooks)} webhook(s) for event: {event_type}"
        )

        # Fire-and-forget: create tasks without awaiting
        for webhook in webhooks:
            task = asyncio.create_task(
                self._deliver_webhook_with_logging(webhook, event_type, payload)
            )
            # Store task reference to prevent garbage collection
            task_id = f"{webhook.id}_{event_type}_{datetime.utcnow().timestamp()}"
            self._pending_tasks[task_id] = task

            # Clean up completed tasks
            task.add_done_callback(
                lambda t, tid=task_id: self._pending_tasks.pop(tid, None)
            )

    async def test_webhook(
        self,
        webhook: WebhookConfig
    ) -> Dict[str, Any]:
        """
        Send a test payload to a webhook.

        Unlike trigger_webhooks, this method awaits the result and returns
        the delivery status.

        Args:
            webhook: The webhook configuration to test

        Returns:
            Dict with delivery status, status_code, response, and attempt count
        """
        test_payload = {
            "event": "test",
            "data": {
                "message": "This is a test webhook from Dumont Cloud",
                "webhook_id": webhook.id,
                "webhook_name": webhook.name,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        logger.info(f"[webhook:{webhook.id}] Sending test webhook to {webhook.url}")

        return await self.send_webhook(webhook, "test", test_payload)


# Singleton instance
_webhook_service: Optional[WebhookService] = None


def get_webhook_service() -> WebhookService:
    """Get or create WebhookService singleton."""
    global _webhook_service

    if _webhook_service is None:
        _webhook_service = WebhookService()

    return _webhook_service


async def trigger_webhooks(
    event_type: str,
    data: Dict[str, Any],
    user_id: Optional[str] = None
):
    """
    Convenience function to trigger webhooks.

    This is the main entry point for event triggers throughout the codebase.
    Use this function to fire webhooks from any service.

    Example:
        from src.services.webhook_service import trigger_webhooks

        # Fire-and-forget webhook delivery
        asyncio.create_task(trigger_webhooks(
            event_type="instance.started",
            data={"instance_id": "123", "gpu_type": "RTX 4090"},
            user_id="user_abc"
        ))

    Args:
        event_type: The event type
        data: The event data
        user_id: Optional user ID to filter webhooks
    """
    service = get_webhook_service()
    await service.trigger_webhooks(event_type, data, user_id)
