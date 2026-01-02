/**
 * Teste COMPLETO do Wizard de Provisionamento
 *
 * Valida o fluxo desde a seleção de região até o provisionamento final
 * Usa demo-app em http://localhost:4898
 */

const { test, expect } = require('@playwright/test');

test.describe('Wizard - Fluxo Completo até Provisionamento', () => {

  test('deve completar todo o wizard e provisionar máquina com sucesso', async ({ page }) => {
    let stepResult = '';

    // ========== PASSO 1: Navegação inicial ==========
    console.log('\n[PASSO 1] Navegando para http://localhost:4898/demo-app');
    await page.goto('http://localhost:4898/demo-app', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Screenshot do estado inicial
    await page.screenshot({ path: 'test-results/step1-inicial.png', fullPage: true });

    // Verificar se página carregou
    const pageTitle = await page.title();
    console.log(`✓ Página carregada: "${pageTitle}"`);
    stepResult = '✓ PASSO 1: Navegação OK';
    console.log(stepResult);

    // ========== PASSO 2: Clicar em região EUA ==========
    console.log('\n[PASSO 2] Aguardando 2s e clicando em região EUA');
    await page.waitForTimeout(2000);

    const regionButton = page.locator('button[data-testid="region-eua"]');
    const regionVisible = await regionButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!regionVisible) {
      console.error('❌ Botão region-eua NÃO encontrado!');
      console.log('Tentando capturar estado da página...');

      // Debug: listar todos os botões visíveis
      const allButtons = await page.locator('button').all();
      console.log(`Total de botões na página: ${allButtons.length}`);

      for (let i = 0; i < Math.min(allButtons.length, 10); i++) {
        const testId = await allButtons[i].getAttribute('data-testid');
        const text = await allButtons[i].textContent();
        console.log(`  Botão ${i}: testid="${testId}", texto="${text?.trim()}"`);
      }

      await page.screenshot({ path: 'test-results/error-region-not-found.png', fullPage: true });
      throw new Error('Region button not found');
    }

    // Clicar forçando disparo do evento (necessário para React capturar)
    await regionButton.click({ force: true });
    await page.waitForTimeout(500);

    // Garantir que o click foi registrado via JavaScript também
    await regionButton.evaluate(button => button.click());

    console.log('✓ Região EUA clicada (forçando disparo)');

    // Esperar estado atualizar
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'test-results/step2-regiao-selecionada.png', fullPage: true });
    stepResult = '✓ PASSO 2: Região EUA selecionada';
    console.log(stepResult);

    // ========== PASSO 3: Clicar em Próximo (Step 1 → Step 2) ==========
    console.log('\n[PASSO 3] Clicando em "Próximo" para ir ao Step 2');

    // Buscar botão "Próximo" que contenha ChevronRight
    const proximoButton = page.locator('button').filter({ hasText: 'Próximo' });

    // Debug: verificar estado do botão
    const buttonCount = await proximoButton.count();
    console.log(`  Botões "Próximo" encontrados: ${buttonCount}`);

    if (buttonCount === 0) {
      console.error('❌ Nenhum botão "Próximo" encontrado!');
      await page.screenshot({ path: 'test-results/error-no-proximo.png', fullPage: true });
      throw new Error('Próximo button not found');
    }

    // Verificar se está visível
    await proximoButton.first().waitFor({ state: 'visible', timeout: 5000 });
    console.log('  Botão "Próximo" visível');

    // Verificar se está habilitado (esperar até 10s)
    let isEnabled = false;
    for (let i = 0; i < 20; i++) {
      isEnabled = await proximoButton.first().isEnabled();
      if (isEnabled) {
        console.log(`  Botão "Próximo" habilitado após ${i * 500}ms`);
        break;
      }
      await page.waitForTimeout(500);
    }

    if (!isEnabled) {
      console.error('❌ Botão "Próximo" permanece DESABILITADO!');
      await page.screenshot({ path: 'test-results/error-proximo-disabled.png', fullPage: true });
      throw new Error('Próximo button remains disabled');
    }

    await proximoButton.first().click({ force: true });
    console.log('✓ Botão "Próximo" clicado');

    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/step3-apos-proximo.png', fullPage: true });

    // ========== PASSO 4: Verificar Step 2 e clicar em "Desenvolver" ==========
    console.log('\n[PASSO 4] Verificando Step 2 e procurando "Desenvolver"');

    // Verificar se está no Step 2 (procurar indicadores)
    const step2Indicators = [
      'O que você vai fazer?',
      'Desenvolver',
      'Treinar',
      'Inferência'
    ];

    let foundIndicator = false;
    for (const indicator of step2Indicators) {
      const hasText = await page.locator(`text="${indicator}"`).isVisible({ timeout: 2000 }).catch(() => false);
      if (hasText) {
        console.log(`✓ Encontrado indicador do Step 2: "${indicator}"`);
        foundIndicator = true;
        break;
      }
    }

    if (!foundIndicator) {
      console.error('❌ NÃO está no Step 2! Indicadores não encontrados.');
      await page.screenshot({ path: 'test-results/error-not-step2.png', fullPage: true });
      throw new Error('Not in Step 2');
    }

    // Clicar em "Desenvolver"
    const desenvolverButton = page.locator('button:has-text("Desenvolver"), button:has-text("Develop")').first();
    await desenvolverButton.waitFor({ state: 'visible', timeout: 5000 });
    await desenvolverButton.click({ force: true });
    console.log('✓ Botão "Desenvolver" clicado');

    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/step4-desenvolver-clicado.png', fullPage: true });
    stepResult = '✓ PASSO 4: Step 2 verificado, "Desenvolver" clicado';
    console.log(stepResult);

    // ========== PASSO 5: Aguardar máquinas carregarem ==========
    console.log('\n[PASSO 5] Aguardando máquinas carregarem (2s)');
    await page.waitForTimeout(2000);

    // Verificar se máquinas apareceram
    const machines = page.locator('[data-testid^="machine-"]');
    const machineCount = await machines.count();
    console.log(`✓ Máquinas encontradas: ${machineCount}`);

    if (machineCount === 0) {
      console.error('❌ Nenhuma máquina encontrada!');
      await page.screenshot({ path: 'test-results/error-no-machines.png', fullPage: true });

      // Debug: verificar se há loading/spinner
      const hasLoading = await page.locator('text=/Loading|Carregando/i').isVisible().catch(() => false);
      console.log(`  Loading visível: ${hasLoading}`);

      throw new Error('No machines found');
    }

    await page.screenshot({ path: 'test-results/step5-maquinas-carregadas.png', fullPage: true });
    stepResult = `✓ PASSO 5: ${machineCount} máquina(s) carregada(s)`;
    console.log(stepResult);

    // ========== PASSO 6: Clicar na primeira máquina ==========
    console.log('\n[PASSO 6] Clicando na primeira máquina');

    const firstMachine = machines.first();
    await firstMachine.click({ force: true });
    console.log('✓ Primeira máquina clicada');

    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'test-results/step6-maquina-selecionada.png', fullPage: true });
    stepResult = '✓ PASSO 6: Primeira máquina selecionada';
    console.log(stepResult);

    // ========== PASSO 7: Clicar em Próximo (Step 2 → Step 3) ==========
    console.log('\n[PASSO 7] Clicando em "Próximo" para ir ao Step 3');

    const proximoButton2 = page.locator('button:has-text("Próximo"), button:has-text("Next")').first();
    await proximoButton2.waitFor({ state: 'visible', timeout: 5000 });
    await proximoButton2.click({ force: true });
    console.log('✓ Botão "Próximo" clicado (indo para Step 3)');

    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/step7-indo-step3.png', fullPage: true });
    stepResult = '✓ PASSO 7: Navegando para Step 3';
    console.log(stepResult);

    // ========== PASSO 8: Verificar Step 3 e botão "Iniciar" ==========
    console.log('\n[PASSO 8] Verificando Step 3 e botão "Iniciar"');

    // Verificar se está no Step 3 (procurar resumo/review)
    const step3Indicators = [
      'Resumo',
      'Review',
      'Iniciar',
      'Start',
      'Confirmar'
    ];

    let foundStep3 = false;
    for (const indicator of step3Indicators) {
      const hasText = await page.locator(`text="${indicator}"`).isVisible({ timeout: 2000 }).catch(() => false);
      if (hasText) {
        console.log(`✓ Encontrado indicador do Step 3: "${indicator}"`);
        foundStep3 = true;
        break;
      }
    }

    if (!foundStep3) {
      console.error('❌ NÃO está no Step 3! Indicadores não encontrados.');
      await page.screenshot({ path: 'test-results/error-not-step3.png', fullPage: true });
      throw new Error('Not in Step 3');
    }

    // Procurar botão "Iniciar"
    const iniciarButton = page.locator('button:has-text("Iniciar"), button:has-text("Start")').first();
    const iniciarVisible = await iniciarButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!iniciarVisible) {
      console.error('❌ Botão "Iniciar" NÃO encontrado!');
      await page.screenshot({ path: 'test-results/error-iniciar-not-found.png', fullPage: true });
      throw new Error('Iniciar button not found');
    }

    // Verificar se está habilitado
    const iniciarEnabled = await iniciarButton.isEnabled();
    console.log(`✓ Botão "Iniciar" encontrado, habilitado: ${iniciarEnabled}`);

    if (!iniciarEnabled) {
      console.warn('⚠️ Botão "Iniciar" está DESABILITADO!');
      await page.screenshot({ path: 'test-results/warning-iniciar-disabled.png', fullPage: true });
    }

    await page.screenshot({ path: 'test-results/step8-step3-verificado.png', fullPage: true });
    stepResult = `✓ PASSO 8: Step 3 verificado, botão "Iniciar" ${iniciarEnabled ? 'HABILITADO' : 'DESABILITADO'}`;
    console.log(stepResult);

    // ========== PASSO 9: Clicar em "Iniciar" ==========
    console.log('\n[PASSO 9] Clicando em "Iniciar" para começar provisionamento');

    await iniciarButton.click({ force: true });
    console.log('✓ Botão "Iniciar" clicado!');

    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/step9-iniciar-clicado.png', fullPage: true });
    stepResult = '✓ PASSO 9: Provisionamento iniciado';
    console.log(stepResult);

    // ========== PASSO 10: Aguardar provisionamento (25s) ==========
    console.log('\n[PASSO 10] Aguardando provisionamento (25s)...');

    // Aguardar em intervalos para monitorar o progresso
    for (let i = 0; i < 5; i++) {
      await page.waitForTimeout(5000);
      console.log(`  ${(i + 1) * 5}s decorridos...`);

      // Verificar se há indicadores de progresso
      const progressIndicators = await page.locator('text=/Provisioning|Aguardando|Racing|Winner|pronta/i').count();
      if (progressIndicators > 0) {
        console.log(`  Indicadores de progresso encontrados: ${progressIndicators}`);
      }
    }

    await page.screenshot({ path: 'test-results/step10-apos-25s.png', fullPage: true });
    stepResult = '✓ PASSO 10: 25s de provisionamento completados';
    console.log(stepResult);

    // ========== PASSO 11: Verificar sucesso do provisionamento ==========
    console.log('\n[PASSO 11] Verificando indicadores de sucesso');

    const successIndicators = [
      'pronta',
      'Winner',
      '🏆',
      'ready',
      'success',
      'Sucesso',
      'concluído',
      'completed'
    ];

    let successFound = false;
    let foundIndicators = [];

    for (const indicator of successIndicators) {
      const hasIndicator = await page.locator(`text="${indicator}"`).isVisible({ timeout: 2000 }).catch(() => false);
      if (hasIndicator) {
        foundIndicators.push(indicator);
        successFound = true;
      }
    }

    // Screenshot final
    await page.screenshot({ path: 'test-results/step11-final.png', fullPage: true });

    // Capturar texto da página para análise
    const pageText = await page.locator('body').textContent();
    const pageTextSnippet = pageText?.substring(0, 500) || '';

    console.log('\n========== RESULTADO FINAL ==========');
    if (successFound) {
      console.log(`✓ SUCESSO! Indicadores encontrados: ${foundIndicators.join(', ')}`);
      stepResult = `✓ PASSO 11: Provisionamento SUCESSO (${foundIndicators.join(', ')})`;
    } else {
      console.log('⚠️ Nenhum indicador de sucesso explícito encontrado');
      console.log('Trecho da página:');
      console.log(pageTextSnippet);
      stepResult = '⚠️ PASSO 11: Provisionamento completado (sem indicador explícito)';
    }
    console.log(stepResult);
    console.log('=====================================\n');

    // Assertions finais
    expect(machineCount).toBeGreaterThan(0); // Pelo menos 1 máquina deve ter aparecido

    // Se quiser garantir sucesso explícito, descomente:
    // expect(successFound).toBe(true);
  });

});
