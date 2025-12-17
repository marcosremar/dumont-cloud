const { test, expect } = require('@playwright/test');

test('Capturar screenshots das páginas', async ({ page }) => {
  test.setTimeout(120000);

  // Capturar erros
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('CONSOLE ERROR:', msg.text());
    }
  });

  // 1. Login
  console.log('1. Acessando login...');
  await page.goto('https://dumontcloud.com', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/test_01_login.png', fullPage: true });
  console.log('Screenshot 1: Login page');

  // Verificar se precisa logar
  const loginInput = page.locator('input[type="text"], input[placeholder*="Usuario"], input[placeholder*="Email"]').first();

  if (await loginInput.isVisible({ timeout: 5000 }).catch(() => false)) {
    console.log('2. Fazendo login...');
    await loginInput.fill('marcosremar@gmail.com');

    const passwordInput = page.locator('input[type="password"]').first();
    await passwordInput.fill('marcos123');

    const submitBtn = page.locator('button[type="submit"]').first();
    await submitBtn.click();

    await page.waitForTimeout(4000);
    await page.screenshot({ path: '/tmp/test_02_after_login.png', fullPage: true });
    console.log('Screenshot 2: Após login');
  } else {
    console.log('Já logado ou página diferente');
  }

  // 3. Dashboard
  console.log('3. Dashboard...');
  await page.goto('https://dumontcloud.com/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/test_03_dashboard.png', fullPage: true });
  console.log('Screenshot 3: Dashboard');

  // 4. Machines
  console.log('4. Machines...');
  await page.goto('https://dumontcloud.com/machines', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/test_04_machines.png', fullPage: true });
  console.log('Screenshot 4: Machines');

  // 5. Metrics
  console.log('5. Metrics...');
  await page.goto('https://dumontcloud.com/metrics', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/test_05_metrics.png', fullPage: true });
  console.log('Screenshot 5: Metrics');

  // 6. Settings
  console.log('6. Settings...');
  await page.goto('https://dumontcloud.com/settings', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/test_06_settings.png', fullPage: true });
  console.log('Screenshot 6: Settings');

  console.log('\nTodos os screenshots salvos em /tmp/test_*.png');
});
