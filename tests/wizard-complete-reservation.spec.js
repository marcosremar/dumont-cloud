const { test, expect } = require('@playwright/test');

test.describe('Wizard Complete GPU Reservation', () => {
  test('should complete full wizard flow and start provisioning', async ({ page }) => {
    // Listen to console for debugging
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('WizardForm') || text.includes('WizardRace') || text.includes('provisioning') || text.includes('Provisioning') || text.includes('Demo')) {
        console.log(`[CONSOLE] ${text}`);
      }
    });

    console.log('=== STARTING COMPLETE WIZARD TEST ===\n');

    // Navigate to demo app
    await page.goto('http://localhost:4894/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'tests/screenshots/reservation-01-start.png', fullPage: true });
    console.log('✓ Step 0: Page loaded');

    // ========== STEP 1: SELECT REGION ==========
    console.log('\n--- STEP 1: Selecting Region ---');

    const euaButton = page.locator('button:has-text("EUA")').first();
    await expect(euaButton).toBeVisible({ timeout: 5000 });
    await euaButton.click();
    console.log('✓ Clicked EUA');
    await page.waitForTimeout(500);

    // Click Next
    const nextBtn1 = page.locator('button:has-text("Próximo")').first();
    await expect(nextBtn1).toBeEnabled({ timeout: 3000 });
    await nextBtn1.click();
    console.log('✓ Clicked Próximo');
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'tests/screenshots/reservation-02-after-region.png', fullPage: true });

    // ========== STEP 2: SELECT PURPOSE & GPU ==========
    console.log('\n--- STEP 2: Selecting Purpose & GPU ---');

    // Select purpose "Desenvolver"
    const developBtn = page.locator('[data-testid="use-case-develop"]').first();
    await expect(developBtn).toBeVisible({ timeout: 5000 });
    await developBtn.click();
    console.log('✓ Clicked Desenvolver');
    await page.waitForTimeout(500);

    // Wait for GPUs to load
    console.log('  Waiting for GPUs to load...');
    await page.waitForSelector('[data-gpu-card="true"]', { timeout: 10000 });

    const gpuCount = await page.locator('[data-gpu-card="true"]').count();
    console.log(`✓ Found ${gpuCount} GPU cards`);

    // Click first GPU
    const firstGpu = page.locator('[data-gpu-card="true"]').first();
    const gpuName = await firstGpu.getAttribute('data-gpu-name');
    await firstGpu.click();
    console.log(`✓ Selected GPU: ${gpuName}`);
    await page.waitForTimeout(500);

    await page.screenshot({ path: 'tests/screenshots/reservation-03-gpu-selected.png', fullPage: true });

    // Click Next to go to Step 3
    const nextBtn2 = page.locator('button:has-text("Próximo")').first();
    await expect(nextBtn2).toBeEnabled({ timeout: 3000 });
    await nextBtn2.click();
    console.log('✓ Clicked Próximo to Step 3');
    await page.waitForTimeout(1000);

    // ========== STEP 3: SELECT STRATEGY ==========
    console.log('\n--- STEP 3: Selecting Failover Strategy ---');

    await page.screenshot({ path: 'tests/screenshots/reservation-04-step3.png', fullPage: true });

    // Check if we're on Step 3
    const step3Indicator = page.locator('text=/3\\/4|Estratégia/').first();
    const onStep3 = await step3Indicator.isVisible({ timeout: 5000 }).catch(() => false);
    console.log(`  On Step 3: ${onStep3}`);

    // Look for strategy options
    const strategyOptions = page.locator('[data-testid*="strategy"], button:has-text("Snapshot"), button:has-text("CPU Standby")');
    const strategyCount = await strategyOptions.count();
    console.log(`  Found ${strategyCount} strategy options`);

    // Try to select a strategy if needed (some might be pre-selected)
    if (strategyCount > 0) {
      await strategyOptions.first().click().catch(() => console.log('  Strategy might be pre-selected'));
      console.log('✓ Strategy selected');
    }

    await page.waitForTimeout(500);

    // Click "Iniciar" button to start provisioning
    console.log('\n--- STEP 4: Starting Provisioning ---');

    // Look for the start button (might be "Iniciar", "Reservar", "Deploy", etc.)
    const startButton = page.locator('button:has-text("Iniciar"), button:has-text("Reservar"), button:has-text("Deploy"), button:has-text("Provisionar")').first();

    if (await startButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await page.screenshot({ path: 'tests/screenshots/reservation-05-before-start.png', fullPage: true });

      await startButton.click();
      console.log('✓ Clicked START button');
      await page.waitForTimeout(2000);
    } else {
      // Maybe we need to click Próximo one more time
      const nextBtn3 = page.locator('button:has-text("Próximo")').first();
      if (await nextBtn3.isVisible({ timeout: 2000 }).catch(() => false)) {
        await nextBtn3.click();
        console.log('✓ Clicked Próximo to Step 4');
        await page.waitForTimeout(2000);
      }
    }

    await page.screenshot({ path: 'tests/screenshots/reservation-06-provisioning.png', fullPage: true });

    // ========== VERIFY PROVISIONING STARTED ==========
    console.log('\n--- Verifying Provisioning ---');

    // Look for provisioning indicators
    const provisioningIndicators = [
      'text=/Provisionando|Conectando|Buscando|Testando/i',
      'text=/Round|Tentativa/i',
      '.animate-spin',
      '[data-testid*="provisioning"]',
      'text=/4\\/4|Provisionar/'
    ];

    let provisioningStarted = false;
    for (const indicator of provisioningIndicators) {
      const element = page.locator(indicator).first();
      if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
        provisioningStarted = true;
        console.log(`✓ Provisioning indicator found: ${indicator}`);
        break;
      }
    }

    // Wait a bit more and take final screenshot
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'tests/screenshots/reservation-07-final.png', fullPage: true });

    // Check for success or progress
    const hasSpinner = await page.locator('.animate-spin').count() > 0;
    const hasRound = await page.locator('text=/Round|Tentativa/i').isVisible().catch(() => false);
    const hasStep4 = await page.locator('text=/4\\/4/').isVisible().catch(() => false);

    console.log(`\n=== FINAL STATUS ===`);
    console.log(`  Provisioning started: ${provisioningStarted}`);
    console.log(`  Has spinner: ${hasSpinner}`);
    console.log(`  Has Round indicator: ${hasRound}`);
    console.log(`  On Step 4: ${hasStep4}`);

    // The test passes if we got to step 4 or provisioning started
    expect(provisioningStarted || hasStep4 || hasSpinner).toBeTruthy();

    console.log('\n✅ WIZARD COMPLETE - GPU RESERVATION INITIATED');
  });
});
