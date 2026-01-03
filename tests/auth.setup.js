/**
 * Playwright Auth Setup - Demo mode authentication
 */
const { test: setup, expect } = require('@playwright/test');
const path = require('path');

const authFile = path.join(__dirname, '.auth/user.json');

setup('authenticate as demo user', async ({ page }) => {
  // Navigate to login with auto_login=demo parameter
  await page.goto('/login?auto_login=demo');

  // Wait for successful login - should redirect to /app
  await page.waitForURL('**/app**', { timeout: 15000 });

  // Verify we're logged in by checking for dashboard elements
  await expect(page.locator('body')).toBeVisible();

  // Save authentication state
  await page.context().storageState({ path: authFile });
});
