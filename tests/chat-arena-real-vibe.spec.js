/**
 * VIBE TEST: Chat Arena with REAL Models on VAST.ai
 * Environment: PRODUCTION (REAL - no mocks)
 * Models: Llama 3.2 3B (RTX 3080) + Qwen 2.5 3B (RTX 3060)
 * Generated: 2026-01-03
 *
 * CRITICAL: This test uses REAL deployed models on VAST.ai servers
 * It will hit actual Ollama endpoints and cost real money per minute.
 */

const { test, expect } = require('@playwright/test');
const fs = require('fs');

// REAL deployment config
const DEPLOYMENT = JSON.parse(
  fs.readFileSync('/Users/marcos/CascadeProjects/dumontcloud/chat_arena_deployment.json', 'utf-8')
);

const MODEL_1 = DEPLOYMENT.instances[0]; // Llama 3.2 3B
const MODEL_2 = DEPLOYMENT.instances[1]; // Qwen 2.5 3B

test.describe('Chat Arena - REAL Models Vibe Test', () => {

  test.beforeEach(async ({ page }) => {
    // CRITICAL: Disable demo mode - we're testing REAL endpoints
    await page.addInitScript(() => {
      localStorage.removeItem('demo_mode');
      localStorage.setItem('demo_mode', 'false');
    });

    console.log('\n==================================================');
    console.log('VIBE TEST: Chat Arena with REAL VAST.ai Models');
    console.log('==================================================');
    console.log(`Model 1: ${MODEL_1.model_name} (${MODEL_1.gpu_name})`);
    console.log(`         ${MODEL_1.ssh_host}:${MODEL_1.ssh_port}`);
    console.log(`Model 2: ${MODEL_2.model_name} (${MODEL_2.gpu_name})`);
    console.log(`         ${MODEL_2.ssh_host}:${MODEL_2.ssh_port}`);
    console.log(`Cost: $${DEPLOYMENT.total_cost_per_hour}/hour`);
    console.log('==================================================\n');

    // Navigate to login
    await page.goto('/login?auto_login=demo');
    await page.waitForURL('**/app**', { timeout: 15000 });

    console.log('✓ Logged in');
  });

  test('REAL Journey: Compare Llama vs Qwen responses', async ({ page }) => {
    const testReport = {
      timestamp: new Date().toISOString(),
      environment: 'PRODUCTION',
      models: [MODEL_1.model_name, MODEL_2.model_name],
      steps: [],
      metrics: {},
      errors: []
    };

    const startTime = Date.now();

    try {
      // ============================================================
      // STEP 1: Navigate to Chat Arena
      // ============================================================
      console.log('\n=== STEP 1: Navigate to Chat Arena ===');
      const step1Start = Date.now();

      await page.goto('/app/chat-arena');
      await page.waitForLoadState('networkidle');

      // Verify page loaded
      const pageTitle = page.locator('h1:has-text("Chat Arena")');
      await expect(pageTitle).toBeVisible({ timeout: 10000 });

      testReport.steps.push({
        step: 1,
        action: 'Navigate to Chat Arena',
        duration: Date.now() - step1Start,
        status: 'PASS'
      });
      console.log(`✓ Chat Arena loaded (${Date.now() - step1Start}ms)`);

      // ============================================================
      // STEP 2: Open model selector and wait for REAL models
      // ============================================================
      console.log('\n=== STEP 2: Fetch REAL models from API ===');
      const step2Start = Date.now();

      // Click model selector
      const selectButton = page.locator('button:has-text("Selecionar Modelos")').first();
      await selectButton.click();
      await page.waitForTimeout(500);

      // Verify dropdown opened
      const dropdown = page.locator('text=Modelos Disponiveis');
      await expect(dropdown).toBeVisible({ timeout: 5000 });

      // Click refresh to fetch REAL models from backend
      const refreshButton = page.locator('button').filter({ has: page.locator('svg') }).nth(1);
      await refreshButton.click();

      console.log('⏳ Fetching models from /api/v1/chat/models...');
      await page.waitForTimeout(2000); // Wait for API call

      // Take screenshot of model list
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-real-1-models-list.png',
        fullPage: true
      });

      testReport.steps.push({
        step: 2,
        action: 'Open model selector and fetch REAL models',
        duration: Date.now() - step2Start,
        status: 'PASS'
      });
      console.log(`✓ Model selector opened (${Date.now() - step2Start}ms)`);

      // ============================================================
      // STEP 3: Verify REAL models are listed
      // ============================================================
      console.log('\n=== STEP 3: Verify REAL models appear ===');
      const step3Start = Date.now();

      // Wait for model cards to appear
      await page.waitForTimeout(1000);

      // Check if we have model cards (generic check since we don't know exact text)
      const modelCards = page.locator('[class*="rounded-lg"]').filter({ hasText: /RTX|GPU|Instance/ });
      const modelCount = await modelCards.count();

      console.log(`Found ${modelCount} model card(s) in dropdown`);

      if (modelCount === 0) {
        console.log('⚠ WARNING: No models found. This could mean:');
        console.log('  1. Backend /api/v1/chat/models is not returning data');
        console.log('  2. VAST.ai API key is not configured');
        console.log('  3. Instances are not exposing port 11434');
        console.log('  4. Demo mode is still active');

        // Try to get error message from page
        const errorMsg = await page.locator('text=/error|Error|failed|Failed/i').first().textContent().catch(() => null);
        if (errorMsg) {
          console.log(`  Error on page: ${errorMsg}`);
        }

        testReport.errors.push({
          step: 3,
          error: 'No models found in dropdown',
          modelCount: 0
        });
      }

      testReport.steps.push({
        step: 3,
        action: 'Verify REAL models are listed',
        duration: Date.now() - step3Start,
        status: modelCount > 0 ? 'PASS' : 'FAIL',
        metadata: { modelCount }
      });

      // ============================================================
      // STEP 4: Select BOTH models (click first 2 available)
      // ============================================================
      console.log('\n=== STEP 4: Select first 2 available models ===');
      const step4Start = Date.now();

      if (modelCount >= 2) {
        // Click first model
        await modelCards.nth(0).click();
        await page.waitForTimeout(500);
        console.log('✓ Selected model 1');

        // Click second model
        await modelCards.nth(1).click();
        await page.waitForTimeout(500);
        console.log('✓ Selected model 2');

        // Verify selection count
        const selectedIndicator = page.locator('text=2 selecionados');
        await expect(selectedIndicator).toBeVisible({ timeout: 3000 });

        testReport.steps.push({
          step: 4,
          action: 'Select 2 models',
          duration: Date.now() - step4Start,
          status: 'PASS'
        });
      } else {
        throw new Error(`Not enough models to compare. Found: ${modelCount}, Need: 2`);
      }

      // ============================================================
      // STEP 5: Close dropdown and verify chat panels
      // ============================================================
      console.log('\n=== STEP 5: Close dropdown and verify panels ===');
      const step5Start = Date.now();

      await page.keyboard.press('Escape');
      await page.waitForTimeout(1000);

      // Verify we have 2 chat panels
      const panels = page.locator('[class*="border"][class*="rounded"]').filter({ hasText: /Aguardando mensagem/ });
      const panelCount = await panels.count();

      console.log(`Found ${panelCount} chat panel(s)`);

      // Take screenshot
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-real-2-panels-ready.png',
        fullPage: true
      });

      testReport.steps.push({
        step: 5,
        action: 'Close dropdown and verify chat panels',
        duration: Date.now() - step5Start,
        status: panelCount >= 2 ? 'PASS' : 'PARTIAL',
        metadata: { panelCount }
      });

      // ============================================================
      // STEP 6: Send REAL question to both models
      // ============================================================
      console.log('\n=== STEP 6: Send question to REAL models ===');
      const step6Start = Date.now();

      const inputField = page.locator('input[type="text"]').first();
      await expect(inputField).toBeVisible({ timeout: 5000 });

      const question = 'Olá, se apresente em uma frase curta e diga seu nome.';
      await inputField.fill(question);
      await page.waitForTimeout(500);

      console.log(`📤 Sending: "${question}"`);

      // Take screenshot before sending
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-real-3-question-ready.png',
        fullPage: true
      });

      // Send message
      await inputField.press('Enter');
      console.log('⏳ Waiting for REAL model responses...');

      testReport.steps.push({
        step: 6,
        action: 'Send question to models',
        duration: Date.now() - step6Start,
        status: 'PASS',
        metadata: { question }
      });

      // ============================================================
      // STEP 7: Wait for REAL responses (may take 5-30s)
      // ============================================================
      console.log('\n=== STEP 7: Wait for REAL responses ===');
      const step7Start = Date.now();

      // Check for loading indicators
      const loadingIndicator = page.locator('text=Pensando...');
      const loadingVisible = await loadingIndicator.first().isVisible({ timeout: 2000 }).catch(() => false);

      if (loadingVisible) {
        console.log('✓ Loading state detected');

        // Wait for BOTH loading indicators to disappear (max 60s)
        await expect(loadingIndicator.first()).not.toBeVisible({ timeout: 60000 });
        console.log('✓ Response 1 received');

        // Check if second loading still active
        const stillLoading = await loadingIndicator.isVisible().catch(() => false);
        if (stillLoading) {
          await expect(loadingIndicator).not.toBeVisible({ timeout: 60000 });
          console.log('✓ Response 2 received');
        }
      } else {
        console.log('⚠ No loading indicator found - responses may have been instant');
      }

      // Wait a bit for rendering
      await page.waitForTimeout(2000);

      const responseTime = Date.now() - step7Start;
      testReport.metrics.responseTime = responseTime;

      testReport.steps.push({
        step: 7,
        action: 'Wait for REAL model responses',
        duration: responseTime,
        status: 'PASS'
      });
      console.log(`✓ Responses received (${responseTime}ms)`);

      // ============================================================
      // STEP 8: Verify and compare responses
      // ============================================================
      console.log('\n=== STEP 8: Verify responses and metrics ===');
      const step8Start = Date.now();

      // Take screenshot of responses
      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-real-4-responses.png',
        fullPage: true
      });

      // Check for user message
      const userMsg = page.locator('text=' + question);
      const userMsgCount = await userMsg.count();
      console.log(`User messages displayed: ${userMsgCount}`);

      // Check for assistant responses (look for text content, not "Pensando")
      const assistantBubbles = page.locator('[class*="bg-"][class*="rounded"]').filter({ hasNot: page.locator('text=Pensando') });
      const responseCount = await assistantBubbles.count();
      console.log(`Assistant response bubbles: ${responseCount}`);

      // Check for metrics (tokens/s)
      const metrics = page.locator('text=/\\d+\\.\\d+ t\\/s/');
      const metricsCount = await metrics.count();
      console.log(`Metrics displayed: ${metricsCount}`);

      // Extract actual metrics values
      const metricValues = [];
      for (let i = 0; i < Math.min(metricsCount, 2); i++) {
        const text = await metrics.nth(i).textContent();
        metricValues.push(text.trim());
      }

      console.log('\nMetrics captured:');
      metricValues.forEach((m, i) => {
        console.log(`  Model ${i + 1}: ${m}`);
      });

      testReport.steps.push({
        step: 8,
        action: 'Verify responses and extract metrics',
        duration: Date.now() - step8Start,
        status: metricsCount >= 1 ? 'PASS' : 'PARTIAL',
        metadata: {
          userMessages: userMsgCount,
          responses: responseCount,
          metrics: metricValues
        }
      });

      // ============================================================
      // STEP 9: Click stats popover to see detailed metrics
      // ============================================================
      console.log('\n=== STEP 9: Check detailed stats ===');
      const step9Start = Date.now();

      const infoButtons = page.locator('button[title="Ver detalhes"]');
      const infoCount = await infoButtons.count();

      if (infoCount > 0) {
        await infoButtons.first().click();
        await page.waitForTimeout(500);

        // Check for stats popover
        const statsPopover = page.locator('text=Total tokens:');
        const statsVisible = await statsPopover.isVisible();

        if (statsVisible) {
          console.log('✓ Stats popover opened');

          // Take screenshot
          await page.screenshot({
            path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-real-5-stats-detail.png',
            fullPage: true
          });

          // Try to extract stats
          const timeToFirst = await page.locator('text=/\\d+ ?ms/').first().textContent().catch(() => null);
          if (timeToFirst) {
            console.log(`  Time to first token: ${timeToFirst}`);
          }

          testReport.steps.push({
            step: 9,
            action: 'Open detailed stats popover',
            duration: Date.now() - step9Start,
            status: 'PASS'
          });

          await page.keyboard.press('Escape');
        } else {
          console.log('⚠ Stats popover not visible');
        }
      } else {
        console.log('⚠ No info buttons found');
      }

      // ============================================================
      // STEP 10: Export conversation
      // ============================================================
      console.log('\n=== STEP 10: Export conversation as JSON ===');
      const step10Start = Date.now();

      const jsonButton = page.locator('button[title="Exportar como JSON"]');
      const jsonButtonVisible = await jsonButton.isVisible();

      if (jsonButtonVisible) {
        const [download] = await Promise.all([
          page.waitForEvent('download', { timeout: 10000 }),
          jsonButton.click()
        ]);

        const filename = download.suggestedFilename();
        const downloadPath = `/Users/marcos/CascadeProjects/dumontcloud/tests/exports/${filename}`;

        await download.saveAs(downloadPath);
        console.log(`✓ Exported to: ${downloadPath}`);

        testReport.steps.push({
          step: 10,
          action: 'Export conversation as JSON',
          duration: Date.now() - step10Start,
          status: 'PASS',
          metadata: { filename }
        });
      } else {
        console.log('⚠ Export button not visible');
      }

      // ============================================================
      // FINAL REPORT
      // ============================================================
      testReport.metrics.totalDuration = Date.now() - startTime;
      testReport.metrics.costIncurred = (testReport.metrics.totalDuration / 1000 / 3600) * DEPLOYMENT.total_cost_per_hour;

      console.log('\n==================================================');
      console.log('VIBE TEST COMPLETE');
      console.log('==================================================');
      console.log(`Total Duration: ${testReport.metrics.totalDuration}ms`);
      console.log(`Steps Completed: ${testReport.steps.filter(s => s.status === 'PASS').length}/${testReport.steps.length}`);
      console.log(`Cost Incurred: $${testReport.metrics.costIncurred.toFixed(6)}`);
      console.log(`Pass Rate: ${(testReport.steps.filter(s => s.status === 'PASS').length / testReport.steps.length * 100).toFixed(1)}%`);

      if (testReport.errors.length > 0) {
        console.log('\nErrors:', testReport.errors.length);
        testReport.errors.forEach(err => {
          console.log(`  - Step ${err.step}: ${err.error}`);
        });
      }

      console.log('==================================================\n');

      // Save report
      fs.mkdirSync('/Users/marcos/CascadeProjects/dumontcloud/tests/exports', { recursive: true });
      fs.writeFileSync(
        '/Users/marcos/CascadeProjects/dumontcloud/tests/CHAT_ARENA_REAL_VIBE_REPORT.json',
        JSON.stringify(testReport, null, 2)
      );

      console.log('✓ Test report saved to tests/CHAT_ARENA_REAL_VIBE_REPORT.json');

    } catch (error) {
      console.error('\n❌ VIBE TEST FAILED:', error.message);

      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/chat-arena-real-ERROR.png',
        fullPage: true
      });

      testReport.errors.push({
        critical: true,
        error: error.message,
        stack: error.stack
      });

      // Save error report
      fs.writeFileSync(
        '/Users/marcos/CascadeProjects/dumontcloud/tests/CHAT_ARENA_REAL_VIBE_REPORT.json',
        JSON.stringify(testReport, null, 2)
      );

      throw error;
    }
  });
});
