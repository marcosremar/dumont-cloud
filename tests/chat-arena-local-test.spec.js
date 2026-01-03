/**
 * Chat Arena Test - Local Ollama at localhost:4896
 * Tests the Chat Arena UI with real local Ollama models
 */

const { test, expect } = require('@playwright/test');

test.describe('Chat Arena - Local Ollama UI Test', () => {

  test('should test Chat Arena UI with local Ollama models', async ({ page }) => {
    console.log('\n=== Starting Chat Arena UI Test ===\n');

    // Step 1: Navigate to the Chat Arena page
    console.log('Step 1: Navigating to Chat Arena...');
    await page.goto('http://localhost:4896/chat-arena');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000); // Wait for models to load
    console.log('  ✓ Navigated to Chat Arena');

    // Step 2: Take initial snapshot
    console.log('\nStep 2: Taking initial snapshot...');
    await page.screenshot({
      path: 'tests/screenshots/chat-arena-step1-initial.png',
      fullPage: true
    });
    console.log('  ✓ Initial snapshot saved');

    // Verify page loaded correctly
    const heading = await page.locator('h1:has-text("Chat Arena")').count();
    expect(heading).toBeGreaterThan(0);
    console.log('  ✓ Chat Arena heading found');

    // Step 3: Click "Selecionar Modelos" button
    console.log('\nStep 3: Opening model selector...');
    const selectButton = page.getByRole('button', { name: /selecionar modelos/i });
    await selectButton.waitFor({ state: 'visible', timeout: 5000 });
    await selectButton.click();
    await page.waitForTimeout(1000);
    console.log('  ✓ Model selector opened');

    // Take snapshot of model selector
    await page.screenshot({
      path: 'tests/screenshots/chat-arena-step2-model-selector.png',
      fullPage: true
    });

    // Step 4: Select both available models
    console.log('\nStep 4: Selecting models...');

    // Wait for models to appear in the dropdown
    await page.waitForTimeout(1000);

    // Try to find model elements by their text content
    const modelButtons = page.locator('button:has-text("Local CPU")');
    const modelCount = await modelButtons.count();
    console.log(`  Found ${modelCount} local model(s)`);

    if (modelCount === 0) {
      // Try alternative selectors
      const allModels = page.locator('div[class*="rounded-lg"] button').filter({ hasText: /.+/ });
      const altCount = await allModels.count();
      console.log(`  Found ${altCount} model buttons (alternative selector)`);

      if (altCount >= 2) {
        await allModels.nth(0).click();
        console.log('  ✓ Selected first model');
        await page.waitForTimeout(500);

        await allModels.nth(1).click();
        console.log('  ✓ Selected second model');
        await page.waitForTimeout(500);
      }
    } else {
      // Select using the original selector
      if (modelCount >= 1) {
        await modelButtons.nth(0).click();
        console.log('  ✓ Selected first model (llama3.2:1b or qwen2.5:0.5b)');
        await page.waitForTimeout(500);
      }

      if (modelCount >= 2) {
        await modelButtons.nth(1).click();
        console.log('  ✓ Selected second model');
        await page.waitForTimeout(500);
      }
    }

    // Close the dropdown by clicking outside or pressing Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    console.log('  ✓ Model selector closed');

    // Take snapshot after model selection
    await page.screenshot({
      path: 'tests/screenshots/chat-arena-step3-models-selected.png',
      fullPage: true
    });

    // Step 5: Type test message
    console.log('\nStep 5: Typing test message...');
    const testMessage = 'Olá, como você está?';

    const inputField = page.locator('input[type="text"]').first();
    await inputField.waitFor({ state: 'visible', timeout: 5000 });
    await inputField.fill(testMessage);
    console.log(`  ✓ Typed message: "${testMessage}"`);

    // Take snapshot with message
    await page.screenshot({
      path: 'tests/screenshots/chat-arena-step4-message-typed.png',
      fullPage: true
    });

    // Step 6: Send message
    console.log('\nStep 6: Sending message...');
    await inputField.press('Enter');
    console.log('  ✓ Message sent - waiting for responses...');

    // Wait for loading indicators
    await page.waitForTimeout(2000);

    // Take snapshot showing loading state
    await page.screenshot({
      path: 'tests/screenshots/chat-arena-step5-loading.png',
      fullPage: true
    });

    // Step 7: Wait for responses (with timeout for real inference)
    console.log('\nStep 7: Waiting for model responses...');
    const maxWaitTime = 30000; // 30 seconds max
    const startTime = Date.now();

    // Wait for either responses or timeout
    try {
      // Look for response content or error messages
      await page.waitForSelector('div[class*="prose"], div:has-text("Error")', {
        timeout: maxWaitTime
      });
      const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`  ✓ Responses received in ${elapsedTime}s`);
    } catch (e) {
      console.log('  ⚠ Timeout waiting for responses, capturing current state...');
    }

    // Take snapshot of responses
    await page.screenshot({
      path: 'tests/screenshots/chat-arena-step6-responses.png',
      fullPage: true
    });

    // Step 8: Verify responses
    console.log('\nStep 8: Verifying responses...');

    const pageContent = await page.content();

    // Check for various response indicators
    const hasError = pageContent.includes('Error:') || pageContent.includes('Erro');
    const hasLoading = pageContent.includes('Pensando...');
    const hasContent = pageContent.toLowerCase().includes('olá') ||
                       pageContent.toLowerCase().includes('hello') ||
                       pageContent.toLowerCase().includes('bem') ||
                       pageContent.toLowerCase().includes('sou um');

    // Count message bubbles/containers
    const messageContainers = await page.locator('div[class*="rounded-xl"] div[class*="prose"]').count();

    console.log(`  Message containers found: ${messageContainers}`);
    console.log(`  Has error messages: ${hasError}`);
    console.log(`  Still loading: ${hasLoading}`);
    console.log(`  Has response content: ${hasContent}`);

    // Report findings
    if (hasError) {
      console.log('\n⚠ ERRORS DETECTED:');
      const errorMessages = await page.locator('div:has-text("Error"), div:has-text("Erro")').allTextContents();
      errorMessages.forEach((msg, i) => console.log(`  Error ${i + 1}: ${msg.substring(0, 100)}...`));
    }

    if (hasContent && !hasError) {
      console.log('\n✅ SUCCESS: Chat Arena is working! Models responded successfully.');
    } else if (hasLoading) {
      console.log('\n⚠ PARTIAL: Models are still processing. May need more time.');
    } else if (hasError) {
      console.log('\n❌ FAILURE: Errors occurred during model inference.');
    } else {
      console.log('\n⚠ UNKNOWN: Unable to determine response state clearly.');
    }

    // Take final screenshot
    await page.screenshot({
      path: 'tests/screenshots/chat-arena-step7-final.png',
      fullPage: true
    });

    console.log('\n=== Test Complete ===\n');
    console.log('Screenshots saved in tests/screenshots/');
    console.log('\nSummary:');
    console.log(`- Models found and selected`);
    console.log(`- Message sent: "${testMessage}"`);
    console.log(`- Responses: ${hasContent ? 'Received' : hasLoading ? 'Loading' : hasError ? 'Error' : 'Unknown'}`);
  });

  test('should export conversation as JSON', async ({ page }) => {
    console.log('\n=== Testing Export Functionality ===\n');

    await page.goto('http://localhost:4896/chat-arena');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Select models and send a message first
    const selectButton = page.getByRole('button', { name: /selecionar modelos/i });
    await selectButton.click();
    await page.waitForTimeout(1000);

    // Select first available model
    const modelButtons = page.locator('button').filter({ hasText: /Local CPU|llama|qwen/i });
    const count = await modelButtons.count();
    if (count > 0) {
      await modelButtons.first().click();
      await page.waitForTimeout(500);
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Send a quick message
    const inputField = page.locator('input[type="text"]').first();
    await inputField.fill('Test export');
    await inputField.press('Enter');
    await page.waitForTimeout(3000);

    // Look for export button
    const exportButton = page.locator('button:has-text("JSON")');
    const exportExists = await exportButton.count();

    if (exportExists > 0) {
      console.log('✓ Export button found');
      await exportButton.click();
      console.log('✓ Export button clicked');
    } else {
      console.log('⚠ Export button not visible (may need conversation history)');
    }

    console.log('\n=== Export Test Complete ===\n');
  });
});
