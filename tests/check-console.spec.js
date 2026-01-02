const { test, expect } = require('@playwright/test');

test.use({
  baseURL: 'http://localhost:4893',
  storageState: undefined // No auth state needed - using auto_login
});

test.describe('Console Error Check', () => {
  test('should capture console messages on auto-login', async ({ page }) => {
    const consoleMessages = [];
    const errors = [];
    const warnings = [];
    const apiErrors = [];
    const apiCalls = [];
    const allApiCalls = [];
    const failedResources = [];

    // Listen to all console messages
    page.on('console', msg => {
      const text = msg.text();
      consoleMessages.push({
        type: msg.type(),
        text: text
      });

      if (msg.type() === 'error') {
        errors.push(text);
      }
      if (msg.type() === 'warning') {
        warnings.push(text);
      }

      // Also log to test output for debugging
      const prefix = msg.type() === 'error' ? '❌' :
                    msg.type() === 'warning' ? '⚠️' :
                    msg.type() === 'log' ? '📝' : '🔍';
      console.log(`${prefix} Browser: ${text}`);
    });

    // Listen to ALL responses (success and failure)
    page.on('response', response => {
      const url = response.url();
      const status = response.status();

      // Track ALL API calls (only /api/)
      if (url.includes('/api/')) {
        allApiCalls.push({
          url: url,
          status: status
        });
      }

      // Track API calls we care about
      if (url.includes('/api/v1/nps/should-show') ||
          url.includes('/api/v1/users/me/teams') ||
          url.includes('/api/v1/settings/complete-onboarding')) {
        apiCalls.push({
          url: url,
          status: status
        });
      }

      // Track 500 errors
      if (status === 500) {
        apiErrors.push({
          url: url,
          status: status
        });
      }

      // Track 404 errors
      if (status === 404) {
        failedResources.push({
          url: url,
          status: status
        });
      }

      // Track 401 errors
      if (status === 401) {
        failedResources.push({
          url: url,
          status: status
        });
        console.log(`🔐 401 Unauthorized: ${url}`);
      }
    });

    // Navigate with auto-login
    console.log('Navigating to /login?auto_login=demo');
    await page.goto('/login?auto_login=demo');

    // Wait for redirect to /app or /demo-app
    console.log('Waiting for redirect...');
    try {
      await page.waitForURL('**/app**', { timeout: 10000 });
      console.log('Redirected to:', page.url());
    } catch (e) {
      console.log('No redirect detected, current URL:', page.url());
    }

    // Wait for page to fully load
    console.log('Waiting for page to load...');
    await page.waitForLoadState('networkidle', { timeout: 30000 });

    // Wait a bit more for any async operations
    await page.waitForTimeout(3000);

    // Report findings
    console.log('\n=== CONSOLE MESSAGES ===');
    consoleMessages.forEach(msg => {
      console.log(`[${msg.type.toUpperCase()}] ${msg.text}`);
    });

    console.log('\n=== ERRORS ===');
    if (errors.length === 0) {
      console.log('No console errors found!');
    } else {
      errors.forEach(err => console.log(`ERROR: ${err}`));
    }

    console.log('\n=== WARNINGS ===');
    if (warnings.length === 0) {
      console.log('No console warnings found!');
    } else {
      warnings.forEach(warn => console.log(`WARNING: ${warn}`));
    }

    console.log('\n=== API 500 ERRORS ===');
    if (apiErrors.length === 0) {
      console.log('No 500 errors found!');
    } else {
      apiErrors.forEach(err => {
        console.log(`500 ERROR: ${err.url} (${err.status})`);
      });
    }

    console.log('\n=== SPECIFIC API CALLS (nps, teams, onboarding) ===');
    if (apiCalls.length === 0) {
      console.log('None of the specific endpoints were called.');
    } else {
      apiCalls.forEach(call => {
        const statusIcon = call.status === 200 ? '✓' : call.status === 500 ? '✗' : '⚠';
        console.log(`${statusIcon} ${call.url} -> ${call.status}`);
      });
    }

    console.log('\n=== 404 ERRORS ===');
    if (failedResources.length === 0) {
      console.log('No 404 errors found!');
    } else {
      failedResources.forEach(err => {
        console.log(`404: ${err.url}`);
      });
    }

    console.log('\n=== ALL API CALLS ===');
    if (allApiCalls.length === 0) {
      console.log('No API calls detected.');
    } else {
      allApiCalls.forEach(call => {
        const statusIcon = call.status >= 200 && call.status < 300 ? '✓' :
                          call.status === 500 ? '✗' :
                          call.status === 404 ? '?' : '⚠';
        // Shorten URL for readability
        const shortUrl = call.url.replace('http://localhost:4893', '').replace('http://localhost:8766', '');
        console.log(`${statusIcon} [${call.status}] ${shortUrl}`);
      });
    }

    // Take a screenshot for reference
    await page.screenshot({ path: 'test-results/console-check.png', fullPage: true });
    console.log('\nScreenshot saved to test-results/console-check.png');

    // Test passes regardless - we just want to see the output
    expect(true).toBe(true);
  });
});
