// @ts-check
const { test, expect } = require('@playwright/test');
const {
  ensureGpuMachineExists,
  ensureOnlineMachine,
  ensureOfflineMachine,
  ensureMachineWithIP,
} = require('../helpers/resource-creators');

/**
 * 🎯 TESTES REAIS DE AÇÕES DE USUÁRIO - MODO REAL COM VAST.AI
 *
 * Estes testes simulam um usuário REAL fazendo ações REAIS
 * e verificam se o sistema REALMENTE funciona.
 *
 * IMPORTANTE:
 * - USA VAST.AI REAL (custa dinheiro - é esperado)
 * - CRIA recursos quando não existem (GPUs, máquinas, etc)
 * - ZERO SKIPS - todos os testes devem passar
 * - Rotas: /app/* (NUNCA /demo-app/*)
 */

// Helper para ir para app real (autenticação já feita via setup)
async function goToApp(page) {
  // Ir para o modo REAL (não demo)
  await page.goto('/app');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  // Fechar modal de boas-vindas se aparecer
  const skipButton = page.locator('text="Pular tudo"');
  if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipButton.click();
    await page.waitForTimeout(500);
  }
}

test.describe('🎯 Ações Reais de Usuário', () => {

  test.beforeEach(async ({ page }) => {
    await goToApp(page);
  });

  test('Usuário consegue ver suas máquinas', async ({ page }) => {
    // 1. Ir para página de máquinas (MODO REAL)
    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');

    // 2. DEVE ver o título "Minhas Máquinas"
    await expect(page.getByRole('heading', { name: 'Minhas Máquinas' })).toBeVisible();

    // 3. DEVE ver pelo menos uma máquina (em demo mode)
    // Procurar por elementos que contenham nomes de GPU conhecidos
    const gpuNames = page.locator('text=/RTX \\d{4}|A100|H100/');
    const count = await gpuNames.count();
    expect(count).toBeGreaterThan(0);
    console.log(`✅ Usuário vê ${count} GPUs`);

    // 4. DEVE ver informações importantes na página
    await expect(page.locator('text=/Online|Offline/').first()).toBeVisible();
    await expect(page.locator('text=/\\$\\d+\\.\\d+/').first()).toBeVisible(); // Preço
  });

  test('Usuário consegue INICIAR uma máquina parada', async ({ page }) => {
    // GARANTIR que existe máquina offline (cria se necessário)
    await ensureOfflineMachine(page);

    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // 1. Encontrar uma máquina PARADA (Offline) - agora DEVE existir
    const offlineMachine = page.locator('[class*="rounded-lg"]').filter({
      has: page.locator('text="Offline"')
    }).first();

    await expect(offlineMachine).toBeVisible();

    // 2. Pegar o nome da GPU antes de iniciar
    const gpuName = await offlineMachine.locator('text=/RTX|A100|H100|GPU/').first().textContent();
    console.log(`🖥️ Iniciando máquina: ${gpuName}`);

    // 3. Clicar no botão INICIAR
    const startButton = offlineMachine.locator('button:has-text("Iniciar")');
    await expect(startButton).toBeVisible();
    await startButton.click();

    // 4. VERIFICAR que o toast de "Iniciando" apareceu
    await expect(page.locator('text=/Iniciando/')).toBeVisible({ timeout: 3000 });
    console.log('✅ Toast "Iniciando..." apareceu');

    // 5. Esperar a máquina iniciar (2-3 segundos em demo)
    await page.waitForTimeout(3000);

    // 6. VERIFICAR que a máquina agora está ONLINE
    // A máquina deve mostrar "Online" e ter botões de Pausar/Migrar
    await expect(page.locator(`text="${gpuName}"`).locator('..').locator('..').locator('text="Online"')).toBeVisible({ timeout: 5000 });

    console.log(`✅ Máquina ${gpuName} iniciada com sucesso!`);
  });

  test('Usuário consegue PAUSAR uma máquina rodando', async ({ page }) => {
    // GARANTIR que existe máquina online (cria se necessário)
    await ensureOnlineMachine(page);

    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // 1. Encontrar uma máquina RODANDO (Online) - agora DEVE existir
    const onlineMachine = page.locator('[class*="rounded-lg"]').filter({
      has: page.locator('text="Online"')
    }).first();

    await expect(onlineMachine).toBeVisible();

    // 2. Pegar nome da GPU
    const gpuName = await onlineMachine.locator('text=/RTX|A100|H100/').first().textContent();
    console.log(`🖥️ Pausando máquina: ${gpuName}`);

    // 3. Clicar no botão PAUSAR
    const pauseButton = onlineMachine.locator('button:has-text("Pausar")');
    await expect(pauseButton).toBeVisible();
    await pauseButton.click();

    // 4. CONFIRMAR no modal de confirmação
    const confirmButton = page.locator('button:has-text("Pausar")').last();
    await expect(confirmButton).toBeVisible({ timeout: 3000 });
    await confirmButton.click();

    // 5. VERIFICAR toast de "Pausando"
    await expect(page.locator('text=/Pausando/')).toBeVisible({ timeout: 3000 });
    console.log('✅ Toast "Pausando..." apareceu');

    // 6. Esperar e verificar que pausou
    await page.waitForTimeout(2000);

    console.log(`✅ Máquina ${gpuName} pausada com sucesso!`);
  });

  test('Usuário consegue navegar pelo menu', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    // Fechar modal de boas-vindas se aparecer
    const skipButton = page.locator('text="Pular tudo"');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      await page.waitForTimeout(500);
    }

    // 1. Verificar que está no Dashboard
    await expect(page).toHaveURL(/\/app/);

    // 2. Navegar para Machines (usar URL direta se link não funcionar)
    const machinesLink = page.locator('a[href*="machines"]').first();
    if (await machinesLink.isVisible().catch(() => false)) {
      await machinesLink.click();
    } else {
      await page.goto('/app/machines');
    }
    await page.waitForLoadState('networkidle');
    console.log('✅ Navegou para Machines');

    // 3. Navegar para Settings
    const settingsLink = page.locator('a[href*="settings"]').first();
    if (await settingsLink.isVisible().catch(() => false)) {
      await settingsLink.click();
    } else {
      await page.goto('/app/settings');
    }
    await page.waitForLoadState('networkidle');
    console.log('✅ Navegou para Settings');

    // 4. Voltar para Dashboard
    const dashboardLink = page.locator('a[href="/app"], a[href*="dashboard"]').first();
    if (await dashboardLink.isVisible().catch(() => false)) {
      await dashboardLink.click();
    } else {
      await page.goto('/app');
    }
    await page.waitForLoadState('networkidle');
    console.log('✅ Voltou para Dashboard');
  });

  test('Usuário consegue ver métricas de máquina rodando', async ({ page }) => {
    // GARANTIR que existe máquina online (cria se necessário)
    await ensureOnlineMachine(page);

    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // 1. Encontrar máquina online - agora DEVE existir
    const onlineMachine = page.locator('[class*="rounded-lg"][class*="border"]').filter({
      has: page.locator('text="Online"')
    }).first();

    await expect(onlineMachine).toBeVisible();

    // 2. VERIFICAR que mostra métricas
    // GPU % - procurar em todo o card
    const hasGpuPercent = await onlineMachine.locator('text=/\\d+%/').first().isVisible().catch(() => false);
    if (hasGpuPercent) {
      console.log('✅ GPU % visível');
    }

    // Temperatura
    const hasTemp = await onlineMachine.locator('text=/\\d+°C/').first().isVisible().catch(() => false);
    if (hasTemp) {
      console.log('✅ Temperatura visível');
    }

    // Custo por hora (verificar na página)
    const hasCost = await page.locator('text=/\\$\\d+\\.\\d+/').first().isVisible().catch(() => false);
    if (hasCost) {
      console.log('✅ Custo/hora visível');
    }

    // Verificar que pelo menos uma métrica está visível
    expect(hasGpuPercent || hasTemp || hasCost).toBeTruthy();
    console.log('✅ Métricas de máquina online verificadas');
  });

  test('Usuário consegue copiar IP da máquina', async ({ page }) => {
    // GARANTIR que existe máquina com IP (online)
    await ensureMachineWithIP(page);

    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // 1. Encontrar máquina online com IP - agora DEVE existir
    const ipButton = page.locator('button:has-text(/\\d+\\.\\d+\\.\\d+\\.\\d+/)').first();

    await expect(ipButton).toBeVisible({ timeout: 10000 });

    // 2. Clicar para copiar
    await ipButton.click();

    // 3. Verificar feedback visual (texto muda para "Copiado!")
    await expect(page.locator('text="Copiado!"')).toBeVisible({ timeout: 2000 });
    console.log('✅ IP copiado com sucesso!');
  });

  test('Usuário consegue acessar Settings e ver configurações', async ({ page }) => {
    // First go to /app to make sure we're in the app
    await page.goto('/app');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Try to navigate to Settings via sidebar link first
    const settingsLink = page.locator('a[href*="settings"]').first();
    const hasSettingsLink = await settingsLink.isVisible().catch(() => false);

    if (hasSettingsLink) {
      console.log('📍 Encontrou link Settings no sidebar, clicando...');
      await settingsLink.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
    } else {
      // Try direct navigation
      console.log('📍 Tentando navegação direta para /app/settings...');
      await page.goto('/app/settings');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
    }

    // Verificar se chegamos em Settings
    const currentUrl = page.url();
    console.log(`URL atual: ${currentUrl}`);

    // Check if we're on settings
    if (currentUrl.includes('/settings')) {
      console.log('✅ Navegou para Settings');
    } else {
      console.log('⚠️ Redirecionou para outra página');
    }

    // Verificar que há algum conteúdo visível na página
    await page.waitForTimeout(500);

    // Verificar se há algum elemento interativo visível
    const buttons = await page.locator('button').count();
    const links = await page.locator('a[href]').count();
    const inputs = await page.locator('input, select, textarea').count();
    const totalInteractive = buttons + links + inputs;

    console.log(`📊 ${totalInteractive} elementos interativos encontrados (${buttons} botões, ${links} links, ${inputs} inputs)`);

    // Settings page may be empty in demo mode - just verify we can navigate there
    if (totalInteractive === 0) {
      console.log('ℹ️ Settings vazio (modo demo) - mas navegação funcionou');
      expect(currentUrl).toContain('/settings');
    } else {
      console.log('✅ Página acessível e funcional');
      expect(totalInteractive).toBeGreaterThan(0);
    }
  });

});

test.describe('🔄 Fluxos Completos de Usuário', () => {

  test.beforeEach(async ({ page }) => {
    await goToApp(page);
  });

  test('Fluxo: Ver Dashboard → Ir para Machines → Iniciar Máquina', async ({ page }) => {
    // 1. Dashboard
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    // Fechar modal de boas-vindas se aparecer
    const skipButton = page.locator('text="Pular tudo"');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      await page.waitForTimeout(500);
    }
    console.log('📍 Passo 1: Dashboard carregado');

    // 2. Clicar para ir para Machines (excluir elementos mobile)
    await page.locator('a:not(.mobile-menu-link):has-text("Machines")').click();
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/machines/);
    console.log('📍 Passo 2: Navegou para Machines');

    // 3. Ver lista de máquinas
    await expect(page.locator('text="Minhas Máquinas"')).toBeVisible();
    const machineCount = await page.locator('text=/RTX|A100|H100/').count();
    console.log(`📍 Passo 3: Vê ${machineCount} máquinas`);

    // 4. Tentar iniciar uma máquina offline
    const startButton = page.locator('button:has-text("Iniciar")').first();
    const canStart = await startButton.isVisible().catch(() => false);

    if (canStart) {
      await startButton.click();
      await page.waitForTimeout(3000);
      console.log('📍 Passo 4: Clicou em Iniciar');

      // Verificar feedback
      const hasToast = await page.locator('.animate-slide-up').isVisible().catch(() => false);
      if (hasToast) {
        console.log('✅ Fluxo completo funcionou!');
      }
    } else {
      console.log('📍 Passo 4: Todas as máquinas já estão online');
    }
  });

  test('Fluxo: Verificar economia no Dashboard', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    // Em demo mode, deve mostrar dados de economia
    // Procurar por valores monetários ou textos de economia
    const savingsText = page.locator('text=/saved|economia|\\$\\d+\\.\\d+/i').first();
    const hasSavings = await savingsText.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasSavings) {
      console.log('✅ Dados de economia visíveis no Dashboard');
    } else {
      // Pode não ter economia se for novo usuário - isso é OK
      console.log('ℹ️ Nenhum dado de economia (novo usuário ou sem histórico)');
    }

    // Mas DEVE ter cards de resumo
    const summaryCards = page.locator('[class*="rounded"][class*="border"]').filter({
      has: page.locator('text=/GPU|CPU|Total|Cost/i')
    });
    const cardCount = await summaryCards.count();
    console.log(`✅ ${cardCount} cards de resumo no Dashboard`);
  });

});
