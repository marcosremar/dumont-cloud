// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * Simplified config for debugging wizard on port 4893
 * No auth setup required - uses auto_login=demo
 */
module.exports = defineConfig({
  testDir: './',
  testMatch: /debug-wizard-(4893|html|flow)\.spec\.js/,
  fullyParallel: false,
  forbidOnly: false,
  retries: 0,
  workers: 1,
  reporter: 'list',
  timeout: 120000,
  use: {
    baseURL: 'http://localhost:4893',
    trace: 'on',
    screenshot: 'on',
    video: 'on',
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // No storageState - uses auto_login=demo
      },
    },
  ],

  outputDir: 'test-results/',
});
