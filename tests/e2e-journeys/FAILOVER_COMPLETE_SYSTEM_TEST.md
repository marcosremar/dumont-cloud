# Failover Complete System Test

**Test File**: `failover-complete-system.spec.js`
**Type**: End-to-End Vibe Test
**Environment**: REAL (Vast.ai + GCP)
**Runtime**: ~5-10 minutes
**Cost**: ~$0.20-0.50 per run

## Overview

This is a comprehensive end-to-end test that validates ALL failover scenarios in Dumont Cloud. Unlike typical unit tests, this is a "vibe test" - it simulates real user behavior on a staging/production environment, creates actual resources, and measures real performance metrics.

## What This Test Covers

### 1. Automatic GPU→CPU Failover
- Creates a real GPU instance on Vast.ai
- Enables CPU Standby backup on GCP
- Simulates GPU failure/interruption
- Verifies automatic failover to CPU instance
- Measures failover latency across all phases

### 2. Manual Failover via UI
- Tests manual failover trigger button
- Monitors failover progress panel
- Validates phase transitions (detecting → gpu_lost → failover_to_cpu → searching_gpu → provisioning → restoring → complete)
- Verifies new GPU instance is provisioned
- Confirms original GPU is destroyed

### 3. Real-Time Sync Verification
- Creates a test file on GPU instance
- Waits for automatic sync to CPU Standby
- Verifies file appears on CPU within seconds
- Validates sync latency (should be < 5s)

### 4. Snapshot Creation & Restoration
- Creates a snapshot of running instance
- Destroys the instance
- Restores from snapshot via UI
- Verifies all files and state are restored
- Measures snapshot and restore latency

### 5. Machine Migration Testing
- Opens migration wizard
- Validates GPU selection options
- Tests migration flow (UI verification only, not executed to save time)

## Test Architecture

### Core Principles (NEVER VIOLATE)

1. **NO MOCKS** - All API calls are real
2. **REAL RESOURCES** - Creates actual GPU instances on Vast.ai
3. **REAL METRICS** - Measures actual latency, not simulated
4. **CLEANUP** - Destroys all created resources at the end

### Test Flow

```
1. Login (auto-login via URL parameter)
   └─> Time: ~1-2s

2. Navigate to Machines page
   └─> Verify existing instances

3. Create GPU Instance
   ├─> Provision RTX 4090 (max $1.50/hr)
   ├─> Wait for "Online" status
   └─> Time: ~60-120s (depends on Vast.ai availability)

4. Enable CPU Standby
   ├─> Toggle CPU Standby switch
   ├─> Wait for GCP instance to provision
   └─> Time: ~10-20s

5. Verify Real-Time Sync
   ├─> Create test file on GPU: echo "test" > /workspace/sync-test.txt
   ├─> Wait for sync to CPU
   ├─> Verify file exists on CPU Standby
   └─> Time: ~5-8s

6. Manual Failover
   ├─> Click "Simular Failover" button
   ├─> Monitor phases:
   │   ├─> detecting
   │   ├─> gpu_lost
   │   ├─> failover_to_cpu
   │   ├─> searching_gpu
   │   ├─> provisioning
   │   ├─> restoring
   │   └─> complete
   └─> Time: ~60-180s

7. Create Snapshot
   ├─> Trigger snapshot via API
   ├─> Wait for snapshot to complete
   └─> Time: ~30-60s

8. Destroy & Restore
   ├─> Destroy instance
   ├─> Restore from snapshot
   ├─> Wait for new instance to provision
   └─> Time: ~60-120s

9. Migration UI Test
   └─> Verify migration wizard (UI only)

10. Cleanup
    └─> Destroy all test instances
```

## Performance Metrics

The test measures and reports:

| Metric | Expected Range | Description |
|--------|---------------|-------------|
| Login Time | 1-3s | Auto-login via URL parameter |
| GPU Provisioning | 60-180s | Vast.ai instance creation |
| CPU Standby Enable | 10-30s | GCP VM provisioning |
| Sync Verification | 5-10s | File sync GPU→CPU |
| Manual Failover | 60-180s | Complete failover cycle |
| Snapshot Create | 30-90s | Restic snapshot to R2 |
| Snapshot Restore | 60-180s | Restore + provision new GPU |
| **TOTAL** | **300-600s** | **5-10 minutes** |

## Running the Test

### Prerequisites

1. **Backend running** on port 8000:
   ```bash
   cd /Users/marcos/CascadeProjects/dumontcloud
   uvicorn src.main:app --reload --port 8000
   ```

2. **Frontend running** on port 4890:
   ```bash
   cd /Users/marcos/CascadeProjects/dumontcloud/web
   npm run dev -- --port 4890
   ```

3. **Environment variables** configured:
   ```bash
   VAST_API_KEY=your_vast_api_key
   GCP_PROJECT_ID=your_gcp_project
   R2_ACCESS_KEY=your_r2_access_key
   R2_SECRET_KEY=your_r2_secret_key
   ```

### Run via Script (Recommended)

```bash
cd /Users/marcos/CascadeProjects/dumontcloud/tests
./run-failover-complete-test.sh
```

This script:
- Checks if backend/frontend are running
- Creates screenshot directory
- Warns about cost implications
- Runs the test in headed mode
- Shows progress in real-time

### Run via Playwright CLI

```bash
cd /Users/marcos/CascadeProjects/dumontcloud/tests

# Headed mode (watch the browser)
npx playwright test --project=failover-complete-system --headed

# Headless mode
npx playwright test --project=failover-complete-system

# Debug mode (step through)
npx playwright test --project=failover-complete-system --debug
```

### Run Specific Scenarios

The test is a single comprehensive journey, but you can modify the code to skip phases by commenting out sections.

## Screenshots

Screenshots are automatically captured at each critical step:

```
tests/screenshots/failover-complete/
├── 2026-01-02-10-00-00-01-logged-in.png
├── 2026-01-02-10-00-02-02-machines-page.png
├── 2026-01-02-10-00-05-03-wizard-opened.png
├── 2026-01-02-10-00-08-04-hardware-selection.png
├── 2026-01-02-10-00-12-05-strategy-selection.png
├── 2026-01-02-10-00-15-06-provisioning-started.png
├── 2026-01-02-10-02-30-08-instance-online.png
├── 2026-01-02-10-02-45-09-instance-details.png
├── 2026-01-02-10-03-00-10-standby-enabled.png
├── 2026-01-02-10-03-15-11-failover-triggered.png
├── 2026-01-02-10-03-20-12-failover-progress.png
├── 2026-01-02-10-05-00-14-failover-complete.png
├── 2026-01-02-10-06-00-15-restore-initiated.png
├── 2026-01-02-10-08-00-16-restore-complete.png
├── 2026-01-02-10-08-15-17-migration-modal.png
└── 2026-01-02-10-08-30-18-final-state.png
```

## Cost Breakdown

Approximate costs per test run:

| Resource | Duration | Cost |
|----------|----------|------|
| GPU Instance (RTX 4090) | ~5 min | ~$0.10 |
| CPU Standby (GCP e2-medium) | ~8 min | ~$0.02 |
| Snapshot Storage (R2) | ~100MB | ~$0.001 |
| Data Transfer | ~500MB | ~$0.01 |
| **TOTAL** | | **~$0.13** |

Note: Actual costs may vary based on:
- Vast.ai spot market prices
- GCP region selected
- Snapshot data size
- Network transfer volume

## Troubleshooting

### Test Fails at Provisioning

**Symptom**: Test times out waiting for GPU instance to provision

**Causes**:
- No available GPUs at specified price
- Vast.ai API rate limiting
- Network connectivity issues

**Solutions**:
1. Increase `maxPrice` parameter (e.g., from $1.50 to $2.00/hr)
2. Try different GPU type (RTX 3090 instead of RTX 4090)
3. Wait a few minutes and retry

### Test Fails at CPU Standby Enable

**Symptom**: CPU Standby toggle doesn't work

**Causes**:
- GCP credentials not configured
- Insufficient GCP quota
- Region not supported

**Solutions**:
1. Verify GCP credentials in `.env`
2. Check GCP quota in console
3. Try different region (e.g., us-central1)

### Sync Verification Fails

**Symptom**: File doesn't appear on CPU Standby

**Causes**:
- rsync daemon not running
- SSH connection issues
- Firewall blocking port 873

**Solutions**:
1. Check SSH connectivity to both instances
2. Verify rsync is installed and running
3. Check firewall rules allow port 873

### Failover Takes Too Long

**Symptom**: Failover exceeds 3 minute timeout

**Causes**:
- No available GPUs in market
- Snapshot restore is slow
- Network congestion

**Solutions**:
1. Increase `MAX_WAIT_FAILOVER` constant
2. Use smaller snapshot (less data)
3. Pre-warm GPU pool for faster failover

## Extending the Test

### Add New Failover Scenario

1. Create a new helper function:
   ```javascript
   async function testNewScenario(page, instanceId) {
     console.log('Testing new scenario...');
     // Your test logic
     return performanceMetric;
   }
   ```

2. Add phase to main test:
   ```javascript
   console.log('\n📍 PHASE X: Test new scenario');
   testMetrics.newScenario = await testNewScenario(page, testInstanceId);
   ```

3. Add metric to report:
   ```javascript
   console.log(`  New Scenario:         ${(testMetrics.newScenario / 1000).toFixed(1)}s`);
   ```

### Test Different GPU Types

Modify `createTestGPUInstance` call:

```javascript
// Test with RTX 3090 instead
const gpuResult = await createTestGPUInstance(page, 'RTX_3090', 1.2);

// Test with A100
const gpuResult = await createTestGPUInstance(page, 'A100_PCIE', 3.0);
```

### Test Different Failover Strategies

Add parameter to `triggerManualFailover`:

```javascript
async function triggerManualFailover(page, instanceId, strategy = 'both') {
  // strategy can be: 'warm_pool', 'cpu_standby', 'both'
  const body = { force_strategy: strategy };
  // ... rest of logic
}
```

## CI/CD Integration

### GitHub Actions

Add to `.github/workflows/e2e-failover.yml`:

```yaml
name: E2E Failover Tests

on:
  schedule:
    - cron: '0 2 * * *' # Run daily at 2 AM
  workflow_dispatch: # Allow manual trigger

jobs:
  failover-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: cd tests && npm ci

      - name: Start backend
        run: |
          cd /app
          uvicorn src.main:app --port 8000 &
          sleep 10

      - name: Start frontend
        run: |
          cd web
          npm run dev -- --port 4890 &
          sleep 5

      - name: Run failover test
        run: cd tests && npx playwright test --project=failover-complete-system
        env:
          VAST_API_KEY: ${{ secrets.VAST_API_KEY }}
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
          R2_ACCESS_KEY: ${{ secrets.R2_ACCESS_KEY }}
          R2_SECRET_KEY: ${{ secrets.R2_SECRET_KEY }}

      - name: Upload screenshots
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: failover-screenshots
          path: tests/screenshots/failover-complete/
```

### Alerts on Failure

Configure Slack/Email alerts when failover test fails:

```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Failover E2E test failed! Check metrics.'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## Monitoring & Metrics

### Track Metrics Over Time

Save metrics to database for trend analysis:

```javascript
// At end of test
await page.evaluate(async (metrics) => {
  await fetch('/api/v1/test-metrics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      test_name: 'failover-complete-system',
      timestamp: new Date().toISOString(),
      metrics
    })
  });
}, testMetrics);
```

### Alert on Degradation

Set thresholds and alert when exceeded:

```javascript
// After test completes
if (testMetrics.manualFailover > 180000) { // 3 minutes
  console.error('⚠️ ALERT: Failover latency exceeded SLA!');
  // Send alert to monitoring system
}

if (testMetrics.syncVerification > 10000) { // 10 seconds
  console.error('⚠️ ALERT: Sync latency degraded!');
}
```

## Best Practices

1. **Run during off-peak hours** - GPU prices are lower
2. **Clean up resources** - Always destroy test instances
3. **Monitor costs** - Track Vast.ai/GCP spending
4. **Version snapshots** - Tag test snapshots for easy cleanup
5. **Parallel testing** - Don't run multiple failover tests simultaneously
6. **Log everything** - Keep detailed logs for debugging
7. **Screenshot liberally** - Capture visual state at each step

## Related Tests

- `cpu-standby-failover.spec.js` - CPU Standby specific tests (demo mode)
- `failover-complete-journeys.spec.js` - Failover UI journeys (demo mode)
- `failover-strategy-selection.spec.js` - Strategy selection tests (demo mode)
- `machine-details-actions.spec.js` - Machine actions including failover

## Support

For issues or questions:
1. Check Playwright HTML report: `npx playwright show-report`
2. Review screenshots in `tests/screenshots/failover-complete/`
3. Check backend logs for API errors
4. Verify Vast.ai/GCP credentials
5. Contact: marcos@dumontcloud.com

---

**Last Updated**: 2026-01-02
**Test Version**: 1.0.0
**Playwright Version**: 1.40+
**Node Version**: 18+
