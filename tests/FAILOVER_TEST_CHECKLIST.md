# Failover Complete System Test - Pre-Flight Checklist

Use this checklist before running the comprehensive failover test.

## Environment Setup

### 1. Backend Service

```bash
# Check if backend is running
curl http://localhost:8000/health

# Expected: {"status":"ok"} or similar
```

- [ ] Backend is running on port 8000
- [ ] Health check returns 200 OK

**If not running:**
```bash
cd /Users/marcos/CascadeProjects/dumontcloud
uvicorn src.main:app --reload --port 8000
```

### 2. Frontend Service

```bash
# Check if frontend is running
curl http://localhost:4890

# Expected: HTML content
```

- [ ] Frontend is running on port 4890
- [ ] Auto-login feature is enabled

**If not running:**
```bash
cd /Users/marcos/CascadeProjects/dumontcloud/web
npm run dev -- --port 4890
```

### 3. Environment Variables

Check that all required environment variables are set:

```bash
# Check Vast.ai credentials
echo $VAST_API_KEY

# Check GCP credentials
echo $GCP_PROJECT_ID

# Check R2 credentials
echo $R2_ACCESS_KEY
echo $R2_SECRET_KEY
```

- [ ] `VAST_API_KEY` is set and valid
- [ ] `GCP_PROJECT_ID` is set
- [ ] `R2_ACCESS_KEY` is set
- [ ] `R2_SECRET_KEY` is set
- [ ] `RESTIC_PASSWORD` is set (optional but recommended)

**If missing, add to `.env`:**
```bash
VAST_API_KEY=your_vast_api_key_here
GCP_PROJECT_ID=your_gcp_project
R2_ACCESS_KEY=your_r2_access_key
R2_SECRET_KEY=your_r2_secret_key
RESTIC_PASSWORD=your_restic_password
```

## Playwright Setup

### 4. Dependencies Installed

```bash
cd /Users/marcos/CascadeProjects/dumontcloud/tests

# Check if node_modules exists
ls node_modules/@playwright/test

# Install if missing
npm install
```

- [ ] Playwright is installed
- [ ] All test dependencies are installed

### 5. Browsers Installed

```bash
# Install Playwright browsers
npx playwright install chromium
```

- [ ] Chromium browser is installed
- [ ] Browser version is compatible

## Account Setup

### 6. Vast.ai Account

```bash
# Test Vast.ai API connection
curl -H "Authorization: Bearer $VAST_API_KEY" \
     https://console.vast.ai/api/v0/instances/
```

- [ ] Vast.ai API key is valid
- [ ] Account has sufficient balance (>$1.00)
- [ ] Can create new instances

### 7. GCP Account

```bash
# Verify GCP credentials
gcloud auth list

# Check quota
gcloud compute regions describe us-central1
```

- [ ] GCP credentials are configured
- [ ] Project has compute quota available
- [ ] Can create e2-medium instances

### 8. R2/B2 Storage

```bash
# Test R2 connection (example with rclone)
rclone ls r2:dumontcloud-snapshots --max-depth 1
```

- [ ] R2 bucket exists and is accessible
- [ ] Restic repository is initialized
- [ ] Can write snapshots

## Test Prerequisites

### 9. Auto-Login Feature

Test the auto-login URL manually:

```bash
# Open in browser
open http://localhost:4890/login?auto_login=demo
```

- [ ] Redirects to `/app` automatically
- [ ] No login form shown
- [ ] Dashboard loads successfully

**Expected behavior:**
1. URL: `http://localhost:4890/login?auto_login=demo`
2. Auto-login triggered (no user interaction)
3. Redirect to: `http://localhost:4890/app`
4. Dashboard visible

### 10. Demo Mode Disabled

Check that demo mode is OFF (test requires real data):

```bash
# Open browser console at http://localhost:4890/app
localStorage.getItem('demo_mode')

# Expected: "false" or null
```

- [ ] Demo mode is disabled or not set
- [ ] Test will use real API calls

## Cost & Budget

### 11. Cost Awareness

Review estimated costs:

| Resource | Cost |
|----------|------|
| GPU Instance (5 min) | ~$0.10 |
| CPU Standby (8 min) | ~$0.02 |
| Snapshot Storage | ~$0.002 |
| Network Transfer | ~$0.005 |
| **TOTAL** | **~$0.13** |

- [ ] Understood: This test costs real money (~$0.14 per run)
- [ ] Budget allows for test execution
- [ ] Monitoring costs is enabled

### 12. Cleanup Confirmation

The test automatically destroys all created resources.

- [ ] Understood: Instances will be destroyed after test
- [ ] Monitoring is in place to catch leaked resources
- [ ] Alert configured if cleanup fails

## Network & Connectivity

### 13. Internet Connection

```bash
# Test connectivity to Vast.ai
ping -c 3 console.vast.ai

# Test connectivity to GCP
ping -c 3 www.googleapis.com

# Test connectivity to R2
ping -c 3 cloudflare.com
```

- [ ] Internet connection is stable
- [ ] Can reach Vast.ai API
- [ ] Can reach GCP APIs
- [ ] Can reach R2 endpoints

### 14. Firewall & Ports

Ensure required ports are open:

- [ ] Port 8000 (backend API)
- [ ] Port 4890 (frontend)
- [ ] Port 22 (SSH for instances)
- [ ] Port 873 (rsync for sync)

## Test Files

### 15. Test File Exists

```bash
ls tests/e2e-journeys/failover-complete-system.spec.js
```

- [ ] Test file exists
- [ ] Test file is readable

### 16. Screenshot Directory

```bash
ls -la tests/screenshots/failover-complete/
```

- [ ] Directory exists and is writable
- [ ] Previous screenshots cleared (optional)

### 17. Runner Script

```bash
ls -la tests/run-failover-complete-test.sh
```

- [ ] Script exists and is executable
- [ ] Script can be run from tests directory

## Final Checks

### 18. Dry Run (Optional)

Run a simpler test first to verify setup:

```bash
cd tests
npx playwright test --project=chromium --grep="Login" --headed
```

- [ ] Login test passes
- [ ] Browser opens correctly
- [ ] Screenshots are captured

### 19. Time Allocation

Estimated runtime: **5-10 minutes**

- [ ] Have 10-15 minutes available
- [ ] Not running during critical production hours
- [ ] Can monitor test execution

### 20. Monitoring Ready

Set up monitoring (optional but recommended):

- [ ] Terminal/console visible for logs
- [ ] Browser window visible (if running headed)
- [ ] Network monitor ready (optional)
- [ ] Cost dashboard open (optional)

## Ready to Run!

If all items are checked, you're ready to run the test:

```bash
cd /Users/marcos/CascadeProjects/dumontcloud/tests
./run-failover-complete-test.sh
```

Or via Playwright CLI:

```bash
npx playwright test --project=failover-complete-system --headed
```

## During Test Execution

### What to Watch For

1. **Console Output**: Progress logs for each phase
2. **Browser Window**: Real user interactions (if headed mode)
3. **Screenshots**: Captured at each critical step
4. **Network Traffic**: API calls to Vast.ai, GCP, R2
5. **Time Elapsed**: Should complete in < 10 minutes

### Expected Console Output

```
🚀 Starting comprehensive failover system test

📍 PHASE 1: Login with auto-login
✅ Auto-login completed in 1247ms

📍 PHASE 2: Navigate to Machines page
✅ Machines page loaded

📍 PHASE 3: Create real GPU instance for testing
🖥️ GPU found: RTX 4090
🔄 Provisioning started...
⏳ Waiting for provisioning... (0s elapsed)
⏳ Waiting for provisioning... (5s elapsed)
...
✅ GPU provisioned in 87s

📍 PHASE 4: Enable CPU Standby backup
🔧 Enabling CPU Standby for instance 12345
✅ CPU Standby enabled in 15s

📍 PHASE 5: Test real-time file sync GPU→CPU
📝 Creating test file: sync-test-1704240000000.txt
✅ Test file created on GPU instance
⏳ Waiting for sync to CPU standby...
✅ File synced to CPU standby in 6.8s

📍 PHASE 6: Trigger manual failover
✅ Clicked "Simular Failover" button
✅ Failover progress panel visible
✅ Phase: detecting
✅ Phase: gpu_lost
✅ Phase: failover_to_cpu
...
✅ Failover completed in 134s

[... continues through all phases ...]

============================================================
✅ COMPREHENSIVE FAILOVER TEST COMPLETE
============================================================

📊 Performance Metrics:
  Login:                1.2s
  GPU Provisioning:     87.5s
  CPU Standby Enable:   15.3s
  Sync Verification:    6.8s
  Manual Failover:      134.2s
  Snapshot Create:      45.6s
  Snapshot Restore:     92.1s
  ──────────────────────────────────────────────────────────
  TOTAL TEST TIME:      382.7s

============================================================

🧹 Cleaning up test resources...
🗑️ Destroying instance 12345
✅ Cleanup complete
```

## After Test Completion

### 21. Verify Results

```bash
# Check if test passed
echo $?  # Should be 0

# View screenshots
ls tests/screenshots/failover-complete/

# View HTML report
npx playwright show-report
```

- [ ] Test passed (exit code 0)
- [ ] Screenshots captured at all phases
- [ ] No errors in Playwright report

### 22. Verify Cleanup

```bash
# Check Vast.ai for leaked instances
curl -H "Authorization: Bearer $VAST_API_KEY" \
     https://console.vast.ai/api/v0/instances/ | jq '.instances | length'

# Expected: 0 or only pre-existing instances
```

- [ ] No test instances left running
- [ ] Cost is as expected (~$0.14)
- [ ] No alerts from cost monitoring

### 23. Review Metrics

Open the Playwright HTML report:

```bash
npx playwright show-report
```

Review:
- [ ] Total test duration
- [ ] Each phase timing
- [ ] Any warnings or errors
- [ ] Screenshots at each step

## Troubleshooting

### If Test Fails

1. **Check console output** for error messages
2. **Review screenshots** to see where it failed
3. **Check backend logs** for API errors
4. **Verify credentials** are still valid
5. **Check Vast.ai market** for GPU availability
6. **Review Playwright report** for detailed trace

### Common Issues

| Issue | Solution |
|-------|----------|
| "Backend not running" | Start backend: `uvicorn src.main:app --port 8000` |
| "Frontend not running" | Start frontend: `cd web && npm run dev -- --port 4890` |
| "Provisioning timeout" | Increase max price or try different GPU |
| "CPU Standby fails" | Check GCP credentials and quota |
| "Sync doesn't work" | Verify rsync installed on instances |
| "Snapshot fails" | Check R2 credentials and bucket |

### Support

Need help?

1. Review docs: `tests/e2e-journeys/FAILOVER_COMPLETE_SYSTEM_TEST.md`
2. Check Playwright logs: `npx playwright show-report`
3. View screenshots: `tests/screenshots/failover-complete/`
4. Check backend logs for API errors

---

**Last Updated**: 2026-01-02
**Checklist Version**: 1.0.0

**Quick Start Commands:**
```bash
# Start services
uvicorn src.main:app --port 8000 &
cd web && npm run dev -- --port 4890 &

# Run test
cd tests && ./run-failover-complete-test.sh
```
