import { chromium } from '@playwright/test';
import fs from 'fs';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Acessando http://localhost:3001...');
  await page.goto('http://localhost:3001', { waitUntil: 'networkidle', timeout: 30000 });

  // Fazer login
  const loginButton = await page.locator('button:has-text("Login")').count();
  if (loginButton > 0) {
    console.log('Fazendo login...');
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', 'admin');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(3000);
  }

  // Capturar screenshot
  console.log('Capturando screenshot...');
  await page.screenshot({ path: 'dashboard-real.png', fullPage: true });

  // Salvar HTML
  const html = await page.content();
  fs.writeFileSync('dashboard-html.txt', html);

  console.log('✅ Screenshot salvo: dashboard-real.png');
  console.log('✅ HTML salvo: dashboard-html.txt');

  await browser.close();
})();
