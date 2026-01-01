# Specification: GPU Reservation System

## Overview

Build a GPU reservation system that allows users to pre-book GPU capacity for guaranteed availability with discounted rates (10-20% off spot pricing). This feature addresses Lambda Labs' primary pain point of unpredictable GPU access by enabling production ML teams and enterprise customers to commit to usage in advance, receiving guaranteed SLA and cost certainty through a 30-day credit rollover mechanism.

## Workflow Type

**Type**: feature

**Rationale**: This is a net-new capability introducing reservation-based capacity management to the existing spot-instance GPU platform. It requires new database models, API endpoints, scheduler logic, pricing calculation, and a calendar-based UI—qualifying as a comprehensive feature implementation rather than refactoring or simple enhancement.

## Task Scope

### Services Involved
- **cli** (primary) - Python backend service hosting API endpoints, database models, reservation logic, pricing engine, and scheduler for credit expiration
- **web** (integration) - React frontend providing reservation calendar UI, booking interface, and management dashboard
- **tests** (verification) - Playwright end-to-end tests for reservation flows

### This Task Will:
- [ ] Create database models for reservations and credit tracking (SQLAlchemy)
- [ ] Implement API endpoints for CRUD operations on reservations
- [ ] Build reservation validation logic (prevent double-booking, check credit balance)
- [ ] Develop pricing engine applying 10-20% discounts to spot rates
- [ ] Create scheduler job for 30-day credit expiration (APScheduler)
- [ ] Build React calendar component for reservation management (react-big-calendar)
- [ ] Implement availability checking endpoint
- [ ] Create reservation form with date/time selection (Flatpickr)
- [ ] Add SLA guarantee enforcement logic

### Out of Scope:
- Capacity planning infrastructure (assume existing GPU inventory system)
- Payment gateway integration (use existing billing system)
- Real-time capacity monitoring dashboard
- Multi-region reservation support
- Dynamic pricing adjustments based on demand

## Service Context

### cli (Backend Service)

**Tech Stack:**
- Language: Python
- Framework: FastAPI (inferred from test-server.py pattern)
- ORM: SQLAlchemy 2.0.40
- Database: PostgreSQL
- Scheduler: APScheduler (for credit expiration jobs)
- Key directories: `src/models/`, `src/routers/`, `alembic/`

**Entry Point:** `cli/__main__.py`

**How to Run:**
```bash
cd cli
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python __main__.py
```

**Port:** 8000 (API server)

**Database Connection:**
```
postgresql://dumont:dumont123@localhost:5432/dumont_cloud
```

### web (Frontend Service)

**Tech Stack:**
- Language: JavaScript
- Framework: React
- Build Tool: Vite
- Styling: Tailwind CSS
- State Management: Redux
- Date Picker: Flatpickr (already installed)
- Calendar Library: react-big-calendar (needs installation)
- Key directories: `src/components/`, `src/services/`

**Entry Point:** `web/src/App.jsx`

**How to Run:**
```bash
cd web
npm install
npm run dev
```

**Port:** 5173 (default Vite dev server)

**API Integration:** Consumes `cli.api` endpoints

### tests (End-to-End Verification)

**Tech Stack:**
- Framework: Playwright
- Language: JavaScript
- Test directory: `tests/tests/`

**How to Run:**
```bash
cd tests
npm install
npx playwright test
```

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `cli/src/models/reservation.py` | cli | **CREATE** - Define Reservation model with fields: `id`, `user_id`, `gpu_type`, `start_time`, `end_time`, `status`, `credits_used`, `discount_rate`, `created_at` |
| `cli/src/models/credit.py` | cli | **CREATE** - Define ReservationCredit model tracking unused credits with `user_id`, `amount`, `expires_at`, `reservation_id` |
| `cli/src/routers/reservations.py` | cli | **CREATE** - API endpoints: POST /reservations, GET /reservations, GET /reservations/{id}, DELETE /reservations/{id}, GET /availability |
| `cli/src/services/reservation_service.py` | cli | **CREATE** - Business logic: validate_reservation(), check_availability(), calculate_pricing(), deduct_credits() |
| `cli/src/services/scheduler_service.py` | cli | **CREATE** - APScheduler setup with daily cron job for credit expiration at midnight UTC |
| `cli/alembic/env.py` | cli | **MODIFY** - Configure `target_metadata` to include new Reservation and ReservationCredit models for autogenerate |
| `cli/src/models/user.py` | cli | **MODIFY** - Add `reservations = relationship("Reservation", back_populates="user")` to User model for bidirectional relationship |
| `web/src/components/ReservationCalendar.jsx` | web | **CREATE** - Calendar view using react-big-calendar with reservation events, availability overlay |
| `web/src/components/ReservationForm.jsx` | web | **CREATE** - Form with GPU type selector, Flatpickr date/time range, credit balance display, submit handler |
| `web/src/services/api.js` | web | **MODIFY** - Add reservation API client methods: createReservation(), fetchReservations(), checkAvailability(), cancelReservation() |
| `web/package.json` | web | **MODIFY** - Add dependencies: `react-big-calendar`, `date-fns` (for calendar localizer) |
| `tests/tests/reservation-flow.spec.js` | tests | **CREATE** - E2E test covering: login → calendar view → create reservation → verify booking → cancel reservation |

## Files to Reference

These files show patterns to follow (inferred from project structure):

| File | Pattern to Copy |
|------|----------------|
| `cli/src/models/*.py` | SQLAlchemy model definition patterns with Base inheritance, relationship() usage |
| `cli/src/routers/*.py` | FastAPI router structure with dependency injection, request/response models |
| `web/src/components/*.jsx` | React component structure with Redux hooks (useSelector, useDispatch) |
| `web/src/services/api.js` | API client patterns for backend communication |
| `tests/tests/*.spec.js` | Playwright test structure with page object patterns |

## Patterns to Follow

### SQLAlchemy Model Pattern

From typical `cli/src/models/` structure:

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from src.config.database import Base
import enum

class ReservationStatus(enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    gpu_type = Column(String, nullable=False)  # e.g., "A100", "H100"
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(ReservationStatus), default=ReservationStatus.ACTIVE)
    credits_used = Column(Integer, nullable=False)
    discount_rate = Column(Integer, default=15)  # 10-20% discount
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="reservations")
```

**Key Points:**
- Use `DateTime(timezone=True)` for all timestamp fields to store UTC
- Enum for status tracking ensures type safety
- Foreign key relationships link to existing User model
- Index on `user_id` for query performance

### FastAPI Router Pattern

From typical `cli/src/routers/` structure:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.models.reservation import Reservation
from src.services.reservation_service import ReservationService

router = APIRouter(prefix="/api/reservations", tags=["reservations"])

@router.post("/", response_model=ReservationResponse)
async def create_reservation(
    reservation: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ReservationService(db)

    # Validate availability
    if not service.check_availability(reservation.gpu_type, reservation.start_time, reservation.end_time):
        raise HTTPException(status_code=409, detail="GPU not available for requested time")

    # Validate credit balance
    if not service.has_sufficient_credits(current_user.id, reservation):
        raise HTTPException(status_code=402, detail="Insufficient credits")

    return service.create_reservation(current_user.id, reservation)
```

**Key Points:**
- Use dependency injection for database session and authentication
- Validate business logic before database operations
- Return appropriate HTTP status codes (409 for conflicts, 402 for payment issues)
- Delegate business logic to service layer

### React Calendar Component Pattern

Using react-big-calendar with date-fns:

```javascript
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enUS } from 'date-fns/locale';
import 'react-big-calendar/lib/css/react-big-calendar.css';

const locales = { 'en-US': enUS };
const localizer = dateFnsLocalizer({ format, parse, startOfWeek, getDay, locales });

export default function ReservationCalendar({ reservations, onSelectSlot }) {
  const events = reservations.map(r => ({
    id: r.id,
    title: `${r.gpu_type} Reserved`,
    start: new Date(r.start_time),
    end: new Date(r.end_time),
    resource: r
  }));

  return (
    <Calendar
      localizer={localizer}
      events={events}
      startAccessor="start"
      endAccessor="end"
      style={{ height: 600 }}
      onSelectSlot={onSelectSlot}
      selectable
    />
  );
}
```

**Key Points:**
- Use `dateFnsLocalizer` for lightweight date handling (13KB vs moment.js 67KB)
- Events must have `start`/`end` as Date objects
- `selectable` prop enables click-to-create-reservation flow
- Import CSS for default styling

## Requirements

### Functional Requirements

1. **Reservation Creation**
   - Description: Users select GPU type, start time, end time to create reservation
   - Acceptance:
     - API validates no overlapping reservations for same GPU/time
     - Credits deducted upfront based on estimated usage with 10-20% discount
     - Database record created with status="active"
     - User receives confirmation with reservation ID

2. **Availability Checking**
   - Description: Real-time availability query before booking
   - Acceptance:
     - GET /api/availability?gpu_type=A100&start=...&end=... returns boolean
     - Accounts for existing reservations and capacity limits
     - Response time < 500ms for calendar UI responsiveness

3. **Discount Pricing Engine**
   - Description: Apply 10-20% discount to spot pricing for reservations
   - Acceptance:
     - Fetch current spot price for GPU type
     - Calculate discount based on reservation duration (longer = higher discount)
     - Store discount_rate in reservation record
     - Display discounted price in UI before confirmation

4. **Credit Rollover System**
   - Description: Unused reservation credits expire after 30 days
   - Acceptance:
     - Daily scheduler job at midnight UTC checks credit expiration
     - Credits with `expires_at` < now() marked as expired
     - User notification sent 7 days before expiration
     - Expired credits removed from available balance

5. **Reservation Management UI**
   - Description: Calendar view showing active, past, upcoming reservations
   - Acceptance:
     - Calendar displays all user reservations color-coded by status
     - Click event shows reservation details modal
     - Cancel button available for future reservations (refunds unused portion)
     - Responsive on mobile/tablet

6. **SLA Guarantee Enforcement**
   - Description: Ensure reserved GPUs available at scheduled time
   - Acceptance:
     - At reservation start_time, system allocates GPU from pool
     - If allocation fails, automatic refund + alert to ops team
     - User notified of allocation success/failure
     - 99.9% SLA tracked in metrics dashboard

### Edge Cases

1. **Overlapping Reservations** - Validate start/end times don't conflict with existing bookings via SQL query: `WHERE gpu_type = X AND NOT (end_time <= new_start OR start_time >= new_end)`
2. **Insufficient Credits** - Check user credit balance >= estimated cost before allowing reservation creation
3. **Past Date Booking** - Frontend and backend validation to reject reservations with start_time < now()
4. **Timezone Handling** - Store all timestamps in UTC, convert to user's local timezone in UI using date-fns
5. **Reservation Modification** - Do not allow editing; require cancel + recreate pattern to avoid complex validation
6. **GPU Type Availability** - If GPU type not in inventory, return 404 with available alternatives
7. **Credit Expiration During Active Reservation** - Credits locked to reservation don't expire until reservation completes
8. **Concurrent Booking Race Condition** - Use database transaction isolation + unique constraint to prevent double-booking

## Implementation Notes

### DO
- Follow existing SQLAlchemy model patterns in `cli/src/models/` for Base inheritance
- Reuse existing authentication middleware from other routers for `/api/reservations` endpoints
- Use Flatpickr (already in `web/package.json`) for date/time selection UI
- Store all timestamps in UTC (DateTime with timezone=True) and convert in frontend
- Implement database migrations with Alembic autogenerate
- Add indexes on `reservations.user_id`, `reservations.start_time`, `reservations.gpu_type` for query performance
- Use Redux for reservation state management following patterns in `web/src/`
- Configure APScheduler with `BackgroundScheduler` (separate thread for web apps)

### DON'T
- Don't use moment.js for date handling (67KB) - prefer date-fns (13KB tree-shakeable)
- Don't allow direct reservation modification - use cancel + recreate workflow
- Don't store credits in user table - separate `reservation_credits` table for expiration tracking
- Don't skip Alembic migration review - autogenerate misses renames and complex changes
- Don't implement real-time WebSocket updates in first iteration - poll for availability
- Don't hardcode discount rates - make configurable via environment variable
- Don't expose internal GPU inventory details in API responses - abstract to "available/unavailable"

## Development Environment

### Start Services

**Backend (CLI):**
```bash
cd cli
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Install new dependencies
pip install apscheduler
# Run migrations
alembic revision --autogenerate -m "Add reservation and credit models"
alembic upgrade head
# Start server
python __main__.py
```

**Frontend (Web):**
```bash
cd web
npm install
# Install new dependencies
npm install react-big-calendar date-fns
# Start dev server
npm run dev
```

**Database:**
```bash
# Start PostgreSQL (if not running)
docker-compose up -d postgres
# Or use existing connection
psql postgresql://dumont:dumont123@localhost:5432/dumont_cloud
```

### Service URLs
- CLI (Backend API): http://localhost:8000
- Web (Frontend): http://localhost:5173 (Vite dev server)
- PostgreSQL: localhost:5432

### Required Environment Variables
- `DATABASE_URL`: postgresql://dumont:dumont123@localhost:5432/dumont_cloud
- `APP_HOST`: 0.0.0.0
- `APP_PORT`: 8000
- `DEBUG`: true
- `RESERVATION_DISCOUNT_MIN`: 10 (minimum discount percentage)
- `RESERVATION_DISCOUNT_MAX`: 20 (maximum discount percentage)
- `CREDIT_EXPIRY_DAYS`: 30

## Success Criteria

The task is complete when:

1. [ ] User can view calendar showing available GPU time slots
2. [ ] User can create reservation by selecting GPU type, start time, end time
3. [ ] Reservation creation validates availability and credit balance
4. [ ] Pricing displayed with 10-20% discount off spot rates
5. [ ] Credits deducted on successful reservation
6. [ ] Reservation appears in user's calendar with correct time/GPU type
7. [ ] User can cancel future reservation (refund unused portion)
8. [ ] Daily scheduler job expires credits older than 30 days
9. [ ] No console errors in browser dev tools
10. [ ] Existing API tests still pass (`pytest cli/tests/`)
11. [ ] New functionality verified via Playwright E2E test
12. [ ] Database migrations run successfully without data loss

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| test_create_reservation_success | `cli/tests/test_reservations.py` | Valid reservation created with correct credits deducted, status=active |
| test_create_reservation_insufficient_credits | `cli/tests/test_reservations.py` | 402 error returned when user credits < estimated cost |
| test_create_reservation_overlap_conflict | `cli/tests/test_reservations.py` | 409 error when overlapping reservation exists for same GPU/time |
| test_check_availability_returns_true | `cli/tests/test_reservations.py` | Availability endpoint returns true for open time slots |
| test_check_availability_returns_false | `cli/tests/test_reservations.py` | Availability endpoint returns false for booked slots |
| test_calculate_discount_pricing | `cli/tests/test_reservation_service.py` | Discount calculation applies 10-20% based on duration |
| test_cancel_reservation_refunds_credits | `cli/tests/test_reservations.py` | Cancelled reservation refunds unused credits proportionally |
| test_credit_expiration_job | `cli/tests/test_scheduler.py` | Scheduler marks credits expired after 30 days |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| test_reservation_flow_api | cli ↔ PostgreSQL | POST /api/reservations creates DB record, deducts credits, returns 201 |
| test_availability_with_existing_bookings | cli ↔ PostgreSQL | GET /api/availability correctly accounts for overlapping reservations |
| test_frontend_api_integration | web ↔ cli | React component fetches reservations, displays in calendar, creates new booking via API |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Complete Reservation Booking | 1. Login as test user<br>2. Navigate to Reservations page<br>3. Open calendar view<br>4. Select available time slot<br>5. Choose GPU type (A100)<br>6. Confirm reservation<br>7. Verify calendar event appears | Reservation appears in calendar, credits deducted from balance, confirmation message shown |
| Cancellation Flow | 1. Login as test user<br>2. View existing reservation in calendar<br>3. Click event to open details<br>4. Click "Cancel Reservation"<br>5. Confirm cancellation<br>6. Verify event removed from calendar | Reservation status changed to "cancelled", unused credits refunded, event removed from UI |
| Insufficient Credits Error | 1. Login as low-balance user<br>2. Attempt to book expensive reservation<br>3. Submit form | Error message displayed: "Insufficient credits for this reservation" |

### Browser Verification (Frontend)
| Page/Component | URL | Checks |
|----------------|-----|--------|
| Reservation Calendar | `http://localhost:8000/reservations` | Calendar renders with react-big-calendar, existing reservations display as events, click-to-create works |
| Reservation Form | `http://localhost:8000/reservations/new` | Flatpickr date picker functional, GPU type dropdown populated, credit balance displayed, submit button enabled only when valid |
| Reservation Details Modal | Calendar event click | Modal shows reservation ID, GPU type, start/end times, credits used, discount rate, cancel button |

### Database Verification
| Check | Query/Command | Expected |
|-------|---------------|----------|
| Reservations table exists | `\dt reservations` | Table schema matches Reservation model with all columns |
| Credits table exists | `\dt reservation_credits` | Table schema matches ReservationCredit model |
| Migration applied | `alembic current` | Migration revision hash matches latest migration file |
| Sample reservation created | `SELECT * FROM reservations WHERE user_id=1;` | Record exists with correct gpu_type, timestamps, status="active" |
| Credit deduction | `SELECT SUM(amount) FROM reservation_credits WHERE user_id=1;` | Balance decremented by reservation cost |
| No overlapping reservations | `SELECT COUNT(*) FROM reservations WHERE gpu_type='A100' AND status='active' AND start_time < '2024-02-01 12:00:00' AND end_time > '2024-02-01 10:00:00';` | Count <= 1 (no double-booking) |

### API Contract Verification
| Endpoint | Method | Request | Response | Status |
|----------|--------|---------|----------|--------|
| /api/reservations | POST | `{"gpu_type": "A100", "start_time": "2024-02-01T10:00:00Z", "end_time": "2024-02-01T12:00:00Z"}` | `{"id": 123, "status": "active", "credits_used": 50, "discount_rate": 15}` | 201 Created |
| /api/reservations | GET | - | `[{"id": 123, "gpu_type": "A100", ...}]` | 200 OK |
| /api/availability | GET | `?gpu_type=A100&start=2024-02-01T10:00:00Z&end=2024-02-01T12:00:00Z` | `{"available": true, "capacity": 5}` | 200 OK |
| /api/reservations/123 | DELETE | - | `{"message": "Reservation cancelled", "credits_refunded": 30}` | 200 OK |

### Scheduler Verification
| Check | Command | Expected |
|-------|---------|----------|
| APScheduler running | Check logs for "Scheduler started" | Background scheduler initialized on app startup |
| Credit expiry job registered | `scheduler.get_jobs()` | Job with trigger=CronTrigger (hour=0, minute=0) exists |
| Expiry logic executes | Manually trigger job or wait until midnight | Credits with `expires_at < now()` removed from available balance |

### QA Sign-off Requirements
- [ ] All 8 unit tests pass with `pytest cli/tests/`
- [ ] All 3 integration tests pass
- [ ] All 3 E2E test flows complete successfully with Playwright
- [ ] Browser verification confirms calendar renders correctly with reservations
- [ ] Database queries show reservations table populated, no overlapping bookings
- [ ] API contract tests return expected status codes and response formats
- [ ] Scheduler job runs at midnight and expires credits correctly
- [ ] No regressions in existing functionality (all previous tests pass)
- [ ] Code follows SQLAlchemy/FastAPI/React patterns from existing codebase
- [ ] No security vulnerabilities (credit manipulation, unauthorized access)
- [ ] No SQL injection risks (use parameterized queries)
- [ ] Timezone handling verified (UTC in DB, local in UI)
- [ ] Performance acceptable (availability check < 500ms, calendar load < 2s)
