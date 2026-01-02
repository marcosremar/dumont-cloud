// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Simple test to open browser and navigate to login with auto_login=demo
 * This will open a visible browser window that stays open
 */
test.describe('Open Browser with Auto-Login Demo', () => {
  test('navigate to login page with auto_login=demo', async ({ page }) => {
    console.log('Opening browser and navigating to http://localhost:4893/login?auto_login=demo');

    // Navigate to the login page with auto_login parameter
    await page.goto('http://localhost:4893/login?auto_login=demo');

    // Wait for auto-login to complete and redirect to /app
    console.log('Waiting for auto-login to complete...');
    await page.waitForURL('**/app**', { timeout: 30000 });

    console.log('Auto-login completed successfully!');

    // Wait a bit so user can see the page
    await page.waitForTimeout(2000);

    // Verify we're on the app page
    expect(page.url()).toContain('/app');

    console.log('Test completed. Browser will remain open until test ends.');

    // Keep browser open for a while so user can interact
    await page.waitForTimeout(60000); // Wait 60 seconds
  });
});
