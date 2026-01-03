const { test } = require('@playwright/test');

test('Capture Chat Arena with real models', async ({ page }) => {
  // Go directly to demo chat arena (correct route)
  await page.goto('/demo-app/chat-arena');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // Screenshot 1: Initial state
  await page.screenshot({ path: 'tests/screenshots/chat-arena-capture-1.png', fullPage: true });

  // Find and click model selector
  const selectBtn = page.getByRole('button', { name: /selecionar/i });
  if (await selectBtn.isVisible({ timeout: 3000 })) {
    await selectBtn.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'tests/screenshots/chat-arena-capture-2-selector.png', fullPage: true });

    // Select models
    const localModels = page.locator('text=/Local CPU/');
    const count = await localModels.count();
    console.log(`Found ${count} local models`);

    if (count >= 2) {
      await localModels.nth(0).click();
      await page.waitForTimeout(300);
      await localModels.nth(1).click();
      await page.waitForTimeout(300);
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }

  await page.screenshot({ path: 'tests/screenshots/chat-arena-capture-3-selected.png', fullPage: true });

  // Send a message
  const input = page.locator('input[type="text"]').first();
  if (await input.isVisible({ timeout: 2000 })) {
    await input.fill('Ola! Quem e voce?');
    await input.press('Enter');
    console.log('Message sent, waiting for responses...');

    // Wait for real Ollama responses
    await page.waitForTimeout(15000);

    await page.screenshot({ path: 'tests/screenshots/chat-arena-capture-4-responses.png', fullPage: true });
  }
});
