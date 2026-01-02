# GPU Wizard - Quick Reference Card

## URL
http://localhost:4895/demo-app

---

## 4-Step Flow

```
1. Region → 2. Hardware → 3. Strategy → 4. Provisioning
```

---

## Step 1: Region Selection

**Click**: EUA button
**Verify**: "Próximo" turns green
**Click**: Próximo
**Time**: ~10s

---

## Step 2: Hardware Selection

**Click**: "Desenvolver" button
**Wait**: Machines load (3s)
**Click**: First machine card (RTX 3060 12GB)
**Verify**: Card highlights green, "Próximo" enabled
**Click**: Próximo
**Time**: ~20s

---

## Step 3: Strategy & Balance

**Verify**: Balance shows $10.00
**Verify**: "Iniciar" button is ENABLED (green)
**Click**: Iniciar
**Time**: ~10s

**Critical**: If "Iniciar" is disabled, there's a bug!

---

## Step 4: Provisioning

**Watch**: 5 machines race
**Wait**: Winner emerges (~18-30s)
**Verify**: Success toast appears
**Click**: "Usar Esta Máquina"
**Time**: ~18-30s

---

## Total Time
55-70 seconds end-to-end

---

## Test Command

```bash
cd /Users/marcos/CascadeProjects/dumontcloud/tests
BASE_URL=http://localhost:4895 npx playwright test wizard-manual-navigation.spec.js --headed --project=wizard-navigation
```

---

## Success Checklist

- [ ] Step 1: Region selected, navigates to Step 2
- [ ] Step 2: Machines load, selection works, navigates to Step 3
- [ ] Step 3: Balance shows $10.00, "Iniciar" enabled, starts provisioning
- [ ] Step 4: Race completes, winner found, no errors

---

## Key Files

1. Test: `wizard-manual-navigation.spec.js`
2. Summary: `WIZARD_NAVIGATION_SUMMARY.md`
3. Walkthrough: `WIZARD_NAVIGATION_WALKTHROUGH.md`
4. Quick Ref: `WIZARD_QUICK_REFERENCE.md` (this file)

---

## Screenshots

Location: `test-results/wizard-navigation/`

- `00-initial-load.png`
- `01-step1-before.png`
- `01-step1-after-selection.png`
- `02-step2-before.png`
- `02-step2-machines.png`
- `03-step3-before.png`
- `04-provisioning-started.png`
- `05-final-state.png`

---

## Common Issues

| Issue | Solution |
|-------|----------|
| "Iniciar" disabled | Check balance displays $10.00 |
| No machines load | Wait 3-5 seconds, check console |
| All machines fail | Normal 5-20% failure rate, should retry |
| Stuck at provisioning | Timeout at 30s, can cancel |

---

## Demo Mode Config

- Balance: $10.00 (mocked)
- Machines: 13 demo offers
- Boot time: 15-30s
- Failure rate: 5% (verified) / 20% (unverified)

---

Created: 2026-01-02
Last Updated: 2026-01-02
