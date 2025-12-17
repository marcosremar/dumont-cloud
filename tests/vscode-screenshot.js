const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Ir para login
  await page.goto('https://dumontcloud.com/demo/vscode/login');

  // Fazer login
  await page.fill('input[type="password"]', 'dumont2024');
  await page.click('input[type="submit"]');

  // Aguardar VS Code carregar
  await page.waitForTimeout(8000);

  // Tirar screenshot
  await page.screenshot({ path: '/tmp/vscode-with-switcher.png', fullPage: true });

  // Verificar se o script foi injetado
  const hasSwitcher = await page.evaluate(() => {
    return document.querySelector('.dumont-machine-switcher') !== null;
  });

  console.log('Machine Switcher present:', hasSwitcher);

  // Verificar se o script global existe
  const hasGlobal = await page.evaluate(() => {
    return typeof window.DumontMachineSwitcher !== 'undefined';
  });

  console.log('Global DumontMachineSwitcher:', hasGlobal);

  // Listar scripts carregados
  const scripts = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  });
  console.log('Loaded scripts:', scripts.filter(s => s.includes('machine')));

  await browser.close();
})();
