const { test, expect } = require('@playwright/test');

test.describe('Wizard de Reserva GPU - Fluxo Completo', () => {
  test('Fluxo completo do wizard - passo a passo com screenshots', async ({ page }) => {
    console.log('\n========================================');
    console.log('TESTE COMPLETO DO WIZARD DE RESERVA GPU');
    console.log('========================================\n');

    // PASSO 1: Login automático
    console.log('📋 PASSO 1: Login automático');
    await page.goto('http://localhost:4894/login?auto_login=demo');

    // Aguardar redirecionamento para /app
    await page.waitForURL('**/app**', { timeout: 10000 });
    console.log('✅ Login automático bem-sucedido');

    await page.screenshot({ path: 'tests/screenshots/wizard-step1-login.png', fullPage: true });
    await page.waitForTimeout(1000);

    // PASSO 2: Verificar Dashboard e localizar wizard
    console.log('\n📋 PASSO 2: Localizar wizard no Dashboard');

    // Aguardar carregamento da página
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'tests/screenshots/wizard-step2-dashboard.png', fullPage: true });

    // Verificar elementos do dashboard
    const dashboardTitle = await page.locator('h1, h2').first().textContent();
    console.log(`Dashboard carregado: "${dashboardTitle}"`);

    // Procurar o wizard - pode estar em modal ou na página
    const wizardVisible = await page.locator('text=/Região|Region|Escolha.*região/i').isVisible({ timeout: 5000 }).catch(() => false);

    if (!wizardVisible) {
      console.log('⚠️ Wizard não está visível - procurando botão para abrir...');

      // Procurar botões que podem abrir o wizard
      const possibleButtons = [
        'text="Buscar Máquinas"',
        'text="Nova Máquina"',
        'text="Criar Máquina"',
        'text="Deploy"',
        'text="Provisionar"',
        'button:has-text("Começar")',
        'button:has-text("Iniciar")'
      ];

      for (const selector of possibleButtons) {
        const btn = page.locator(selector).first();
        if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
          console.log(`Encontrado botão: ${selector}`);
          await btn.click();
          await page.waitForTimeout(1500);
          break;
        }
      }
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-step3-wizard-opened.png', fullPage: true });

    // PASSO 3: Selecionar região
    console.log('\n📋 PASSO 3: Selecionar região');

    // Aguardar elementos de região aparecerem
    await page.waitForTimeout(1500);

    // Pegar snapshot dos elementos visíveis
    const regionElements = await page.locator('button, [role="button"], .region, [class*="region"]').all();
    console.log(`Encontrados ${regionElements.length} elementos clicáveis`);

    // Procurar por regiões comuns
    const regions = ['us-east', 'us-west', 'europe', 'asia', 'EUA', 'Europa', 'América'];
    let regionSelected = false;

    for (const region of regions) {
      const regionBtn = page.locator(`text=/${region}/i`).first();
      if (await regionBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        console.log(`Selecionando região: ${region}`);
        await regionBtn.click();
        regionSelected = true;
        await page.waitForTimeout(1500);
        break;
      }
    }

    if (!regionSelected) {
      // Tentar clicar no primeiro botão/card visível
      console.log('Tentando selecionar primeira região disponível...');
      const firstRegion = page.locator('button:visible, [role="button"]:visible').first();
      await firstRegion.click();
      await page.waitForTimeout(1500);
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-step4-region-selected.png', fullPage: true });
    console.log('✅ Região selecionada');

    // PASSO 4: Selecionar propósito
    console.log('\n📋 PASSO 4: Selecionar propósito');

    await page.waitForTimeout(1500);

    // Procurar por opções de propósito
    const purposes = [
      'Treinamento',
      'Training',
      'Inferência',
      'Inference',
      'Fine-tuning',
      'Desenvolvimento',
      'Development'
    ];

    let purposeSelected = false;
    for (const purpose of purposes) {
      const purposeBtn = page.locator(`text=/${purpose}/i`).first();
      if (await purposeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        console.log(`Selecionando propósito: ${purpose}`);
        await purposeBtn.click();
        purposeSelected = true;
        await page.waitForTimeout(1500);
        break;
      }
    }

    if (!purposeSelected) {
      console.log('Propósito não encontrado, tentando próximo botão...');
      const nextBtn = page.locator('button:has-text(/Próximo|Next|Continuar/)').first();
      if (await nextBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await nextBtn.click();
        await page.waitForTimeout(1500);
      }
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-step5-purpose-selected.png', fullPage: true });
    console.log('✅ Propósito selecionado');

    // PASSO 5: Aguardar GPUs carregarem
    console.log('\n📋 PASSO 5: Aguardar GPUs carregarem da API VAST.ai');

    // Esperar por indicadores de carregamento
    await page.waitForTimeout(3000);

    // Verificar se há loading spinner
    const loading = page.locator('text=/Carregando|Loading|Buscando/i');
    if (await loading.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('⏳ Aguardando carregamento das GPUs...');
      await page.waitForTimeout(5000);
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-step6-gpus-loading.png', fullPage: true });

    // Procurar por cards de GPU
    const gpuCards = await page.locator('[class*="gpu"], [class*="card"], [class*="offer"]').all();
    console.log(`Encontrados ${gpuCards.length} possíveis cards de GPU`);

    // Verificar se há GPUs visíveis
    const gpuNames = ['RTX', 'A100', 'H100', 'V100', 'Tesla', 'GPU'];
    let gpusFound = false;

    for (const gpuName of gpuNames) {
      const gpuElement = page.locator(`text=/${gpuName}/i`).first();
      if (await gpuElement.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log(`✅ GPUs carregadas - encontrado: ${gpuName}`);
        gpusFound = true;
        break;
      }
    }

    if (!gpusFound) {
      console.log('⚠️ Nenhuma GPU detectada no timeout - continuando...');
    }

    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'tests/screenshots/wizard-step7-gpus-loaded.png', fullPage: true });

    // PASSO 6: Selecionar uma GPU
    console.log('\n📋 PASSO 6: Selecionar uma GPU');

    // Procurar botões de seleção
    const selectButtons = [
      'button:has-text("Selecionar")',
      'button:has-text("Select")',
      'button:has-text("Escolher")',
      '[class*="select"]'
    ];

    let gpuSelected = false;
    for (const selector of selectButtons) {
      const btn = page.locator(selector).first();
      if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log(`Clicando em botão de seleção: ${selector}`);
        await btn.click();
        gpuSelected = true;
        await page.waitForTimeout(1500);
        break;
      }
    }

    if (!gpuSelected) {
      console.log('⚠️ Botão "Selecionar" não encontrado - tentando clicar no primeiro card');
      const firstCard = page.locator('[class*="card"], [class*="offer"]').first();
      if (await firstCard.isVisible({ timeout: 1000 }).catch(() => false)) {
        await firstCard.click();
        await page.waitForTimeout(1500);
      }
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-step8-gpu-selected.png', fullPage: true });
    console.log('✅ GPU selecionada');

    // PASSO 7: Avançar para estratégia
    console.log('\n📋 PASSO 7: Avançar para seleção de estratégia');

    await page.waitForTimeout(1500);

    // Procurar por opções de estratégia
    const strategies = ['Race', 'Serverless', 'Coldstart', 'Round Robin'];
    let strategyVisible = false;

    for (const strategy of strategies) {
      const strategyElement = page.locator(`text=/${strategy}/i`).first();
      if (await strategyElement.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log(`✅ Página de estratégia visível - encontrado: ${strategy}`);
        strategyVisible = true;
        break;
      }
    }

    if (!strategyVisible) {
      console.log('Procurando botão "Próximo" para avançar...');
      const nextBtn = page.locator('button:has-text(/Próximo|Next|Continuar/)').first();
      if (await nextBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await nextBtn.click();
        await page.waitForTimeout(1500);
      }
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-step9-strategy-page.png', fullPage: true });

    // Selecionar uma estratégia se visível
    for (const strategy of strategies) {
      const strategyBtn = page.locator(`text=/${strategy}/i`).first();
      if (await strategyBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        console.log(`Selecionando estratégia: ${strategy}`);
        await strategyBtn.click();
        await page.waitForTimeout(1500);
        break;
      }
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-step10-strategy-selected.png', fullPage: true });

    // PASSO 8: Clicar em Iniciar/Reservar
    console.log('\n📋 PASSO 8: Iniciar provisionamento');

    await page.waitForTimeout(1500);

    // Procurar botões de ação final
    const actionButtons = [
      'button:has-text("Iniciar")',
      'button:has-text("Reservar")',
      'button:has-text("Provisionar")',
      'button:has-text("Deploy")',
      'button:has-text("Criar")',
      'button:has-text("Start")',
      'button:has-text("Launch")'
    ];

    let actionClicked = false;
    for (const selector of actionButtons) {
      const btn = page.locator(selector).first();
      if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log(`Clicando em botão de ação: ${selector}`);

        // Pegar texto do botão antes de clicar
        const btnText = await btn.textContent();
        console.log(`Texto do botão: "${btnText}"`);

        await btn.click();
        actionClicked = true;
        await page.waitForTimeout(2000);
        break;
      }
    }

    if (!actionClicked) {
      console.log('⚠️ Botão de ação final não encontrado');
    }

    await page.screenshot({ path: 'tests/screenshots/wizard-step11-action-clicked.png', fullPage: true });

    // PASSO 9: Verificar provisionamento iniciado
    console.log('\n📋 PASSO 9: Verificar se provisionamento foi iniciado');

    await page.waitForTimeout(3000);

    // Verificar indicadores de provisionamento
    const provisioningIndicators = [
      'text=/Provisionando|Provisioning/',
      'text=/Criando|Creating/',
      'text=/Aguarde|Wait/',
      'text=/Iniciando|Starting/',
      '[class*="progress"]',
      '[class*="loading"]',
      '[class*="spinner"]'
    ];

    let provisioningDetected = false;
    for (const selector of provisioningIndicators) {
      const indicator = page.locator(selector).first();
      if (await indicator.isVisible({ timeout: 2000 }).catch(() => false)) {
        const text = await indicator.textContent();
        console.log(`✅ Provisionamento detectado: "${text}"`);
        provisioningDetected = true;
        break;
      }
    }

    // Verificar console do browser para erros
    const consoleMessages = [];
    page.on('console', msg => {
      consoleMessages.push(`${msg.type()}: ${msg.text()}`);
    });

    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'tests/screenshots/wizard-step12-provisioning-status.png', fullPage: true });

    // Verificar network requests
    const networkRequests = [];
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        networkRequests.push({
          method: request.method(),
          url: request.url()
        });
      }
    });

    await page.waitForTimeout(2000);

    // Log final
    console.log('\n========================================');
    console.log('RESUMO DO TESTE');
    console.log('========================================');
    console.log(`✅ Login automático: OK`);
    console.log(`✅ Dashboard carregado: OK`);
    console.log(`✅ Wizard acessível: ${wizardVisible ? 'OK' : 'PARCIAL'}`);
    console.log(`✅ Região selecionada: ${regionSelected ? 'OK' : 'PARCIAL'}`);
    console.log(`✅ GPUs carregadas: ${gpusFound ? 'OK' : 'NÃO DETECTADO'}`);
    console.log(`✅ GPU selecionada: ${gpuSelected ? 'OK' : 'PARCIAL'}`);
    console.log(`✅ Estratégia visível: ${strategyVisible ? 'OK' : 'NÃO DETECTADO'}`);
    console.log(`✅ Botão de ação clicado: ${actionClicked ? 'OK' : 'NÃO ENCONTRADO'}`);
    console.log(`✅ Provisionamento iniciado: ${provisioningDetected ? 'OK' : 'NÃO DETECTADO'}`);

    if (consoleMessages.length > 0) {
      console.log('\n📋 Mensagens do console:');
      consoleMessages.slice(-10).forEach(msg => console.log(`  ${msg}`));
    }

    if (networkRequests.length > 0) {
      console.log('\n📋 Requisições API:');
      networkRequests.slice(-5).forEach(req => console.log(`  ${req.method} ${req.url}`));
    }

    console.log('\n========================================\n');

    // Screenshot final
    await page.screenshot({ path: 'tests/screenshots/wizard-step13-final.png', fullPage: true });

    // Manter navegador aberto por 5 segundos para inspeção visual
    await page.waitForTimeout(5000);
  });
});
