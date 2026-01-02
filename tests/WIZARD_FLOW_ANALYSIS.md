# GPU Provisioning Wizard Flow Analysis

## Overview
The GPU provisioning wizard at `/demo-app` is a 4-step process that guides users through:
1. **Region Selection** - Choose geographic location
2. **Hardware Selection** - Select GPU tier and specific machine
3. **Strategy/Failover** - Configure failover strategy
4. **Provisioning** - Race provisioning with live progress

## Flow Architecture

### Step 1: Region Selection
- **Component**: `WizardForm` step 1
- **User Actions**:
  - Click "EUA" button (or other region)
  - Button has `data-testid="region-eua"`
  - Selection shows tag with region name
- **Validation**: Must select a location before proceeding
- **Next Button**: Enabled when `selectedLocation` is set

### Step 2: Hardware Selection
- **Component**: `WizardForm` step 2
- **User Actions**:
  1. Click use case button (e.g., "Desenvolver") - `data-testid="use-case-develop"`
  2. Wait for machines to load (uses DEMO_OFFERS in demo mode)
  3. Click on a machine card - `data-testid="machine-{id}"`
- **Data Flow**:
  - Selecting tier triggers `useEffect` to fetch machines
  - In demo mode: Uses `DEMO_OFFERS` from constants
  - Filters based on tier (Lento, Medio, Rapido, Ultra)
  - Displays 3 recommended machines with labels
- **Validation**: Must select a tier AND a machine
- **Next Button**: Enabled when both `selectedTier` and machine are selected

### Step 3: Strategy/Failover
- **Component**: `WizardForm` step 3
- **Default Selection**: `snapshot_only` (automatically selected)
- **User Actions**: Can change failover strategy or use default
- **Balance Check**: Fetches user balance via `/api/v1/balance`
- **Validation**:
  - Checks minimum balance ($0.10)
  - Validates location and tier still selected
- **Next Button**: Actually labeled "Iniciar" - triggers provisioning

### Step 4: Provisioning
- **Trigger**: Clicking "Iniciar" in Step 3 calls `handleWizardSearchWithRaceIntegrated()`
- **Flow**:
  1. `handleWizardSearchWithRaceIntegrated()`
     - Fetches offers based on tier
     - In demo mode: Uses filtered `DEMO_OFFERS`
  2. `startProvisioningRaceIntegrated(offers, isDemoMode, round=1)`
     - Takes top 5 offers
     - Sets `raceCandidates` state
     - Calls provisioning race function
  3. **Demo Mode**: `runDemoProvisioningRace(candidates)`
     - Simulates realistic provisioning phases
     - Progress: creating (0-15%) → connecting (15-40%) → loading (40-85%) → running (85-100%)
     - Random failures based on machine verification status
     - Winner selection when first machine reaches 100%
  4. **Real Mode**: `runRealProvisioningRaceWithMultiRound(candidates, offers, round)`
     - Creates actual instances via API
     - Polls for status updates
     - Destroys losing instances automatically
     - Supports multi-round (up to 3 rounds if all fail)
- **Display**:
  - Shows round indicator: `[data-testid="wizard-round-indicator"]`
  - Shows timer: `[data-testid="wizard-timer"]`
  - Shows candidates: `[data-testid="provisioning-candidate-{index}"]`
  - Progress bars for each machine
  - Status messages (creating, connecting, loading, running, failed)
- **Completion**:
  - Winner found: Shows "Usar Esta Máquina" button
  - All failed: Error message, can retry or go back

## Demo Mode Configuration

### Demo Offers
Location: `web/src/components/dashboard/constants.js`
- 13 pre-configured demo machines
- Price range: $0.08/h - $4.00/h
- Covers all tiers (Lento, Medio, Rapido, Ultra)
- Mix of verified and unverified machines
- Different regions (US, EU)

### Demo Mode Detection
Function: `isDemoMode()` in `utils/api.js`
- Checks `localStorage.getItem('demo_mode') === 'true'`
- OR checks if route starts with `/demo-app` or `/demo-docs`

### Demo Provisioning Simulation
- Realistic boot times: 15-30 seconds
- Speed modifiers based on:
  - Internet speed (`inet_down`)
  - Verification status (verified 20% faster)
  - GPU type (4090/A100 10% faster)
- Failure simulation:
  - Verified: 5% failure rate
  - Unverified: 20% failure rate
- Realistic error messages:
  - "Máquina já alugada por outro usuário"
  - "Timeout de conexão SSH"
  - "Erro ao baixar imagem Docker"

## Props Flow

### WizardForm Props (from Dashboard.jsx)
```javascript
<WizardForm
  // Step 1: Location
  searchCountry={searchCountry}
  selectedLocation={selectedLocation}
  onSearchChange={handleSearchChange}
  onRegionSelect={handleRegionSelect}
  onCountryClick={setSelectedLocation}
  onClearSelection={clearSelection}

  // Step 2: Hardware
  selectedGPU={selectedGPU}
  onSelectGPU={setSelectedGPU}
  selectedGPUCategory={selectedGPUCategory}
  onSelectGPUCategory={setSelectedGPUCategory}
  selectedTier={selectedTier}
  onSelectTier={setSelectedTier}

  // Actions
  loading={loading}
  onSubmit={handleWizardSearchWithRaceIntegrated}

  // Step 4: Provisioning
  provisioningCandidates={raceCandidates}
  provisioningWinner={raceWinner}
  isProvisioning={provisioningMode}
  onCancelProvisioning={cancelProvisioningRace}
  onCompleteProvisioning={completeProvisioningRace}
  currentRound={currentRound}
  maxRounds={MAX_ROUNDS}
/>
```

## Potential Issues

### 1. Balance Check
**Issue**: Step 3 requires minimum $0.10 balance
**Location**: `WizardForm.jsx` line 482-495
**Impact**: Button disabled if balance < $0.10
**Fix**: In demo mode, balance should be mocked

### 2. API Calls in Demo Mode
**Issue**: Step 3 tries to fetch balance via `/api/v1/balance`
**Location**: `WizardForm.jsx` line 454-478
**Impact**: May fail if backend not running
**Current Behavior**: Sets balance to 0 on error, which triggers insufficient balance warning

### 3. Machine Loading
**Issue**: Step 2 waits for machines to load
**Location**: `WizardForm.jsx` line 285-388
**Demo Handling**: Good - uses DEMO_OFFERS when `isDemoMode()` is true
**Potential Issue**: `isDemoMode()` must return true

### 4. Provisioning Mode State
**Issue**: `provisioningMode` state not being set to true
**Location**: `Dashboard.jsx` line 1540
**Code**: `// DON'T set provisioningMode to true - wizard handles step 4 display`
**Impact**: May affect UI state, but wizard should handle it internally

## Test Strategy

### Automated Test Checkpoints
1. **Initial Load**: Verify wizard visible at `/demo-app`
2. **Step 1 - Region**:
   - Region buttons visible
   - Click "EUA" button
   - Verify selection registered
   - Próximo enabled
3. **Step 2 - Hardware**:
   - Use case buttons visible
   - Click "Desenvolver"
   - Wait for machines to load (check loading indicator)
   - Verify 3 demo machines displayed
   - Click first machine
   - Próximo enabled
4. **Step 3 - Strategy**:
   - Verify default selection (snapshot_only)
   - Check balance display
   - Verify "Iniciar" button state
5. **Step 4 - Provisioning**:
   - Verify provisioning started
   - Check round indicator
   - Check timer
   - Check candidates visible
   - Wait for winner (max 30s)
   - Verify "Usar Esta Máquina" button

### Manual Testing Checklist
- [ ] Navigate to http://localhost:4895/demo-app
- [ ] Wizard "Nova Instância GPU" visible
- [ ] Step 1: Click "EUA", verify selection, click "Próximo"
- [ ] Step 2: Click "Desenvolver", wait for machines, select first, click "Próximo"
- [ ] Step 3: Verify balance displayed, click "Iniciar"
- [ ] Step 4: Verify provisioning starts, candidates show progress
- [ ] Wait for winner or observe errors
- [ ] Note: Any error messages or disabled buttons

## Current Status

### Known Working
- ✅ Demo mode detection
- ✅ DEMO_OFFERS data structure
- ✅ Demo provisioning simulation
- ✅ Step navigation logic
- ✅ Machine filtering by tier

### Needs Testing
- ⚠️ Balance check in demo mode
- ⚠️ Step 3 to Step 4 transition
- ⚠️ Provisioning initialization
- ⚠️ Race candidate display

### Likely Root Cause
**Balance validation preventing Step 3 → Step 4 transition**
- Demo mode may not properly mock balance
- Balance fetch fails → sets balance to 0
- Balance < $0.10 → button disabled
- Error message: "Saldo insuficiente"

## Recommended Fixes

### Fix 1: Mock Balance in Demo Mode
```javascript
// In WizardForm.jsx, fetchUserBalance function
const fetchUserBalance = async () => {
  setLoadingBalance(true);
  setBalanceError(null);

  try {
    // Check demo mode first
    if (isDemoMode()) {
      setUserBalance(10.00); // Mock balance for demo
      setLoadingBalance(false);
      return;
    }

    // ... existing code ...
  }
}
```

### Fix 2: Skip Balance Check in Demo Mode
```javascript
// In handleStartProvisioning
if (userBalance !== null && userBalance < MIN_BALANCE && !isDemoMode()) {
  errors.push(`Saldo insuficiente...`);
}
```

### Fix 3: Auto-navigate for Demo
```javascript
// In Dashboard.jsx demo provisioning completion
if (winnerState) {
  const winner = { ...winnerState.candidate, status: 'ready', progress: 100, instanceId: winnerState.instanceId };
  setRaceWinner(winner);
  toast.success(`🏆 ${winner.gpu_name} pronta em ${bootTimeSeconds}s!`);

  // Auto-navigate in demo mode
  if (isDemoMode()) {
    setTimeout(() => {
      navigate(`${basePath}/machines`);
    }, 2500);
  }
}
```
