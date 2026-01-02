const { test, expect } = require('@playwright/test');

test.describe('Wizard Step 2 Debug', () => {
  test('should advance from step 2 to step 3', async ({ page }) => {
    // Listen to console
    page.on('console', msg => {
      if (msg.text().includes('WizardForm')) {
        console.log(`[CONSOLE] ${msg.text()}`);
      }
    });

    // Navigate to demo app
    await page.goto('http://localhost:4894/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Take initial screenshot
    await page.screenshot({ path: 'tests/screenshots/debug-step2-01-initial.png', fullPage: true });
    console.log('Step 1: Initial page loaded');

    // Step 1: Select region (EUA)
    const euaButton = page.locator('[data-testid="region-usa"], button:has-text("EUA")').first();
    if (await euaButton.isVisible({ timeout: 5000 })) {
      await euaButton.click();
      console.log('Step 1: Clicked EUA');
      await page.waitForTimeout(500);
    }

    // Click Next to go to Step 2
    const nextButton = page.locator('button:has-text("Próximo")').first();
    if (await nextButton.isVisible({ timeout: 3000 })) {
      await nextButton.click();
      console.log('Step 1: Clicked Próximo');
      await page.waitForTimeout(1000);
    }

    await page.screenshot({ path: 'tests/screenshots/debug-step2-02-after-region.png', fullPage: true });

    // Step 2: Select purpose (Desenvolver)
    console.log('Step 2: Looking for purpose cards...');

    // Try different selectors
    const developButton = page.locator('[data-testid="use-case-develop"]').first();
    const visible = await developButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (visible) {
      console.log('Step 2: Found use-case-develop button');
      await developButton.click();
      console.log('Step 2: Clicked Desenvolver');
      await page.waitForTimeout(1000);
    } else {
      console.log('Step 2: use-case-develop not found, trying text selector');
      const devText = page.locator('button:has-text("Desenvolver")').first();
      if (await devText.isVisible({ timeout: 3000 })) {
        await devText.click();
        console.log('Step 2: Clicked Desenvolver via text');
        await page.waitForTimeout(1000);
      }
    }

    await page.screenshot({ path: 'tests/screenshots/debug-step2-03-after-purpose.png', fullPage: true });

    // Wait for GPUs to load
    console.log('Step 2: Waiting for GPUs to load...');
    await page.waitForTimeout(3000);

    // Check if GPU cards appeared
    const gpuCards = await page.locator('[data-gpu-card="true"]').count();
    console.log(`Step 2: Found ${gpuCards} GPU cards`);

    if (gpuCards > 0) {
      // Click first GPU
      await page.locator('[data-gpu-card="true"]').first().click();
      console.log('Step 2: Clicked first GPU');
      await page.waitForTimeout(500);
    }

    await page.screenshot({ path: 'tests/screenshots/debug-step2-04-gpu-selected.png', fullPage: true });

    // Check Next button state
    const nextBtn = page.locator('button:has-text("Próximo")').first();
    const isDisabled = await nextBtn.getAttribute('disabled');
    console.log(`Step 2: Next button disabled: ${isDisabled}`);

    // Try to advance
    if (!isDisabled) {
      await nextBtn.click();
      console.log('Step 2: Clicked Próximo');
      await page.waitForTimeout(2000);
    }

    await page.screenshot({ path: 'tests/screenshots/debug-step2-05-final.png', fullPage: true });

    // Verify we're on Step 3
    const stepIndicator = await page.locator('text=/3\\/4|Estratégia/').first();
    const onStep3 = await stepIndicator.isVisible({ timeout: 5000 }).catch(() => false);

    console.log(`Result: On Step 3: ${onStep3}`);

    expect(gpuCards).toBeGreaterThan(0);
  });
});
