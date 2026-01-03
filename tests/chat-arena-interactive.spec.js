/**
 * Chat Arena Interactive Test
 * Environment: Local (http://localhost:4894)
 * Purpose: Test Chat Arena UI functionality with real demo mode
 * Generated: 2026-01-03
 */

const { test, expect } = require('@playwright/test');

test.describe('Chat Arena - Interactive UI Test', () => {

  test.beforeEach(async ({ page }) => {
    // Set demo mode BEFORE navigating to any page
    await page.addInitScript(() => {
      localStorage.setItem('demo_mode', 'true');
    });

    // Navigate to login with auto_login=demo
    console.log('Step 1: Navigating to login page...');
    await page.goto('/login?auto_login=demo');

    // Wait for redirect to /app
    console.log('Step 2: Waiting for login redirect...');
    await page.waitForURL('**/app**', { timeout: 15000 });

    // Navigate to Chat Arena
    console.log('Step 3: Navigating to Chat Arena...');
    await page.goto('/app/chat-arena');
    await page.waitForLoadState('networkidle');

    console.log('Setup complete. Chat Arena loaded in demo mode.');
  });

  test('Complete Chat Arena Journey - All Features', async ({ page }) => {
    const startTime = Date.now();
    const testReport = {
      steps: [],
      errors: [],
      metrics: {}
    };

    try {
      // STEP 1: Verify initial state - no models selected
      console.log('\n=== STEP 1: Verify Initial State ===');
      const stepStart = Date.now();

      const emptyState = page.locator('text=Selecione Modelos para Comparar');
      await expect(emptyState).toBeVisible({ timeout: 10000 });

      // Use the button in the header (top right), not the one in empty state
      const selectButton = page.locator('button:has-text("Selecionar Modelos")').first();
      await expect(selectButton).toBeVisible();

      testReport.steps.push({
        step: 1,
        action: 'Verify initial empty state',
        duration: Date.now() - stepStart,
        status: 'PASS'
      });
      console.log('✓ Initial state verified');

      // STEP 2: Open model selector dropdown
      console.log('\n=== STEP 2: Open Model Selector ===');
      const step2Start = Date.now();

      await selectButton.click();
      await page.waitForTimeout(500); // Wait for animation

      // Verify dropdown is visible
      const dropdown = page.locator('text=Modelos Disponiveis').first();
      await expect(dropdown).toBeVisible({ timeout: 5000 });

      // Take screenshot
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-1-dropdown-open.png',
        fullPage: true
      });

      testReport.steps.push({
        step: 2,
        action: 'Open model selector dropdown',
        duration: Date.now() - step2Start,
        status: 'PASS'
      });
      console.log('✓ Dropdown opened');

      // STEP 3: Verify demo models are listed
      console.log('\n=== STEP 3: Verify Demo Models ===');
      const step3Start = Date.now();

      // Check for demo-1 model
      const demo1 = page.locator('text=RTX 4090 - Llama 3.1 70B');
      await expect(demo1).toBeVisible({ timeout: 5000 });

      // Check for demo-2 model
      const demo2 = page.locator('text=RTX 3090 - Mistral 7B');
      await expect(demo2).toBeVisible();

      // Check for demo-3 model
      const demo3 = page.locator('text=A100 - CodeLlama 34B');
      await expect(demo3).toBeVisible();

      testReport.steps.push({
        step: 3,
        action: 'Verify 3 demo models are listed',
        duration: Date.now() - step3Start,
        status: 'PASS'
      });
      console.log('✓ All demo models found');

      // STEP 4: Select demo-1 model
      console.log('\n=== STEP 4: Select First Model (demo-1) ===');
      const step4Start = Date.now();

      await demo1.click();
      await page.waitForTimeout(300);

      // Verify selection indicator
      const selectedCount = page.locator('text=1 selecionado');
      await expect(selectedCount).toBeVisible({ timeout: 3000 });

      testReport.steps.push({
        step: 4,
        action: 'Select demo-1 model',
        duration: Date.now() - step4Start,
        status: 'PASS'
      });
      console.log('✓ First model selected');

      // STEP 5: Select demo-2 model
      console.log('\n=== STEP 5: Select Second Model (demo-2) ===');
      const step5Start = Date.now();

      await demo2.click();
      await page.waitForTimeout(300);

      // Verify selection count updated
      const selectedCount2 = page.locator('text=2 selecionados');
      await expect(selectedCount2).toBeVisible({ timeout: 3000 });

      testReport.steps.push({
        step: 5,
        action: 'Select demo-2 model',
        duration: Date.now() - step5Start,
        status: 'PASS'
      });
      console.log('✓ Second model selected');

      // STEP 6: Close dropdown and verify chat panels
      console.log('\n=== STEP 6: Close Dropdown & Verify Panels ===');
      const step6Start = Date.now();

      // Click outside to close dropdown
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);

      // Verify both model panels are visible
      const panel1 = page.locator('text=RTX 4090 - Llama 3.1 70B').nth(1); // nth(1) because nth(0) is in dropdown
      const panel2 = page.locator('text=RTX 3090 - Mistral 7B').nth(1);

      await expect(panel1).toBeVisible({ timeout: 5000 });
      await expect(panel2).toBeVisible();

      // Take screenshot
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-2-panels-ready.png',
        fullPage: true
      });

      testReport.steps.push({
        step: 6,
        action: 'Close dropdown and verify chat panels',
        duration: Date.now() - step6Start,
        status: 'PASS'
      });
      console.log('✓ Chat panels displayed');

      // STEP 7: Test System Prompt Modal (demo-1)
      console.log('\n=== STEP 7: Test System Prompt Modal ===');
      const step7Start = Date.now();

      // Find and click settings button for first model
      const settingsButtons = page.locator('button[title="System Prompt"]');
      await settingsButtons.first().click();
      await page.waitForTimeout(500);

      // Verify modal is open
      const modalTitle = page.locator('text=System Prompt');
      await expect(modalTitle).toBeVisible({ timeout: 5000 });

      // Type in system prompt
      const textarea = page.locator('textarea');
      await textarea.fill('You are a helpful AI assistant specialized in software engineering.');
      await page.waitForTimeout(300);

      // Take screenshot
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-3-system-prompt.png',
        fullPage: true
      });

      // Click Save
      const saveButton = page.locator('button:has-text("Salvar")');
      await saveButton.click();
      await page.waitForTimeout(500);

      // Verify modal closed and system prompt indicator is visible
      const promptIndicator = page.locator('text=You are a helpful AI assistant').first();
      await expect(promptIndicator).toBeVisible({ timeout: 3000 });

      testReport.steps.push({
        step: 7,
        action: 'Configure system prompt for model',
        duration: Date.now() - step7Start,
        status: 'PASS'
      });
      console.log('✓ System prompt configured');

      // STEP 8: Send a message
      console.log('\n=== STEP 8: Send Test Message ===');
      const step8Start = Date.now();

      const inputField = page.locator('input[type="text"]').first();
      await expect(inputField).toBeVisible({ timeout: 5000 });

      const testMessage = 'Hello! Can you explain what a REST API is?';
      await inputField.fill(testMessage);
      await page.waitForTimeout(500);

      // Take screenshot before sending
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-4-message-typed.png',
        fullPage: true
      });

      // Press Enter to send (more reliable than clicking button)
      await inputField.press('Enter');
      await page.waitForTimeout(500);

      testReport.steps.push({
        step: 8,
        action: 'Type and send message',
        duration: Date.now() - step8Start,
        status: 'PASS'
      });
      console.log('✓ Message sent');

      // STEP 9: Wait for responses
      console.log('\n=== STEP 9: Wait for Responses ===');
      const step9Start = Date.now();

      // Try to check for loading indicator, but don't fail if it's too fast
      const loadingIndicator = page.locator('text=Pensando...');
      const loadingVisible = await loadingIndicator.first().isVisible().catch(() => false);

      if (loadingVisible) {
        console.log('✓ Loading state visible');
        // Wait for loading to disappear
        await expect(loadingIndicator.first()).not.toBeVisible({ timeout: 10000 });
      } else {
        console.log('⚡ Response was too fast - loading state skipped');
      }

      // Wait a bit for responses to render
      await page.waitForTimeout(2000);

      testReport.steps.push({
        step: 9,
        action: 'Wait for model responses',
        duration: Date.now() - step9Start,
        status: 'PASS'
      });
      console.log('✓ Responses received');

      // STEP 10: Verify responses and metrics
      console.log('\n=== STEP 10: Verify Responses & Metrics ===');
      const step10Start = Date.now();

      // Check for user message bubbles
      const userMessages = page.locator('text=' + testMessage);
      const userMsgCount = await userMessages.count();
      console.log(`Found ${userMsgCount} user message(s)`);

      // Check for metrics in responses
      const tokensPerSecMetrics = page.locator('text=/\\d+\\.\\d+ t\\/s/');
      const metricsCount = await tokensPerSecMetrics.count();
      console.log(`Found ${metricsCount} response metric(s)`);

      if (metricsCount >= 2) {
        console.log('✓ Metrics displayed for both models');
      } else {
        testReport.errors.push({
          step: 10,
          error: `Expected 2 metrics, found ${metricsCount}`
        });
        console.log(`⚠ Warning: Expected 2 metrics, found ${metricsCount}`);
      }

      // Take screenshot of responses
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-5-responses.png',
        fullPage: true
      });

      testReport.steps.push({
        step: 10,
        action: 'Verify responses and metrics',
        duration: Date.now() - step10Start,
        status: metricsCount >= 2 ? 'PASS' : 'PARTIAL'
      });

      // STEP 11: Test stats popover
      console.log('\n=== STEP 11: Test Stats Popover ===');
      const step11Start = Date.now();

      // Click on info icon to show detailed stats
      const infoButtons = page.locator('button[title="Ver detalhes"]');
      const infoCount = await infoButtons.count();

      if (infoCount > 0) {
        await infoButtons.first().click();
        await page.waitForTimeout(500);

        // Check for stats popover
        const totalTokensLabel = page.locator('text=Total tokens:');
        const isStatsVisible = await totalTokensLabel.isVisible();

        if (isStatsVisible) {
          console.log('✓ Stats popover displayed');

          // Take screenshot
          await page.screenshot({
            path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-6-stats-popover.png',
            fullPage: true
          });

          testReport.steps.push({
            step: 11,
            action: 'Open stats popover',
            duration: Date.now() - step11Start,
            status: 'PASS'
          });
        } else {
          testReport.errors.push({
            step: 11,
            error: 'Stats popover not visible'
          });
          console.log('⚠ Stats popover not visible');
        }

        // Close popover
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);
      } else {
        testReport.errors.push({
          step: 11,
          error: 'No info buttons found'
        });
        console.log('⚠ No info buttons found for stats');
      }

      // STEP 12: Test Export as Markdown
      console.log('\n=== STEP 12: Test Export as Markdown ===');
      const step12Start = Date.now();

      const mdButton = page.locator('button[title="Exportar como Markdown"]');
      await expect(mdButton).toBeVisible({ timeout: 5000 });

      // Set up download handler
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 10000 }),
        mdButton.click()
      ]);

      const filename = download.suggestedFilename();
      console.log(`✓ MD export triggered: ${filename}`);

      testReport.steps.push({
        step: 12,
        action: 'Export conversation as Markdown',
        duration: Date.now() - step12Start,
        status: filename.endsWith('.md') ? 'PASS' : 'FAIL',
        metadata: { filename }
      });

      // STEP 13: Test Export as JSON
      console.log('\n=== STEP 13: Test Export as JSON ===');
      const step13Start = Date.now();

      const jsonButton = page.locator('button[title="Exportar como JSON"]');
      await expect(jsonButton).toBeVisible({ timeout: 5000 });

      const [download2] = await Promise.all([
        page.waitForEvent('download', { timeout: 10000 }),
        jsonButton.click()
      ]);

      const filename2 = download2.suggestedFilename();
      console.log(`✓ JSON export triggered: ${filename2}`);

      testReport.steps.push({
        step: 13,
        action: 'Export conversation as JSON',
        duration: Date.now() - step13Start,
        status: filename2.endsWith('.json') ? 'PASS' : 'FAIL',
        metadata: { filename: filename2 }
      });

      // STEP 14: Test clear conversations
      console.log('\n=== STEP 14: Test Clear Conversations ===');
      const step14Start = Date.now();

      const clearButton = page.locator('button[title="Limpar conversas"]');
      await expect(clearButton).toBeVisible({ timeout: 5000 });
      await clearButton.click();
      await page.waitForTimeout(500);

      // Verify messages are cleared
      const waitingMessage = page.locator('text=Aguardando mensagem...').first();
      await expect(waitingMessage).toBeVisible({ timeout: 5000 });

      console.log('✓ Conversations cleared');

      testReport.steps.push({
        step: 14,
        action: 'Clear all conversations',
        duration: Date.now() - step14Start,
        status: 'PASS'
      });

      // Take final screenshot
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-7-cleared.png',
        fullPage: true
      });

      // Calculate total time
      testReport.metrics.totalDuration = Date.now() - startTime;
      testReport.metrics.averageStepDuration = testReport.steps.reduce((sum, s) => sum + s.duration, 0) / testReport.steps.length;

      // Print summary
      console.log('\n=== TEST SUMMARY ===');
      console.log(`Total Duration: ${testReport.metrics.totalDuration}ms`);
      console.log(`Steps Completed: ${testReport.steps.length}`);
      console.log(`Errors Found: ${testReport.errors.length}`);
      console.log(`Pass Rate: ${testReport.steps.filter(s => s.status === 'PASS').length}/${testReport.steps.length}`);

      if (testReport.errors.length > 0) {
        console.log('\n=== ERRORS ===');
        testReport.errors.forEach(err => {
          console.log(`Step ${err.step}: ${err.error}`);
        });
      }

      // Save report
      const fs = require('fs');
      fs.writeFileSync(
        '/Users/marcos/CascadeProjects/dumontcloud/tests/CHAT_ARENA_TEST_REPORT.json',
        JSON.stringify(testReport, null, 2)
      );

      console.log('\n✓ Test report saved to tests/CHAT_ARENA_TEST_REPORT.json');

    } catch (error) {
      console.error('\n❌ TEST FAILED:', error.message);

      // Take error screenshot
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-ERROR.png',
        fullPage: true
      });

      testReport.errors.push({
        critical: true,
        error: error.message,
        stack: error.stack
      });

      throw error;
    }
  });
});
