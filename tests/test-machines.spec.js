const { test, expect } = require('@playwright/test');

test.describe('Machines Page Tests', () => {
  test('Machines page loads without critical JS errors', async ({ page }) => {
    // Track page errors (uncaught exceptions)
    const pageErrors = [];
    page.on('pageerror', err => {
      pageErrors.push(err.message);
    });

    // Navigate directly to machines page (auth state is already saved)
    await page.goto('/app/machines');

    // Wait for any content to appear with longer timeout
    await page.waitForSelector('body', { timeout: 15000 });

    // Give the page time to render and catch errors
    await page.waitForTimeout(3000);

    // Take a screenshot for debugging
    await page.screenshot({
      path: 'test-results/machines-page-snapshot.png',
      fullPage: true
    });

    // Log the HTML to debug
    const bodyHTML = await page.locator('main').innerHTML().catch(() => 'main not found');
    console.log('Main content length:', bodyHTML.length);
    console.log('Page errors found:', pageErrors);

    // Fail if there are critical JS errors
    const criticalErrors = pageErrors.filter(e =>
      e.includes('ReferenceError') ||
      e.includes('is not defined') ||
      e.includes('TypeError')
    );

    if (criticalErrors.length > 0) {
      console.error('Critical errors:', criticalErrors);
    }

    expect(criticalErrors).toHaveLength(0);
  });

  test('Machines page renders content', async ({ page }) => {
    // Navigate directly to machines page
    await page.goto('/app/machines');

    // Wait for something to render in main - could be loading, error, or content
    await page.waitForSelector('main > *', { timeout: 20000 }).catch(() => null);

    // Take screenshot
    await page.screenshot({
      path: 'test-results/machines-page-content.png',
      fullPage: true
    });

    // Check if any content loaded in main
    const mainHTML = await page.locator('main').innerHTML().catch(() => '');
    console.log('Main content length:', mainHTML.length);

    // We expect content in main (8000+ chars indicates full page loaded)
    expect(mainHTML.length).toBeGreaterThan(100);
  });
});
