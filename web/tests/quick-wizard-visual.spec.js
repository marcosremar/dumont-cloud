import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('Quick wizard visual check', async ({ page }) => {
  const screenshotsDir = path.join(__dirname, '..', 'screenshots');

  console.log('Acessando login...');
  await page.goto('http://localhost:4894/login');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(screenshotsDir, 'quick-01-login-page.png'), fullPage: true });
  console.log('Screenshot login salvo');

  // Verificar se auto_login funciona
  console.log('Tentando auto_login...');
  await page.goto('http://localhost:4894/login?auto_login=demo');
  await page.waitForTimeout(5000);
  await page.screenshot({ path: path.join(screenshotsDir, 'quick-02-after-autologin.png'), fullPage: true });
  console.log('Screenshot após auto_login salvo');

  const currentUrl = page.url();
  console.log(`URL atual: ${currentUrl}`);

  // Se ainda estiver no login, fazer login manual
  if (currentUrl.includes('/login')) {
    console.log('Auto-login não funcionou, fazendo login manual...');

    await page.fill('input[type="email"], input[name="email"]', 'demo@dumontcloud.com');
    await page.fill('input[type="password"], input[name="password"]', 'demo123');
    await page.click('button[type="submit"], button:has-text("Entrar")');
    await page.waitForTimeout(3000);

    await page.screenshot({ path: path.join(screenshotsDir, 'quick-03-after-manual-login.png'), fullPage: true });
  }

  console.log('Navegando para dashboard...');
  await page.goto('http://localhost:4894/app');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(screenshotsDir, 'quick-04-dashboard.png'), fullPage: true });

  console.log('Procurando por wizard/formulário...');
  const pageContent = await page.content();

  // Procurar por textos relacionados ao wizard
  const hasRegion = pageContent.includes('Região') || pageContent.includes('Region');
  const hasGPU = pageContent.includes('GPU');
  const hasWizard = pageContent.includes('Wizard') || pageContent.includes('Assistente');

  console.log(`Tem "Região": ${hasRegion}`);
  console.log(`Tem "GPU": ${hasGPU}`);
  console.log(`Tem "Wizard": ${hasWizard}`);

  // Clicar em qualquer botão de região/EUA
  const regionButtons = await page.$$('button, [role="button"]');
  console.log(`Total de botões encontrados: ${regionButtons.length}`);

  for (let i = 0; i < Math.min(regionButtons.length, 20); i++) {
    const text = await regionButtons[i].textContent();
    console.log(`Botão ${i}: ${text?.trim()}`);
  }

  await page.screenshot({ path: path.join(screenshotsDir, 'quick-05-final.png'), fullPage: true });
  console.log('Teste visual rápido concluído');
});
