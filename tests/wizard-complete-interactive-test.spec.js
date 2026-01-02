/**
 * TESTE COMPLETO E INTERATIVO DO WIZARD DE RESERVA DE GPU
 *
 * Este teste percorre CADA passo do wizard e documenta exatamente o que acontece.
 * Servidor: http://localhost:4894
 */

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

// Criar diretório para screenshots se não existir
const screenshotsDir = path.join(__dirname, 'wizard-interactive-screenshots');
if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

test.describe('Wizard de Reserva de GPU - Teste Completo Interativo', () => {

  test('Fluxo completo do wizard de reserva', async ({ page }) => {
    // Coletar logs do console
    const consoleLogs = [];
    const consoleErrors = [];

    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push(text);
      if (msg.type() === 'error') {
        consoleErrors.push(text);
      }
    });

    console.log('\n========================================');
    console.log('PASSO 1: ACESSO E LOGIN AUTOMÁTICO');
    console.log('========================================\n');

    // Navegar para login com auto_login
    await page.goto('http://localhost:4894/login?auto_login=demo');
    await page.screenshot({
      path: path.join(screenshotsDir, '01-login-auto.png'),
      fullPage: true
    });
    console.log('✓ Screenshot: 01-login-auto.png');

    // Aguardar redirecionamento para /app
    console.log('⏳ Aguardando login automático...');
    await page.waitForURL('**/app**', { timeout: 10000 });
    console.log('✓ Login automático concluído - redirecionado para /app');

    await page.screenshot({
      path: path.join(screenshotsDir, '02-dashboard-inicial.png'),
      fullPage: true
    });
    console.log('✓ Screenshot: 02-dashboard-inicial.png');

    // Verificar erros no console até aqui
    if (consoleErrors.length > 0) {
      console.log('⚠️ ERROS NO CONSOLE (Login):');
      consoleErrors.forEach(err => console.log('  - ' + err));
    }

    console.log('\n========================================');
    console.log('PASSO 2: ENCONTRAR E ABRIR WIZARD');
    console.log('========================================\n');

    // Aguardar que a página carregue completamente
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Procurar pelo wizard - pode estar em modal de onboarding ou diretamente no dashboard
    let wizardVisible = false;

    // Verificar se há modal de onboarding
    const skipButton = page.locator('text="Pular tudo"');
    if (await skipButton.isVisible().catch(() => false)) {
      console.log('✓ Modal de onboarding detectado - fechando...');
      await skipButton.click();
      await page.waitForTimeout(1000);
    }

    // Procurar pelo wizard no dashboard
    const wizardTitle = page.locator('text=/Novo Deploy|Deploy de GPU|Criar Máquina/i');
    wizardVisible = await wizardTitle.isVisible().catch(() => false);

    if (!wizardVisible) {
      // Tentar encontrar botão para abrir wizard
      const createButton = page.locator('button:has-text(/Criar|Deploy|Nova Máquina/i)').first();
      if (await createButton.isVisible().catch(() => false)) {
        console.log('✓ Botão de criar máquina encontrado - clicando...');
        await createButton.click();
        await page.waitForTimeout(1000);
      }
    }

    await page.screenshot({
      path: path.join(screenshotsDir, '03-wizard-aberto.png'),
      fullPage: true
    });
    console.log('✓ Screenshot: 03-wizard-aberto.png');

    console.log('\n========================================');
    console.log('PASSO 3: STEP 1 - SELECIONAR REGIÃO');
    console.log('========================================\n');

    // Verificar se há indicador de step 1
    const step1Indicator = page.locator('text=/Região|Step 1|Passo 1/i');
    const step1Visible = await step1Indicator.isVisible().catch(() => false);
    console.log(step1Visible ? '✓ Step 1 (Região) visível' : '⚠️ Step 1 não encontrado');

    // Procurar por opções de região (botões com texto específico)
    const regionOptions = page.locator('button').filter({ hasText: /EUA|Europa|Ásia|América/ });
    const regionCount = await regionOptions.count();
    console.log(`✓ Encontradas ${regionCount} opções de região`);

    if (regionCount > 0) {
      // Selecionar primeira região (geralmente EUA)
      const firstRegion = regionOptions.first();
      const regionText = await firstRegion.textContent();
      console.log(`⏳ Selecionando região: ${regionText}`);
      await firstRegion.click();
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: path.join(screenshotsDir, '04-step1-regiao-selecionada.png'),
        fullPage: true
      });
      console.log('✓ Screenshot: 04-step1-regiao-selecionada.png');
      console.log(`✓ Região "${regionText}" selecionada`);
    } else {
      console.log('❌ ERRO: Nenhuma opção de região encontrada!');
    }

    // Procurar botão "Próximo" ou "Continuar"
    const nextButton1 = page.locator('button').filter({ hasText: /Próximo|Continuar|Next/ });
    if (await nextButton1.isVisible().catch(() => false)) {
      console.log('✓ Botão "Próximo" encontrado - clicando...');
      await nextButton1.click();
      await page.waitForTimeout(1500);
    } else {
      console.log('⚠️ Botão "Próximo" não encontrado - tentando avançar automaticamente...');
    }

    console.log('\n========================================');
    console.log('PASSO 4: STEP 2 - SELECIONAR PROPÓSITO');
    console.log('========================================\n');

    await page.screenshot({
      path: path.join(screenshotsDir, '05-step2-proposito.png'),
      fullPage: true
    });
    console.log('✓ Screenshot: 05-step2-proposito.png');

    // Verificar se step 2 está visível
    const step2Indicator = page.locator('text=/Propósito|Step 2|Passo 2|Hardware/i');
    const step2Visible = await step2Indicator.isVisible().catch(() => false);
    console.log(step2Visible ? '✓ Step 2 (Propósito) visível' : '⚠️ Step 2 não encontrado');

    // Procurar por opções de propósito
    const purposeOptions = page.locator('button').filter({ hasText: /Desenvolver|Treinar|Inferência|Produção/ });
    const purposeCount = await purposeOptions.count();
    console.log(`✓ Encontradas ${purposeCount} opções de propósito`);

    if (purposeCount > 0) {
      const firstPurpose = purposeOptions.first();
      const purposeText = await firstPurpose.textContent();
      console.log(`⏳ Selecionando propósito: ${purposeText}`);
      await firstPurpose.click();
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: path.join(screenshotsDir, '06-step2-proposito-selecionado.png'),
        fullPage: true
      });
      console.log('✓ Screenshot: 06-step2-proposito-selecionado.png');
      console.log(`✓ Propósito "${purposeText}" selecionado`);
    } else {
      console.log('❌ ERRO: Nenhuma opção de propósito encontrada!');
    }

    // Botão próximo do step 2
    const nextButton2 = page.locator('button').filter({ hasText: /Próximo|Continuar|Next/ });
    if (await nextButton2.isVisible().catch(() => false)) {
      console.log('✓ Botão "Próximo" encontrado - clicando...');
      await nextButton2.click();
      await page.waitForTimeout(2000);
    }

    console.log('\n========================================');
    console.log('PASSO 5: AGUARDANDO OFERTAS DE GPU');
    console.log('========================================\n');

    await page.screenshot({
      path: path.join(screenshotsDir, '07-carregando-ofertas.png'),
      fullPage: true
    });
    console.log('✓ Screenshot: 07-carregando-ofertas.png');

    // Aguardar ofertas de GPU carregarem
    console.log('⏳ Aguardando ofertas de GPU carregarem...');
    await page.waitForTimeout(3000);

    // Verificar se há loading indicator
    const loadingIndicator = page.locator('text=/Carregando|Loading|Buscando/i');
    if (await loadingIndicator.isVisible().catch(() => false)) {
      console.log('⏳ Indicador de carregamento detectado - aguardando...');
      await page.waitForTimeout(5000);
    }

    await page.screenshot({
      path: path.join(screenshotsDir, '08-ofertas-carregadas.png'),
      fullPage: true
    });
    console.log('✓ Screenshot: 08-ofertas-carregadas.png');

    console.log('\n========================================');
    console.log('PASSO 6: STEP 3 - SELECIONAR GPU');
    console.log('========================================\n');

    // Procurar por cards de GPU (várias estratégias)
    let gpuCards = page.locator('[class*="gpu-card"], [class*="offer-card"]');
    let gpuCount = await gpuCards.count();

    // Se não encontrou, tentar botões com nomes de GPU
    if (gpuCount === 0) {
      gpuCards = page.locator('button').filter({ hasText: /RTX|A100|H100|Tesla|GPU/ });
      gpuCount = await gpuCards.count();
    }

    console.log(`✓ Encontradas ${gpuCount} ofertas de GPU`);

    if (gpuCount > 0) {
      // Selecionar primeira GPU
      const firstGpu = gpuCards.first();
      const gpuText = await firstGpu.textContent().catch(() => 'GPU');
      console.log(`⏳ Selecionando GPU: ${gpuText.substring(0, 50)}...`);
      await firstGpu.click();
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: path.join(screenshotsDir, '09-step3-gpu-selecionada.png'),
        fullPage: true
      });
      console.log('✓ Screenshot: 09-step3-gpu-selecionada.png');
      console.log('✓ GPU selecionada');
    } else {
      console.log('❌ ERRO: Nenhuma oferta de GPU encontrada!');
      console.log('⚠️ Verificando erros de API...');

      // Verificar erros no console
      if (consoleErrors.length > 0) {
        console.log('ERROS NO CONSOLE:');
        consoleErrors.forEach(err => console.log('  - ' + err));
      }
    }

    // Botão próximo do step 3
    const nextButton3 = page.locator('button').filter({ hasText: /Próximo|Continuar|Next/ });
    if (await nextButton3.isVisible().catch(() => false)) {
      console.log('✓ Botão "Próximo" encontrado - clicando...');
      await nextButton3.click();
      await page.waitForTimeout(1500);
    }

    console.log('\n========================================');
    console.log('PASSO 7: STEP 4 - CONFIGURAR ESTRATÉGIA');
    console.log('========================================\n');

    await page.screenshot({
      path: path.join(screenshotsDir, '10-step4-estrategia.png'),
      fullPage: true
    });
    console.log('✓ Screenshot: 10-step4-estrategia.png');

    // Verificar se step 4 está visível
    const step4Indicator = page.locator('text=/Estratégia|Step 4|Passo 4|Configurar/i');
    const step4Visible = await step4Indicator.isVisible().catch(() => false);
    console.log(step4Visible ? '✓ Step 4 (Estratégia) visível' : '⚠️ Step 4 não encontrado');

    // Procurar por opções de estratégia
    const strategyOptions = page.locator('button').filter({ hasText: /Race|RoundRobin|Coldstart|Serverless/ });
    const strategyCount = await strategyOptions.count();
    console.log(`✓ Encontradas ${strategyCount} opções de estratégia`);

    if (strategyCount > 0) {
      const firstStrategy = strategyOptions.first();
      const strategyText = await firstStrategy.textContent();
      console.log(`⏳ Selecionando estratégia: ${strategyText}`);
      await firstStrategy.click();
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: path.join(screenshotsDir, '11-step4-estrategia-selecionada.png'),
        fullPage: true
      });
      console.log('✓ Screenshot: 11-step4-estrategia-selecionada.png');
      console.log(`✓ Estratégia "${strategyText}" selecionada`);
    }

    console.log('\n========================================');
    console.log('PASSO 8: FINALIZAR E RESERVAR/INICIAR');
    console.log('========================================\n');

    // Procurar botão final (Reservar, Iniciar, Deploy, etc)
    const finalButtons = [
      page.locator('button').filter({ hasText: /Reservar|Iniciar|Deploy|Criar Máquina/ }),
      page.locator('button[type="submit"]'),
      page.locator('button').filter({ hasText: /Finalizar|Confirmar/ })
    ];

    let finalButtonFound = false;
    for (const btnLocator of finalButtons) {
      if (await btnLocator.isVisible().catch(() => false)) {
        const btnText = await btnLocator.textContent();
        console.log(`✓ Botão final encontrado: "${btnText}"`);
        console.log('⏳ Clicando no botão final...');

        await page.screenshot({
          path: path.join(screenshotsDir, '12-antes-de-reservar.png'),
          fullPage: true
        });
        console.log('✓ Screenshot: 12-antes-de-reservar.png');

        await btnLocator.click();
        finalButtonFound = true;
        break;
      }
    }

    if (!finalButtonFound) {
      console.log('❌ ERRO: Botão final não encontrado!');
    }

    // Aguardar processamento
    console.log('⏳ Aguardando processamento da reserva...');
    await page.waitForTimeout(5000);

    await page.screenshot({
      path: path.join(screenshotsDir, '13-apos-reservar.png'),
      fullPage: true
    });
    console.log('✓ Screenshot: 13-apos-reservar.png');

    console.log('\n========================================');
    console.log('PASSO 9: VERIFICAR LISTA DE MÁQUINAS');
    console.log('========================================\n');

    // Tentar navegar para página de máquinas
    const machinesLink = page.locator('a').filter({ hasText: /Máquinas|Machines|Instâncias/ });
    if (await machinesLink.isVisible().catch(() => false)) {
      console.log('✓ Link para Máquinas encontrado - navegando...');
      await machinesLink.click();
      await page.waitForTimeout(2000);
    } else {
      // Tentar URL direta
      console.log('⏳ Navegando diretamente para /app/machines...');
      await page.goto('http://localhost:4894/app/machines');
      await page.waitForTimeout(2000);
    }

    await page.screenshot({
      path: path.join(screenshotsDir, '14-lista-de-maquinas.png'),
      fullPage: true
    });
    console.log('✓ Screenshot: 14-lista-de-maquinas.png');

    // Verificar se há máquinas na lista
    const machineCards = page.locator('[class*="machine-card"], [class*="instance-card"]');
    const machineCount = await machineCards.count();
    console.log(`✓ Encontradas ${machineCount} máquinas na lista`);

    console.log('\n========================================');
    console.log('RELATÓRIO FINAL');
    console.log('========================================\n');

    console.log(`Total de logs no console: ${consoleLogs.length}`);
    console.log(`Total de erros no console: ${consoleErrors.length}`);

    if (consoleErrors.length > 0) {
      console.log('\n⚠️ ERROS DETECTADOS NO CONSOLE:');
      consoleErrors.forEach((err, i) => {
        console.log(`${i + 1}. ${err}`);
      });
    }

    // Salvar relatório completo
    const report = {
      timestamp: new Date().toISOString(),
      steps: {
        login: 'OK',
        wizardOpen: wizardVisible || 'VERIFICAR',
        step1_region: regionCount > 0 ? 'OK' : 'FALHOU',
        step2_purpose: purposeCount > 0 ? 'OK' : 'FALHOU',
        step3_gpu: gpuCount > 0 ? 'OK' : 'FALHOU',
        step4_strategy: strategyCount > 0 ? 'OK' : 'VERIFICAR',
        finalButton: finalButtonFound ? 'OK' : 'FALHOU',
        machinesList: machineCount > 0 ? 'OK' : 'NENHUMA MÁQUINA'
      },
      consoleLogs: consoleLogs,
      consoleErrors: consoleErrors,
      screenshots: [
        '01-login-auto.png',
        '02-dashboard-inicial.png',
        '03-wizard-aberto.png',
        '04-step1-regiao-selecionada.png',
        '05-step2-proposito.png',
        '06-step2-proposito-selecionado.png',
        '07-carregando-ofertas.png',
        '08-ofertas-carregadas.png',
        '09-step3-gpu-selecionada.png',
        '10-step4-estrategia.png',
        '11-step4-estrategia-selecionada.png',
        '12-antes-de-reservar.png',
        '13-apos-reservar.png',
        '14-lista-de-maquinas.png'
      ]
    };

    fs.writeFileSync(
      path.join(screenshotsDir, 'wizard-complete-report.json'),
      JSON.stringify(report, null, 2)
    );

    console.log('\n✓ Relatório salvo em: wizard-interactive-screenshots/wizard-complete-report.json');
    console.log('✓ Screenshots salvos em: wizard-interactive-screenshots/\n');

    console.log('========================================\n');
  });
});
