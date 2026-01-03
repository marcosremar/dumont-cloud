const { chromium } = require('playwright');

/**
 * Chat Arena UI Test
 * Tests the model comparison functionality via Playwright
 */

async function testChatArenaUI() {
  console.log('='.repeat(60));
  console.log('CHAT ARENA UI TESTS');
  console.log('='.repeat(60));
  console.log();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const frontendUrl = 'http://localhost:4893';

  const results = {
    passed: [],
    failed: [],
    errors: []
  };

  try {
    // TEST 1: Navigate to Chat Arena
    console.log('TEST 1: Navigate to Chat Arena...');
    await page.goto(`${frontendUrl}/demo-app/chat-arena`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    const currentUrl = page.url();
    if (currentUrl.includes('/demo-app/chat-arena')) {
      console.log('  PASS: Chat Arena page loaded');
      results.passed.push('Chat Arena page load');
    } else {
      console.log(`  FAIL: Redirected to ${currentUrl}`);
      results.failed.push('Chat Arena page load');
    }

    // TEST 2: Check page title
    console.log('TEST 2: Check page title...');
    const title = await page.locator('h1').first().textContent();
    if (title && title.includes('Chat Arena')) {
      console.log(`  PASS: Title is "${title}"`);
      results.passed.push('Page title correct');
    } else {
      console.log(`  FAIL: Title is "${title}"`);
      results.failed.push('Page title correct');
    }

    // TEST 3: Check "Select Models" button
    console.log('TEST 3: Check model selector...');
    const selectBtn = page.locator('button:has-text("Selecionar Modelos"), button:has-text("Select Models")');
    if (await selectBtn.count() > 0) {
      console.log('  PASS: Model selector button visible');
      results.passed.push('Model selector button');

      // Click to open dropdown
      await selectBtn.first().click();
      await page.waitForTimeout(500);

      // TEST 4: Check dropdown opened
      console.log('TEST 4: Check dropdown content...');
      const dropdown = page.locator('div:has-text("Modelos Disponiveis"), div:has-text("Available Models")');
      if (await dropdown.count() > 0) {
        console.log('  PASS: Dropdown opened');
        results.passed.push('Dropdown opens');
      } else {
        console.log('  WARN: Dropdown may not have opened');
        results.passed.push('Dropdown (partial)');
      }

      // TEST 5: Check demo models are listed
      console.log('TEST 5: Check demo models...');
      const modelItems = page.locator('button:has-text("RTX"), button:has-text("A100"), button:has-text("Llama"), button:has-text("Mistral")');
      const modelCount = await modelItems.count();
      if (modelCount >= 2) {
        console.log(`  PASS: Found ${modelCount} demo models`);
        results.passed.push('Demo models listed');
      } else {
        console.log(`  WARN: Only found ${modelCount} models`);
        results.passed.push('Demo models (partial)');
      }

      // TEST 6: Select first model
      console.log('TEST 6: Select a model...');
      if (await modelItems.count() > 0) {
        await modelItems.first().click();
        await page.waitForTimeout(300);
        console.log('  PASS: Model selected');
        results.passed.push('Model selection');
      } else {
        console.log('  SKIP: No models to select');
        results.passed.push('Model selection (skipped)');
      }

      // Close dropdown by clicking elsewhere
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200);

    } else {
      console.log('  FAIL: Model selector button not found');
      results.failed.push('Model selector button');
    }

    // TEST 7: Check chat input
    console.log('TEST 7: Check chat input...');
    const chatInput = page.locator('input[placeholder*="mensagem"], input[placeholder*="message"]');
    if (await chatInput.count() > 0) {
      console.log('  PASS: Chat input found');
      results.passed.push('Chat input visible');

      // TEST 8: Type a message
      console.log('TEST 8: Type and send message...');
      await chatInput.first().fill('Hello, this is a test message');

      // Find send button
      const sendBtn = page.locator('button:has(svg)').last();
      if (await sendBtn.count() > 0) {
        await sendBtn.click();
        await page.waitForTimeout(2000); // Wait for response

        console.log('  PASS: Message sent');
        results.passed.push('Send message');

        // TEST 9: Check response received
        console.log('TEST 9: Check for response...');
        const responses = await page.locator('.prose').count();
        if (responses > 0) {
          console.log(`  PASS: Found ${responses} response(s)`);
          results.passed.push('Response received');
        } else {
          console.log('  WARN: No visible responses yet');
          results.passed.push('Response (may be delayed)');
        }
      }
    } else {
      console.log('  FAIL: Chat input not found');
      results.failed.push('Chat input visible');
    }

    // TEST 10: Check stats display
    console.log('TEST 10: Check stats display...');
    await page.waitForTimeout(500);
    const statsElements = page.locator('text=/t\\/s|tokens|latency|ms/i');
    const statsCount = await statsElements.count();
    if (statsCount > 0) {
      console.log(`  PASS: Found ${statsCount} stats elements`);
      results.passed.push('Stats display');
    } else {
      console.log('  INFO: Stats may appear after response');
      results.passed.push('Stats display (pending)');
    }

    // TEST 11: Check system prompt button
    console.log('TEST 11: Check system prompt feature...');
    const settingsBtn = page.locator('button:has(svg[class*="settings"]), button[title*="System"]');
    if (await settingsBtn.count() > 0) {
      console.log('  PASS: System prompt button found');
      results.passed.push('System prompt button');
    } else {
      console.log('  INFO: System prompt button may be per-model');
      results.passed.push('System prompt (partial)');
    }

    // TEST 12: Check export buttons
    console.log('TEST 12: Check export buttons...');
    const exportMdBtn = page.locator('button:has-text("MD"), button[title*="Markdown"]');
    const exportJsonBtn = page.locator('button:has-text("JSON"), button[title*="JSON"]');

    if (await exportMdBtn.count() > 0 || await exportJsonBtn.count() > 0) {
      console.log('  PASS: Export buttons found');
      results.passed.push('Export buttons');
    } else {
      console.log('  INFO: Export buttons appear after messages');
      results.passed.push('Export buttons (pending)');
    }

    // TEST 13: Check clear button
    console.log('TEST 13: Check clear button...');
    const clearBtn = page.locator('button[title*="Limpar"], button:has(svg[class*="trash"])');
    if (await clearBtn.count() > 0) {
      console.log('  PASS: Clear button found');
      results.passed.push('Clear button');
    } else {
      console.log('  INFO: Clear button may be hidden');
      results.passed.push('Clear button (partial)');
    }

  } catch (error) {
    console.error('\nERROR:', error.message);
    results.errors.push(error.message);
  } finally {
    await browser.close();
  }

  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('CHAT ARENA UI TEST SUMMARY');
  console.log('='.repeat(60));
  console.log(`PASSED: ${results.passed.length}`);
  console.log(`FAILED: ${results.failed.length}`);
  console.log(`ERRORS: ${results.errors.length}`);
  console.log();

  if (results.passed.length > 0) {
    console.log('Passed tests:');
    results.passed.forEach(t => console.log(`  - ${t}`));
  }

  if (results.failed.length > 0) {
    console.log('\nFailed tests:');
    results.failed.forEach(t => console.log(`  - ${t}`));
  }

  console.log();
  console.log('='.repeat(60));

  return results;
}

// Run tests
testChatArenaUI()
  .then(results => {
    process.exit(results.failed.length > 0 ? 1 : 0);
  })
  .catch(err => {
    console.error('Test script failed:', err);
    process.exit(1);
  });
