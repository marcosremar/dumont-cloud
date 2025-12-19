import { chromium } from 'playwright';
import fs from 'fs';

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('1️⃣  Navegando para o login...');
    await page.goto('https://dumontcloud.com/login', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    console.log('2️⃣  Procurando campos de login...');
    const userField = await page.$('input[placeholder*="email"], input[placeholder*="username"], input[type="text"]');
    const passField = await page.$('input[type="password"]');

    if (userField && passField) {
      console.log('3️⃣  Preenchendo credenciais...');
      await userField.fill('demo@dumont.cloud');
      await passField.fill('test123');

      console.log('4️⃣  Clicando em login...');
      const loginBtn = await page.$('button:has-text("Login"), button:has-text("Entrar"), button[type="submit"]');
      if (loginBtn) {
        await loginBtn.click();
      }

      await page.waitForTimeout(3000);
    }

    console.log('5️⃣  Navegando para dashboard...');
    await page.goto('https://dumontcloud.com/app', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    console.log('6️⃣  Capturando screenshot do dashboard...');
    const screenshotPath = '/tmp/dashboard-screenshot.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`✅ Screenshot salvo em: ${screenshotPath}`);

    console.log('\n📊 Informações da página:');
    const title = await page.title();
    const url = page.url();
    console.log(`   Título: ${title}`);
    console.log(`   URL: ${url}`);

    // Verificar se tema está funcionando
    const html = await page.$('html');
    const darkClass = await html.evaluate(el => el.classList.contains('dark'));
    console.log(`   Modo escuro ativo: ${darkClass}`);

    // Pegar conteúdo HTML para análise
    const content = await page.content();
    const hasThemeCode = content.includes('toggleTheme') || content.includes('useTheme');
    console.log(`   Código de tema presente: ${hasThemeCode}`);

  } catch (error) {
    console.error('❌ Erro:', error.message);
  } finally {
    await browser.close();
  }
})();
