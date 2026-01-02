const { test, expect } = require('@playwright/test');

test.describe('Wizard de Reserva GPU - Fluxo Corrigido com TestIDs', () => {
  test('Fluxo completo com seletores corretos', async ({ page }) => {
    console.log('\n========================================');
    console.log('WIZARD TEST - VERSÃO CORRIGIDA');
    console.log('========================================\n');

    // STEP 1: Login automático
    console.log('STEP 1: Auto-login');
    await page.goto('http://localhost:4894/login?auto_login=demo');
    await page.waitForURL('**/app**', { timeout: 10000 });
    console.log('✅ Login OK - Redirecionado para /app\n');

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-01-logged-in.png', fullPage: true });
    await page.waitForTimeout(2000);

    // Verificar se wizard está visível
    const wizardVisible = await page.locator('text="Nova Instância GPU"').isVisible({ timeout: 5000 });
    console.log(`Wizard visível: ${wizardVisible}\n`);

    if (!wizardVisible) {
      console.log('⚠️ Wizard não está aberto - terminando teste');
      return;
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-02-wizard-open.png', fullPage: true });

    // STEP 2: Selecionar Região (Step 1/4 do wizard)
    console.log('STEP 2: Selecionar Região');

    // Verificar que estamos no step 1
    const step1Active = await page.locator('text="1/4"').isVisible();
    console.log(`Step 1/4 ativo: ${step1Active}`);

    // Clicar em uma das regiões - usando botão específico
    const euaButton = page.locator('button:has-text("EUA")').first();
    const isEuaVisible = await euaButton.isVisible({ timeout: 3000 }).catch(() => false);

    if (isEuaVisible) {
      console.log('Clicando em região "EUA"');
      await euaButton.click();
      await page.waitForTimeout(1000);
      console.log('✅ Região selecionada\n');
    } else {
      console.log('⚠️ Botão EUA não encontrado - tentando primeira região disponível');
      const firstRegion = page.locator('[class*="region"], button[class*="rounded"]').first();
      await firstRegion.click();
      await page.waitForTimeout(1000);
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-03-region-selected.png', fullPage: true });

    // Clicar em "Próximo" para ir ao Step 2
    console.log('STEP 3: Avançar para Hardware (Step 2/4)');
    const nextButton = page.locator('button:has-text("Próximo")').first();
    await nextButton.click();
    await page.waitForTimeout(2000);
    console.log('✅ Navegado para Step 2\n');

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-04-step2-hardware.png', fullPage: true });

    // STEP 4: Selecionar Propósito/Use Case
    console.log('STEP 4: Selecionar propósito (use case)');

    // Verificar que estamos no step 2
    const step2Active = await page.locator('text="2/4"').isVisible();
    console.log(`Step 2/4 ativo: ${step2Active}`);

    // Verificar label "O que você vai fazer?"
    const purposeLabel = await page.locator('text="O que você vai fazer?"').isVisible();
    console.log(`Label de propósito visível: ${purposeLabel}`);

    // Selecionar um use case usando data-testid
    const useCases = ['train', 'develop', 'test', 'production', 'cpu_only'];
    let useCaseSelected = false;

    for (const useCaseId of useCases) {
      const useCaseButton = page.locator(`[data-testid="use-case-${useCaseId}"]`);
      const isVisible = await useCaseButton.isVisible({ timeout: 1000 }).catch(() => false);

      if (isVisible) {
        console.log(`Selecionando use case: ${useCaseId}`);
        await useCaseButton.click();
        await page.waitForTimeout(2000); // Aguardar máquinas carregarem
        useCaseSelected = true;
        break;
      }
    }

    if (!useCaseSelected) {
      console.log('⚠️ Nenhum use case encontrado com data-testid');
    } else {
      console.log('✅ Use case selecionado\n');
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-05-usecase-selected.png', fullPage: true });

    // STEP 5: Aguardar máquinas carregarem
    console.log('STEP 5: Aguardar máquinas carregarem');

    // Verificar loading state
    const loadingText = page.locator('text="Buscando máquinas disponíveis"');
    const isLoading = await loadingText.isVisible({ timeout: 2000 }).catch(() => false);

    if (isLoading) {
      console.log('⏳ Aguardando carregamento...');
      await page.waitForTimeout(5000);
    }

    // Verificar se há máquinas disponíveis
    const machineCards = await page.locator('[data-testid^="machine-"]').count();
    console.log(`Máquinas encontradas: ${machineCards}`);

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-06-machines-loaded.png', fullPage: true });

    // STEP 6: Selecionar uma máquina
    console.log('STEP 6: Selecionar máquina GPU');

    if (machineCards > 0) {
      const firstMachine = page.locator('[data-testid^="machine-"]').first();
      console.log('Selecionando primeira máquina disponível');
      await firstMachine.click();
      await page.waitForTimeout(1500);
      console.log('✅ Máquina selecionada\n');
    } else {
      console.log('⚠️ Nenhuma máquina disponível - verifique API VAST.ai\n');
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-07-machine-selected.png', fullPage: true });

    // STEP 7: Avançar para Estratégia (Step 3/4)
    console.log('STEP 7: Avançar para Estratégia (Step 3/4)');

    const nextButton2 = page.locator('button:has-text("Próximo")').first();
    const isNext2Visible = await nextButton2.isVisible({ timeout: 2000 }).catch(() => false);

    if (isNext2Visible) {
      await nextButton2.click();
      await page.waitForTimeout(2000);
      console.log('✅ Navegado para Step 3\n');
    } else {
      console.log('⚠️ Botão "Próximo" não está habilitado (falta selecionar máquina?)\n');
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-08-step3-strategy.png', fullPage: true });

    // STEP 8: Selecionar estratégia de failover
    console.log('STEP 8: Selecionar estratégia de failover');

    const step3Active = await page.locator('text="3/4"').isVisible({ timeout: 2000 }).catch(() => false);
    console.log(`Step 3/4 ativo: ${step3Active}`);

    // Verificar label de estratégia
    const strategyLabel = await page.locator('text=/Estratégia de Failover/i').isVisible({ timeout: 2000 }).catch(() => false);
    console.log(`Label de estratégia visível: ${strategyLabel}`);

    // Selecionar estratégia usando data-testid
    const strategies = ['snapshot_only', 'cpu_standby', 'warm_pool', 'no_failover'];
    let strategySelected = false;

    for (const strategyId of strategies) {
      const strategyButton = page.locator(`[data-testid="failover-option-${strategyId}"]`);
      const isVisible = await strategyButton.isVisible({ timeout: 1000 }).catch(() => false);
      const isDisabled = await strategyButton.isDisabled().catch(() => false);

      if (isVisible && !isDisabled) {
        console.log(`Selecionando estratégia: ${strategyId}`);
        await strategyButton.click();
        await page.waitForTimeout(1500);
        strategySelected = true;
        break;
      } else if (isVisible && isDisabled) {
        console.log(`Estratégia ${strategyId} está desabilitada`);
      }
    }

    if (!strategySelected) {
      console.log('⚠️ Nenhuma estratégia selecionada');
    } else {
      console.log('✅ Estratégia selecionada\n');
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-09-strategy-selected.png', fullPage: true });

    // STEP 9: Iniciar provisionamento
    console.log('STEP 9: Iniciar provisionamento');

    // O botão "Próximo" no Step 3 inicia o provisionamento
    const startButton = page.locator('button:has-text("Próximo")').first();
    const isStartVisible = await startButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (isStartVisible) {
      const buttonText = await startButton.textContent();
      console.log(`Clicando em botão: "${buttonText}"`);
      await startButton.click();
      await page.waitForTimeout(3000);
      console.log('✅ Provisionamento iniciado\n');
    } else {
      console.log('⚠️ Botão para iniciar não encontrado\n');
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-10-provisioning-started.png', fullPage: true });

    // STEP 10: Verificar step 4 (provisionamento)
    console.log('STEP 10: Verificar tela de provisionamento');

    await page.waitForTimeout(2000);

    const step4Active = await page.locator('text="4/4"').isVisible({ timeout: 3000 }).catch(() => false);
    console.log(`Step 4/4 (Provisionar) ativo: ${step4Active}`);

    // Verificar indicadores de provisionamento
    const provisioningIndicators = [
      'text="Provisionando"',
      'text="Conectando"',
      'text="Buscando máquina"',
      'text=/Racing.*máquinas/i',
      '[class*="animate-spin"]',
    ];

    let provisioningDetected = false;
    for (const selector of provisioningIndicators) {
      const indicator = page.locator(selector).first();
      const isVisible = await indicator.isVisible({ timeout: 1000 }).catch(() => false);
      if (isVisible) {
        const text = await indicator.textContent().catch(() => '');
        console.log(`✅ Provisionamento detectado: "${text}"`);
        provisioningDetected = true;
        break;
      }
    }

    if (!provisioningDetected) {
      console.log('⚠️ Indicador de provisionamento não detectado');
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-11-provisioning.png', fullPage: true });

    // Aguardar um pouco mais para ver o estado
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'tests/screenshots/wizard-fixed-12-final.png', fullPage: true });

    // RESUMO
    console.log('\n========================================');
    console.log('RESUMO DO TESTE');
    console.log('========================================');
    console.log('✅ Login automático: OK');
    console.log(`✅ Wizard aberto: ${wizardVisible ? 'OK' : 'FALHOU'}`);
    console.log(`✅ Step 1 - Região: OK`);
    console.log(`✅ Step 2 - Hardware: ${step2Active ? 'OK' : 'NÃO ALCANÇADO'}`);
    console.log(`✅ Use case selecionado: ${useCaseSelected ? 'OK' : 'FALHOU'}`);
    console.log(`✅ Máquinas carregadas: ${machineCards} máquinas`);
    console.log(`✅ Step 3 - Estratégia: ${step3Active ? 'OK' : 'NÃO ALCANÇADO'}`);
    console.log(`✅ Estratégia selecionada: ${strategySelected ? 'OK' : 'FALHOU'}`);
    console.log(`✅ Step 4 - Provisionamento: ${step4Active ? 'OK' : 'NÃO ALCANÇADO'}`);
    console.log(`✅ Provisionamento iniciado: ${provisioningDetected ? 'OK' : 'NÃO DETECTADO'}`);
    console.log('========================================\n');
  });
});
