import { chromium } from 'playwright';
import fs from 'fs';

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('1️⃣  Navegando para dashboard DEMO (sem login)...');
    await page.goto('https://dumontcloud.com/demo-app', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    console.log('2️⃣  Capturando screenshot do dashboard...');
    const screenshotPath = '/tmp/dashboard-screenshot.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`✅ Screenshot salvo em: ${screenshotPath}`);
    console.log(`📸 Tamanho: ${fs.statSync(screenshotPath).size} bytes`);

    console.log('\n📊 Informações da página:');
    const title = await page.title();
    const url = page.url();
    console.log(`   Título: ${title}`);
    console.log(`   URL: ${url}`);

    // Verificar se tema está funcionando
    const html = await page.$('html');
    const darkClass = await html.evaluate(el => el.classList.contains('dark'));
    console.log(`   Classe 'dark' no HTML: ${darkClass}`);

    // Procurar pelo botão de tema
    const themeBtn = await page.$('button[aria-label*="Dark"], button[aria-label*="Mode"], button[aria-label*="Tema"]');
    console.log(`   Botão de tema encontrado: ${!!themeBtn}`);

    // Verificar cores do fundo
    const bodyBg = await page.evaluate(() => {
      return window.getComputedStyle(document.body).backgroundColor;
    });
    console.log(`   Cor de fundo do body: ${bodyBg}`);

    // Contar elementos
    const headers = await page.$$('header');
    const cards = await page.$$('[class*="card"]');
    console.log(`   Headers: ${headers.length}`);
    console.log(`   Cards: ${cards.length}`);

    console.log('\n✅ Teste concluído!');

  } catch (error) {
    console.error('❌ Erro:', error.message);
    console.error(error);
  } finally {
    await browser.close();
  }
})();
