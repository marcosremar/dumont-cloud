# Fine-Tuning Vibe Test - Quick Start Guide

This guide will help you run the Fine-Tuning vibe test for the Dumont Cloud platform.

## What This Test Does

The Fine-Tuning vibe test simulates a **REAL user creating a fine-tuning job** through the UI:

1. Navigates to the Fine-Tuning page (`/app/finetune`)
2. Clicks "New Fine-Tune Job" button
3. Goes through 4-step wizard:
   - **Step 1**: Selects Phi-3 Mini model (smallest, 8GB VRAM)
   - **Step 2**: Configures dataset from HuggingFace URL
   - **Step 3**: Sets job name, GPU type (A100), and parameters
   - **Step 4**: Reviews and launches the job
4. Verifies the job appears in the dashboard
5. Tests action buttons (Refresh, Logs)

**IMPORTANT**: This test creates a REAL fine-tuning job on your staging/production environment via SkyPilot on GCP.

## Prerequisites

1. **Backend running** with Fine-Tuning API endpoints:
   - `GET /api/finetune/jobs` - List jobs
   - `POST /api/finetune/jobs` - Create job
   - `GET /api/finetune/jobs/{id}/logs` - Get logs

2. **Frontend running**:
   - Dev server: `http://localhost:5173`
   - Or production build

3. **Authentication configured**:
   - Valid auth token in `tests/.auth/user.json`
   - Or run auth setup: `npx playwright test tests/e2e-journeys/auth.setup.js`

4. **SkyPilot configured** (for backend):
   - GCP credentials set up
   - SkyPilot installed: `pip install skypilot[gcp]`
   - Cloud authenticated: `sky check`

## Quick Start

### 1. Install Dependencies

```bash
# Install Playwright
npm install

# Install Chromium browser
npx playwright install chromium
```

### 2. Start the Application

```bash
# Terminal 1: Backend
python src/main.py

# Terminal 2: Frontend
cd web && npm run dev
```

### 3. Run the Test

```bash
# Run the fine-tuning vibe test
npx playwright test tests/vibe/finetune-journey-vibe.spec.js --project=chromium

# OR with visible browser (headed mode)
npx playwright test tests/vibe/finetune-journey-vibe.spec.js --headed

# OR with Playwright UI (best for debugging)
npx playwright test tests/vibe/finetune-journey-vibe.spec.js --ui
```

## Expected Output

```
========================================
VIBE TEST: Fine-Tuning Job Creation Journey
Environment: REAL (no mocks)
Model: Phi-3 Mini (3.8B params, 8GB VRAM)
========================================

STEP 1: Login and navigate to Fine-Tuning
⏱️  Time: 1234ms
✅ Status: Authenticated and navigated to Fine-Tuning page
✅ Validated: URL contains /app/finetune

STEP 2: Verify Fine-Tuning page loaded correctly
⏱️  Time: 567ms
✅ Validated: "Fine-Tuning" header visible
✅ Validated: "New Fine-Tune Job" button visible
✅ Validated: Stats cards visible
📊 Existing fine-tuning jobs: 2

STEP 3: Click "New Fine-Tune Job" button
⏱️  Time: 345ms
✅ Validated: Modal opened
✅ Validated: Step 1 of 4 shown

...

========================================
🎉 VIBE TEST COMPLETE!
========================================
Total journey time: 23456ms (23.46s)

📊 Step Breakdown:
  Step 1 (Login & Nav):       1234ms
  Step 2 (Page Load):         567ms
  Step 3 (Open Modal):        345ms
  Step 4 (Select Model):      678ms
  Step 5 (Dataset):           890ms
  Step 6 (Configuration):     1234ms
  Step 7 (Review & Launch):   456ms
  Step 8 (Modal Close):       123ms
  Step 9 (Verify Job):        2345ms
  Step 10 (Stats):            234ms
  Step 11 (Actions):          567ms

✅ All validations passed:
  ✓ Real environment (no mocks)
  ✓ Modal 4-step wizard completed
  ✓ Phi-3 Mini model selected
  ✓ Dataset configured from HuggingFace
  ✓ Job created: test-finetune-phi3-1703001234567
  ✓ Job visible in dashboard
  ✓ Stats updated
  ✓ Action buttons functional
========================================
```

## Test Scenarios

The test file includes 3 test scenarios:

### 1. Main Journey (Complete Job Creation)
```bash
npx playwright test tests/vibe/finetune-journey-vibe.spec.js -g "should complete full"
```
Creates a real fine-tuning job through the entire UI flow.

### 2. Empty Jobs State
```bash
npx playwright test tests/vibe/finetune-journey-vibe.spec.js -g "should handle empty"
```
Verifies the empty state UI when no jobs exist.

### 3. Filter Tabs Navigation
```bash
npx playwright test tests/vibe/finetune-journey-vibe.spec.js -g "should display correct filter"
```
Tests the All/Running/Completed/Failed filter tabs.

## Debugging

### View Test in Real-Time

```bash
# Run with headed browser to see what's happening
npx playwright test tests/vibe/finetune-journey-vibe.spec.js --headed --slowmo=1000
```

### Debug Mode (Step Through)

```bash
# Open Playwright Inspector
npx playwright test tests/vibe/finetune-journey-vibe.spec.js --debug
```

### View Screenshots

On failure, Playwright saves screenshots automatically:
```bash
ls test-results/vibe-finetune-journey*/
```

### Generate Trace

```bash
# Run with tracing
npx playwright test tests/vibe/finetune-journey-vibe.spec.js --trace on

# View the trace (detailed timeline)
npx playwright show-trace test-results/.../trace.zip
```

## Common Issues

### Issue 1: Modal doesn't open
**Symptom**: Test fails at Step 3
**Solution**: Check if Fine-Tuning page loaded correctly. Try:
```bash
npx playwright test --headed --slowmo=2000
```

### Issue 2: Job not visible after creation
**Symptom**: Test fails at Step 9
**Possible causes**:
- API call failed (check backend logs)
- Job creation error (check browser console)
- Slow response (try increasing timeout)

**Debug**:
```javascript
// In the test, increase timeout
const jobVisible = await jobCard.isVisible({ timeout: 10000 });
```

### Issue 3: Authentication failed
**Symptom**: Redirected to login page
**Solution**: Re-run auth setup:
```bash
npx playwright test tests/e2e-journeys/auth.setup.js
```

### Issue 4: Backend not responding
**Symptom**: Timeouts, network errors
**Solution**: Verify backend is running:
```bash
curl http://localhost:5000/api/finetune/jobs
```

## Metrics Captured

The test captures performance metrics for:

- **Login & Navigation**: Time to load Fine-Tuning page
- **Page Load**: Time for dashboard to render
- **Modal Open**: Time for wizard to appear
- **Step Navigation**: Time to move between wizard steps
- **API Response**: Time for job creation API call
- **UI Update**: Time for job to appear in dashboard

These metrics help identify:
- Slow API endpoints
- Heavy React re-renders
- Network latency issues
- Database query performance

## What Gets Created

This test creates a **REAL fine-tuning job** with:

- **Model**: `unsloth/Phi-3-mini-4k-instruct-bnb-4bit`
- **Dataset**: HuggingFace Alpaca cleaned dataset
- **GPU**: A100 40GB (configurable in test)
- **Config**: Default LoRA settings (rank=16, alpha=16, lr=0.0002)

The job will:
1. Be submitted to SkyPilot
2. Provision a GCP VM with A100 GPU
3. Download the model and dataset
4. Start the fine-tuning process
5. Run for 1 epoch (default)

**Cost Estimate**: ~$1.50/hour for A100 40GB

## Cleanup

After the test, you may want to cancel the job to avoid costs:

### Via UI
1. Go to `/app/finetune`
2. Find the test job (`test-finetune-phi3-*`)
3. Click "Cancel" button

### Via API
```bash
# List jobs to find the ID
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/finetune/jobs

# Cancel the job
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/finetune/jobs/{JOB_ID}/cancel
```

### Via SkyPilot
```bash
# List all SkyPilot clusters
sky status

# Cancel the cluster
sky down finetune-test-*
```

## Next Steps

1. **Monitor the job**: Watch logs in the UI
2. **Wait for completion**: Takes ~30-60 min depending on dataset size
3. **Download the model**: Use the download button when complete
4. **Test the model**: Deploy it and test inference

## Advanced: Test Against Production

To run against production (https://dumontcloud.com):

1. Edit `playwright.config.js`:
```javascript
use: {
  baseURL: 'https://dumontcloud.com',
}
```

2. Run the test:
```bash
npx playwright test tests/vibe/finetune-journey-vibe.spec.js --project=chromium
```

**WARNING**: This will create a REAL job on production!

## Support

- GitHub Issues: [dumont-cloud/issues](https://github.com/dumont-cloud/issues)
- Slack: #vibe-tests channel
- Email: support@dumontcloud.com

---

**Last Updated**: 2025-12-19
**Maintained By**: Dumont Cloud Team
