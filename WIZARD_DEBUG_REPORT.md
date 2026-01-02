# Wizard Debug Report - Port 4893

**Date**: 2026-01-02
**Application**: Dumont Cloud - GPU Provisioning Wizard
**Port**: http://localhost:4893

---

## Summary

The wizard **IS working** and successfully makes API calls to `/api/v1/instances/offers`. However, there are several issues that need attention.

---

## Test Results

### ✅ What's Working

1. **Auto-login**: `?auto_login=demo` works correctly and redirects to `/app`
2. **Wizard loads**: The "Nova Instância GPU" wizard opens automatically when navigating to `/app`
3. **Navigation works**: Can successfully navigate through wizard steps:
   - Step 1: Region selection (EUA, Europa, Ásia, América do Sul)
   - Step 2: Tier selection (Desenvolver, Produção, Treinar)
4. **API call is made**: When selecting "Desenvolver" tier, the wizard makes:
   ```
   GET /api/v1/instances/offers?limit=5&order_by=dph_total&region=BR&min_gpu_ram=10&max_price=0.45
   ```
5. **API responds successfully**: Returns HTTP 200 with valid JSON

### ❌ Issues Found

#### 1. **Empty Offers Response**
The `/offers` endpoint returns successfully but with **zero offers**:

```json
{
  "offers": [],
  "count": 0
}
```

**Query Parameters**:
- `region=BR` (Brasil)
- `min_gpu_ram=10` (GB)
- `max_price=0.45` ($/hour)
- `limit=5`
- `order_by=dph_total`

**Possible causes**:
- No GPU offers available in Brasil (BR) region matching criteria
- Price filter too restrictive ($0.45/hour max)
- Backend not returning demo data for demo mode
- Database has no matching records

#### 2. **Authentication Errors on Load**

Two API calls fail when loading `/app`:

**A. Balance endpoint (401 Unauthorized)**:
```
GET /api/v1/instances/balance
Response: 401 Unauthorized
Body: {"error": "Not authenticated"}
```

**B. Teams endpoint (500 Internal Server Error)**:
```
GET /api/v1/users/me/teams?demo=true
Response: 500 Internal Server Error

Error details:
(psycopg2.errors.UndefinedTable) relation "teams" does not exist
LINE 2: FROM teams JOIN team_members ON teams.id = team_members.team...
```

The `teams` table does not exist in the database.

---

## Wizard Flow (Step-by-Step)

### Step 1: Initial Load
- URL: `http://localhost:4893/login?auto_login=demo`
- Auto-login executes with demo credentials
- Redirects to `/app`
- Wizard modal opens showing "Nova Instância GPU"

### Step 2: Region Selection
**Options visible**:
- ✅ EUA (USA)
- ✅ Europa (Europe)
- ✅ Ásia (Asia)
- ✅ América do Sul (South America)

**Note**: Earlier screenshots showed "Brasil, Canadá, Escandinava" which suggests the wizard might have multiple region selection modes or the UI changed.

**Action**: Click "América do Sul" → "Próximo" button

### Step 3: Hardware/Tier Selection
**Options visible**:
- ✅ Desenvolver (Development)
- ✅ Produção (Production)
- ✅ Treinar (Training)

**Action**: Click "Desenvolver"

### Step 4: API Call Triggered
Immediately after clicking "Desenvolver", the wizard makes:
```
GET /api/v1/instances/offers?limit=5&order_by=dph_total&region=BR&min_gpu_ram=10&max_price=0.45
```

Response:
```json
{
  "offers": [],
  "count": 0
}
```

---

## Console Messages

### Errors
1. `Failed to load resource: the server responded with a status of 401 (Unauthorized)` - `/balance` endpoint
2. `Failed to load resource: the server responded with a status of 500 (Internal Server Error)` - `/teams` endpoint

### Info/Debug
- `[Login] Auto-login check: {autoLogin: demo, hasOnLogin: true}`
- `[Login] Executing demo auto-login...`
- `[handleLogin] Using demo credentials, doing demo login`
- `[Login] onLogin result: {success: true, isDemo: true}`

---

## Recommendations

### Priority 1: Fix Empty Offers Response

**Option A - Add Demo Data**:
The backend should return mock/demo offers when `?demo=true` parameter is present, even if database is empty.

**Option B - Adjust Query Parameters**:
The wizard's default filters might be too restrictive:
- Consider increasing `max_price` limit
- Consider decreasing `min_gpu_ram` requirement
- Add fallback to show "no offers available" message in UI

### Priority 2: Fix Database Issues

1. **Create teams table** or make teams feature optional in demo mode
2. **Fix authentication** for `/balance` endpoint in demo mode - should not require full auth

### Priority 3: Improve Error Handling

The wizard should:
1. Display user-friendly message when no offers are found
2. Suggest adjusting filters or trying different region
3. Not silently fail on empty results

---

## API Endpoints Called

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/users/me/teams?demo=true` | GET | 500 | Database table missing |
| `/api/v1/instances/balance` | GET | 401 | Auth required (should work in demo) |
| `/api/v1/instances/offers?...` | GET | 200 ✅ | Works but returns empty array |

---

## Screenshots

Generated during test run:
- `test-results/flow-step1-initial.png` - Wizard initial state
- `test-results/flow-step3-region-selected.png` - After selecting América do Sul
- `test-results/flow-step4-next-clicked.png` - After clicking Próximo
- `test-results/flow-step6-tier-selected.png` - After selecting Desenvolver
- `test-results/flow-step7-final.png` - Final state showing empty offers

---

## Next Steps

To fully debug the offers issue, investigate:

1. **Backend**: Check `/api/v1/instances/offers` endpoint implementation
   - File: `src/api/v1/endpoints/instances.py` (likely location)
   - Does it handle demo mode?
   - What's the actual database query?

2. **Database**: Check if there are any GPU offers in the database
   - Are there records in the offers/instances table?
   - Do they match the query filters?

3. **Mock Data**: Consider adding seed data for demo mode
   - Add sample GPU offers for testing
   - Ensure filters match available data
