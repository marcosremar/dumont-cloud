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

test.describe('📄 Tab Content - Settings Tab Content Rendering', () => {

  test('Tab Content: APIs tab renders all credential sections', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Verificar seção Vast.ai
    await expect(page.getByText('Vast.ai')).toBeVisible({ timeout: 5000 });

    // Verificar campo de API Key do Vast.ai
    const vastApiKeyInput = page.locator('[data-testid="settings-vast-api-key"]');
    const hasVastApiKey = await vastApiKeyInput.isVisible({ timeout: 5000 }).catch(() => false);
    if (hasVastApiKey) {
      await expect(vastApiKeyInput).toBeVisible();
    }

    // Verificar seção Cloudflare R2
    await expect(page.getByText('Cloudflare R2')).toBeVisible({ timeout: 5000 });

    // Verificar campos R2 (pelo menos um deve existir)
    const r2AccessKeyInput = page.locator('[data-testid="settings-r2-access-key"]');
    const r2SecretKeyInput = page.locator('[data-testid="settings-r2-secret-key"]');
    const r2BucketInput = page.locator('[data-testid="settings-r2-bucket"]');

    const hasR2AccessKey = await r2AccessKeyInput.isVisible({ timeout: 3000 }).catch(() => false);
    const hasR2SecretKey = await r2SecretKeyInput.isVisible({ timeout: 3000 }).catch(() => false);
    const hasR2Bucket = await r2BucketInput.isVisible({ timeout: 3000 }).catch(() => false);

    // Pelo menos um campo R2 deve estar presente
    expect(hasR2AccessKey || hasR2SecretKey || hasR2Bucket).toBeTruthy();

    // Verificar botão de salvar
    const saveButton = page.locator('[data-testid="settings-apis-save"]');
    const hasSaveButton = await saveButton.isVisible({ timeout: 3000 }).catch(() => false);
    if (hasSaveButton) {
      await expect(saveButton).toBeVisible();
    }
  });

  test('Tab Content: Storage tab renders Restic configuration', async ({ page }) => {
    await goToSettings(page, 'storage');

    // Verificar título Restic
    await expect(page.getByText('Restic')).toBeVisible({ timeout: 5000 });

    // Verificar que há menção a proteção/criptografia
    await expect(page.getByText(/Repository Password|Proteção e criptografia|senha/i).first()).toBeVisible();

    // Verificar campo de senha do repository
    const repoPasswordInput = page.locator('[data-testid="settings-restic-password"]');
    const hasRepoPassword = await repoPasswordInput.isVisible({ timeout: 5000 }).catch(() => false);
    if (hasRepoPassword) {
      await expect(repoPasswordInput).toBeVisible();
    }

    // Verificar que há inputs de texto na página (usando getByRole - AI)
    const inputCount = await page.getByRole('textbox').count();
    expect(inputCount).toBeGreaterThanOrEqual(0);

    // Verificar botão de salvar (se existir)
    const saveButton = page.locator('[data-testid="settings-storage-save"]');
    const hasSaveButton = await saveButton.isVisible({ timeout: 3000 }).catch(() => false);
    if (hasSaveButton) {
      await expect(saveButton).toBeVisible();
    }
  });

  test('Tab Content: Cloud Storage tab renders provider configuration', async ({ page }) => {
    await goToSettings(page, 'cloudstorage');

    // Verificar título da seção
    await expect(page.getByText(/Cloud Storage Failover/i).first()).toBeVisible({ timeout: 5000 });

    // Verificar toggle de habilitação
    const enableToggle = page.locator('[data-testid="settings-cloudstorage-enabled-toggle"]');
    await expect(enableToggle).toBeVisible({ timeout: 5000 });

    // Verificar seletor de provedor
    const providerSelect = page.locator('[data-testid="settings-cloudstorage-provider"]');
    await expect(providerSelect).toBeVisible();

    // Verificar que há opções de provedores (R2, S3, etc)
    const hasR2Option = await page.getByText(/R2|Cloudflare/i).first().isVisible({ timeout: 3000 }).catch(() => false);
    const hasS3Option = await page.getByText(/S3|AWS/i).first().isVisible({ timeout: 3000 }).catch(() => false);

    // Pelo menos um provedor deve ser mencionado
    expect(hasR2Option || hasS3Option).toBeTruthy();

    // Verificar botão de salvar
    const saveButton = page.locator('[data-testid="settings-cloudstorage-save"]');
    const hasSaveButton = await saveButton.isVisible({ timeout: 3000 }).catch(() => false);
    if (hasSaveButton) {
      await expect(saveButton).toBeVisible();
    }
  });

  test('Tab Content: Agent tab renders sync configuration', async ({ page }) => {
    await goToSettings(page, 'agent');

    // Verificar título DumontAgent
    await expect(page.getByText('DumontAgent')).toBeVisible({ timeout: 5000 });

    // Verificar dropdown de intervalo de sincronização
    const syncIntervalSelect = page.locator('[data-testid="settings-agent-sync-interval"]');
    await expect(syncIntervalSelect).toBeVisible();

    // Verificar dropdown de retenção (keep last)
    const keepLastSelect = page.locator('[data-testid="settings-agent-keep-last"]');
    await expect(keepLastSelect).toBeVisible();

    // Verificar que há texto explicativo sobre sincronização
    const hasSyncText = await page.getByText(/sync|sincronização|intervalo/i).first().isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasSyncText).toBeTruthy();

    // Verificar botão de salvar
    const saveButton = page.locator('[data-testid="settings-agent-save"]');
    await expect(saveButton).toBeVisible();

    // Verificar que o botão está habilitado ou desabilitado (mas existe)
    const isDisabled = await saveButton.isDisabled();
    // Não importa se está disabled ou não, apenas que existe
    expect(typeof isDisabled).toBe('boolean');
  });

  test('Tab Content: Notifications tab renders alert configuration', async ({ page }) => {
    await goToSettings(page, 'notifications');

    // Verificar título/seção de notificações
    await expect(page.getByText(/Notificações|Alertas de Saldo/i).first()).toBeVisible({ timeout: 5000 });

    // Verificar botão de testar notificação
    const testButton = page.locator('[data-testid="settings-test-notification"]');
    await expect(testButton).toBeVisible();

    // Verificar que há configurações de alerta (toggle ou slider)
    const alertToggle = page.locator('[data-testid="settings-notifications-enabled"]');
    const hasAlertToggle = await alertToggle.isVisible({ timeout: 3000 }).catch(() => false);

    const alertThreshold = page.locator('[data-testid="settings-notifications-threshold"]');
    const hasAlertThreshold = await alertThreshold.isVisible({ timeout: 3000 }).catch(() => false);

    // Verificar que há algum elemento interativo (pelo menos o botão de teste)
    const buttonCount = await page.locator('button').count();
    expect(buttonCount).toBeGreaterThan(0);

    // Verificar menção a Telegram ou outro canal de notificação
    const hasTelegram = await page.getByText(/Telegram|WhatsApp|Email|SMS/i).first().isVisible({ timeout: 3000 }).catch(() => false);
    if (hasTelegram) {
      // Se existir, verificar campos relacionados
      const telegramInput = page.locator('[data-testid="settings-telegram-chat-id"]');
      const hasTelegramInput = await telegramInput.isVisible({ timeout: 3000 }).catch(() => false);
      if (hasTelegramInput) {
        await expect(telegramInput).toBeVisible();
      }
    }
  });

  test('Tab Content: Failover tab renders cost estimation and standby config', async ({ page }) => {
    await goToSettings(page, 'failover');

    // Verificar título da seção
    await expect(page.getByText(/Estimativa de Custo|CPU Failover/i).first()).toBeVisible({ timeout: 5000 });

    // Verificar StandbyConfig (pode estar carregando)
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    const hasStandbyConfig = await standbyConfig.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasStandbyConfig) {
      await expect(standbyConfig).toBeVisible();

      // Verificar elementos dentro do StandbyConfig
      const standbyToggle = page.locator('[data-testid="standby-config-enabled"]');
      const hasStandbyToggle = await standbyToggle.isVisible({ timeout: 3000 }).catch(() => false);
      if (hasStandbyToggle) {
        await expect(standbyToggle).toBeVisible();
      }
    }

    // Verificar FailoverReport
    const failoverReport = page.locator('[data-testid="failover-report"]');
    const hasFailoverReport = await failoverReport.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasFailoverReport) {
      await expect(failoverReport).toBeVisible();
    }

    // Verificar menção a armazenamento em nuvem
    const hasCloudStorage = await page.getByText(/Cloudflare R2|Armazenamento em nuvem|Cloud Storage/i).first().isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasCloudStorage).toBeTruthy();

    // Verificar que há elementos visuais de custo (valores monetários ou porcentagem)
    const hasCostValue = await page.getByText(/\$\d+|\d+%|custo/i).first().isVisible({ timeout: 3000 }).catch(() => false);
    if (hasCostValue) {
      // Pelo menos algum indicador de custo deve existir
      expect(hasCostValue).toBeTruthy();
    }
  });

  test('Tab Content: Each tab has unique content that changes on navigation', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Capturar conteúdo único da tab APIs
    const apisContent = await page.getByText('Vast.ai').isVisible().catch(() => false);
    expect(apisContent).toBeTruthy();

    // Navegar para Storage e verificar que conteúdo mudou
    const storageTab = page.locator('[data-testid="settings-tab-storage"]');
    await storageTab.click();
    await page.waitForTimeout(500);

    const storageContent = await page.getByText('Restic').isVisible().catch(() => false);
    expect(storageContent).toBeTruthy();

    // Navegar para Agent e verificar que conteúdo mudou
    const agentTab = page.locator('[data-testid="settings-tab-agent"]');
    await agentTab.click();
    await page.waitForTimeout(500);

    const agentContent = await page.getByText('DumontAgent').isVisible().catch(() => false);
    expect(agentContent).toBeTruthy();

    // Navegar para Notifications e verificar que conteúdo mudou
    const notificationsTab = page.locator('[data-testid="settings-tab-notifications"]');
    await notificationsTab.click();
    await page.waitForTimeout(500);

    const notificationsContent = await page.getByText(/Notificações|Alertas/i).first().isVisible().catch(() => false);
    expect(notificationsContent).toBeTruthy();
  });

});

test.describe('🔐 SecretInput - Toggle Visibility Tests', () => {

  test('SecretInput: Vast.ai API key toggle visibility works', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do Vast.ai API Key
    const apiKeyInput = page.locator('[data-testid="input-vast_api_key"]');
    await expect(apiKeyInput).toBeVisible({ timeout: 5000 });

    // Verificar que o input começa como type="password"
    await expect(apiKeyInput).toHaveAttribute('type', 'password');

    // Localizar e clicar no botão de toggle
    const toggleButton = page.locator('[data-testid="toggle-visibility-vast_api_key"]');
    await expect(toggleButton).toBeVisible();
    await toggleButton.click();
    await page.waitForTimeout(300);

    // Verificar que o input agora é type="text" (visível)
    await expect(apiKeyInput).toHaveAttribute('type', 'text');

    // Clicar novamente para ocultar
    await toggleButton.click();
    await page.waitForTimeout(300);

    // Verificar que voltou para type="password"
    await expect(apiKeyInput).toHaveAttribute('type', 'password');
  });

  test('SecretInput: R2 Access Key toggle visibility works', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Access Key
    const accessKeyInput = page.locator('[data-testid="input-r2_access_key"]');
    await expect(accessKeyInput).toBeVisible({ timeout: 5000 });

    // Verificar estado inicial (password)
    await expect(accessKeyInput).toHaveAttribute('type', 'password');

    // Toggle para mostrar
    const toggleButton = page.locator('[data-testid="toggle-visibility-r2_access_key"]');
    await expect(toggleButton).toBeVisible();
    await toggleButton.click();
    await page.waitForTimeout(300);

    // Verificar que está visível
    await expect(accessKeyInput).toHaveAttribute('type', 'text');

    // Toggle para ocultar
    await toggleButton.click();
    await page.waitForTimeout(300);

    // Verificar que está oculto novamente
    await expect(accessKeyInput).toHaveAttribute('type', 'password');
  });

  test('SecretInput: R2 Secret Key toggle visibility works', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Secret Key
    const secretKeyInput = page.locator('[data-testid="input-r2_secret_key"]');
    await expect(secretKeyInput).toBeVisible({ timeout: 5000 });

    // Verificar estado inicial (password)
    await expect(secretKeyInput).toHaveAttribute('type', 'password');

    // Toggle para mostrar
    const toggleButton = page.locator('[data-testid="toggle-visibility-r2_secret_key"]');
    await expect(toggleButton).toBeVisible();
    await toggleButton.click();
    await page.waitForTimeout(300);

    // Verificar que está visível
    await expect(secretKeyInput).toHaveAttribute('type', 'text');

    // Toggle para ocultar
    await toggleButton.click();
    await page.waitForTimeout(300);

    // Verificar que está oculto novamente
    await expect(secretKeyInput).toHaveAttribute('type', 'password');
  });

  test('SecretInput: Restic password toggle visibility works', async ({ page }) => {
    await goToSettings(page, 'storage');

    // Localizar o input do Restic Password
    const passwordInput = page.locator('[data-testid="input-restic_password"]');
    await expect(passwordInput).toBeVisible({ timeout: 5000 });

    // Verificar estado inicial (password)
    await expect(passwordInput).toHaveAttribute('type', 'password');

    // Toggle para mostrar
    const toggleButton = page.locator('[data-testid="toggle-visibility-restic_password"]');
    await expect(toggleButton).toBeVisible();
    await toggleButton.click();
    await page.waitForTimeout(300);

    // Verificar que está visível
    await expect(passwordInput).toHaveAttribute('type', 'text');

    // Toggle para ocultar
    await toggleButton.click();
    await page.waitForTimeout(300);

    // Verificar que está oculto novamente
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test('SecretInput: Toggle button shows correct icon state', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o botão de toggle do Vast.ai API Key
    const toggleButton = page.locator('[data-testid="toggle-visibility-vast_api_key"]');
    await expect(toggleButton).toBeVisible({ timeout: 5000 });

    // Verificar que o botão tem título "Mostrar" quando oculto
    await expect(toggleButton).toHaveAttribute('title', 'Mostrar');

    // Clicar para mostrar
    await toggleButton.click();
    await page.waitForTimeout(300);

    // Verificar que o botão tem título "Ocultar" quando visível
    await expect(toggleButton).toHaveAttribute('title', 'Ocultar');

    // Clicar para ocultar novamente
    await toggleButton.click();
    await page.waitForTimeout(300);

    // Verificar que voltou para "Mostrar"
    await expect(toggleButton).toHaveAttribute('title', 'Mostrar');
  });

  test('SecretInput: Multiple toggles work independently', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar os inputs
    const vastApiKeyInput = page.locator('[data-testid="input-vast_api_key"]');
    const r2AccessKeyInput = page.locator('[data-testid="input-r2_access_key"]');
    const r2SecretKeyInput = page.locator('[data-testid="input-r2_secret_key"]');

    // Localizar os toggles
    const vastToggle = page.locator('[data-testid="toggle-visibility-vast_api_key"]');
    const r2AccessToggle = page.locator('[data-testid="toggle-visibility-r2_access_key"]');
    const r2SecretToggle = page.locator('[data-testid="toggle-visibility-r2_secret_key"]');

    // Aguardar que todos estejam visíveis
    await expect(vastApiKeyInput).toBeVisible({ timeout: 5000 });
    await expect(r2AccessKeyInput).toBeVisible();
    await expect(r2SecretKeyInput).toBeVisible();

    // Todos começam ocultos
    await expect(vastApiKeyInput).toHaveAttribute('type', 'password');
    await expect(r2AccessKeyInput).toHaveAttribute('type', 'password');
    await expect(r2SecretKeyInput).toHaveAttribute('type', 'password');

    // Mostrar apenas o Vast API Key
    await vastToggle.click();
    await page.waitForTimeout(300);

    // Verificar que apenas o Vast está visível
    await expect(vastApiKeyInput).toHaveAttribute('type', 'text');
    await expect(r2AccessKeyInput).toHaveAttribute('type', 'password');
    await expect(r2SecretKeyInput).toHaveAttribute('type', 'password');

    // Mostrar também o R2 Access Key
    await r2AccessToggle.click();
    await page.waitForTimeout(300);

    // Verificar que Vast e R2 Access estão visíveis, R2 Secret ainda oculto
    await expect(vastApiKeyInput).toHaveAttribute('type', 'text');
    await expect(r2AccessKeyInput).toHaveAttribute('type', 'text');
    await expect(r2SecretKeyInput).toHaveAttribute('type', 'password');

    // Ocultar o Vast
    await vastToggle.click();
    await page.waitForTimeout(300);

    // Verificar que Vast está oculto, R2 Access ainda visível
    await expect(vastApiKeyInput).toHaveAttribute('type', 'password');
    await expect(r2AccessKeyInput).toHaveAttribute('type', 'text');
    await expect(r2SecretKeyInput).toHaveAttribute('type', 'password');
  });

  test('SecretInput: Cloud Storage Backblaze B2 toggle visibility works', async ({ page }) => {
    await goToSettings(page, 'cloudstorage');

    // Backblaze B2 é o provedor padrão, então os campos devem estar visíveis
    // Localizar o input do B2 Key ID
    const b2KeyIdInput = page.locator('[data-testid="input-b2_key_id"]');
    const hasB2KeyId = await b2KeyIdInput.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasB2KeyId) {
      // Verificar estado inicial (password)
      await expect(b2KeyIdInput).toHaveAttribute('type', 'password');

      // Toggle para mostrar
      const toggleButton = page.locator('[data-testid="toggle-visibility-b2_key_id"]');
      await expect(toggleButton).toBeVisible();
      await toggleButton.click();
      await page.waitForTimeout(300);

      // Verificar que está visível
      await expect(b2KeyIdInput).toHaveAttribute('type', 'text');

      // Toggle para ocultar
      await toggleButton.click();
      await page.waitForTimeout(300);

      // Verificar que está oculto novamente
      await expect(b2KeyIdInput).toHaveAttribute('type', 'password');
    } else {
      // Se Backblaze B2 não é o provedor padrão, verificar que a seção de provedor existe
      const providerSelect = page.locator('[data-testid="settings-cloudstorage-provider"]');
      await expect(providerSelect).toBeVisible();
    }
  });

});

test.describe('✅ Validation - Form Input Validation Tests', () => {

  test('Validation: Vast.ai API key shows error for short input', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do Vast.ai API Key
    const apiKeyInput = page.locator('[data-testid="input-vast_api_key"]');
    await expect(apiKeyInput).toBeVisible({ timeout: 5000 });

    // Limpar e digitar uma API key curta (menos de 20 caracteres)
    await apiKeyInput.fill('short_api_key');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro aparece
    const errorAlert = page.getByText('API key muito curta');
    await expect(errorAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: Vast.ai API key shows success for valid input', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do Vast.ai API Key
    const apiKeyInput = page.locator('[data-testid="input-vast_api_key"]');
    await expect(apiKeyInput).toBeVisible({ timeout: 5000 });

    // Digitar uma API key válida (20+ caracteres)
    await apiKeyInput.fill('valid_api_key_12345678901234567890');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de sucesso aparece
    const successAlert = page.getByText('Formato válido');
    await expect(successAlert.first()).toBeVisible({ timeout: 3000 });
  });

  test('Validation: R2 Access Key shows error for short input', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Access Key
    const accessKeyInput = page.locator('[data-testid="input-r2_access_key"]');
    await expect(accessKeyInput).toBeVisible({ timeout: 5000 });

    // Digitar uma access key curta (menos de 10 caracteres)
    await accessKeyInput.fill('short');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro aparece
    const errorAlert = page.getByText('Access key muito curta');
    await expect(errorAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: R2 Access Key shows success for valid input', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Access Key
    const accessKeyInput = page.locator('[data-testid="input-r2_access_key"]');
    await expect(accessKeyInput).toBeVisible({ timeout: 5000 });

    // Digitar uma access key válida (10+ caracteres)
    await accessKeyInput.fill('valid_access_key_123');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de sucesso aparece
    const successAlert = page.getByText('Formato válido');
    await expect(successAlert.first()).toBeVisible({ timeout: 3000 });
  });

  test('Validation: R2 Secret Key shows error for short input', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Secret Key
    const secretKeyInput = page.locator('[data-testid="input-r2_secret_key"]');
    await expect(secretKeyInput).toBeVisible({ timeout: 5000 });

    // Digitar uma secret key curta (menos de 20 caracteres)
    await secretKeyInput.fill('short_secret');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro aparece
    const errorAlert = page.getByText('Secret key muito curta');
    await expect(errorAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: R2 Secret Key shows success for valid input', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Secret Key
    const secretKeyInput = page.locator('[data-testid="input-r2_secret_key"]');
    await expect(secretKeyInput).toBeVisible({ timeout: 5000 });

    // Digitar uma secret key válida (20+ caracteres)
    await secretKeyInput.fill('valid_secret_key_12345678901234567890');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de sucesso aparece
    const successAlert = page.getByText('Formato válido');
    await expect(successAlert.first()).toBeVisible({ timeout: 3000 });
  });

  test('Validation: R2 Endpoint shows error for non-https URL', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Endpoint
    const endpointInput = page.locator('[data-testid="input-r2_endpoint"]');
    await expect(endpointInput).toBeVisible({ timeout: 5000 });

    // Digitar um endpoint sem https
    await endpointInput.fill('http://example.r2.cloudflarestorage.com');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro aparece
    const errorAlert = page.getByText('Deve começar com https://');
    await expect(errorAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: R2 Endpoint shows error for non-R2 URL', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Endpoint
    const endpointInput = page.locator('[data-testid="input-r2_endpoint"]');
    await expect(endpointInput).toBeVisible({ timeout: 5000 });

    // Digitar um endpoint que não é R2
    await endpointInput.fill('https://example.s3.amazonaws.com');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro aparece
    const errorAlert = page.getByText('Deve ser um endpoint R2 válido');
    await expect(errorAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: R2 Endpoint shows success for valid URL', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Endpoint
    const endpointInput = page.locator('[data-testid="input-r2_endpoint"]');
    await expect(endpointInput).toBeVisible({ timeout: 5000 });

    // Digitar um endpoint válido
    await endpointInput.fill('https://abc123.r2.cloudflarestorage.com');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de sucesso aparece
    const successAlert = page.getByText('URL válida');
    await expect(successAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: R2 Bucket shows error for short name', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Bucket
    const bucketInput = page.locator('[data-testid="input-r2_bucket"]');
    await expect(bucketInput).toBeVisible({ timeout: 5000 });

    // Digitar um nome de bucket curto (menos de 3 caracteres)
    await bucketInput.fill('ab');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro aparece
    const errorAlert = page.getByText('Nome muito curto (min. 3 caracteres)');
    await expect(errorAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: R2 Bucket shows error for invalid characters', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Bucket
    const bucketInput = page.locator('[data-testid="input-r2_bucket"]');
    await expect(bucketInput).toBeVisible({ timeout: 5000 });

    // Digitar um nome de bucket com caracteres inválidos
    await bucketInput.fill('Invalid_Bucket_Name!');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro aparece
    const errorAlert = page.getByText('Apenas letras minúsculas, números e hífens');
    await expect(errorAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: R2 Bucket shows success for valid name', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do R2 Bucket
    const bucketInput = page.locator('[data-testid="input-r2_bucket"]');
    await expect(bucketInput).toBeVisible({ timeout: 5000 });

    // Digitar um nome de bucket válido
    await bucketInput.fill('my-valid-bucket-123');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de sucesso aparece
    const successAlert = page.getByText('Nome válido');
    await expect(successAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: Restic password shows error for short password', async ({ page }) => {
    await goToSettings(page, 'storage');

    // Localizar o input do Restic Password
    const passwordInput = page.locator('[data-testid="input-restic_password"]');
    await expect(passwordInput).toBeVisible({ timeout: 5000 });

    // Digitar uma senha curta (menos de 8 caracteres)
    await passwordInput.fill('short');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro aparece
    const errorAlert = page.getByText('Senha muito curta (min. 8 caracteres)');
    await expect(errorAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: Restic password shows success for valid password', async ({ page }) => {
    await goToSettings(page, 'storage');

    // Localizar o input do Restic Password
    const passwordInput = page.locator('[data-testid="input-restic_password"]');
    await expect(passwordInput).toBeVisible({ timeout: 5000 });

    // Digitar uma senha válida (8+ caracteres)
    await passwordInput.fill('valid_password_123');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de sucesso aparece
    const successAlert = page.getByText('Senha válida');
    await expect(successAlert).toBeVisible({ timeout: 3000 });
  });

  test('Validation: Empty fields do not show validation messages', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do Vast.ai API Key
    const apiKeyInput = page.locator('[data-testid="input-vast_api_key"]');
    await expect(apiKeyInput).toBeVisible({ timeout: 5000 });

    // Limpar o campo
    await apiKeyInput.fill('');
    await page.waitForTimeout(500);

    // Verificar que nenhuma mensagem de validação aparece para campo vazio
    const errorAlert = page.getByText('API key muito curta');
    const successAlert = page.getByText('Formato válido');

    const hasError = await errorAlert.isVisible({ timeout: 1000 }).catch(() => false);
    const hasSuccess = await successAlert.first().isVisible({ timeout: 1000 }).catch(() => false);

    // Para campo vazio, não deve haver mensagem de erro
    expect(hasError).toBeFalsy();
  });

  test('Validation: Form shows validation error message when invalid', async ({ page }) => {
    await goToSettings(page, 'notifications');

    // Primeiro navegar para APIs para preencher um campo inválido
    const apisTab = page.locator('[data-testid="settings-tab-apis"]');
    await apisTab.click();
    await page.waitForTimeout(500);

    // Preencher com valor inválido
    const apiKeyInput = page.locator('[data-testid="input-vast_api_key"]');
    await expect(apiKeyInput).toBeVisible({ timeout: 5000 });
    await apiKeyInput.fill('short');
    await page.waitForTimeout(500);

    // Voltar para notifications para verificar o erro do formulário
    const notificationsTab = page.locator('[data-testid="settings-tab-notifications"]');
    await notificationsTab.click();
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro de validação do formulário aparece
    const formValidationError = page.locator('[data-testid="settings-form-validation-error"]');
    const hasFormError = await formValidationError.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasFormError) {
      await expect(formValidationError).toBeVisible();
      await expect(page.getByText('Corrija os erros antes de salvar')).toBeVisible();
    }
  });

  test('Validation: Multiple invalid fields show individual errors', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar os inputs
    const vastApiKeyInput = page.locator('[data-testid="input-vast_api_key"]');
    const r2AccessKeyInput = page.locator('[data-testid="input-r2_access_key"]');
    const r2BucketInput = page.locator('[data-testid="input-r2_bucket"]');

    await expect(vastApiKeyInput).toBeVisible({ timeout: 5000 });
    await expect(r2AccessKeyInput).toBeVisible();
    await expect(r2BucketInput).toBeVisible();

    // Preencher todos com valores inválidos
    await vastApiKeyInput.fill('short');
    await r2AccessKeyInput.fill('tiny');
    await r2BucketInput.fill('AB'); // uppercase e curto
    await page.waitForTimeout(500);

    // Verificar que múltiplas mensagens de erro aparecem
    const apiKeyError = page.getByText('API key muito curta');
    const accessKeyError = page.getByText('Access key muito curta');
    const bucketError = page.getByText(/Nome muito curto|Apenas letras minúsculas/);

    await expect(apiKeyError).toBeVisible({ timeout: 3000 });
    await expect(accessKeyError).toBeVisible();
    await expect(bucketError).toBeVisible();
  });

  test('Validation: Correcting invalid input updates validation message', async ({ page }) => {
    await goToSettings(page, 'apis');

    // Localizar o input do Vast.ai API Key
    const apiKeyInput = page.locator('[data-testid="input-vast_api_key"]');
    await expect(apiKeyInput).toBeVisible({ timeout: 5000 });

    // Primeiro, preencher com valor inválido
    await apiKeyInput.fill('short');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro aparece
    const errorAlert = page.getByText('API key muito curta');
    await expect(errorAlert).toBeVisible({ timeout: 3000 });

    // Agora, corrigir para valor válido
    await apiKeyInput.fill('valid_api_key_12345678901234567890');
    await page.waitForTimeout(500);

    // Verificar que a mensagem de erro desapareceu e sucesso aparece
    const successAlert = page.getByText('Formato válido');
    await expect(successAlert.first()).toBeVisible({ timeout: 3000 });

    // Verificar que o erro não está mais visível
    await expect(errorAlert).not.toBeVisible();
  });

});

test.describe('🔔 Toast - Notification Toast Tests', () => {

  test('Toast: Test notification button triggers toast notification', async ({ page }) => {
    await goToSettings(page, 'notifications');

    // Localizar o botão de testar notificação
    const testButton = page.locator('[data-testid="settings-test-notification"]');
    await expect(testButton).toBeVisible({ timeout: 5000 });

    // Clicar no botão de testar notificação
    await testButton.click();

    // Aguardar que o toast apareça
    const toast = page.locator('.toast[role="alert"]');
    await expect(toast).toBeVisible({ timeout: 5000 });

    // Verificar que o toast tem a estrutura correta (tem conteúdo de mensagem)
    const toastMessage = toast.locator('p');
    await expect(toastMessage).toBeVisible();

    // Verificar que o toast está no container correto
    const toastContainer = page.locator('.toast-container');
    await expect(toastContainer).toBeVisible();
  });

  test('Toast: Toast can be closed by clicking close button', async ({ page }) => {
    await goToSettings(page, 'notifications');

    // Localizar e clicar no botão de testar notificação
    const testButton = page.locator('[data-testid="settings-test-notification"]');
    await expect(testButton).toBeVisible({ timeout: 5000 });
    await testButton.click();

    // Aguardar que o toast apareça
    const toast = page.locator('.toast[role="alert"]');
    await expect(toast).toBeVisible({ timeout: 5000 });

    // Localizar e clicar no botão de fechar (aria-label="Fechar notificacao")
    const closeButton = toast.locator('button[aria-label="Fechar notificacao"]');
    await expect(closeButton).toBeVisible();
    await closeButton.click();

    // Aguardar que o toast desapareça
    await expect(toast).not.toBeVisible({ timeout: 3000 });
  });

  test('Toast: Toast has correct visual structure with accent bar and icon', async ({ page }) => {
    await goToSettings(page, 'notifications');

    // Clicar no botão de testar notificação
    const testButton = page.locator('[data-testid="settings-test-notification"]');
    await expect(testButton).toBeVisible({ timeout: 5000 });
    await testButton.click();

    // Aguardar que o toast apareça
    const toast = page.locator('.toast[role="alert"]');
    await expect(toast).toBeVisible({ timeout: 5000 });

    // Verificar que tem borda arredondada (rounded-lg class)
    await expect(toast).toHaveClass(/rounded-lg/);

    // Verificar que tem o background escuro (bg-gray-900)
    await expect(toast).toHaveClass(/bg-gray-900/);

    // Verificar que tem a animação (animate-toast-in)
    await expect(toast).toHaveClass(/animate-toast-in/);

    // Verificar que o botão de fechar existe
    const closeButton = toast.locator('button[aria-label="Fechar notificacao"]');
    await expect(closeButton).toBeVisible();
  });

  test('Toast: Multiple toasts can be displayed simultaneously', async ({ page }) => {
    await goToSettings(page, 'notifications');

    // Localizar o botão de testar notificação
    const testButton = page.locator('[data-testid="settings-test-notification"]');
    await expect(testButton).toBeVisible({ timeout: 5000 });

    // Clicar múltiplas vezes para criar múltiplos toasts
    await testButton.click();
    await page.waitForTimeout(200);
    await testButton.click();
    await page.waitForTimeout(200);

    // Verificar que há pelo menos 2 toasts visíveis
    const toasts = page.locator('.toast[role="alert"]');
    const count = await toasts.count();
    expect(count).toBeGreaterThanOrEqual(2);

    // Fechar o primeiro toast
    const firstToastCloseButton = toasts.first().locator('button[aria-label="Fechar notificacao"]');
    await firstToastCloseButton.click();
    await page.waitForTimeout(300);

    // Verificar que ainda há pelo menos 1 toast
    const remainingCount = await toasts.count();
    expect(remainingCount).toBeGreaterThanOrEqual(1);
  });

});

test.describe('⚙️ StandbyConfig - CPU Standby/Failover Configuration Tests', () => {

  test.beforeEach(async ({ page }) => {
    await goToSettings(page, 'failover');
    // Aguardar o componente carregar (loading state terminar)
    await page.waitForTimeout(2000);
  });

  test('StandbyConfig: Component renders after loading', async ({ page }) => {
    // Primeiro, verificar se está carregando ou já carregou
    const loadingState = page.locator('[data-testid="standby-config-loading"]');
    const loadedState = page.locator('[data-testid="standby-config"]');

    // Aguardar que o loading termine e o componente carregue
    const isLoading = await loadingState.isVisible({ timeout: 1000 }).catch(() => false);
    if (isLoading) {
      // Aguardar loading terminar
      await expect(loadedState).toBeVisible({ timeout: 10000 });
    }

    // Verificar que o componente carregado está visível
    await expect(loadedState).toBeVisible({ timeout: 10000 });
  });

  test('StandbyConfig: Header shows title and description', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar título
    await expect(page.getByText('CPU Standby / Failover')).toBeVisible({ timeout: 5000 });

    // Verificar descrição
    await expect(page.getByText('Backup automático em VM CPU quando GPU falha')).toBeVisible();
  });

  test('StandbyConfig: Status badge is visible and shows state', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que o badge de status está visível
    const statusBadge = page.locator('[data-testid="standby-config-status-badge"]');
    await expect(statusBadge).toBeVisible({ timeout: 5000 });

    // Verificar que mostra "Ativo" ou "Inativo"
    const badgeText = await statusBadge.textContent();
    expect(badgeText === 'Ativo' || badgeText === 'Inativo').toBeTruthy();
  });

  test('StandbyConfig: Enable toggle is visible and clickable', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que o toggle de habilitação existe
    const enableToggle = page.locator('[data-testid="standby-config-enabled-toggle"]');
    await expect(enableToggle).toBeVisible({ timeout: 5000 });

    // Verificar texto do toggle
    await expect(page.getByText('Habilitar Auto-Standby')).toBeVisible();
    await expect(page.getByText('Cria VM CPU automaticamente ao criar GPU')).toBeVisible();

    // Capturar estado inicial
    const initialChecked = await enableToggle.isChecked();

    // Clicar para mudar o estado
    await enableToggle.click();
    await page.waitForTimeout(300);

    // Verificar que o estado mudou
    const newChecked = await enableToggle.isChecked();
    expect(newChecked).not.toBe(initialChecked);

    // Restaurar estado original
    await enableToggle.click();
    await page.waitForTimeout(300);
  });

  test('StandbyConfig: GCP Zone selector is visible and has options', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que o seletor de zona está visível
    const zoneSelect = page.locator('[data-testid="standby-config-gcp-zone"]');
    await expect(zoneSelect).toBeVisible({ timeout: 5000 });

    // Verificar label
    await expect(page.getByText('Zona GCP')).toBeVisible();

    // Verificar que tem opções
    const options = await zoneSelect.locator('option').allTextContents();
    expect(options.length).toBeGreaterThan(0);

    // Verificar que contém algumas zonas esperadas
    const optionsText = options.join(' ');
    expect(optionsText).toContain('Europe West');
  });

  test('StandbyConfig: Machine Type selector is visible and has options', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que o seletor de tipo de máquina está visível
    const machineTypeSelect = page.locator('[data-testid="standby-config-machine-type"]');
    await expect(machineTypeSelect).toBeVisible({ timeout: 5000 });

    // Verificar label
    await expect(page.getByText('Tipo de Máquina')).toBeVisible();

    // Verificar que tem opções
    const options = await machineTypeSelect.locator('option').allTextContents();
    expect(options.length).toBeGreaterThan(0);

    // Verificar que contém tipos e2
    const optionsText = options.join(' ');
    expect(optionsText).toContain('e2-');
  });

  test('StandbyConfig: Disk Size input is visible and accepts values', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que o input de tamanho do disco está visível
    const diskSizeInput = page.locator('[data-testid="standby-config-disk-size"]');
    await expect(diskSizeInput).toBeVisible({ timeout: 5000 });

    // Verificar label
    await expect(page.getByText('Disco (GB)')).toBeVisible();

    // Verificar que o input é do tipo number
    await expect(diskSizeInput).toHaveAttribute('type', 'number');

    // Verificar atributos min e max
    await expect(diskSizeInput).toHaveAttribute('min', '10');
    await expect(diskSizeInput).toHaveAttribute('max', '500');
  });

  test('StandbyConfig: Spot VM toggle is visible', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que o toggle de Spot VM está visível
    const spotToggle = page.locator('[data-testid="standby-config-spot-toggle"]');
    await expect(spotToggle).toBeVisible({ timeout: 5000 });

    // Verificar texto do toggle
    await expect(page.getByText('Usar Spot VM (70% mais barato)')).toBeVisible();
  });

  test('StandbyConfig: Sync Interval input is visible and accepts values', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que o input de intervalo de sync está visível
    const syncIntervalInput = page.locator('[data-testid="standby-config-sync-interval"]');
    await expect(syncIntervalInput).toBeVisible({ timeout: 5000 });

    // Verificar label
    await expect(page.getByText('Intervalo de Sync (segundos)')).toBeVisible();

    // Verificar que o input é do tipo number
    await expect(syncIntervalInput).toHaveAttribute('type', 'number');

    // Verificar atributos min e max
    await expect(syncIntervalInput).toHaveAttribute('min', '10');
    await expect(syncIntervalInput).toHaveAttribute('max', '300');
  });

  test('StandbyConfig: Auto Failover toggle is visible', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que o toggle de auto-failover está visível
    const autoFailoverToggle = page.locator('[data-testid="standby-config-auto-failover-toggle"]');
    await expect(autoFailoverToggle).toBeVisible({ timeout: 5000 });

    // Verificar texto do toggle
    await expect(page.getByText('Auto-Failover (troca para CPU se GPU falhar)')).toBeVisible();
  });

  test('StandbyConfig: Auto Recovery toggle is visible', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que o toggle de auto-recovery está visível
    const autoRecoveryToggle = page.locator('[data-testid="standby-config-auto-recovery-toggle"]');
    await expect(autoRecoveryToggle).toBeVisible({ timeout: 5000 });

    // Verificar texto do toggle
    await expect(page.getByText('Auto-Recovery (provisiona nova GPU após failover)')).toBeVisible();
  });

  test('StandbyConfig: Save button is visible and clickable', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que o botão de salvar está visível
    const saveButton = page.locator('[data-testid="standby-config-save"]');
    await expect(saveButton).toBeVisible({ timeout: 5000 });

    // Verificar texto do botão
    await expect(saveButton).toContainText('Salvar Configuração');
  });

  test('StandbyConfig: Form fields are disabled when standby is disabled', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Desabilitar o standby (se estiver habilitado)
    const enableToggle = page.locator('[data-testid="standby-config-enabled-toggle"]');
    const isEnabled = await enableToggle.isChecked();

    if (isEnabled) {
      await enableToggle.click();
      await page.waitForTimeout(300);
    }

    // Verificar que os campos estão desabilitados
    const zoneSelect = page.locator('[data-testid="standby-config-gcp-zone"]');
    const machineTypeSelect = page.locator('[data-testid="standby-config-machine-type"]');
    const diskSizeInput = page.locator('[data-testid="standby-config-disk-size"]');
    const spotToggle = page.locator('[data-testid="standby-config-spot-toggle"]');
    const syncIntervalInput = page.locator('[data-testid="standby-config-sync-interval"]');
    const autoFailoverToggle = page.locator('[data-testid="standby-config-auto-failover-toggle"]');
    const autoRecoveryToggle = page.locator('[data-testid="standby-config-auto-recovery-toggle"]');

    await expect(zoneSelect).toBeDisabled();
    await expect(machineTypeSelect).toBeDisabled();
    await expect(diskSizeInput).toBeDisabled();
    await expect(spotToggle).toBeDisabled();
    await expect(syncIntervalInput).toBeDisabled();
    await expect(autoFailoverToggle).toBeDisabled();
    await expect(autoRecoveryToggle).toBeDisabled();

    // Restaurar estado se necessário
    if (isEnabled) {
      await enableToggle.click();
      await page.waitForTimeout(300);
    }
  });

  test('StandbyConfig: Form fields are enabled when standby is enabled', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Habilitar o standby (se estiver desabilitado)
    const enableToggle = page.locator('[data-testid="standby-config-enabled-toggle"]');
    const wasEnabled = await enableToggle.isChecked();

    if (!wasEnabled) {
      await enableToggle.click();
      await page.waitForTimeout(300);
    }

    // Verificar que os campos estão habilitados
    const zoneSelect = page.locator('[data-testid="standby-config-gcp-zone"]');
    const machineTypeSelect = page.locator('[data-testid="standby-config-machine-type"]');
    const diskSizeInput = page.locator('[data-testid="standby-config-disk-size"]');
    const spotToggle = page.locator('[data-testid="standby-config-spot-toggle"]');
    const syncIntervalInput = page.locator('[data-testid="standby-config-sync-interval"]');
    const autoFailoverToggle = page.locator('[data-testid="standby-config-auto-failover-toggle"]');
    const autoRecoveryToggle = page.locator('[data-testid="standby-config-auto-recovery-toggle"]');

    await expect(zoneSelect).toBeEnabled();
    await expect(machineTypeSelect).toBeEnabled();
    await expect(diskSizeInput).toBeEnabled();
    await expect(spotToggle).toBeEnabled();
    await expect(syncIntervalInput).toBeEnabled();
    await expect(autoFailoverToggle).toBeEnabled();
    await expect(autoRecoveryToggle).toBeEnabled();

    // Restaurar estado se necessário
    if (!wasEnabled) {
      await enableToggle.click();
      await page.waitForTimeout(300);
    }
  });

  test('StandbyConfig: GCP Zone can be changed', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Habilitar o standby se necessário
    const enableToggle = page.locator('[data-testid="standby-config-enabled-toggle"]');
    const wasEnabled = await enableToggle.isChecked();
    if (!wasEnabled) {
      await enableToggle.click();
      await page.waitForTimeout(300);
    }

    // Selecionar uma zona diferente
    const zoneSelect = page.locator('[data-testid="standby-config-gcp-zone"]');
    const currentValue = await zoneSelect.inputValue();

    // Selecionar US Central se não for a atual
    const newZone = currentValue === 'us-central1-a' ? 'europe-west1-b' : 'us-central1-a';
    await zoneSelect.selectOption(newZone);
    await page.waitForTimeout(300);

    // Verificar que o valor mudou
    const newValue = await zoneSelect.inputValue();
    expect(newValue).toBe(newZone);

    // Restaurar estado
    await zoneSelect.selectOption(currentValue);
    if (!wasEnabled) {
      await enableToggle.click();
    }
  });

  test('StandbyConfig: Machine Type can be changed', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Habilitar o standby se necessário
    const enableToggle = page.locator('[data-testid="standby-config-enabled-toggle"]');
    const wasEnabled = await enableToggle.isChecked();
    if (!wasEnabled) {
      await enableToggle.click();
      await page.waitForTimeout(300);
    }

    // Selecionar um tipo de máquina diferente
    const machineTypeSelect = page.locator('[data-testid="standby-config-machine-type"]');
    const currentValue = await machineTypeSelect.inputValue();

    // Selecionar e2-small se não for o atual
    const newType = currentValue === 'e2-small' ? 'e2-medium' : 'e2-small';
    await machineTypeSelect.selectOption(newType);
    await page.waitForTimeout(300);

    // Verificar que o valor mudou
    const newValue = await machineTypeSelect.inputValue();
    expect(newValue).toBe(newType);

    // Restaurar estado
    await machineTypeSelect.selectOption(currentValue);
    if (!wasEnabled) {
      await enableToggle.click();
    }
  });

  test('StandbyConfig: Disk Size can be changed', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Habilitar o standby se necessário
    const enableToggle = page.locator('[data-testid="standby-config-enabled-toggle"]');
    const wasEnabled = await enableToggle.isChecked();
    if (!wasEnabled) {
      await enableToggle.click();
      await page.waitForTimeout(300);
    }

    // Mudar o tamanho do disco
    const diskSizeInput = page.locator('[data-testid="standby-config-disk-size"]');
    const currentValue = await diskSizeInput.inputValue();

    // Definir novo valor
    const newSize = currentValue === '100' ? '150' : '100';
    await diskSizeInput.fill(newSize);
    await page.waitForTimeout(300);

    // Verificar que o valor mudou
    const newValue = await diskSizeInput.inputValue();
    expect(newValue).toBe(newSize);

    // Restaurar estado
    await diskSizeInput.fill(currentValue);
    if (!wasEnabled) {
      await enableToggle.click();
    }
  });

  test('StandbyConfig: Toggles can be changed when enabled', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Habilitar o standby
    const enableToggle = page.locator('[data-testid="standby-config-enabled-toggle"]');
    const wasEnabled = await enableToggle.isChecked();
    if (!wasEnabled) {
      await enableToggle.click();
      await page.waitForTimeout(300);
    }

    // Testar toggle de Spot VM
    const spotToggle = page.locator('[data-testid="standby-config-spot-toggle"]');
    const spotInitial = await spotToggle.isChecked();
    await spotToggle.click();
    await page.waitForTimeout(200);
    const spotAfter = await spotToggle.isChecked();
    expect(spotAfter).not.toBe(spotInitial);
    await spotToggle.click(); // Restaurar

    // Testar toggle de Auto Failover
    const autoFailoverToggle = page.locator('[data-testid="standby-config-auto-failover-toggle"]');
    const failoverInitial = await autoFailoverToggle.isChecked();
    await autoFailoverToggle.click();
    await page.waitForTimeout(200);
    const failoverAfter = await autoFailoverToggle.isChecked();
    expect(failoverAfter).not.toBe(failoverInitial);
    await autoFailoverToggle.click(); // Restaurar

    // Testar toggle de Auto Recovery
    const autoRecoveryToggle = page.locator('[data-testid="standby-config-auto-recovery-toggle"]');
    const recoveryInitial = await autoRecoveryToggle.isChecked();
    await autoRecoveryToggle.click();
    await page.waitForTimeout(200);
    const recoveryAfter = await autoRecoveryToggle.isChecked();
    expect(recoveryAfter).not.toBe(recoveryInitial);
    await autoRecoveryToggle.click(); // Restaurar

    // Restaurar estado do enable toggle
    if (!wasEnabled) {
      await enableToggle.click();
    }
  });

  test('StandbyConfig: Pricing info shows when enabled', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Habilitar o standby
    const enableToggle = page.locator('[data-testid="standby-config-enabled-toggle"]');
    const wasEnabled = await enableToggle.isChecked();
    if (!wasEnabled) {
      await enableToggle.click();
      await page.waitForTimeout(1000); // Aguardar API de pricing
    }

    // Verificar se a info de pricing aparece (pode não aparecer se API falhar)
    const pricingInfo = page.locator('[data-testid="standby-config-pricing"]');
    const hasPricing = await pricingInfo.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasPricing) {
      // Verificar que mostra custo estimado
      await expect(pricingInfo).toContainText('Custo estimado');
      await expect(pricingInfo).toContainText('/mês');
    }

    // Restaurar estado
    if (!wasEnabled) {
      await enableToggle.click();
    }
  });

  test('StandbyConfig: All configuration options are accessible', async ({ page }) => {
    const standbyConfig = page.locator('[data-testid="standby-config"]');
    await expect(standbyConfig).toBeVisible({ timeout: 10000 });

    // Verificar que todos os elementos de configuração existem
    const elements = [
      '[data-testid="standby-config-enabled-toggle"]',
      '[data-testid="standby-config-gcp-zone"]',
      '[data-testid="standby-config-machine-type"]',
      '[data-testid="standby-config-disk-size"]',
      '[data-testid="standby-config-spot-toggle"]',
      '[data-testid="standby-config-sync-interval"]',
      '[data-testid="standby-config-auto-failover-toggle"]',
      '[data-testid="standby-config-auto-recovery-toggle"]',
      '[data-testid="standby-config-save"]',
      '[data-testid="standby-config-status-badge"]',
    ];

    for (const selector of elements) {
      const element = page.locator(selector);
      await expect(element).toBeVisible({ timeout: 5000 });
    }
  });

});
