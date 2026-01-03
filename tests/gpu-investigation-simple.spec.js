const { test, expect } = require('@playwright/test');

test('Investigate GPU List - Port 4892', async ({ page }) => {
  const consoleMessages = [];
  const apiCalls = [];

  // Capture console
  page.on('console', msg => {
    const text = msg.text();
    const type = msg.type();
    consoleMessages.push({ type, text });
    console.log(`[CONSOLE ${type.toUpperCase()}] ${text}`);
  });

  // Capture page errors
  page.on('pageerror', error => {
    console.log(`[PAGE ERROR] ${error.message}`);
  });

  // Capture API requests
  page.on('request', request => {
    const url = request.url();
    if (url.includes('/api/')) {
      console.log(`[REQUEST] ${request.method()} ${url}`);
      apiCalls.push({ method: request.method(), url, type: 'request' });
    }
  });

  // Capture API responses
  page.on('response', async response => {
    const url = response.url();
    if (url.includes('/api/')) {
      const status = response.status();
      console.log(`[RESPONSE] ${status} ${url}`);

      if (url.includes('/api/v1/instances/offers')) {
        try {
          const body = await response.text();
          console.log(`[OFFERS API RESPONSE BODY]\n${body}\n`);
          apiCalls.push({ method: 'response', url, status, body, type: 'response' });
        } catch (e) {
          console.log(`[ERROR] Could not read response: ${e.message}`);
        }
      }
    }
  });

  console.log('\n=== NAVIGATING TO http://localhost:4892/app ===\n');
  await page.goto('http://localhost:4892/app');
  await page.waitForLoadState('domcontentloaded');

  console.log(`Page Title: ${await page.title()}`);
  console.log(`Current URL: ${page.url()}\n`);

  // Wait for React to render
  await page.waitForTimeout(2000);

  // Take initial screenshot
  await page.screenshot({
    path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshot-step1.png',
    fullPage: true
  });
  console.log('Screenshot saved: screenshot-step1.png\n');

  // Check current state
  const bodyText = await page.locator('body').innerText();
  console.log(`=== PAGE CONTENT (first 600 chars) ===\n${bodyText.substring(0, 600)}\n`);

  // Try to navigate to step 2
  console.log('=== ATTEMPTING TO NAVIGATE TO STEP 2 ===\n');

  // Check if we're on step 1
  const step1Text = await page.locator('h2, h3').allTextContents();
  console.log(`Headers found: ${step1Text.join(', ')}\n`);

  // Look for location/region selection (Step 1)
  const locationArea = page.locator('text=/Localização|Location|Selecione.*região/i');
  if (await locationArea.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log('Step 1 (Location) is visible');

    // Try clicking a location
    const usButton = page.locator('button:has-text("Estados Unidos")').or(page.locator('button:has-text("United States")')).first();
    if (await usButton.isVisible({ timeout: 1000 }).catch(() => false)) {
      await usButton.click();
      console.log('Clicked US/Estados Unidos button');
      await page.waitForTimeout(500);
    }

    // Click Next
    const nextBtn = page.locator('button:has-text("Próximo")').or(page.locator('button:has-text("Next")')).first();
    if (await nextBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await nextBtn.click();
      console.log('Clicked Next button');
      await page.waitForTimeout(1500);
    }
  }

  // Take screenshot after navigation
  await page.screenshot({
    path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshot-step2.png',
    fullPage: true
  });
  console.log('Screenshot saved: screenshot-step2.png\n');

  // Check if we're on step 2
  const step2Content = await page.locator('body').innerText();
  console.log(`=== STEP 2 CONTENT (first 800 chars) ===\n${step2Content.substring(0, 800)}\n`);

  // Look for tier selection
  const tierButtons = await page.locator('button').allTextContents();
  console.log(`All buttons found:\n${tierButtons.join('\n')}\n`);

  // Try to select a tier
  const starterTier = page.locator('button:has-text("Starter")').or(
    page.locator('button:has-text("Básico")')
  ).or(
    page.locator('button:has-text("Profissional")')
  ).first();

  if (await starterTier.isVisible({ timeout: 2000 }).catch(() => false)) {
    const tierText = await starterTier.innerText();
    console.log(`=== SELECTING TIER: ${tierText} ===\n`);
    await starterTier.click();
    await page.waitForTimeout(3000); // Wait for API call

    // Take screenshot after tier selection
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshot-tier-selected.png',
      fullPage: true
    });
    console.log('Screenshot saved: screenshot-tier-selected.png\n');

    // Check for GPU offers
    const afterTierContent = await page.locator('body').innerText();
    console.log(`=== CONTENT AFTER TIER SELECTION ===\n${afterTierContent}\n`);

    // Look for machine cards
    const machineCards = page.locator('[class*="machine"], [class*="offer"], [class*="card"]');
    const cardCount = await machineCards.count();
    console.log(`Found ${cardCount} machine/offer cards\n`);

    // Check for "Mais econômico" or similar labels
    const hasOffers = await page.locator('text=/Mais econômico|Most economical|Melhor custo/i').isVisible({ timeout: 1000 }).catch(() => false);
    console.log(`GPU offers visible: ${hasOffers}\n`);

    // Check for error or empty state
    const errorOrEmpty = await page.locator('text=/erro|error|não.*encontr|no.*found|vazio|empty/i').isVisible({ timeout: 1000 }).catch(() => false);
    console.log(`Error/empty state visible: ${errorOrEmpty}\n`);
  } else {
    console.log('Tier button not found!\n');
  }

  // Summary
  console.log('\n=== SUMMARY ===');
  console.log(`Total API calls: ${apiCalls.filter(c => c.type === 'request').length}`);
  console.log(`API calls to /api/v1/instances/offers: ${apiCalls.filter(c => c.url.includes('/api/v1/instances/offers')).length}`);

  const errors = consoleMessages.filter(m => m.type === 'error');
  console.log(`Console errors: ${errors.length}`);
  if (errors.length > 0) {
    console.log('\nErrors:');
    errors.forEach(e => console.log(`  - ${e.text}`));
  }

  console.log('\n=== PAUSING FOR INSPECTION ===');
  console.log('Use Playwright Inspector to examine the page state.\n');

  await page.pause();
});
