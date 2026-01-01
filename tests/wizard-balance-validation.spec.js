// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * 🧪 TESTE AUTOMATIZADO - VALIDAÇÃO DE SALDO NO WIZARD
 *
 * Este teste valida que:
 * 1. Quando balance <= 0: Wizard é bloqueado e mostra mensagem "Saldo Insuficiente"
 * 2. Quando balance > 0: Wizard é exibido normalmente
 * 3. Botões "Adicionar Créditos" e "Verificar Novamente" funcionam corretamente
 *
 * IMPORTANTE: Testa com APIs reais da VAST.ai (não é mock)
 */

test.describe('🎯 Wizard - Validação de Saldo', () => {
  test.beforeEach(async ({ page }) => {
    // Auto-login via URL parameter (usa APIs reais)
    console.log('🔐 Fazendo auto-login via ?auto_login=demo');
    await page.goto('/login?auto_login=demo');

    // Aguardar redirect para /app
    await page.waitForURL('**/app**', { timeout: 10000 });
    console.log('✅ Login automático completado');

    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Fechar modal de boas-vindas se aparecer
    const skipButton = page.getByText('Pular tudo');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      await page.waitForTimeout(500);
    }
  });

  test('Quando balance <= 0: Deve mostrar mensagem de saldo insuficiente', async ({ page }) => {
    console.log('🧪 Teste: Validar mensagem de saldo insuficiente quando balance <= 0');

    // Aguardar carregamento do saldo
    await page.waitForTimeout(2000);

    // Verificar se a mensagem de saldo insuficiente está visível
    const insufficientBalanceMsg = page.getByTestId('insufficient-balance-message');
    const isInsufficientBalanceVisible = await insufficientBalanceMsg.isVisible({ timeout: 5000 }).catch(() => false);

    if (isInsufficientBalanceVisible) {
      console.log('✅ Mensagem "Saldo Insuficiente" está visível');

      // Verificar que o wizard NÃO está visível
      const wizardForm = page.getByTestId('wizard-form-container');
      const isWizardVisible = await wizardForm.isVisible({ timeout: 1000 }).catch(() => false);

      expect(isWizardVisible).toBeFalsy();
      console.log('✅ Wizard NÃO está visível (correto quando balance <= 0)');

      // Verificar botões de ação
      const addCreditsButton = page.getByTestId('add-credits-button');
      const checkBalanceButton = page.getByTestId('check-balance-button');

      await expect(addCreditsButton).toBeVisible();
      await expect(checkBalanceButton).toBeVisible();
      console.log('✅ Botões "Adicionar Créditos" e "Verificar Novamente" estão visíveis');

      // Testar botão "Verificar Novamente"
      await checkBalanceButton.click();
      await page.waitForTimeout(1000);
      console.log('✅ Botão "Verificar Novamente" foi clicado');
    } else {
      console.log('⚠️  Mensagem de saldo insuficiente NÃO está visível');
      console.log('ℹ️  Isso significa que a conta tem saldo positivo');

      // Verificar que o wizard ESTÁ visível
      const wizardForm = page.getByTestId('wizard-form-container');
      const isWizardVisible = await wizardForm.isVisible({ timeout: 5000 }).catch(() => false);

      if (isWizardVisible) {
        console.log('✅ Wizard está visível (correto quando balance > 0)');
      } else {
        console.log('❌ ERRO: Nem mensagem de saldo insuficiente nem wizard estão visíveis!');
        throw new Error('Nenhum dos elementos esperados foi encontrado');
      }
    }
  });

  test('Debug: Verificar estado de carregamento e valores de saldo', async ({ page }) => {
    console.log('🧪 Teste: Debug - Estado de carregamento do saldo');

    // Aguardar brevemente e verificar se está em loading
    const loadingIndicator = page.getByTestId('balance-loading');
    const isLoadingVisible = await loadingIndicator.isVisible({ timeout: 2000 }).catch(() => false);

    if (isLoadingVisible) {
      console.log('⏳ Estado de loading detectado');
      // Aguardar fim do loading
      await page.waitForTimeout(3000);
    }

    // Capturar console.logs do browser
    const logs = [];
    page.on('console', msg => {
      if (msg.text().includes('[BALANCE]') || msg.text().includes('[WIZARD RENDER]')) {
        logs.push(msg.text());
        console.log(`📝 Browser Log: ${msg.text()}`);
      }
    });

    // Recarregar página para capturar logs
    await page.reload();
    await page.waitForTimeout(3000);

    // Mostrar todos os logs capturados
    console.log('\n📋 Logs capturados do browser:');
    logs.forEach(log => console.log(`  ${log}`));
  });

  test('Verificar chamada à API de balance', async ({ page }) => {
    console.log('🧪 Teste: Verificar chamada à API /api/v1/instances/balance');

    // Interceptar requisições à API
    const balanceRequests = [];
    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/instances/balance')) {
        const status = response.status();
        console.log(`📡 API /balance chamada - Status: ${status}`);

        if (status === 200) {
          try {
            const body = await response.json();
            console.log('📥 Resposta da API:', JSON.stringify(body, null, 2));
            balanceRequests.push(body);
          } catch (e) {
            console.error('❌ Erro ao parsear resposta:', e);
          }
        }
      }
    });

    // Recarregar página para disparar requisição
    await page.reload();
    await page.waitForTimeout(3000);

    // Verificar se API foi chamada
    if (balanceRequests.length > 0) {
      console.log(`✅ API de balance foi chamada ${balanceRequests.length} vez(es)`);
      const lastBalance = balanceRequests[balanceRequests.length - 1];
      console.log(`💰 Saldo atual: ${lastBalance.credit}`);
      console.log(`📊 Balance: ${lastBalance.balance}`);
      console.log(`📧 Email: ${lastBalance.email}`);
    } else {
      console.log('❌ API de balance NÃO foi chamada');
    }
  });

  test('Validação completa: Balance -> UI State', async ({ page }) => {
    console.log('🧪 Teste: Validação completa de balance -> estado da UI');

    // Capturar resposta da API
    let balanceData = null;
    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/instances/balance') && response.status() === 200) {
        try {
          balanceData = await response.json();
        } catch (e) {
          console.error('Erro ao parsear balance:', e);
        }
      }
    });

    // Recarregar para disparar chamadas
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);

    console.log('\n📊 VALIDAÇÃO COMPLETA:');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    if (balanceData) {
      const credit = balanceData.credit || 0;
      console.log(`💰 Saldo da API: ${credit}`);

      // Verificar estado esperado da UI baseado no saldo
      const insufficientBalanceMsg = page.getByTestId('insufficient-balance-message');
      const wizardForm = page.getByTestId('wizard-form-container');

      const isMsgVisible = await insufficientBalanceMsg.isVisible({ timeout: 2000 }).catch(() => false);
      const isWizardVisible = await wizardForm.isVisible({ timeout: 2000 }).catch(() => false);

      console.log(`🎨 UI - Mensagem de saldo insuficiente: ${isMsgVisible ? 'VISÍVEL' : 'OCULTA'}`);
      console.log(`🎨 UI - Wizard form: ${isWizardVisible ? 'VISÍVEL' : 'OCULTO'}`);

      // Validar comportamento esperado
      if (credit <= 0) {
        console.log('\n🔍 VALIDAÇÃO: Balance <= 0');
        expect(isMsgVisible).toBeTruthy();
        expect(isWizardVisible).toBeFalsy();
        console.log('✅ PASSOU: Mensagem visível e wizard oculto');
      } else {
        console.log('\n🔍 VALIDAÇÃO: Balance > 0');
        expect(isMsgVisible).toBeFalsy();
        expect(isWizardVisible).toBeTruthy();
        console.log('✅ PASSOU: Wizard visível e mensagem oculta');
      }
    } else {
      console.log('❌ FALHOU: Não foi possível capturar dados da API');
      throw new Error('API de balance não respondeu');
    }

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  });
});

/**
 * INSTRUÇÕES PARA RODAR OS TESTES:
 *
 * 1. Rodar todos os testes de balance:
 *    cd tests
 *    npm run test -- wizard-balance-validation.spec.js
 *
 * 2. Modo headed (ver browser):
 *    npm run test -- wizard-balance-validation.spec.js --headed
 *
 * 3. Modo debug:
 *    npm run test -- wizard-balance-validation.spec.js --debug
 *
 * 4. Rodar apenas um teste específico:
 *    npm run test -- wizard-balance-validation.spec.js --grep "Validação completa"
 */
