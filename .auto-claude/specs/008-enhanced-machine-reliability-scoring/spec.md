# Specification: Enhanced Machine Reliability Scoring

## Overview

This feature extends the existing machine blacklist system to include user-visible reliability scoring for GPU hosts on the Vast.ai platform. Users will see a 0-100 reliability score for each machine based on uptime percentage, interruption rate, and community ratings, with 30-day historical performance data. This addresses the pain point of variable machine quality and differentiates the platform from raw GPU marketplaces by surfacing quality metrics to help users make informed decisions, particularly for long-running training jobs.

## Workflow Type

**Type**: feature

**Rationale**: This is a new feature development that extends existing blacklist functionality with user-facing reliability metrics. It's not a bug fix, refactor, or greenfield project, but rather an enhancement to existing machine selection capabilities.

## Task Scope

### Services Involved
- **cli** (primary) - Python backend service that interfaces with Vast.ai API and manages machine data
- **web** (primary) - React frontend service that displays machine selection UI to users
- **PostgreSQL database** (integration) - Stores reliability metrics, historical performance data, and user ratings

### This Task Will:
- [x] Add reliability score calculation (0-100 scale) based on multiple factors
- [x] Track and store 30-day historical uptime and interruption data per machine
- [x] Implement user rating collection and aggregation system
- [x] Display reliability scores in machine selection UI
- [x] Add auto-sort capability by reliability score
- [x] Implement auto-exclusion of machines below reliability threshold with user override
- [x] Create API endpoints for reliability data retrieval and user rating submission

### Out of Scope:
- Modifying existing blacklist functionality (only extending it)
- Real-time machine monitoring infrastructure (will use existing telemetry)
- Changing Vast.ai API integration patterns
- Adding cost optimization features
- Implementing machine performance benchmarking

## Service Context

### cli (Python Backend)

**Tech Stack:**
- Language: Python
- Framework: FastAPI (inferred from test-server.py pattern)
- Database: PostgreSQL via SQLAlchemy (inferred)
- Package manager: pip

**Entry Point:** `cli/__main__.py`

**How to Run:**
```bash
cd cli
python -m cli
```

**Port:** 8000 (APP_PORT from .env)

**Key Integration Points:**
- Vast.ai API integration via `VAST_API_KEY`
- Database connection via `DATABASE_URL`
- Redis for caching via `REDIS_URL`

### web (React Frontend)

**Tech Stack:**
- Language: JavaScript/JSX
- Framework: React
- Build Tool: Vite
- State Management: Redux (@reduxjs/toolkit)
- Styling: Tailwind CSS
- UI Components: Radix UI

**Entry Point:** `web/src/App.jsx`

**How to Run:**
```bash
cd web
npm run dev
```

**Port:** 8000 (default_port)

**Key Integration Points:**
- Consumes CLI API endpoints
- Redux store for state management
- Radix UI components for consistent UI patterns

### PostgreSQL Database

**Connection:**
- URL: `postgresql://dumont:dumont123@localhost:5432/dumont_cloud`
- Host: localhost:5432
- Database: dumont_cloud

## Files to Modify

**Note:** Context gathering phase did not identify specific files. Implementation will require codebase exploration to locate:

| File Pattern | Service | What to Change |
|-------------|---------|---------------|
| `cli/models/*.py` or `cli/db/models.py` | cli | Add database models for machine reliability metrics, historical data, and user ratings |
| `cli/api/routes/*.py` or `cli/routes/*.py` | cli | Add API endpoints for reliability scores, historical data, and rating submission |
| `cli/services/*.py` or `cli/utils/*.py` | cli | Add reliability score calculation logic and data aggregation service |
| `web/src/components/**/MachineList*.jsx` | web | Update machine list component to display reliability scores |
| `web/src/store/**/machineSlice.js` or similar | web | Add Redux state management for reliability data and sorting preferences |
| `web/src/api/*.js` or `web/src/services/*.js` | web | Add API client methods for fetching reliability data and submitting ratings |

## Files to Reference

**Note:** Context gathering phase did not identify specific reference files. Implementation should follow patterns from:

| File Pattern | Pattern to Copy |
|-------------|----------------|
| Existing blacklist implementation | Machine filtering and user preference storage patterns |
| Existing Vast.ai API integration | API data fetching and caching patterns |
| Existing Redux slices in web/src/store/ | State management patterns for machine data |
| Existing database models in cli/models/ | SQLAlchemy model definition patterns |
| Existing API routes in cli/api/ or cli/routes/ | FastAPI route definition and validation patterns |

## Patterns to Follow

### Database Model Pattern (SQLAlchemy)

Expected pattern based on PostgreSQL usage:

```python
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

class MachineReliability(Base):
    __tablename__ = 'machine_reliability'

    id = Column(Integer, primary_key=True)
    machine_id = Column(String, unique=True, nullable=False, index=True)
    reliability_score = Column(Float, nullable=False)  # 0-100
    uptime_percentage = Column(Float, nullable=False)
    interruption_rate = Column(Float, nullable=False)
    total_ratings = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    last_calculated = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
```

**Key Points:**
- Use SQLAlchemy declarative base
- Index machine_id for fast lookups
- Store pre-calculated scores for performance
- Track calculation timestamp for cache invalidation

### Redux State Management Pattern

Expected pattern based on @reduxjs/toolkit:

```javascript
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const fetchMachineReliability = createAsyncThunk(
  'machines/fetchReliability',
  async (machineIds) => {
    const response = await api.getMachineReliability(machineIds);
    return response.data;
  }
);

const machineSlice = createSlice({
  name: 'machines',
  initialState: {
    reliabilityData: {},
    sortByReliability: false,
    reliabilityThreshold: 70,
    excludeBelowThreshold: true,
    loading: false
  },
  reducers: {
    toggleReliabilitySort: (state) => {
      state.sortByReliability = !state.sortByReliability;
    },
    setReliabilityThreshold: (state, action) => {
      state.reliabilityThreshold = action.payload;
    },
    toggleThresholdExclusion: (state) => {
      state.excludeBelowThreshold = !state.excludeBelowThreshold;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMachineReliability.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchMachineReliability.fulfilled, (state, action) => {
        state.reliabilityData = action.payload;
        state.loading = false;
      });
  }
});
```

**Key Points:**
- Use createAsyncThunk for API calls
- Store user preferences in slice state
- Use builder pattern for async reducers
- Maintain loading states for UI feedback

### FastAPI Endpoint Pattern

Expected pattern based on existing FastAPI usage:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from . import schemas, dependencies

router = APIRouter(prefix="/api/reliability", tags=["reliability"])

@router.get("/machines/{machine_id}", response_model=schemas.MachineReliability)
async def get_machine_reliability(
    machine_id: str,
    db: Session = Depends(dependencies.get_db)
):
    """Get reliability score and metrics for a specific machine."""
    reliability = db.query(models.MachineReliability).filter(
        models.MachineReliability.machine_id == machine_id
    ).first()

    if not reliability:
        raise HTTPException(status_code=404, detail="Machine reliability data not found")

    return reliability

@router.post("/machines/{machine_id}/rate", response_model=schemas.RatingResponse)
async def rate_machine(
    machine_id: str,
    rating: schemas.MachineRating,
    db: Session = Depends(dependencies.get_db)
):
    """Submit user rating for a machine."""
    # Implementation for rating submission
    pass
```

**Key Points:**
- Use APIRouter for route organization
- Dependency injection for database sessions
- Pydantic schemas for request/response validation
- Proper HTTP status codes and error handling

## Requirements

### Functional Requirements

1. **Reliability Score Display**
   - Description: Display a 0-100 reliability score for each available machine in the machine selection interface
   - Acceptance: User can see reliability score badge/indicator next to each machine listing

2. **Score Calculation**
   - Description: Calculate reliability score based on uptime percentage (40% weight), interruption rate (40% weight), and community ratings (20% weight)
   - Acceptance: Score accurately reflects the weighted combination of all three factors

3. **Historical Data Visibility**
   - Description: Show 30-day performance history including uptime trends and interruption events
   - Acceptance: User can view a chart or table showing daily uptime percentages and interruption counts for the past 30 days

4. **Auto-Sort Capability**
   - Description: Provide toggle to sort machine list by reliability score (high to low)
   - Acceptance: Clicking sort toggle reorders machines by reliability score, with visual indicator of sort state

5. **Smart Filtering with Override**
   - Description: Automatically exclude machines below reliability threshold (default 70) with option to disable filtering
   - Acceptance:
     - Machines below threshold are hidden by default
     - User can toggle "Show all machines" to override filter
     - Threshold value is configurable in user preferences

6. **User Rating Submission**
   - Description: Allow users to rate machines they've used (1-5 stars)
   - Acceptance:
     - Rating interface appears for machines user has rented
     - Rating successfully submits and updates aggregated score
     - User can see their submitted rating

### Edge Cases

1. **New Machines Without History** - Display "Insufficient Data" badge instead of score for machines with <7 days of data
2. **Zero Ratings** - Use only uptime/interruption data (reweight to 50/50) when no community ratings exist
3. **Stale Data** - Show warning indicator if reliability data is >24 hours old
4. **Database Unavailable** - Gracefully degrade to show machines without reliability data rather than failing
5. **API Rate Limiting** - Cache reliability data with 1-hour TTL to reduce database load
6. **Concurrent Rating Submissions** - Use database locks or atomic operations to prevent race conditions in rating aggregation

## Implementation Notes

### DO
- Follow existing database migration patterns for schema changes
- Reuse existing Vast.ai API client patterns for machine data fetching
- Use existing Redux patterns for state management in web service
- Leverage existing caching infrastructure (Redis) for reliability score caching
- Follow established FastAPI route structure for new endpoints
- Implement database indexes on machine_id for performance
- Add comprehensive logging for score calculation process
- Create Pydantic schemas for all API request/response models

### DON'T
- Create a separate machine filtering system - extend the existing blacklist infrastructure
- Bypass existing authentication/authorization patterns for API endpoints
- Store raw telemetry data in main database - aggregate before storing
- Calculate scores on every request - use pre-calculated cached values
- Modify existing Vast.ai API integration - work with existing data
- Add frontend dependencies without checking existing UI component libraries (Radix UI)

## Development Environment

### Start Services

```bash
# Start PostgreSQL and Redis (via Docker Compose)
docker-compose up -d

# Start CLI backend
cd cli
python -m cli

# Start web frontend (separate terminal)
cd web
npm run dev
```

### Service URLs
- CLI Backend: http://localhost:8000 (API endpoints)
- Web Frontend: http://localhost:8000 (Dev server may use different port like 5173 for Vite)
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Required Environment Variables
- `DATABASE_URL`: postgresql://dumont:dumont123@localhost:5432/dumont_cloud
- `REDIS_URL`: redis://localhost:6379/0
- `VAST_API_KEY`: API key for Vast.ai integration (required for machine data)
- `APP_HOST`: 0.0.0.0
- `APP_PORT`: 8000
- `DEBUG`: true (for development)

## Success Criteria

The task is complete when:

1. [x] Reliability scores (0-100) are displayed for all machines in the selection UI
2. [x] Score breakdown shows uptime %, interruption rate, and average rating
3. [x] 30-day historical performance chart is accessible via expand/detail view
4. [x] Auto-sort toggle correctly reorders machines by reliability score
5. [x] Smart filtering excludes machines below threshold (default 70) by default
6. [x] User can override threshold exclusion with "Show all machines" toggle
7. [x] User can submit ratings (1-5 stars) for machines they've used
8. [x] Submitted ratings are reflected in aggregated community rating score
9. [x] No console errors in browser or backend logs
10. [x] Existing tests still pass (no regressions)
11. [x] New functionality verified via browser for web UI
12. [x] API endpoints verified via curl/Postman for backend
13. [x] Database migrations execute successfully
14. [x] Redis caching reduces database queries for reliability data

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| Reliability Score Calculation | `cli/tests/test_reliability_service.py` | Verify weighted score calculation (40% uptime, 40% interruption, 20% rating) returns correct 0-100 value |
| Edge Case: Zero Ratings | `cli/tests/test_reliability_service.py` | Verify score calculation with no ratings uses 50/50 uptime/interruption weighting |
| Edge Case: Insufficient Data | `cli/tests/test_reliability_service.py` | Verify machines with <7 days data return None or special indicator |
| Rating Aggregation | `cli/tests/test_reliability_service.py` | Verify new rating correctly updates average_rating and total_ratings |
| Database Model Validation | `cli/tests/test_models.py` | Verify MachineReliability model creates/updates records correctly |
| API Input Validation | `cli/tests/test_reliability_routes.py` | Verify API rejects invalid rating values (outside 1-5 range) |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| Reliability Data Fetch | web ↔ cli | Verify web can fetch reliability data from API and populate Redux store |
| Rating Submission Flow | web ↔ cli ↔ database | Verify rating submitted from UI persists to database and updates aggregated score |
| Caching Behavior | cli ↔ Redis | Verify reliability data cached in Redis with 1-hour TTL |
| Threshold Filtering | web ↔ cli | Verify machines below threshold excluded from results when filter enabled |
| Sort Functionality | web ↔ cli | Verify API returns machines sorted by reliability when sort param provided |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Machine Selection with Reliability | 1. Navigate to machine selection page 2. View machine list | Reliability scores displayed for each machine with badge/indicator |
| Historical Data View | 1. Click on machine 2. Expand reliability details | 30-day uptime chart and interruption history visible |
| Enable Auto-Sort | 1. Toggle "Sort by Reliability" switch | Machine list reorders with highest reliability scores at top |
| Smart Filtering | 1. Set threshold to 70 2. Enable auto-exclude | Machines with scores <70 hidden from list |
| Override Filtering | 1. With filtering enabled 2. Toggle "Show all machines" | Previously hidden low-reliability machines now visible |
| Submit Rating | 1. Select used machine 2. Submit 4-star rating 3. Refresh | Rating appears in machine's community rating, average updates |

### Browser Verification (Frontend)
| Page/Component | URL | Checks |
|----------------|-----|--------|
| Machine Selection Page | `http://localhost:8000/machines` or `/select` | - Reliability badges visible on each machine<br>- Scores display as 0-100 numbers<br>- Color coding (green >80, yellow 60-80, red <60) |
| Machine Detail View | Click on specific machine | - 30-day historical chart renders<br>- Uptime %, interruption rate, rating count visible<br>- Chart shows daily data points |
| Sort Controls | Machine list page header | - Toggle switch labeled "Sort by Reliability"<br>- Toggle state persists on page refresh |
| Filter Controls | Machine list page header | - Threshold slider (0-100 with default 70)<br>- "Auto-exclude" checkbox<br>- "Show all" override toggle |
| Rating Component | Used machine detail | - Star rating component (1-5 stars)<br>- Submit button enables only when rating selected<br>- Success message after submission |

### Database Verification
| Check | Query/Command | Expected |
|-------|---------------|----------|
| Migration Applied | `psql -d dumont_cloud -c "\dt machine_*"` | Tables: machine_reliability, machine_historical_data, machine_ratings exist |
| Sample Data | `SELECT * FROM machine_reliability LIMIT 5;` | Records exist with reliability_score between 0-100 |
| Index Created | `SELECT indexname FROM pg_indexes WHERE tablename='machine_reliability';` | Index on machine_id exists |
| Rating Constraints | `\d machine_ratings` | rating column has CHECK constraint (rating >= 1 AND rating <= 5) |
| Historical Data Retention | `SELECT COUNT(*) FROM machine_historical_data WHERE created_at < NOW() - INTERVAL '30 days';` | Zero records (30-day retention policy enforced) |

### API Verification
| Endpoint | Method | Test | Expected |
|----------|--------|------|----------|
| `/api/reliability/machines/{machine_id}` | GET | Fetch existing machine | 200 OK with reliability_score, uptime_percentage, interruption_rate, average_rating |
| `/api/reliability/machines/{machine_id}` | GET | Fetch non-existent machine | 404 Not Found with error message |
| `/api/reliability/machines/{machine_id}/history` | GET | Fetch 30-day history | 200 OK with array of daily metrics (max 30 entries) |
| `/api/reliability/machines/{machine_id}/rate` | POST | Submit valid rating (1-5) | 200 OK with updated average_rating |
| `/api/reliability/machines/{machine_id}/rate` | POST | Submit invalid rating (6) | 422 Unprocessable Entity with validation error |
| `/api/reliability/machines` | GET | List all with sort=reliability | 200 OK with machines sorted descending by reliability_score |
| `/api/reliability/machines` | GET | List with min_score=70 | 200 OK with only machines having reliability_score >= 70 |

### Performance Verification
| Metric | Test | Threshold |
|--------|------|-----------|
| API Response Time | GET `/api/reliability/machines` (100 machines) | < 500ms (with Redis caching) |
| Database Query Time | SELECT with machine_id index | < 50ms |
| Frontend Rendering | Machine list with 100 items + reliability scores | < 2 seconds initial render |
| Cache Hit Rate | Monitor Redis cache hits for reliability data | > 80% after warm-up |

### QA Sign-off Requirements
- [ ] All unit tests pass (minimum 6 new tests)
- [ ] All integration tests pass (minimum 5 tests)
- [ ] All E2E tests pass (minimum 6 user flows)
- [ ] Browser verification complete (all 5 components functional)
- [ ] Database verification complete (schema, constraints, indexes valid)
- [ ] API verification complete (all 7 endpoint tests pass)
- [ ] Performance metrics meet thresholds
- [ ] No regressions in existing machine selection functionality
- [ ] Code follows established patterns (SQLAlchemy, FastAPI, Redux)
- [ ] No security vulnerabilities (SQL injection, XSS in rating inputs)
- [ ] Error handling graceful (API failures don't crash UI)
- [ ] Accessibility: Reliability scores readable by screen readers
- [ ] Mobile responsiveness: Reliability UI functional on mobile viewports
