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
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  timeout: 600000, // 10 minutes for long tests
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
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
  ],

  outputDir: 'test-results/',
});
