const { test, expect } = require('@playwright/test');

test('Full UI Review - All Pages', async ({ page }) => {
  test.setTimeout(180000);

  // Capturar erros do console
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
      console.log('CONSOLE ERROR:', msg.text());
    }
  });

  page.on('pageerror', err => {
    console.log('PAGE ERROR:', err.message);
  });

  // 1. Login Page
  console.log('1. Capturando página de login...');
  await page.goto('https://dumontcloud.com/?t=' + Date.now());
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/review_01_login.png', fullPage: true });
  console.log('Screenshot 1: Login page');

  // Fazer login - usando seletores CSS
  console.log('2. Fazendo login...');
  await page.locator('.form-group input[type="text"]').fill('marcosremar@gmail.com');
  await page.locator('.form-group input[type="password"]').fill('marcos123');
  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(3000);

  // 2. Dashboard / Deploy Wizard
  console.log('3. Capturando Dashboard (Deploy Wizard)...');
  await page.screenshot({ path: '/tmp/review_02_dashboard.png', fullPage: true });

  // Testar interações no Dashboard
  console.log('4. Testando seleção de região Europa...');
  const europaTab = page.locator('button:has-text("Europa")');
  if (await europaTab.isVisible()) {
    await europaTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/review_03_dashboard_europa.png', fullPage: true });
  }

  console.log('5. Testando seleção de região Global...');
  const globalTab = page.locator('button:has-text("Global")');
  if (await globalTab.isVisible()) {
    await globalTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/review_04_dashboard_global.png', fullPage: true });
  }

  // 3. Machines Page
  console.log('6. Navegando para /machines...');
  await page.goto('https://dumontcloud.com/machines');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/review_05_machines.png', fullPage: true });

  // Testar filtros na página de máquinas
  console.log('7. Testando filtro Online...');
  const onlineTab = page.locator('button:has-text("Online")');
  if (await onlineTab.isVisible()) {
    await onlineTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/review_06_machines_online.png', fullPage: true });
  }

  console.log('8. Testando filtro Offline...');
  const offlineTab = page.locator('button:has-text("Offline")');
  if (await offlineTab.isVisible()) {
    await offlineTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/review_07_machines_offline.png', fullPage: true });
  }

  // 4. Settings Page
  console.log('9. Navegando para /settings...');
  await page.goto('https://dumontcloud.com/settings');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/review_08_settings.png', fullPage: true });

  // 5. GPU Metrics Page
  console.log('10. Navegando para /metrics...');
  await page.goto('https://dumontcloud.com/metrics');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/review_09_metrics.png', fullPage: true });

  // 6. Testar responsividade - Mobile
  console.log('11. Testando responsividade mobile (375px)...');
  await page.setViewportSize({ width: 375, height: 812 });

  await page.goto('https://dumontcloud.com/');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/review_10_mobile_dashboard.png', fullPage: true });

  await page.goto('https://dumontcloud.com/machines');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/review_11_mobile_machines.png', fullPage: true });

  // 7. Testar responsividade - Tablet
  console.log('12. Testando responsividade tablet (768px)...');
  await page.setViewportSize({ width: 768, height: 1024 });

  await page.goto('https://dumontcloud.com/');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/review_12_tablet_dashboard.png', fullPage: true });

  await page.goto('https://dumontcloud.com/machines');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/review_13_tablet_machines.png', fullPage: true });

  // Voltar para desktop
  await page.setViewportSize({ width: 1280, height: 720 });

  // Resumo de erros
  console.log('\n=== RESUMO ===');
  console.log(`Total de erros de console: ${consoleErrors.length}`);
  if (consoleErrors.length > 0) {
    console.log('Erros encontrados:');
    consoleErrors.forEach((err, i) => console.log(`  ${i+1}. ${err}`));
  }

  console.log('\nScreenshots salvos em /tmp/review_*.png');
});
