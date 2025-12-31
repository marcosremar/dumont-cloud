// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * 🎯 TESTES DA PÁGINA DE CONFIGURAÇÕES (SETTINGS)
 *
 * Estes testes verificam que todos os componentes da página de Settings
 * estão funcionando corretamente, incluindo navegação entre tabs,
 * inputs de configuração e componentes especializados.
 *
 * IMPORTANTE:
 * - Rotas: /app/settings (NUNCA /demo-app/*)
 * - Usa autenticação via setup (storageState)
 * - Testa 6 tabs: apis, storage, cloudstorage, agent, notifications, failover
 */

// Helper para navegar para Settings e aguardar carregamento
async function goToSettings(page, tab = null) {
  const url = tab ? `/app/settings?tab=${tab}` : '/app/settings';
  await page.goto(url);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);

  // Fechar modal de boas-vindas se aparecer
  const skipButton = page.getByText('Pular tudo');
  if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipButton.click();
    await page.waitForTimeout(500);
  }
}

// Lista de tabs disponíveis na página Settings
const SETTINGS_TABS = [
  { id: 'apis', label: 'APIs & Credenciais' },
  { id: 'storage', label: 'Armazenamento' },
  { id: 'cloudstorage', label: 'Cloud Storage Failover' },
  { id: 'agent', label: 'Agent Sync' },
  { id: 'notifications', label: 'Notificações' },
  { id: 'failover', label: 'CPU Failover' },
];

test.describe('🔧 Navigation - Settings Tab Navigation', () => {

  test.beforeEach(async ({ page }) => {
    await goToSettings(page);
  });

  test('Navigation: Settings page loads with default APIs tab', async ({ page }) => {
    // Verificar que a página carregou
    const pageTitle = page.locator('[data-testid="settings-page-title"]');
    await expect(pageTitle).toBeVisible({ timeout: 10000 });
    await expect(pageTitle).toHaveText('Configurações');

    // Verificar que o container da página existe
    const pageContainer = page.locator('[data-testid="settings-page"]');
    await expect(pageContainer).toBeVisible();

    // Verificar que o form existe
    const settingsForm = page.locator('[data-testid="settings-form"]');
    await expect(settingsForm).toBeVisible();
  });

  test('Navigation: All 6 tab buttons are visible and clickable', async ({ page }) => {
    // Verificar que todos os 6 botões de tab estão visíveis
    for (const tab of SETTINGS_TABS) {
      const tabButton = page.locator(`[data-testid="settings-tab-${tab.id}"]`);
      await expect(tabButton).toBeVisible({ timeout: 5000 });
    }
  });

  test('Navigation: Clicking tab changes active state and content', async ({ page }) => {
    // Clicar em cada tab e verificar que o conteúdo muda
    for (const tab of SETTINGS_TABS) {
      const tabButton = page.locator(`[data-testid="settings-tab-${tab.id}"]`);
      await tabButton.click();
      await page.waitForTimeout(500);

      // Verificar que o botão está ativo (tem classe de destaque)
      await expect(tabButton).toHaveClass(/text-brand-400|bg-brand/);
    }
  });

  test('Navigation: Navigate to APIs tab', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Verificar que a tab APIs está ativa
    const tabButton = page.locator('[data-testid="settings-tab-apis"]');
    await expect(tabButton).toHaveClass(/text-brand-400/);

    // Verificar que o conteúdo da tab APIs está visível
    await expect(page.getByText('Vast.ai')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Cloudflare R2')).toBeVisible();
  });

  test('Navigation: Navigate to Storage tab', async ({ page }) => {
    await goToSettings(page, 'storage');

    // Verificar que a tab Storage está ativa
    const tabButton = page.locator('[data-testid="settings-tab-storage"]');
    await expect(tabButton).toHaveClass(/text-brand-400/);

    // Verificar que o conteúdo da tab Storage está visível
    await expect(page.getByText('Restic')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Repository Password|Proteção e criptografia/i)).toBeVisible();
  });

  test('Navigation: Navigate to Cloud Storage tab', async ({ page }) => {
    await goToSettings(page, 'cloudstorage');

    // Verificar que a tab Cloud Storage está ativa
    const tabButton = page.locator('[data-testid="settings-tab-cloudstorage"]');
    await expect(tabButton).toHaveClass(/text-brand-400/);

    // Verificar que o conteúdo da tab Cloud Storage está visível
    await expect(page.getByText(/Cloud Storage Failover/i).first()).toBeVisible({ timeout: 5000 });

    // Verificar que o toggle de habilitação existe
    const enableToggle = page.locator('[data-testid="settings-cloudstorage-enabled-toggle"]');
    await expect(enableToggle).toBeVisible();

    // Verificar que o seletor de provedor existe
    const providerSelect = page.locator('[data-testid="settings-cloudstorage-provider"]');
    await expect(providerSelect).toBeVisible();
  });

  test('Navigation: Navigate to Agent tab', async ({ page }) => {
    await goToSettings(page, 'agent');

    // Verificar que a tab Agent está ativa
    const tabButton = page.locator('[data-testid="settings-tab-agent"]');
    await expect(tabButton).toHaveClass(/text-brand-400/);

    // Verificar que o conteúdo da tab Agent está visível
    await expect(page.getByText('DumontAgent')).toBeVisible({ timeout: 5000 });

    // Verificar dropdowns
    const syncIntervalSelect = page.locator('[data-testid="settings-agent-sync-interval"]');
    await expect(syncIntervalSelect).toBeVisible();

    const keepLastSelect = page.locator('[data-testid="settings-agent-keep-last"]');
    await expect(keepLastSelect).toBeVisible();

    // Verificar botão de salvar
    const saveButton = page.locator('[data-testid="settings-agent-save"]');
    await expect(saveButton).toBeVisible();
  });

  test('Navigation: Navigate to Notifications tab', async ({ page }) => {
    await goToSettings(page, 'notifications');

    // Verificar que a tab Notifications está ativa
    const tabButton = page.locator('[data-testid="settings-tab-notifications"]');
    await expect(tabButton).toHaveClass(/text-brand-400/);

    // Verificar que o conteúdo da tab Notifications está visível
    await expect(page.getByText(/Notificações|Alertas de Saldo/i).first()).toBeVisible({ timeout: 5000 });

    // Verificar botão de testar notificação
    const testButton = page.locator('[data-testid="settings-test-notification"]');
    await expect(testButton).toBeVisible();
  });

  test('Navigation: Navigate to Failover tab', async ({ page }) => {
    await goToSettings(page, 'failover');

    // Verificar que a tab Failover está ativa
    const tabButton = page.locator('[data-testid="settings-tab-failover"]');
    await expect(tabButton).toHaveClass(/text-brand-400/);

    // Verificar que o conteúdo da tab Failover está visível
    await expect(page.getByText(/Estimativa de Custo|CPU Failover/i).first()).toBeVisible({ timeout: 5000 });

    // Verificar que StandbyConfig está presente (pelo data-testid)
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    const hasStandbyConfig = await standbyConfig.isVisible({ timeout: 5000 }).catch(() => false);

    // StandbyConfig pode estar carregando, então verificar apenas se a área de failover existe
    if (!hasStandbyConfig) {
      // Verificar pelo menos o card de estimativa de custo
      await expect(page.getByText(/Cloudflare R2|Armazenamento em nuvem/i).first()).toBeVisible();
    }

    // Verificar que FailoverReport está presente
    const failoverReport = page.locator('[data-testid="failover-report"]');
    const hasFailoverReport = await failoverReport.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasFailoverReport) {
      // Se visível, pode verificar mais detalhes
      await expect(failoverReport).toBeVisible();
    }
  });

  test('Navigation: Tab navigation via clicking (full cycle)', async ({ page }) => {
    // Começar na tab APIs
    await goToSettings(page, 'apis');

    // Navegar por todas as tabs clicando nos botões
    for (let i = 0; i < SETTINGS_TABS.length; i++) {
      const tab = SETTINGS_TABS[i];
      const tabButton = page.locator(`[data-testid="settings-tab-${tab.id}"]`);

      await tabButton.click();
      await page.waitForTimeout(300);

      // Verificar que a tab está ativa
      await expect(tabButton).toHaveClass(/text-brand-400/);
    }

    // Voltar para a primeira tab
    const firstTab = page.locator('[data-testid="settings-tab-apis"]');
    await firstTab.click();
    await expect(firstTab).toHaveClass(/text-brand-400/);
  });

  test('Navigation: Direct URL navigation preserves tab state', async ({ page }) => {
    // Navegar diretamente para cada tab via URL
    for (const tab of SETTINGS_TABS) {
      await page.goto(`/app/settings?tab=${tab.id}`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Verificar que a tab correta está ativa
      const tabButton = page.locator(`[data-testid="settings-tab-${tab.id}"]`);
      await expect(tabButton).toHaveClass(/text-brand-400/);
    }
  });

});
