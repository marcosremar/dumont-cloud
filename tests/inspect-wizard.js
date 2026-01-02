const { chromium } = require('@playwright/test');

(async () => {
  console.log('=== INSPEÇÃO DO WIZARD GPU ===\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Navegar para demo-app
    console.log('1. Navegando para http://localhost:4898/demo-app');
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 2. Tirar screenshot
    console.log('2. Capturando screenshot inicial...');
    await page.screenshot({ path: 'wizard-initial.png', fullPage: true });
    console.log('   ✓ Salvo: wizard-initial.png');

    // 3. Analisar elementos visíveis
    console.log('\n3. ELEMENTOS VISÍVEIS NA PÁGINA:');

    // Títulos
    const headings = await page.locator('h1, h2, h3').all();
    console.log('\n   Títulos:');
    for (const h of headings) {
      if (await h.isVisible()) {
        const text = await h.textContent();
        const tag = await h.evaluate(el => el.tagName);
        console.log(`   - ${tag}: "${text?.trim()}"`);
      }
    }

    // Botões
    const buttons = await page.locator('button').all();
    console.log(`\n   Botões (${buttons.length} total):`);
    for (let i = 0; i < Math.min(buttons.length, 30); i++) {
      if (await buttons[i].isVisible()) {
        const text = await buttons[i].textContent();
        const classes = await buttons[i].getAttribute('class');
        console.log(`   ${i + 1}. "${text?.trim()}"`);
        if (classes?.includes('primary') || classes?.includes('selected')) {
          console.log(`      Classes: ${classes}`);
        }
      }
    }

    // 4. Procurar especificamente por botões de região
    console.log('\n4. PROCURANDO BOTÕES DE REGIÃO:');

    const regionChecks = [
      { name: 'EUA', locator: page.locator('button:has-text("EUA")') },
      { name: 'USA', locator: page.locator('button:has-text("USA")') },
      { name: 'Europa', locator: page.locator('button:has-text("Europa")') },
      { name: 'Ásia', locator: page.locator('button:has-text("Ásia")') },
      { name: 'América do Sul', locator: page.locator('button:has-text("América do Sul")') },
    ];

    for (const check of regionChecks) {
      const count = await check.locator.count();
      const visible = count > 0 && await check.locator.first().isVisible().catch(() => false);
      console.log(`   ${check.name}: ${count} encontrado(s), visível: ${visible}`);
    }

    // 5. Verificar se há botão "Buscar Máquinas"
    console.log('\n5. PROCURANDO BOTÃO DE ABERTURA DO WIZARD:');
    const searchButtons = [
      { name: 'Buscar Máquinas', locator: page.locator('button:has-text("Buscar Máquinas")') },
      { name: 'Buscar', locator: page.locator('button:has-text("Buscar")') },
      { name: 'Nova Máquina', locator: page.locator('button:has-text("Nova Máquina")') },
      { name: 'Criar', locator: page.locator('button:has-text("Criar")') },
    ];

    let wizardOpened = false;
    for (const btn of searchButtons) {
      const count = await btn.locator.count();
      if (count > 0) {
        console.log(`   ✓ Encontrado: "${btn.name}"`);
        if (!wizardOpened) {
          console.log(`   → Clicando em "${btn.name}"...`);
          await btn.locator.first().click();
          await page.waitForTimeout(2000);
          await page.screenshot({ path: 'wizard-after-click.png', fullPage: true });
          console.log('   ✓ Salvo: wizard-after-click.png');
          wizardOpened = true;
        }
      }
    }

    // 6. Após clicar, verificar novamente os botões de região
    if (wizardOpened) {
      console.log('\n6. VERIFICANDO BOTÕES DE REGIÃO APÓS ABRIR WIZARD:');

      for (const check of regionChecks) {
        const count = await check.locator.count();
        const visible = count > 0 && await check.locator.first().isVisible().catch(() => false);
        console.log(`   ${check.name}: ${count} encontrado(s), visível: ${visible}`);

        if (visible) {
          const rect = await check.locator.first().boundingBox();
          console.log(`      Posição: x=${rect?.x}, y=${rect?.y}, w=${rect?.width}, h=${rect?.height}`);
        }
      }

      // 7. Tentar clicar em EUA
      const euaButton = page.locator('button:has-text("EUA")').or(page.locator('button:has-text("USA")'));
      if (await euaButton.count() > 0) {
        console.log('\n7. CLICANDO EM BOTÃO EUA:');
        await euaButton.first().click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: 'wizard-after-eua.png', fullPage: true });
        console.log('   ✓ Salvo: wizard-after-eua.png');

        // Verificar se há indicador de seleção
        const selected = page.locator('[class*="selected"], [aria-pressed="true"], text=/✓|selecionado/i');
        const selectedCount = await selected.count();
        console.log(`   Indicadores de seleção: ${selectedCount} encontrado(s)`);

        // 8. Procurar botão Próximo
        console.log('\n8. PROCURANDO BOTÃO PRÓXIMO:');
        const nextButtons = [
          { name: 'Próximo', locator: page.locator('button:has-text("Próximo")') },
          { name: 'Next', locator: page.locator('button:has-text("Next")') },
          { name: 'Continuar', locator: page.locator('button:has-text("Continuar")') },
        ];

        for (const btn of nextButtons) {
          const count = await btn.locator.count();
          if (count > 0) {
            const isDisabled = await btn.locator.first().isDisabled();
            console.log(`   ${btn.name}: ${count} encontrado(s), desabilitado: ${isDisabled}`);

            if (!isDisabled) {
              console.log(`   → Clicando em "${btn.name}"...`);
              await btn.locator.first().click();
              await page.waitForTimeout(1000);
              await page.screenshot({ path: 'wizard-step2.png', fullPage: true });
              console.log('   ✓ Salvo: wizard-step2.png');

              // Verificar se avançou para Step 2
              const step2 = page.locator('text=/step 2|passo 2|etapa 2/i');
              const step2Count = await step2.count();
              console.log(`   Indicadores de Step 2: ${step2Count} encontrado(s)`);
              break;
            }
          }
        }
      }
    }

    // 9. Salvar HTML final
    console.log('\n9. SALVANDO HTML DA PÁGINA:');
    const html = await page.content();
    const fs = require('fs');
    fs.writeFileSync('wizard-page.html', html);
    console.log('   ✓ Salvo: wizard-page.html');

    console.log('\n=== INSPEÇÃO CONCLUÍDA ===');
    console.log('\nArquivos gerados:');
    console.log('  - wizard-initial.png');
    console.log('  - wizard-after-click.png');
    console.log('  - wizard-after-eua.png');
    console.log('  - wizard-step2.png');
    console.log('  - wizard-page.html');

  } catch (error) {
    console.error('\n❌ ERRO:', error.message);
  } finally {
    await browser.close();
  }
})();
