const { test } = require('@playwright/test');

test('Metrics with Data', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });

  // Login
  await page.goto('https://dumontcloud.com', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  const loginInput = page.locator('input[type="text"]').first();
  if (await loginInput.isVisible({ timeout: 3000 }).catch(() => false)) {
    await loginInput.fill('test@test.com');
    await page.locator('input[type="password"]').first().fill('test123');
    await page.locator('button[type="submit"]').first().click();
    await page.waitForTimeout(3000);
  }

  // Go to metrics
  await page.goto('https://dumontcloud.com/metrics', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000); // Wait for data to load

  await page.screenshot({ path: '/tmp/data_01_market.png', fullPage: true });
  console.log('Market tab screenshot saved');

  // Click Providers
  const providersBtn = page.locator('button:has-text("Provedores")');
  if (await providersBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await providersBtn.click();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/data_02_providers.png', fullPage: true });
    console.log('Providers tab screenshot saved');
  }

  // Click Efficiency
  const efficiencyBtn = page.locator('button:has-text("Eficiência")');
  if (await efficiencyBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await efficiencyBtn.click();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/data_03_efficiency.png', fullPage: true });
    console.log('Efficiency tab screenshot saved');
  }

  console.log('Done!');
});
