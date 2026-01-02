import { test } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('Wizard GPU usando DevBar credentials', async ({ page }) => {
  const screenshotsDir = path.join(__dirname, '..', 'screenshots');

  console.log('=== TESTE WIZARD COM DEVBAR ===\n');

  // 1. Ir para login
  console.log('1. Navegando para login...');
  await page.goto('http://localhost:4894/login');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2000);

  await page.screenshot({
    path: path.join(screenshotsDir, 'devbar-01-login.png'),
    fullPage: true
  });

  // 2. Preencher usando os valores da DevBar (que aparecem no snapshot)
  // Email: marcosremar@gmail.com
  // Senha: dumont123

  console.log('2. Preenchendo credenciais...');

  // Tentar diferentes formas de encontrar o input
  const emailSelectors = [
    'input[placeholder*="email"]',
    'input[placeholder*="Email"]',
    'input[placeholder*="seu@"]',
    'input[name="email"]',
    'input[id="email"]',
    'textbox'
  ];

  let emailFilled = false;
  for (const selector of emailSelectors) {
    try {
      const input = page.locator(selector).first();
      if (await input.isVisible({ timeout: 1000 })) {
        console.log(`Usando seletor de email: ${selector}`);
        await input.fill('marcosremar@gmail.com');
        emailFilled = true;
        break;
      }
    } catch (e) {
      // Continuar
    }
  }

  console.log(`Email preenchido: ${emailFilled ? '✅' : '❌'}`);

  const passwordSelectors = [
    'input[type="password"]',
    'input[placeholder*="••"]',
    'input[placeholder*="senha"]',
    'input[name="password"]',
    'input[id="password"]'
  ];

  let passwordFilled = false;
  for (const selector of passwordSelectors) {
    try {
      const input = page.locator(selector).first();
      if (await input.isVisible({ timeout: 1000 })) {
        console.log(`Usando seletor de senha: ${selector}`);
        await input.fill('dumont123');
        passwordFilled = true;
        break;
      }
    } catch (e) {
      // Continuar
    }
  }

  console.log(`Senha preenchida: ${passwordFilled ? '✅' : '❌'}`);

  await page.screenshot({
    path: path.join(screenshotsDir, 'devbar-02-filled.png'),
    fullPage: true
  });

  // 3. Clicar em Entrar
  console.log('\n3. Clicando em Entrar...');
  const loginBtn = page.locator('button:has-text("Entrar")').first();
  await loginBtn.click();
  await page.waitForTimeout(5000);

  await page.screenshot({
    path: path.join(screenshotsDir, 'devbar-03-after-login.png'),
    fullPage: true
  });

  const currentUrl = page.url();
  console.log(`URL após login: ${currentUrl}`);

  // 4. Navegar para /app se não redirecionou
  if (!currentUrl.includes('/app')) {
    console.log('Navegando manualmente para /app...');
    await page.goto('http://localhost:4894/app');
    await page.waitForTimeout(3000);
  }

  await page.screenshot({
    path: path.join(screenshotsDir, 'devbar-04-dashboard.png'),
    fullPage: true
  });

  // 5. Salvar HTML para análise
  console.log('\n5. Salvando HTML da página...');
  const html = await page.content();
  fs.writeFileSync(
    path.join(screenshotsDir, 'devbar-dashboard.html'),
    html
  );

  // 6. Procurar por elementos do wizard
  console.log('\n6. Procurando elementos do wizard...');

  const wizardElements = {
    'Região/Region': html.includes('Região') || html.includes('Region'),
    'EUA/USA': html.includes('EUA') || html.includes('USA'),
    'GPU': html.includes('GPU'),
    'Wizard': html.includes('Wizard') || html.includes('Assistente'),
    'Próximo/Next': html.includes('Próximo') || html.includes('Next'),
    'RTX': /RTX\s*\d{4}/i.test(html),
    'Preço ($)': /\$\s*[\d.]+/i.test(html)
  };

  console.log('Elementos encontrados:');
  Object.entries(wizardElements).forEach(([key, found]) => {
    console.log(`  ${key}: ${found ? '✅' : '❌'}`);
  });

  // 7. Contar botões visíveis
  console.log('\n7. Analisando botões visíveis...');
  const buttons = page.locator('button');
  const buttonCount = await buttons.count();
  console.log(`Total de botões: ${buttonCount}`);

  // Mostrar primeiros 15 botões
  for (let i = 0; i < Math.min(buttonCount, 15); i++) {
    const btn = buttons.nth(i);
    const text = await btn.textContent();
    const isVisible = await btn.isVisible();
    if (isVisible && text?.trim()) {
      console.log(`  [${i}] ${text.trim().substring(0, 50)}`);
    }
  }

  // 8. Screenshot final
  await page.screenshot({
    path: path.join(screenshotsDir, 'devbar-05-final.png'),
    fullPage: true
  });

  console.log('\n=== TESTE CONCLUÍDO ===');
  console.log(`Screenshots em: ${screenshotsDir}`);
});
