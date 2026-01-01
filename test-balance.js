const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Capturar logs do console
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[BALANCE') || text.includes('[DASHBOARD]')) {
      console.log('CONSOLE LOG:', text);
    }
  });

  try {
    console.log('1. Acessando página de login...');
    await page.goto('http://localhost:4892/login');

    console.log('2. Aguardando formulário de login carregar...');
    await page.waitForSelector('input[placeholder="seu@email.com"]', { timeout: 10000 });

    console.log('3. Fazendo login...');
    await page.fill('input[placeholder="seu@email.com"]', 'marcosremar@gmail.com');
    await page.fill('input[placeholder="••••••••"]', 'dumont123');
    await page.click('button[type="submit"]');

    console.log('4. Aguardando carregar o dashboard...');
    await page.waitForURL('**/app', { timeout: 10000 });
    await page.waitForTimeout(3000); // Aguardar balance carregar

    console.log('5. Verificando balance no header...');
    // Procurar pelo texto "VAST.ai" e pegar o valor ao lado
    const balanceText = await page.locator('text=VAST.ai').locator('..').locator('p').last().textContent();
    console.log('BALANCE NO HEADER:', balanceText);

    if (balanceText && balanceText.includes('-')) {
      console.log('✅ SUCCESS: Balance negativo está sendo exibido!');
    } else {
      console.log('❌ FAIL: Balance não está mostrando valor negativo');
    }

    await page.waitForTimeout(5000); // Manter aberto para ver

  } catch (error) {
    console.error('ERRO:', error.message);
  } finally {
    await browser.close();
  }
})();
