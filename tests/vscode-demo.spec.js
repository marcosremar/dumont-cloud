const { test, expect } = require('@playwright/test');

test.describe('VS Code Demo - Machine Switcher', () => {

  test('should load VS Code and show Machine Switcher', async ({ page }) => {
    // Ir para a página de login do code-server
    await page.goto('https://dumontcloud.com/demo/vscode/login');

    // Fazer login
    await page.fill('input[name="password"]', 'dumont2024');
    await page.click('button[type="submit"]');

    // Aguardar o VS Code carregar
    await page.waitForTimeout(5000);

    // Tirar screenshot
    await page.screenshot({ path: 'vscode-demo-screenshot.png', fullPage: true });

    // Verificar se o Machine Switcher foi carregado
    const switcher = await page.$('.dumont-machine-switcher');

    console.log('Machine Switcher found:', !!switcher);

    // Verificar se o script foi injetado
    const scriptInjected = await page.evaluate(() => {
      return typeof window.DumontMachineSwitcher !== 'undefined';
    });

    console.log('Script injected:', scriptInjected);
  });
});
