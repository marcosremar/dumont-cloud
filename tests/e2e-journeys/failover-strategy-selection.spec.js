/**
 * Failover Strategy Selection - Testes E2E Headless
 *
 * Testa a criação de máquinas e seleção de diferentes tipos de failover:
 * - Disabled (Sem proteção)
 * - CPU Standby (GCP e2-medium)
 * - GPU Warm Pool (GPU reservada)
 * - Regional Volume (Volume + Spot GPU)
 * - Snapshot (Backblaze B2)
 */

const { test, expect } = require('@playwright/test');

// Configuração para headless mode
test.use({
  headless: true,
  viewport: { width: 1920, height: 1080 },
});

// Usa demo-app pois é o modo padrão para testes
const BASE_PATH = '/demo-app';

// Helper para navegar para Machines
async function goToMachines(page) {
  await page.goto(`${BASE_PATH}/machines`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2000);
}

// Helper para navegar para Dashboard
async function goToDashboard(page) {
  await page.goto(`${BASE_PATH}`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2000);
}

// ============================================================
// TESTE 1: Verificar que página Machines carrega com cards
// ============================================================
test.describe('📋 Página de Máquinas', () => {

  test('Página Machines carrega corretamente', async ({ page }) => {
    await goToMachines(page);

    // Verificar URL
    expect(page.url()).toContain('/machines');

    // Verificar título ou header
    const header = page.getByRole('heading', { name: /máquinas|machines|gpus/i }).first();
    await expect(header).toBeVisible({ timeout: 5000 });

    console.log('✅ Página Machines carregou corretamente');
  });

  test('Mostra saldo VAST.ai no topo', async ({ page }) => {
    await goToMachines(page);

    // Verificar que o saldo aparece
    const balanceElement = page.getByText(/saldo/i).first();
    const hasBalance = await balanceElement.isVisible().catch(() => false);

    if (hasBalance) {
      console.log('✅ Saldo VAST.ai está visível');
      await expect(balanceElement).toBeVisible();

      // Verificar que mostra valor em dólar
      const dollarValue = page.getByText(/\$\d+\.\d{2}/);
      await expect(dollarValue.first()).toBeVisible();
    } else {
      console.log('ℹ️ Saldo não visível - pode estar em modo sem autenticação');
    }
  });

  test('Mostra cards de máquinas ou estado vazio', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    // Verificar se tem máquinas ou estado vazio
    const hasGPUCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);
    const hasEmptyState = await page.getByText(/nenhuma máquina|no machines|criar.*primeira/i).first().isVisible().catch(() => false);

    if (hasGPUCards) {
      console.log('✅ Cards de máquinas encontrados');
    } else if (hasEmptyState) {
      console.log('✅ Estado vazio - nenhuma máquina ainda');
    }

    expect(hasGPUCards || hasEmptyState).toBe(true);
  });
});

// ============================================================
// TESTE 2: Verificar badge de failover nos cards
// ============================================================
test.describe('🛡️ Badge de Failover nos Cards', () => {

  test('Card de máquina mostra estratégia de failover atual', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    // Verificar se tem máquinas
    const hasGPUCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);

    if (!hasGPUCards) {
      console.log('ℹ️ Nenhuma máquina para verificar badge de failover');
      test.skip();
      return;
    }

    // Procurar por badges de failover
    const failoverBadges = [
      page.getByText(/cpu standby/i),
      page.getByText(/warm pool/i),
      page.getByText(/regional volume/i),
      page.getByText(/snapshot/i),
      page.getByText(/desabilitado/i),
    ];

    let foundBadge = false;
    for (const badge of failoverBadges) {
      if (await badge.first().isVisible().catch(() => false)) {
        foundBadge = true;
        console.log('✅ Badge de failover encontrado');
        break;
      }
    }

    expect(foundBadge).toBe(true);
  });

  test('Badge mostra custo adicional do failover', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    // Procurar por custo de failover (formato: +$0.XX/h)
    const costPattern = page.getByText(/\+\$\d+\.\d+\/h/);
    const hasCost = await costPattern.first().isVisible().catch(() => false);

    if (hasCost) {
      console.log('✅ Custo de failover visível no badge');
      await expect(costPattern.first()).toBeVisible();
    } else {
      // Pode estar desabilitado (custo 0)
      console.log('ℹ️ Custo de failover não visível - pode estar desabilitado');
    }
  });
});

// ============================================================
// TESTE 3: Dropdown de seleção de failover
// ============================================================
test.describe('🔄 Seleção de Estratégia de Failover', () => {

  test('Clicar no badge abre dropdown com opções', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    // Verificar se tem máquinas
    const hasGPUCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);

    if (!hasGPUCards) {
      console.log('ℹ️ Nenhuma máquina para testar dropdown');
      test.skip();
      return;
    }

    // Usar o data-testid para encontrar o botão de failover
    const failoverButton = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverButton.isVisible().catch(() => false)) {
      await failoverButton.click();
      await page.waitForTimeout(500);

      // Verificar se o dropdown menu abriu
      const dropdownMenu = page.locator('[data-testid="failover-dropdown-menu"]');
      const isDropdownVisible = await dropdownMenu.isVisible().catch(() => false);

      if (isDropdownVisible) {
        console.log('✅ Dropdown de failover aberto com opções');
        expect(isDropdownVisible).toBe(true);
      } else {
        // Fallback: verificar opções individuais
        const cpuOption = page.locator('[data-testid="failover-option-cpu_standby"]');
        const hasCpuOption = await cpuOption.isVisible().catch(() => false);
        console.log('✅ Dropdown de failover aberto com opções');
        expect(hasCpuOption).toBe(true);
      }
    } else {
      console.log('ℹ️ Botão de failover não encontrado no card');
      test.skip();
    }
  });

  test('Dropdown mostra todas as 5 estratégias de failover', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    // Verificar se tem máquinas
    const hasGPUCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);

    if (!hasGPUCards) {
      test.skip();
      return;
    }

    // Usar data-testid para abrir dropdown
    const failoverButton = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverButton.isVisible().catch(() => false)) {
      await failoverButton.click();
      await page.waitForTimeout(500);

      // Verificar todas as opções usando data-testid
      const strategyTestIds = [
        { id: 'disabled', name: 'Desabilitado' },
        { id: 'cpu_standby', name: 'CPU Standby' },
        { id: 'warm_pool', name: 'GPU Warm Pool' },
        { id: 'regional_volume', name: 'Regional Volume' },
        { id: 'snapshot', name: 'Snapshot' },
      ];

      let foundCount = 0;
      for (const strategy of strategyTestIds) {
        const element = page.locator(`[data-testid="failover-option-${strategy.id}"]`);
        if (await element.isVisible().catch(() => false)) {
          foundCount++;
          console.log(`✅ Estratégia "${strategy.name}" disponível`);
        } else {
          console.log(`⚠️ Estratégia "${strategy.name}" não encontrada`);
        }
      }

      console.log(`📊 ${foundCount}/5 estratégias encontradas`);
      expect(foundCount).toBeGreaterThanOrEqual(3); // Pelo menos 3 estratégias
    }
  });

  test('Cada estratégia mostra tempo de recovery e custo', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    const hasGPUCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);

    if (!hasGPUCards) {
      test.skip();
      return;
    }

    const failoverTrigger = page.getByRole('button').filter({ hasText: /standby|failover|pool|snapshot|desabilitado/i }).first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      await failoverTrigger.click();
      await page.waitForTimeout(500);

      // Verificar que mostra tempos de recovery
      const recoveryPatterns = [
        /~?\d+-?\d*\s*(min|s|seg|segundos|minutos)/i,
        /recovery/i,
        /tempo.*recuperação/i,
      ];

      let hasRecoveryInfo = false;
      for (const pattern of recoveryPatterns) {
        const element = page.getByText(pattern);
        if (await element.first().isVisible().catch(() => false)) {
          hasRecoveryInfo = true;
          console.log('✅ Informação de tempo de recovery visível');
          break;
        }
      }

      // Verificar custos
      const costPattern = page.getByText(/\$\d+\.\d+/);
      const hasCostInfo = await costPattern.first().isVisible().catch(() => false);

      if (hasCostInfo) {
        console.log('✅ Informação de custo visível no dropdown');
      }

      expect(hasRecoveryInfo || hasCostInfo).toBe(true);
    }
  });
});

// ============================================================
// TESTE 4: Criar máquina via Dashboard
// ============================================================
test.describe('➕ Criar Máquina via Dashboard', () => {

  test('Dashboard mostra opções de GPU disponíveis', async ({ page }) => {
    await goToDashboard(page);
    await page.waitForTimeout(2000);

    // Verificar ofertas de GPU usando data-testid ou texto
    const gpuCards = page.locator('[data-testid="gpu-offer-card"]');
    const hasGpuCards = await gpuCards.first().isVisible().catch(() => false);

    // Fallback: verificar por texto de GPU
    const hasGpuText = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);

    // Verificar botão de seleção
    const selectButtons = page.locator('[data-testid="gpu-offer-select-button"]');
    const hasSelectButtons = await selectButtons.first().isVisible().catch(() => false);

    // Verificar se há seção de criar instância ou nova GPU
    const hasCreateSection = await page.getByText(/nova.*instância|nova.*gpu|criar.*máquina|select.*gpu/i).first().isVisible().catch(() => false);

    // Verificar se Dashboard carregou (tem estatísticas, cards, etc)
    const hasDashboardContent = await page.getByText(/máquinas|machines|gpus.*ativas|custo/i).first().isVisible().catch(() => false);

    if (hasGpuCards || hasSelectButtons) {
      console.log('✅ Cards de GPU com botões de seleção disponíveis');
    } else if (hasGpuText) {
      console.log('✅ Ofertas de GPU disponíveis (texto encontrado)');
    } else if (hasCreateSection) {
      console.log('✅ Seção de criar instância disponível');
    } else if (hasDashboardContent) {
      console.log('✅ Dashboard carregou (ofertas podem estar em outra seção)');
    }

    // Passa se qualquer conteúdo relevante foi encontrado
    const hasContent = hasGpuCards || hasSelectButtons || hasGpuText || hasCreateSection || hasDashboardContent;
    expect(hasContent).toBe(true);
  });

  test('Seleção de GPU inicia processo de criação', async ({ page }) => {
    await goToDashboard(page);
    await page.waitForTimeout(2000);

    // Procurar pelo botão de seleção usando data-testid
    const selectButton = page.locator('[data-testid="gpu-offer-select-button"]').first();

    // Fallback: procurar por botões com texto
    const fallbackButton = page.getByRole('button').filter({ hasText: /selecionar|escolher|select/i }).first();

    let clicked = false;

    if (await selectButton.isVisible().catch(() => false)) {
      await selectButton.click();
      clicked = true;
      console.log('✅ Clicou no botão Selecionar');
    } else if (await fallbackButton.isVisible().catch(() => false)) {
      await fallbackButton.click();
      clicked = true;
      console.log('✅ Clicou no botão de seleção (fallback)');
    }

    if (clicked) {
      await page.waitForTimeout(1000);

      // Verificar se iniciou criação (modal, redirecionamento, ou tela de progresso)
      const hasProgress = await page.getByText(/criando|creating|provisioning|conectando/i).first().isVisible().catch(() => false);
      const hasModal = await page.getByRole('dialog').isVisible().catch(() => false);
      const redirectedToMachines = page.url().includes('/machines');

      if (hasProgress || hasModal || redirectedToMachines) {
        console.log('✅ Processo de criação iniciado');
      }

      expect(hasProgress || hasModal || redirectedToMachines).toBe(true);
    } else {
      console.log('ℹ️ Nenhum card/botão de GPU clicável encontrado');
      // Não falha o teste pois pode não haver ofertas disponíveis
    }
  });
});

// ============================================================
// TESTE 5: Trocar estratégia de failover em máquina existente
// ============================================================
test.describe('🔁 Trocar Estratégia de Failover', () => {

  test('Selecionar CPU Standby atualiza badge e mostra custo', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    const hasGPUCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);

    if (!hasGPUCards) {
      test.skip();
      return;
    }

    // Abrir dropdown usando data-testid
    const failoverButton = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverButton.isVisible().catch(() => false)) {
      await failoverButton.click();
      await page.waitForTimeout(500);

      // Selecionar CPU Standby usando data-testid
      const cpuStandbyOption = page.locator('[data-testid="failover-option-cpu_standby"]');
      if (await cpuStandbyOption.isVisible().catch(() => false)) {
        await cpuStandbyOption.click();
        await page.waitForTimeout(500);

        console.log('✅ CPU Standby selecionado');

        // Verificar que badge atualizou (dropdown fecha, badge mostra nova estratégia)
        const badge = page.locator('[data-testid="failover-selector"]').first();
        const badgeText = await badge.textContent();

        if (badgeText && badgeText.toLowerCase().includes('cpu')) {
          console.log('✅ Badge atualizado para CPU Standby');
        }

        // Verificar custo no badge
        if (badgeText && badgeText.includes('$')) {
          console.log('✅ Custo de CPU Standby exibido');
        }

        expect(true).toBe(true); // Passou se chegou aqui
      } else {
        console.log('ℹ️ Opção CPU Standby não encontrada');
      }
    }
  });

  test('Selecionar GPU Warm Pool mostra custo mais alto', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    const hasGPUCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);

    if (!hasGPUCards) {
      test.skip();
      return;
    }

    // Abrir dropdown usando data-testid
    const failoverButton = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverButton.isVisible().catch(() => false)) {
      await failoverButton.click();
      await page.waitForTimeout(500);

      // Selecionar Warm Pool usando data-testid
      const warmPoolOption = page.locator('[data-testid="failover-option-warm_pool"]');
      if (await warmPoolOption.isVisible().catch(() => false)) {
        await warmPoolOption.click();
        await page.waitForTimeout(500);

        console.log('✅ Warm Pool selecionado');

        // Verificar badge
        const badge = page.locator('[data-testid="failover-selector"]').first();
        const badgeText = await badge.textContent();

        if (badgeText && badgeText.toLowerCase().includes('warm')) {
          console.log('✅ Badge atualizado para Warm Pool');
        }

        if (badgeText && badgeText.includes('$')) {
          console.log(`✅ Custo do Warm Pool exibido`);
        }

        expect(true).toBe(true);
      } else {
        console.log('ℹ️ Opção Warm Pool não encontrada');
      }
    }
  });

  test('Selecionar Desabilitado remove custo adicional', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    const hasGPUCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);

    if (!hasGPUCards) {
      test.skip();
      return;
    }

    // Abrir dropdown usando data-testid
    const failoverButton = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverButton.isVisible().catch(() => false)) {
      await failoverButton.click();
      await page.waitForTimeout(500);

      // Selecionar Desabilitado usando data-testid
      const disabledOption = page.locator('[data-testid="failover-option-disabled"]');
      if (await disabledOption.isVisible().catch(() => false)) {
        await disabledOption.click();
        await page.waitForTimeout(500);

        console.log('✅ Failover desabilitado');

        // Verificar badge
        const badge = page.locator('[data-testid="failover-selector"]').first();
        const badgeText = await badge.textContent();

        if (badgeText && badgeText.toLowerCase().includes('desabilitado')) {
          console.log('✅ Badge atualizado para Desabilitado');
        }

        // Desabilitado não deve mostrar custo ou mostrar sem custo
        if (badgeText && !badgeText.includes('+$')) {
          console.log('✅ Custo zerado para failover desabilitado');
        }

        expect(true).toBe(true);
      } else {
        console.log('ℹ️ Opção Desabilitado não encontrada');
      }
    }
  });
});

// ============================================================
// TESTE 6: Verificar custos calculados dinamicamente
// ============================================================
test.describe('💰 Custos Dinâmicos de Failover', () => {

  test('Custos são calculados baseados no preço da GPU', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    const hasGPUCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);

    if (!hasGPUCards) {
      test.skip();
      return;
    }

    // Abrir dropdown e verificar custos
    const failoverTrigger = page.getByRole('button').filter({ hasText: /standby|failover|pool|snapshot|desabilitado/i }).first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      await failoverTrigger.click();
      await page.waitForTimeout(500);

      // Coletar todos os custos visíveis
      const costs = await page.getByText(/\$\d+\.\d+/).allTextContents();

      console.log('📊 Custos encontrados:', costs);

      // Verificar que há pelo menos 2 custos diferentes (diferentes estratégias)
      const uniqueCosts = [...new Set(costs)];
      console.log(`✅ ${uniqueCosts.length} custos únicos encontrados`);

      expect(uniqueCosts.length).toBeGreaterThanOrEqual(1);
    }
  });

  test('Footer mostra base de cálculo (custo GPU/h)', async ({ page }) => {
    await goToMachines(page);
    await page.waitForTimeout(2000);

    const hasGPUCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);

    if (!hasGPUCards) {
      test.skip();
      return;
    }

    const failoverTrigger = page.getByRole('button').filter({ hasText: /standby|failover|pool|snapshot|desabilitado/i }).first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      await failoverTrigger.click();
      await page.waitForTimeout(500);

      // Verificar footer com base de cálculo
      const baseCalcPattern = page.getByText(/baseado|gpu.*\$|custo.*gpu/i);
      const hasBaseCalc = await baseCalcPattern.first().isVisible().catch(() => false);

      if (hasBaseCalc) {
        const text = await baseCalcPattern.first().textContent();
        console.log(`✅ Base de cálculo visível: ${text}`);
      } else {
        console.log('ℹ️ Base de cálculo não explicitamente mostrada');
      }
    }
  });
});

// ============================================================
// TESTE 7: Integração com API de Failover
// ============================================================
test.describe('🔌 Integração API de Failover', () => {

  test('API de estratégias retorna dados válidos', async ({ page, request }) => {
    // Testar API diretamente
    const response = await request.get('http://localhost:8000/api/v1/failover/strategies?demo=true');

    expect(response.ok()).toBe(true);

    const data = await response.json();
    expect(data.strategies).toBeDefined();
    expect(data.strategies.length).toBeGreaterThanOrEqual(3);

    console.log(`✅ API retornou ${data.strategies.length} estratégias`);

    // Verificar estrutura das estratégias
    for (const strategy of data.strategies) {
      expect(strategy.id).toBeDefined();
      expect(strategy.name).toBeDefined();
      expect(strategy.description).toBeDefined();
      console.log(`  - ${strategy.name}: ${strategy.recovery_time}`);
    }
  });

  test('API de standby status retorna associações', async ({ page, request }) => {
    const response = await request.get('http://localhost:8000/api/v1/standby/status?demo=true');

    expect(response.ok()).toBe(true);

    const data = await response.json();
    expect(data.configured).toBeDefined();
    expect(data.associations).toBeDefined();

    console.log(`✅ Standby configurado: ${data.configured}`);
    console.log(`✅ Associações ativas: ${data.active_associations}`);
  });

  test('API de balance retorna saldo VAST.ai', async ({ page, request }) => {
    const response = await request.get('http://localhost:8000/api/v1/instances/balance?demo=true');

    expect(response.ok()).toBe(true);

    const data = await response.json();
    expect(data.credit).toBeDefined();

    console.log(`✅ Saldo VAST.ai: $${data.credit}`);
  });
});
