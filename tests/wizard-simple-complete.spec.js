const { test, expect } = require('@playwright/test');

test.describe('GPU Wizard - Step by Step Test', () => {
  test('should complete wizard flow from Step 1 to Step 3', async ({ page }) => {
    console.log('=== Starting Wizard Step-by-Step Test ===');

    // Step 1: Navigate to demo-app
    console.log('Step 1: Navigating to demo-app...');
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('networkidle');

    // Take snapshot of initial state
    await page.screenshot({ path: 'wizard-step1-initial.png', fullPage: true });
    console.log('✓ Screenshot saved: wizard-step1-initial.png');

    // Step 2: Click "EUA" (USA region)
    console.log('Step 2: Clicking on EUA region...');
    const usaButton = page.locator('text=/EUA|USA/i').first();
    await expect(usaButton).toBeVisible({ timeout: 5000 });
    await usaButton.click();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'wizard-step1-usa-selected.png', fullPage: true });
    console.log('✓ Screenshot saved: wizard-step1-usa-selected.png');

    // Step 3: Click "Próximo" to go to Step 2
    console.log('Step 3: Clicking Próximo to go to Step 2...');
    const nextButton = page.locator('button:has-text("Próximo")').first();
    await expect(nextButton).toBeVisible();
    await nextButton.click();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'wizard-step2-initial.png', fullPage: true });
    console.log('✓ Screenshot saved: wizard-step2-initial.png');

    // Step 4: Click "Desenvolver" (Development use case)
    console.log('Step 4: Clicking on Desenvolver...');
    const devButton = page.locator('text=/Desenvolver|Development/i').first();
    await expect(devButton).toBeVisible({ timeout: 5000 });
    await devButton.click();

    await page.screenshot({ path: 'wizard-step2-dev-selected.png', fullPage: true });
    console.log('✓ Screenshot saved: wizard-step2-dev-selected.png');

    // Step 5: Wait 2 seconds for machines to load
    console.log('Step 5: Waiting 2s for machines to load...');
    await page.waitForTimeout(2000);

    // Step 6: Take snapshot and verify machines appear
    await page.screenshot({ path: 'wizard-step2-machines-loaded.png', fullPage: true });
    console.log('✓ Screenshot saved: wizard-step2-machines-loaded.png');

    // Check if machines are visible
    const machineCards = page.locator('[class*="machine"], [class*="card"], [class*="offer"]');
    const machineCount = await machineCards.count();
    console.log(`Found ${machineCount} machine elements`);

    if (machineCount === 0) {
      // Try alternative selectors
      const buttons = await page.locator('button').count();
      const gpuText = await page.locator('text=/RTX|GPU|NVIDIA/i').count();
      console.log(`Found ${buttons} buttons and ${gpuText} GPU-related text elements`);
    }

    // Step 7: Click on first machine
    console.log('Step 6: Clicking on first machine...');

    // Try multiple strategies to find and click the first machine
    let machineClicked = false;

    // Strategy 1: Look for clickable cards
    const clickableCards = page.locator('[role="button"], button, [class*="cursor-pointer"]');
    if (await clickableCards.count() > 0) {
      await clickableCards.first().click();
      machineClicked = true;
      console.log('✓ Clicked first clickable card');
    }

    if (!machineClicked) {
      // Strategy 2: Look for GPU names
      const gpuElement = page.locator('text=/RTX|A100|H100|V100/i').first();
      if (await gpuElement.isVisible({ timeout: 2000 }).catch(() => false)) {
        await gpuElement.click();
        machineClicked = true;
        console.log('✓ Clicked GPU element');
      }
    }

    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'wizard-step2-machine-selected.png', fullPage: true });
    console.log('✓ Screenshot saved: wizard-step2-machine-selected.png');

    // Step 8: Click "Próximo" to go to Step 3
    console.log('Step 7: Clicking Próximo to go to Step 3...');
    const nextButton2 = page.locator('button:has-text("Próximo")').first();
    await expect(nextButton2).toBeVisible();
    await nextButton2.click();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'wizard-step3-initial.png', fullPage: true });
    console.log('✓ Screenshot saved: wizard-step3-initial.png');

    // Step 9: Verify "Iniciar" button is enabled
    console.log('Step 8: Verifying Iniciar button is enabled...');
    const startButton = page.locator('button:has-text(/Iniciar|Start/i)').first();
    await expect(startButton).toBeVisible({ timeout: 5000 });

    const isEnabled = await startButton.isEnabled();
    console.log(`Iniciar button enabled: ${isEnabled}`);

    if (!isEnabled) {
      console.log('⚠ Iniciar button is DISABLED');
      const buttonClasses = await startButton.getAttribute('class');
      console.log(`Button classes: ${buttonClasses}`);
    }

    // Step 10: Click "Iniciar"
    console.log('Step 9: Clicking Iniciar...');
    await startButton.click();
    await page.screenshot({ path: 'wizard-step3-provisioning-start.png', fullPage: true });
    console.log('✓ Screenshot saved: wizard-step3-provisioning-start.png');

    // Step 11: Wait 20s for provisioning
    console.log('Step 10: Waiting 20s for provisioning...');
    for (let i = 1; i <= 20; i++) {
      await page.waitForTimeout(1000);
      if (i % 5 === 0) {
        console.log(`  ... ${i}s elapsed`);
      }
    }

    // Step 12: Take final snapshot
    await page.screenshot({ path: 'wizard-step3-provisioning-final.png', fullPage: true });
    console.log('✓ Screenshot saved: wizard-step3-provisioning-final.png');

    // Check for success/failure indicators
    const successText = await page.locator('text=/success|criado|created|online/i').count();
    const errorText = await page.locator('text=/error|erro|failed|falhou/i').count();

    console.log('\n=== Final Status ===');
    console.log(`Success indicators: ${successText}`);
    console.log(`Error indicators: ${errorText}`);

    // Get page text content for analysis
    const bodyText = await page.locator('body').textContent();
    console.log('\nPage content keywords:');
    if (bodyText.toLowerCase().includes('provisioning')) console.log('  - Provisioning in progress');
    if (bodyText.toLowerCase().includes('online')) console.log('  - Machine online');
    if (bodyText.toLowerCase().includes('error')) console.log('  - Error detected');
    if (bodyText.toLowerCase().includes('success')) console.log('  - Success detected');

    console.log('\n=== Test Complete ===');
    console.log('Check screenshots in tests/ directory for visual verification');
  });
});
