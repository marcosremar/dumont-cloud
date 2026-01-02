/**
 * Teste DEBUG - Verificar clique em região EUA
 */

const { test, expect } = require('@playwright/test');

test('DEBUG: Clicar em EUA e verificar estado', async ({ page }) => {
  console.log('\n[1] Navegando para /demo-app');
  await page.goto('http://localhost:4898/demo-app');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  console.log('[2] Capturando console logs');
  const logs = [];
  page.on('console', msg => {
    const text = msg.text();
    logs.push(text);
    console.log(`  [CONSOLE] ${text}`);
  });

  console.log('[3] Procurando botão region-eua');
  const regionButton = page.locator('button[data-testid="region-eua"]');
  const isVisible = await regionButton.isVisible({ timeout: 5000 });
  console.log(`  Botão visível: ${isVisible}`);

  await page.screenshot({ path: 'test-results/debug-before-click.png', fullPage: true });

  console.log('[4] Clicando em região EUA (forçando disparo)');

  // Tentar múltiplas abordagens de click
  await regionButton.click({ force: true });
  await page.waitForTimeout(500);

  // Se ainda não funcionou, tentar via JavaScript
  await regionButton.evaluate(button => button.click());

  console.log('[5] Aguardando 3s para React atualizar estado');
  await page.waitForTimeout(3000);

  await page.screenshot({ path: 'test-results/debug-after-click.png', fullPage: true });

  console.log('[6] Verificando botão Próximo');
  const proximoButton = page.locator('button').filter({ hasText: 'Próximo' });
  const proximoVisible = await proximoButton.isVisible();
  const proximoEnabled = await proximoButton.isEnabled();

  console.log(`  Próximo visível: ${proximoVisible}`);
  console.log(`  Próximo habilitado: ${proximoEnabled}`);

  console.log('[7] Injetando script para ler React state');
  const reactState = await page.evaluate(() => {
    // Tentar acessar o elemento raiz do React
    const rootElement = document.querySelector('#root');
    if (rootElement && rootElement._reactRootContainer) {
      return { hasReactRoot: true };
    }

    // Procurar por elementos com data attributes que indiquem estado
    const wizardElement = document.querySelector('[data-wizard]');
    return {
      hasWizardElement: !!wizardElement,
      bodyHTML: document.body.innerHTML.substring(0, 500)
    };
  });

  console.log(`  React state: ${JSON.stringify(reactState, null, 2)}`);

  console.log('\n[8] Console logs capturados:');
  logs.forEach((log, idx) => {
    console.log(`  [${idx}] ${log}`);
  });

  // Assertion simples
  expect(proximoVisible).toBe(true);
});
