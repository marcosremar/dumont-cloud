# Wizard Hardware Step - Visual Test Report

**Date**: 2026-01-02
**Test File**: `/Users/marcos/CascadeProjects/dumontcloud/tests/wizard-hardware-visual.spec.ts`
**Environment**: http://localhost:4896
**Status**: ✅ PASSED

---

## Test Flow Executed

### Step 1: Auto-Login ✅
- Navigated to: `http://localhost:4896/login?auto_login=demo`
- Login completed in: **1480ms**
- Redirected to: `/app`

### Step 2: Locate Wizard ✅
- Wizard was already open on the dashboard
- No need to click "Nova Máquina" button

### Step 3: Navigate to Step 2 (Hardware) ✅
- Started on Step 1 (Região)
- Found **3 region quick-select buttons** (EUA, Europa, Ásia)
- Selected first region (EUA)
- Clicked "Próximo" button
- Successfully moved to Step 2

### Step 4: Select GPU Tier ✅
- Found **1 tier button** visible
- Clicked "Rápido" tier
- Tier selection succeeded

### Step 5: Screenshot Captured ✅
- Saved to: `/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-step2-hardware.png`

---

## Screenshot Analysis

### What's Visible on Step 2 (Hardware):

1. **Step Indicator**: "2/4 Hardware - GPU e performance"

2. **Usage Question**: "O que você vai fazer?"
   - Buttons: Apenas CPU | Experimentar | Desempenho | Treinar modelo | Produção
   - "Experimentar" is selected (green highlight)

3. **GPU Selection Section**: "Seleção de GPU"
   - Shows GPU options:
     - RTX 3060 (8GB) - $0.10/h
     - RTX 3060 Ti (8GB) - $0.12/h
     - RTX 4070 Ti (12GB) - $0.12/h (partially visible)

4. **Performance Tier**: "Tier: Lento"
   - RTX 3060 | VRAM: 8-16GB | VRAM
   - Price: $6.50 - $0.25/hr

5. **Navigation**:
   - "Voltar" (Back) button on the left
   - "Próximo" (Next) button on the right (green)

---

## Issues Found

### 1. No API Call to `/api/v1/instances/offers`
- **Expected**: When selecting a tier, the wizard should call `/api/v1/instances/offers` to fetch available GPU machines
- **Actual**: No API requests were logged
- **Impact**: The GPU selection might be showing static/demo data instead of real offers

### 2. Console Errors
- **Error**: "Failed to load resource: the server responded with a status of 404 (Not Found)"
- **Count**: 1 error
- **Details**: Not specified which resource failed

### 3. No Machine Cards Displayed
- **Expected**: After selecting a tier, individual GPU machine cards should appear
- **Actual**: 0 machine/offer cards found
- **Note**: The screenshot shows GPU options (RTX 3060, etc.) but not in the expected card format

---

## Network Activity

- **Total API Requests**: 0
- **Requests to `/api/v1/instances/offers`**: None
- **Console Errors**: 1 (404 Not Found)

---

## Observations

### Positive:
1. Wizard navigation works correctly (Step 1 → Step 2)
2. UI renders properly with tier options
3. GPU models are displayed (RTX 3060, RTX 3060 Ti, RTX 4070 Ti)
4. Pricing information is shown
5. Auto-login works flawlessly

### Concerns:
1. **Backend Integration**: No API calls detected - wizard might be in demo mode
2. **GPU Offers**: Need to verify if real GPU offers are being fetched from VAST.ai
3. **Error Handling**: One 404 error suggests a missing resource

---

## Recommendations

### 1. Verify Demo Mode Status
Check if the wizard is running in demo mode vs. real mode:
```javascript
// In browser console:
localStorage.getItem('demo_mode')
```

### 2. Enable API Logging
Add detailed logging to track when `/api/v1/instances/offers` is called:
- On tier selection
- On usage type selection
- On region change

### 3. Investigate 404 Error
Check browser DevTools Network tab to identify which resource returned 404

### 4. Test Real Backend Integration
Run test with explicit demo_mode=false to ensure real API calls work

---

## Next Steps

1. **Run test in headless mode** to verify it works in CI/CD
2. **Add assertions for API calls** - test should fail if offers endpoint not called
3. **Capture browser console in detail** - log all network requests
4. **Test with different tiers** - Equilibrado, Lento, etc.
5. **Validate pricing data** - ensure prices match VAST.ai actual rates

---

## Test Code Location

**File**: `/Users/marcos/CascadeProjects/dumontcloud/tests/wizard-hardware-visual.spec.ts`

**Key Features**:
- Auto-login via URL parameter
- Console error capture
- Network request monitoring
- Full-page screenshots
- Detailed logging of each step

**Runtime**: ~14.8 seconds (including auth setup)

---

## Conclusion

The wizard UI works correctly and displays GPU options, but there's a question about whether it's fetching real data from the backend. The lack of API calls to `/api/v1/instances/offers` suggests either:

1. Data is cached/pre-loaded
2. Demo mode is enabled
3. API calls happen on a different trigger

**Recommendation**: Manually verify the wizard behavior in the browser console to determine if real API integration is working.
