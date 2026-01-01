# Specification: Webhook Integration System

## Overview

Implement a comprehensive webhook notification system for the Dumont Cloud platform that enables external automation by sending HTTP callbacks for critical infrastructure events. This feature will allow DevOps engineers and developers to integrate Dumont with third-party tools like Slack, CI/CD pipelines, and automation platforms (Zapier, n8n) by configuring webhooks that fire when instance lifecycle events, snapshots, failovers, or cost thresholds occur.

## Workflow Type

**Type**: feature

**Rationale**: This is a net-new capability that extends the platform's functionality to support event-driven integrations. It requires new database models, API endpoints, background services for webhook delivery, and dashboard UI components—classic feature development scope rather than refactoring or bug fixes.

## Task Scope

### Services Involved
- **api** (primary) - FastAPI backend service (src/) implementing webhook management APIs, event triggering logic, and async delivery service
- **web** (integration) - React frontend for webhook configuration UI and delivery log viewer in dashboard

### This Task Will:
- [ ] Create database schema for webhook configurations and delivery logs
- [ ] Implement API endpoints for webhook CRUD operations and test trigger
- [ ] Build async webhook delivery service with retry logic (3 attempts)
- [ ] Integrate webhook triggers into existing event emission points (instance lifecycle, snapshots, failover, cost alerts)
- [ ] Add HMAC-SHA256 signature generation for webhook security
- [ ] Create React dashboard UI for webhook management and log viewing

### Out of Scope:
- Migration of existing historical events (webhooks only fire for new events)
- Advanced retry strategies beyond 3 attempts with exponential backoff
- Webhook templating or custom payload transformation
- Rate limiting per webhook endpoint (future enhancement)
- Webhook authentication beyond HMAC signatures (OAuth, API keys, etc.)

## Service Context

### API (Backend Service)

**Tech Stack:**
- Language: Python
- Framework: FastAPI
- ORM: SQLAlchemy 2.0.40
- Database: PostgreSQL (dumont_cloud)
- Key directories: `src/models/`, `src/services/`, `src/api/v1/endpoints/`

**Entry Point:** `src/main.py`

**How to Run:**
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Port:** 8000 (backend API)

**Dependencies:**
- httpx 0.28.1 (async HTTP client for webhook delivery)
- tenacity 9.1.2 (retry decorator with exponential backoff)
- SQLAlchemy 2.0.40 (ORM)
- psycopg2-binary 2.9.11 (PostgreSQL adapter)

### Web (Frontend Service)

**Tech Stack:**
- Language: JavaScript
- Framework: React
- Build Tool: Vite
- Styling: Tailwind CSS
- State Management: Redux (@reduxjs/toolkit)
- UI Components: Radix UI

**Entry Point:** `src/App.jsx`

**How to Run:**
```bash
cd web
npm run dev
```

**Port:** 8000 (development server proxies to backend)

**Key Directories:**
- `src/components/` - React components
- `src/pages/` - Page-level components
- `src/store/` - Redux slices

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `src/models/webhook_config.py` | api | **CREATE NEW** - Define WebhookConfig and WebhookLog models using SQLAlchemy |
| `src/services/webhook_service.py` | api | **CREATE NEW** - Implement async webhook delivery with httpx + tenacity retry |
| `src/api/v1/endpoints/webhooks.py` | api | **CREATE NEW** - FastAPI router for webhook CRUD and test endpoints |
| `src/core/security/hmac_signature.py` | api | **CREATE NEW** - HMAC-SHA256 signature generation/verification |
| `src/migrations/add_webhooks.py` | api | **CREATE NEW** - Database migration for webhook tables |
| `src/services/gpu/instance_manager.py` | api | Add webhook trigger calls for instance.started, instance.stopped events (if exists) |
| `src/services/snapshot_service.py` | api | Add webhook trigger call for snapshot.completed event (if exists) |
| `src/services/failover_orchestrator.py` | api | Add webhook trigger call for failover.triggered event |
| `src/services/cost_monitor.py` | api | Add webhook trigger call for cost.threshold event (if exists) |
| `web/src/pages/Settings/Webhooks.jsx` | web | **CREATE NEW** - Webhook management UI (list, create, edit, delete, test) |
| `web/src/components/WebhookLogViewer.jsx` | web | **CREATE NEW** - Table component showing webhook delivery history |
| `web/src/store/webhooksSlice.js` | web | **CREATE NEW** - Redux slice for webhook state management |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `src/models/instance_status.py` | SQLAlchemy model definition conventions (Base class, table structure, Integer IDs) |
| `src/config/database.py` | Database Base class import and session management |
| `src/services/job/job_manager.py` | Async service pattern with asyncio |
| `src/api/v1/endpoints/instances.py` | FastAPI endpoint pattern with dependency injection |
| `web/src/pages/Settings/` | Settings page layout and component structure |
| `web/src/store/instancesSlice.js` | Redux slice pattern for API integration |

## Patterns to Follow

### Database Model Pattern

From `src/models/instance_status.py`:

```python
from sqlalchemy import Column, String, Boolean, JSON, DateTime, Integer, Index
from datetime import datetime
from src.config.database import Base

class WebhookConfig(Base):
    __tablename__ = 'webhook_configs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(JSON, nullable=False)  # ['instance.started', 'cost.threshold']
    secret = Column(String(100), nullable=True)  # For HMAC signing
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_user_webhooks', 'user_id', 'enabled'),
    )

class WebhookLog(Base):
    __tablename__ = 'webhook_logs'

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    status_code = Column(Integer, nullable=True)
    response = Column(String(1000), nullable=True)
    attempt = Column(Integer, default=1)
    error = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_webhook_logs', 'webhook_id', 'created_at'),
    )
```

**Key Points:**
- Use `from src.config.database import Base` for model base class
- Use Integer primary keys (matching instance_status.py pattern)
- Index `user_id` and `webhook_id` for query performance
- JSON columns for flexible event lists and payloads
- Timestamp columns with `datetime.utcnow` (matching codebase pattern)
- Composite indexes with `__table_args__` for common queries

### Async Webhook Delivery with Retry

From httpx + tenacity libraries (research notes):

```python
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import hmac
import hashlib
import json

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException))
)
async def send_webhook(url: str, payload: dict, secret: str = None) -> dict:
    """Send webhook with retry logic."""
    headers = {"Content-Type": "application/json"}

    # Add HMAC signature if secret provided
    if secret:
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raises HTTPStatusError on 4xx/5xx
        return {"status": response.status_code, "response": response.text}

async def trigger_webhooks(event_type: str, payload: dict):
    """Fire-and-forget webhook delivery for event."""
    webhooks = get_active_webhooks_for_event(event_type)

    for webhook in webhooks:
        # Create task without awaiting (fire-and-forget)
        asyncio.create_task(
            _deliver_webhook_with_logging(webhook, event_type, payload)
        )
```

**Key Points:**
- Use httpx AsyncClient with explicit 10-second timeout
- Tenacity decorator handles 3 retries with exponential backoff (2s, 4s, 8s...)
- HMAC-SHA256 signature in `X-Webhook-Signature` header (GitHub/Stripe pattern)
- Fire-and-forget with `asyncio.create_task()` to avoid blocking
- Log delivery attempts to WebhookLog table

### FastAPI Router Pattern

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[str]
    secret: str = None

@router.post("/")
async def create_webhook(webhook: WebhookCreate, user_id: str = Depends(get_current_user)):
    """Create new webhook configuration."""
    # Validate events
    valid_events = {"instance.started", "instance.stopped", "snapshot.completed",
                    "failover.triggered", "cost.threshold"}
    if not set(webhook.events).issubset(valid_events):
        raise HTTPException(400, "Invalid event types")

    # Save to database...

@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str, user_id: str = Depends(get_current_user)):
    """Send test payload to webhook."""
    webhook = get_webhook(webhook_id, user_id)
    sample_payload = {
        "event": "test",
        "data": {"message": "This is a test webhook"},
        "timestamp": datetime.utcnow().isoformat()
    }
    await send_webhook(webhook.url, sample_payload, webhook.secret)
```

**Key Points:**
- Use Pydantic models for request/response validation
- Dependency injection for auth (`get_current_user`)
- Test endpoint sends sample payload for validation

## Requirements

### Functional Requirements

1. **Webhook Configuration Management**
   - Description: Users can create, read, update, delete webhook configurations via API and dashboard UI
   - Acceptance: POST /webhooks creates config, GET /webhooks lists user's webhooks, PUT /webhooks/{id} updates, DELETE /webhooks/{id} removes

2. **Event Type Subscription**
   - Description: Webhooks can subscribe to specific event types (instance.started, instance.stopped, snapshot.completed, failover.triggered, cost.threshold)
   - Acceptance: Webhook fires only for subscribed event types, validated at creation time

3. **Webhook Delivery with Retry**
   - Description: Webhooks deliver via HTTP POST with 3 retry attempts on failure
   - Acceptance: Failed deliveries retry with exponential backoff (2s, 4s, 8s), all attempts logged

4. **HMAC Signature Security**
   - Description: Webhooks optionally include HMAC-SHA256 signature for payload verification
   - Acceptance: If secret configured, X-Webhook-Signature header contains sha256=<hex_digest> of payload

5. **Test Webhook Endpoint**
   - Description: Users can send test payload to webhook without waiting for real event
   - Acceptance: POST /webhooks/{id}/test sends sample payload, returns delivery status

6. **Webhook Delivery Logs**
   - Description: All delivery attempts logged with status, response, error details
   - Acceptance: Dashboard shows log table with timestamp, event, status, attempt count, error (if any)

### Edge Cases

1. **Webhook URL Unreachable** - Retry 3 times, log final failure, don't block event processing
2. **Slow Webhook Response (>10s timeout)** - Timeout exception triggers retry, max 3 attempts
3. **Webhook Returns 4xx/5xx** - Log error response, retry (some 4xx like 404 may not benefit from retry but keep logic simple)
4. **User Deletes Webhook During Delivery** - Check webhook.enabled flag before delivery, skip if disabled/deleted
5. **Concurrent Events** - Use asyncio tasks to deliver webhooks in parallel without blocking
6. **Payload Too Large** - Set reasonable payload size limit (e.g., 100KB) to prevent abuse
7. **Secret Rotation** - Allow updating webhook secret without breaking existing deliveries

## Implementation Notes

### DO
- Follow the SQLAlchemy model pattern in `src/models/instance_status.py` for webhook tables (Integer IDs, datetime.utcnow)
- Reuse async patterns from `src/services/job/job_manager.py` for webhook delivery service
- Use httpx (not requests) for native async support
- Implement HMAC signature with `hmac.compare_digest()` to prevent timing attacks
- Log every delivery attempt to WebhookLog table for observability
- Use `asyncio.create_task()` for fire-and-forget delivery (don't block events)
- Set explicit 10-second timeout on httpx client
- Validate event types against whitelist at webhook creation
- Register webhook router in `src/api/v1/router.py` following existing endpoint patterns

### DON'T
- Don't use synchronous `requests` library (project uses async patterns)
- Don't await webhook delivery in event handlers (use fire-and-forget)
- Don't propagate webhook errors to main application flow
- Don't retry indefinitely (hard limit of 3 attempts)
- Don't expose webhook secrets in API responses (redact in GET responses)
- Don't skip HMAC signature verification if secret is configured
- Don't use plain string comparison for HMAC (timing attack vulnerability)

## Development Environment

### Start Services

```bash
# Start backend (from project root)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (separate terminal)
cd web
npm run dev

# Database migrations (if needed)
# Add migration script to src/migrations/ and import in src/config/database.py
```

### Service URLs
- Backend API: http://localhost:8000
- Frontend Dev: http://localhost:8000 (Vite proxy to backend)
- PostgreSQL: localhost:5432 (dumont_cloud database)
- Redis: localhost:6379

### Required Environment Variables
- `DATABASE_URL`: postgresql://dumont:dumont123@localhost:5432/dumont_cloud
- `REDIS_URL`: redis://localhost:6379/0
- `APP_HOST`: 0.0.0.0
- `APP_PORT`: 8000
- `DEBUG`: true (for development)

## Success Criteria

The task is complete when:

1. [ ] User can create webhook via POST /webhooks with name, URL, event list, optional secret
2. [ ] User can list webhooks via GET /webhooks (secrets redacted)
3. [ ] User can test webhook via POST /webhooks/{id}/test and see delivery result
4. [ ] Instance start/stop events trigger webhooks subscribed to instance.started/instance.stopped
5. [ ] Snapshot completion triggers webhooks subscribed to snapshot.completed
6. [ ] Failed webhook deliveries retry 3 times with exponential backoff
7. [ ] All delivery attempts logged to webhook_logs table
8. [ ] Dashboard UI displays webhook list with create/edit/delete actions
9. [ ] Dashboard UI displays webhook logs with status, timestamp, error details
10. [ ] HMAC-SHA256 signature included in X-Webhook-Signature header when secret configured
11. [ ] No console errors in browser or backend logs
12. [ ] Existing tests still pass
13. [ ] Webhook delivery tested via ngrok or webhook.site

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| test_webhook_config_model | `tests/models/test_webhook_config.py` | WebhookConfig and WebhookLog models create/query correctly |
| test_hmac_signature | `tests/core/security/test_hmac_signature.py` | HMAC-SHA256 generation matches expected format, verification works |
| test_send_webhook_success | `tests/services/test_webhook_service.py` | Webhook delivery succeeds with 200 response |
| test_send_webhook_retry | `tests/services/test_webhook_service.py` | Failed delivery retries 3 times with exponential backoff |
| test_trigger_webhooks | `tests/services/test_webhook_service.py` | Only webhooks subscribed to event type fire |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| test_webhook_crud_api | api | POST creates, GET lists, PUT updates, DELETE removes webhooks |
| test_webhook_test_endpoint | api | POST /api/v1/webhooks/{id}/test delivers sample payload |
| test_event_to_webhook_flow | api (services → webhook service) | Instance events trigger webhooks correctly |
| test_webhook_log_creation | api (webhook service → database) | Delivery attempts create WebhookLog records |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Create and Test Webhook | 1. Navigate to Settings → Webhooks<br>2. Click "Add Webhook"<br>3. Fill form (name, URL, events, secret)<br>4. Save webhook<br>5. Click "Test" button | Webhook appears in list, test delivery succeeds, log entry shows 200 status |
| Instance Event Triggers Webhook | 1. Create webhook for instance.started<br>2. Start GPU instance<br>3. Check webhook logs | Log entry shows instance.started delivery with instance details in payload |
| Failed Webhook Retries | 1. Create webhook with invalid URL (e.g., http://localhost:9999/hook)<br>2. Trigger event<br>3. Check logs | 3 log entries with attempt 1, 2, 3 and connection error messages |

### Browser Verification (Frontend)
| Page/Component | URL | Checks |
|----------------|-----|--------|
| Webhook Settings Page | `http://localhost:8000/settings/webhooks` | Page loads, displays webhook table, "Add Webhook" button visible |
| Webhook Create Form | `http://localhost:8000/settings/webhooks` (modal/drawer) | Form has name, URL, event checkboxes, secret field (optional) |
| Webhook Log Viewer | `http://localhost:8000/settings/webhooks` (expand row or separate view) | Logs table shows timestamp, event, status code, attempt, error |

### Database Verification
| Check | Query/Command | Expected |
|-------|---------------|----------|
| Webhook config persists | `SELECT * FROM webhook_configs WHERE user_id = 'test_user';` | Row exists with correct URL, events JSON, secret |
| Webhook log created | `SELECT * FROM webhook_logs WHERE webhook_id = '<id>' ORDER BY created_at DESC LIMIT 3;` | 3 rows (if retries triggered) with attempt 1, 2, 3 |
| Migration applied | `alembic current` | Shows latest migration hash (xxx_add_webhooks) |

### API Verification
| Endpoint | Method | Request Body | Expected Response |
|----------|--------|--------------|-------------------|
| /webhooks | POST | `{"name": "Test", "url": "https://webhook.site/...", "events": ["instance.started"]}` | 201 Created, returns webhook object with id |
| /webhooks | GET | - | 200 OK, array of webhooks (secrets redacted) |
| /webhooks/{id} | PUT | `{"enabled": false}` | 200 OK, webhook disabled |
| /webhooks/{id}/test | POST | - | 200 OK, delivery status returned |
| /webhooks/{id} | DELETE | - | 204 No Content |

### QA Sign-off Requirements
- [ ] All unit tests pass (pytest coverage >80% for webhook code)
- [ ] All integration tests pass (API endpoints return correct status codes)
- [ ] All E2E tests pass (Playwright verifies UI flows)
- [ ] Browser verification complete (webhook UI loads and functions)
- [ ] Database state verified (migrations applied, data persists)
- [ ] No regressions in existing functionality (instance start/stop still works without webhooks)
- [ ] Code follows established patterns (SQLAlchemy models, async services, FastAPI routers)
- [ ] No security vulnerabilities introduced (HMAC verification, no secret leakage in logs)
- [ ] Webhook delivery tested with external service (webhook.site or ngrok)
- [ ] Retry logic verified (3 attempts with exponential backoff logged correctly)
