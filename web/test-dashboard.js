import { chromium } from '@playwright/test';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Acessando http://localhost:3001...');
  await page.goto('http://localhost:3001', { waitUntil: 'networkidle', timeout: 30000 });

  // Verificar se precisa fazer login
  const loginButton = await page.locator('button:has-text("Login")').count();

  if (loginButton > 0) {
    console.log('Página de login detectada. Fazendo login com demo/demo...');
    await page.fill('input[type="text"]', 'demo');
    await page.fill('input[type="password"]', 'demo');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(2000);
  }

  // Esperar o Dashboard carregar
  await page.waitForTimeout(3000);

  // Screenshot inicial do Dashboard
  console.log('Tirando screenshot inicial do Dashboard...');
  await page.screenshot({ path: 'screenshot-dashboard-inicial.png', fullPage: true });

  // Tentar clicar no botão Europa
  console.log('Tentando clicar em Europa...');
  try {
    const europa = page.locator('button:has-text("Europa")');
    await europa.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'screenshot-europa.png', fullPage: true });
    console.log('✓ Screenshot Europa salvo!');
  } catch (e) {
    console.log('Erro ao clicar em Europa:', e.message);
  }

  // Tentar clicar no botão EUA
  console.log('Tentando clicar em EUA...');
  try {
    const eua = page.locator('button:has-text("EUA")');
    await eua.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'screenshot-eua.png', fullPage: true });
    console.log('✓ Screenshot EUA salvo!');
  } catch (e) {
    console.log('Erro ao clicar em EUA:', e.message);
  }

  // Tentar clicar no botão Ásia
  console.log('Tentando clicar em Ásia...');
  try {
    const asia = page.locator('button:has-text("Ásia")');
    await asia.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'screenshot-asia.png', fullPage: true });
    console.log('✓ Screenshot Ásia salvo!');
  } catch (e) {
    console.log('Erro ao clicar em Ásia:', e.message);
  }

  // Tentar clicar no botão América do Sul
  console.log('Tentando clicar em América do Sul...');
  try {
    const americaSul = page.locator('button:has-text("América do Sul")');
    await americaSul.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'screenshot-america-sul.png', fullPage: true });
    console.log('✓ Screenshot América do Sul salvo!');
  } catch (e) {
    console.log('Erro ao clicar em América do Sul:', e.message);
  }

  // Tentar clicar no botão Global
  console.log('Tentando clicar em Global...');
  try {
    const global = page.locator('button:has-text("Global")');
    await global.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'screenshot-global.png', fullPage: true });
    console.log('✓ Screenshot Global salvo!');
  } catch (e) {
    console.log('Erro ao clicar em Global:', e.message);
  }

  console.log('\n✅ Screenshots salvos com sucesso!');
  console.log('- screenshot-dashboard-inicial.png');
  console.log('- screenshot-eua.png');
  console.log('- screenshot-europa.png');
  console.log('- screenshot-asia.png');
  console.log('- screenshot-america-sul.png');
  console.log('- screenshot-global.png');

  await browser.close();
})();
