# Investigation Report: GPU-to-CPU Migration E2E Tests

**Date:** 2025-12-31
**Workflow:** Investigation
**Objective:** Verify GPU-to-CPU migration functionality through Playwright E2E tests
**Status:** Analysis Complete (Manual Test Execution Required)

---

## Executive Summary

This investigation analyzed the Playwright E2E test suite for GPU-to-CPU migration and failover functionality. The test infrastructure is properly configured but **tests could not be executed in the sandbox environment** (npm/npx blocked). Static analysis of all test files was performed to identify issues and propose corrections.

### Key Findings

| Metric | Value |
|--------|-------|
| Total Test Files Analyzed | 4 spec files |
| Total Tests Identified | 47 tests |
| Tests with Weak Assertions | ~60% |
| Critical Gaps Identified | 4 |
| Recommended Priority Fixes | 6 |

---

## Test Infrastructure Status

### Configuration Files

| File | Status | Notes |
|------|--------|-------|
| `playwright.config.js` | ✅ Correct | Timeout 10min, HTML reporter, chromium project |
| `auth.setup.js` | ✅ Correct | Supports DEMO and REAL modes |
| `package.json` | ✅ Correct | Playwright v1.57.0 installed |
| `.auth/user.json` | ✅ Exists | Pre-authenticated state available |

### Environment Requirements

```bash
# Required setup (run outside sandbox)
cd tests && npm install && npx playwright install chromium

# Start frontend
cd web && npm run dev

# Run tests in demo mode
cd tests && USE_DEMO_MODE=true npx playwright test e2e-journeys/
```

---

## Test File Analysis

### 1. `cpu-standby-failover.spec.js`

**Tests:** 11 tests in 3 suites
**Coverage:** CPU Standby configuration, failover simulation, metrics

| Suite | Tests | Assertions |
|-------|-------|------------|
| CPU Standby e Failover Automatico | 4 | Weak (2 use `expect(true)`) |
| Metricas e Status do CPU Standby | 2 | Conditional |
| Relatorio de Failover | 5 | Mixed |

**Strengths:**
- Uses flexible selectors: `.first()`, `.catch(() => false)`
- Appropriate timeouts (2000-5000ms)
- Force clicks to avoid overlay issues
- Good console logging for debugging

**Issues Found:**
1. **Weak Assertions (P1):** Tests 3 and 4 use `expect(true).toBeTruthy()` - always pass
2. **No Failure Cases (P2):** No tests verify error states or edge cases
3. **Conditional Logic (P2):** Many tests pass regardless of element visibility

**Code Example - Problem:**
```javascript
// Line 159 - Always passes
expect(true).toBeTruthy(); // Teste passa se chegou aqui

// Line 198 - Always passes
expect(true).toBeTruthy();
```

**Recommended Fix:**
```javascript
// Replace with meaningful assertions
const hasOnlineOrBackup = hasOnline || hasBackup;
expect(hasOnlineOrBackup).toBeTruthy();
```

---

### 2. `failover-complete-journeys.spec.js`

**Tests:** 19 tests in 7 journey suites
**Coverage:** Complete user flows for all failover functionality

| Suite | Tests | Assertions |
|-------|-------|------------|
| Configuracoes de Failover | 3 | URL-based only |
| Regional Volume Failover | 3 | Minimal |
| Simulacao de Failover | 3 | None explicit |
| CPU Standby Associations | 3 | Minimal |
| Fast Failover | 2 | URL-based only |
| Metricas de Failover | 3 | None explicit |
| Jornada Completa | 2 | URL-based |

**Strengths:**
- Well-organized into logical user journeys
- Excellent test naming (describes user action)
- Multi-page fallback strategies
- Comprehensive coverage of UI areas

**Issues Found:**
1. **No Explicit Assertions (P1):** Many tests have NO `expect()` calls
2. **Exploratory Only (P2):** Tests are investigative, not assertive
3. **Console-Only Verification (P3):** Results logged but not validated

**Code Example - Problem:**
```javascript
// Line 190-194 - No assertion, just logging
if (hasRegionFilter) {
  console.log('✅ Filtro de regiao encontrado');
} else {
  console.log('ℹ️ Filtro de regiao pode estar no GPU Advisor');
}
// Test passes regardless!
```

**Recommended Fix:**
```javascript
// Add explicit assertion at end
expect(hasRegionFilter || hasGpuList).toBeTruthy();
```

---

### 3. `failover-strategy-selection.spec.js`

**Tests:** 17 tests in 7 suites
**Coverage:** Strategy selection UI, dropdown behavior, API integration

| Suite | Tests | Assertions |
|-------|-------|------------|
| Pagina de Maquinas | 3 | Strong |
| Badge de Failover | 2 | Conditional |
| Selecao de Estrategia | 3 | Mixed |
| Criar Maquina via Dashboard | 2 | Conditional |
| Trocar Estrategia | 3 | Weak (`expect(true)`) |
| Custos Dinamicos | 2 | Partial |
| Integracao API | 3 | Strong |

**Strengths:**
- Uses `data-testid` selectors (more stable)
- Tests API endpoints directly
- Tests 5 different failover strategies
- Verifies dynamic cost calculations

**Issues Found:**
1. **Uses `/demo-app` path (P2):** Different from other tests using `/app`
2. **`test.skip()` usage (P3):** Tests skip silently when no machines exist
3. **Weak Assertions (P1):** Lines 412, 457, 508 use `expect(true).toBe(true)`

**Code Example - Problem:**
```javascript
// Line 412 - Always passes
expect(true).toBe(true); // Passou se chegou aqui
```

---

### 4. `auth.setup.js`

**Status:** ✅ Correctly Implemented
**Modes:** DEMO (USE_DEMO_MODE=true) and REAL (credentials)

**Flow in DEMO Mode:**
1. Navigate to `/demo-app`
2. Wait for page load
3. Set `demo_mode=true` in localStorage
4. Close welcome modal if present
5. Save auth state to `.auth/user.json`

**Existing Auth State Found:**
- JWT token present (valid)
- `demo_mode: true`
- `onboarding_completed: true`
- Theme: dark

---

## Critical Gaps for Migration Testing

### Gap 1: No "Create Machine" Flow Test
**Impact:** High
**Description:** No test verifies the machine creation flow where migration strategy is initially selected.

**Recommendation:** Add test:
```javascript
test('Create machine flow includes failover strategy selection', async ({ page }) => {
  await page.goto('/app');
  await page.getByRole('button', { name: /selecionar|select/i }).first().click();
  // Verify failover strategy dropdown appears during creation
  const strategySelector = page.locator('[data-testid="failover-strategy-selector"]');
  await expect(strategySelector).toBeVisible({ timeout: 10000 });
});
```

### Gap 2: No Migration Trigger Verification
**Impact:** High
**Description:** No test verifies that clicking "Simular Failover" actually triggers the migration process.

**Recommendation:** Add API interception:
```javascript
test('Simulate failover triggers migration API', async ({ page }) => {
  // Intercept API calls
  const migrationApiCall = page.waitForRequest('**/api/v1/migration/**');

  await page.goto('/app/machines');
  await page.getByRole('button', { name: /simular/i }).first().click();

  // Verify API was called
  const request = await migrationApiCall;
  expect(request.url()).toContain('migration');
});
```

### Gap 3: No Migration State Verification
**Impact:** Medium
**Description:** No test verifies UI state changes during migration (progress indicators, status updates).

### Gap 4: No Error Case Testing
**Impact:** Medium
**Description:** No tests verify behavior when migration fails or is cancelled.

---

## Summary of Problems by Severity

### P1 - Critical (Must Fix)

| Issue | File(s) | Line(s) | Impact |
|-------|---------|---------|--------|
| `expect(true)` always passes | cpu-standby-failover.spec.js | 159, 198 | Tests give false positives |
| `expect(true).toBe(true)` | failover-strategy-selection.spec.js | 412, 457, 508 | Tests give false positives |
| No assertions in journey tests | failover-complete-journeys.spec.js | Multiple | Tests always pass |

### P2 - High (Should Fix)

| Issue | File(s) | Impact |
|-------|---------|--------|
| Inconsistent base paths | failover-strategy-selection.spec.js uses `/demo-app`, others use `/app` | Test inconsistency |
| Silent test.skip() | failover-strategy-selection.spec.js | Hides test coverage gaps |
| No negative test cases | All files | No error path coverage |

### P3 - Medium (Nice to Have)

| Issue | File(s) | Impact |
|-------|---------|--------|
| Console-only verification | failover-complete-journeys.spec.js | No automated failure detection |
| Excessive waitForTimeout | All files | Slower test execution |
| Missing data-testid | Some selectors | Fragile element selection |

---

## Recommended Fixes

### Fix 1: Replace Weak Assertions in `cpu-standby-failover.spec.js`

```javascript
// Instead of expect(true).toBeTruthy()
// Use the actual condition that was checked

// Line 159 - Replace:
expect(true).toBeTruthy();
// With:
expect(hasOnline || hasBackup || hasAnyMachine).toBeTruthy();

// Line 198 - Replace:
expect(true).toBeTruthy();
// With:
expect(hasFailoverTab || hasConfigElements).toBeTruthy();
```

### Fix 2: Add Assertions to Journey Tests

Add explicit assertions at the end of each test in `failover-complete-journeys.spec.js`:

```javascript
// Example for test "Usuario busca GPUs disponiveis em regiao especifica"
test('Usuario busca GPUs disponiveis em regiao especifica', async ({ page }) => {
  // ... existing code ...

  // ADD at end:
  const hasContent = hasRegionFilter || hasGpuList || page.url().includes('/app');
  expect(hasContent).toBeTruthy();
});
```

### Fix 3: Standardize Base Paths

Update `failover-strategy-selection.spec.js` to use consistent paths:

```javascript
// Change from:
const BASE_PATH = '/demo-app';

// To:
const BASE_PATH = '/app';
```

### Fix 4: Add Migration Flow Test

Create new test file `tests/e2e-journeys/migration-flow.spec.js`:

```javascript
const { test, expect } = require('@playwright/test');

test.describe('GPU to CPU Migration Flow', () => {
  test('Create machine shows failover strategy options', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('domcontentloaded');

    // Find and click create/select button
    const selectBtn = page.getByRole('button', { name: /selecionar|select/i }).first();
    if (await selectBtn.isVisible().catch(() => false)) {
      await selectBtn.click();
      await page.waitForTimeout(1000);

      // Verify failover options are shown
      const hasFailoverOptions = await page.getByText(/cpu standby|warm pool|failover/i)
        .first()
        .isVisible()
        .catch(() => false);

      expect(hasFailoverOptions).toBeTruthy();
    }
  });
});
```

### Fix 5: Replace `test.skip()` with Conditional Assertions

```javascript
// Instead of:
if (!hasGPUCards) {
  test.skip();
  return;
}

// Use:
test.skip(async ({ page }) => {
  await page.goto('/app/machines');
  const hasGPU = await page.getByText(/RTX|A100|H100/i).first().isVisible().catch(() => false);
  return !hasGPU;
}, 'No GPU machines available');
```

### Fix 6: Add API Integration Verification

```javascript
test('Failover strategy change calls API', async ({ page }) => {
  // Listen for API calls
  const apiCalls = [];
  page.on('request', req => {
    if (req.url().includes('/api/')) {
      apiCalls.push(req.url());
    }
  });

  await page.goto('/app/machines');
  // ... interact with failover selector ...

  // Verify API was called
  const hasFailoverApiCall = apiCalls.some(url => url.includes('failover') || url.includes('standby'));
  expect(hasFailoverApiCall).toBeTruthy();
});
```

---

## Test Execution Instructions

### Run All Failover Tests

```bash
cd tests
USE_DEMO_MODE=true npx playwright test e2e-journeys/*failover*.spec.js --reporter=html
```

### Run with UI (Debug Mode)

```bash
cd tests
USE_DEMO_MODE=true npx playwright test --ui
```

### Generate HTML Report

```bash
cd tests
npx playwright show-report
```

### Expected Results

In **DEMO MODE** with mock data:
- All 47 tests should pass
- Console output shows element visibility status
- No actual API calls to production systems

In **REAL MODE**:
- Requires valid credentials
- Depends on actual machine state
- Some tests may skip based on data availability

---

## Conclusion

The E2E test suite for GPU-to-CPU migration has **good structural coverage** but suffers from:

1. **Weak assertions** that always pass (P1)
2. **Missing migration-specific tests** (Gap 1, 2)
3. **No error case coverage** (Gap 4)

### Recommended Priority Order

1. **First:** Fix P1 issues (weak assertions) - 2 hours estimated
2. **Second:** Add migration flow tests (Gap 1, 2) - 4 hours estimated
3. **Third:** Standardize paths and skip conditions (P2) - 1 hour estimated
4. **Fourth:** Add error case tests (Gap 4) - 3 hours estimated

### Next Steps

1. Execute tests manually to verify current pass/fail status
2. Apply Fix 1-3 to existing test files
3. Create new migration-specific test file
4. Re-run full suite and document actual results
5. Update this report with execution results

---

## Appendix: Test File Quick Reference

| File | Tests | Primary Coverage |
|------|-------|------------------|
| `cpu-standby-failover.spec.js` | 11 | CPU Standby config, metrics, reports |
| `failover-complete-journeys.spec.js` | 19 | User journey flows |
| `failover-strategy-selection.spec.js` | 17 | Strategy UI, dropdown, API |
| **Total** | **47** | |

---

*Report generated by auto-claude investigation workflow*
