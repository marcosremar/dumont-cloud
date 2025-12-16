const { test, expect } = require('@playwright/test');

test('Screenshot VS Code admin page', async ({ page }) => {
  test.setTimeout(60000);

  console.log('1. Acessando VS Code admin...');
  await page.goto('https://dumontcloud.com/admin/vscode/');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/screenshot_vscode_1.png', fullPage: true });
  console.log('Screenshot 1: VS Code page saved');

  // Verificar se tem login do code-server
  const hasPasswordField = await page.locator('input[type="password"]').count();
  console.log('Has password field:', hasPasswordField);

  if (hasPasswordField > 0) {
    console.log('2. Fazendo login no code-server...');
    await page.locator('input[type="password"]').fill('dumont2024');
    // Pressionar Enter para submeter o form
    await page.keyboard.press('Enter');
    await page.waitForTimeout(10000);
    await page.screenshot({ path: '/tmp/screenshot_vscode_2.png', fullPage: true });
    console.log('Screenshot 2: After code-server login saved');
  }
});
