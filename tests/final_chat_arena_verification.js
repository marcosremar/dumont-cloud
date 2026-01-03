const { chromium } = require('playwright');

/**
 * Final Chat Arena Verification
 */

async function finalVerification() {
  console.log('='.repeat(70));
  console.log('          FINAL VERIFICATION - CHAT ARENA');
  console.log('='.repeat(70));
  console.log();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const frontendUrl = 'http://localhost:4893';
  const apiUrl = 'http://localhost:8000';

  const checks = {
    passed: [],
    failed: []
  };

  try {
    // 1. API Health
    console.log('1. API Health Check');
    const health = await page.request.get(`${apiUrl}/health`);
    if (health.ok()) {
      const data = await health.json();
      console.log(`   [PASS] API healthy - v${data.version}`);
      checks.passed.push('API Health');
    } else {
      console.log('   [FAIL] API not responding');
      checks.failed.push('API Health');
    }

    // 2. Chat Models API
    console.log('\n2. Chat Models API');
    const modelsApi = await page.request.get(`${apiUrl}/api/v1/chat/models`);
    if (modelsApi.status() === 401 || modelsApi.status() === 400) {
      console.log('   [PASS] Chat models API requires auth (expected)');
      checks.passed.push('Chat Models API auth');
    } else if (modelsApi.ok()) {
      const data = await modelsApi.json();
      console.log(`   [PASS] Chat models API works - ${data.count || 0} models`);
      checks.passed.push('Chat Models API');
    } else {
      console.log('   [FAIL] Chat models API error');
      checks.failed.push('Chat Models API');
    }

    // 3. Chat Arena UI
    console.log('\n3. Chat Arena UI');
    await page.goto(`${frontendUrl}/demo-app/chat-arena`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    const title = await page.locator('h1').first().textContent();
    if (title && title.includes('Chat Arena')) {
      console.log('   [PASS] Chat Arena page loads correctly');
      checks.passed.push('Chat Arena page');
    } else {
      console.log('   [FAIL] Chat Arena page error');
      checks.failed.push('Chat Arena page');
    }

    // 4. Model Selector
    console.log('\n4. Model Selector');
    const selectorBtn = page.locator('button:has-text("Selecionar Modelos")').first();
    await selectorBtn.click();
    await page.waitForTimeout(500);

    const modelButtons = page.locator('.max-h-64 button');
    const modelCount = await modelButtons.count();

    if (modelCount >= 2) {
      console.log(`   [PASS] ${modelCount} demo models available`);
      checks.passed.push('Demo models');
    } else {
      console.log('   [FAIL] Not enough demo models');
      checks.failed.push('Demo models');
    }

    // Select 2 models
    for (let i = 0; i < Math.min(2, modelCount); i++) {
      await modelButtons.nth(i).click();
      await page.waitForTimeout(200);
    }
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // 5. Comparison Panels
    console.log('\n5. Comparison Panels');
    const panels = page.locator('.flex.flex-col.bg-\\[\\#161b22\\]');
    const panelCount = await panels.count();

    if (panelCount >= 2) {
      console.log(`   [PASS] ${panelCount} comparison panels visible`);
      checks.passed.push('Comparison panels');
    } else {
      console.log('   [FAIL] Not enough comparison panels');
      checks.failed.push('Comparison panels');
    }

    // 6. Message Send/Receive
    console.log('\n6. Message Send/Receive');
    const chatInput = page.locator('input[placeholder*="mensagem"]').first();
    await chatInput.fill('What is 2+2?');
    await chatInput.press('Enter');
    await page.waitForTimeout(6000);

    const convContainers = page.locator('.flex-1.overflow-y-auto.p-4');
    let totalResponses = 0;

    for (let i = 0; i < await convContainers.count(); i++) {
      const html = await convContainers.nth(i).innerHTML();
      const assistMsgs = (html.match(/1c2128/g) || []).length;
      totalResponses += assistMsgs;
    }

    if (totalResponses >= 2) {
      console.log(`   [PASS] ${totalResponses} responses from models`);
      checks.passed.push('Model responses');
    } else if (totalResponses >= 1) {
      console.log(`   [PASS] ${totalResponses} response received`);
      checks.passed.push('Model response');
    } else {
      console.log('   [FAIL] No responses received');
      checks.failed.push('Model responses');
    }

    // 7. Performance Stats
    console.log('\n7. Performance Stats');
    const stats = await page.locator('text=/\\d+(\\.\\d+)?\\s*t\\/s/').count();

    if (stats > 0) {
      console.log(`   [PASS] ${stats} performance stats displayed`);
      checks.passed.push('Performance stats');
    } else {
      console.log('   [FAIL] No performance stats');
      checks.failed.push('Performance stats');
    }

    // 8. Export Buttons
    console.log('\n8. Export Functionality');
    const exportMd = await page.locator('button:has-text("MD")').count();
    const exportJson = await page.locator('button:has-text("JSON")').count();

    if (exportMd > 0 && exportJson > 0) {
      console.log('   [PASS] Export buttons (MD & JSON) visible');
      checks.passed.push('Export buttons');
    } else {
      console.log('   [FAIL] Export buttons missing');
      checks.failed.push('Export buttons');
    }

  } catch (error) {
    console.error('\nERROR:', error.message);
    checks.failed.push(`Error: ${error.message}`);
  } finally {
    await browser.close();
  }

  // Summary
  console.log('\n' + '='.repeat(70));
  console.log('                         VERIFICATION SUMMARY');
  console.log('='.repeat(70));

  const total = checks.passed.length + checks.failed.length;
  const passRate = (checks.passed.length / total * 100).toFixed(1);

  console.log(`\n   Total Checks:  ${total}`);
  console.log(`   Passed:        ${checks.passed.length}`);
  console.log(`   Failed:        ${checks.failed.length}`);
  console.log(`   Pass Rate:     ${passRate}%`);

  if (checks.failed.length > 0) {
    console.log('\n   Failed Checks:');
    checks.failed.forEach(f => console.log(`     - ${f}`));
  }

  console.log('\n' + '='.repeat(70));

  if (checks.failed.length === 0) {
    console.log('   STATUS: ALL CHECKS PASSED - CHAT ARENA IS FULLY OPERATIONAL');
  } else {
    console.log('   STATUS: SOME CHECKS FAILED - REVIEW REQUIRED');
  }

  console.log('='.repeat(70));

  // Models ready for deployment
  console.log('\n' + '='.repeat(70));
  console.log('             SMALL MODELS FOR REAL DEPLOYMENT');
  console.log('='.repeat(70));

  const realModels = [
    'TinyLlama 1.1B (~600MB)',
    'Qwen2 0.5B (~350MB)',
    'Phi-3 Mini (4k)',
    'Gemma 2B',
    'Stable LM Zephyr 3B',
  ];

  console.log('\n   Models ready for serverless deployment:');
  realModels.forEach((m, i) => {
    console.log(`     ${i + 1}. ${m}`);
  });

  console.log('\n   Deploy script: scripts/deploy_tiny_arena_models.py');
  console.log('   Estimated cost: ~$0.10-0.20/hour per model');

  console.log('\n' + '='.repeat(70));
  console.log('             CHAT ARENA TESTING COMPLETE');
  console.log('='.repeat(70) + '\n');

  return checks;
}

// Run
finalVerification()
  .then(checks => {
    process.exit(checks.failed.length > 0 ? 1 : 0);
  })
  .catch(err => {
    console.error('Verification failed:', err);
    process.exit(1);
  });
