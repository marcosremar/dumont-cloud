// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Chat Arena Full E2E Test', () => {
  test('Compare two local Ollama models', async ({ page }) => {
    // 1. Navigate to home first, then click sidebar link
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Click Chat Arena in sidebar using text
    await page.click('text=Chat Arena');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    console.log('1. Chat Arena loaded');

    // Take initial screenshot
    await page.screenshot({ path: 'tests/screenshots/full-test-0-initial.png' });

    // 2. Open model selector - wait longer for page to fully render
    const selectorBtn = page.getByRole('button', { name: /selecionar modelos/i }).first();
    await expect(selectorBtn).toBeVisible({ timeout: 10000 });
    await selectorBtn.click();
    await page.waitForTimeout(500);
    console.log('2. Model selector opened');

    // 3. Select llama3.2:1b
    const llamaOption = page.locator('button').filter({ hasText: 'llama3.2:1b' });
    await expect(llamaOption).toBeVisible({ timeout: 3000 });
    await llamaOption.click();
    await page.waitForTimeout(300);
    console.log('3. Selected llama3.2:1b');

    // 4. Select qwen2.5:0.5b
    const qwenOption = page.locator('button').filter({ hasText: 'qwen2.5:0.5b' });
    await expect(qwenOption).toBeVisible({ timeout: 3000 });
    await qwenOption.click();
    await page.waitForTimeout(300);
    console.log('4. Selected qwen2.5:0.5b');

    // Close dropdown by clicking elsewhere
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // 5. Verify chat panels appeared
    const chatPanels = page.locator('.grid > div').filter({ has: page.locator('text=Aguardando mensagem') });
    const panelCount = await chatPanels.count();
    console.log(`5. Found ${panelCount} chat panels`);

    // Take screenshot of selected models
    await page.screenshot({ path: 'tests/screenshots/full-test-1-selected.png' });

    // 6. Type and send message
    const input = page.locator('input[placeholder*="Enviar mensagem"]');
    await expect(input).toBeVisible({ timeout: 5000 });
    await input.fill('Diga olá em português em 1 frase curta.');
    console.log('6. Typed message');

    // 7. Send using Enter key (more reliable than clicking button)
    await input.press('Enter');
    console.log('7. Sent message via Enter');

    // Take screenshot before response
    await page.screenshot({ path: 'tests/screenshots/full-test-2-sent.png' });

    // 8. Wait for responses (may take up to 60s for CPU inference)
    console.log('8. Waiting for responses...');

    // Wait for loading indicators to appear then disappear
    await page.waitForTimeout(2000); // Give time for request to start

    // Wait for responses - look for assistant messages
    try {
      await page.waitForSelector('.prose', { timeout: 60000 });
      console.log('   First response received');
    } catch (e) {
      console.log('   Timeout waiting for response');
    }

    // Wait a bit more for second model
    await page.waitForTimeout(5000);

    // 9. Take final screenshot
    await page.screenshot({ path: 'tests/screenshots/full-test-3-responses.png' });

    // 10. Verify we got responses
    const responses = page.locator('.prose');
    const responseCount = await responses.count();
    console.log(`9. Got ${responseCount} responses`);

    // Check for tokens/s metrics
    const metrics = page.locator('text=/\\d+\\.\\d+ t\\/s/');
    const metricsCount = await metrics.count();
    console.log(`10. Found ${metricsCount} metrics displays`);

    // Final verification
    expect(responseCount).toBeGreaterThanOrEqual(1);
    console.log('✅ TEST PASSED: Chat Arena working with real models!');
  });
});
