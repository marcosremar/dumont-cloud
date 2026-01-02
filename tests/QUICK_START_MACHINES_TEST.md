# Quick Start: Machines Page Test

## 60-Second Test Run

### Step 1: Start Server (Terminal 1)
```bash
cd /Users/marcos/CascadeProjects/dumontcloud/web
npm run dev -- --port 4893
```
Wait for: "Local: http://localhost:4893"

### Step 2: Run Tests (Terminal 2)
```bash
cd /Users/marcos/CascadeProjects/dumontcloud/tests
npx playwright test test-machines.spec.js
```

### Step 3: Check Results
```
✓ = PASS (page working correctly)
✗ = FAIL (check error messages)
```

## Test Commands Cheat Sheet

```bash
# Standard run
npx playwright test test-machines.spec.js

# See browser (visible)
npx playwright test test-machines.spec.js --headed

# Debug mode (step-through)
npx playwright test test-machines.spec.js --debug

# Run one test
npx playwright test test-machines.spec.js -g "loads without JS errors"

# HTML report
npx playwright test test-machines.spec.js --reporter=html
npx playwright show-report
```

## What's Being Tested?

1. **No JavaScript errors** - Page loads without ReferenceError/TypeError
2. **UI renders correctly** - Title, cards, buttons visible
3. **Console is clean** - No undefined variables or errors

## Where Are Results?

- **Screenshots**: `test-results/machines-page-*.png`
- **Console output**: Terminal
- **HTML report**: `playwright-report/index.html`

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Server not running | Start server on port 4893 |
| Tests timeout | Wait for server to fully start |
| Permission denied | `chmod +x run-machines-test.sh` |
| Missing dependencies | `npm install` in tests directory |

## Success Looks Like

```
Running 3 tests using 1 worker

✓ test-machines.spec.js:4:3 › Machines page loads without JS errors (5s)
✓ test-machines.spec.js:76:3 › Machines page - verify UI elements (3s)
✓ test-machines.spec.js:111:3 › check for undefined variables in console (3s)

3 passed (11s)
```

## Need More Info?

- Full guide: `MACHINES_PAGE_TESTING_GUIDE.md`
- Summary: `MACHINES_PAGE_TEST_SUMMARY.md`
- Report: `MACHINES_PAGE_TEST_REPORT.md`

---

**Target**: http://localhost:4893/demo-app/machines
**Auto-login**: http://localhost:4893/login?auto_login=demo
