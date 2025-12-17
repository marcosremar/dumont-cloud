const { test, expect } = require('@playwright/test');

test('Full Feature Test - All Pages', async ({ page }) => {
  test.setTimeout(300000);

  // Capturar erros
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('CONSOLE ERROR:', msg.text());
    }
  });

  // ========================================
  // 1. LOGIN PAGE - Verificar logo
  // ========================================
  console.log('1. Testando página de Login...');
  await page.goto('https://dumontcloud.com/?t=' + Date.now());
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/final_01_login.png', fullPage: true });
  console.log('Screenshot: Login page');

  // Verificar se logo existe
  const logo = page.locator('.login-logo');
  const hasLogo = await logo.count() > 0;
  console.log(`Logo presente: ${hasLogo}`);

  // Login
  await page.locator('.form-group input[type="text"]').fill('marcosremar@gmail.com');
  await page.locator('.form-group input[type="password"]').fill('marcos123');
  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(4000);

  // ========================================
  // 2. DASHBOARD - Verificar Wizard/Avançado
  // ========================================
  console.log('2. Testando Dashboard...');
  await page.screenshot({ path: '/tmp/final_02_dashboard.png', fullPage: true });

  // Verificar toggle Wizard/Avançado
  const wizardBtn = page.locator('button:has-text("Wizard")');
  const advancedBtn = page.locator('button:has-text("Avançado")');

  if (await advancedBtn.isVisible()) {
    console.log('Toggle Wizard/Avançado encontrado!');
    await advancedBtn.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/final_03_dashboard_advanced.png', fullPage: true });
    console.log('Screenshot: Dashboard modo Avançado');

    // Voltar para Wizard
    await wizardBtn.click();
    await page.waitForTimeout(500);
  }

  // Testar seleção de região
  const europaTab = page.locator('button:has-text("Europa")');
  if (await europaTab.isVisible()) {
    await europaTab.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/final_04_dashboard_europa.png', fullPage: true });
    console.log('Screenshot: Dashboard região Europa');
  }

  // ========================================
  // 3. MACHINES PAGE
  // ========================================
  console.log('3. Testando Machines...');
  await page.goto('https://dumontcloud.com/machines');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/final_05_machines.png', fullPage: true });
  console.log('Screenshot: Machines page');

  // Verificar se tem máquina e testar botão Pausar (AlertDialog)
  const pauseBtn = page.locator('button:has-text("Pausar Máquina")').first();
  if (await pauseBtn.isVisible()) {
    console.log('Botão Pausar encontrado, testando AlertDialog...');
    await pauseBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/final_06_machines_pause_dialog.png', fullPage: true });
    console.log('Screenshot: AlertDialog de confirmação');

    // Cancelar
    const cancelBtn = page.locator('button:has-text("Cancelar")');
    if (await cancelBtn.isVisible()) {
      await cancelBtn.click();
      await page.waitForTimeout(300);
    }
  }

  // Verificar uptime
  const uptimeElement = page.locator('text=/UPTIME/i');
  const hasUptime = await uptimeElement.count() > 0;
  console.log(`Uptime visível: ${hasUptime}`);

  // ========================================
  // 4. SETTINGS PAGE - Verificar máscaras
  // ========================================
  console.log('4. Testando Settings...');
  await page.goto('https://dumontcloud.com/settings');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/final_07_settings.png', fullPage: true });
  console.log('Screenshot: Settings page');

  // Verificar botões de show/hide
  const eyeButtons = page.locator('.secret-toggle-btn');
  const eyeCount = await eyeButtons.count();
  console.log(`Botões show/hide encontrados: ${eyeCount}`);

  if (eyeCount > 0) {
    // Clicar no primeiro para mostrar
    await eyeButtons.first().click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: '/tmp/final_08_settings_show_key.png', fullPage: true });
    console.log('Screenshot: Settings com API key visível');
  }

  // Testar botão de notificação (Toast)
  const testNotifBtn = page.locator('button:has-text("Testar Notificação")');
  if (await testNotifBtn.isVisible()) {
    await testNotifBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/final_09_settings_toast.png', fullPage: true });
    console.log('Screenshot: Toast de notificação');
  }

  // ========================================
  // 5. METRICS PAGE - Verificar estado vazio
  // ========================================
  console.log('5. Testando Metrics...');
  await page.goto('https://dumontcloud.com/metrics');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/final_10_metrics.png', fullPage: true });
  console.log('Screenshot: Metrics page');

  // ========================================
  // 6. MOBILE VIEW - Verificar menu hamburger
  // ========================================
  console.log('6. Testando Mobile View...');
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('https://dumontcloud.com/');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/final_11_mobile_dashboard.png', fullPage: true });
  console.log('Screenshot: Mobile Dashboard');

  // Verificar hamburger
  const hamburgerBtn = page.locator('.mobile-menu-button');
  if (await hamburgerBtn.isVisible()) {
    console.log('Menu hamburger encontrado!');
    await hamburgerBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/final_12_mobile_menu_open.png', fullPage: true });
    console.log('Screenshot: Mobile menu aberto');

    // Verificar links no menu
    const menuLinks = page.locator('.mobile-menu-link');
    const linkCount = await menuLinks.count();
    console.log(`Links no menu mobile: ${linkCount}`);

    // Fechar menu
    const overlay = page.locator('.mobile-menu-overlay');
    if (await overlay.isVisible()) {
      await overlay.click();
      await page.waitForTimeout(300);
    }
  } else {
    console.log('Menu hamburger NÃO encontrado!');
  }

  // Mobile Machines
  await page.goto('https://dumontcloud.com/machines');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/final_13_mobile_machines.png', fullPage: true });
  console.log('Screenshot: Mobile Machines');

  // Mobile Settings
  await page.goto('https://dumontcloud.com/settings');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/final_14_mobile_settings.png', fullPage: true });
  console.log('Screenshot: Mobile Settings');

  // ========================================
  // 7. TABLET VIEW
  // ========================================
  console.log('7. Testando Tablet View...');
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto('https://dumontcloud.com/');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/final_15_tablet_dashboard.png', fullPage: true });
  console.log('Screenshot: Tablet Dashboard');

  console.log('\n========================================');
  console.log('TESTE COMPLETO!');
  console.log('========================================');
});
