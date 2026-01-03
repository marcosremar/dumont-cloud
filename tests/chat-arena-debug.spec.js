/**
 * Chat Arena Debug Test
 * Detailed debugging of Chat Arena UI with verbose logging
 */

const { test, expect } = require('@playwright/test');

test.describe('Chat Arena - Debug Mode', () => {

  test('detailed UI inspection and debugging', async ({ page }) => {
    // Enable console logging from the page
    page.on('console', msg => {
      console.log(`[BROWSER] ${msg.type()}: ${msg.text()}`);
    });

    // Log network requests
    page.on('request', request => {
      if (request.url().includes('/api/') || request.url().includes('/ollama')) {
        console.log(`[REQUEST] ${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (response.url().includes('/api/') || response.url().includes('/ollama')) {
        console.log(`[RESPONSE] ${response.status()} ${response.url()}`);
      }
    });

    // Log page errors
    page.on('pageerror', error => {
      console.log(`[PAGE ERROR] ${error.message}`);
    });

    console.log('\n=== Chat Arena Debug Test ===\n');

    // Navigate
    console.log('1. Navigating to Chat Arena...');
    await page.goto('http://localhost:4896/chat-arena');
    await page.waitForLoadState('domcontentloaded');
    console.log('   Page loaded');

    // Wait for React to hydrate
    await page.waitForTimeout(2000);

    // Check localStorage
    const demoMode = await page.evaluate(() => localStorage.getItem('demo_mode'));
    console.log(`   Demo mode: ${demoMode}`);

    // Take initial screenshot
    await page.screenshot({ path: 'tests/screenshots/debug-1-initial.png', fullPage: true });

    // Inspect page structure
    console.log('\n2. Inspecting page structure...');

    const headingText = await page.locator('h1').first().textContent();
    console.log(`   Page heading: "${headingText}"`);

    const buttons = await page.locator('button').allTextContents();
    console.log(`   Found ${buttons.length} buttons`);
    buttons.slice(0, 10).forEach((text, i) => {
      console.log(`   - Button ${i + 1}: "${text.trim().substring(0, 50)}"`);
    });

    // Look for model selector button
    console.log('\n3. Looking for model selector...');
    const selectorButton = page.locator('button:has-text("Selecionar")');
    const selectorCount = await selectorButton.count();
    console.log(`   Model selector buttons found: ${selectorCount}`);

    if (selectorCount > 0) {
      const buttonText = await selectorButton.first().textContent();
      console.log(`   Button text: "${buttonText}"`);

      // Click to open
      await selectorButton.first().click();
      console.log('   Clicked model selector');

      await page.waitForTimeout(1500);
      await page.screenshot({ path: 'tests/screenshots/debug-2-selector-open.png', fullPage: true });

      // Look for models in dropdown
      console.log('\n4. Inspecting available models...');

      // Try multiple selectors to find models
      const modelLocators = [
        page.locator('button:has-text("Local CPU")'),
        page.locator('button:has-text("llama")'),
        page.locator('button:has-text("qwen")'),
        page.locator('div[class*="max-h-64"] button'),
        page.locator('[role="button"]:has-text("CPU")'),
      ];

      for (let i = 0; i < modelLocators.length; i++) {
        const count = await modelLocators[i].count();
        console.log(`   Selector ${i + 1} found ${count} elements`);

        if (count > 0) {
          const texts = await modelLocators[i].allTextContents();
          texts.forEach((text, idx) => {
            console.log(`     - Model ${idx + 1}: "${text.trim().substring(0, 60)}"`);
          });
        }
      }

      // Get all visible text in the dropdown
      const dropdownText = await page.locator('div[class*="max-h-64"]').first().textContent();
      console.log(`\n   Dropdown full text: "${dropdownText.trim().substring(0, 200)}..."`);

      // Try to select models
      console.log('\n5. Attempting to select models...');

      const modelButtons = page.locator('div[class*="max-h-64"] button');
      const modelCount = await modelButtons.count();
      console.log(`   Found ${modelCount} model buttons`);

      if (modelCount >= 2) {
        // Select first model
        const firstModelText = await modelButtons.nth(0).textContent();
        console.log(`   Selecting model 1: "${firstModelText.trim().substring(0, 40)}"`);
        await modelButtons.nth(0).click();
        await page.waitForTimeout(500);
        await page.screenshot({ path: 'tests/screenshots/debug-3-model1-selected.png', fullPage: true });

        // Select second model
        const secondModelText = await modelButtons.nth(1).textContent();
        console.log(`   Selecting model 2: "${secondModelText.trim().substring(0, 40)}"`);
        await modelButtons.nth(1).click();
        await page.waitForTimeout(500);
        await page.screenshot({ path: 'tests/screenshots/debug-4-model2-selected.png', fullPage: true });

        // Close dropdown
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
        console.log('   Models selected and dropdown closed');

        await page.screenshot({ path: 'tests/screenshots/debug-5-models-ready.png', fullPage: true });

        // Check if chat grids appeared
        console.log('\n6. Checking for chat grids...');
        const chatGrids = await page.locator('div[class*="grid"]').count();
        console.log(`   Grid containers found: ${chatGrids}`);

        // Send a test message
        console.log('\n7. Sending test message...');
        const input = page.locator('input[type="text"]').first();
        const inputExists = await input.count();

        if (inputExists > 0) {
          const placeholder = await input.getAttribute('placeholder');
          console.log(`   Input placeholder: "${placeholder}"`);

          await input.fill('Olá! Como você está?');
          console.log('   Message typed');

          await page.screenshot({ path: 'tests/screenshots/debug-6-message-typed.png', fullPage: true });

          await input.press('Enter');
          console.log('   Message sent');

          await page.waitForTimeout(2000);
          await page.screenshot({ path: 'tests/screenshots/debug-7-message-sent.png', fullPage: true });

          // Wait and check for responses
          console.log('\n8. Waiting for responses...');
          await page.waitForTimeout(15000);

          await page.screenshot({ path: 'tests/screenshots/debug-8-after-wait.png', fullPage: true });

          // Check for response content
          const messages = await page.locator('div[class*="prose"]').allTextContents();
          console.log(`   Message elements found: ${messages.length}`);
          messages.forEach((msg, i) => {
            console.log(`   Message ${i + 1}: "${msg.trim().substring(0, 80)}..."`);
          });

          // Check for errors
          const errors = await page.locator('div:has-text("Error"), div:has-text("Erro")').allTextContents();
          if (errors.length > 0) {
            console.log('\n   ERRORS DETECTED:');
            errors.forEach((err, i) => {
              console.log(`   Error ${i + 1}: "${err.trim()}"`);
            });
          }

          // Check for loading indicators
          const loading = await page.locator('text=Pensando').count();
          console.log(`   Loading indicators: ${loading}`);

          await page.screenshot({ path: 'tests/screenshots/debug-9-final.png', fullPage: true });
        } else {
          console.log('   ❌ Input field not found!');
        }
      } else {
        console.log('   ❌ Not enough models found to select');
      }
    } else {
      console.log('   ❌ Model selector button not found');
    }

    console.log('\n=== Debug Test Complete ===\n');
  });
});
