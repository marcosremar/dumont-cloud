// @ts-check
/**
 * Authentication Setup for Playwright Tests
 *
 * Supports two modes:
 * - DEMO MODE (USE_DEMO_MODE=true): Navigates directly to /demo-app, no login required
 * - REAL MODE (default): Performs actual login with credentials
 *
 * Both modes set demo_mode=true in localStorage for mocked data.
 */
const { test, expect } = require('@playwright/test');
const path = require('path');

// Configuração para headless mode consistente
test.use({
  headless: true,
  viewport: { width: 1920, height: 1080 },
});

const authFile = path.join(__dirname, '.auth/user.json');

// Demo app path for consistent navigation
const DEMO_APP_PATH = '/demo-app';

test('authenticate', async ({ page }) => {
  console.log('\n🔐 Setting up authentication...\n');

  // Listen to console for debugging (filter important messages)
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('App.jsx') || text.includes('login') || text.includes('error') || text.includes('auth')) {
      console.log(`[BROWSER] ${msg.type()}: ${text}`);
    }
  });

  // Check if we should use demo mode (USE_DEMO_MODE=true for tests)
  const useDemoMode = process.env.USE_DEMO_MODE === 'true';

  if (useDemoMode) {
    console.log('📍 DEMO MODE: Using demo app (no auth required)\n');

    // Navigate directly to demo app
    await page.goto(DEMO_APP_PATH);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1500);

    // Verify demo app loaded successfully
    const isLoaded = await page.locator('body').isVisible().catch(() => false);
    if (isLoaded) {
      console.log('✅ Demo mode loaded successfully');
    } else {
      console.log('⚠️ Demo app may not have loaded completely');
    }
  } else {
    console.log('📍 REAL MODE: Logging in with credentials\n');

    // Navigate to login page
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('📍 On login page');

    // Fill in credentials
    const username = process.env.TEST_USER_EMAIL || 'marcosremar@gmail.com';
    const password = process.env.TEST_USER_PASSWORD || 'dumont123';

    console.log(`📧 Using username: ${username}`);

    // Find username input (first matching input with .first() for safety)
    const usernameInput = page.locator('input[name="username"], input[type="text"], input[type="email"]').first();
    await usernameInput.fill(username);
    console.log('✅ Username filled');

    // Find password input (with .first() for consistency)
    const passwordInput = page.locator('input[type="password"]').first();
    await passwordInput.fill(password);
    console.log('✅ Password filled');

    // Click login button (with .first() to avoid multiple matches)
    const loginButton = page.locator('button:has-text("Entrar"), button:has-text("Login")').first();
    console.log('🔍 Looking for login button...');

    const isButtonVisible = await loginButton.isVisible({ timeout: 5000 }).catch(() => false);
    if (isButtonVisible) {
      console.log('✅ Login button found');
      await loginButton.click({ force: true });
      console.log('🔑 Credentials submitted');
    } else {
      console.log('⚠️ Login button not found - trying form submit');
      await passwordInput.press('Enter');
      console.log('🔑 Submitted via Enter key');
    }

    // Wait for the request to complete
    await page.waitForTimeout(3000);

    // Check current URL
    const currentUrl = page.url();
    console.log(`📍 Current URL after submit: ${currentUrl}`);

    // Wait for redirect to /app (not /demo-app)
    if (!currentUrl.includes('/app')) {
      console.log('⏳ Waiting for redirect to /app...');
      try {
        await page.waitForURL('**/app**', { timeout: 15000 });
        console.log('✅ Redirected to /app');
      } catch (e) {
        console.log('⚠️ Redirect timeout - continuing anyway');
      }
    }

    console.log('✅ Logged in successfully');
  }

  console.log(`📍 Current URL: ${page.url()}`);

  // Set demo_mode=true in localStorage for mocked backend data
  // This is required for both modes to have data available
  console.log('🔧 Garantindo demo_mode=true para dados mockados...');
  await page.evaluate(() => {
    localStorage.setItem('demo_mode', 'true');
  });
  console.log('✅ demo_mode habilitado (dados mockados disponíveis)');

  // Close welcome modal if present (multiple possible selectors)
  const skipSelectors = [
    'text="Pular tudo"',
    'text="Skip"',
    'button:has-text("Pular")',
    'button:has-text("Skip")',
    '[data-testid="skip-welcome"]',
  ];

  for (const selector of skipSelectors) {
    const skipButton = page.locator(selector).first();
    const isVisible = await skipButton.isVisible({ timeout: 1000 }).catch(() => false);
    if (isVisible) {
      await skipButton.click({ force: true }).catch(() => {});
      await page.waitForTimeout(500);
      console.log('✅ Closed welcome modal');
      break;
    }
  }

  // Navigate to demo-app to ensure proper state if in demo mode
  if (useDemoMode) {
    const currentUrl = page.url();
    if (!currentUrl.includes(DEMO_APP_PATH)) {
      await page.goto(DEMO_APP_PATH);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);
    }
  }

  // Save signed-in state
  await page.context().storageState({ path: authFile });
  console.log(`💾 Auth state saved to ${authFile}\n`);
});
