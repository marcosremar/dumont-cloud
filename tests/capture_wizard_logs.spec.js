const { test } = require('@playwright/test');

test.use({ storageState: { cookies: [], origins: [] } }); // Sem auth

test('Capturar logs do wizard ao clicar em Próximo', async ({ page }) => {
  // Capturar TODOS os console.log
  const logs = [];
  page.on('console', msg => {
    const text = msg.text();
    logs.push({
      type: msg.type(),
      text: text,
      timestamp: new Date().toISOString()
    });
    console.log(`[CONSOLE-${msg.type().toUpperCase()}] ${text}`);
  });

  // Navegar para demo-app
  console.log('\n=== NAVEGANDO PARA /demo-app ===');
  await page.goto('http://localhost:4898/demo-app');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  console.log('\n=== CLICANDO EM "EUA" ===');
  // Procurar botão EUA
  const usaButton = page.locator('text="EUA"').first();
  await usaButton.waitFor({ state: 'visible', timeout: 5000 });
  await usaButton.click();
  await page.waitForTimeout(1000);

  console.log('\n=== CLICANDO EM "PRÓXIMO" ===');
  // Procurar botão Próximo
  const nextButton = page.locator('button:has-text("Próximo")').first();
  await nextButton.waitFor({ state: 'visible', timeout: 5000 });
  await nextButton.click();
  await page.waitForTimeout(3000);

  console.log('\n=== LOGS CAPTURADOS ===');
  const handleNextLogs = logs.filter(log => log.text.includes('[handleNext]'));
  console.log('\nLogs com [handleNext]:');
  handleNextLogs.forEach(log => {
    console.log(`  ${log.text}`);
  });

  console.log('\nTODOS os logs (últimos 50):');
  logs.slice(-50).forEach(log => {
    console.log(`  [${log.type}] ${log.text}`);
  });

  // Tirar screenshot final
  await page.screenshot({ path: '/tmp/wizard_after_next.png', fullPage: true });
  console.log('\nScreenshot salvo em: /tmp/wizard_after_next.png');
});
