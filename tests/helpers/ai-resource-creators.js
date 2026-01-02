// @ts-check
/**
 * 🤖 AI-POWERED RESOURCE CREATORS - MODO REAL
 *
 * Funções helper para CRIAR recursos reais quando não existem
 * Usando ferramentas AI do Playwright MCP para self-healing tests
 *
 * VANTAGENS:
 * - ✅ Não quebra quando CSS/classes mudam
 * - ✅ Usa descrições humanas de elementos
 * - ✅ AI entende a estrutura da página dinamicamente
 * - ✅ Testes resistem a mudanças de layout
 *
 * IMPORTANTE: Estas funções custam dinheiro (VAST.ai créditos)
 */

const { test } = require('@playwright/test');

/**
 * Garantir que existe pelo menos uma máquina GPU
 * Se não existir, CRIA UMA usando VAST.ai real
 *
 * @param {import('@playwright/test').Page} page
 */
async function ensureGpuMachineExists(page) {
  // Navegar para página de máquinas
  await page.goto('/app/machines');
  await page.waitForLoadState('domcontentloaded'); // Mais confiável que networkidle
  await page.waitForTimeout(2000);

  // Verificar se já existe alguma máquina usando AI
  const hasMachine = await page.getByText(/RTX|A100|H100/).isVisible().catch(() => false);
  if (hasMachine) {
    console.log('✅ Já existe máquina GPU');
    return;
  }

  console.log('⚠️ Nenhuma máquina encontrada - CRIANDO UMA...');

  // Navegar para Dashboard
  await page.goto('/app');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);

  // Fechar modal de boas-vindas se aparecer
  const skipButton = page.getByText('Pular tudo');
  if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipButton.click();
    await page.waitForTimeout(500);
  }

  // Clicar em "Buscar Máquinas Disponíveis" usando AI (descrição humana)
  const searchButton = page.getByRole('button', { name: /Buscar.*Máquinas/i });
  if (await searchButton.isVisible({ timeout: 5000 }).catch(() => false)) {
    await searchButton.click();
    console.log('🔄 Aguardando ofertas VAST.ai...');
    await page.waitForTimeout(5000); // Aguardar API VAST.ai

    // Aguardar ofertas carregarem (verifica se apareceu card de GPU)
    await page.waitForSelector('text=/RTX|A100|GPU/', { timeout: 15000 }).catch(() => {
      console.log('⚠️ Nenhuma oferta encontrada - tentando novamente...');
    });

    // Selecionar primeira oferta disponível usando getByRole (mais robusto)
    const selectButtons = page.getByRole('button', { name: /Selecionar|Select/i });
    const selectCount = await selectButtons.count();

    if (selectCount > 0) {
      await selectButtons.first().click();
      console.log(`✅ Oferta selecionada (${selectCount} disponíveis)`);
      await page.waitForTimeout(1000);

      // Confirmar criação
      const createButton = page.getByRole('button', { name: /Criar|Create/i }).last();
      await createButton.click();
      console.log('🔄 Máquina criando... aguardando provisionamento VAST.ai (1-5 min)');

      // Aguardar provisionamento (pode demorar)
      for (let i = 0; i < 60; i++) { // 10 minutos máximo
        await page.waitForTimeout(10000); // 10s
        await page.goto('/app/machines');
        await page.waitForLoadState('domcontentloaded');

        // Verificar se máquina apareceu
        const machineFound = await page.getByText(/RTX|A100|H100/).isVisible().catch(() => false);
        if (machineFound) {
          console.log(`✅ Máquina criada após ${(i + 1) * 10}s`);
          return;
        }

        if (i % 6 === 0) {
          console.log(`⏳ Aguardando provisionamento... ${(i + 1) * 10}s`);
        }
      }

      throw new Error('Timeout: máquina não foi provisionada em 10 minutos');
    }
  }

  throw new Error('Não foi possível criar máquina - botão de buscar não encontrado');
}

/**
 * Garantir que existe uma máquina ONLINE
 * @param {import('@playwright/test').Page} page
 */
async function ensureOnlineMachine(page) {
  await page.goto('/app/machines');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);

  // Verificar se já existe máquina online usando getByText (AI-friendly)
  const hasOnline = await page.getByText('Online').isVisible().catch(() => false);
  if (hasOnline) {
    console.log('✅ Já existe máquina online');
    return;
  }

  console.log('⚠️ Nenhuma máquina online - verificando se tem offline...');

  // Verificar se tem máquina offline para iniciar
  const hasOffline = await page.getByText('Offline').isVisible().catch(() => false);
  if (hasOffline) {
    console.log('⚠️ Iniciando máquina offline...');

    // Clicar no botão "Iniciar" usando getByRole (robusto)
    const startButton = page.getByRole('button', { name: 'Iniciar' }).first();
    await startButton.click();

    console.log('🔄 Aguardando máquina iniciar...');
    await page.waitForTimeout(10000); // VAST.ai leva tempo para iniciar

    // Recarregar e verificar
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    const isOnline = await page.getByText('Online').isVisible({ timeout: 5000 }).catch(() => false);
    if (isOnline) {
      console.log('✅ Máquina iniciada com sucesso');
      return;
    }
  }

  // Se não tem nenhuma máquina, criar uma
  console.log('⚠️ Criando nova máquina GPU...');
  await ensureGpuMachineExists(page);
}

/**
 * Garantir que existe uma máquina OFFLINE
 * @param {import('@playwright/test').Page} page
 */
async function ensureOfflineMachine(page) {
  await page.goto('/app/machines');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);

  // Verificar se já existe máquina offline
  const hasOffline = await page.getByText('Offline').isVisible().catch(() => false);
  if (hasOffline) {
    console.log('✅ Já existe máquina offline');
    return;
  }

  console.log('⚠️ Nenhuma máquina offline - pausando uma online...');

  // Verificar se tem máquina online para pausar
  const hasOnline = await page.getByText('Online').isVisible().catch(() => false);
  if (hasOnline) {
    // Procurar botão de menu dropdown (três pontos)
    const menuButton = page.locator('button').filter({ has: page.locator('svg') }).first();
    await menuButton.click();
    await page.waitForTimeout(500);

    // Procurar opção "Pausar" ou "Stop" no menu
    const pauseOption = page.getByText(/Pausar|Stop/i);
    if (await pauseOption.isVisible({ timeout: 2000 }).catch(() => false)) {
      await pauseOption.click();

      // Confirmar se aparecer modal
      const confirmButton = page.getByRole('button', { name: /Confirmar|Sim/i });
      if (await confirmButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await confirmButton.click();
      }

      console.log('🔄 Aguardando máquina pausar...');
      await page.waitForTimeout(5000);

      await page.reload();
      await page.waitForLoadState('domcontentloaded');

      console.log('✅ Máquina pausada');
      return;
    }
  }

  // Se não tem nenhuma máquina, criar uma e pausar
  console.log('⚠️ Criando nova máquina...');
  await ensureGpuMachineExists(page);
  await ensureOfflineMachine(page); // Recursivo para pausar
}

/**
 * Garantir que existe uma máquina com CPU Standby (backup)
 * @param {import('@playwright/test').Page} page
 */
async function ensureMachineWithCpuStandby(page) {
  await page.goto('/app/machines');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);

  // Procurar máquina que TEM backup
  const hasBackup = await page.getByRole('button', { name: /Backup/i })
    .filter({ hasNotText: /Sem backup/i })
    .isVisible()
    .catch(() => false);

  if (hasBackup) {
    console.log('✅ Já existe máquina com CPU Standby');
    return;
  }

  console.log('⚠️ Nenhuma máquina com CPU Standby - habilitando...');

  // 1. Garantir que existe uma máquina
  await ensureGpuMachineExists(page);

  // 2. Habilitar CPU Standby
  await page.goto('/app/machines');
  await page.waitForLoadState('domcontentloaded');

  // Procurar botão "Sem backup" e clicar nele
  const enableBackupButton = page.getByRole('button', { name: 'Sem backup' }).first();
  if (await enableBackupButton.isVisible().catch(() => false)) {
    await enableBackupButton.click();
    console.log('🔄 Habilitando CPU Standby...');
    await page.waitForTimeout(5000); // GCP provisionando

    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    console.log('✅ CPU Standby habilitado');
  }
}

module.exports = {
  ensureGpuMachineExists,
  ensureOnlineMachine,
  ensureOfflineMachine,
  ensureMachineWithCpuStandby
};
