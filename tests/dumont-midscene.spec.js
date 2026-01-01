/**
 * Dumont Cloud - AI-Powered E2E Tests using Midscene.js
 *
 * Tests the complete flow of creating a GPU machine using AI vision
 * Using OpenRouter API with Google Gemini 3 Flash Preview (economical)
 */

const { test: base, expect } = require('@playwright/test');
const { PlaywrightAiFixture, overrideAIConfig } = require('@midscene/web/playwright');

// Load environment variables (override system env vars)
require('dotenv').config({ path: '../.env', override: true });

// Configure midscene with OpenRouter + Gemini 2.5 Flash
overrideAIConfig({
  MIDSCENE_MODEL_API_KEY: process.env.OPENROUTER_API_KEY,
  MIDSCENE_MODEL_BASE_URL: 'https://openrouter.ai/api/v1',
  MIDSCENE_MODEL_NAME: 'google/gemini-2.5-flash',
  MIDSCENE_USE_GEMINI: 'false'
});

// Extend Playwright test with Midscene AI fixtures
const test = base.extend(PlaywrightAiFixture());

test.describe('Dumont Cloud - Midscene.js AI Tests', () => {

  test.beforeEach(async ({ page }) => {
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

    // Click login button using text selector
    const loginButton = page.locator('button:has-text("Entrar"), button:has-text("Login")');
    await loginButton.click();
    console.log('Credentials submitted');

    // Wait for the request to complete
    await page.waitForTimeout(3000);

    // Wait for redirect to /app
    await page.waitForURL('**/app**', { timeout: 15000 });
    console.log('Logged in successfully');

    // Wait for the app to load
    await page.waitForTimeout(1000);
  });

  test('should create a new GPU machine with AI', async ({ aiAct, aiQuery }) => {
    console.log('=== TEST: Create GPU Machine with Midscene ===');

    // Use AI to click on GPU Offers button
    await aiAct('Click on the "GPU Offers" or "Nova Máquina" button');
    await test.step('Wait after GPU Offers click', async () => {
      await new Promise(resolve => setTimeout(resolve, 1500));
    });

    // AI selects Europa region
    await aiAct('Click on the "Europa" region button on the map');
    await test.step('Wait after Europa selection', async () => {
      await new Promise(resolve => setTimeout(resolve, 1500));
    });

    // AI selects Fast speed tier
    await aiAct('Click on the "Fast" speed tier button');
    await test.step('Wait after speed tier selection', async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
    });

    // AI selects first GPU offer
    await aiAct('Click on the first GPU offer card to select it');
    await test.step('Wait after GPU offer selection', async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
    });

    // AI clicks create button
    await aiAct('Click the "Criar Máquina" or "Create Machine" button at the bottom');

    // Wait for creation to complete
    await test.step('Wait for machine creation', async () => {
      await new Promise(resolve => setTimeout(resolve, 5000));
    });

    // Use AI to verify machine was created
    const machineExists = await aiQuery('Is there at least one machine card visible on the page?');

    expect(machineExists).toBeTruthy();
    console.log('Machine creation test completed successfully');
  });

  test('should verify VS Code button with AI', async ({ aiAct, aiQuery }) => {
    console.log('=== TEST: VS Code Button ===');

    // Already on the app page after login, no navigation needed
    await test.step('Wait for page load', async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
    });

    // AI finds and clicks VS Code button
    await aiAct('Click on the VS Code button on the first machine card');
    await test.step('Wait after click', async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
    });

    // AI verifies dropdown appeared
    const dropdownVisible = await aiQuery('Is there a dropdown menu with "Online (Web)" option visible?');

    expect(dropdownVisible).toBeTruthy();
    console.log('VS Code button test completed successfully');
  });

  test('should verify region filter with AI', async ({ aiAct, aiQuery }) => {
    console.log('=== TEST: Region Filter ===');

    // Go to GPU offers
    await aiAct('Click on GPU Offers or Nova Máquina button');
    await test.step('Wait for offers page', async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
    });

    // Select Europa region
    await aiAct('Click on the Europa region on the map');
    await test.step('Wait for filtering', async () => {
      await new Promise(resolve => setTimeout(resolve, 2000));
    });

    // Verify only European offers are shown
    const europeanOffersOnly = await aiQuery('Are all GPU offers shown from European countries like Spain, Germany, France, Netherlands, Poland?');
    expect(europeanOffersOnly).toBeTruthy();

    // Verify no non-European countries
    const noAsianOffers = await aiQuery('Are there any offers from China, Korea, Canada, or United States?');
    expect(noAsianOffers).toBeFalsy();

    console.log('Region filter test completed successfully');
  });

  test('should display GPU offer information', async ({ aiAct, aiQuery }) => {
    console.log('=== TEST: GPU Offers Display ===');

    // Navigate to offers
    await aiAct('Go to the GPU Offers page');
    await test.step('Wait for offers page', async () => {
      await new Promise(resolve => setTimeout(resolve, 2000));
    });

    // Verify offers are displayed
    const offersVisible = await aiQuery('Are multiple GPU offer cards visible on the page?');
    expect(offersVisible).toBeTruthy();

    // Verify offer details
    const offerHasDetails = await aiQuery('Do the GPU offers show GPU type, price, and location information?');
    expect(offerHasDetails).toBeTruthy();

    console.log('GPU offers display test completed successfully');
  });

  test('should delete a machine with AI', async ({ aiAct, aiQuery }) => {
    console.log('=== TEST: Delete Machine ===');

    // Already on the app page with machines after login
    await test.step('Wait for page load', async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
    });

    // Click destroy button
    await aiAct('Click on the destroy/delete button (trash icon) on the first machine');
    await test.step('Wait for dialog', async () => {
      await new Promise(resolve => setTimeout(resolve, 500));
    });

    // Confirm deletion
    await aiAct('Click the confirm button in the confirmation dialog');
    await test.step('Wait for deletion', async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
    });

    // Verify loading animation appears
    const loadingVisible = await aiQuery('Is there a loading spinner or "Destruindo máquina" message visible?');
    expect(loadingVisible).toBeTruthy();

    console.log('Delete machine test completed successfully');
  });

  test.afterEach(async ({ page }) => {
    // Take screenshot for debugging
    const timestamp = Date.now();
    await page.screenshot({
      path: `tests/screenshots/midscene-test-${timestamp}.png`,
      fullPage: true
    });

    console.log(`Screenshot saved: midscene-test-${timestamp}.png`);
  });
});
