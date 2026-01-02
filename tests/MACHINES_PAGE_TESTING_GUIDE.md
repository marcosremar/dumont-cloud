# Machines Page Testing Guide

## Overview
This guide provides comprehensive instructions for testing the Machines page at http://localhost:4893/demo-app/machines.

## Quick Start

### Prerequisites
1. Server must be running on port 4893
2. Node.js and npm installed
3. Playwright dependencies installed

### Start the Server
```bash
cd /Users/marcos/CascadeProjects/dumontcloud/web
npm run dev -- --port 4893
```

Wait for the server to start and show: "Local: http://localhost:4893"

### Run the Tests
```bash
# Option 1: Use the test runner script
cd /Users/marcos/CascadeProjects/dumontcloud/tests
chmod +x run-machines-test.sh
./run-machines-test.sh

# Option 2: Run Playwright directly
cd /Users/marcos/CascadeProjects/dumontcloud/tests
npx playwright test test-machines.spec.js

# Option 3: Run with visible browser
npx playwright test test-machines.spec.js --headed

# Option 4: Debug mode (step through tests)
npx playwright test test-machines.spec.js --debug
```

## Test Suite Details

### Test File Location
`/Users/marcos/CascadeProjects/dumontcloud/tests/test-machines.spec.js`

### What Gets Tested

#### Test 1: Page Loads Without JavaScript Errors
**Purpose**: Verify the page loads without critical JavaScript errors

**Steps**:
1. Navigate to http://localhost:4893/login?auto_login=demo
2. Wait for automatic login and redirect to /demo-app
3. Navigate to http://localhost:4893/demo-app/machines
4. Wait for h1 title to appear
5. Check page title contains "máquina"
6. Wait for machine cards or empty state
7. Count machine cards
8. Take full-page screenshot

**Expected Results**:
- No ReferenceError in console
- No TypeError in console
- No "is not defined" errors
- Page title visible and correct
- Either machine cards or empty state visible
- Screenshot saved to: `test-results/machines-page-snapshot.png`

**What Can Go Wrong**:
- Missing imports
- Undefined variables
- Component rendering errors
- Translation keys not found
- Props not passed correctly

#### Test 2: Verify UI Elements
**Purpose**: Ensure all expected UI elements are present and visible

**Steps**:
1. Navigate to machines page
2. Verify "Minhas Máquinas" title is visible
3. Check for machine cards
4. Check for empty state (if no machines)
5. Verify at least one element is visible
6. Take full-page screenshot

**Expected Results**:
- Title "Minhas Máquinas" visible
- If demo machines exist: Machine cards visible
- If no machines: Empty state visible
- Screenshot saved to: `test-results/machines-page-ui-elements.png`

**UI Components Checked**:
- Page title and subtitle
- "Nova Máquina" button
- Stats cards (GPUs Ativas, CPU Backup, VRAM Total, Custo/Hora)
- Filter tabs (All, Online, Offline)
- Machine cards grid

#### Test 3: Check for Undefined Variables
**Purpose**: Deep dive into console messages to find any variable issues

**Steps**:
1. Track all console messages (log, warn, error, debug)
2. Track all page errors
3. Navigate to machines page
4. Wait for page to stabilize
5. Categorize errors by type
6. Report findings

**Expected Results**:
- Zero page errors
- Zero undefined variable errors
- Zero ReferenceErrors
- Zero TypeErrors
- All console messages logged for analysis

**Error Categories**:
- Undefined variables: "X is not defined"
- ReferenceError: Variable access before declaration
- TypeError: Invalid type operations
- Other console errors

## Understanding Test Results

### Success Indicators
```
✓ Machines page loads without JS errors (5s)
✓ Machines page - verify UI elements (3s)
✓ Machines page - check for undefined variables in console (3s)

3 passed (11s)
```

### Failure Indicators
```
✗ Machines page loads without JS errors (5s)

Expected: 0
Received: 2

Critical JavaScript errors found:
- ReferenceError: someVariable is not defined
- TypeError: Cannot read property 'x' of undefined
```

## Common Issues and Solutions

### Issue 1: Server Not Running
**Error**: Connection refused or timeout
**Solution**:
```bash
cd /Users/marcos/CascadeProjects/dumontcloud/web
npm run dev -- --port 4893
```

### Issue 2: Demo Mode Not Working
**Error**: Login fails or redirects incorrectly
**Solution**:
- Check auto-login implementation in Login.jsx
- Verify demo credentials are configured
- Check browser console for auth errors

### Issue 3: Missing Components
**Error**: "Component is not defined"
**Solution**:
- Check imports in Machines.jsx
- Verify all components are exported
- Check file paths are correct

### Issue 4: Missing Demo Data
**Error**: No machines displayed or empty array
**Solution**:
- Check DEMO_MACHINES in constants/demoData.js
- Verify demo mode detection (isDemoMode())
- Check fetchMachines() demo branch

### Issue 5: Translation Keys Missing
**Error**: i18n warnings in console
**Solution**:
- Check i18n configuration
- Verify translation files exist
- Add missing translation keys

## Manual Testing Checklist

If automated tests pass but you want to verify manually:

### Visual Checks
- [ ] Page loads without white screen
- [ ] Title "Minhas Máquinas" is visible
- [ ] Stats cards show correct numbers
- [ ] Filter tabs are clickable
- [ ] Machine cards display properly
- [ ] Images/icons load correctly

### Functional Checks
- [ ] "Nova Máquina" button is clickable
- [ ] Filter tabs work (All, Online, Offline)
- [ ] Machine cards show correct status badges
- [ ] Action buttons are visible
- [ ] Hover states work
- [ ] No console errors in browser DevTools

### Demo Mode Specific
- [ ] Demo machines load (from DEMO_MACHINES)
- [ ] Actions show toast notifications
- [ ] No real API calls are made
- [ ] Animations work smoothly
- [ ] No polling/auto-refresh happens

## Screenshots and Artifacts

### Screenshot Locations
All screenshots are saved to `test-results/` directory:
- `machines-page-snapshot.png` - Full page after initial load
- `machines-page-ui-elements.png` - After UI verification
- `test-failed-*.png` - If tests fail (automatic)

### Other Artifacts
- `test-results/` - HTML report
- Videos (if enabled in config)
- Traces (on retry)

## Advanced Testing

### Run Specific Tests
```bash
# Run only the first test
npx playwright test test-machines.spec.js -g "loads without JS errors"

# Run only UI verification test
npx playwright test test-machines.spec.js -g "verify UI elements"
```

### Debug Mode
```bash
# Opens Playwright Inspector for step-by-step debugging
npx playwright test test-machines.spec.js --debug
```

### Headed Mode (Visible Browser)
```bash
# See the browser while tests run
npx playwright test test-machines.spec.js --headed
```

### Generate HTML Report
```bash
npx playwright test test-machines.spec.js --reporter=html
npx playwright show-report
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Machines Page Tests
  run: |
    cd tests
    npx playwright test test-machines.spec.js
  env:
    BASE_URL: http://localhost:4893
```

### Expected CI Behavior
- Retries: 2 (configured in playwright.config.js)
- Parallel: No (CI uses 1 worker)
- Screenshots: Always on failure
- Videos: On retry

## Troubleshooting

### Tests Are Flaky
- Increase timeouts in test
- Check for race conditions
- Verify network stability
- Check for animation delays

### Tests Pass Locally But Fail in CI
- Check BASE_URL environment variable
- Verify server startup time
- Check for different browser versions
- Verify dependencies are installed

### Screenshots Look Wrong
- Check viewport size (default: Desktop Chrome)
- Verify CSS is loaded
- Check for missing fonts
- Verify image paths are correct

## Performance Notes

### Test Execution Time
- Expected total: ~10-15 seconds for all 3 tests
- Test 1: ~5 seconds
- Test 2: ~3 seconds
- Test 3: ~3 seconds

### Timeout Configuration
- Page load: 10 seconds
- Element visibility: 10 seconds
- Test timeout: 30 seconds (Playwright default)

## Next Steps

After running these tests:

1. **If tests pass**: Page is working correctly, no JavaScript errors
2. **If tests fail**: Review error messages, check console output, examine screenshots
3. **For deeper testing**: Run E2E tests for user journeys
4. **For performance**: Add timing metrics and load tests

## Related Tests

- `e2e-journeys/machine-details-actions.spec.js` - Machine card interactions
- `e2e-journeys/accessibility-machinecard.spec.js` - Accessibility testing
- `dumont-midscene.spec.js` - AI-powered visual testing
- `dumont-hybrid.spec.js` - Hybrid Playwright + AI testing

## Support

For issues or questions:
1. Check console output in browser DevTools
2. Review Playwright trace files
3. Examine screenshots in test-results/
4. Check CLAUDE.md for project guidelines
