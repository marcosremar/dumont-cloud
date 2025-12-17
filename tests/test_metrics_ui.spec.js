const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://dumontcloud.com';

// Test credentials - using test user
const TEST_USER = 'test@test.com';
const TEST_PASS = 'test123';

test.describe('Metrics Page UI Tests', () => {

  test('1. Access metrics page and verify new UI elements', async ({ page }) => {
    // Go to home page
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // Take screenshot of initial state
    await page.screenshot({ path: '/tmp/metrics_ui_01_initial.png', fullPage: true });

    // Check if we're on login page
    const loginInput = page.locator('input[type="text"], input[placeholder*="Usuario"], input[placeholder*="Email"]').first();

    if (await loginInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      console.log('On login page - attempting login');

      // Try login
      await loginInput.fill(TEST_USER);
      const passwordInput = page.locator('input[type="password"]').first();
      await passwordInput.fill(TEST_PASS);

      const submitBtn = page.locator('button[type="submit"]').first();
      await submitBtn.click();

      await page.waitForTimeout(3000);
      await page.screenshot({ path: '/tmp/metrics_ui_02_after_login.png', fullPage: true });
    }

    // Try to navigate to metrics page
    console.log('Navigating to metrics page...');

    // Check if there's a Métricas menu item
    const metricsMenu = page.locator('text=Métricas').first();
    if (await metricsMenu.isVisible({ timeout: 3000 }).catch(() => false)) {
      await metricsMenu.hover();
      await page.waitForTimeout(500);
      await page.screenshot({ path: '/tmp/metrics_ui_03_menu_hover.png', fullPage: true });

      // Click on GPU Metrics
      const gpuMetricsLink = page.locator('text=Métricas de GPU').first();
      if (await gpuMetricsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await gpuMetricsLink.click();
        await page.waitForTimeout(2000);
      }
    } else {
      // Direct navigation
      await page.goto(`${BASE_URL}/metrics`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(3000);
    }

    await page.screenshot({ path: '/tmp/metrics_ui_04_metrics_page.png', fullPage: true });

    // Check for new UI elements
    const currentUrl = page.url();
    console.log('Current URL:', currentUrl);

    // Check for tabs
    const marketTab = page.locator('text=Mercado').first();
    const providersTab = page.locator('text=Provedores').first();
    const efficiencyTab = page.locator('text=Eficiência').first();

    console.log('Market tab visible:', await marketTab.isVisible().catch(() => false));
    console.log('Providers tab visible:', await providersTab.isVisible().catch(() => false));
    console.log('Efficiency tab visible:', await efficiencyTab.isVisible().catch(() => false));

    // Check for filters
    const gpuFilter = page.locator('select').first();
    console.log('GPU filter visible:', await gpuFilter.isVisible().catch(() => false));
  });

  test('2. Test tab navigation', async ({ page }) => {
    // Direct navigation to metrics
    await page.goto(`${BASE_URL}/metrics`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Check current URL
    const url = page.url();
    console.log('Current URL:', url);

    if (url.includes('metrics')) {
      // Test clicking on Providers tab
      const providersTab = page.locator('button:has-text("Provedores")').first();
      if (await providersTab.isVisible({ timeout: 3000 }).catch(() => false)) {
        await providersTab.click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: '/tmp/metrics_ui_05_providers_tab.png', fullPage: true });
        console.log('Providers tab clicked');
      }

      // Test clicking on Efficiency tab
      const efficiencyTab = page.locator('button:has-text("Eficiência")').first();
      if (await efficiencyTab.isVisible({ timeout: 3000 }).catch(() => false)) {
        await efficiencyTab.click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: '/tmp/metrics_ui_06_efficiency_tab.png', fullPage: true });
        console.log('Efficiency tab clicked');
      }

      // Back to Market tab
      const marketTab = page.locator('button:has-text("Mercado")').first();
      if (await marketTab.isVisible({ timeout: 3000 }).catch(() => false)) {
        await marketTab.click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: '/tmp/metrics_ui_07_market_tab.png', fullPage: true });
        console.log('Market tab clicked');
      }
    } else {
      console.log('Not on metrics page - might be redirected to login');
      await page.screenshot({ path: '/tmp/metrics_ui_05_not_metrics.png', fullPage: true });
    }
  });

  test('3. Verify page structure', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Get page content
    const content = await page.content();

    // Check for expected elements
    const hasMetricsTitle = content.includes('Métricas de GPU');
    const hasMarketTab = content.includes('Mercado');
    const hasProvidersTab = content.includes('Provedores');
    const hasEfficiencyTab = content.includes('Eficiência');
    const hasFilters = content.includes('filter-') || content.includes('Todas as GPUs');

    console.log('\n=== PAGE STRUCTURE CHECK ===');
    console.log('Has Metrics Title:', hasMetricsTitle);
    console.log('Has Market Tab:', hasMarketTab);
    console.log('Has Providers Tab:', hasProvidersTab);
    console.log('Has Efficiency Tab:', hasEfficiencyTab);
    console.log('Has Filters:', hasFilters);
    console.log('============================\n');

    await page.screenshot({ path: '/tmp/metrics_ui_08_final.png', fullPage: true });
  });
});
