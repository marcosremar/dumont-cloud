const { test, expect } = require('@playwright/test');

test('Debug Wizard on Port 4893 - Capture Network and Console', async ({ page }) => {
  const consoleMessages = [];
  const networkRequests = [];
  const failedRequests = [];
  const apiResponses = [];

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

    if (url.includes('/api/')) {
      console.log(`[REQUEST] ${method} ${url}`);
    }
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

      try {
        const contentType = response.headers()['content-type'] || '';
        let body = null;

        if (contentType.includes('application/json')) {
          body = await response.json();
        } else {
          body = await response.text();
        }

        apiResponses.push({
          url,
          status,
          body,
          success: status >= 200 && status < 300
        });

        if (status >= 400) {
          console.log(`[RESPONSE ERROR BODY] ${JSON.stringify(body, null, 2)}`);
        } else if (url.includes('/offers')) {
          console.log(`[OFFERS RESPONSE] ${JSON.stringify(body, null, 2)}`);
        }
      } catch (e) {
        console.log(`[RESPONSE ERROR] Could not parse body: ${e.message}`);
      }
    }
  });

  console.log('\n========================================');
  console.log('STEP 1: Navigate to login with auto_login');
  console.log('========================================');
  await page.goto('http://localhost:4893/login?auto_login=demo');
  await page.waitForTimeout(2000);

  console.log('\n========================================');
  console.log('STEP 2: Wait for redirect to /app');
  console.log('========================================');
  try {
    await page.waitForURL('**/app**', { timeout: 10000 });
    console.log('✓ Successfully redirected to /app');
  } catch (e) {
    console.log('✗ Failed to redirect to /app:', e.message);
    console.log('Current URL:', page.url());
  }

  await page.waitForTimeout(1000);

  console.log('\n========================================');
  console.log('STEP 3: Look for wizard or create machine button');
  console.log('========================================');
  const currentUrl = page.url();
  console.log('Current URL:', currentUrl);

  // Take screenshot
  await page.screenshot({ path: 'test-results/debug-4893-step3.png', fullPage: true });
  console.log('Screenshot saved: test-results/debug-4893-step3.png');

  // Check if welcome modal is present
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

  // Look for create machine or wizard
  const createButton = page.locator('button:has-text(/Criar Máquina|Create Machine/i)');
  if (await createButton.isVisible({ timeout: 3000 }).catch(() => false)) {
    console.log('✓ Found "Criar Máquina" button');
    await createButton.click();
    console.log('Clicked create machine button');
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'test-results/debug-4893-wizard-opened.png', fullPage: true });
    console.log('Screenshot saved: test-results/debug-4893-wizard-opened.png');
  } else {
    console.log('✗ "Criar Máquina" button not found');
  }

  console.log('\n========================================');
  console.log('STEP 4: Try to navigate wizard - Select Region');
  console.log('========================================');

  // Look for region selection - wizard might already be open
  const regionButtons = await page.locator('button').filter({ hasText: 'Brasil' }).count();
  console.log(`Found ${regionButtons} buttons with "Brasil" text`);

  // Try to find and click Brasil button
  const brasilButton = page.locator('button').filter({ hasText: 'Brasil' }).first();
  if (await brasilButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log('✓ Found "Brasil" button');
    console.log('Clicking "Brasil" region...');
    await brasilButton.click();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'test-results/debug-4893-region-selected.png', fullPage: true });
    console.log('Screenshot saved: test-results/debug-4893-region-selected.png');
  } else {
    console.log('✗ Could not find "Brasil" button');
  }

  console.log('\n========================================');
  console.log('STEP 5: Look for next step - Tier/Hardware selection');
  console.log('========================================');

  await page.waitForTimeout(1000);

  // Look for tier buttons
  const desenvolverButton = page.locator('button').filter({ hasText: 'Desenvolver' }).first();
  const producaoButton = page.locator('button').filter({ hasText: 'Produção' }).first();
  const treinarButton = page.locator('button').filter({ hasText: 'Treinar' }).first();

  const desenvolverVisible = await desenvolverButton.isVisible({ timeout: 2000 }).catch(() => false);
  const producaoVisible = await producaoButton.isVisible({ timeout: 2000 }).catch(() => false);
  const treinarVisible = await treinarButton.isVisible({ timeout: 2000 }).catch(() => false);

  console.log(`Tier buttons visible: Desenvolver=${desenvolverVisible}, Produção=${producaoVisible}, Treinar=${treinarVisible}`);

  if (desenvolverVisible) {
    console.log('Clicking "Desenvolver" tier...');
    await desenvolverButton.click();
    console.log('Waiting for API calls...');
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'test-results/debug-4893-tier-selected.png', fullPage: true });
    console.log('Screenshot saved: test-results/debug-4893-tier-selected.png');
  } else {
    console.log('✗ Tier buttons not visible - might still be on step 1');

    // Take screenshot to see current state
    await page.screenshot({ path: 'test-results/debug-4893-after-region-click.png', fullPage: true });
    console.log('Screenshot saved: test-results/debug-4893-after-region-click.png');
  }

  console.log('\n========================================');
  console.log('STEP 6: Watch for API calls to /api/v1/instances/offers');
  console.log('========================================');
  await page.waitForTimeout(2000);

  console.log('\n========================================');
  console.log('FINAL SCREENSHOT');
  console.log('========================================');
  await page.screenshot({ path: 'test-results/debug-4893-final.png', fullPage: true });
  console.log('Screenshot saved: test-results/debug-4893-final.png');

  // Wait a bit more to capture any delayed requests
  await page.waitForTimeout(2000);

  console.log('\n========================================');
  console.log('SUMMARY REPORT');
  console.log('========================================');
  console.log(`Total console messages: ${consoleMessages.length}`);
  console.log(`Total network requests: ${networkRequests.length}`);
  console.log(`Total failed requests: ${failedRequests.length}`);

  // Filter API requests
  const apiRequests = networkRequests.filter(r => r.url.includes('/api/'));
  console.log(`\n--- API Requests (${apiRequests.length}) ---`);
  apiRequests.forEach(req => {
    console.log(`  ${req.method} ${req.url}`);
  });

  // Show API responses with details
  console.log(`\n--- API Responses (${apiResponses.length}) ---`);
  apiResponses.forEach(res => {
    console.log(`\n  ${res.status} ${res.url}`);
    console.log(`  Success: ${res.success}`);
    if (res.body) {
      const bodyStr = typeof res.body === 'string' ? res.body : JSON.stringify(res.body, null, 2);
      console.log(`  Body: ${bodyStr.substring(0, 500)}${bodyStr.length > 500 ? '...' : ''}`);
    }
  });

  // Show errors
  const errors = consoleMessages.filter(m => m.type === 'error');
  console.log(`\n--- Console Errors (${errors.length}) ---`);
  errors.forEach(err => {
    console.log(`  ${err.text}`);
  });

  // Show warnings
  const warnings = consoleMessages.filter(m => m.type === 'warning');
  console.log(`\n--- Console Warnings (${warnings.length}) ---`);
  warnings.forEach(warn => {
    console.log(`  ${warn.text}`);
  });

  console.log(`\n--- Failed Requests (${failedRequests.length}) ---`);
  failedRequests.forEach(req => {
    console.log(`  ${req.url} - ${req.failure ? req.failure.errorText : 'unknown'}`);
  });

  // Check specifically for /offers endpoint
  const offersRequest = apiRequests.find(r => r.url.includes('/offers'));
  const offersResponse = apiResponses.find(r => r.url.includes('/offers'));

  console.log('\n========================================');
  console.log('CRITICAL CHECK: /offers endpoint');
  console.log('========================================');
  if (offersRequest) {
    console.log('✓ /offers request was made');
    console.log(`  ${offersRequest.method} ${offersRequest.url}`);
  } else {
    console.log('✗ /offers request was NOT made');
  }

  if (offersResponse) {
    console.log('✓ /offers response received');
    console.log(`  Status: ${offersResponse.status}`);
    console.log(`  Success: ${offersResponse.success}`);
    console.log(`  Body: ${JSON.stringify(offersResponse.body, null, 2)}`);
  } else {
    console.log('✗ /offers response was NOT received');
  }

  console.log('\n========================================');
  console.log('END OF DEBUG REPORT');
  console.log('========================================');
});
