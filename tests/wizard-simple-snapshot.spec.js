const { test, expect } = require('@playwright/test');

test('Wizard GPU - Snapshot e Navegação', async ({ page }) => {
  console.log('=== TESTE DO WIZARD GPU - SNAPSHOT ===');

  // 1. Navegar para demo-app
  console.log('1. Navegando para http://localhost:4898/demo-app');
  await page.goto('http://localhost:4898/demo-app');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // 2. Tirar screenshot da página inicial
  console.log('2. Tirando screenshot da página inicial');
  await page.screenshot({ path: 'wizard-initial.png', fullPage: true });

  // 3. Buscar por botões de região
  console.log('3. Procurando botões de região...');

  const regionButtons = await page.locator('button').all();
  console.log(`Encontrados ${regionButtons.length} botões na página`);

  for (let i = 0; i < Math.min(regionButtons.length, 20); i++) {
    const text = await regionButtons[i].textContent();
    const isVisible = await regionButtons[i].isVisible();
    console.log(`  Botão ${i}: "${text?.trim()}" (visível: ${isVisible})`);
  }

  // 4. Procurar especificamente por botões de região
  const usaButton = page.locator('button:has-text("EUA")').or(page.locator('button:has-text("USA")'));
  const europaButton = page.locator('button:has-text("Europa")');
  const asiaButton = page.locator('button:has-text("Ásia")');
  const sulButton = page.locator('button:has-text("América do Sul")');

  console.log('4. Verificando botões de região:');
  console.log(`  EUA/USA: ${await usaButton.count()} encontrado(s)`);
  console.log(`  Europa: ${await europaButton.count()} encontrado(s)`);
  console.log(`  Ásia: ${await asiaButton.count()} encontrado(s)`);
  console.log(`  América do Sul: ${await sulButton.count()} encontrado(s)`);

  // 5. Verificar se há algum wizard ou modal aberto
  const headings = await page.locator('h1, h2, h3').all();
  console.log('5. Títulos encontrados:');
  for (const heading of headings) {
    const text = await heading.textContent();
    const isVisible = await heading.isVisible();
    if (isVisible) {
      console.log(`  - "${text?.trim()}"`);
    }
  }

  // 6. Verificar se há botão "Buscar Máquinas" ou similar
  const searchButton = page.locator('button:has-text("Buscar")');
  console.log(`6. Botão "Buscar": ${await searchButton.count()} encontrado(s)`);

  if (await searchButton.count() > 0) {
    console.log('7. Clicando em "Buscar Máquinas"...');
    await searchButton.first().click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'wizard-after-buscar.png', fullPage: true });

    // Verificar novamente os botões de região após clicar em Buscar
    console.log('8. Verificando botões de região após Buscar:');
    console.log(`  EUA/USA: ${await usaButton.count()} encontrado(s)`);
    console.log(`  Europa: ${await europaButton.count()} encontrado(s)`);
    console.log(`  Ásia: ${await asiaButton.count()} encontrado(s)`);
    console.log(`  América do Sul: ${await sulButton.count()} encontrado(s)`);

    // Se encontrou EUA, tentar clicar
    if (await usaButton.count() > 0) {
      console.log('9. Clicando em botão EUA...');
      await usaButton.first().click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: 'wizard-after-eua.png', fullPage: true });

      // Verificar se badge de seleção apareceu
      const selectedBadge = page.locator('text=/selecionado|selected|✓/i');
      console.log(`Badge de seleção: ${await selectedBadge.count()} encontrado(s)`);

      // Procurar botão "Próximo"
      const nextButton = page.locator('button:has-text("Próximo")').or(page.locator('button:has-text("Next")'));
      console.log(`Botão Próximo: ${await nextButton.count()} encontrado(s)`);

      if (await nextButton.count() > 0) {
        console.log('10. Clicando em "Próximo"...');
        await nextButton.first().click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: 'wizard-step2.png', fullPage: true });

        // Verificar se avançou para Step 2
        const step2Indicator = page.locator('text=/step 2|passo 2/i');
        console.log(`Indicador Step 2: ${await step2Indicator.count()} encontrado(s)`);
      }
    }
  }

  // 7. Capturar HTML completo para análise
  const html = await page.content();
  const fs = require('fs');
  fs.writeFileSync('wizard-page.html', html);
  console.log('HTML completo salvo em wizard-page.html');

  console.log('\n=== TESTE CONCLUÍDO ===');
  console.log('Screenshots salvos:');
  console.log('  - wizard-initial.png');
  console.log('  - wizard-after-buscar.png (se botão Buscar foi encontrado)');
  console.log('  - wizard-after-eua.png (se botão EUA foi encontrado)');
  console.log('  - wizard-step2.png (se avançou para Step 2)');
});
