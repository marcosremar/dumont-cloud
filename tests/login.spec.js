/**
 * Dumont Cloud - Login E2E Tests
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.TEST_URL || 'https://dumontcloud.com';
const TEST_USER = process.env.TEST_USER || 'marcosremar@gmail.com';
const TEST_PASS = process.env.TEST_PASS || 'Marcos123';

test.describe('Login Tests', () => {
  test('should display login page', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForTimeout(2000);

    // Take screenshot
    await page.screenshot({ path: 'screenshots/login-page.png', fullPage: true });

    // Check for login form elements
    const title = page.locator('text=Dumont Cloud');
    await expect(title).toBeVisible();

    const usernameInput = page.locator('input[type="text"]');
    const passwordInput = page.locator('input[type="password"]');
    const loginButton = page.locator('button:has-text("Login")');

    await expect(usernameInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(loginButton).toBeVisible();
  });

  test('should fail login with wrong password', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForTimeout(1000);

    await page.fill('input[type="text"]', TEST_USER);
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button:has-text("Login")');

    await page.waitForTimeout(2000);

    // Take screenshot
    await page.screenshot({ path: 'screenshots/login-error.png', fullPage: true });

    // Should show error message
    const errorMsg = page.locator('.alert-error, [class*="error"]');
    await expect(errorMsg).toBeVisible();

    // Should still be on login page
    expect(page.url()).toContain('/login');
  });

  test('should successfully login with correct credentials', async ({ page }) => {
    // Listen to API responses
    let loginResponse = null;
    page.on('response', async (response) => {
      if (response.url().includes('/api/auth/login')) {
        loginResponse = {
          status: response.status(),
          body: await response.json().catch(() => null)
        };
        console.log('Login API Response:', loginResponse);
      }
    });

    await page.goto(`${BASE_URL}/login`);
    await page.waitForTimeout(1000);

    // Fill login form
    await page.fill('input[type="text"]', TEST_USER);
    await page.fill('input[type="password"]', TEST_PASS);

    // Take screenshot before clicking
    await page.screenshot({ path: 'screenshots/login-before-submit.png', fullPage: true });

    // Click login
    await page.click('button:has-text("Login")');

    // Wait for navigation or response
    await page.waitForTimeout(3000);

    // Take screenshot after
    await page.screenshot({ path: 'screenshots/login-after-submit.png', fullPage: true });

    // Check the result
    const currentUrl = page.url();
    console.log('Current URL after login:', currentUrl);
    console.log('Login API Response:', loginResponse);

    // If still on login page, check for error
    if (currentUrl.includes('/login')) {
      const errorVisible = await page.locator('.alert-error, [class*="error"]').isVisible();
      const errorText = await page.locator('.alert-error, [class*="error"]').textContent().catch(() => '');
      console.log('Error visible:', errorVisible);
      console.log('Error text:', errorText);

      // This should not happen - fail the test
      expect(currentUrl).not.toContain('/login');
    } else {
      // Successfully logged in - verify we're on dashboard
      console.log('Login successful! Redirected to:', currentUrl);
      expect(currentUrl).not.toContain('/login');
    }
  });

  test('should persist login session', async ({ page }) => {
    // Login first
    await page.goto(`${BASE_URL}/login`);
    await page.waitForTimeout(1000);
    await page.fill('input[type="text"]', TEST_USER);
    await page.fill('input[type="password"]', TEST_PASS);
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(3000);

    // Check localStorage for token
    const token = await page.evaluate(() => localStorage.getItem('auth_token'));
    console.log('Token in localStorage:', token ? 'Present' : 'Not found');

    // Navigate to machines page
    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(2000);

    // Take screenshot
    await page.screenshot({ path: 'screenshots/machines-after-login.png', fullPage: true });

    // Should not be redirected to login
    expect(page.url()).not.toContain('/login');
  });
});
