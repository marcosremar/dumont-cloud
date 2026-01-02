const { test, expect } = require('@playwright/test');

test('Debug Wizard - Capture Network and Console', async ({ page }) => {
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

  console.log('\n=== STEP 1: Navigate to login with auto_login ===');
  await page.goto('http://localhost:4893/login?auto_login=demo');
  await page.waitForTimeout(2000);

  console.log('\n=== STEP 2: Wait for redirect to /app ===');
  try {
    await page.waitForURL('**/app**', { timeout: 10000 });
    console.log('✓ Successfully redirected to /app');
  } catch (e) {
    console.log('✗ Failed to redirect to /app:', e.message);
    console.log('Current URL:', page.url());
  }

  await page.waitForTimeout(1000);

  console.log('\n=== STEP 3: Look for wizard or create machine button ===');
  const currentUrl = page.url();
  console.log('Current URL:', currentUrl);

  // Take screenshot
  await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/debug-step3.png', fullPage: true });
  console.log('Screenshot saved: debug-step3.png');

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

    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/debug-wizard-opened.png', fullPage: true });
    console.log('Screenshot saved: debug-wizard-opened.png');
  } else {
    console.log('✗ "Criar Máquina" button not found');
  }

  console.log('\n=== STEP 4: Try to navigate wizard - Select Region ===');

  // Look for region selection (Step 1)
  const regionButtons = await page.locator('button:has-text(/Brasil|US|Europa|North America/i)').count();
  console.log(`Found ${regionButtons} region buttons`);

  if (regionButtons > 0) {
    const brasilButton = page.locator('button:has-text("Brasil")').first();
    if (await brasilButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('Clicking "Brasil" region...');
      await brasilButton.click();
      await page.waitForTimeout(1000);

      await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/debug-region-selected.png', fullPage: true });
      console.log('Screenshot saved: debug-region-selected.png');
    }
  }

  console.log('\n=== STEP 5: Select a tier (e.g., "Desenvolver") ===');

  // Look for tier selection (Step 2)
  const tierButtons = await page.locator('button:has-text(/Desenvolver|Produção|Treinar|Develop/i)').count();
  console.log(`Found ${tierButtons} tier buttons`);

  if (tierButtons > 0) {
    const desenvolverButton = page.locator('button:has-text(/Desenvolver/i)').first();
    if (await desenvolverButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('Clicking "Desenvolver" tier...');
      await desenvolverButton.click();
      await page.waitForTimeout(2000);

      await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/debug-tier-selected.png', fullPage: true });
      console.log('Screenshot saved: debug-tier-selected.png');
    }
  }

  console.log('\n=== STEP 6: Watch for API calls to /api/v1/instances/offers ===');
  await page.waitForTimeout(2000);

  console.log('\n=== FINAL SCREENSHOT ===');
  await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/debug-final.png', fullPage: true });
  console.log('Screenshot saved: debug-final.png');

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
  await page.waitForTimeout(3000);
});
