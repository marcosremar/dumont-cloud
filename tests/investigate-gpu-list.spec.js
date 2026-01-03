const { test, expect } = require('@playwright/test');

test.describe('GPU List Investigation', () => {
  test('navigate to app and investigate GPU list issue', async ({ page }) => {
    // Set up listeners BEFORE navigation
    const consoleMessages = [];
    const pageErrors = [];
    const apiRequests = [];
    const apiResponses = [];

    page.on('console', msg => {
      const text = msg.text();
      consoleMessages.push({ type: msg.type(), text });
      console.log(`[CONSOLE ${msg.type().toUpperCase()}] ${text}`);
    });

    page.on('pageerror', error => {
      pageErrors.push(error.message);
      console.log(`[PAGE ERROR] ${error.message}`);
    });

    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/v1/instances/offers')) {
        const req = {
          url,
          method: request.method(),
          headers: request.headers()
        };
        apiRequests.push(req);
        console.log(`[API REQUEST] ${request.method()} ${url}`);
      }
    });

    page.on('response', async response => {
      const url = response.url();
      if (url.includes('/api/v1/instances/offers')) {
        const status = response.status();
        console.log(`[API RESPONSE] ${status} ${url}`);
        try {
          const body = await response.text();
          console.log(`[RESPONSE BODY] ${body}`);
          apiResponses.push({ status, url, body });
        } catch (e) {
          console.log(`[ERROR] Could not read response body: ${e.message}`);
        }
      }
    });

    // Navigate to the application
    console.log('\n=== NAVIGATING TO http://localhost:4892/app ===\n');
    await page.goto('http://localhost:4892/app');
    await page.waitForLoadState('domcontentloaded');

    console.log(`\n=== PAGE LOADED ===`);
    console.log(`Title: ${await page.title()}`);
    console.log(`URL: ${page.url()}\n`);

    // Wait for React to render
    await page.waitForTimeout(1000);

    // Check what's on the page
    const bodyText = await page.locator('body').innerText();
    console.log(`\n=== PAGE CONTENT (first 800 chars) ===\n${bodyText.substring(0, 800)}\n`);

    // Look for wizard steps
    const stepHeaders = await page.locator('h2, h3, [class*="step"], [class*="wizard"]').allTextContents();
    console.log(`\n=== FOUND HEADERS/STEPS ===\n${stepHeaders.join('\n')}\n`);

    // Check if we need to navigate to step 2
    console.log('\n=== ATTEMPTING TO NAVIGATE TO STEP 2 ===\n');

    // First, check if we're on step 1
    const step1Visible = await page.locator('text=/Localização|Location|Região/i').isVisible({ timeout: 2000 }).catch(() => false);
    console.log(`Step 1 (Location) visible: ${step1Visible}`);

    if (step1Visible) {
      // Try to select a location first
      const locationButtons = page.locator('button:has-text("Estados Unidos"), button:has-text("United States"), button:has-text("US")');
      const locationCount = await locationButtons.count();
      console.log(`Found ${locationCount} location buttons`);

      if (locationCount > 0) {
        await locationButtons.first().click();
        console.log('Clicked location button');
        await page.waitForTimeout(500);
      }

      // Now try to click Next
      const nextButton = page.locator('button:has-text("Próximo"), button:has-text("Next"), button:has-text("Avançar")').first();
      if (await nextButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('Clicking Next button to go to step 2');
        await nextButton.click();
        await page.waitForTimeout(1000);
      }
    }

    // Check if we're on step 2 now
    const step2Visible = await page.locator('text=/Hardware|GPU|Tier|Camada/i').isVisible({ timeout: 2000 }).catch(() => false);
    console.log(`\nStep 2 (Hardware) visible: ${step2Visible}`);

    if (step2Visible) {
      console.log('\n=== ON STEP 2 - LOOKING FOR TIER SELECTION ===\n');

      // Look for tier buttons
      const tierButtons = page.locator('button:has-text("Básico"), button:has-text("Profissional"), button:has-text("Starter")');
      const tierCount = await tierButtons.count();
      console.log(`Found ${tierCount} tier buttons`);

      // List all tier buttons
      for (let i = 0; i < tierCount; i++) {
        const text = await tierButtons.nth(i).innerText();
        console.log(`  Tier ${i}: ${text}`);
      }

      // Select the first tier to trigger the API call
      if (tierCount > 0) {
        console.log('\n=== CLICKING FIRST TIER BUTTON ===\n');
        await tierButtons.first().click();
        await page.waitForTimeout(2000);

        console.log('\n=== CHECKING FOR GPU OFFERS ===\n');

        // Check for loading indicators
        const loadingVisible = await page.locator('[class*="loading"], [class*="spinner"]').isVisible({ timeout: 1000 }).catch(() => false);
        console.log(`Loading indicator visible: ${loadingVisible}`);

        // Check for offer cards or GPU list
        const offerCards = page.locator('[class*="offer"], [class*="machine"], [class*="gpu"]');
        const offerCount = await offerCards.count();
        console.log(`Found ${offerCount} offer/machine/gpu elements`);

        // Check for error messages
        const errorMsg = page.locator('[class*="error"], [class*="alert"]');
        const errorCount = await errorMsg.count();
        console.log(`Found ${errorCount} error/alert elements`);
        if (errorCount > 0) {
          const errorText = await errorMsg.first().innerText();
          console.log(`Error message: ${errorText}`);
        }
      }
    }

    console.log(`\n=== API REQUESTS SUMMARY ===`);
    console.log(`Total API requests to /api/v1/instances/offers: ${apiRequests.length}`);
    console.log(`Total API responses: ${apiResponses.length}`);

    console.log(`\n=== CONSOLE ERRORS ===`);
    const errors = consoleMessages.filter(m => m.type === 'error');
    console.log(`Total console errors: ${errors.length}`);
    errors.forEach(err => console.log(`  - ${err.text}`));

    console.log(`\n=== PAGE ERRORS ===`);
    console.log(`Total page errors: ${pageErrors.length}`);
    pageErrors.forEach(err => console.log(`  - ${err}`));

    // Keep browser open for debugging
    console.log('\n=== PAUSING FOR INSPECTION ===\n');
    await page.pause();
  });
});
