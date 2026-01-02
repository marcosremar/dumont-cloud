const { test, expect } = require('@playwright/test');

test('Debug Wizard - Capture HTML Structure', async ({ page }) => {
  console.log('\n========================================');
  console.log('Navigate and capture HTML structure');
  console.log('========================================');

  await page.goto('http://localhost:4893/login?auto_login=demo');
  await page.waitForTimeout(2000);
  await page.waitForURL('**/app**', { timeout: 10000 });

  console.log('✓ On /app page');
  await page.waitForTimeout(2000);

  // Get the main content HTML
  const mainHTML = await page.locator('main').innerHTML();
  console.log('\n=== MAIN HTML (first 2000 chars) ===');
  console.log(mainHTML.substring(0, 2000));

  // Look for any element with "Brasil" text
  console.log('\n=== Elements containing "Brasil" ===');
  const brasilElements = page.locator('*:has-text("Brasil")');
  const brasilCount = await brasilElements.count();
  console.log(`Found ${brasilCount} elements with "Brasil" text`);

  for (let i = 0; i < Math.min(brasilCount, 5); i++) {
    const element = brasilElements.nth(i);
    const tagName = await element.evaluate(el => el.tagName);
    const className = await element.getAttribute('class').catch(() => 'N/A');
    const role = await element.getAttribute('role').catch(() => 'N/A');
    const outerHTML = await element.evaluate(el => el.outerHTML.substring(0, 300));

    console.log(`\nElement ${i + 1}:`);
    console.log(`  Tag: ${tagName}`);
    console.log(`  Class: ${className}`);
    console.log(`  Role: ${role}`);
    console.log(`  HTML: ${outerHTML}`);
  }

  // Look for clickable elements in the wizard
  console.log('\n=== Clickable elements (buttons, divs with role=button) ===');
  const clickables = page.locator('button, [role="button"], [onclick]');
  const clickableCount = await clickables.count();
  console.log(`Found ${clickableCount} clickable elements`);

  // Get text of first 20 clickable elements
  for (let i = 0; i < Math.min(clickableCount, 20); i++) {
    const element = clickables.nth(i);
    const text = await element.textContent().catch(() => '');
    const className = await element.getAttribute('class').catch(() => 'N/A');

    if (text.trim()) {
      console.log(`  [${i}] "${text.trim()}" (class: ${className})`);
    }
  }

  // Check for wizard-specific elements
  console.log('\n=== Elements with "região" or "region" (case insensitive) ===');
  const regionElements = page.locator('*').filter({ hasText: /região|region/i });
  const regionCount = await regionElements.count();
  console.log(`Found ${regionCount} elements`);

  for (let i = 0; i < Math.min(regionCount, 10); i++) {
    const element = regionElements.nth(i);
    const text = await element.textContent().catch(() => '');
    console.log(`  [${i}] "${text.trim().substring(0, 100)}"`);
  }

  // Try to find the region selection container
  console.log('\n=== Looking for wizard step container ===');
  const wizardContainer = page.locator('[class*="wizard"], [class*="step"], [class*="form"]');
  const containerCount = await wizardContainer.count();
  console.log(`Found ${containerCount} potential wizard containers`);

  // Take final screenshot
  await page.screenshot({ path: 'test-results/debug-html-structure.png', fullPage: true });
  console.log('\nScreenshot saved: test-results/debug-html-structure.png');
});
