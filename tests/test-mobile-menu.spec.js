const { test, expect } = require('@playwright/test');

test('Test Mobile Menu', async ({ page }) => {
  test.setTimeout(60000);

  // Login
  await page.goto('https://dumontcloud.com/?t=' + Date.now());
  await page.waitForTimeout(2000);
  await page.locator('.form-group input[type="text"]').fill('marcosremar@gmail.com');
  await page.locator('.form-group input[type="password"]').fill('marcos123');
  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(3000);

  // Screenshot Desktop
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/test_desktop.png', fullPage: true });
  console.log('Screenshot: Desktop view');

  // Screenshot Mobile - Menu fechado
  await page.setViewportSize({ width: 375, height: 667 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/test_mobile_closed.png', fullPage: true });
  console.log('Screenshot: Mobile view - menu closed');

  // Tentar abrir o menu mobile
  const hamburgerButton = page.locator('.mobile-menu-button');
  if (await hamburgerButton.isVisible()) {
    await hamburgerButton.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/test_mobile_open.png', fullPage: true });
    console.log('Screenshot: Mobile view - menu open');

    // Verificar se os links estão visíveis
    const dashboardLink = page.locator('.mobile-menu-link').first();
    await expect(dashboardLink).toBeVisible();
    console.log('Mobile menu links visible!');

    // Fechar menu
    await page.locator('.mobile-menu-overlay').click();
    await page.waitForTimeout(500);
  } else {
    console.log('Hamburger button not visible - might not be mobile view');
  }

  // Screenshot Tablet
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/test_tablet.png', fullPage: true });
  console.log('Screenshot: Tablet view');
});
