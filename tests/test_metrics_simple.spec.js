const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://dumontcloud.com';
const TEST_USER = 'test@test.com';
const TEST_PASS = 'test123';

test('Simple Metrics Page Test', async ({ page }) => {
  test.setTimeout(60000);

  // Set viewport to desktop size
  await page.setViewportSize({ width: 1920, height: 1080 });

  // 1. Login
  console.log('1. Going to login...');
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  const loginInput = page.locator('input[type="text"]').first();
  if (await loginInput.isVisible({ timeout: 3000 }).catch(() => false)) {
    console.log('2. Logging in...');
    await loginInput.fill(TEST_USER);
    await page.locator('input[type="password"]').first().fill(TEST_PASS);
    await page.locator('button[type="submit"]').first().click();
    await page.waitForTimeout(3000);
  }

  await page.screenshot({ path: '/tmp/simple_01_dashboard.png', fullPage: true });
  console.log('Dashboard screenshot saved');

  // 2. Go directly to /metrics
  console.log('3. Navigating directly to /metrics...');
  await page.goto(`${BASE_URL}/metrics`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(4000);

  await page.screenshot({ path: '/tmp/simple_02_metrics.png', fullPage: true });
  console.log('Metrics page screenshot saved');

  // 3. Check current URL
  const currentUrl = page.url();
  console.log('Current URL:', currentUrl);

  // 4. Check for new UI elements
  const pageContent = await page.content();

  const checks = {
    'metrics-tabs': pageContent.includes('metrics-tab'),
    'Market button': pageContent.includes('Mercado'),
    'Providers button': pageContent.includes('Provedores'),
    'Efficiency button': pageContent.includes('Eficiência'),
    'GPU filter': pageContent.includes('Todas as GPUs') || pageContent.includes('filter-select'),
    'Type filter': pageContent.includes('Tipo de Máquina') || pageContent.includes('Todos os Tipos'),
  };

  console.log('\n=== UI ELEMENTS CHECK ===');
  for (const [name, found] of Object.entries(checks)) {
    console.log(`${name}: ${found ? 'YES' : 'NO'}`);
  }
  console.log('========================\n');

  // 5. Try to interact with tabs if they exist
  const providersBtn = page.locator('button:has-text("Provedores")');
  if (await providersBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log('Clicking Providers tab...');
    await providersBtn.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/simple_03_providers.png', fullPage: true });
  }

  const efficiencyBtn = page.locator('button:has-text("Eficiência")');
  if (await efficiencyBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log('Clicking Efficiency tab...');
    await efficiencyBtn.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/simple_04_efficiency.png', fullPage: true });
  }

  console.log('Test completed!');
});
