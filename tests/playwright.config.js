// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './',
  testIgnore: ['**/._*', '**/node_modules/**'],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1, // Allow 1 retry locally for flaky tests
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  timeout: 600000, // 10 minutes for long tests
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:4894',
    trace: 'on-first-retry',
    screenshot: 'on',
    video: 'on-first-retry',
  },

  projects: [
    // Setup project for authentication
    {
      name: 'setup',
      testMatch: /auth\.setup\.js/,
    },
    // Main tests depend on auth setup
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Use saved authentication state
        storageState: '.auth/user.json',
      },
      dependencies: ['setup'],
    },
    // Failover Complete System Test (uses auto-login, port 4890)
    {
      name: 'failover-complete-system',
      testMatch: /failover-complete-system\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4890',
        // No storageState - uses auto_login=demo
      },
    },
    // Midscene.js AI tests (no auth setup dependency, does its own auth)
    {
      name: 'midscene',
      testMatch: /dumont-midscene\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        // No storageState - Midscene tests do their own login
      },
    },
    // Hybrid tests (Playwright + Midscene, uses saved auth)
    {
      name: 'hybrid',
      testMatch: /dumont-hybrid\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: '.auth/user.json',
      },
      dependencies: ['setup'],
    },
    // Standalone wizard navigation test (no auth required - direct demo-app access)
    {
      name: 'wizard-navigation',
      testMatch: /wizard-manual-navigation\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        // No storageState - navigates directly to /demo-app
      },
    },
    // Wizard reservation test (no auth required - demo mode)
    {
      name: 'wizard-reservation',
      testMatch: /wizard-(reservation-test|v2-test|manual-interactive)\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        // No storageState - uses demo mode
      },
    },
    // Wizard debug test (uses port 4898)
    {
      name: 'wizard-debug',
      testMatch: /wizard-(debug|simple|gpu-test)\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4898',
        // No storageState - uses demo mode
      },
    },
    // Wizard logs capture test (uses port 4898)
    {
      name: 'wizard-logs',
      testMatch: /capture_wizard_logs\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4898',
        // No storageState - uses demo mode
      },
    },
    // Wizard test with correct selectors (uses port 4898)
    {
      name: 'wizard-seletores',
      testMatch: /wizard-test-seletores-corretos\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4898',
        // No storageState - uses demo mode
      },
    },
    // Wizard robust test with detailed logging (uses port 4898)
    {
      name: 'wizard-robust',
      testMatch: /wizard-robust-test\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4898',
        // No storageState - uses demo mode
      },
    },
    // Wizard state debugging (uses port 4898)
    {
      name: 'wizard-state-debug',
      testMatch: /wizard-debug-state\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4898',
        // No storageState - uses demo mode
      },
    },
    // Wizard click methods comparison (uses port 4898)
    {
      name: 'wizard-click-methods',
      testMatch: /wizard-click-methods\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4898',
        // No storageState - uses demo mode
      },
    },
    // Simple wizard flow test (uses port 4898)
    {
      name: 'wizard-simple-flow',
      testMatch: /wizard-simple-flow-test\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4898',
        // No storageState - uses demo mode
      },
    },
    // Complete wizard flow test (uses port 4898)
    {
      name: 'wizard-complete-flow',
      testMatch: /wizard-complete-flow-test\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4898',
        // No storageState - uses demo mode
      },
    },
    // Console check test (uses port 4893)
    {
      name: 'console-check',
      testMatch: /check-console\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4893',
        // No storageState - uses auto_login=demo
      },
    },
    // Debug region click test (uses port 4898)
    {
      name: 'wizard-debug-region',
      testMatch: /wizard-debug-region-click\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4898',
        // No storageState - uses demo mode
      },
    },
    // Visual check GPU test (uses port 4892)
    {
      name: 'wizard-gpu-visual',
      testMatch: /wizard-gpu-visual-check\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4892',
        // No storageState - uses auto_login=demo
      },
    },
    // Visual check wizard test (uses port 4893)
    {
      name: 'wizard-visual-check',
      testMatch: /wizard-visual-check\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4893',
        // No storageState - uses auto_login=demo
      },
    },
    // Machines page auto-login test (uses port 4894)
    {
      name: 'machines-page-auto-login',
      testMatch: /machines-page-auto-login\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:4894',
        // No storageState - uses auto_login=demo
      },
    },
  ],

  outputDir: 'test-results/',
});
