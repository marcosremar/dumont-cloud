# Specification: Multi-Currency Pricing System

## Overview

Implement a comprehensive multi-currency pricing system to support international expansion, enabling users to view prices and complete transactions in USD, EUR, GBP, and BRL. This feature reduces friction for international users by eliminating mental currency conversion overhead and enables the platform to expand into European and Brazilian markets. The system will fetch daily exchange rates, store user currency preferences, and display transparent conversion rates at checkout.

## Workflow Type

**Type**: feature

**Rationale**: This introduces new functionality to the platform (multi-currency support) rather than fixing bugs or refactoring existing code. It requires new database models, API endpoints, scheduled tasks, and frontend components to enable international pricing capabilities.

## Task Scope

### Services Involved
- **cli** (primary) - Backend API service that will handle exchange rate fetching, storage, currency conversion logic, and provide pricing endpoints
- **web** (primary) - React frontend that will display prices in user-selected currencies and show conversion rates
- **Database** (integration) - PostgreSQL for storing exchange rates, currency preferences, and pricing data

### This Task Will:
- [ ] Integrate external exchange rate API (exchangerate-api.io or similar) for daily rate updates
- [ ] Create database models for storing exchange rates and user currency preferences
- [ ] Implement scheduled task (APScheduler) to fetch and update exchange rates daily
- [ ] Build backend API endpoints for currency selection and price conversion
- [ ] Create frontend currency selector component with USD, EUR, GBP, BRL options
- [ ] Update all pricing displays across the web interface to show user-selected currency
- [ ] Display transparent conversion rates at checkout
- [ ] Add currency formatting using Babel (backend) and Dinero.js (frontend)
- [ ] Implement graceful fallback to cached rates if API fails

### Out of Scope:
- **Payment processor integration changes** - Note: Original requirement includes "billing in local currency where possible" but this Phase 1 focuses on **display-only** multi-currency pricing. Actual billing/charging in non-USD currencies requires payment processor configuration and is deferred to Phase 2. Users will see prices in their preferred currency but be charged in USD.
- Historical exchange rate tracking and analytics
- Automatic currency detection based on user location
- Support for cryptocurrencies
- Currency conversion for existing subscriptions/invoices
- Multi-currency refund handling

## Service Context

**⚠️ CRITICAL: Verify Before Implementation**

The following items from research were not verified during spec creation. **Must be confirmed** before starting implementation:

1. **Payment Processor Integration**: What payment gateway is currently integrated (Stripe, PayPal, other)? Impacts billing strategy.
2. **Existing i18n Infrastructure**: Does the project already have react-intl, i18next, or other internationalization libraries? Affects frontend formatting choice.
3. **Product Pricing Model**: How are prices currently stored in the database? What tables/schema exist? Determines conversion approach.
4. **Existing Scheduled Jobs**: Are there already APScheduler, Celery, or cron tasks running? Affects scheduler setup.

**Action Required**: Search codebase for these items in implementation phase or adjust spec if discovered.

---

### cli (Backend API Service)

**Tech Stack:**
- Language: Python
- Framework: FastAPI (inferred from test-server.py patterns)
- Database: PostgreSQL (dumont_cloud)
- Cache: Redis
- Testing: pytest

**Key directories:**
- `utils/` - Utility functions
- `tests/` - Test files

**Entry Point:** `__main__.py`

**How to Run:**
```bash
cd cli
python -m cli  # or python __main__.py
```

**Port:** 8000 (APP_PORT from environment)

**Dependencies to Add:**
- `babel>=2.12.0` - Currency formatting
- `apscheduler>=3.10.0` - Scheduled rate updates
- `httpx` or `requests` - Exchange rate API calls

### web (React Frontend)

**Tech Stack:**
- Language: JavaScript
- Framework: React
- Build Tool: Vite
- Styling: Tailwind CSS
- State Management: Redux (@reduxjs/toolkit)
- Testing: Playwright

**Key directories:**
- `src/` - Source code
- `src/components/` - React components

**Entry Point:** `src/App.jsx`

**How to Run:**
```bash
cd web
npm run dev
```

**Port:** 8000

**Dependencies to Add:**
- `dinero.js@^2.0.0` - Money calculations
- `@dinero.js/currencies` - Currency definitions

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `cli/models.py` (or similar) | cli | Add `ExchangeRate` and `UserCurrencyPreference` models |
| `cli/api/pricing.py` (new) | cli | Create pricing endpoints with currency conversion |
| `cli/api/currency.py` (new) | cli | Create currency selection endpoints |
| `cli/services/exchange_rate.py` (new) | cli | Implement exchange rate fetching and caching logic |
| `cli/scheduler.py` (new) | cli | Setup APScheduler for daily rate updates |
| `cli/__main__.py` | cli | Initialize scheduler on app startup |
| `web/src/components/CurrencySelector.jsx` (new) | web | Create currency dropdown component |
| `web/src/store/currencySlice.js` (new) | web | Add Redux slice for currency state |
| `web/src/utils/formatCurrency.js` (new) | web | Currency formatting utilities |
| `web/src/components/PriceDisplay.jsx` (modify/new) | web | Update/create component to show prices in selected currency |
| `.env` | infrastructure | Add `EXCHANGE_RATE_API_KEY` and `EXCHANGE_RATE_API_URL` |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| Existing Redux slices in `web/src/store/` | State management patterns for currency selection |
| Existing API route files in `cli/api/` | FastAPI route structure and error handling |
| Existing model files in `cli/models.py` or `cli/db/models.py` | SQLAlchemy/database model patterns |
| Existing components using Radix UI in `web/src/components/` | Dropdown/select component patterns |
| Existing utility files in `cli/utils/` | Utility function structure and error handling |

## Patterns to Follow

### Exchange Rate Model Pattern

```python
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Index
from datetime import datetime

class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'

    id = Column(Integer, primary_key=True)
    from_currency = Column(String(3), nullable=False)  # ISO 4217 codes
    to_currency = Column(String(3), nullable=False)
    rate = Column(Numeric(precision=18, scale=6), nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # NOTE: This design allows historical rates. To get latest rate: ORDER BY fetched_at DESC LIMIT 1
    # Index optimizes lookup of most recent rate for each currency pair
    # Alternative approach: Use single row per pair with ON CONFLICT UPDATE for simpler queries
    __table_args__ = (
        Index('idx_latest_rate', 'from_currency', 'to_currency', 'fetched_at'),
    )
```

**Key Points:**
- Use 3-character ISO 4217 currency codes (USD, EUR, GBP, BRL)
- Store rates with high precision (18,6) to avoid rounding errors
- Always include timestamp for rate freshness validation
- Store rates as base currency (USD) to other currencies for consistency

### APScheduler Integration Pattern

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

async def update_exchange_rates():
    """Fetch and update exchange rates from API"""
    # Implementation here
    pass

# Initialize in FastAPI startup event
@app.on_event("startup")
async def startup_event():
    scheduler.add_job(
        update_exchange_rates,
        CronTrigger(hour=0, minute=0),  # Run daily at midnight UTC
        id='update_exchange_rates',
        replace_existing=True
    )
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
```

**Key Points:**
- Use AsyncIOScheduler (runs in-process with FastAPI)
- Schedule daily updates at consistent time (midnight UTC)
- Use unique job IDs and replace_existing to prevent duplicates
- Always implement graceful shutdown

### Currency Formatting Pattern (Backend)

```python
from babel.numbers import format_currency

def format_price(amount: float, currency: str, locale: str = 'en_US') -> str:
    """
    Format price with proper currency symbol and locale

    Args:
        amount: Numeric price value
        currency: ISO 4217 currency code
        locale: Babel locale code (must match currency region)

    Returns:
        Formatted currency string
    """
    locale_mapping = {
        'USD': 'en_US',
        'EUR': 'de_DE',  # or 'fr_FR', 'es_ES'
        'GBP': 'en_GB',
        'BRL': 'pt_BR'
    }

    return format_currency(
        amount,
        currency,
        locale=locale_mapping.get(currency, 'en_US')
    )
```

**Key Points:**
- Locale must match currency region for correct formatting
- Babel is thread-safe for FastAPI concurrent requests
- Use consistent locale mapping across application

### Currency Display Pattern (Frontend)

```javascript
import { dinero, add, multiply, toDecimal } from 'dinero.js';
import { USD, EUR, GBP } from '@dinero.js/currencies';

// NOTE: BRL may not be included in @dinero.js/currencies package
// If import fails, define it manually with ISO 4217 standard (2 decimal places)
// Verify during implementation: try importing BRL first, fallback to manual definition
const currencyMap = {
  USD,
  EUR,
  GBP,
  BRL: { code: 'BRL', base: 10, exponent: 2 }  // Manual definition if not in package
};

function formatPrice(amountInCents, currencyCode) {
  const currency = currencyMap[currencyCode];
  const money = dinero({ amount: amountInCents, currency });

  // Dinero.js v2 uses transformer functions, not format strings
  return toDecimal(money, ({ value, currency }) =>
    `${currency.code} ${value.toFixed(2)}`
  );
}

// Convert price to user's selected currency
function convertPrice(baseAmountInCents, fromCurrency, toCurrency, exchangeRate) {
  const baseMoney = dinero({
    amount: baseAmountInCents,
    currency: currencyMap[fromCurrency]
  });

  // Multiply by exchange rate (convert rate to factor)
  const convertedAmount = Math.round(baseAmountInCents * exchangeRate);

  return dinero({
    amount: convertedAmount,
    currency: currencyMap[toCurrency]
  });
}
```

**Key Points:**
- Store amounts as integers (cents) to avoid floating-point errors
- Dinero.js operations are immutable (always return new objects)
- Define custom currency for BRL if not in @dinero.js/currencies
- Round converted amounts to nearest cent

### Exchange Rate Fetching with Fallback Pattern

```python
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Optional

async def fetch_exchange_rates(db: Session) -> Dict[str, float]:
    """
    Fetch latest exchange rates with graceful fallback to cached rates

    Returns dict of currency codes to rates (e.g., {'EUR': 0.92, 'GBP': 0.79})
    """
    api_url = os.getenv('EXCHANGE_RATE_API_URL')
    api_key = os.getenv('EXCHANGE_RATE_API_KEY')

    try:
        # Attempt to fetch from external API
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                api_url,
                params={'apikey': api_key} if api_key else None
            )
            response.raise_for_status()
            data = response.json()

            # Store successful rates in database
            rates = data.get('rates', {})
            for currency, rate in rates.items():
                if currency in ['EUR', 'GBP', 'BRL']:
                    exchange_rate = ExchangeRate(
                        from_currency='USD',
                        to_currency=currency,
                        rate=rate,
                        fetched_at=datetime.utcnow()
                    )
                    db.add(exchange_rate)
            db.commit()
            return rates

    except (httpx.HTTPError, httpx.TimeoutException, KeyError) as e:
        # Fallback to cached rates from database
        logger.warning(f"Exchange rate API failed: {e}. Using cached rates.")

        cached_rates = {}
        for currency in ['EUR', 'GBP', 'BRL']:
            latest = db.query(ExchangeRate).filter(
                ExchangeRate.from_currency == 'USD',
                ExchangeRate.to_currency == currency
            ).order_by(ExchangeRate.fetched_at.desc()).first()

            if latest:
                cached_rates[currency] = float(latest.rate)
                # Warn if rates are stale (>48 hours)
                if datetime.utcnow() - latest.fetched_at > timedelta(hours=48):
                    logger.error(f"Stale exchange rate for {currency}: {latest.fetched_at}")

        if not cached_rates:
            raise Exception("No cached exchange rates available and API failed")

        return cached_rates
```

**Key Points:**
- Always try external API first with 10-second timeout
- On failure (network, timeout, invalid response), fall back to database cache
- Warn if cached rates are >48 hours old
- Store successful API responses in database for future fallback
- Raise exception only if both API and cache fail

### Redux Currency State Pattern

```javascript
import { createSlice } from '@reduxjs/toolkit';

const currencySlice = createSlice({
  name: 'currency',
  initialState: {
    selectedCurrency: 'USD',
    exchangeRates: {},
    lastUpdated: null,
    loading: false,
    error: null
  },
  reducers: {
    setCurrency: (state, action) => {
      state.selectedCurrency = action.payload;
      // Persist to localStorage
      localStorage.setItem('preferredCurrency', action.payload);
    },
    setExchangeRates: (state, action) => {
      state.exchangeRates = action.payload.rates;
      state.lastUpdated = action.payload.timestamp;
    },
    setLoading: (state, action) => {
      state.loading = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
    }
  }
});

export const { setCurrency, setExchangeRates, setLoading, setError } = currencySlice.actions;
export default currencySlice.reducer;
```

**Key Points:**
- Persist user's currency preference to localStorage
- Store exchange rates in state for offline access
- Include timestamp to show users when rates were last updated
- Follow existing Redux Toolkit patterns in the project

## Requirements

### Functional Requirements

1. **Currency Selection**
   - Description: Users can select their preferred display currency from USD, EUR, GBP, BRL
   - Acceptance: Dropdown component accessible from navigation; selection persists across sessions via localStorage and backend preference API

2. **Price Display Conversion**
   - Description: All prices throughout the application display in user's selected currency using current exchange rates
   - Acceptance: Verify pricing pages, product cards, and checkout show correct converted amounts; amounts match backend calculations within 0.01 currency unit

3. **Daily Exchange Rate Updates**
   - Description: System fetches latest exchange rates daily at midnight UTC from external API
   - Acceptance: Database shows new exchange_rate records daily; scheduler job logs confirm successful execution; rates update without service restart

4. **Transparent Rate Disclosure**
   - Description: Checkout page displays the exchange rate used for conversion and original USD base price
   - Acceptance: Checkout shows "1 USD = X EUR (rate as of YYYY-MM-DD)" and "Original price: $XX.XX USD"

5. **Graceful Fallback**
   - Description: If exchange rate API fails, system uses last successfully cached rates
   - Acceptance: Simulate API failure; verify prices still display using cached rates; warning shown to user about rate staleness if >24 hours old

### Edge Cases

1. **Stale Exchange Rates** - If rates are older than 48 hours, display warning banner: "Exchange rates may not be current. Last updated: [timestamp]"

2. **API Rate Limiting** - Implement exponential backoff if API returns 429; cache rates in Redis with 24-hour TTL; log failures for monitoring

3. **Invalid Currency Selection** - If user's stored preference is invalid (e.g., currency removed), default to USD and log warning

4. **Rounding Precision** - Always round displayed prices to 2 decimal places; use banker's rounding (round half to even) to minimize cumulative errors

5. **Zero or Negative Prices** - Validate conversion results; if converted price <= 0, fallback to base USD price and log error

6. **First-Time Bootstrapping** - On initial deployment, pre-populate exchange_rates table with manual rates; scheduler will update on next run

## Implementation Notes

### DO
- Store all base prices in USD in the database (source of truth)
- Use Redis caching for exchange rates to reduce database queries
- Validate ISO 4217 currency codes on all inputs
- Log all exchange rate updates and failures for monitoring
- Implement API request timeout of 10 seconds for exchange rate fetches
- Use environment variables for API keys (`EXCHANGE_RATE_API_KEY`, `EXCHANGE_RATE_API_URL`)
- Display currency symbols using native Babel/Dinero.js formatting
- Write unit tests for currency conversion logic with known exchange rates
- Test with extreme values (very large/small amounts) to verify precision

### DON'T
- Don't store converted prices in database (always calculate on-demand)
- Don't auto-detect currency from IP/geolocation (user must explicitly select)
- Don't use forex-python library (unreliable; use direct REST API instead)
- Don't modify existing billing/payment processor integration in Phase 1
- Don't round intermediate calculations (only final displayed amounts)
- Don't block page loads on exchange rate fetches (load asynchronously)
- Don't forget to handle time zones (store all timestamps in UTC)
- Don't hard-code exchange rates (always fetch from external API)

## Development Environment

### Start Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Start backend API
cd cli
python -m cli

# Start frontend (in separate terminal)
cd web
npm run dev
```

### Service URLs
- Backend API: http://localhost:8000
- Frontend: http://localhost:8000 (verify actual port from Vite output)
- PostgreSQL: localhost:5432 (database: dumont_cloud)
- Redis: localhost:6379

### Required Environment Variables

Add to `.env` file:
```bash
# Exchange Rate API Configuration
EXCHANGE_RATE_API_KEY=your_api_key_here
# ⚠️ WARNING: API endpoint below is unverified - verify actual API URL format during implementation
EXCHANGE_RATE_API_URL=https://api.exchangerate-api.io/v4/latest/USD

# Existing variables
DATABASE_URL=postgresql://dumont:dumont123@localhost:5432/dumont_cloud
REDIS_URL=redis://localhost:6379/0
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
```

**To obtain API key:**
1. **CRITICAL**: Verify API provider supports all required currencies (USD, EUR, GBP, BRL) before implementation
2. Sign up at https://www.exchangerate-api.io (free tier: ~1,500 requests/month) - **verify current limits**
3. Alternative providers: https://fixer.io, https://openexchangerates.org, or European Central Bank API
4. **Verify endpoint format** - the URL above is illustrative and must be confirmed against actual API documentation
5. Store key securely in `.env` (never commit to git)

## Success Criteria

The task is complete when:

1. [ ] User can select currency (USD/EUR/GBP/BRL) from navigation dropdown
2. [ ] Currency preference persists across browser sessions (localStorage + backend)
3. [ ] All pricing displays throughout the application show selected currency
4. [ ] Checkout page displays conversion rate and original USD price
5. [ ] Exchange rates update daily via automated scheduler
6. [ ] System gracefully handles API failures using cached rates
7. [ ] No console errors in browser or backend logs
8. [ ] Existing tests still pass
9. [ ] New functionality verified via manual browser testing
10. [ ] Database migrations applied successfully (exchange_rates table created)

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests

| Test | File | What to Verify |
|------|------|----------------|
| `test_exchange_rate_fetch` | `cli/tests/test_exchange_rate.py` | API call succeeds; rates stored in database; correct data structure |
| `test_currency_conversion` | `cli/tests/test_pricing.py` | Conversion math is accurate; handles edge cases (0, negative, very large) |
| `test_format_currency` | `cli/tests/test_formatting.py` | Babel formatting returns correct symbols and decimal places for all 4 currencies |
| `test_stale_rate_fallback` | `cli/tests/test_exchange_rate.py` | System uses cached rates when API fails; warning logged |
| `test_currency_selector_component` | `web/src/components/__tests__/CurrencySelector.test.jsx` | Renders all 4 currencies; onChange updates Redux state |
| `test_price_display_conversion` | `web/src/components/__tests__/PriceDisplay.test.jsx` | Displays converted amount; uses Dinero.js correctly |

### Integration Tests

| Test | Services | What to Verify |
|------|----------|----------------|
| `test_currency_preference_api` | cli ↔ database | POST /api/user/currency saves preference; GET retrieves correct value |
| `test_pricing_endpoint_with_currency` | cli ↔ database | GET /api/pricing?currency=EUR returns converted prices using latest rates |
| `test_scheduler_rate_update` | cli ↔ external API ↔ database | Scheduler job executes; rates fetched from API; database updated |
| `test_frontend_currency_change` | web ↔ cli | User changes currency in dropdown; frontend calls API; prices re-render with new currency |

### End-to-End Tests

| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Currency Selection Flow | 1. Open app 2. Click currency dropdown 3. Select EUR 4. Navigate to pricing page | All prices display in EUR; selection persists on page reload |
| Checkout Conversion Display | 1. Add item to cart 2. Select BRL as currency 3. Go to checkout | Checkout shows BRL price, conversion rate (e.g., "1 USD = 5.XX BRL"), and original USD price |
| Stale Rate Warning | 1. Stop scheduler 2. Wait 48+ hours (or mock system time) 3. Load pricing page | Warning banner appears: "Exchange rates may not be current. Last updated: [date]" |

### Browser Verification (Frontend)

| Page/Component | URL | Checks |
|----------------|-----|--------|
| Currency Selector | All pages (navigation) | Dropdown shows 4 currencies; selected currency highlighted; onChange triggers update |
| Pricing Page | `http://localhost:8000/pricing` | All prices display in selected currency; symbols correct (€, £, R$, $) |
| Checkout Page | `http://localhost:8000/checkout` | Conversion rate shown (e.g., "1 USD = 0.92 EUR as of 2025-12-30"); original USD price displayed |
| Product Cards | `http://localhost:8000/products` | Each card shows price in selected currency; formatting consistent |

### Database Verification

| Check | Query/Command | Expected |
|-------|---------------|----------|
| Exchange rates table exists | `\dt exchange_rates` in psql | Table created with correct schema |
| Daily rates populated | `SELECT * FROM exchange_rates WHERE fetched_at > NOW() - INTERVAL '1 day';` | 3 rows (USD→EUR, USD→GBP, USD→BRL) with today's timestamp |
| User preferences table | `SELECT * FROM user_currency_preferences;` | Can store user_id and currency_code |
| Rate precision | `SELECT rate FROM exchange_rates LIMIT 1;` | Value has 6 decimal places (e.g., 0.923456) |

### API Verification

| Endpoint | Method | Request | Expected Response |
|----------|--------|---------|-------------------|
| `/api/currency/rates` | GET | - | `{ "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "BRL": 5.42, "updated_at": "2025-12-30T00:00:00Z" }` |
| `/api/user/currency` | POST | `{ "currency": "EUR" }` | `{ "success": true, "currency": "EUR" }` |
| `/api/user/currency` | GET | - | `{ "currency": "EUR" }` |
| `/api/pricing/convert` | POST | `{ "amount": 100, "from": "USD", "to": "EUR" }` | `{ "original_amount": 100, "converted_amount": 92, "rate": 0.92, "currency": "EUR" }` |

### Performance Checks

| Metric | Threshold | How to Verify |
|--------|-----------|---------------|
| Currency conversion time | < 50ms | Use browser DevTools Network tab; check API response time for pricing endpoints |
| Redis cache hit rate | > 95% | Check Redis stats; exchange rates should be cached, not queried from DB every request |
| Page load with currency change | < 200ms | Change currency; measure time until all prices re-render |
| Exchange rate API timeout | Handled gracefully | Simulate API timeout; verify fallback to cached rates without errors |

### QA Sign-off Requirements

- [ ] All unit tests pass (minimum 6 new tests)
- [ ] All integration tests pass (minimum 4 new tests)
- [ ] All E2E tests pass (minimum 3 flows)
- [ ] Browser verification complete for 4 pages/components
- [ ] Database schema verified with correct data types and constraints
- [ ] API endpoints return correct data for all 4 currencies
- [ ] Performance thresholds met (< 50ms conversion, > 95% cache hit)
- [ ] No regressions in existing functionality (all old tests pass)
- [ ] Code follows established patterns (Redux, FastAPI, component structure)
- [ ] No security vulnerabilities (API keys in .env, not committed; input validation on currency codes)
- [ ] Error handling tested (API failures, invalid currencies, network issues)
- [ ] Scheduler verified running and updating rates daily
- [ ] Documentation added (API docs, component docs, README updated)

### Security Verification

| Check | What to Verify |
|-------|---------------|
| API Key Protection | `EXCHANGE_RATE_API_KEY` in `.env` file; not in git; not exposed to frontend |
| Currency Code Validation | Only accept 'USD', 'EUR', 'GBP', 'BRL'; reject invalid codes with 400 error |
| SQL Injection Prevention | Use parameterized queries for all database operations |
| Rate Tampering | Exchange rates only writable by scheduler job, not user-facing API |

---

**Implementation Priority:**
1. Database schema (exchange_rates, user_currency_preferences tables)
2. Backend exchange rate fetching service + scheduler
3. Backend API endpoints (currency selection, pricing conversion)
4. Frontend currency selector component
5. Frontend price display conversion
6. Integration testing
7. E2E testing and browser verification

**Estimated Complexity:** Medium-High (requires backend + frontend + scheduled tasks + external API integration)

**Estimated Time:** 2-3 days for full implementation and testing
