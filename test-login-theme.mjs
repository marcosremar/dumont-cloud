import { chromium } from 'playwright';
import fs from 'fs';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🔐 Acessando página de login...');
    await page.goto('https://dumontcloud.com/login', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    console.log('\n📊 Informações iniciais:');
    const html1 = await page.$('html');
    const darkClass1 = await html1.evaluate(el => el.classList.contains('dark'));
    console.log(`   Modo escuro ativo: ${darkClass1}`);

    // Procurar botão de tema
    const themeBtn = await page.$('button[aria-label*="Dark"], button[aria-label*="Mode"], button[aria-label*="Tema"]');
    console.log(`   Botão de tema encontrado: ${!!themeBtn}`);

    console.log('\n📸 Screenshot ANTES de clicar no tema:');
    await page.screenshot({ path: '/tmp/login-light.png', fullPage: true });
    console.log('   ✓ Salvo: /tmp/login-light.png');

    if (themeBtn) {
      console.log('\n🌙 Clicando no botão de tema...');
      await themeBtn.click();
      await page.waitForTimeout(1500);

      const html2 = await page.$('html');
      const darkClass2 = await html2.evaluate(el => el.classList.contains('dark'));
      console.log(`   Modo escuro após clique: ${darkClass2}`);

      const theme = await page.evaluate(() => localStorage.getItem('theme'));
      console.log(`   Theme em localStorage: ${theme}`);

      console.log('\n📸 Screenshot DEPOIS de clicar no tema:');
      await page.screenshot({ path: '/tmp/login-dark.png', fullPage: true });
      console.log('   ✓ Salvo: /tmp/login-dark.png');
    } else {
      console.log('\n❌ Botão de tema NÃO encontrado na página de login!');
    }

  } catch (error) {
    console.error('❌ Erro:', error.message);
  } finally {
    await browser.close();
  }
})();
