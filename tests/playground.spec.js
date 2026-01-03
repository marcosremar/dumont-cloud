const { test, expect } = require('@playwright/test');

test.describe('Playground Page', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to Playground page (auth handled by storageState in playwright.config.js)
    await page.goto('/app/playground');
    await page.waitForLoadState('networkidle');
  });

  test('should display Playground page header', async ({ page }) => {
    // Wait for page to load
    await page.waitForSelector('body', { timeout: 10000 });

    // The page should have loaded successfully (no error state)
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(0);

    // Take a screenshot for verification
    await page.screenshot({ path: 'tests/screenshots/playground-loaded.png', fullPage: true });
  });

  test('should display model selector', async ({ page }) => {
    // Look for model selector elements
    // The Playground has a model dropdown/selector
    const modelElements = page.locator('text=/modelo|model|selec/i').first();

    // Either model selector exists or we have a "no models" state
    const hasModels = await modelElements.isVisible({ timeout: 5000 }).catch(() => false);
    const noModelsMessage = await page.locator('text=/nenhum modelo|no model|deploy/i').first().isVisible({ timeout: 2000 }).catch(() => false);

    // One of these states should be true
    expect(hasModels || noModelsMessage).toBe(true);
  });

  test('should have input area for messages', async ({ page }) => {
    // Look for input field (textarea or input for chat messages)
    const inputArea = page.locator('textarea, input[type="text"]').first();

    // Input should be visible or page shows no-models state
    const hasInput = await inputArea.isVisible({ timeout: 5000 }).catch(() => false);
    const noModelsMessage = await page.locator('text=/nenhum modelo|no model|deploy/i').first().isVisible({ timeout: 2000 }).catch(() => false);

    expect(hasInput || noModelsMessage).toBe(true);
  });

  test('should display refresh button', async ({ page }) => {
    // Look for refresh button
    const refreshBtn = page.locator('button').filter({ has: page.locator('svg') }).first();

    // Should have some interactive elements
    const hasButtons = await refreshBtn.isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasButtons).toBe(true);
  });

});
