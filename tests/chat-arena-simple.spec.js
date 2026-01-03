const { test, expect } = require('@playwright/test');

test.describe('Chat Arena Simple Test', () => {
  test('Load Chat Arena and select local models', async ({ page }) => {
    // Navigate directly to demo chat arena
    await page.goto('/demo-app/chat-arena');
    await page.waitForLoadState('networkidle');

    // Verify we're on Chat Arena page (use heading to avoid sidebar match)
    await expect(page.getByRole('heading', { name: 'Chat Arena' })).toBeVisible({ timeout: 5000 });
    console.log('1. Chat Arena page loaded');

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/simple-1-chatarena.png' });

    // Click model selector button (use first one in header)
    const selectorBtn = page.getByRole('button', { name: /selecionar modelos/i }).first();
    await expect(selectorBtn).toBeVisible({ timeout: 5000 });
    await selectorBtn.click();
    await page.waitForTimeout(1000);
    console.log('2. Clicked model selector');

    await page.screenshot({ path: 'tests/screenshots/simple-2-dropdown.png' });

    // Look for local models in dropdown
    const pageContent = await page.content();
    const hasQwen = pageContent.includes('Qwen') || pageContent.includes('qwen');
    const hasLlama = pageContent.includes('Llama') || pageContent.includes('llama');
    const hasLocalCPU = pageContent.includes('Local CPU');

    console.log(`3. Found Qwen: ${hasQwen}, Llama: ${hasLlama}, Local CPU: ${hasLocalCPU}`);

    // Select models if visible
    const modelCheckboxes = page.locator('[type="checkbox"], [role="checkbox"]');
    const checkboxCount = await modelCheckboxes.count();
    console.log(`   Found ${checkboxCount} checkboxes`);

    if (checkboxCount >= 2) {
      await modelCheckboxes.nth(0).click();
      await modelCheckboxes.nth(1).click();
      console.log('4. Selected 2 models');
    }

    // Close dropdown
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    await page.screenshot({ path: 'tests/screenshots/simple-3-selected.png' });

    // Look for input field
    const input = page.locator('input[type="text"], textarea').first();
    const inputVisible = await input.isVisible({ timeout: 3000 }).catch(() => false);
    console.log(`5. Input visible: ${inputVisible}`);

    if (inputVisible) {
      await input.fill('Teste rapido');
      await input.press('Enter');
      console.log('6. Sent message');

      // Wait for response
      await page.waitForTimeout(10000);
      await page.screenshot({ path: 'tests/screenshots/simple-4-response.png', fullPage: true });
    }

    console.log('Test complete');
  });
});
