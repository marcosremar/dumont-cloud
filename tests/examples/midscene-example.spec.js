// @ts-check
/**
 * 🤖 EXEMPLO: Testes AI-Powered com Midscene.js
 *
 * Este arquivo demonstra como usar Midscene.js para criar testes que:
 * - ✅ Usam linguagem natural para interagir com elementos
 * - ✅ Reconhecem elementos visualmente via OpenAI Vision
 * - ✅ São verdadeiramente self-healing (não dependem de seletores)
 * - ✅ Podem fazer queries inteligentes sobre o estado da página
 *
 * REQUISITOS:
 * - OPENAI_API_KEY configurada em .env
 * - @midscene/web instalado (npm install)
 *
 * CUSTO:
 * - Cada operação AI custa aproximadamente $0.01-0.03
 * - Use com moderação em CI/CD
 *
 * @see https://midscenejs.com/
 */

const { test, expect } = require('@playwright/test');
const { setupMidsceneTest, checkApiKey, logCostWarning } = require('../helpers/midscene-helpers');

// Helper para navegação com tratamento de modal de boas-vindas
async function goToPage(page, path) {
  await page.goto(path);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);

  // Fechar modal de boas-vindas se aparecer
  const skipButton = page.getByText('Pular tudo');
  if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipButton.click();
    await page.waitForTimeout(500);
  }
}

test.describe('🤖 Midscene.js: Testes AI-Powered', () => {

  test.beforeEach(async ({ page }) => {
    // Login é feito automaticamente pelo auth.setup.js via storageState
    // Verificar custo antes de cada teste
    if (checkApiKey()) {
      logCostWarning('action');
    }
  });

  test('AI Navigation: Navegar para Machines usando linguagem natural', async ({ page }) => {
    // Setup - verifica API key e inicializa Midscene
    const { ai, skip, skipReason } = await setupMidsceneTest(page);
    if (skip) {
      console.log(`⏭️ Teste ignorado: ${skipReason}`);
      test.skip();
      return;
    }

    // 1. Ir para dashboard
    await goToPage(page, '/app');

    // 2. Usar AI para clicar no link "Machines"
    await ai.action('click on the link that says "Machines"');

    // 3. Verificar navegação usando AI assertion
    await ai.assert('The page shows a list of machines or GPUs');

    // 4. Verificar também com Playwright (fallback verification)
    const hasMachineContent = await page.getByText(/Minhas Máquinas|Machines|RTX|A100/i).first().isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasMachineContent).toBeTruthy();
  });

  test('AI Query: Extrair informação da página de Machines', async ({ page }) => {
    const { ai, skip, skipReason } = await setupMidsceneTest(page);
    if (skip) {
      console.log(`⏭️ Teste ignorado: ${skipReason}`);
      test.skip();
      return;
    }

    await goToPage(page, '/app/machines');
    await page.waitForTimeout(2000);

    // Usar AI para fazer query sobre a página
    const pageDescription = await ai.query('Describe what you see on this page in one sentence');
    console.log('📋 AI descreveu a página:', pageDescription);

    // Verificar se existem máquinas
    const hasMachines = await ai.query('Are there any GPU machines or cards visible on this page? Answer with yes or no');
    console.log('🖥️ Tem máquinas:', hasMachines);

    // Verificar com Playwright
    const hasGPUText = await page.getByText(/RTX|A100|H100|4090|3090|GPU/i).first().isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasGPUText).toBeTruthy();
  });

  test('AI Action: Interagir com filtros na página de Machines', async ({ page }) => {
    const { ai, skip, skipReason } = await setupMidsceneTest(page);
    if (skip) {
      console.log(`⏭️ Teste ignorado: ${skipReason}`);
      test.skip();
      return;
    }

    await goToPage(page, '/app/machines');
    await page.waitForTimeout(2000);

    // Verificar se existem filtros
    const hasFilters = await ai.query('Are there any filter buttons visible like "Online", "Offline", or "All"? Answer yes or no');
    console.log('🔍 Tem filtros:', hasFilters);

    if (String(hasFilters).toLowerCase().includes('yes')) {
      // Clicar em filtro usando linguagem natural
      await ai.action('click on any filter button you see');
      await page.waitForTimeout(1000);
      console.log('✅ Clicou em um filtro');
    } else {
      console.log('ℹ️ Nenhum filtro encontrado - pulando interação');
    }

    // Verificar que a página ainda está funcional
    await ai.assert('The page is showing machine or GPU related content');
  });

  test('AI Assert: Verificar elementos do Dashboard', async ({ page }) => {
    const { ai, skip, skipReason } = await setupMidsceneTest(page);
    if (skip) {
      console.log(`⏭️ Teste ignorado: ${skipReason}`);
      test.skip();
      return;
    }

    await goToPage(page, '/app');
    await page.waitForTimeout(2000);

    // Usar AI assertions para verificar elementos
    await ai.assert('There is a navigation menu or sidebar visible');
    await ai.assert('The page has a main content area');

    // Verificar links de navegação
    const hasNavigation = await ai.query('Is there a link or button for "Machines" visible? Answer yes or no');
    console.log('🔗 Navegação para Machines:', hasNavigation);

    // Verificar com Playwright também
    const machinesLink = page.getByRole('link', { name: 'Machines' });
    const hasMachinesLink = await machinesLink.isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasMachinesLink).toBeTruthy();
  });

});

test.describe('🚀 Midscene.js: Fluxos Completos', () => {

  test('Fluxo: Dashboard → Machines → Verificar status', async ({ page }) => {
    const { ai, skip, skipReason } = await setupMidsceneTest(page);
    if (skip) {
      console.log(`⏭️ Teste ignorado: ${skipReason}`);
      test.skip();
      return;
    }

    // 1. Ir para Dashboard
    await goToPage(page, '/app');
    await ai.assert('This looks like a dashboard or main application page');
    console.log('✅ Dashboard carregado');

    // 2. Navegar para Machines
    await ai.action('click on the Machines link in the navigation');
    await page.waitForTimeout(2000);
    console.log('✅ Navegou para Machines');

    // 3. Verificar conteúdo
    const machineStatus = await ai.query('What is the status of the machines shown? Are they online, offline, or mixed?');
    console.log('📊 Status das máquinas:', machineStatus);

    // 4. Verificar com Playwright
    const hasContent = await page.getByText(/RTX|A100|H100|Online|Offline/i).first().isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasContent).toBeTruthy();
  });

  test('Fluxo: Navegar para Settings e verificar tabs', async ({ page }) => {
    const { ai, skip, skipReason } = await setupMidsceneTest(page);
    if (skip) {
      console.log(`⏭️ Teste ignorado: ${skipReason}`);
      test.skip();
      return;
    }

    // 1. Ir para Settings
    await goToPage(page, '/app/settings');
    await page.waitForTimeout(2000);

    // 2. Verificar que está na página de Settings
    await ai.assert('This is a settings or configuration page');
    console.log('✅ Página de Settings carregada');

    // 3. Query sobre as tabs disponíveis
    const tabsInfo = await ai.query('What tabs or sections are visible on this settings page?');
    console.log('📑 Tabs encontradas:', tabsInfo);

    // 4. Tentar clicar em uma tab
    await ai.action('click on any tab button that you see');
    await page.waitForTimeout(1000);
    console.log('✅ Clicou em uma tab');

    // 5. Verificar com Playwright
    const hasSettingsContent = await page.getByText(/Configurações|Settings|API|Storage/i).first().isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasSettingsContent).toBeTruthy();
  });

});

test.describe('💡 Midscene.js: Padrões e Boas Práticas', () => {

  test('Padrão: Combinar AI com Playwright tradicional', async ({ page }) => {
    const { ai, skip, skipReason } = await setupMidsceneTest(page);
    if (skip) {
      console.log(`⏭️ Teste ignorado: ${skipReason}`);
      test.skip();
      return;
    }

    await goToPage(page, '/app/machines');
    await page.waitForTimeout(2000);

    // ✅ PADRÃO RECOMENDADO: Usar AI para ações complexas
    await ai.action('look for any machine card on the page');

    // ✅ PADRÃO RECOMENDADO: Usar Playwright para verificações rápidas
    const hasMachineCards = await page.getByText(/RTX|A100|H100|4090|3090/i).first().isVisible({ timeout: 5000 }).catch(() => false);

    if (hasMachineCards) {
      // Usar AI para interações complexas
      const machineInfo = await ai.query('Describe the first machine card you see - what GPU does it have?');
      console.log('🖥️ Info da máquina:', machineInfo);
    }

    // ✅ PADRÃO RECOMENDADO: Assertion final com Playwright
    expect(hasMachineCards).toBeTruthy();
  });

  test('Padrão: Fallback quando AI não encontra elemento', async ({ page }) => {
    const { ai, skip, skipReason } = await setupMidsceneTest(page);
    if (skip) {
      console.log(`⏭️ Teste ignorado: ${skipReason}`);
      test.skip();
      return;
    }

    await goToPage(page, '/app');
    await page.waitForTimeout(2000);

    // Tentar usar AI primeiro
    try {
      await ai.action('click on the Machines link');
      console.log('✅ AI encontrou e clicou no link');
    } catch (aiError) {
      console.log('⚠️ AI falhou, usando fallback Playwright');

      // ✅ FALLBACK: Usar Playwright tradicional
      const machinesLink = page.getByRole('link', { name: 'Machines' });
      if (await machinesLink.isVisible({ timeout: 5000 }).catch(() => false)) {
        await machinesLink.click();
        console.log('✅ Playwright encontrou e clicou no link');
      } else {
        // Navegar diretamente
        await page.goto('/app/machines');
        console.log('✅ Navegou diretamente via URL');
      }
    }

    // Verificar resultado
    await page.waitForTimeout(2000);
    const isOnMachinesPage = await page.getByText(/Minhas Máquinas|Machines/i).first().isVisible({ timeout: 5000 }).catch(() => false);
    expect(isOnMachinesPage).toBeTruthy();
  });

  test('Padrão: Queries estruturadas para extração de dados', async ({ page }) => {
    const { ai, skip, skipReason } = await setupMidsceneTest(page);
    if (skip) {
      console.log(`⏭️ Teste ignorado: ${skipReason}`);
      test.skip();
      return;
    }

    await goToPage(page, '/app/machines');
    await page.waitForTimeout(2000);

    // ✅ Query específica para obter dados estruturados
    const machineCount = await ai.query('How many machine cards are visible on this page? Return just a number');
    console.log('📊 Número de máquinas:', machineCount);

    const hasOnlineMachines = await ai.query('Are there any machines showing "Online" status? Answer with yes or no');
    console.log('🟢 Máquinas online:', hasOnlineMachines);

    const hasOfflineMachines = await ai.query('Are there any machines showing "Offline" status? Answer with yes or no');
    console.log('🔴 Máquinas offline:', hasOfflineMachines);

    // Verificação com Playwright
    const pageHasContent = await page.locator('main, [role="main"]').isVisible().catch(() => false);
    expect(pageHasContent).toBeTruthy();
  });

});

test.describe('⚠️ Midscene.js: Tratamento de Erros', () => {

  test('Erro: Teste pula graciosamente sem API key', async ({ page }) => {
    // Este teste demonstra o comportamento quando OPENAI_API_KEY não está configurada
    // O setupMidsceneTest retorna skip=true e o teste é ignorado
    const { ai, skip, skipReason } = await setupMidsceneTest(page);

    if (skip) {
      console.log(`⏭️ Comportamento esperado: ${skipReason}`);
      console.log('💡 Configure OPENAI_API_KEY no arquivo .env para executar testes Midscene');
      test.skip();
      return;
    }

    // Se chegou aqui, API key está configurada
    await goToPage(page, '/app');
    await ai.assert('The page loaded successfully');
  });

  test('Erro: Timeout em operações AI longas', async ({ page }) => {
    const { ai, skip, skipReason } = await setupMidsceneTest(page);
    if (skip) {
      console.log(`⏭️ Teste ignorado: ${skipReason}`);
      test.skip();
      return;
    }

    await goToPage(page, '/app');

    // Demonstrar waitFor com timeout
    try {
      await ai.waitFor('The page shows a very specific element that might not exist', {
        timeout: 5000,
        pollInterval: 2000
      });
    } catch (timeoutError) {
      console.log('⏱️ Timeout esperado para elemento inexistente');
      // Este é o comportamento esperado - timeout para elemento não encontrado
    }

    // Verificar que a página ainda funciona
    const pageIsResponsive = await page.locator('body').isVisible();
    expect(pageIsResponsive).toBeTruthy();
  });

});
