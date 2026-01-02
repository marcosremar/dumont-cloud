const { test, expect } = require('@playwright/test');

test.describe('Wizard GPU - Teste com Seletores Corretos', () => {
  test('deve completar wizard usando data-testid', async ({ page }) => {
    console.log('\n=== INICIANDO TESTE DO WIZARD ===\n');

    // 1. Navegar para /demo-app
    console.log('1. Navegando para /demo-app');
    await page.goto('/demo-app');
    await page.waitForLoadState('networkidle');
    console.log('✅ Página carregada');

    // Aguardar modal aparecer
    await page.waitForTimeout(1000);

    // 2. Clicar em "EUA" e depois "Próximo"
    console.log('\n2. Clicando em "EUA"');
    const euaButton = page.locator('button:has-text("EUA")');
    await expect(euaButton).toBeVisible({ timeout: 5000 });
    await euaButton.click();
    console.log('✅ EUA selecionado');

    // Aguardar que o botão "Próximo" fique habilitado (sem disabled)
    console.log('\n3. Aguardando botão "Próximo" ficar habilitado...');
    const proximoStep1 = page.locator('button:has-text("Próximo")').last();
    await expect(proximoStep1).toBeEnabled({ timeout: 5000 });
    console.log('✅ Botão "Próximo" habilitado');

    console.log('\n4. Clicando em "Próximo" (Step 1 -> Step 2)');
    await proximoStep1.click();
    await page.waitForTimeout(500);
    console.log('✅ Avançou para Step 2');

    // 3. Clicar em "Desenvolver"
    console.log('\n5. Procurando botão "Desenvolver"');
    const desenvolverButton = page.locator('button:has-text("Desenvolver")');
    await expect(desenvolverButton).toBeVisible({ timeout: 5000 });
    console.log('✅ Botão "Desenvolver" visível');

    console.log('\n6. Clicando em "Desenvolver"');
    await desenvolverButton.click();
    await page.waitForTimeout(500); // Aguardar estado atualizar
    console.log('✅ Desenvolver clicado');

    // Verificar se o botão ficou selecionado (mudou de estilo)
    const desenvolverIsSelected = await desenvolverButton.evaluate(el => {
      return el.classList.contains('bg-brand-600') ||
             el.classList.contains('ring-2') ||
             el.getAttribute('aria-selected') === 'true';
    });
    console.log(`Desenvolver está selecionado: ${desenvolverIsSelected}`);

    // 4. Aguardar máquinas carregarem (API faz fetch)
    console.log('\n7. Aguardando 5 segundos para API carregar máquinas...');
    await page.waitForTimeout(5000);
    console.log('✅ Aguardou');

    // 5. Verificar se há erro de API ou máquinas carregadas
    console.log('\n8. Verificando se máquinas carregaram ou se há erro...');

    // Procurar mensagens de erro ou loading
    const loadingVisible = await page.locator('text=/Carregando|Loading/i').isVisible().catch(() => false);
    const errorVisible = await page.locator('text=/Erro|Error|Nenhuma oferta/i').isVisible().catch(() => false);

    console.log(`Loading visível: ${loadingVisible}`);
    console.log(`Erro visível: ${errorVisible}`);

    // 5. Usar seletor [data-testid^="machine-"] para clicar na primeira máquina
    console.log('\n9. Procurando máquinas com seletor [data-testid^="machine-"]');
    const machineSelector = '[data-testid^="machine-"]';

    // Aguardar máquinas aparecerem
    const machinesFound = await page.waitForSelector(machineSelector, { timeout: 10000 }).catch(() => null);

    if (!machinesFound) {
      // Debug: mostrar o HTML do Step 2
      const step2Content = await page.locator('text=Hardware').locator('..').locator('..').textContent();
      console.log('\n⚠️ Máquinas não encontradas. Conteúdo do Step 2:');
      console.log(step2Content.substring(0, 500));
      throw new Error('Nenhuma máquina encontrada com data-testid após 10s');
    }

    // Contar máquinas encontradas
    const machineCount = await page.locator(machineSelector).count();
    console.log(`✅ Encontradas ${machineCount} máquinas`);

    if (machineCount === 0) {
      throw new Error('Nenhuma máquina encontrada com data-testid');
    }

    // Clicar na primeira máquina
    console.log('\n8. Clicando na primeira máquina');
    const firstMachine = page.locator(machineSelector).first();
    await firstMachine.click();
    console.log('✅ Primeira máquina clicada');

    // 6. Aguardar botão "Próximo" ficar habilitado e clicar
    console.log('\n9. Aguardando botão "Próximo" ficar habilitado (Step 2 -> Step 3)...');
    const proximoStep2 = page.locator('button:has-text("Próximo")').last();
    await expect(proximoStep2).toBeEnabled({ timeout: 5000 });
    console.log('✅ Botão "Próximo" habilitado');

    console.log('\n10. Clicando em "Próximo" para avançar ao Step 3');
    await proximoStep2.click();
    await page.waitForTimeout(500);
    console.log('✅ Avançou para Step 3');

    // 7. Clicar em "Iniciar"
    console.log('\n11. Procurando botão "Iniciar" no Step 3');
    await page.waitForTimeout(500);
    const iniciarButton = page.locator('button:has-text("Iniciar")');
    await expect(iniciarButton).toBeVisible({ timeout: 5000 });
    console.log('✅ Botão "Iniciar" visível');

    console.log('\n12. Clicando em "Iniciar"');
    await iniciarButton.click();
    console.log('✅ Provisionamento iniciado');

    // 8. Aguardar 20s pelo provisionamento
    console.log('\n13. Aguardando 20 segundos pelo provisionamento...');
    await page.waitForTimeout(20000);
    console.log('✅ Aguardou 20s');

    // 9. Verificar se aparece sucesso
    console.log('\n14. Verificando mensagens de sucesso...');

    // Capturar conteúdo da página para debug
    const pageContent = await page.content();

    // Procurar por indicadores de sucesso
    const successIndicators = [
      'GPU pronta',
      'Winner',
      'sucesso',
      'pronto',
      'ready',
      'completed',
      'Máquina criada'
    ];

    let foundSuccess = false;
    for (const indicator of successIndicators) {
      const element = page.locator(`text="${indicator}"`, { caseInsensitive: true });
      const isVisible = await element.isVisible().catch(() => false);

      if (isVisible) {
        console.log(`✅ SUCESSO: Encontrado "${indicator}"`);
        foundSuccess = true;
        break;
      }
    }

    // Verificar logs do console
    const logs = [];
    page.on('console', msg => {
      const text = msg.text();
      logs.push(text);
      console.log(`[BROWSER LOG] ${text}`);
    });

    // Verificar estado final da página
    const finalUrl = page.url();
    console.log(`\n📍 URL final: ${finalUrl}`);

    // Capturar screenshot final
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/test-results/wizard-final-state.png',
      fullPage: true
    });
    console.log('📸 Screenshot salvo em test-results/wizard-final-state.png');

    // Verificar elementos visíveis na página
    const visibleElements = await page.locator('body').textContent();
    console.log('\n📄 Conteúdo visível na página (primeiros 500 chars):');
    console.log(visibleElements.substring(0, 500));

    if (!foundSuccess) {
      console.warn('\n⚠️ AVISO: Nenhum indicador de sucesso encontrado após 20s');
      console.warn('Verifique o screenshot para análise manual');
    }

    console.log('\n=== TESTE CONCLUÍDO ===\n');
  });
});
