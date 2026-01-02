# Failover Complete System Test - Quick Start

## TL;DR

```bash
# 1. Start services
cd /Users/marcos/CascadeProjects/dumontcloud
uvicorn src.main:app --reload --port 8000 &
cd web && npm run dev -- --port 4890 &

# 2. Run test
cd tests
./run-failover-complete-test.sh
```

## What It Tests

- ✅ Automatic GPU→CPU failover
- ✅ Manual failover via UI
- ✅ Real-time sync (GPU→CPU)
- ✅ Snapshot creation & restoration
- ✅ Machine migration wizard

## Key Info

| Item | Value |
|------|-------|
| **Runtime** | 5-10 minutes |
| **Cost** | ~$0.20 per run |
| **Environment** | REAL (Vast.ai + GCP) |
| **Cleanup** | Automatic |
| **Port** | 4890 |

## Test Flow

```
Login → Create GPU → Enable CPU Standby → Test Sync →
Manual Failover → Create Snapshot → Restore → Cleanup
```

## Success Criteria

- All phases complete without errors
- Failover completes in < 3 minutes
- Sync latency < 10 seconds
- Total test time < 10 minutes

## View Results

```bash
# Screenshots
ls tests/screenshots/failover-complete/

# HTML Report
npx playwright show-report
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Provisioning timeout | Increase max price to $2.00/hr |
| CPU Standby fails | Check GCP credentials |
| Sync doesn't work | Verify rsync on instances |

## Files

- **Test**: `tests/e2e-journeys/failover-complete-system.spec.js`
- **Runner**: `tests/run-failover-complete-test.sh`
- **Docs**: `tests/e2e-journeys/FAILOVER_COMPLETE_SYSTEM_TEST.md`

---

**Quick Tip**: Run in headed mode (`--headed`) to watch the browser execute the test in real-time!
