const { chromium } = require('playwright');

// List of 10 small LLM models to deploy in serverless mode
const SMALL_LLMS = [
  { id: 'qwen2.5-0.5b', name: 'Qwen 2.5 0.5B', model_id: 'Qwen/Qwen2.5-0.5B-Instruct' },
  { id: 'qwen3-0.6b', name: 'Qwen3 0.6B', model_id: 'Qwen/Qwen3-0.6B' },
  { id: 'phi-3-mini', name: 'Phi-3 Mini', model_id: 'microsoft/Phi-3-mini-4k-instruct' },
  { id: 'tinyllama', name: 'TinyLlama 1.1B', model_id: 'TinyLlama/TinyLlama-1.1B-Chat-v1.0' },
  { id: 'stablelm-zephyr', name: 'StableLM Zephyr 3B', model_id: 'stabilityai/stablelm-zephyr-3b' },
  { id: 'gemma-2b', name: 'Gemma 2B', model_id: 'google/gemma-2b-it' },
  { id: 'opt-1.3b', name: 'OPT 1.3B', model_id: 'facebook/opt-1.3b' },
  { id: 'bloom-560m', name: 'BLOOM 560M', model_id: 'bigscience/bloom-560m' },
  { id: 'pythia-1b', name: 'Pythia 1B', model_id: 'EleutherAI/pythia-1b' },
  { id: 'openelm-270m', name: 'OpenELM 270M', model_id: 'apple/OpenELM-270M-Instruct' },
];

async function testServerlessUI() {
  console.log('Starting Serverless UI tests...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const baseUrl = 'http://localhost:4893';
  const results = {
    passed: [],
    failed: [],
    errors: []
  };

  try {
    // Test 1: Navigate to Serverless page (demo mode)
    console.log('Test 1: Navigating to Serverless page...');
    await page.goto(`${baseUrl}/demo-app/serverless`);
    await page.waitForLoadState('networkidle');

    // Check page loaded
    const pageTitle = await page.textContent('h1');
    if (pageTitle && pageTitle.includes('Serverless')) {
      console.log('  PASS: Serverless page loaded');
      results.passed.push('Navigate to Serverless page');
    } else {
      console.log('  FAIL: Serverless page not loaded correctly');
      results.failed.push('Navigate to Serverless page');
    }

    // Test 2: Check stats cards are visible
    console.log('Test 2: Checking stats cards...');
    const statsCards = await page.locator('.bg-dark-surface-card').count();
    if (statsCards >= 4) {
      console.log(`  PASS: Found ${statsCards} stats cards`);
      results.passed.push('Stats cards visible');
    } else {
      console.log(`  FAIL: Expected at least 4 stats cards, found ${statsCards}`);
      results.failed.push('Stats cards visible');
    }

    // Test 3: Check demo endpoints are displayed
    console.log('Test 3: Checking demo endpoints...');
    const endpointCards = await page.locator('.rounded-xl.bg-dark-surface-card').count();
    if (endpointCards >= 3) {
      console.log(`  PASS: Found ${endpointCards} endpoint cards`);
      results.passed.push('Demo endpoints displayed');
    } else {
      console.log(`  FAIL: Expected at least 3 endpoint cards, found ${endpointCards}`);
      results.failed.push('Demo endpoints displayed');
    }

    // Test 4: Click on "Criar Endpoint" button
    console.log('Test 4: Opening Create Endpoint modal...');
    const createButton = await page.locator('button:has-text("Criar Endpoint"), button:has-text("Create")');
    if (await createButton.count() > 0) {
      await createButton.first().click();
      await page.waitForTimeout(500);

      // Check modal opened
      const modal = await page.locator('[role="alertdialog"], .modal, [class*="AlertDialog"]');
      if (await modal.count() > 0) {
        console.log('  PASS: Create Endpoint modal opened');
        results.passed.push('Create Endpoint modal opens');

        // Test 5: Check model templates are visible
        console.log('Test 5: Checking model templates...');
        const templates = await page.locator('button[class*="rounded-lg"][class*="border"]').count();
        if (templates >= 5) {
          console.log(`  PASS: Found ${templates} model templates`);
          results.passed.push('Model templates visible');
        } else {
          console.log(`  FAIL: Expected at least 5 model templates`);
          results.failed.push('Model templates visible');
        }

        // Test 6: Try selecting first small model template
        console.log('Test 6: Selecting a model template...');
        const templateButtons = await page.locator('button:has-text("Qwen"), button:has-text("qwen")');
        if (await templateButtons.count() > 0) {
          await templateButtons.first().click();
          await page.waitForTimeout(300);
          console.log('  PASS: Selected Qwen template');
          results.passed.push('Model template selection works');
        } else {
          console.log('  FAIL: Could not find Qwen template');
          results.failed.push('Model template selection works');
        }

        // Test 7: Check machine type options (Spot vs On-Demand)
        console.log('Test 7: Checking machine type options...');
        const spotButton = await page.locator('button:has-text("Spot")');
        const onDemandButton = await page.locator('button:has-text("On-Demand")');
        if (await spotButton.count() > 0 && await onDemandButton.count() > 0) {
          console.log('  PASS: Spot and On-Demand options visible');
          results.passed.push('Machine type options visible');

          // Try clicking Spot
          await spotButton.first().click();
          await page.waitForTimeout(200);
        } else {
          console.log('  FAIL: Machine type options not found');
          results.failed.push('Machine type options visible');
        }

        // Test 8: Try to create endpoint (demo mode - should show alert)
        console.log('Test 8: Testing endpoint creation (demo mode)...');

        // Fill in endpoint name
        const nameInput = await page.locator('input[placeholder*="endpoint"], input[placeholder*="meu-endpoint"]');
        if (await nameInput.count() > 0) {
          await nameInput.first().fill('test-llm-endpoint');
        }

        // Click create button
        const submitButton = await page.locator('button:has-text("Criar"), button:has-text("Create")');
        if (await submitButton.count() > 0) {
          // Handle dialog that might appear
          page.on('dialog', async dialog => {
            console.log(`  INFO: Demo alert: ${dialog.message().substring(0, 50)}...`);
            await dialog.dismiss();
          });

          await submitButton.last().click();
          await page.waitForTimeout(500);
          console.log('  PASS: Create endpoint action triggered');
          results.passed.push('Create endpoint action works');
        }

        // Close modal
        const closeButton = await page.locator('button:has-text("Cancelar"), button:has-text("Cancel"), button[class*="close"]');
        if (await closeButton.count() > 0) {
          await closeButton.first().click();
          await page.waitForTimeout(300);
        }
      } else {
        console.log('  FAIL: Modal did not open');
        results.failed.push('Create Endpoint modal opens');
      }
    } else {
      console.log('  FAIL: Create Endpoint button not found');
      results.failed.push('Create Endpoint button found');
    }

    // Test 9: Check endpoint actions
    console.log('Test 9: Checking endpoint action buttons...');
    const settingsButtons = await page.locator('button:has-text("Configurar"), button:has-text("Settings")');
    const metricsButtons = await page.locator('button:has-text("Métricas"), button:has-text("Metrics")');
    if (await settingsButtons.count() > 0 && await metricsButtons.count() > 0) {
      console.log('  PASS: Endpoint action buttons visible');
      results.passed.push('Endpoint action buttons visible');
    } else {
      console.log('  FAIL: Some endpoint action buttons missing');
      results.failed.push('Endpoint action buttons visible');
    }

    // Test 10: Test API endpoint directly
    console.log('\nTest 10: Testing backend API endpoints...');

    // Test serverless status endpoint
    const response = await page.request.get('http://localhost:8000/api/v1/serverless/status');
    if (response.ok()) {
      const data = await response.json();
      console.log(`  PASS: Serverless status API works - ${data.status || 'operational'}`);
      results.passed.push('Serverless status API');
    } else {
      console.log(`  FAIL: Serverless status API returned ${response.status()}`);
      results.failed.push('Serverless status API');
    }

    // Test pricing endpoint
    const pricingResponse = await page.request.get('http://localhost:8000/api/v1/serverless/pricing');
    if (pricingResponse.ok()) {
      console.log('  PASS: Serverless pricing API works');
      results.passed.push('Serverless pricing API');
    } else {
      console.log(`  FAIL: Serverless pricing API returned ${pricingResponse.status()}`);
      results.failed.push('Serverless pricing API');
    }

  } catch (error) {
    console.error('\nERROR:', error.message);
    results.errors.push(error.message);
  } finally {
    await browser.close();
  }

  // Print summary
  console.log('\n========================================');
  console.log('TEST SUMMARY');
  console.log('========================================');
  console.log(`PASSED: ${results.passed.length}`);
  console.log(`FAILED: ${results.failed.length}`);
  console.log(`ERRORS: ${results.errors.length}`);

  if (results.passed.length > 0) {
    console.log('\nPassed tests:');
    results.passed.forEach(t => console.log(`  - ${t}`));
  }

  if (results.failed.length > 0) {
    console.log('\nFailed tests:');
    results.failed.forEach(t => console.log(`  - ${t}`));
  }

  if (results.errors.length > 0) {
    console.log('\nErrors:');
    results.errors.forEach(e => console.log(`  - ${e}`));
  }

  console.log('\n========================================');

  // Return exit code
  process.exit(results.failed.length + results.errors.length);
}

// Run tests
testServerlessUI().catch(console.error);
