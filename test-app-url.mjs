import { chromium } from 'playwright';
import fs from 'fs';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🔗 Acessando: https://dumontcloud.com/app');
    await page.goto('https://dumontcloud.com/app', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    console.log('\n📊 Informações da página:');
    const title = await page.title();
    const url = page.url();
    console.log(`   Título: ${title}`);
    console.log(`   URL final: ${url}`);

    // Verificar se está em login
    const isLogin = url.includes('/login');
    console.log(`   Redirecionado para login: ${isLogin}`);

    // Verificar classe dark
    const html = await page.$('html');
    const darkClass = await html.evaluate(el => el.classList.contains('dark'));
    console.log(`   Modo escuro ativo: ${darkClass}`);

    // Verificar fundo
    const bodyBg = await page.evaluate(() => {
      return window.getComputedStyle(document.body).backgroundColor;
    });
    console.log(`   Cor fundo body: ${bodyBg}`);

    // Verificar se tem conteúdo
    const mainContent = await page.$('main');
    console.log(`   <main> encontrado: ${!!mainContent}`);

    console.log('\n📸 Capturando screenshot da URL /app...');
    const screenshotPath = '/tmp/app-url-screenshot.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`✅ Screenshot salvo: ${screenshotPath}`);
    console.log(`📏 Tamanho: ${fs.statSync(screenshotPath).size} bytes`);

  } catch (error) {
    console.error('❌ Erro:', error.message);
  } finally {
    await browser.close();
  }
})();
