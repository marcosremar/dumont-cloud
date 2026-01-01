# Specification: Cost Prediction Dashboard

## Overview

This feature builds a predictive analytics dashboard that forecasts GPU spot pricing and total workload costs for the next 7 days using machine learning. It extends the existing `PricePredictionService` to help users plan budgets, optimize job timing, and receive proactive alerts when forecasted spending exceeds configured thresholds. This addresses a critical gap in budget planning capabilities and differentiates Dumont Cloud from competitors who lack cost forecasting features.

## Workflow Type

**Type**: feature

**Rationale**: This is a new capability that adds ML-powered cost forecasting, optimal timing recommendations, budget alerts, and calendar integration. It's not a refactor, bugfix, or investigation—it's net-new functionality built on top of existing infrastructure.

## Task Scope

### Services Involved
- **cli** (primary) - Backend API service hosting ML forecasting endpoints and alert logic
- **web** (primary) - Frontend React dashboard displaying forecasts and recommendations
- **tests** (integration) - E2E tests validating forecast flows

### This Task Will:
- [ ] Extend `PricePredictionService` to generate 7-day cost forecasts based on usage patterns
- [ ] Create new API endpoints for cost forecasting in `src/routers/spot_instances.py`
- [ ] Build React dashboard component with Chart.js visualization for forecasted costs
- [ ] Implement optimal timing recommendation algorithm for planned jobs
- [ ] Add budget alert system using FastAPI BackgroundTasks + SMTP
- [ ] Create historical accuracy tracking for ML prediction validation
- [ ] Integrate Google Calendar API for scheduled workload suggestions

### Out of Scope:
- Real-time alerting (uses periodic background tasks instead)
- Multi-user budget sharing (individual user budgets only)
- Custom ML model retraining UI (uses existing model training pipeline)
- Mobile-specific UI (responsive web only)

## Service Context

### cli

**Tech Stack:**
- Language: Python
- Framework: FastAPI (inferred from test-server.py)
- Key directories: utils/, tests/
- ML Stack: scikit-learn 1.8.0, google-api-python-client 2.187.0

**Entry Point:** `__main__.py`

**How to Run:**
```bash
cd cli
pip install -r requirements.txt
python -m cli
```

**Port:** 8000 (from APP_PORT env var)

**Key Services to Extend:**
- `src/services/price_prediction_service.py` - Existing ML forecasting service
- `src/routers/spot_instances.py` - REST API router for spot instance operations

### web

**Tech Stack:**
- Language: JavaScript
- Framework: React 18 + Vite
- State Management: Redux (@reduxjs/toolkit)
- Styling: Tailwind CSS + Radix UI components
- Charts: Chart.js 4.5.1

**Entry Point:** `src/App.jsx`

**How to Run:**
```bash
cd web
npm install
npm run dev
```

**Port:** 8000 (default_port from project_index)

**Service URLs:**
- Web Frontend: http://localhost:8000
- Backend API: http://localhost:8000 (proxied through Vite)

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `cli/src/services/price_prediction_service.py` | cli | Add `forecast_costs_7day()` method to generate multi-day cost predictions |
| `cli/src/routers/spot_instances.py` | cli | Add `/cost-forecast`, `/optimal-timing`, `/budget-alerts` endpoints |
| `cli/requirements.txt` | cli | Verify scikit-learn, google-api-python-client (already present) |
| `web/src/components/spot/SpotPrediction.jsx` | web | Extract Chart.js patterns as reference for new cost forecast chart |
| `web/src/components/savings/SavingsHistoryGraph.jsx` | web | Reference for multi-dataset chart patterns |
| `web/package.json` | web | Verify Chart.js 4.5.1 (already installed, no changes needed) |
| `.env` | Infrastructure | Add SMTP config vars, Google Calendar OAuth credentials |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `web/src/components/spot/SpotPrediction.jsx` | Chart.js registration, tooltip formatting, dark theme colors |
| `web/src/components/savings/SavingsHistoryGraph.jsx` | Multi-dataset line charts, area fills, time-series data handling |
| `cli/src/services/price_prediction_service.py` | RandomForestRegressor usage, StandardScaler persistence, feature engineering |

## Patterns to Follow

### Chart.js Registration (React Frontend)

From `web/src/components/spot/SpotPrediction.jsx`:

**Key Points:**
- Register all required Chart.js components before rendering
- Use `CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler`
- Apply `fill: true` on datasets for gradient area charts
- Custom tooltip callbacks for currency formatting: `$X.XX/hour`
- Dark theme must match Tailwind CSS variables (use `bg-gray-800`, `text-gray-100`)

### ML Feature Engineering

From `cli/src/services/price_prediction_service.py`:

**Key Points:**
- Features: hour-of-day, day-of-week, cyclical encoding (sin/cos transforms), weekend boolean flag
- Requires minimum 50 historical data points to train
- **CRITICAL**: Save StandardScaler with model using pickle for consistent predictions
- Use `RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)`
- Return predictions with confidence intervals using `std` from tree estimators

### Google Calendar OAuth Flow

**Pattern:**
```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# 1. Load credentials from environment
creds = Credentials.from_authorized_user_file(
    os.getenv('GOOGLE_CALENDAR_TOKEN_JSON'),
    scopes=[
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events'
    ]
)

# 2. Build service
service = build('calendar', 'v3', credentials=creds)

# 3. Fetch events
events = service.events().list(
    calendarId='primary',
    timeMin=datetime.utcnow().isoformat() + 'Z',
    maxResults=10,
    singleEvents=True,
    orderBy='startTime'
).execute()
```

**Key Points:**
- Scopes: `calendar.readonly` (read) + `calendar.events` (write for suggestions)
- Store refresh token securely in database
- Handle timezone conversions (user TZ → UTC)
- Rate limit: 1M queries/day (far above needs)

### Background Task Alerts (FastAPI)

**Pattern:**
```python
from fastapi import BackgroundTasks
import smtplib
from email.mime.text import MIMEText

async def send_budget_alert(email: str, forecast: dict):
    msg = MIMEText(f"Forecasted cost ${forecast['total']} exceeds threshold")
    msg['Subject'] = 'Budget Alert'
    msg['From'] = os.getenv('ALERT_EMAIL_FROM')
    msg['To'] = email

    with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT'))) as server:
        server.starttls()
        server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
        server.send_message(msg)

@router.post("/check-budget")
async def check_budget(background_tasks: BackgroundTasks):
    background_tasks.add_task(send_budget_alert, user.email, forecast)
```

**Key Points:**
- Use `BackgroundTasks` to avoid blocking response
- Check forecasts vs thresholds periodically (cron or scheduled task)
- Email template includes: predicted cost, threshold, time range, optimization recommendations

## Requirements

### Functional Requirements

1. **7-Day Cost Forecasting**
   - Description: Generate hourly spot price predictions for next 168 hours (7 days), aggregate into daily cost estimates based on user's typical usage patterns
   - Acceptance: API returns `{day: date, forecasted_cost: float, confidence_interval: [lower, upper]}[]` for 7 days

2. **Optimal Timing Recommendations**
   - Description: Analyze forecasted price curve and suggest best time windows to run planned jobs to minimize costs
   - Acceptance: Given job duration and requirements, API returns recommended start times ranked by cost savings

3. **Budget Alert System**
   - Description: Compare 7-day forecast against user-configured budget threshold; send email alert if forecasted spending exceeds limit
   - Acceptance: Users receive email when forecast > threshold, with breakdown and recommendations

4. **Historical Accuracy Tracking**
   - Description: Store forecasted vs actual prices to calculate MAPE (Mean Absolute Percentage Error) and display accuracy metrics
   - Acceptance: Dashboard shows "Prediction accuracy: X% MAPE over last 30 days"

5. **Calendar Integration**
   - Description: Fetch user's Google Calendar events, identify compute-intensive scheduled tasks, suggest optimal timing adjustments
   - Acceptance: Dashboard displays calendar events overlaid on cost forecast chart with move suggestions

### Edge Cases

1. **Insufficient Historical Data** - If < 50 data points exist, return error with message "Need at least 50 hours of price history to generate forecast"
2. **Calendar OAuth Expiry** - Gracefully degrade to manual scheduling if refresh token invalid; show "Reconnect Calendar" prompt
3. **SMTP Failure** - Log alert failure but don't block API response; retry alerts on next scheduled check
4. **Extreme Price Spikes** - Cap confidence interval display at 3σ to avoid confusing UI, flag outliers in tooltip
5. **Timezone Mismatches** - Always store predictions in UTC, convert to user's timezone only in frontend display

## Implementation Notes

### DO
- Follow the Chart.js registration pattern in `SpotPrediction.jsx` for rendering forecast visualizations
- Reuse existing `RandomForestRegressor` from `PricePredictionService` for 7-day extension
- Use Radix UI components (`@radix-ui/react-slider`, `@radix-ui/react-switch`) for budget threshold controls
- Store StandardScaler and model artifacts in same directory as existing price prediction models
- Leverage Redux state management patterns from existing `web/src` components
- Use FastAPI's `BackgroundTasks` for email alerts to avoid blocking requests
- Add comprehensive error handling for Google Calendar API rate limits and OAuth failures
- **Calendar UI Decision**: Build calendar visualization using existing Radix UI components (no new dependencies) instead of FullCalendar to minimize bundle size and maintain design consistency. Display events as timeline overlays on the cost forecast chart rather than a separate calendar view.

### DON'T
- Create new chart library dependency when Chart.js 4.5.1 is already installed
- Train new ML model architecture; extend existing `RandomForestRegressor` approach
- Implement custom email queue when FastAPI's BackgroundTasks handles async ops
- Hardcode SMTP credentials; use environment variables from `.env`
- Skip StandardScaler persistence (causes prediction drift)
- Block API responses while sending alert emails
- Use regular Gmail password for SMTP; Gmail requires app-specific passwords (generate at https://myaccount.google.com/apppasswords)

## Development Environment

### Start Services

```bash
# Terminal 1: Start backend
cd cli
pip install -r requirements.txt
python -m cli

# Terminal 2: Start frontend
cd web
npm install
npm run dev

# Terminal 3: Start PostgreSQL + Redis (if needed)
docker-compose up -d
```

### Service URLs
- Web Frontend: http://localhost:8000
- Backend API: http://localhost:8000/docs (Swagger UI)
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Required Environment Variables

Add to `.env`:

```bash
# Existing variables (no changes)
DATABASE_URL=postgresql://dumont:dumont123@localhost:5432/dumont_cloud
APP_PORT=8000

# New variables for this feature
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@dumontcloud.com
SMTP_PASSWORD=<your-smtp-password>
ALERT_EMAIL_FROM=alerts@dumontcloud.com

# Google Calendar OAuth
GOOGLE_CALENDAR_CREDENTIALS_JSON=/path/to/credentials.json
GOOGLE_CALENDAR_TOKEN_JSON=/path/to/token.json
```

## Success Criteria

The task is complete when:

1. [ ] 7-day cost forecast displays in dashboard with Chart.js visualization matching design patterns from `SpotPrediction.jsx`
2. [ ] API endpoint `/api/cost-forecast` returns 7-day predictions with confidence intervals
3. [ ] Optimal timing recommendations visible when user inputs planned job parameters
4. [ ] Budget alert email sent when forecasted cost exceeds user-configured threshold
5. [ ] Historical accuracy (MAPE) displayed on dashboard with 30-day rolling window
6. [ ] Google Calendar integration shows scheduled events on forecast timeline (with graceful degradation if OAuth fails)
7. [ ] No console errors in browser DevTools
8. [ ] Existing unit tests in `cli/tests/` and `web/` still pass
9. [ ] New functionality verified via manual testing in browser at http://localhost:8000

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| `test_forecast_costs_7day` | `cli/tests/test_price_prediction_service.py` | Verify 7-day forecast returns 168 hourly predictions with confidence intervals |
| `test_forecast_insufficient_data` | `cli/tests/test_price_prediction_service.py` | Verify error raised when < 50 historical data points |
| `test_optimal_timing_calculation` | `cli/tests/test_price_prediction_service.py` | Verify optimal timing recommends lowest-cost windows |
| `test_budget_alert_threshold` | `cli/tests/test_routers.py` | Verify alert triggered when forecast > threshold |
| `test_calendar_oauth_failure_handling` | `cli/tests/test_calendar_service.py` | Verify graceful degradation when OAuth token invalid |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| `test_cost_forecast_api_e2e` | cli ↔ PostgreSQL | POST /api/cost-forecast returns valid 7-day forecast JSON |
| `test_budget_alert_smtp_integration` | cli ↔ SMTP | Email sent to user when forecast exceeds threshold |
| `test_calendar_fetch_events` | cli ↔ Google Calendar API | Fetch events for next 7 days and return scheduling suggestions |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| View Cost Forecast Dashboard | 1. Navigate to /dashboard/cost-forecast 2. Wait for chart render | Chart displays 7-day forecast with confidence bands |
| Configure Budget Alert | 1. Open budget settings 2. Set threshold to $100 3. Save | Alert email received when forecast > $100 |
| Calendar Integration Flow | 1. Connect Google Calendar 2. View scheduled events on timeline 3. Click optimization suggestion | Calendar events overlay on forecast, move suggestions shown |
| Optimal Timing Recommendation | 1. Input job: 8 hours GPU 2. Click "Find Best Time" | Top 3 time windows displayed with cost savings |

### Browser Verification (if frontend)
| Page/Component | URL | Checks |
|----------------|-----|--------|
| Cost Forecast Dashboard | `http://localhost:8000/dashboard/cost-forecast` | Chart.js renders with 7-day data, dark theme colors match design |
| Budget Settings Modal | `http://localhost:8000/settings/budget` | Radix UI Slider sets threshold, Switch enables/disables alerts |
| Calendar Integration Panel | `http://localhost:8000/dashboard/cost-forecast#calendar` | Google Calendar events visible if OAuth connected, "Reconnect" button if expired |
| Accuracy Tracker Widget | `http://localhost:8000/dashboard/cost-forecast#accuracy` | MAPE percentage displays (e.g., "94.3% accurate over 30 days") |

### Database Verification (if applicable)
| Check | Query/Command | Expected |
|-------|---------------|----------|
| Forecasts table exists | `psql -d dumont_cloud -c "\dt cost_forecasts"` | Table with columns: id, user_id, timestamp, forecasted_prices JSON, created_at |
| Budget alerts table exists | `psql -d dumont_cloud -c "\dt budget_alerts"` | Table with columns: id, user_id, threshold, email, enabled, created_at |
| Accuracy metrics stored | `SELECT * FROM prediction_accuracy LIMIT 5` | Rows with forecasted_price, actual_price, absolute_percentage_error |

### QA Sign-off Requirements
- [ ] All unit tests pass (`pytest cli/tests/test_price_prediction_service.py`)
- [ ] All integration tests pass (API endpoints return valid data)
- [ ] All E2E tests pass (browser flows complete successfully)
- [ ] Browser verification complete (UI renders correctly, interactions work)
- [ ] Database migrations applied (new tables exist with correct schemas)
- [ ] No regressions in existing spot instance features
- [ ] Code follows established patterns (Chart.js usage, Redux state, FastAPI routes)
- [ ] No security vulnerabilities (SMTP creds in env vars, Calendar OAuth secure)
- [ ] Error handling validated (insufficient data, OAuth failures, SMTP errors)
- [ ] Performance acceptable (forecast generation < 2 seconds, chart renders < 500ms)
