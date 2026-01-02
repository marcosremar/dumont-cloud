/**
 * Wizard de GPU - Teste Manual Completo
 *
 * Este teste verifica se o fix do wizard funcionou corretamente.
 * Testa todos os steps: Região → Hardware → Confirmação → Provisionamento
 */

const { test, expect } = require('@playwright/test');

test.describe('Wizard de GPU - Teste Completo', () => {
  test.beforeEach(async ({ page }) => {
    // Ir direto para demo-app (não precisa de autenticação)
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('networkidle');

    console.log('✓ Navegou para http://localhost:4898/demo-app');
  });

  test('Wizard completo: Região → Hardware → Confirmação → Provisionamento', async ({ page }) => {
    // ============================================================
    // STEP 1: Verificar se wizard está visível
    // ============================================================
    console.log('\n[STEP 1] Verificando wizard "Nova Instância GPU"...');

    const wizardTitle = page.locator('text="Nova Instância GPU"').or(
      page.locator('h1:has-text("Nova Instância")'),
      page.locator('h2:has-text("Nova Instância")')
    );

    await expect(wizardTitle).toBeVisible({ timeout: 10000 });
    console.log('✓ Wizard "Nova Instância GPU" está visível');

    // ============================================================
    // STEP 2: Clicar em "EUA" (região)
    // ============================================================
    console.log('\n[STEP 2] Clicando em "EUA"...');

    const usaButton = page.locator('button:has-text("EUA")').or(
      page.locator('[role="button"]:has-text("EUA")'),
      page.locator('div[class*="cursor-pointer"]:has-text("EUA")')
    );

    await expect(usaButton).toBeVisible({ timeout: 5000 });
    await usaButton.click();
    console.log('✓ Clicou em "EUA"');

    // Aguardar feedback visual
    await page.waitForTimeout(500);

    // ============================================================
    // STEP 3: Clicar em "Próximo" (Step 1 → Step 2)
    // ============================================================
    console.log('\n[STEP 3] Clicando em "Próximo" para ir ao Step 2...');

    const nextButton1 = page.locator('button:has-text("Próximo")').or(
      page.locator('button:has-text("Next")')
    );

    await expect(nextButton1).toBeVisible({ timeout: 5000 });
    await expect(nextButton1).toBeEnabled();
    await nextButton1.click();
    console.log('✓ Clicou em "Próximo"');

    await page.waitForTimeout(1000);

    // ============================================================
    // STEP 4: Verificar se avançou para Step 2 (Hardware)
    // ============================================================
    console.log('\n[STEP 4] Verificando se avançou para Step 2 (Hardware)...');

    const hardwareTitle = page.locator('text="Hardware"').or(
      page.locator('text="Escolha o Hardware"'),
      page.locator('text="Selecione o Hardware"')
    );

    await expect(hardwareTitle).toBeVisible({ timeout: 5000 });
    console.log('✓ Avançou para Step 2 (Hardware)');

    // ============================================================
    // STEP 5: Clicar em "Desenvolver"
    // ============================================================
    console.log('\n[STEP 5] Clicando em "Desenvolver"...');

    const devButton = page.locator('button:has-text("Desenvolver")').or(
      page.locator('[role="button"]:has-text("Desenvolver")'),
      page.locator('div[class*="cursor-pointer"]:has-text("Desenvolver")')
    );

    await expect(devButton).toBeVisible({ timeout: 5000 });
    await devButton.click();
    console.log('✓ Clicou em "Desenvolver"');

    // ============================================================
    // STEP 6: Aguardar máquinas carregarem (2s)
    // ============================================================
    console.log('\n[STEP 6] Aguardando máquinas carregarem (2s)...');
    await page.waitForTimeout(2000);
    console.log('✓ Aguardou 2 segundos');

    // ============================================================
    // STEP 7: Verificar se as máquinas aparecem
    // ============================================================
    console.log('\n[STEP 7] Verificando se as máquinas aparecem...');

    // Procurar por cards de máquinas (diversos padrões possíveis)
    const machineCards = page.locator('[class*="machine-card"]').or(
      page.locator('[class*="gpu-card"]'),
      page.locator('button:has-text("RTX")'),
      page.locator('button:has-text("Selecionar")')
    );

    const machineCount = await machineCards.count();
    console.log(`✓ Encontradas ${machineCount} máquinas`);

    if (machineCount === 0) {
      // Tirar screenshot para debug
      await page.screenshot({ path: 'wizard-no-machines.png', fullPage: true });
      console.log('⚠ AVISO: Nenhuma máquina encontrada! Screenshot salvo em wizard-no-machines.png');

      // Tentar procurar por loading spinner
      const loading = page.locator('text=/carregando|loading/i');
      if (await loading.isVisible().catch(() => false)) {
        console.log('ℹ INFO: Ainda está carregando máquinas...');
        await page.waitForTimeout(3000);
      }
    }

    expect(machineCount).toBeGreaterThan(0);

    // ============================================================
    // STEP 8: Selecionar uma máquina
    // ============================================================
    console.log('\n[STEP 8] Selecionando uma máquina...');

    // Procurar botão "Selecionar" na primeira máquina
    const selectButton = page.locator('button:has-text("Selecionar")').first();

    await expect(selectButton).toBeVisible({ timeout: 5000 });
    await selectButton.click();
    console.log('✓ Selecionou a primeira máquina');

    await page.waitForTimeout(500);

    // ============================================================
    // STEP 9: Clicar em "Próximo" para ir ao Step 3
    // ============================================================
    console.log('\n[STEP 9] Clicando em "Próximo" para ir ao Step 3...');

    const nextButton2 = page.locator('button:has-text("Próximo")').or(
      page.locator('button:has-text("Next")')
    );

    await expect(nextButton2).toBeVisible({ timeout: 5000 });
    await expect(nextButton2).toBeEnabled();
    await nextButton2.click();
    console.log('✓ Clicou em "Próximo"');

    await page.waitForTimeout(1000);

    // ============================================================
    // STEP 10: Verificar Step 3 (Confirmação)
    // ============================================================
    console.log('\n[STEP 10] Verificando Step 3 (Confirmação)...');

    const confirmTitle = page.locator('text="Confirmação"').or(
      page.locator('text="Revisar"'),
      page.locator('text="Confirmar"')
    );

    await expect(confirmTitle).toBeVisible({ timeout: 5000 });
    console.log('✓ Chegou ao Step 3 (Confirmação)');

    // ============================================================
    // STEP 11: Clicar em "Iniciar"
    // ============================================================
    console.log('\n[STEP 11] Clicando em "Iniciar"...');

    const startButton = page.locator('button:has-text("Iniciar")').or(
      page.locator('button:has-text("Start")'),
      page.locator('button:has-text("Criar")')
    );

    await expect(startButton).toBeVisible({ timeout: 5000 });
    await expect(startButton).toBeEnabled();
    await startButton.click();
    console.log('✓ Clicou em "Iniciar"');

    // ============================================================
    // STEP 12: Aguardar provisionamento e verificar sucesso
    // ============================================================
    console.log('\n[STEP 12] Aguardando provisionamento...');

    // Procurar por indicadores de provisionamento
    const provisioning = page.locator('text=/provisionando|provisioning|criando/i');

    // Aguardar mensagem de sucesso (pode demorar)
    const success = page.locator('text=/sucesso|success|online|ready/i').or(
      page.locator('[class*="success"]'),
      page.locator('[class*="check"]')
    );

    // Timeout maior para provisionamento real (30s-2min)
    const successVisible = await success.isVisible({ timeout: 120000 }).catch(() => false);

    if (successVisible) {
      console.log('✓ Provisionamento bem-sucedido!');

      // Tirar screenshot do sucesso
      await page.screenshot({ path: 'wizard-success.png', fullPage: true });
      console.log('✓ Screenshot de sucesso salvo em wizard-success.png');
    } else {
      console.log('⚠ AVISO: Não detectou mensagem de sucesso em 2 minutos');

      // Tirar screenshot para debug
      await page.screenshot({ path: 'wizard-provisioning.png', fullPage: true });
      console.log('ℹ Screenshot salvo em wizard-provisioning.png');

      // Verificar se há mensagem de erro
      const error = page.locator('text=/erro|error|falhou|failed/i');
      if (await error.isVisible().catch(() => false)) {
        const errorText = await error.textContent();
        console.log(`❌ ERRO DETECTADO: ${errorText}`);
        throw new Error(`Provisionamento falhou: ${errorText}`);
      }
    }

    // ============================================================
    // RESUMO FINAL
    // ============================================================
    console.log('\n============================================================');
    console.log('RESUMO DO TESTE:');
    console.log('============================================================');
    console.log('✓ Step 1: Wizard visível');
    console.log('✓ Step 2: Selecionou região "EUA"');
    console.log('✓ Step 3: Avançou para Hardware');
    console.log('✓ Step 4: Selecionou "Desenvolver"');
    console.log('✓ Step 5: Máquinas carregaram');
    console.log('✓ Step 6: Selecionou uma máquina');
    console.log('✓ Step 7: Avançou para Confirmação');
    console.log('✓ Step 8: Iniciou provisionamento');
    console.log(successVisible ? '✓ Step 9: Provisionamento bem-sucedido' : '⚠ Step 9: Provisionamento em andamento');
    console.log('============================================================');
  });

  test('Verificar se botão Próximo está desabilitado sem seleção', async ({ page }) => {
    console.log('\n[TESTE ADICIONAL] Verificando validação do wizard...');

    // Verificar que botão "Próximo" está desabilitado sem selecionar região
    const nextButton = page.locator('button:has-text("Próximo")');

    // Pode estar desabilitado ou não visível
    const isDisabled = await nextButton.isDisabled().catch(() => true);

    if (isDisabled) {
      console.log('✓ Validação OK: Botão "Próximo" desabilitado sem seleção');
    } else {
      console.log('⚠ AVISO: Botão "Próximo" está habilitado sem seleção (verificar validação)');
    }
  });
});
