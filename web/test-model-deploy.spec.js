const { test, expect } = require('@playwright/test');

test.describe('Model Deploy Tests', () => {
  test('should navigate to models page and test deploy functionality', async ({ page }) => {
    const consoleMessages = [];
    const networkRequests = [];
    const failedRequests = [];

    // Capture console messages
    page.on('console', msg => {
      const msgText = msg.text();
      const type = msg.type();
      consoleMessages.push({ type, text: msgText });
      console.log(`[CONSOLE ${type.toUpperCase()}] ${msgText}`);
    });

    // Capture network requests
    page.on('request', request => {
      const url = request.url();
      const method = request.method();
      networkRequests.push({ method, url, timestamp: Date.now() });
      console.log(`[REQUEST] ${method} ${url}`);
    });

    // Capture failed requests
    page.on('requestfailed', request => {
      const url = request.url();
      const failure = request.failure();
      failedRequests.push({ url, failure });
      console.log(`[REQUEST FAILED] ${url} - ${failure ? failure.errorText : 'unknown'}`);
    });

    // Capture responses
    page.on('response', async response => {
      const url = response.url();
      const status = response.status();

      if (url.includes('/api/')) {
        console.log(`[RESPONSE] ${status} ${url}`);

        if (status >= 400) {
          try {
            const body = await response.text();
            console.log(`[RESPONSE ERROR BODY] ${body}`);
          } catch (e) {
            console.log(`[RESPONSE ERROR] Could not read body: ${e.message}`);
          }
        }
      }
    });

    console.log('\n=== STEP 1: Navigate to localhost and enable demo mode ===');
    await page.goto('http://localhost:4892');

    // Enable demo mode
    await page.evaluate(() => {
      localStorage.setItem('demo_mode', 'true');
    });
    console.log('✓ Demo mode enabled');

    await page.waitForTimeout(1000);

    console.log('\n=== STEP 2: Login (demo mode) ===');
    // Check if already logged in or need to login
    let currentUrl = page.url();
    if (currentUrl.includes('/login')) {
      console.log('On login page, attempting auto-login...');
      await page.goto('http://localhost:4892/login?auto_login=demo');
      await page.waitForTimeout(2000);
    }

    console.log('\n=== STEP 3: Navigate to /app/models ===');
    await page.goto('http://localhost:4892/app/models');
    await page.waitForTimeout(2000);

  // Take screenshot
  await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/test-models-page.png', fullPage: true });
  console.log('Screenshot saved: test-models-page.png');

  console.log('\n=== STEP 4: Verify page loads correctly ===');
  const modelsPageUrl = page.url();
  console.log('Current URL:', modelsPageUrl);

  // Check if we're on the models page
  if (!modelsPageUrl.includes('/app/models')) {
    console.log('✗ Not on models page');
  } else {
    console.log('✓ On models page');
  }

  // Check for welcome modal and skip if present
  const welcomeModal = page.locator('text=/Bem-vindo|Welcome|Pular tudo/i');
  if (await welcomeModal.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log('Found welcome modal, checking for skip button...');
    const skipButton = page.locator('button:has-text("Pular tudo")');
    if (await skipButton.isVisible({ timeout: 1000 }).catch(() => false)) {
      await skipButton.click();
      console.log('✓ Clicked "Pular tudo" button');
      await page.waitForTimeout(500);
    }
  }

  console.log('\n=== STEP 5: Look for Deploy Model button (Rocket icon) ===');

  // Try different selectors for the deploy button
  const deployButtonSelectors = [
    'button:has-text(/Deploy Model/i)',
    'button:has-text(/Deploy/i)',
    '[aria-label*="Deploy"]',
    '[title*="Deploy"]',
    'button:has([data-icon="rocket"])',
    'button svg[data-icon="rocket"]',
    'button:has(.lucide-rocket)',
  ];

  let deployButton = null;
  for (const selector of deployButtonSelectors) {
    try {
      const btn = page.locator(selector).first();
      if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
        deployButton = btn;
        console.log(`✓ Found deploy button with selector: ${selector}`);
        break;
      }
    } catch (e) {
      // Continue to next selector
    }
  }

  if (!deployButton) {
    console.log('✗ Deploy button not found, checking page content...');
    const pageContent = await page.content();
    console.log('Page has buttons:', await page.locator('button').count());

    // Take a screenshot for debugging
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/test-no-deploy-button.png', fullPage: true });
    console.log('Screenshot saved: test-no-deploy-button.png');
  } else {
    console.log('\n=== STEP 6: Click Deploy Model button ===');
    await deployButton.click();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/test-deploy-wizard-opened.png', fullPage: true });
    console.log('Screenshot saved: test-deploy-wizard-opened.png');

    console.log('\n=== STEP 7: Navigate through wizard steps ===');

    // Step 1: Select model type or category
    console.log('Looking for model selection...');

    // Try to find LLM models
    const llmModels = page.locator('text=/meta-llama|Llama|GPT|Model/i');
    const modelCount = await llmModels.count();
    console.log(`Found ${modelCount} model-related elements`);

    // Look for specific model: meta-llama/Llama-3.2-3B-Instruct
    const targetModel = page.locator('text=/Llama-3.2-3B-Instruct/i').first();
    if (await targetModel.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('✓ Found target model: Llama-3.2-3B-Instruct');
      await targetModel.click();
      await page.waitForTimeout(1000);

      await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/test-model-selected.png', fullPage: true });
      console.log('Screenshot saved: test-model-selected.png');
    } else {
      console.log('✗ Target model not found, looking for any model...');

      // Try to click any model button/card
      const modelButtons = page.locator('button:has-text(/Model/i), [role="button"]:has-text(/llama|gpt/i)');
      const btnCount = await modelButtons.count();
      if (btnCount > 0) {
        await modelButtons.first().click();
        console.log('Clicked first available model');
        await page.waitForTimeout(1000);
      }
    }

    // Look for "Next" or "Continue" button to proceed to next step
    console.log('\n=== STEP 8: Navigate wizard steps ===');

    const nextButtonSelectors = [
      'button:has-text(/Next/i)',
      'button:has-text(/Próximo/i)',
      'button:has-text(/Continue/i)',
      'button:has-text(/Continuar/i)',
    ];

    for (let step = 1; step <= 4; step++) {
      console.log(`\nAttempting wizard step ${step}...`);

      let nextButton = null;
      for (const selector of nextButtonSelectors) {
        const btn = page.locator(selector).first();
        if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
          nextButton = btn;
          break;
        }
      }

      if (nextButton) {
        await nextButton.click();
        console.log(`✓ Clicked next button for step ${step}`);
        await page.waitForTimeout(1500);

        await page.screenshot({
          path: `/Users/marcos/CascadeProjects/dumontcloud/web/test-wizard-step-${step}.png`,
          fullPage: true
        });
        console.log(`Screenshot saved: test-wizard-step-${step}.png`);
      } else {
        console.log(`No next button found at step ${step}`);
        break;
      }
    }

    console.log('\n=== STEP 9: Configure GPU and Deploy ===');

    // Look for GPU selection
    const gpuSelectors = page.locator('text=/GPU|gpu|Graphics/i');
    const gpuCount = await gpuSelectors.count();
    console.log(`Found ${gpuCount} GPU-related elements`);

    // Look for deploy/submit button
    const deployFinalSelectors = [
      'button:has-text(/Deploy/i)',
      'button:has-text(/Create/i)',
      'button:has-text(/Criar/i)',
      'button:has-text(/Submit/i)',
      'button[type="submit"]',
    ];

    let deployFinalButton = null;
    for (const selector of deployFinalSelectors) {
      const btn = page.locator(selector).first();
      if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
        deployFinalButton = btn;
        console.log(`✓ Found deploy button with selector: ${selector}`);
        break;
      }
    }

    if (deployFinalButton) {
      console.log('Clicking final deploy button...');
      await deployFinalButton.click();
      await page.waitForTimeout(2000);

      await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/test-deploy-submitted.png', fullPage: true });
      console.log('Screenshot saved: test-deploy-submitted.png');
    } else {
      console.log('✗ Final deploy button not found');
    }
  }

  console.log('\n=== FINAL SCREENSHOT ===');
  await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/test-final.png', fullPage: true });
  console.log('Screenshot saved: test-final.png');

  console.log('\n=== SUMMARY ===');
  console.log(`Total console messages: ${consoleMessages.length}`);
  console.log(`Total network requests: ${networkRequests.length}`);
  console.log(`Total failed requests: ${failedRequests.length}`);

  // Filter API requests
  const apiRequests = networkRequests.filter(r => r.url.includes('/api/'));
  console.log(`\nAPI Requests (${apiRequests.length}):`);
  apiRequests.forEach(req => {
    console.log(`  ${req.method} ${req.url}`);
  });

  // Show errors
  const errors = consoleMessages.filter(m => m.type === 'error');
  console.log(`\nConsole Errors (${errors.length}):`);
  errors.forEach(err => {
    console.log(`  ${err.text}`);
  });

  console.log(`\nFailed Requests (${failedRequests.length}):`);
  failedRequests.forEach(req => {
    console.log(`  ${req.url} - ${req.failure ? req.failure.errorText : 'unknown'}`);
  });

    // Wait a bit more to capture any delayed requests
    await page.waitForTimeout(2000);
  });
});
