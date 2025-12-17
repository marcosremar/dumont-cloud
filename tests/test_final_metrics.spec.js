const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://dumontcloud.com';
const TEST_USER = 'test@test.com';
const TEST_PASS = 'test123';

test('Final Metrics Page Test', async ({ page }) => {
  test.setTimeout(60000);

  // 1. Login
  console.log('1. Going to homepage...');
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  // Login if needed
  const loginInput = page.locator('input[type="text"]').first();
  if (await loginInput.isVisible({ timeout: 3000 }).catch(() => false)) {
    console.log('2. Logging in...');
    await loginInput.fill(TEST_USER);
    await page.locator('input[type="password"]').first().fill(TEST_PASS);
    await page.locator('button[type="submit"]').first().click();
    await page.waitForTimeout(3000);
  }

  await page.screenshot({ path: '/tmp/final_01_dashboard.png', fullPage: true });

  // 2. Navigate to Metrics
  console.log('3. Navigating to metrics...');

  // Click on Métricas dropdown
  const metricsDropdown = page.locator('span.nav-link:has-text("Métricas")').first();
  if (await metricsDropdown.isVisible({ timeout: 3000 }).catch(() => false)) {
    await metricsDropdown.click();
    await page.waitForTimeout(500);

    // Click on dropdown item
    const metricsLink = page.locator('a[href="/metrics"]').first();
    if (await metricsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await metricsLink.click();
    }
  } else {
    // Direct navigation
    await page.goto(`${BASE_URL}/metrics`, { waitUntil: 'domcontentloaded' });
  }

  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/final_02_metrics.png', fullPage: true });

  // 3. Check for new elements
  const currentUrl = page.url();
  console.log('Current URL:', currentUrl);

  // Check for tabs
  const marketTab = await page.locator('button:has-text("Mercado")').isVisible().catch(() => false);
  const providersTab = await page.locator('button:has-text("Provedores")').isVisible().catch(() => false);
  const efficiencyTab = await page.locator('button:has-text("Eficiência")').isVisible().catch(() => false);

  console.log('Market Tab:', marketTab);
  console.log('Providers Tab:', providersTab);
  console.log('Efficiency Tab:', efficiencyTab);

  // 4. Click on Providers tab if visible
  if (providersTab) {
    console.log('4. Clicking Providers tab...');
    await page.locator('button:has-text("Provedores")').click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/final_03_providers.png', fullPage: true });
  }

  // 5. Click on Efficiency tab if visible
  if (efficiencyTab) {
    console.log('5. Clicking Efficiency tab...');
    await page.locator('button:has-text("Eficiência")').click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/final_04_efficiency.png', fullPage: true });
  }

  // 6. Final check - print page content summary
  const content = await page.content();
  console.log('\n=== FINAL CHECK ===');
  console.log('Has tabs:', content.includes('metrics-tab'));
  console.log('Has filters:', content.includes('filter-select') || content.includes('Todas as GPUs'));
  console.log('Has market elements:', content.includes('market-summary') || content.includes('Mercado'));
  console.log('==================\n');

  // Take final screenshot
  await page.screenshot({ path: '/tmp/final_05_complete.png', fullPage: true });
});
