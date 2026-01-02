# Next Steps: Failover Testing Roadmap

**Current Status:** VAST.ai integration tested and working ✓
**Date:** 2026-01-02
**Last Test Cost:** $0.0046 USD

---

## Completed Tests

- [x] **VAST.ai Basic Integration** (test_vast_direct_integration.py)
  - Provision GPU
  - SSH access
  - File operations
  - Instance cleanup
  - Duration: ~2 min
  - Cost: $0.0046

---

## Test Roadmap

### Phase 1: Storage Integration (1-2 hours)

#### Test 1.1: Backblaze B2 Snapshot Upload

**Goal:** Create snapshot and upload to B2 bucket

**Script:** `cli/tests/test_b2_snapshot.py`

**Steps:**
1. Provision RTX 4090 (cheapest available)
2. Create test files (100 MB total)
3. Calculate MD5 checksums
4. Create tar.gz snapshot
5. Upload to B2 bucket via rclone
6. Verify upload success
7. Destroy GPU

**Expected Duration:** 5-10 min
**Expected Cost:** $0.02-0.03 USD

**Success Criteria:**
- [ ] Snapshot uploaded to B2
- [ ] File size matches (compressed)
- [ ] No upload errors
- [ ] GPU destroyed after test

---

#### Test 1.2: Snapshot Download and Restore

**Goal:** Download snapshot from B2 and restore to new GPU

**Script:** `cli/tests/test_b2_restore.py`

**Steps:**
1. Download snapshot from B2 (from Test 1.1)
2. Provision new RTX 4090
3. Download snapshot via rclone
4. Extract tar.gz
5. Verify MD5 checksums match
6. Destroy GPU

**Expected Duration:** 5-10 min
**Expected Cost:** $0.02-0.03 USD

**Success Criteria:**
- [ ] Snapshot downloaded successfully
- [ ] Files extracted without errors
- [ ] All MD5 checksums match
- [ ] No data corruption

---

### Phase 2: Full Failover Journey (2-3 hours)

#### Test 2.1: Manual Failover (GPU → Snapshot → GPU)

**Goal:** Complete failover with data verification

**Script:** `cli/tests/test_manual_failover.py`

**Steps:**
1. **GPU 1 (Source):**
   - Provision RTX 4090
   - Install model (Qwen 0.6B via Ollama)
   - Create test dataset (1000 files)
   - Run inference test
   - Create snapshot
   - Upload to B2
   - Destroy GPU 1

2. **GPU 2 (Target):**
   - Provision new RTX 4090
   - Download snapshot from B2
   - Restore files
   - Verify model files exist
   - Run same inference test
   - Compare outputs

**Expected Duration:** 15-20 min
**Expected Cost:** $0.08-0.12 USD

**Success Criteria:**
- [ ] Model restored successfully
- [ ] Inference outputs match
- [ ] No file corruption
- [ ] Total time < 20 min

---

#### Test 2.2: Automated Failover (With Detection)

**Goal:** Detect failure and trigger failover automatically

**Script:** `cli/tests/test_auto_failover.py`

**Steps:**
1. Provision GPU 1 with heartbeat
2. Create files + snapshot
3. Simulate failure (pause GPU 1)
4. Detect failure (heartbeat timeout)
5. Trigger failover:
   - Provision GPU 2
   - Restore latest snapshot
   - Verify data
   - Update DNS/routing
6. Verify application running on GPU 2

**Expected Duration:** 10-15 min
**Expected Cost:** $0.05-0.08 USD

**Success Criteria:**
- [ ] Failure detected within 30s
- [ ] Failover triggered automatically
- [ ] GPU 2 online within 3 min
- [ ] No manual intervention needed

---

### Phase 3: Hibernation & Cost Optimization (3-4 hours)

#### Test 3.1: Auto-Hibernation (Idle Detection)

**Goal:** Detect idle GPU and trigger snapshot + destroy

**Script:** `cli/tests/test_auto_hibernation.py`

**Steps:**
1. Provision GPU
2. Create model + files
3. Simulate idle (GPU < 5% for 3 min)
4. Auto-hibernation triggers:
   - Create snapshot
   - Upload to B2
   - Destroy GPU
5. Verify snapshot exists
6. Verify GPU destroyed

**Expected Duration:** 5-8 min
**Expected Cost:** $0.02-0.03 USD

**Success Criteria:**
- [ ] Idle detected after 3 min
- [ ] Snapshot created automatically
- [ ] GPU destroyed
- [ ] State preserved in B2

---

#### Test 3.2: Wake from Hibernation

**Goal:** Restore GPU from hibernated state

**Script:** `cli/tests/test_wake_from_hibernation.py`

**Steps:**
1. Find hibernated snapshot (from Test 3.1)
2. Provision new GPU
3. Restore snapshot
4. Verify files exist
5. Run application
6. Measure wake time

**Expected Duration:** 3-5 min
**Expected Cost:** $0.01-0.02 USD

**Success Criteria:**
- [ ] GPU restored in < 3 min
- [ ] All files intact
- [ ] Application runs normally
- [ ] Wake time measured

---

### Phase 4: Stress Testing (4-6 hours)

#### Test 4.1: Large Model Snapshot (Llama 7B)

**Goal:** Test snapshot/restore with large model

**Script:** `cli/tests/test_large_model_snapshot.py`

**Steps:**
1. Provision GPU
2. Install Llama 7B (13 GB model)
3. Create snapshot
4. Upload to B2 (measure time)
5. Provision new GPU
6. Download snapshot (measure time)
7. Verify model files
8. Run inference

**Expected Duration:** 20-30 min
**Expected Cost:** $0.08-0.15 USD

**Success Criteria:**
- [ ] 13 GB snapshot uploaded
- [ ] Upload time < 10 min
- [ ] Download time < 10 min
- [ ] Model runs after restore

---

#### Test 4.2: Multiple Failovers (10x)

**Goal:** Test reliability with repeated failovers

**Script:** `cli/tests/test_multiple_failovers.py`

**Steps:**
1. Create initial GPU + files
2. Loop 10 times:
   - Create snapshot
   - Destroy GPU
   - Provision new GPU
   - Restore snapshot
   - Verify files
3. Measure:
   - Success rate
   - Average failover time
   - Total cost

**Expected Duration:** 30-40 min
**Expected Cost:** $0.20-0.30 USD

**Success Criteria:**
- [ ] 10/10 failovers successful
- [ ] No data corruption
- [ ] Average time < 3 min per failover
- [ ] Total cost < $0.30

---

## Estimated Total Budget

| Phase | Tests | Duration | Cost |
|-------|-------|----------|------|
| Phase 1 | 2 tests | 15-20 min | $0.04-0.06 |
| Phase 2 | 2 tests | 25-35 min | $0.13-0.20 |
| Phase 3 | 2 tests | 8-13 min | $0.03-0.05 |
| Phase 4 | 2 tests | 50-70 min | $0.28-0.45 |
| **TOTAL** | **8 tests** | **~2-3 hours** | **$0.48-0.76** |

**Budget buffer:** $1.00
**Safety margin:** 30% extra = $1.30 total

---

## Success Metrics

### Performance Targets

| Metric | Target | Stretch Goal |
|--------|--------|--------------|
| Failover Time | < 5 min | < 3 min |
| Wake Time | < 3 min | < 2 min |
| Snapshot Upload | < 10 min/GB | < 5 min/GB |
| Snapshot Download | < 10 min/GB | < 5 min/GB |
| Success Rate | > 95% | 100% |

### Cost Targets

| Operation | Target Cost | Notes |
|-----------|-------------|-------|
| Small Failover | < $0.05 | < 5 min on RTX 4090 |
| Large Failover | < $0.15 | With 13 GB model |
| Hibernation | < $0.03 | Snapshot + destroy |
| Wake | < $0.02 | Restore + boot |

---

## Development Order

### Week 1: Storage Integration

1. **Day 1-2:** Implement B2 snapshot upload
   - Create `src/services/storage/b2_snapshot.py`
   - Add rclone integration
   - Test upload performance

2. **Day 3-4:** Implement snapshot restore
   - Create restore logic
   - Add verification (MD5)
   - Test download performance

3. **Day 5:** Run Tests 1.1 and 1.2
   - Execute and collect metrics
   - Document issues
   - Fix bugs

### Week 2: Failover Logic

1. **Day 1-2:** Implement failover service
   - Create `src/services/failover/failover_service.py`
   - Add state machine
   - Implement rollback

2. **Day 3-4:** Implement auto-detection
   - Add heartbeat monitoring
   - Implement idle detection
   - Create trigger logic

3. **Day 5:** Run Tests 2.1 and 2.2
   - Execute full failover
   - Measure performance
   - Document results

### Week 3: Optimization & Stress

1. **Day 1-2:** Implement hibernation
   - Create `src/services/hibernation/hibernation_service.py`
   - Add auto-snapshot
   - Test idle detection

2. **Day 3:** Run Tests 3.1 and 3.2
   - Test hibernation cycle
   - Measure wake time
   - Verify data integrity

3. **Day 4-5:** Run Tests 4.1 and 4.2
   - Large model test
   - Multiple failovers
   - Collect final metrics

---

## Monitoring & Observability

### Metrics to Collect

1. **Timing Metrics:**
   - Snapshot creation time
   - Upload time (B2)
   - Download time (B2)
   - GPU provisioning time
   - SSH availability time
   - Total failover time

2. **Data Metrics:**
   - Snapshot size (raw)
   - Snapshot size (compressed)
   - Compression ratio
   - MD5 checksums
   - File count

3. **Cost Metrics:**
   - GPU cost per test
   - Storage cost (B2)
   - Total cost per failover
   - Cost per GB transferred

4. **Reliability Metrics:**
   - Success rate
   - Failure types
   - Retry count
   - Data corruption incidents

---

## Risk Mitigation

### Known Risks

1. **VAST.ai Rate Limiting**
   - Mitigation: Backoff retry logic (already implemented)
   - Max retries: 10 attempts
   - Backoff: Exponential (2s → 60s)

2. **B2 Upload Failures**
   - Mitigation: Retry with exponential backoff
   - Alternative: Use multipart uploads
   - Fallback: Try R2 or S3

3. **GPU Provisioning Timeouts**
   - Mitigation: 10 min timeout
   - Fallback: Try different region
   - Last resort: Use CPU standby

4. **Data Corruption**
   - Mitigation: MD5 verification
   - Pre-snapshot checksum
   - Post-restore verification

5. **Cost Overrun**
   - Mitigation: Max budget limit ($2.00)
   - Auto-stop on budget reached
   - Alert on >50% budget

---

## Cleanup Checklist

After each test, ensure:

- [ ] All GPUs destroyed
- [ ] No orphaned instances
- [ ] Snapshots cataloged
- [ ] Costs logged
- [ ] Metrics saved
- [ ] Errors documented

---

## Quick Start

### Run Next Test (Test 1.1)

```bash
# Create test script
cd /Users/marcos/CascadeProjects/dumontcloud

# Run B2 snapshot test
python3 cli/tests/test_b2_snapshot.py

# Expected output:
# - Snapshot created: /tmp/snapshot-*.tar.gz
# - Uploaded to: b2://dumontcloud-snapshots/snapshots/snapshot-*
# - Size: ~100 MB compressed
# - Time: ~5 min
# - Cost: ~$0.02
```

### Monitor Test Progress

```bash
# Watch logs in real-time
tail -f vast_test_output.log

# Check B2 bucket
rclone ls b2:dumontcloud-snapshots/snapshots/

# List running instances
curl -H "Authorization: Bearer $VAST_API_KEY" \
     https://cloud.vast.ai/api/v0/instances/
```

---

**Ready to proceed?** Start with Test 1.1 (B2 Snapshot Upload)

**Questions?** Review the full test report: `VAST_REAL_INTEGRATION_TEST_REPORT.md`
