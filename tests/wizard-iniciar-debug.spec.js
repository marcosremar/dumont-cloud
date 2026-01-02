const { test, expect } = require('@playwright/test');

test.describe('Wizard Iniciar Button Debug', () => {
  test('should click Iniciar button and trigger handleNext', async ({ page }) => {
    // Capture ALL console messages
    page.on('console', msg => {
      console.log(`[BROWSER] ${msg.text()}`);
    });

    // Navigate to demo app
    await page.goto('http://localhost:4894/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Step 1: Select region
    await page.locator('button:has-text("EUA")').first().click();
    await page.waitForTimeout(300);
    await page.locator('button:has-text("Próximo")').first().click();
    await page.waitForTimeout(500);
    console.log('✅ Step 1 done - Region selected');

    // Step 2: Select purpose and GPU
    await page.locator('[data-testid="use-case-develop"]').click();
    await page.waitForTimeout(500);
    await page.waitForSelector('[data-gpu-card="true"]', { timeout: 10000 });
    await page.locator('[data-gpu-card="true"]').first().click();
    await page.waitForTimeout(300);
    await page.locator('button:has-text("Próximo")').first().click();
    await page.waitForTimeout(500);
    console.log('✅ Step 2 done - GPU selected');

    // Step 3: We should be on strategy selection
    await page.screenshot({ path: 'tests/screenshots/iniciar-debug-step3.png', fullPage: true });

    // Check the Iniciar button
    const iniciarBtn = page.locator('button:has-text("Iniciar")').first();

    // Check if visible
    const isVisible = await iniciarBtn.isVisible({ timeout: 5000 });
    console.log(`Iniciar button visible: ${isVisible}`);

    // Check if disabled
    const isDisabled = await iniciarBtn.getAttribute('disabled');
    console.log(`Iniciar button disabled attribute: ${isDisabled}`);

    // Get button text
    const buttonText = await iniciarBtn.textContent();
    console.log(`Iniciar button text: ${buttonText}`);

    // Check if enabled via Playwright
    const isEnabled = await iniciarBtn.isEnabled();
    console.log(`Iniciar button isEnabled: ${isEnabled}`);

    // Wait a moment
    await page.waitForTimeout(500);

    // Try clicking with force
    console.log('Attempting to click Iniciar button...');
    await iniciarBtn.click({ force: true });
    console.log('Clicked Iniciar button');

    // Wait for any state change
    await page.waitForTimeout(3000);

    // Check if we advanced to step 4
    await page.screenshot({ path: 'tests/screenshots/iniciar-debug-after-click.png', fullPage: true });

    const step4Text = await page.locator('text=/4\\/4|Provisionando/').first().isVisible().catch(() => false);
    console.log(`On Step 4 / Provisionando: ${step4Text}`);

    // Check candidates count
    const candidatesText = await page.locator('text=/Testando.*máquinas/').first().textContent().catch(() => 'not found');
    console.log(`Candidates text: ${candidatesText}`);

    expect(step4Text).toBeTruthy();
  });
});
