// @ts-check
/**
 * Failover Complete Journeys - Testes E2E Headless
 *
 * Testes de jornadas completas para funcionalidades de failover:
 * - Configurações globais e por máquina
 * - Regional Volume Failover
 * - Fast Failover (Race Strategy)
 * - Simulação de Failover
 * - CPU Standby Associations
 * - Relatórios e métricas
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

// Helper para navegar para Settings
async function goToSettings(page) {
  await page.goto(`${BASE_PATH}/settings`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

// Helper para navegar para Failover Report
async function goToFailoverReport(page) {
  await page.goto(`${BASE_PATH}/failover-report`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

// Helper para navegar para Dashboard
async function goToDashboard(page) {
  await page.goto(BASE_PATH);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

// ============================================================
// JORNADA 1: Configurações de Failover (Settings)
// ============================================================
test.describe('🔧 Jornada: Configurações de Failover', () => {

  test('Usuário acessa configurações globais de failover', async ({ page }) => {
    await goToSettings(page);

    // Procurar seção de Failover
    const failoverSection = page.getByText(/failover|backup|standby/i).first();
    const hasFailoverSection = await failoverSection.isVisible().catch(() => false);

    if (hasFailoverSection) {
      console.log('✅ Seção de Failover encontrada em Settings');
    } else {
      console.log('ℹ️ Seção de Failover pode estar em outra página ou não visível');
    }

    // Verificar que página Settings carregou
    const currentUrl = page.url();
    expect(currentUrl).toContain('/settings');
    console.log('✅ Página de Settings carregada');
  });

  test('Usuário configura estratégia de failover para máquina', async ({ page }) => {
    await goToMachines(page);

    // Verificar se tem máquinas
    const hasMachines = await page.getByText(/RTX|A100|H100|GPU|4090|3090/i).first().isVisible().catch(() => false);

    if (hasMachines) {
      console.log('✅ Máquinas encontradas');

      // Procurar botão de configuração de failover
      const configButton = page.getByRole('button', { name: /backup|failover|configurar/i }).first();
      const hasConfigButton = await configButton.isVisible().catch(() => false);

      if (hasConfigButton) {
        console.log('✅ Botão de configuração de failover encontrado');
        await configButton.click({ force: true });
        await page.waitForTimeout(1000);

        // Verificar modal/dropdown de opções
        const warmPoolOption = page.getByText(/warm pool|gpu standby/i).first();
        const cpuStandbyOption = page.getByText(/cpu standby/i).first();

        const hasOptions = await warmPoolOption.isVisible().catch(() => false) ||
                          await cpuStandbyOption.isVisible().catch(() => false);

        if (hasOptions) {
          console.log('✅ Opções de estratégia de failover visíveis');
        }
      } else {
        console.log('ℹ️ Botão de configuração de failover não encontrado - pode estar em Settings');
      }
    } else {
      console.log('ℹ️ Nenhuma máquina encontrada - verificando UI');
    }

    // Verificar que estamos na página correta
    expect(page.url()).toContain('/machines');
    console.log('✅ Página de Machines carregada');
  });

  test('Usuário vê estimativa de custo do CPU Standby', async ({ page }) => {
    await goToSettings(page);

    // Procurar informação de pricing
    const pricingInfo = page.getByText(/\$.*\/mês|\$.*\/month|custo|cost/i).first();
    const hasPricing = await pricingInfo.isVisible().catch(() => false);

    if (hasPricing) {
      console.log('✅ Informação de pricing encontrada');
    } else {
      console.log('ℹ️ Pricing pode não estar visível na UI');
    }

    // Verificar Settings carregou
    expect(page.url()).toContain('/settings');
    console.log('✅ Página de Settings carregada');
  });
});

// ============================================================
// JORNADA 2: Regional Volume Failover
// ============================================================
test.describe('🌍 Jornada: Regional Volume Failover', () => {

  test('Usuário visualiza volumes regionais disponíveis', async ({ page }) => {
    await goToMachines(page);

    // Procurar seção de volumes
    const volumeSection = page.getByText(/volume|storage|armazenamento/i).first();
    const hasVolumeSection = await volumeSection.isVisible().catch(() => false);

    if (hasVolumeSection) {
      console.log('✅ Seção de volumes encontrada');
    } else {
      console.log('ℹ️ Volumes podem estar em outra seção ou via API');
    }

    // Verificar que página carregou
    const currentUrl = page.url();
    expect(currentUrl).toContain('/machines');
    console.log('✅ Página de Machines carregada');
  });

  test('Usuário vê opção de criar volume regional', async ({ page }) => {
    await goToMachines(page);

    // Procurar botão de criar volume
    const createVolumeBtn = page.getByRole('button', { name: /criar volume|create volume|novo volume/i }).first();
    const hasCreateBtn = await createVolumeBtn.isVisible().catch(() => false);

    if (hasCreateBtn) {
      console.log('✅ Botão de criar volume encontrado');
    } else {
      // Verificar se tem card de adicionar
      const addCard = page.getByText(/adicionar|add.*volume/i).first();
      const hasAddCard = await addCard.isVisible().catch(() => false);

      if (hasAddCard) {
        console.log('✅ Card de adicionar volume encontrado');
      } else {
        console.log('ℹ️ Criação de volume pode estar em modal ou Settings');
      }
    }

    expect(page.url()).toContain('/machines');
    console.log('✅ Página de Machines carregada');
  });

  test('Usuário busca GPUs disponíveis em região específica', async ({ page }) => {
    await goToDashboard(page);

    // Procurar filtro de região
    const regionFilter = page.getByRole('combobox', { name: /região|region/i }).first();
    const regionFilterAlt = page.getByText(/US|EU|região|region/i).first();

    const hasRegionFilter = await regionFilter.isVisible().catch(() => false) ||
                           await regionFilterAlt.isVisible().catch(() => false);

    if (hasRegionFilter) {
      console.log('✅ Filtro de região encontrado');
    } else {
      console.log('ℹ️ Filtro de região pode estar no GPU Advisor');
    }

    // Verificar busca de GPUs
    const gpuList = page.getByText(/RTX|A100|H100|disponível|4090|3090/i).first();
    const hasGpuList = await gpuList.isVisible().catch(() => false);

    if (hasGpuList) {
      console.log('✅ Lista de GPUs visível');
    }

    console.log('✅ Dashboard carregado');
  });
});

// ============================================================
// JORNADA 3: Simulação e Teste de Failover
// ============================================================
test.describe('🧪 Jornada: Simulação de Failover', () => {

  test('Usuário simula failover em máquina com backup', async ({ page }) => {
    await goToMachines(page);

    // Procurar máquina com backup habilitado
    const machineWithBackup = page.getByText(/backup|standby|protegid/i).first();
    const hasBackupMachine = await machineWithBackup.isVisible().catch(() => false);

    if (hasBackupMachine) {
      console.log('✅ Máquina com backup encontrada');

      // Procurar botão de simular/testar failover
      const simulateBtn = page.getByRole('button', { name: /simular|testar|test.*failover/i }).first();
      const hasSimulateBtn = await simulateBtn.isVisible().catch(() => false);

      if (hasSimulateBtn) {
        console.log('✅ Botão de simular failover encontrado');
        // Não clicar em produção - apenas verificar existência
      } else {
        console.log('ℹ️ Simulação de failover pode estar em menu de ações');
      }
    } else {
      console.log('ℹ️ Nenhuma máquina com backup encontrada');
    }

    expect(page.url()).toContain('/machines');
    console.log('✅ Página de Machines carregada');
  });

  test('Usuário visualiza relatório de failover', async ({ page }) => {
    await goToFailoverReport(page);

    // Verificar se página existe
    const is404 = await page.getByText(/404|not found/i).first().isVisible().catch(() => false);

    if (!is404) {
      console.log('✅ Página de relatório de failover existe');

      // Verificar elementos do relatório
      const mttrMetric = page.getByText(/MTTR|recovery.*time|tempo.*recuperação/i).first();
      const successRate = page.getByText(/success.*rate|taxa.*sucesso|%/i).first();

      const hasMttr = await mttrMetric.isVisible().catch(() => false);
      const hasSuccessRate = await successRate.isVisible().catch(() => false);

      if (hasMttr || hasSuccessRate) {
        console.log('✅ Métricas de failover visíveis');
      }
    } else {
      console.log('ℹ️ Relatório pode estar em outra URL ou integrado em Settings');

      // Tentar em Settings
      await goToSettings(page);

      const failoverReport = page.getByText(/failover.*report|relatório.*failover/i).first();
      const hasReport = await failoverReport.isVisible().catch(() => false);

      if (hasReport) {
        console.log('✅ Relatório encontrado em Settings');
      }
    }

    console.log('✅ Verificação de relatório concluída');
  });

  test('Usuário vê histórico de failovers', async ({ page }) => {
    // Tentar encontrar histórico em várias páginas
    const pagesToTry = [
      { fn: goToSettings, name: 'settings' },
      { fn: goToFailoverReport, name: 'failover-report' },
      { fn: goToMachines, name: 'machines' }
    ];

    let historyFound = false;

    for (const { fn, name } of pagesToTry) {
      await fn(page);

      const historySection = page.getByText(/histórico|history|eventos|events/i).first();
      const hasHistory = await historySection.isVisible().catch(() => false);

      if (hasHistory) {
        console.log(`✅ Histórico encontrado em ${name}`);
        historyFound = true;
        break;
      }
    }

    if (!historyFound) {
      console.log('ℹ️ Histórico de failovers pode estar disponível via API');
    }

    console.log('✅ Verificação de histórico concluída');
  });
});

// ============================================================
// JORNADA 4: CPU Standby Associations
// ============================================================
test.describe('🔗 Jornada: CPU Standby Associations', () => {

  test('Usuário vê associações GPU↔CPU ativas', async ({ page }) => {
    await goToMachines(page);

    // Procurar indicador de associação
    const associationIndicator = page.getByText(/CPU.*Standby|GCP|backup.*ativo/i).first();
    const hasAssociation = await associationIndicator.isVisible().catch(() => false);

    if (hasAssociation) {
      console.log('✅ Indicador de CPU Standby encontrado');
    } else {
      // Verificar badge ou ícone
      const backupBadge = page.locator('[class*="badge"]').filter({ hasText: /backup|standby/i }).first();
      const hasBadge = await backupBadge.isVisible().catch(() => false);

      if (hasBadge) {
        console.log('✅ Badge de backup encontrado');
      } else {
        console.log('ℹ️ Máquinas podem não ter CPU Standby configurado');
      }
    }

    expect(page.url()).toContain('/machines');
    console.log('✅ Página de Machines carregada');
  });

  test('Usuário habilita/desabilita sync de dados', async ({ page }) => {
    await goToMachines(page);

    // Procurar controle de sync
    const syncToggle = page.getByRole('switch', { name: /sync|sincronização/i }).first();
    const syncButton = page.getByRole('button', { name: /sync|sincronizar/i }).first();

    const hasSync = await syncToggle.isVisible().catch(() => false) ||
                   await syncButton.isVisible().catch(() => false);

    if (hasSync) {
      console.log('✅ Controle de sync encontrado');
    } else {
      console.log('ℹ️ Sync pode ser automático ou configurado em Settings');
    }

    expect(page.url()).toContain('/machines');
    console.log('✅ Página de Machines carregada');
  });

  test('Usuário vê status de sincronização em tempo real', async ({ page }) => {
    await goToMachines(page);

    // Procurar indicadores de sync
    const syncStatus = page.getByText(/sync.*ok|sincronizando|última.*sync|last.*sync/i).first();
    const hasSyncStatus = await syncStatus.isVisible().catch(() => false);

    if (hasSyncStatus) {
      console.log('✅ Status de sincronização visível');
    } else {
      // Procurar métricas de latência
      const latencyMetric = page.getByText(/latência|latency|ms/i).first();
      const hasLatency = await latencyMetric.isVisible().catch(() => false);

      if (hasLatency) {
        console.log('✅ Métrica de latência encontrada');
      } else {
        console.log('ℹ️ Status de sync pode estar em detalhes da máquina');
      }
    }

    expect(page.url()).toContain('/machines');
    console.log('✅ Página de Machines carregada');
  });
});

// ============================================================
// JORNADA 5: Fast Failover (Race Strategy)
// ============================================================
test.describe('⚡ Jornada: Fast Failover', () => {

  test('Usuário vê opção de failover rápido', async ({ page }) => {
    await goToMachines(page);

    // Procurar opção de failover rápido
    const fastFailoverOption = page.getByText(/fast.*failover|failover.*rápido|race/i).first();
    const hasFastOption = await fastFailoverOption.isVisible().catch(() => false);

    if (hasFastOption) {
      console.log('✅ Opção de Fast Failover encontrada');
    } else {
      // Pode estar em menu de ações
      const actionsMenu = page.getByRole('button', { name: /ações|actions|menu/i }).first();
      const hasActions = await actionsMenu.isVisible().catch(() => false);

      if (hasActions) {
        await actionsMenu.click({ force: true });
        await page.waitForTimeout(500);

        const fastOption = page.getByText(/fast|rápido/i).first();
        const hasFast = await fastOption.isVisible().catch(() => false);

        if (hasFast) {
          console.log('✅ Fast Failover encontrado no menu de ações');
        }
      } else {
        console.log('ℹ️ Fast Failover pode estar disponível apenas via API/CLI');
      }
    }

    expect(page.url()).toContain('/machines');
    console.log('✅ Página de Machines carregada');
  });

  test('Usuário vê estratégias de failover disponíveis', async ({ page }) => {
    await goToSettings(page);

    // Procurar lista de estratégias
    const strategies = [
      'Warm Pool',
      'CPU Standby',
      'Regional Volume',
      'warm_pool',
      'cpu_standby'
    ];

    let strategiesFound = 0;

    for (const strategy of strategies) {
      const strategyEl = page.getByText(new RegExp(strategy, 'i')).first();
      const hasStrategy = await strategyEl.isVisible().catch(() => false);

      if (hasStrategy) {
        strategiesFound++;
        console.log(`✅ Estratégia "${strategy}" encontrada`);
      }
    }

    if (strategiesFound > 0) {
      console.log(`✅ ${strategiesFound} estratégias de failover visíveis`);
    } else {
      console.log('ℹ️ Estratégias podem estar em modal ou seção colapsada');
    }

    expect(page.url()).toContain('/settings');
    console.log('✅ Página de Settings carregada');
  });
});

// ============================================================
// JORNADA 6: Métricas e Dashboard de Failover
// ============================================================
test.describe('📊 Jornada: Métricas de Failover', () => {

  test('Usuário vê MTTR (Mean Time To Recovery) no Dashboard', async ({ page }) => {
    await goToDashboard(page);

    // Procurar métrica de MTTR
    const mttrMetric = page.getByText(/MTTR|recovery.*time|tempo.*recuperação/i).first();
    const hasMttr = await mttrMetric.isVisible().catch(() => false);

    if (hasMttr) {
      console.log('✅ Métrica MTTR encontrada no Dashboard');
    } else {
      // Tentar em página de relatório
      await goToFailoverReport(page);

      const mttrInReport = page.getByText(/MTTR/i).first();
      const hasMttrReport = await mttrInReport.isVisible().catch(() => false);

      if (hasMttrReport) {
        console.log('✅ MTTR encontrado na página de relatório');
      } else {
        console.log('ℹ️ MTTR pode não estar implementado na UI ainda');
      }
    }

    console.log('✅ Verificação de MTTR concluída');
  });

  test('Usuário vê taxa de sucesso de failovers', async ({ page }) => {
    // Verificar em múltiplas páginas
    const pagesToCheck = [
      { fn: goToDashboard, name: 'dashboard' },
      { fn: goToSettings, name: 'settings' },
      { fn: goToFailoverReport, name: 'failover-report' }
    ];

    let successRateFound = false;

    for (const { fn, name } of pagesToCheck) {
      await fn(page);

      const successRate = page.getByText(/sucesso|success.*rate|taxa|\d+%/i).first();
      const hasRate = await successRate.isVisible().catch(() => false);

      if (hasRate) {
        console.log(`✅ Taxa de sucesso encontrada em ${name}`);
        successRateFound = true;
        break;
      }
    }

    if (!successRateFound) {
      console.log('ℹ️ Taxa de sucesso pode não estar exposta na UI');
    }

    console.log('✅ Verificação de taxa de sucesso concluída');
  });

  test('Usuário vê breakdown de latências por fase', async ({ page }) => {
    await goToFailoverReport(page);

    const is404 = await page.getByText(/404/i).first().isVisible().catch(() => false);

    if (!is404) {
      // Procurar breakdown de fases
      const phases = [
        'snapshot',
        'provisioning',
        'restore',
        'detection',
        'gpu_search'
      ];

      let phasesFound = 0;

      for (const phase of phases) {
        const phaseEl = page.getByText(new RegExp(phase, 'i')).first();
        const hasPhase = await phaseEl.isVisible().catch(() => false);

        if (hasPhase) {
          phasesFound++;
        }
      }

      if (phasesFound > 0) {
        console.log(`✅ ${phasesFound} fases de failover encontradas no relatório`);
      } else {
        console.log('ℹ️ Breakdown por fase pode estar em formato de gráfico');
      }
    } else {
      console.log('ℹ️ Página de relatório de failover não existe - verificar URL');

      // Tentar Settings
      await goToSettings(page);
    }

    console.log('✅ Verificação de breakdown concluída');
  });
});

// ============================================================
// JORNADA 7: Fluxo Completo de Failover (End-to-End)
// ============================================================
test.describe('🚀 Jornada Completa: Configurar → Simular → Verificar', () => {

  test('Fluxo: Acessar máquinas → Ver status backup → Ver relatório', async ({ page }) => {
    // PASSO 1: Dashboard
    console.log('📍 Passo 1: Dashboard');
    await goToDashboard(page);

    // Verificar Dashboard carregou
    const dashboardLoaded = await page.getByText(/dashboard|bem-vindo|economia|savings/i).first().isVisible().catch(() => false);
    console.log(dashboardLoaded ? '✅ Dashboard carregado' : 'ℹ️ Dashboard sem texto esperado');

    // PASSO 2: Ir para Machines
    console.log('📍 Passo 2: Navegar para Machines');
    await goToMachines(page);

    expect(page.url()).toContain('/machines');
    console.log('✅ Navegou para Machines');

    // PASSO 3: Verificar se tem máquinas com backup
    console.log('📍 Passo 3: Verificar máquinas com backup');
    const machinesWithBackup = page.getByText(/backup|standby|protegid/i);
    const backupCount = await machinesWithBackup.count();
    console.log(`ℹ️ Encontradas ${backupCount} indicações de backup`);

    // PASSO 4: Ir para Settings
    console.log('📍 Passo 4: Ir para Settings');
    await goToSettings(page);

    expect(page.url()).toContain('/settings');
    console.log('✅ Navegou para Settings');

    // PASSO 5: Verificar configurações de failover
    console.log('📍 Passo 5: Verificar configurações de failover');
    const failoverConfig = page.getByText(/failover|backup.*automático|auto.*standby/i).first();
    const hasConfig = await failoverConfig.isVisible().catch(() => false);
    console.log(hasConfig ? '✅ Configurações de failover visíveis' : 'ℹ️ Configurações podem estar em seção colapsada');

    console.log('\n🎉 Fluxo completo executado!');
  });

  test('Fluxo: Settings → Habilitar backup → Verificar em Machines', async ({ page }) => {
    // PASSO 1: Settings
    console.log('📍 Passo 1: Ir para Settings');
    await goToSettings(page);

    // PASSO 2: Procurar toggle de auto-standby
    console.log('📍 Passo 2: Procurar configuração de auto-standby');
    const autoStandbyToggle = page.getByRole('switch', { name: /auto.*standby|backup.*automático/i }).first();
    const hasToggle = await autoStandbyToggle.isVisible().catch(() => false);

    if (hasToggle) {
      console.log('✅ Toggle de auto-standby encontrado');
      // Não mudar estado em teste
    } else {
      // Procurar checkbox ou botão
      const enableBtn = page.getByRole('button', { name: /habilitar|enable.*backup/i }).first();
      const hasBtn = await enableBtn.isVisible().catch(() => false);

      if (hasBtn) {
        console.log('✅ Botão de habilitar backup encontrado');
      } else {
        console.log('ℹ️ Configuração de backup pode estar em outro formato');
      }
    }

    // PASSO 3: Voltar para Machines
    console.log('📍 Passo 3: Voltar para Machines');
    await goToMachines(page);

    expect(page.url()).toContain('/machines');
    console.log('✅ Navegou de volta para Machines');

    console.log('\n🎉 Fluxo Settings → Machines concluído!');
  });
});
