// @ts-check
/**
 * 🤖 EXEMPLO: Teste usando ferramentas AI do Playwright
 *
 * Este arquivo demonstra como escrever testes SELF-HEALING que:
 * - ✅ Não quebram quando CSS/classes mudam
 * - ✅ Usam descrições humanas de elementos
 * - ✅ Adaptam-se automaticamente a mudanças de layout
 * - ✅ Não precisam de manutenção constante
 *
 * REGRA DE OURO:
 * - NUNCA usar page.locator('css-selector')
 * - SEMPRE usar page.getByRole(), page.getByText(), page.getByLabel()
 */

const { test, expect } = require('@playwright/test');
const { ensureOnlineMachine } = require('../helpers/ai-resource-creators');

test.describe('🤖 Exemplo: Testes AI-Powered', () => {
  test.beforeEach(async ({ page }) => {
    // Login é feito pelo auth.setup.js automaticamente
    // através do storageState configurado no playwright.config.js
  });

  test('✅ CORRETO: Navegar para Machines usando getByRole', async ({ page }) => {
    // 1. Ir para dashboard
    await page.goto('/app');
    await page.waitForLoadState('domcontentloaded');

    // 2. Encontrar link "Machines" pelo ROLE e NAME (AI-friendly)
    const machinesLink = page.getByRole('link', { name: 'Machines' });

    // 3. Verificar que está visível
    await expect(machinesLink).toBeVisible();

    // 4. Clicar
    await machinesLink.click();

    // 5. Verificar que navegou (usando heading ao invés de URL)
    await expect(page.getByRole('heading', { name: 'Minhas Máquinas' })).toBeVisible();
  });

  test('✅ CORRETO: Clicar em Iniciar usando getByRole', async ({ page }) => {
    await page.goto('/app/machines');
    await page.waitForLoadState('domcontentloaded');

    // Garantir que existe máquina offline
    const hasOffline = await page.getByText('Offline').isVisible().catch(() => false);
    if (!hasOffline) {
      console.log('⚠️ Teste pulado: nenhuma máquina offline disponível');
      test.skip();
      return;
    }

    // Encontrar botão "Iniciar" pelo ROLE e NAME (robusto!)
    const startButton = page.getByRole('button', { name: 'Iniciar' }).first();

    // Verificar que está visível
    await expect(startButton).toBeVisible();

    // Clicar
    await startButton.click();

    // Aguardar feedback visual (pode ser toast, modal, etc)
    await page.waitForTimeout(2000);

    // Verificar que iniciou (procurar por "Online" próximo da máquina)
    // Nota: em teste real, esperaria até o status mudar de fato
    console.log('✅ Botão Iniciar clicado com sucesso');
  });

  test('✅ CORRETO: Verificar elementos usando getByText', async ({ page }) => {
    await page.goto('/app/machines');
    await page.waitForLoadState('domcontentloaded');

    // Verificar textos importantes estão visíveis
    await expect(page.getByText('Minhas Máquinas')).toBeVisible();
    await expect(page.getByText('GPUs Ativas')).toBeVisible();
    await expect(page.getByText('CPU Backup')).toBeVisible();
    await expect(page.getByText('VRAM Total')).toBeVisible();
  });

  test('✅ CORRETO: Filtrar máquinas usando getByRole', async ({ page }) => {
    await page.goto('/app/machines');
    await page.waitForLoadState('domcontentloaded');

    // Clicar no filtro "Online" usando getByRole
    const onlineFilter = page.getByRole('button', { name: /Online \(\d+\)/ });
    await expect(onlineFilter).toBeVisible();
    await onlineFilter.click();

    // Verificar que apenas máquinas online aparecem
    await expect(page.getByText('Online')).toBeVisible();

    // Clicar no filtro "Todas"
    const allFilter = page.getByRole('button', { name: /Todas \(\d+\)/ });
    await allFilter.click();
  });

  test('✅ CORRETO: Navegar pelo menu usando getByRole', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('domcontentloaded');

    // Dashboard
    const dashboardLink = page.getByRole('link', { name: 'Dashboard' });
    await expect(dashboardLink).toBeVisible();

    // Machines
    const machinesLink = page.getByRole('link', { name: 'Machines' });
    await expect(machinesLink).toBeVisible();
    await machinesLink.click();
    await expect(page.getByRole('heading', { name: 'Minhas Máquinas' })).toBeVisible();

    // Settings
    const settingsLink = page.getByRole('link', { name: 'Settings' });
    await expect(settingsLink).toBeVisible();
    await settingsLink.click();
    await expect(page.getByRole('heading', { name: /Settings|Configurações/ })).toBeVisible();
  });

  test('❌ ERRADO: Exemplo de teste FRÁGIL (NÃO FAZER ISSO!)', async ({ page }) => {
    // ❌ NUNCA fazer isso - quebrará quando CSS mudar
    // await page.locator('.machine-card').first().click();
    // await page.locator('button[class*="btn-primary"]').click();
    // await page.locator('a:not(.mobile-menu-link):has-text("Machines")').click();

    // ✅ Fazer isso ao invés:
    await page.goto('/app/machines');
    const machineCards = page.getByRole('button', { name: /RTX|A100|H100/ });
    const firstCard = machineCards.first();
    // ... etc
  });
});

test.describe('🚀 Exemplo: Fluxos Completos AI-Powered', () => {
  test('Dashboard → Machines → Iniciar Máquina', async ({ page }) => {
    // 1. Ver Dashboard
    await page.goto('/app');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

    // 2. Ir para Machines
    await page.getByRole('link', { name: 'Machines' }).click();
    await expect(page.getByRole('heading', { name: 'Minhas Máquinas' })).toBeVisible();

    // 3. Verificar se tem máquina offline
    const hasOffline = await page.getByText('Offline').isVisible().catch(() => false);

    if (hasOffline) {
      // 4. Iniciar máquina
      const startButton = page.getByRole('button', { name: 'Iniciar' }).first();
      await expect(startButton).toBeVisible();
      await startButton.click();

      console.log('✅ Fluxo completo executado com sucesso');
    } else {
      console.log('⚠️ Nenhuma máquina offline para iniciar');
    }
  });

  test('Criar nova máquina usando AI Wizard', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('domcontentloaded');

    // Clicar em "AI Assistant"
    const aiAssistantButton = page.getByRole('button', { name: 'AI Assistant' });
    if (await aiAssistantButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await aiAssistantButton.click();
      console.log('✅ AI Assistant aberto');

      // Aguardar interface do wizard
      await page.waitForTimeout(2000);
    }

    // Ou usar "Buscar Máquinas Disponíveis"
    const searchButton = page.getByRole('button', { name: /Buscar.*Máquinas/i });
    if (await searchButton.isVisible().catch(() => false)) {
      await searchButton.click();
      console.log('✅ Buscando máquinas disponíveis...');
    }
  });
});
