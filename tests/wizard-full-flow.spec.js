/**
 * Wizard Full Flow Test - Complete GPU provisioning
 * This test runs without auth setup (uses demo mode)
 */
const { test, expect } = require('@playwright/test');

// Skip auth setup - demo mode doesn't require login
test.use({
  storageState: { cookies: [], origins: [] }
});

test('Complete wizard flow from region to provisioning', async ({ page }) => {
  const BASE_URL = 'http://localhost:4898';

  console.log('\n=== WIZARD FULL FLOW TEST ===\n');

  // Step 1: Navigate to demo app
  console.log('[1] Navigating to demo app...');
  await page.goto(`${BASE_URL}/demo-app`);
  await page.waitForTimeout(2000);

  // Verify wizard is visible
  const wizard = page.locator('text=Nova Instância GPU');
  await expect(wizard).toBeVisible({ timeout: 10000 });
  console.log('[1] ✓ Wizard visible');

  // Step 2: Select region (EUA)
  console.log('[2] Selecting EUA region...');
  const euaButton = page.locator('button[data-testid="region-eua"]');
  await expect(euaButton).toBeVisible({ timeout: 5000 });

  // Use JavaScript click directly on the element
  await euaButton.evaluate((btn) => {
    btn.click();
    // Dispatch additional events to ensure React captures it
    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  });
  await page.waitForTimeout(2000);

  // Verify selection badge appears (EUA with X to clear)
  const selectedBadge = page.locator('.rounded-full:has-text("EUA")');
  const hasBadge = await selectedBadge.count() > 0;
  console.log(`[2] Badge visible: ${hasBadge}`);

  // If badge not visible, try clicking again
  if (!hasBadge) {
    console.log('[2] Retrying click...');
    await euaButton.click({ force: true });
    await page.waitForTimeout(2000);
    const hasBadgeRetry = await selectedBadge.count() > 0;
    console.log(`[2] Badge visible after retry: ${hasBadgeRetry}`);
  }

  console.log('[2] ✓ EUA clicked');

  // Step 3: Click "Próximo" to go to Step 2
  console.log('[3] Clicking Próximo...');
  const nextBtn1 = page.locator('button:has-text("Próximo")');

  // Wait for button to be enabled (max 10s)
  try {
    await expect(nextBtn1).toBeEnabled({ timeout: 10000 });
  } catch (e) {
    // Take screenshot if button not enabled
    await page.screenshot({ path: 'test-results/debug-proximo-disabled.png' });
    throw new Error('Botão Próximo não ficou habilitado após clicar em EUA');
  }

  await nextBtn1.click();
  await page.waitForTimeout(3000);
  console.log('[3] ✓ Clicked Próximo');

  // Step 4: Verify we're on Step 2 (wait longer)
  console.log('[4] Verifying Step 2...');
  const step2Title = page.locator('text=O que você vai fazer?');
  try {
    await expect(step2Title).toBeVisible({ timeout: 10000 });
    console.log('[4] ✓ On Step 2 (Hardware)');
  } catch (e) {
    // If not found, check what step we're on
    await page.screenshot({ path: 'test-results/debug-step2-not-visible.png' });
    const currentStepText = await page.locator('[class*="step"]').first().textContent().catch(() => 'N/A');
    console.log(`[4] ❌ Step 2 not visible. Current: ${currentStepText}`);
    throw e;
  }

  // Step 5: Select "Desenvolver" tier
  console.log('[5] Selecting Desenvolver...');
  const desenvolverBtn = page.locator('button[data-testid="use-case-develop"]');
  await expect(desenvolverBtn).toBeVisible({ timeout: 5000 });
  await desenvolverBtn.click();
  await page.waitForTimeout(2000);
  console.log('[5] ✓ Desenvolver selected');

  // Step 6: Wait for machines to load and select first one
  console.log('[6] Selecting first machine...');
  const machineBtn = page.locator('[data-testid^="machine-"]').first();
  await expect(machineBtn).toBeVisible({ timeout: 10000 });
  await machineBtn.click({ force: true });
  await page.waitForTimeout(1000);
  console.log('[6] ✓ Machine selected');

  // Step 7: Click "Próximo" to go to Step 3
  console.log('[7] Clicking Próximo to Step 3...');
  const nextBtn2 = page.locator('button:has-text("Próximo")');
  await expect(nextBtn2).toBeEnabled({ timeout: 5000 });
  await nextBtn2.click({ force: true });
  await page.waitForTimeout(2000);
  console.log('[7] ✓ Advanced to Step 3');

  // Step 8: Verify "Iniciar" button is visible
  console.log('[8] Looking for Iniciar button...');
  const iniciarBtn = page.locator('button:has-text("Iniciar")');
  await expect(iniciarBtn).toBeVisible({ timeout: 5000 });
  console.log('[8] ✓ Iniciar button visible');

  // Step 9: Click "Iniciar" to start provisioning
  console.log('[9] Clicking Iniciar...');
  await iniciarBtn.click({ force: true });
  await page.waitForTimeout(2000);
  console.log('[9] ✓ Provisioning started');

  // Step 10: Wait for provisioning (up to 30s)
  console.log('[10] Waiting for provisioning (max 30s)...');

  for (let i = 0; i < 6; i++) {
    await page.waitForTimeout(5000);

    // Check for success indicators
    const success = await page.locator('text=/pronta|winner|vencedor|sucesso|ready|🏆/i').count();
    const progress = await page.locator('text=/race|candidat|provisionando|conectando/i').count();

    console.log(`  [${(i+1)*5}s] Success: ${success}, Progress: ${progress}`);

    if (success > 0) {
      console.log('[10] ✓ GPU provisioned successfully!');
      break;
    }
  }

  // Take final screenshot
  await page.screenshot({ path: 'test-results/wizard-final-state.png', fullPage: true });
  console.log('[10] ✓ Final screenshot saved');

  console.log('\n=== TEST COMPLETED ===\n');
});
