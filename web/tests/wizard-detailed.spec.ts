import { test } from '@playwright/test';

test('detailed wizard inspection', async ({ page }) => {
  console.log('Navigating...');
  await page.goto('http://localhost:4893/login?auto_login=demo');
  await page.waitForTimeout(3000);

  // Look for all buttons
  const allButtons = await page.locator('button').all();
  console.log(`\nFound ${allButtons.length} buttons total`);

  for (let i = 0; i < allButtons.length; i++) {
    const text = await allButtons[i].textContent();
    const visible = await allButtons[i].isVisible();
    const testId = await allButtons[i].getAttribute('data-testid');
    console.log(`  Button ${i}: "${text?.trim()}" visible=${visible} testId=${testId}`);
  }

  // Find the wizard modal specifically
  const modal = page.locator('[role="dialog"]');
  if (await modal.isVisible()) {
    console.log('\nModal is visible');
    const modalText = await modal.textContent();
    console.log('Modal text:', modalText?.substring(0, 300));

    // Look for buttons inside modal
    const modalButtons = await modal.locator('button').all();
    console.log(`\nFound ${modalButtons.length} buttons in modal:`);
    for (let i = 0; i < modalButtons.length; i++) {
      const text = await modalButtons[i].textContent();
      const testId = await modalButtons[i].getAttribute('data-testid');
      console.log(`  Modal button ${i}: "${text?.trim()}" testId=${testId}`);
    }
  }

  // Take screenshot
  await page.screenshot({ path: '/tmp/wizard-detailed.png', fullPage: true });

  // Look specifically for Guiado/Avançado buttons by test ID
  const guiadoByTestId = page.locator('[data-testid="config-guided"]');
  const avancadoByTestId = page.locator('[data-testid="config-advanced"]');

  console.log('\nSearching by test IDs:');
  console.log('  config-guided visible:', await guiadoByTestId.isVisible().catch(() => false));
  console.log('  config-advanced visible:', await avancadoByTestId.isVisible().catch(() => false));

  // Check if they're in a hidden parent
  const guiadoParent = page.locator('[data-testid="config-guided"]').locator('..');
  if (await guiadoParent.count() > 0) {
    const parentVisible = await guiadoParent.first().isVisible().catch(() => false);
    const parentClass = await guiadoParent.first().getAttribute('class');
    console.log('  Guiado parent visible:', parentVisible);
    console.log('  Guiado parent class:', parentClass);
  }
});
