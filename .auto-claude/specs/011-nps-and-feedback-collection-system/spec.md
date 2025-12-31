# Specification: NPS and Feedback Collection System

## Overview

Build an integrated NPS (Net Promoter Score) and feedback collection system that measures user satisfaction at strategic moments in the user journey. The system will collect 0-10 scores with optional comments, display them in an admin dashboard, and enable product managers to track satisfaction trends and follow up with detractors. This feature is essential for data-driven product decisions and aligns with the product vision's success metrics.

**⚠️ IMPORTANT**: This spec was created without research validation (research.json missing). Before implementation, verify:
- All mentioned npm packages are installed in `web/package.json` (@radix-ui/react-dialog, framer-motion, etc.)
- Python packages are available (FastAPI, SQLAlchemy, Pydantic)
- Existing codebase patterns for Redux, API routes, and database models
- Migration tool being used (Alembic vs other)
- Whether a background job system exists (Celery, RQ, etc.)

## Workflow Type

**Type**: feature

**Rationale**: This is a new feature implementation adding user satisfaction measurement capabilities to the platform. It requires new UI components, backend APIs, database schema, and integration with existing user workflows.

## Task Scope

### Services Involved
- **web** (primary) - React frontend for NPS survey UI and admin dashboard
- **cli** (primary) - Python/FastAPI backend for NPS data storage and retrieval APIs
- **Database** (integration) - PostgreSQL for storing NPS responses, survey configurations, and user interaction history
- **Redis** (optional) - Cache for rate limiting (can use PostgreSQL if Redis not available)

### This Task Will:
- [ ] Create configurable trigger system for showing NPS surveys at key moments (first deployment, monthly, after issue resolution)
- [ ] Build frontend NPS survey component (0-10 score + optional comment)
- [ ] Implement rate limiting to prevent survey fatigue (dismiss tracking, frequency controls)
- [ ] Create admin dashboard for viewing NPS trends over time
- [ ] Build detractor follow-up mechanism for low scores (0-6)
- [ ] Develop backend APIs for storing/retrieving NPS data
- [ ] Create database schema for NPS responses and survey configurations

### Out of Scope:
- Email notifications for detractor alerts (manual follow-up initially)
- Advanced analytics (cohort analysis, segmentation) - future enhancement
- Integration with external analytics platforms (Mixpanel, Amplitude)
- Automated response workflows (e.g., auto-send resources to detractors)
- Multi-language survey support

## Service Context

### Web (Primary Frontend Service)

**Tech Stack:**
- Language: JavaScript
- Framework: React
- Build Tool: Vite
- Styling: Tailwind CSS
- State Management: Redux
- UI Components: Radix UI, Framer Motion
- Charts: ApexCharts, Chart.js

**Entry Point:** `src/App.jsx`

**How to Run:**
```bash
cd web
npm run dev
```

**Port:** 3000 (proxied through CLI backend on port 8000)

**Key Directories:**
- `src/` - Source code
- `src/components/` - React components
- `src/store/` - Redux state management
- `src/pages/` - Page components

### CLI (Primary Backend Service)

**Tech Stack:**
- Language: Python 3.10+ (uses modern union type syntax)
- Framework: FastAPI (inferred from project context)
- Database: PostgreSQL
- ORM: SQLAlchemy
- Testing: pytest

**Entry Point:** `__main__.py`

**How to Run:**
```bash
cd cli
python -m cli
```

**Key Directories:**
- `utils/` - Utility functions
- `tests/` - Test files

**Environment Variables:**
- `DATABASE_URL`: postgresql://dumont:dumont123@localhost:5432/dumont_cloud
- `DB_HOST`: localhost
- `DB_PORT`: 5432
- `DB_NAME`: dumont_cloud
- `APP_PORT`: 8000

## Files to Modify

Since this is a greenfield implementation, the following new files will be created:

| File | Service | What to Create |
|------|---------|----------------|
| `web/src/components/NPSSurvey.jsx` | web | NPS survey modal component (0-10 score + comment) |
| `web/src/components/AdminDashboard/NPSTrends.jsx` | web | Admin dashboard page for viewing NPS trends (or `web/src/pages/Admin/NPSTrends.jsx` - follow existing admin page structure) |
| `web/src/store/slices/npsSlice.js` | web | Redux state management for NPS data (must be imported in store configuration) |
| `web/src/hooks/useNPSTrigger.js` | web | Custom hook for handling survey triggers and rate limiting |
| `cli/routes/nps.py` | cli | FastAPI routes for NPS data endpoints |
| `cli/models/nps.py` | cli | SQLAlchemy models for NPS data |
| `cli/services/nps_service.py` | cli | Business logic for NPS triggers and rate limiting |
| `cli/migrations/xxx_create_nps_tables.py` | cli | Database migration for NPS schema |

## Files to Reference

**⚠️ NOTE**: No specific reference files were identified in context.json. Before implementation, explore the codebase to find examples:

| Pattern Area | What to Find | Where to Look |
|--------------|--------------|---------------|
| React Components | Existing modal/dialog components | `web/src/components/**/*.jsx` |
| API Routes | FastAPI route structure and patterns | `cli/routes/*.py` |
| Database Models | SQLAlchemy model definitions | `cli/models/*.py` |
| Database Migrations | Migration file format and tool | `cli/migrations/*.py` or `cli/alembic/versions/*.py` |
| Redux State | Redux Toolkit slice patterns | `web/src/store/slices/*.js` |
| Redux Store Config | How slices are registered | `web/src/store/index.js` or `web/src/store/store.js` |
| Form Handling | Validation and submission patterns | `web/src/components/forms/*.jsx` |
| Authentication | How user_id is accessed | `web/src/` (auth context/hooks) |

## Patterns to Follow

### React Component Pattern

Components should use:
- Functional components with hooks
- Radix UI for accessible UI primitives
- Tailwind CSS for styling
- Framer Motion for animations
- PropTypes or TypeScript for type safety

**Example structure:**
```jsx
import { useState } from 'react';
import { motion } from 'framer-motion';
import * as Dialog from '@radix-ui/react-dialog';

export default function NPSSurvey({ isOpen, onClose, onSubmit }) {
  const [score, setScore] = useState(null);
  const [comment, setComment] = useState('');

  // Component logic

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      {/* Survey UI */}
    </Dialog.Root>
  );
}
```

**Key Points:**
- Use Radix UI Dialog for modal overlay
- Implement accessible keyboard navigation
- Add smooth animations with Framer Motion
- Validate score (0-10) before submission

### FastAPI Route Pattern

Backend routes should follow RESTful conventions:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/nps", tags=["nps"])

class NPSSubmission(BaseModel):
    score: int
    comment: str | None = None
    user_id: int
    trigger_type: str

@router.post("/submit")
async def submit_nps(submission: NPSSubmission):
    # Validation and business logic
    return {"status": "success"}
```

**Key Points:**
- Use Pydantic models for request/response validation
- Implement proper error handling with HTTP status codes
- Add authentication/authorization checks
- Return consistent JSON responses

### Database Model Pattern

Use SQLAlchemy ORM for data models:

```python
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class NPSResponse(Base):
    __tablename__ = "nps_responses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    score = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, index=True)

class NPSSurveyConfig(Base):
    __tablename__ = "nps_survey_config"

    id = Column(Integer, primary_key=True)
    trigger_type = Column(String(50), nullable=False, unique=True)
    enabled = Column(Boolean, default=True)
    frequency_days = Column(Integer, default=30)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

class NPSUserInteraction(Base):
    __tablename__ = "nps_user_interactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    interaction_type = Column(String(20), nullable=False)  # 'shown', 'dismissed', 'submitted'
    trigger_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, index=True)
```

**Key Points:**
- Use proper column types and constraints
- Add indexes for frequently queried columns
- Include timestamps for audit trail
- Add foreign key relationships where appropriate

## Requirements

### Functional Requirements

1. **NPS Survey Collection**
   - Description: Display 0-10 scale survey with optional comment field
   - Acceptance: User can rate from 0-10, optionally add text feedback, and submit successfully

2. **Configurable Triggers**
   - Description: Survey appears after first deployment, monthly, or after issue resolution
   - Acceptance: Survey triggers fire at configured events; system tracks which triggers have occurred

3. **Rate Limiting & Dismissal**
   - Description: Users can dismiss surveys; system prevents showing surveys too frequently
   - Acceptance: Dismissed surveys don't reappear for configured time period; users see max 1 survey per month

4. **Admin Dashboard**
   - Description: Product managers view NPS trends over time with charts
   - Acceptance: Dashboard displays NPS score over time, response count, detractor/passive/promoter breakdown

5. **Detractor Follow-up**
   - Description: Flag responses with scores 0-6 for manual follow-up
   - Acceptance: Admin dashboard highlights detractors; enables filtering and viewing individual responses

### Edge Cases

1. **Anonymous/Unauthenticated Users** - Survey should only appear for authenticated users with valid user IDs
2. **Multiple Browser Sessions** - Rate limiting should be server-side (user_id based), not cookie-based
3. **Survey During Critical Actions** - Don't show survey during deployments or other critical workflows (check Redux state for active operations)
4. **Database Connection Failures** - Gracefully handle submission failures with retry logic and user feedback
5. **Concurrent Submissions** - Prevent duplicate submissions via:
   - Frontend: Disable submit button after first click
   - Backend: Add unique constraint on (user_id, trigger_type, date) or use idempotency keys
6. **Historical Data Migration** - If implementing on existing platform, ensure backward compatibility

## Implementation Notes

### DO
- Store all NPS data with timestamps for trend analysis
- Implement server-side rate limiting (don't rely on client-side state)
- Evaluate triggers asynchronously via polling or event hooks (don't block user workflows)
  - **Note**: If project has Celery/RQ/background job system, use it; otherwise implement with periodic polling
- Add indexes on user_id and created_at for dashboard queries
- Validate score is between 0-10 on both frontend and backend
- Log survey dismissals for analytics (measure dismissal rate)
- Use chart libraries (ApexCharts/Chart.js) already in dependencies
- Follow Radix UI accessibility patterns for survey modal
- Add loading states for async submissions
- Implement proper error boundaries for survey component

### DON'T
- Don't show surveys during active deployments or critical operations
  - **Implementation**: Check deployment status endpoint or Redux state before showing survey
  - **Alternative**: Add a global "criticalOperation" flag in Redux that blocks surveys
- Don't persist incomplete surveys (only store completed submissions)
- Don't expose individual user responses in public APIs
- Don't hard-code trigger logic (make it configurable via admin settings)
- Don't use polling for real-time updates (implement on-demand refresh)
- Don't skip input validation (sanitize comment text)
- Don't forget to handle timezone differences in trend charts

## Development Environment

### Start Services

```bash
# Start database (if using Docker Compose)
docker-compose up -d

# Start backend (CLI service)
cd cli
python -m cli

# Start frontend (Web service)
cd web
npm run dev
```

### Service URLs
- Web Frontend: http://localhost:8000
- CLI Backend: http://localhost:8000 (API endpoints)

### Required Environment Variables
- `DATABASE_URL`: postgresql://dumont:dumont123@localhost:5432/dumont_cloud
- `DB_HOST`: localhost
- `DB_PORT`: 5432
- `DB_NAME`: dumont_cloud
- `APP_PORT`: 8000
- `DEBUG`: true
- `REDIS_URL`: redis://localhost:6379/0 (optional - for rate limiting cache; falls back to PostgreSQL if not set)

### Database Setup
```bash
# Run migrations to create NPS tables
cd cli
alembic upgrade head  # or equivalent migration command
```

## Success Criteria

The task is complete when:

1. [ ] NPS survey appears after first successful deployment (configurable trigger)
2. [ ] Survey shows 0-10 score buttons and optional comment textarea
3. [ ] User can dismiss survey; dismissed state persists for 30 days
4. [ ] Rate limiting prevents survey from appearing more than once per month
5. [ ] Survey data is stored in PostgreSQL with user_id, score, comment, timestamp
6. [ ] Admin dashboard displays NPS trend chart (line/bar chart)
7. [ ] Dashboard shows breakdown: Detractors (0-6), Passives (7-8), Promoters (9-10)
8. [ ] Detractor responses are highlighted/flagged in admin view
9. [ ] No console errors during survey interaction
10. [ ] Existing tests still pass
11. [ ] Backend API endpoints return proper status codes (200, 400, 500)
12. [ ] Survey modal is accessible (keyboard navigation, screen reader compatible)

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests

| Test | File | What to Verify |
|------|------|----------------|
| NPS score validation | `cli/tests/test_nps_service.py` | Score must be 0-10, reject invalid values |
| Rate limiting logic | `cli/tests/test_nps_service.py` | User cannot receive survey more than once per configured interval |
| Survey trigger conditions | `cli/tests/test_nps_service.py` | Triggers fire at correct events (first deployment, monthly, issue resolution) |
| Comment sanitization | `cli/tests/test_nps_service.py` | HTML/script tags are stripped from comment field |
| NPS category calculation | `cli/tests/test_nps_service.py` | Detractors (0-6), Passives (7-8), Promoters (9-10) correctly categorized |
| Frontend component rendering | `web/src/components/__tests__/NPSSurvey.test.jsx` | Survey renders 0-10 buttons, comment field, submit/dismiss buttons |

### Integration Tests

| Test | Services | What to Verify |
|------|----------|----------------|
| Submit NPS survey | web ↔ cli | POST /nps/submit returns 200, data persists in database |
| Fetch NPS trends | web ↔ cli | GET /nps/trends returns aggregated data for dashboard |
| Rate limit enforcement | web ↔ cli | Repeated survey requests are blocked within time window |
| Detractor flagging | web ↔ cli | Responses with score 0-6 are marked as detractors in database |

### End-to-End Tests

| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| First deployment survey | 1. Complete first deployment 2. Survey appears 3. Submit score 8 with comment | Survey submits successfully, doesn't reappear for 30 days |
| Dismiss survey | 1. Trigger survey 2. Click dismiss button | Survey closes, doesn't reappear for configured period |
| Detractor submission | 1. Submit score 3 with comment 2. Check admin dashboard | Response appears in detractors list with flag |
| Monthly survey trigger | 1. Wait 30 days (or mock time) 2. Survey appears 3. Submit | Survey triggers correctly after time interval |

### Browser Verification (if frontend)

| Page/Component | URL | Checks |
|----------------|-----|--------|
| NPS Survey Modal | `http://localhost:8000/` (triggered) | Modal opens, 0-10 buttons clickable, comment field accepts text, submit/dismiss work |
| Admin Dashboard | `http://localhost:8000/admin/nps` | Trend chart displays, detractor list shows flagged responses, date range filters work |

### Database Verification

| Check | Query/Command | Expected |
|-------|---------------|----------|
| NPS responses table exists | `SELECT * FROM nps_responses LIMIT 1;` | Table exists with columns: id, user_id, score, comment, trigger_type, created_at |
| Survey config table exists | `SELECT * FROM nps_survey_config LIMIT 1;` | Table exists with trigger configurations |
| User interaction tracking | `SELECT * FROM nps_user_interactions LIMIT 1;` | Table tracks dismissals and survey shown timestamps |
| Indexes created | `\d nps_responses` (PostgreSQL) | Indexes on user_id, created_at for performance |

### API Endpoint Verification

| Endpoint | Method | Expected Response |
|----------|--------|------------------|
| `/nps/submit` | POST | 200 OK with `{"status": "success", "id": <nps_id>}` |
| `/nps/trends` | GET | 200 OK with `{"scores": [...], "categories": {...}}` |
| `/nps/detractors` | GET | 200 OK with array of detractor responses |
| `/nps/should-show` | GET | 200 OK with `{"show": true/false, "reason": "..."}` |

### QA Sign-off Requirements
- [ ] All unit tests pass (pytest for backend, Jest for frontend)
- [ ] All integration tests pass (API contract verified)
- [ ] All E2E tests pass (Playwright tests for user flows)
- [ ] Browser verification complete (survey and dashboard work in Chrome, Firefox, Safari)
- [ ] Database schema verified (tables, indexes, constraints exist)
- [ ] API endpoints return correct status codes and data formats
- [ ] No regressions in existing functionality (deployments, issues workflows unaffected)
- [ ] Code follows established patterns (React/Redux, FastAPI, SQLAlchemy)
- [ ] No security vulnerabilities introduced (input sanitization, rate limiting)
- [ ] Accessibility verified (keyboard navigation, screen reader support)
- [ ] Rate limiting works as expected (surveys don't spam users)
- [ ] Performance acceptable (dashboard loads in <2s, survey submission <500ms)
