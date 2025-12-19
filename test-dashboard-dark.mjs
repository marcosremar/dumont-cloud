import { chromium } from 'playwright';
import fs from 'fs';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('1️⃣  Navegando para dashboard DEMO...');
    await page.goto('https://dumontcloud.com/demo-app', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    console.log('2️⃣  Ativando modo escuro (clicando botão tema)...');

    // Clicar no botão de tema (lua/sol)
    const themeBtn = await page.$('button[aria-label*="Dark"], button[aria-label*="Mode"], button[aria-label*="Tema"], button:has-text("🌙"), button:has-text("☀️")');

    if (themeBtn) {
      console.log('   ✓ Botão de tema encontrado, clicando...');
      await themeBtn.click();
      await page.waitForTimeout(1500);
    } else {
      // Tenta clicar usando JavaScript
      console.log('   ℹ️  Procurando botão por texto...');
      await page.evaluate(() => {
        const buttons = document.querySelectorAll('button');
        for (let btn of buttons) {
          if (btn.innerHTML.includes('Moon') || btn.innerHTML.includes('Sun') || btn.textContent.includes('🌙') || btn.textContent.includes('☀️')) {
            btn.click();
            break;
          }
        }
      });
      await page.waitForTimeout(1500);
    }

    console.log('3️⃣  Capturando screenshot do dashboard ESCURO...');
    const screenshotPath = '/tmp/dashboard-dark-screenshot.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`✅ Screenshot escuro salvo em: ${screenshotPath}`);
    console.log(`📸 Tamanho: ${fs.statSync(screenshotPath).size} bytes`);

    // Verificar se modo escuro está ativo
    const html = await page.$('html');
    const darkClass = await html.evaluate(el => el.classList.contains('dark'));
    console.log(`\n✨ Modo escuro ativo: ${darkClass}`);

    // Pegar tema do localStorage
    const themeFromStorage = await page.evaluate(() => localStorage.getItem('theme'));
    console.log(`💾 Tema salvo em localStorage: ${themeFromStorage}`);

  } catch (error) {
    console.error('❌ Erro:', error.message);
  } finally {
    await browser.close();
  }
})();
