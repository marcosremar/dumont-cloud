# Deploy Wizard Timing Test

## Overview

This automated test verifies that the deploy wizard respects the batch timing requirements:

- **BATCH_TIMEOUT = 15s** (time to wait for SSH on each batch)
- **BATCH_SIZE = 5** (5 machines per batch)
- **MAX_BATCHES = 3** (maximum of 15 machines total)

## Problem Being Debugged

The deploy wizard was failing too quickly - batches weren't waiting the full 15 seconds for SSH before moving to the next batch. This test helps identify timing issues by:

1. Monitoring backend logs in real-time
2. Capturing UI state during provisioning
3. Analyzing batch durations and events
4. Verifying if batches respect the 15s timeout

## Test Files

- `deploy-wizard-timing.spec.js` - Main test file
- `src/services/deploy_wizard.py` - Backend deploy wizard service

## Running the Tests

### Quick UI Test (No Real Provisioning)

Tests only the UI elements without actually creating machines:

```bash
cd tests
npm run test:deploy -- --grep "Teste rápido de UI"
```

This verifies:
- ✓ "Configuração Guiada" section exists
- ✓ GPU buttons are present
- ✓ Tier buttons are present
- ✓ "Iniciar" button is available

### Full Timing Test (Real Provisioning)

**⚠️ WARNING: This creates REAL machines on vast.ai and costs money!**

```bash
cd tests
npm run test:deploy -- --grep "respeita timeout de 15s"
```

Or run all deploy tests:

```bash
cd tests
npm run test:deploy
```

### Headed Mode (See Browser)

To watch the test run in a visible browser window:

```bash
cd tests
npm run test:deploy:headed
```

## What the Test Does

### 1. Backend Log Monitoring

The test spawns a process to monitor backend logs in real-time:

```
orb run -m dumontcloud tail -f /tmp/dumont-backend.log
```

It captures:
- Batch start events
- Instance creation
- SSH ready events
- Batch timeouts
- Instance destruction

### 2. UI Monitoring

The test navigates through the dashboard and:

1. Clicks "Configuração Guiada"
2. Selects region (if available)
3. Selects GPU (RTX 4090 preferred)
4. Selects tier (Fast preferred)
5. Clicks "Iniciar"
6. Monitors provisioning progress in the UI

### 3. Timing Analysis

After the test completes, it analyzes the captured logs to determine:

- **Batch durations**: How long each batch took
- **Events per batch**: What happened during each batch
- **Timing violations**: If any batch failed faster than 15s

## Example Output

```
📊 ANÁLISE DE BATCHES:
================================================================================

Batch 1:
  Duração: 14.8s
  Eventos: 8
  ✅ Timing OK
  [+0.0s] batch_start: [Batch 1] Iniciando batch de 5 máquinas
  [+1.2s] instance_create: Creating instance 29370851
  [+1.5s] instance_create: Creating instance 29370852
  ...
  [+14.8s] batch_timeout: Batch 1 timeout - moving to next batch

Batch 2:
  Duração: 3.2s
  Eventos: 2
  ⚠️  FALHOU MUITO RÁPIDO! (esperado ~15s, obteve 3.2s)
  [+0.0s] batch_start: [Batch 2] Iniciando batch de 5 máquinas
  [+3.2s] batch_timeout: Batch 2 timeout - no instances available

================================================================================
```

## Interpreting Results

### ✅ Good (Timing Respected)

```
Batch 1:
  Duração: 14.8s
  Eventos: 8
  ✅ Timing OK
```

The batch took ~15s as expected, meaning it waited the full timeout before moving to the next batch.

### ❌ Bad (Too Fast - Bug!)

```
Batch 2:
  Duração: 3.2s
  Eventos: 2
  ⚠️  FALHOU MUITO RÁPIDO! (esperado ~15s, obteve 3.2s)
```

The batch failed after only 3.2s instead of waiting the full 15s. This indicates a bug in the deploy wizard logic - it's not respecting the BATCH_TIMEOUT.

## Common Issues

### Test Can't Find "Iniciar" Button

The WizardForm component only shows the "Iniciar" button after you:

1. Select a region (Step 1)
2. Select a use case (Step 2)
3. Select a machine (Step 3)
4. Configure settings (Step 4)

The test needs to navigate through these steps first.

### Batches Failing Immediately

If all batches fail in under 5 seconds, check:

1. vast.ai API is accessible
2. API key is valid
3. Region filters aren't too restrictive
4. GPU availability in the selected region

### Backend Logs Not Captured

Ensure the backend is running and logs are being written to:

```
/tmp/dumont-backend.log
```

You can manually check logs with:

```bash
orb run -m dumontcloud tail -f /tmp/dumont-backend.log
```

## Debugging the Deploy Wizard

If the test reveals timing issues, check these files:

### Backend (`src/services/deploy_wizard.py`)

```python
# Configuracoes de timeout e batches - OTIMIZADO
BATCH_TIMEOUT = 15   # 15s timeout por batch para SSH ficar pronto
CHECK_INTERVAL = 2   # 2s entre verificacoes
BATCH_SIZE = 5       # maquinas por batch
MAX_BATCHES = 3      # maximo de batches (15 maquinas total)
```

Key areas to check:

1. **Batch loop** (~line 200): Ensure it waits full BATCH_TIMEOUT
2. **SSH polling** (~line 250): Check CHECK_INTERVAL timing
3. **Early termination** (~line 280): Verify it doesn't exit too early

### Frontend (`web/src/components/dashboard/WizardForm.jsx`)

Check provisioning state management:

- `provisioningCandidates` - List of machines being created
- `provisioningWinner` - First machine to become ready
- `currentRound` - Which batch we're on

## Expected Behavior

### Correct Flow

1. **Batch 1 starts** (0s)
   - Create 5 instances
   - Poll SSH every 2s
   - Wait up to 15s for any to become ready
   - If winner found: cleanup others, complete
   - If timeout (15s): move to Batch 2

2. **Batch 2 starts** (15s)
   - Same as Batch 1
   - If timeout (30s): move to Batch 3

3. **Batch 3 starts** (30s)
   - Same as Batch 1
   - If timeout (45s): give up, show error

### Bug: Batches Failing Too Fast

If batches are failing in under 15s, the issue is likely:

1. **Timeout not being respected** - Check `asyncio.wait_for` calls
2. **Early termination on errors** - Check exception handling
3. **API rate limiting** - Check for 429 errors
4. **as_completed timeout** - Verify it's using BATCH_TIMEOUT

## Next Steps

If timing violations are found:

1. **Add more logging** to deploy_wizard.py at each decision point
2. **Check asyncio timing** - Ensure timeouts are in seconds, not milliseconds
3. **Verify as_completed usage** - Should wait full timeout before yielding
4. **Test with single batch** - Isolate to one batch to debug timing

## Contact

For questions about this test, check:

- `tests/deploy-wizard-timing.spec.js` - Test implementation
- `src/services/deploy_wizard.py` - Deploy wizard logic
- GitHub Issues - Report bugs found by this test
