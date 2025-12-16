const { test, expect } = require('@playwright/test');

test('Screenshot machines page', async ({ page }) => {
  test.setTimeout(60000);

  // Capturar erros do console
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('CONSOLE ERROR:', msg.text());
    }
  });

  page.on('pageerror', err => {
    console.log('PAGE ERROR:', err.message);
  });

  console.log('1. Acessando página de login...');
  // Add cache bust to force fresh content
  await page.goto('https://dumontcloud.com/?t=' + Date.now());
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/screenshot_1_login.png' });
  console.log('Screenshot 1: Login page saved');

  // Fazer login usando seletores da versão SnapGPU (servidor atual)
  console.log('2. Fazendo login...');
  await page.locator('input[placeholder="Usuario"]').fill('marcosremar@gmail.com');
  await page.locator('input[placeholder="Senha"]').fill('marcos123');
  await page.locator('button[type="submit"]').click();

  // Aguardar navegação
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/screenshot_2_after_login.png' });
  console.log('Screenshot 2: After login saved');

  // Navegar para /machines
  console.log('3. Navegando para /machines...');
  await page.goto('https://dumontcloud.com/machines');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/screenshot_3_machines.png', fullPage: true });
  console.log('Screenshot 3: Machines page saved');
});
