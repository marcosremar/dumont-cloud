/**
 * Dumont Cloud - AI-Powered E2E Tests using UI-TARS
 *
 * Tests the complete flow of creating a GPU machine using AI vision
 * Using OpenRouter API with UI-TARS 7B model (economical alternative)
 */

const { test, expect } = require('@playwright/test');
const { GUIAgent } = require('@ui-tars/sdk');
const { BrowserOperator } = require('@ui-tars/operator-browser');
const config = require('./ui-tars.config');

// Load environment variables
require('dotenv').config({ path: '../.env' });

test.describe('Dumont Cloud - UI-TARS Tests', () => {
  let guiAgent;

  test.beforeEach(async ({ page, browser }) => {
    // Navigate directly to login page
    await page.goto('http://dumontcloud.orb.local:4890/login');
    await page.waitForLoadState('networkidle');

    // Login using standard Playwright (faster than AI for simple forms)
    const user = 'marcosremar@gmail.com';
    const pass = 'dumont123';

    console.log('Logging in...');

    // Find and fill username input
    const usernameInput = page.locator('input[name="username"], input[type="text"], input[type="email"]').first();
    await usernameInput.fill(user);

    // Find and fill password input
    const passwordInput = page.locator('input[type="password"]');
    await passwordInput.fill(pass);

    // Click login button using text selector (more reliable)
    const loginButton = page.locator('button:has-text("Entrar"), button:has-text("Login")');
    await loginButton.click();
    console.log('Credentials submitted');

    // Wait for the request to complete
    await page.waitForTimeout(3000);

    // Wait for redirect to /app (not /machines)
    await page.waitForURL('**/app**', { timeout: 15000 });
    console.log('Logged in successfully');

    // Wait a bit for the app to load
    await page.waitForTimeout(1000);

    // Initialize UI-TARS agent AFTER login
    // BrowserOperator needs the browser object, not page
    const operator = new BrowserOperator(browser);

    guiAgent = new GUIAgent({
      model: config.model,
      operator,
      onData: ({ data }) => console.log('[UI-TARS]', data),
      onError: ({ data, error }) => console.error('[UI-TARS ERROR]', error, data),
    });
  });

  test('should create a new GPU machine', async ({ page }) => {
    console.log('=== TEST: Create GPU Machine ===');

    // Step 1: Navigate to machine creation
    await guiAgent.run('Click on the "GPU Offers" or "Nova Máquina" button');
    await page.waitForTimeout(1000);

    // Step 2: Select Europa region
    await guiAgent.run('Click on the "Europa" region button on the map');
    await page.waitForTimeout(1500);

    // Step 3: Select Fast speed tier
    await guiAgent.run('Click on the "Fast" speed tier button');
    await page.waitForTimeout(1000);

    // Step 4: Select first GPU offer
    await guiAgent.run('Click on the first GPU offer card to select it');
    await page.waitForTimeout(1000);

    // Step 5: Click create button
    await guiAgent.run('Click the "Criar Máquina" or "Create Machine" button at the bottom');

    // Wait for creation to complete
    await page.waitForTimeout(5000);

    // Step 6: Verify we're on machines page
    const url = page.url();
    expect(url).toContain('/machines');

    // Step 7: Verify machine was created
    await guiAgent.run('Verify that there is at least one machine card visible on the page');

    console.log('Machine creation test completed successfully');
  });

  test('should verify VS Code button functionality', async ({ page }) => {
    console.log('=== TEST: VS Code Button ===');

    // Navigate to machines page
    await guiAgent.run('Navigate to the machines list page');
    await page.waitForTimeout(2000);

    // Find and click VS Code button
    await guiAgent.run('Click on the VS Code button on the first machine card');
    await page.waitForTimeout(1000);

    // Verify dropdown appeared
    await guiAgent.run('Verify that a dropdown menu with "Online (Web)" option appeared');

    console.log('VS Code button test completed successfully');
  });

  test('should verify region filter works correctly', async ({ page }) => {
    console.log('=== TEST: Region Filter ===');

    // Go to GPU offers
    await guiAgent.run('Click on GPU Offers or Nova Máquina button');
    await page.waitForTimeout(1000);

    // Select Europa region
    await guiAgent.run('Click on the Europa region on the map');
    await page.waitForTimeout(2000);

    // Verify only European offers are shown
    await guiAgent.run('Verify that all GPU offers shown are from European countries like Spain, Germany, France, Netherlands, Poland');

    // Verify no non-European countries
    await guiAgent.run('Verify that there are NO offers from China, Korea, Canada, or United States');

    console.log('Region filter test completed successfully');
  });

  test('should display GPU offer information', async ({ page }) => {
    console.log('=== TEST: GPU Offers Display ===');

    // Navigate to offers
    await guiAgent.run('Go to the GPU Offers page');
    await page.waitForTimeout(2000);

    // Verify offers are displayed
    await guiAgent.run('Verify that multiple GPU offer cards are visible');
    await guiAgent.run('Verify that each offer shows GPU type, price, and location information');

    console.log('GPU offers display test completed successfully');
  });

  test('should delete a machine with animation', async ({ page }) => {
    console.log('=== TEST: Delete Machine ===');

    // Navigate to machines page
    await guiAgent.run('Navigate to the machines list');
    await page.waitForTimeout(2000);

    // Click destroy button
    await guiAgent.run('Click on the destroy/delete button (trash icon) on the first machine');
    await page.waitForTimeout(500);

    // Confirm deletion
    await guiAgent.run('Click the confirm button in the confirmation dialog');
    await page.waitForTimeout(1000);

    // Verify loading animation appears
    await guiAgent.run('Verify that a loading spinner or "Destruindo máquina" message appears');

    console.log('Delete machine test completed successfully');
  });

  test.afterEach(async ({ page }) => {
    // Take screenshot for debugging
    const timestamp = Date.now();
    await page.screenshot({
      path: `tests/screenshots/uitars-test-${timestamp}.png`,
      fullPage: true
    });

    console.log(`Screenshot saved: uitars-test-${timestamp}.png`);
  });
});
