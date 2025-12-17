const { test, expect } = require('@playwright/test');

test('Quick Screenshots', async ({ page }) => {
  test.setTimeout(120000);

  // 1. Login page
  console.log('1. Login page...');
  await page.goto('https://dumontcloud.com/');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/test_01_login.png', fullPage: true });

  // Check logo
  const logoSvg = page.locator('svg').first();
  const hasLogo = await logoSvg.count() > 0;
  console.log(`Logo presente: ${hasLogo}`);

  // 2. Login
  console.log('2. Fazendo login...');
  await page.locator('input[type="text"]').fill('marcosremar@gmail.com');
  await page.locator('input[type="password"]').fill('Marcos123');
  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(4000);
  await page.screenshot({ path: '/tmp/test_02_dashboard.png', fullPage: true });

  // 3. Machines
  console.log('3. Machines page...');
  await page.goto('https://dumontcloud.com/machines');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/test_03_machines.png', fullPage: true });

  // 4. Settings
  console.log('4. Settings page...');
  await page.goto('https://dumontcloud.com/settings');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/test_04_settings.png', fullPage: true });

  // Check show/hide buttons
  const eyeButtons = page.locator('.secret-toggle-btn');
  const eyeCount = await eyeButtons.count();
  console.log(`Botões show/hide: ${eyeCount}`);

  // 5. Mobile view
  console.log('5. Mobile view...');
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('https://dumontcloud.com/');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/test_05_mobile.png', fullPage: true });

  // Check hamburger menu
  const hamburger = page.locator('.mobile-menu-button');
  const hasHamburger = await hamburger.isVisible();
  console.log(`Menu hamburger visível: ${hasHamburger}`);

  if (hasHamburger) {
    await hamburger.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/test_06_mobile_menu.png', fullPage: true });
  }

  console.log('Teste completo!');
});
