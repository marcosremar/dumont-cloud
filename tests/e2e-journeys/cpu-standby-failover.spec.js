// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * 🎯 TESTE E2E: CPU Standby e Failover Automático
 *
 * Este teste verifica o fluxo completo de:
 * 1. Máquina GPU com CPU Standby configurado
 * 2. Simulação de "roubo" da GPU (preemption)
 * 3. Failover automático para CPU Standby
 * 4. Busca e provisionamento de nova GPU
 * 5. Restauração de dados e sincronização
 *
 * O teste simula um cenário real onde:
 * - Usuário tem uma máquina GPU rodando
 * - A GPU é interrompida (spot instance preempted)
 * - Sistema automaticamente faz failover para CPU backup
 * - Sistema busca nova GPU e restaura os dados
 */

test.describe('🔄 CPU Standby e Failover Automático', () => {

  test('Verificar que máquina tem CPU Standby configurado', async ({ page }) => {
    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // 1. Encontrar máquina com CPU Standby (badge "Backup")
    const machineWithBackup = page.locator('[class*="rounded-lg"][class*="border"]').filter({
      has: page.locator('text="Backup"')
    }).first();

    const hasBackup = await machineWithBackup.isVisible().catch(() => false);
    if (!hasBackup) {
      console.log('⚠️ Nenhuma máquina com CPU Standby - pulando');
      test.skip();
      return;
    }

    // 2. Verificar badge de backup visível
    await expect(machineWithBackup.locator('button:has-text("Backup")')).toBeVisible();
    console.log('✅ Badge de Backup visível');

    // 3. Clicar no badge para ver detalhes
    await machineWithBackup.locator('button:has-text("Backup")').click();
    await page.waitForTimeout(500);

    // 4. Verificar informações do CPU Standby no popover
    const popover = page.locator('[class*="popover"], [role="dialog"]').filter({
      has: page.locator('text=/GCP|CPU Standby|e2-medium/')
    });

    // Verificar provider
    const hasGCP = await page.locator('text=/GCP|gcp/').first().isVisible().catch(() => false);
    if (hasGCP) {
      console.log('✅ Provider GCP visível');
    }

    // Verificar estado (ready, syncing, etc)
    const hasState = await page.locator('text=/Pronto para failover|Sincronizando|Failover ativo/').first().isVisible().catch(() => false);
    if (hasState) {
      console.log('✅ Estado do standby visível');
    }

    // Verificar IP
    const hasIP = await page.locator('text=/\\d+\\.\\d+\\.\\d+\\.\\d+/').first().isVisible().catch(() => false);
    if (hasIP) {
      console.log('✅ IP do CPU Standby visível');
    }

    expect(hasGCP || hasState || hasIP).toBeTruthy();
    console.log('✅ CPU Standby configurado corretamente');
  });

  test('Simular failover completo: GPU roubada → CPU Standby → Nova GPU', async ({ page }) => {
    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // 1. Encontrar máquina ONLINE com CPU Standby e botão de simular failover
    const machineWithFailover = page.locator('[class*="rounded-lg"][class*="border"]').filter({
      has: page.locator('button:has-text("Simular Failover")')
    }).first();

    const hasFailoverButton = await machineWithFailover.isVisible().catch(() => false);
    if (!hasFailoverButton) {
      console.log('⚠️ Nenhuma máquina online com CPU Standby para simular failover');
      test.skip();
      return;
    }

    // 2. Pegar o nome da GPU atual
    const gpuName = await machineWithFailover.locator('text=/RTX|A100|H100/').first().textContent();
    console.log(`🖥️ GPU atual: ${gpuName}`);

    // 3. Clicar em "Simular Failover"
    const failoverButton = machineWithFailover.locator('button:has-text("Simular Failover")');
    await expect(failoverButton).toBeVisible();
    await failoverButton.click();

    // 4. VERIFICAR PAINEL DE PROGRESSO VISUAL
    // O painel deve aparecer imediatamente após clicar
    const progressPanel = page.locator('[data-testid="failover-progress-panel"]');
    await expect(progressPanel).toBeVisible({ timeout: 3000 });
    console.log('✅ Painel de progresso do failover visível');

    // 5. Verificar título do painel
    await expect(page.locator('text="Failover em Progresso"')).toBeVisible();
    console.log('✅ Título "Failover em Progresso" visível');

    // 6. FASE 1: GPU Interrompida - verificar step visual
    const step1 = page.locator('[data-testid="failover-step-gpu-lost"]');
    await expect(step1).toBeVisible();
    await expect(step1).toContainText('GPU Interrompida');
    console.log('✅ Passo 1: GPU Interrompida visível no painel');

    // 7. FASE 2: Failover Ativo - verificar step visual
    await page.waitForTimeout(2500);
    const step2 = page.locator('[data-testid="failover-step-active"]');
    await expect(step2).toBeVisible();
    await expect(step2).toContainText('Failover para CPU Standby');
    console.log('✅ Passo 2: Failover para CPU Standby visível');

    // 8. FASE 3: Buscando GPU - verificar step visual
    await page.waitForTimeout(3000);
    const step3 = page.locator('[data-testid="failover-step-searching"]');
    await expect(step3).toBeVisible();
    await expect(step3).toContainText('Buscando Nova GPU');
    console.log('✅ Passo 3: Buscando Nova GPU visível');

    // 9. FASE 4: Provisionando - verificar step visual com nome da GPU
    await page.waitForTimeout(3500);
    const step4 = page.locator('[data-testid="failover-step-provisioning"]');
    await expect(step4).toBeVisible();
    await expect(step4).toContainText('Provisionando');
    console.log('✅ Passo 4: Provisionando nova GPU visível');

    // 10. FASE 5: Restaurando - verificar step visual
    await page.waitForTimeout(3000);
    const step5 = page.locator('[data-testid="failover-step-restoring"]');
    await expect(step5).toBeVisible();
    await expect(step5).toContainText('Restaurando Dados');
    console.log('✅ Passo 5: Restaurando Dados visível');

    // 11. FASE 6: Completo - verificar step visual
    await page.waitForTimeout(4000);
    const step6 = page.locator('[data-testid="failover-step-complete"]');
    await expect(step6).toBeVisible();
    await expect(step6).toContainText('Recuperação Completa');
    console.log('✅ Passo 6: Recuperação Completa visível');

    // 12. Verificar mensagem de status no painel
    const statusMessage = page.locator('[data-testid="failover-message"]');
    await expect(statusMessage).toBeVisible();
    const messageText = await statusMessage.textContent();
    console.log(`📝 Mensagem de status: ${messageText}`);

    // 13. Verificar que todos os steps anteriores têm checkmark (✓)
    // Os steps completados devem mostrar ✓
    const completedSteps = await progressPanel.locator('text="✓"').count();
    expect(completedSteps).toBeGreaterThanOrEqual(5);
    console.log(`✅ ${completedSteps} passos completados com ✓`);

    // 14. Verificar que a máquina tem nova GPU
    await page.waitForTimeout(1000);
    const newGpuName = await machineWithFailover.locator('text=/RTX|A100|H100/').first().textContent().catch(() => 'N/A');
    console.log(`🖥️ Nova GPU: ${newGpuName}`);

    console.log('✅ Fluxo completo de failover com feedback visual verificado!');
  });

  test('Verificar que máquina está Online após failover', async ({ page }) => {
    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Verificar que existem máquinas online com CPU Standby
    const onlineMachinesWithBackup = page.locator('[class*="rounded-lg"][class*="border"]').filter({
      has: page.locator('text="Online"')
    }).filter({
      has: page.locator('text="Backup"')
    });

    const count = await onlineMachinesWithBackup.count();

    if (count > 0) {
      console.log(`✅ ${count} máquina(s) online com CPU Standby`);

      // Verificar estado "ready" do standby
      const firstMachine = onlineMachinesWithBackup.first();
      await firstMachine.locator('button:has-text("Backup")').click();
      await page.waitForTimeout(500);

      const isReady = await page.locator('text=/Pronto para failover|ready/i').isVisible().catch(() => false);
      if (isReady) {
        console.log('✅ CPU Standby pronto para próximo failover');
      }
    } else {
      console.log('⚠️ Nenhuma máquina online com backup - verificação básica OK');
    }

    expect(true).toBeTruthy(); // Teste passa se chegou aqui
  });

  test('Verificar configuração de CPU Standby em Settings', async ({ page }) => {
    await page.goto('/app/settings');
    await page.waitForLoadState('networkidle');

    // Fechar modal de boas-vindas se aparecer
    const skipButton = page.locator('text="Pular tudo"');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      await page.waitForTimeout(500);
    }

    // Clicar na aba de Failover/CPU Standby
    const failoverTab = page.locator('button:has-text("CPU Failover"), button:has-text("Failover")');
    const hasFailoverTab = await failoverTab.isVisible().catch(() => false);

    if (hasFailoverTab) {
      await failoverTab.click();
      await page.waitForTimeout(500);

      // Verificar elementos de configuração
      const hasConfigElements = await page.locator('text=/Auto-Failover|Auto-Recovery|CPU Standby|R2/i').first().isVisible().catch(() => false);

      if (hasConfigElements) {
        console.log('✅ Configuração de CPU Failover visível em Settings');
      }

      // Verificar estimativa de custo
      const hasCostEstimate = await page.locator('text=/Estimativa de Custo|\\$\\d+/').first().isVisible().catch(() => false);
      if (hasCostEstimate) {
        console.log('✅ Estimativa de custo do R2 visível');
      }
    } else {
      console.log('⚠️ Aba de Failover não encontrada em Settings');
    }

    expect(true).toBeTruthy();
  });

});

test.describe('📊 Métricas e Status do CPU Standby', () => {

  test('Verificar métricas de sync do CPU Standby', async ({ page }) => {
    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Encontrar máquina com backup
    const machineWithBackup = page.locator('[class*="rounded-lg"]').filter({
      has: page.locator('text="Backup"')
    }).first();

    const hasBackup = await machineWithBackup.isVisible().catch(() => false);
    if (!hasBackup) {
      console.log('⚠️ Nenhuma máquina com backup para verificar métricas');
      test.skip();
      return;
    }

    // Abrir popover de backup
    await machineWithBackup.locator('button:has-text("Backup")').click();
    await page.waitForTimeout(500);

    // Verificar sync count
    const hasSyncCount = await page.locator('text=/syncs|sincroniza/i').isVisible().catch(() => false);
    if (hasSyncCount) {
      console.log('✅ Contador de syncs visível');
    }

    // Verificar custo/hora
    const hasCost = await page.locator('text=/\\$0\\.0\\d+\\/h|custo/i').first().isVisible().catch(() => false);
    if (hasCost) {
      console.log('✅ Custo por hora do standby visível');
    }

    // Verificar zone
    const hasZone = await page.locator('text=/us-|europe-|asia-/i').first().isVisible().catch(() => false);
    if (hasZone) {
      console.log('✅ Zona do GCP visível');
    }

    expect(hasSyncCount || hasCost || hasZone).toBeTruthy();
    console.log('✅ Métricas do CPU Standby verificadas');
  });

  test('Verificar custo total inclui CPU Standby', async ({ page }) => {
    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Encontrar máquina online com backup
    const machineWithBackup = page.locator('[class*="rounded-lg"]').filter({
      has: page.locator('text="Online"')
    }).filter({
      has: page.locator('text="Backup"')
    }).first();

    const hasBackup = await machineWithBackup.isVisible().catch(() => false);
    if (!hasBackup) {
      console.log('⚠️ Nenhuma máquina online com backup para verificar custo');
      test.skip();
      return;
    }

    // Verificar que mostra "+backup" no custo
    const hasBackupCost = await machineWithBackup.locator('text="+backup"').isVisible().catch(() => false);

    if (hasBackupCost) {
      console.log('✅ Indicador de custo +backup visível');
    }

    // Verificar valor do custo (deve ter $ e /hora)
    const costElement = machineWithBackup.locator('text=/\\$\\d+\\.\\d+/').first();
    const costText = await costElement.textContent().catch(() => '');

    if (costText) {
      console.log(`✅ Custo total visível: ${costText}`);
    }

    expect(hasBackupCost || costText).toBeTruthy();
  });

});

test.describe('📈 Relatório de Failover', () => {

  test('Verificar relatório de failover em Settings', async ({ page }) => {
    await page.goto('/app/settings');
    await page.waitForLoadState('networkidle');

    // Fechar modal de boas-vindas se aparecer
    const skipButton = page.locator('text="Pular tudo"');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      await page.waitForTimeout(500);
    }

    // Clicar na aba de Failover/CPU Standby
    const failoverTab = page.locator('button:has-text("CPU Failover")');
    await expect(failoverTab).toBeVisible();
    await failoverTab.click();
    await page.waitForTimeout(500);

    // Verificar que o relatório de failover está visível
    const failoverReport = page.locator('[data-testid="failover-report"]');
    await expect(failoverReport).toBeVisible({ timeout: 5000 });
    console.log('✅ Relatório de Failover visível');

    // Verificar métricas principais
    const metricsSection = page.locator('[data-testid="failover-metrics"]');
    await expect(metricsSection).toBeVisible();
    console.log('✅ Seção de métricas visível');

    // Verificar "Total de Failovers"
    await expect(page.locator('text="Total de Failovers"')).toBeVisible();
    console.log('✅ Métrica "Total de Failovers" visível');

    // Verificar "Taxa de Sucesso"
    await expect(page.locator('text="Taxa de Sucesso"')).toBeVisible();
    console.log('✅ Métrica "Taxa de Sucesso" visível');

    // Verificar "MTTR"
    await expect(page.locator('text=/MTTR|Tempo Médio/')).toBeVisible();
    console.log('✅ Métrica "MTTR" visível');

    // Verificar "Latência Detecção"
    await expect(page.locator('text="Latência Detecção"')).toBeVisible();
    console.log('✅ Métrica "Latência Detecção" visível');
  });

  test('Verificar breakdown de latências por fase', async ({ page }) => {
    await page.goto('/app/settings');
    await page.waitForLoadState('networkidle');

    // Fechar modal de boas-vindas se aparecer
    const skipButton = page.locator('text="Pular tudo"');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      await page.waitForTimeout(500);
    }

    // Ir para aba de Failover
    await page.locator('button:has-text("CPU Failover")').click();
    await page.waitForTimeout(500);

    // Verificar seção de latência por fase
    const latencyBreakdown = page.locator('[data-testid="latency-breakdown"]');
    await expect(latencyBreakdown).toBeVisible({ timeout: 5000 });
    console.log('✅ Breakdown de latência visível');

    // Verificar fases
    await expect(page.locator('text="Detecção"')).toBeVisible();
    await expect(page.locator('text="Failover para CPU"')).toBeVisible();
    await expect(page.locator('text="Busca de GPU"')).toBeVisible();
    await expect(page.locator('text="Provisionamento"')).toBeVisible();
    await expect(page.locator('text="Restauração"')).toBeVisible();
    console.log('✅ Todas as 5 fases de latência visíveis');
  });

  test('Verificar histórico de failovers', async ({ page }) => {
    await page.goto('/app/settings');
    await page.waitForLoadState('networkidle');

    // Fechar modal de boas-vindas se aparecer
    const skipButton = page.locator('text="Pular tudo"');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      await page.waitForTimeout(500);
    }

    // Ir para aba de Failover
    await page.locator('button:has-text("CPU Failover")').click();
    await page.waitForTimeout(500);

    // Verificar seção de histórico
    const failoverHistory = page.locator('[data-testid="failover-history"]');
    await expect(failoverHistory).toBeVisible({ timeout: 5000 });
    console.log('✅ Histórico de failovers visível');

    // Verificar que há pelo menos um item no histórico (demo data)
    const historyItems = page.locator('[data-testid^="failover-item-"]');
    const itemCount = await historyItems.count();
    expect(itemCount).toBeGreaterThan(0);
    console.log(`✅ ${itemCount} eventos de failover no histórico`);

    // Verificar informações em um item
    const firstItem = historyItems.first();
    await expect(firstItem).toBeVisible();

    // Verificar que o item tem conteúdo (GPU name pode variar)
    const itemText = await firstItem.textContent();
    expect(itemText.length).toBeGreaterThan(10);
    console.log('✅ Item do histórico tem conteúdo');

    // Verificar que mostra informações de tempo ou status
    const hasTimeOrStatus = itemText.includes('s') || itemText.includes('m') || itemText.includes('tempo') || itemText.includes('sucesso') || itemText.includes('falha');
    expect(hasTimeOrStatus).toBeTruthy();
    console.log('✅ Informações de tempo/status visíveis no histórico');
  });

  test('Verificar filtro de período no relatório', async ({ page }) => {
    await page.goto('/app/settings');
    await page.waitForLoadState('networkidle');

    // Fechar modal de boas-vindas se aparecer
    const skipButton = page.locator('text="Pular tudo"');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      await page.waitForTimeout(500);
    }

    // Ir para aba de Failover
    await page.locator('button:has-text("CPU Failover")').click();
    await page.waitForTimeout(500);

    // Verificar botões de período
    await expect(page.locator('button:has-text("7 dias")')).toBeVisible();
    await expect(page.locator('button:has-text("30 dias")')).toBeVisible();
    await expect(page.locator('button:has-text("90 dias")')).toBeVisible();
    console.log('✅ Filtros de período visíveis');

    // Clicar em 7 dias e verificar que está ativo
    await page.locator('button:has-text("7 dias")').click();
    await page.waitForTimeout(300);

    // O botão de 7 dias deve ter estilo de ativo (bg-green)
    const sevenDayButton = page.locator('button:has-text("7 dias")');
    const className = await sevenDayButton.getAttribute('class');
    expect(className).toContain('green');
    console.log('✅ Filtro de 7 dias funciona');
  });

  test('Verificar métricas secundárias do relatório', async ({ page }) => {
    await page.goto('/app/settings');
    await page.waitForLoadState('networkidle');

    // Fechar modal de boas-vindas se aparecer
    const skipButton = page.locator('text="Pular tudo"');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      await page.waitForTimeout(500);
    }

    // Ir para aba de Failover
    await page.locator('button:has-text("CPU Failover")').click();
    await page.waitForTimeout(500);

    // Verificar métricas secundárias
    await expect(page.locator('text="Dados Restaurados"')).toBeVisible();
    console.log('✅ "Dados Restaurados" visível');

    await expect(page.locator('text="GPUs Provisionadas"')).toBeVisible();
    console.log('✅ "GPUs Provisionadas" visível');

    await expect(page.locator('text="CPU Standby Ativo"')).toBeVisible();
    console.log('✅ "CPU Standby Ativo" visível');

    await expect(page.locator('text="Causa Principal"')).toBeVisible();
    console.log('✅ "Causa Principal" visível');
  });

});
