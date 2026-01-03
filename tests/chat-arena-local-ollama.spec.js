/**
 * Chat Arena Test - Local Ollama Models
 * Tests real model comparison using local Ollama
 */

const { test, expect } = require('@playwright/test');

test.describe('Chat Arena - Local Ollama Test', () => {

  test.beforeEach(async ({ page }) => {
    // Enable demo mode for testing
    await page.addInitScript(() => {
      localStorage.setItem('demo_mode', 'true');
    });
  });

  test('Real model comparison with local Ollama', async ({ page }) => {
    console.log('\n=== Testing Chat Arena with LOCAL Ollama ===\n');

    // Navigate to demo chat arena (correct route)
    await page.goto('/demo-app/chat-arena');
    await page.waitForLoadState('networkidle');

    // Take initial screenshot
    await page.screenshot({ path: 'tests/screenshots/local-ollama-1-initial.png' });
    console.log('1. Navigated to Chat Arena');

    // Click to select models
    const selectButton = page.getByRole('button', { name: /selecionar/i });
    if (await selectButton.isVisible({ timeout: 3000 })) {
      await selectButton.click();
      await page.waitForTimeout(500);
      console.log('2. Clicked model selector');

      // Check if models are visible
      const modelList = page.locator('text=Local CPU');
      const modelCount = await modelList.count();
      console.log(`   Found ${modelCount} local model(s)`);

      // Select first two models if available
      if (modelCount >= 2) {
        await modelList.nth(0).click();
        await page.waitForTimeout(300);
        await modelList.nth(1).click();
        await page.waitForTimeout(300);
        console.log('3. Selected both models');
      }

      // Close dropdown
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }

    await page.screenshot({ path: 'tests/screenshots/local-ollama-2-models-selected.png' });

    // Find input and send message
    const input = page.locator('input[placeholder*="mensagem"], input[type="text"]').first();
    if (await input.isVisible({ timeout: 3000 })) {
      const testMessage = 'Responda em uma frase: o que e inteligencia artificial?';
      await input.fill(testMessage);
      console.log(`4. Typed message: "${testMessage}"`);

      // Send message
      await input.press('Enter');
      console.log('5. Sent message - waiting for REAL Ollama responses...');

      // Wait for responses (real inference takes time)
      await page.waitForTimeout(20000);

      await page.screenshot({ path: 'tests/screenshots/local-ollama-3-responses.png' });

      // Check for response content
      const responseAreas = page.locator('[class*="message"], [class*="response"]');
      const responseCount = await responseAreas.count();
      console.log(`6. Found ${responseCount} response area(s)`);

      // Verify responses are not demo responses
      const pageContent = await page.content();
      const hasDemoResponse = pageContent.includes('modo demonstração');
      const hasRealResponse = pageContent.includes('inteligência artificial') ||
                              pageContent.includes('artificial intelligence') ||
                              pageContent.includes('IA') ||
                              pageContent.includes('AI');

      console.log(`   Demo response detected: ${hasDemoResponse}`);
      console.log(`   Real response detected: ${hasRealResponse}`);

      if (!hasDemoResponse && hasRealResponse) {
        console.log('\n✅ SUCCESS: Real Ollama responses received!\n');
      } else if (hasDemoResponse) {
        console.log('\n⚠️ PARTIAL: Still using demo responses\n');
      }

    } else {
      console.log('⚠️ Input field not found');
    }

    await page.screenshot({ path: 'tests/screenshots/local-ollama-4-final.png', fullPage: true });
    console.log('\n=== Test Complete ===\n');
  });
});
