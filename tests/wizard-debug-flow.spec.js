/**
 * Wizard Debug Flow Test
 * Comprehensive test to debug GPU provisioning wizard
 * Captures screenshots and detailed state at each step
 */
const { test, expect } = require('@playwright/test');

test('Debug wizard provisioning flow', async ({ page }) => {
  // Enable detailed logging
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    if (type === 'error' || text.includes('Error') || text.includes('fail')) {
      console.log(`[BROWSER ${type.toUpperCase()}]:`, text);
    }
  });

  page.on('pageerror', err => console.log('[PAGE ERROR]:', err.message));

  page.on('requestfailed', request => {
    console.log('[REQUEST FAILED]:', request.url(), request.failure()?.errorText);
  });

  const baseUrl = process.env.BASE_URL || 'http://localhost:4895';

  console.log('\n========================================');
  console.log('WIZARD DEBUG FLOW TEST');
  console.log('========================================\n');

  // STEP 0: Navigate to demo-app
  console.log('STEP 0: Navigating to demo-app...');
  await page.goto(`${baseUrl}/demo-app`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  await page.screenshot({ path: 'test-results/wizard-debug-initial.png', fullPage: true });

  // Check if wizard is visible
  const wizardTitle = page.locator('text=Nova Instância GPU').first();
  const hasWizard = await wizardTitle.isVisible().catch(() => false);
  console.log(`✓ Wizard visible: ${hasWizard}`);

  if (!hasWizard) {
    console.error('✗ ERROR: Wizard not found!');
    const bodyText = await page.locator('body').textContent();
    console.log('Page content:', bodyText.substring(0, 500));
    throw new Error('Wizard not found on page');
  }

  // ========================================
  // STEP 1: REGION SELECTION
  // ========================================
  console.log('\n----------------------------------------');
  console.log('STEP 1: Region Selection');
  console.log('----------------------------------------');

  await page.screenshot({ path: 'test-results/wizard-debug-step1-start.png', fullPage: true });

  // Check for region buttons
  const regionButtons = page.locator('button[data-testid^="region-"]');
  const regionCount = await regionButtons.count();
  console.log(`Found ${regionCount} region buttons`);

  // Try to find and click EUA button
  const euaButton = page.locator('button[data-testid="region-eua"], button:has-text("EUA")').first();
  const euaVisible = await euaButton.isVisible({ timeout: 5000 }).catch(() => false);
  console.log(`EUA button visible: ${euaVisible}`);

  if (euaVisible) {
    await euaButton.click();
    console.log('✓ Clicked EUA button');
    await page.waitForTimeout(500);

    // Check if selection was registered
    const selectedRegion = page.locator('text=Estados Unidos, text=EUA').first();
    const hasSelection = await selectedRegion.isVisible({ timeout: 2000 }).catch(() => false);
    console.log(`Region selected: ${hasSelection}`);
  } else {
    console.error('✗ EUA button not found!');
  }

  await page.screenshot({ path: 'test-results/wizard-debug-step1-after-click.png', fullPage: true });

  // Check Próximo button
  const nextButton1 = page.locator('button:has-text("Próximo")').first();
  const nextEnabled1 = await nextButton1.isEnabled().catch(() => false);
  console.log(`Próximo button enabled: ${nextEnabled1}`);

  if (nextEnabled1) {
    await nextButton1.click();
    console.log('✓ Clicked Próximo to Step 2');
    await page.waitForTimeout(1000);
  } else {
    console.error('✗ ERROR: Próximo button disabled!');
    throw new Error('Cannot proceed to Step 2 - Próximo disabled');
  }

  // ========================================
  // STEP 2: HARDWARE SELECTION
  // ========================================
  console.log('\n----------------------------------------');
  console.log('STEP 2: Hardware Selection');
  console.log('----------------------------------------');

  await page.screenshot({ path: 'test-results/wizard-debug-step2-start.png', fullPage: true });

  // Check for use case buttons
  const useCaseButtons = page.locator('button[data-testid^="use-case-"]');
  const useCaseCount = await useCaseButtons.count();
  console.log(`Found ${useCaseCount} use case buttons`);

  // Click "Desenvolver" use case
  const developButton = page.locator('button[data-testid="use-case-develop"]').first();
  const developVisible = await developButton.isVisible({ timeout: 5000 }).catch(() => false);
  console.log(`Desenvolver button visible: ${developVisible}`);

  if (developVisible) {
    await developButton.click();
    console.log('✓ Clicked Desenvolver use case');
    await page.waitForTimeout(2000);
  } else {
    console.error('✗ Desenvolver button not found!');
    throw new Error('Desenvolver button not found');
  }

  await page.screenshot({ path: 'test-results/wizard-debug-step2-after-usecase.png', fullPage: true });

  // Wait for machines to load
  console.log('Waiting for machines to load...');

  // Check for loading indicator
  const loadingIndicator = page.locator('text=Buscando máquinas, text=Carregando').first();
  const isLoading = await loadingIndicator.isVisible({ timeout: 2000 }).catch(() => false);
  console.log(`Loading indicator visible: ${isLoading}`);

  if (isLoading) {
    console.log('Waiting for loading to complete...');
    await page.waitForTimeout(5000);
  }

  await page.screenshot({ path: 'test-results/wizard-debug-step2-after-loading.png', fullPage: true });

  // Check if machines are displayed
  const noMachines = await page.locator('text=Nenhuma máquina encontrada').isVisible().catch(() => false);
  if (noMachines) {
    console.error('✗ ERROR: No machines found!');

    // Check for error message
    const errorMsg = page.locator('text=/erro|error/i');
    const hasError = await errorMsg.count() > 0;
    if (hasError) {
      const errorTexts = await errorMsg.allTextContents();
      console.log('Error messages:', errorTexts);
    }

    throw new Error('No machines found');
  }

  // Look for machine cards
  const machineCards = page.locator('[data-testid^="machine-"]');
  const machineCount = await machineCards.count();
  console.log(`Found ${machineCount} machine cards`);

  if (machineCount > 0) {
    // Get info about first machine
    const firstMachine = machineCards.first();
    const machineText = await firstMachine.textContent();
    console.log(`First machine: ${machineText.substring(0, 100)}`);

    await firstMachine.click();
    console.log('✓ Clicked first machine');
    await page.waitForTimeout(500);
  } else {
    console.error('✗ ERROR: No machine cards found!');
    throw new Error('No machine cards found');
  }

  await page.screenshot({ path: 'test-results/wizard-debug-step2-after-machine-select.png', fullPage: true });

  // Check Próximo button
  const nextButton2 = page.locator('button:has-text("Próximo")').first();
  const nextEnabled2 = await nextButton2.isEnabled().catch(() => false);
  console.log(`Step 2 Próximo enabled: ${nextEnabled2}`);

  if (nextEnabled2) {
    await nextButton2.click();
    console.log('✓ Clicked Próximo to Step 3');
    await page.waitForTimeout(1000);
  } else {
    console.error('✗ ERROR: Próximo button disabled after machine selection!');
    throw new Error('Cannot proceed to Step 3 - Próximo disabled');
  }

  // ========================================
  // STEP 3: STRATEGY/FAILOVER
  // ========================================
  console.log('\n----------------------------------------');
  console.log('STEP 3: Strategy/Failover');
  console.log('----------------------------------------');

  await page.screenshot({ path: 'test-results/wizard-debug-step3-start.png', fullPage: true });

  // Check for failover options
  const failoverOptions = page.locator('[data-testid^="failover-option-"]');
  const failoverCount = await failoverOptions.count();
  console.log(`Found ${failoverCount} failover options`);

  // Check default selection
  const snapshotOnly = page.locator('[data-testid="failover-option-snapshot_only"]');
  const isSnapshotSelected = await snapshotOnly.evaluate(el => {
    return el.classList.contains('border-brand-500') ||
           el.querySelector('[class*="bg-brand"]') !== null;
  }).catch(() => false);
  console.log(`Snapshot Only selected (default): ${isSnapshotSelected}`);

  // Check balance
  const balanceDisplay = page.locator('text=/saldo|balance/i').first();
  const hasBalance = await balanceDisplay.isVisible({ timeout: 2000 }).catch(() => false);
  console.log(`Balance display visible: ${hasBalance}`);

  if (hasBalance) {
    const balanceText = await balanceDisplay.textContent();
    console.log(`Balance text: ${balanceText}`);
  }

  // Check for insufficient balance warning
  const insufficientBalance = page.locator('text=/insuficiente|insufficient/i');
  const hasInsufficientWarning = await insufficientBalance.isVisible().catch(() => false);
  console.log(`Insufficient balance warning: ${hasInsufficientWarning}`);

  await page.screenshot({ path: 'test-results/wizard-debug-step3-full.png', fullPage: true });

  // Check Próximo/Iniciar button
  const nextButton3 = page.locator('button:has-text("Próximo"), button:has-text("Iniciar")').first();
  const nextEnabled3 = await nextButton3.isEnabled().catch(() => false);
  const nextText = await nextButton3.textContent().catch(() => '');
  console.log(`Step 3 button enabled: ${nextEnabled3}, text: "${nextText}"`);

  if (nextEnabled3) {
    await nextButton3.click();
    console.log(`✓ Clicked "${nextText}" button`);
    await page.waitForTimeout(2000);
  } else {
    console.error('✗ ERROR: Step 3 button disabled!');

    // Check for validation errors
    const validationErrors = page.locator('text=/erro|error|corrija|insuficiente/i');
    const errorCount = await validationErrors.count();
    if (errorCount > 0) {
      const errors = await validationErrors.allTextContents();
      console.log('Validation errors:', errors);
    }

    throw new Error('Cannot proceed to Step 4 - button disabled');
  }

  // ========================================
  // STEP 4: PROVISIONING
  // ========================================
  console.log('\n----------------------------------------');
  console.log('STEP 4: Provisioning');
  console.log('----------------------------------------');

  await page.screenshot({ path: 'test-results/wizard-debug-step4-start.png', fullPage: true });

  // Check for provisioning indicators
  const provisioningTitle = page.locator('text=Provisionando, text=Conectando').first();
  const isProvisioning = await provisioningTitle.isVisible({ timeout: 5000 }).catch(() => false);
  console.log(`Provisioning started: ${isProvisioning}`);

  // Check for round indicator
  const roundIndicator = page.locator('[data-testid="wizard-round-indicator"]');
  const hasRoundIndicator = await roundIndicator.isVisible({ timeout: 2000 }).catch(() => false);
  console.log(`Round indicator visible: ${hasRoundIndicator}`);

  if (hasRoundIndicator) {
    const roundText = await roundIndicator.textContent();
    console.log(`Round: ${roundText}`);
  }

  // Check for timer
  const timer = page.locator('[data-testid="wizard-timer"]');
  const hasTimer = await timer.isVisible({ timeout: 2000 }).catch(() => false);
  console.log(`Timer visible: ${hasTimer}`);

  if (hasTimer) {
    const timerText = await timer.textContent();
    console.log(`Timer: ${timerText}`);
  }

  // Check for provisioning candidates
  const candidates = page.locator('[data-testid^="provisioning-candidate-"]');
  const candidateCount = await candidates.count();
  console.log(`Provisioning candidates: ${candidateCount}`);

  if (candidateCount > 0) {
    console.log('Candidate details:');
    for (let i = 0; i < candidateCount; i++) {
      const candidate = candidates.nth(i);
      const text = await candidate.textContent();
      console.log(`  ${i + 1}. ${text.substring(0, 100)}`);
    }
  } else {
    console.error('✗ ERROR: No provisioning candidates found!');
  }

  await page.screenshot({ path: 'test-results/wizard-debug-step4-provisioning.png', fullPage: true });

  // Wait for winner or timeout
  console.log('Waiting for provisioning to complete (max 30s)...');

  const winnerFound = await page.locator('text=Conectado, text=Máquina Conectada').first()
    .isVisible({ timeout: 30000 })
    .catch(() => false);

  console.log(`Winner found: ${winnerFound}`);

  await page.screenshot({ path: 'test-results/wizard-debug-step4-final.png', fullPage: true });

  // Check final state
  if (winnerFound) {
    console.log('✓ SUCCESS: Provisioning completed!');

    // Check for "Usar Esta Máquina" button
    const useMachineButton = page.locator('button:has-text("Usar Esta Máquina")');
    const hasButton = await useMachineButton.isVisible().catch(() => false);
    console.log(`"Usar Esta Máquina" button visible: ${hasButton}`);

  } else {
    console.log('⚠ WARNING: Provisioning did not complete within timeout');

    // Check for errors
    const errorIndicators = page.locator('text=/erro|error|falha|failed/i');
    const hasErrors = await errorIndicators.count() > 0;
    if (hasErrors) {
      const errors = await errorIndicators.allTextContents();
      console.log('Errors found:', errors);
    }
  }

  // ========================================
  // SUMMARY
  // ========================================
  console.log('\n========================================');
  console.log('TEST SUMMARY');
  console.log('========================================');
  console.log('Step 1 (Region): ✓ Passed');
  console.log('Step 2 (Hardware): ✓ Passed');
  console.log('Step 3 (Strategy): ✓ Passed');
  console.log(`Step 4 (Provision): ${winnerFound ? '✓ Passed' : '⚠ Timeout'}`);
  console.log('========================================\n');

  // The test should pass if we got to provisioning step
  expect(isProvisioning).toBeTruthy();
});
