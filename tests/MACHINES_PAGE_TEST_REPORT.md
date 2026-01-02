# Machines Page Test Report

## Test Overview
Testing the Machines page at http://localhost:4893/demo-app/machines to verify:

1. No JavaScript errors (ReferenceError, TypeError)
2. Machine cards are visible
3. "Minhas Máquinas" title is present
4. No console errors related to undefined variables
5. Page loads and renders correctly

## Test Specifications

### Test File
- **Location**: `/Users/marcos/CascadeProjects/dumontcloud/tests/test-machines.spec.js`
- **Framework**: Playwright
- **Browser**: Chromium (Desktop Chrome)

### Test Cases

#### 1. Machines page loads without JS errors
- Navigate to login with auto_login parameter
- Wait for redirect to /demo-app
- Navigate to /demo-app/machines
- Track console errors and page errors
- Verify no ReferenceError or TypeError
- Take full-page screenshot

#### 2. Machines page - verify UI elements
- Navigate to machines page
- Verify "Minhas Máquinas" title is visible
- Check for machine cards or empty state
- Verify at least one card is visible (if cards exist)
- Take full-page screenshot

#### 3. Machines page - check for undefined variables in console
- Track all console messages
- Track all page errors
- Categorize errors by type (undefined, ReferenceError, TypeError)
- Report all findings
- Verify zero page errors

## Expected Results

### Page Structure
- **Title**: "Minhas Máquinas" (h1)
- **Subtitle**: "Gerencie suas instâncias de GPU e CPU"
- **New Machine Button**: Link to /demo-app or /app
- **Stats Cards**:
  - GPUs Ativas
  - CPU Backup (conditional)
  - VRAM Total
  - Custo/Hora
- **Filter Tabs**: All, Online, Offline
- **Machine Cards Grid**: Responsive grid (1 col mobile, 2 col tablet, 3 col desktop)

### Machine Card Components
Each machine card should contain:
- GPU name and status badge
- Resource information (VRAM, CPU, RAM, Disk)
- Cost per hour
- SSH connection details
- Action buttons (Start/Pause, Destroy, Snapshot, etc.)
- Sync status indicators
- Failover progress (if applicable)

### Demo Mode Behavior
- Uses DEMO_MACHINES from constants/demoData
- Simulates loading delay (500ms)
- Shows demo toast notifications
- Auto-refreshes disabled (no polling)

## Test Improvements Made

### Removed Discouraged APIs
- **Before**: Used `waitForLoadState('networkidle')` and `waitForTimeout(2000)`
- **After**: Wait for specific elements to be visible with timeout
  - Wait for h1 title to appear
  - Wait for cards or empty state to appear
  - Use explicit element visibility checks

### Enhanced Error Detection
- Separate tracking for:
  - Undefined variable errors
  - ReferenceErrors
  - TypeErrors
- Detailed console message logging
- Full error stack trace capture

### Better Assertions
- Verify page title contains "máquina"
- Check for either machine cards or empty state
- Take screenshots for debugging
- Categorized error reporting

## Common Issues to Watch For

### Potential JavaScript Errors
1. **Undefined variables**: Check imports and variable declarations
2. **Missing dependencies**: Verify all required components are imported
3. **Translation keys**: Ensure all i18n keys exist
4. **API mocking**: Verify demo mode returns proper data structure

### Component Issues
1. **MachineCard props**: All required props must be provided
2. **State management**: Redux store must be properly initialized
3. **Conditional rendering**: Empty state vs. cards vs. error state
4. **Animation states**: New machine highlights, deleting animations

## Running the Tests

```bash
# From tests directory
cd /Users/marcos/CascadeProjects/dumontcloud/tests

# Run all machine tests
npx playwright test test-machines.spec.js

# Run with headed browser (visible)
npx playwright test test-machines.spec.js --headed

# Run in debug mode
npx playwright test test-machines.spec.js --debug

# Run specific test
npx playwright test test-machines.spec.js -g "loads without JS errors"
```

## Test Results
(To be filled after test execution)

### Execution Date
TBD

### Test Status
- [ ] Test 1: Machines page loads without JS errors
- [ ] Test 2: Machines page - verify UI elements
- [ ] Test 3: Machines page - check for undefined variables in console

### Screenshots
- [ ] machines-page-snapshot.png
- [ ] machines-page-ui-elements.png

### Issues Found
(To be documented)

### Fixes Applied
(To be documented)

---

## Notes
- Server must be running on http://localhost:4893
- Auto-login must be configured (?auto_login=demo)
- Demo mode must be properly initialized
- All required components must be built and available
