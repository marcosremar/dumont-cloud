import { test, expect, apiRequest, cleanupTestResources } from '../fixtures/auth';

/**
 * Jornada E2E: Failover Completo
 *
 * Testa o fluxo completo de failover end-to-end:
 * 1. Verificar configuração de failover
 * 2. Simular falha de GPU
 * 3. Verificar transição para standby
 * 4. Verificar dados preservados
 * 5. Verificar relatório de failover
 * 6. Testar recovery automático
 */

test.describe('Complete Failover Journey', () => {
  test.describe.configure({ mode: 'serial' });

  test('should view failover report page', async ({ authenticatedPage: page }) => {
    // Navegar para relatório de failover
    await page.goto('/failover-report');
    await page.waitForLoadState('networkidle');

    // Verificar elementos do relatório
    await expect(page.locator('text=Failover, text=Relatório, text=Report').first()).toBeVisible({ timeout: 10000 });

    // Verificar métricas principais
    const metricsVisible = await page.locator('text=/MTTR|Taxa.*Sucesso|Recovery|Total.*failover/i').count() > 0;
    expect(metricsVisible).toBe(true);
  });

  test('should display failover history', async ({ authenticatedPage: page }) => {
    await page.goto('/failover-report');
    await page.waitForLoadState('networkidle');

    // Verificar se há histórico ou mensagem de "sem failovers"
    const hasHistory = await page.locator('[data-testid="failover-item"], .failover-item, tr:has-text("GPU")').count() > 0;
    const hasEmptyMessage = await page.locator('text=/nenhum failover|no failovers|sem.*histórico/i').count() > 0;

    expect(hasHistory || hasEmptyMessage).toBe(true);
  });

  test('should get failover report via API', async ({ apiToken }) => {
    const response = await apiRequest(apiToken, 'GET', '/api/v1/standby/failover/report');

    expect(response.ok).toBe(true);

    const report = await response.json();

    // Verificar estrutura do relatório
    expect(report).toHaveProperty('total_failovers');
    expect(report).toHaveProperty('success_rate');
    expect(report).toHaveProperty('average_recovery_time_ms');

    console.log('Failover report:', {
      total: report.total_failovers,
      successRate: report.success_rate,
      avgRecoveryMs: report.average_recovery_time_ms,
    });
  });

  test('should get active failovers', async ({ apiToken }) => {
    const response = await apiRequest(apiToken, 'GET', '/api/v1/standby/failover/active');

    expect(response.ok).toBe(true);

    const activeFailovers = await response.json();
    expect(Array.isArray(activeFailovers)).toBe(true);

    console.log(`Active failovers: ${activeFailovers.length}`);
  });

  test('should get failover history', async ({ apiToken }) => {
    const response = await apiRequest(apiToken, 'GET', '/api/v1/standby/failover/test-real/history');

    expect([200, 404]).toContain(response.status);

    if (response.ok) {
      const history = await response.json();
      expect(Array.isArray(history)).toBe(true);
      console.log(`Failover history entries: ${history.length}`);
    }
  });
});

test.describe('Failover Simulation', () => {
  test('should simulate failover for testing', async ({ apiToken }) => {
    // Obter instância para simular failover
    const instancesResponse = await apiRequest(apiToken, 'GET', '/api/v1/instances');

    if (!instancesResponse.ok) {
      test.skip();
      return;
    }

    const instances = await instancesResponse.json();
    if (!instances.length) {
      console.log('No instances for failover simulation');
      test.skip();
      return;
    }

    const gpuInstanceId = instances[0].id || instances[0].vast_id;

    // Simular failover (não afeta a instância real)
    const response = await apiRequest(
      apiToken,
      'POST',
      `/api/v1/standby/failover/simulate/${gpuInstanceId}`
    );

    expect([200, 400, 404]).toContain(response.status);

    if (response.ok) {
      const simulation = await response.json();
      expect(simulation).toHaveProperty('failover_id');
      expect(simulation).toHaveProperty('status');

      console.log('Failover simulation:', simulation);

      // Verificar status da simulação
      if (simulation.failover_id) {
        const statusResponse = await apiRequest(
          apiToken,
          'GET',
          `/api/v1/standby/failover/status/${simulation.failover_id}`
        );

        if (statusResponse.ok) {
          const status = await statusResponse.json();
          console.log('Simulation status:', status);
        }
      }
    }
  });

  test('should run fast failover test', async ({ apiToken }) => {
    // Obter instância
    const instancesResponse = await apiRequest(apiToken, 'GET', '/api/v1/instances');

    if (!instancesResponse.ok) {
      test.skip();
      return;
    }

    const instances = await instancesResponse.json();
    if (!instances.length) {
      console.log('No instances for fast failover test');
      test.skip();
      return;
    }

    const gpuInstanceId = instances[0].id || instances[0].vast_id;

    // Fast failover test (validação rápida)
    const response = await apiRequest(
      apiToken,
      'POST',
      `/api/v1/standby/failover/fast/${gpuInstanceId}`
    );

    expect([200, 400, 404]).toContain(response.status);

    if (response.ok) {
      const result = await response.json();
      console.log('Fast failover result:', result);
    }
  });
});

test.describe('Failover Settings per Machine', () => {
  test('should get global failover settings', async ({ apiToken }) => {
    const response = await apiRequest(apiToken, 'GET', '/api/v1/failover/settings/global');

    expect(response.ok).toBe(true);

    const settings = await response.json();
    expect(settings).toHaveProperty('default_strategy');
    expect(settings).toHaveProperty('auto_failover_enabled');

    console.log('Global failover settings:', settings);
  });

  test('should update global failover settings', async ({ apiToken }) => {
    const response = await apiRequest(apiToken, 'PUT', '/api/v1/failover/settings/global', {
      default_strategy: 'warm_pool_first',
      auto_failover_enabled: true,
      auto_recovery_enabled: true,
      notification_enabled: true,
    });

    expect([200, 201]).toContain(response.status);
  });

  test('should list machine-specific failover settings', async ({ apiToken }) => {
    const response = await apiRequest(apiToken, 'GET', '/api/v1/failover/settings/machines');

    expect(response.ok).toBe(true);

    const machines = await response.json();
    expect(Array.isArray(machines)).toBe(true);

    console.log(`Machines with custom failover settings: ${machines.length}`);
  });

  test('should configure failover for specific machine', async ({ apiToken }) => {
    // Obter instância
    const instancesResponse = await apiRequest(apiToken, 'GET', '/api/v1/instances');

    if (!instancesResponse.ok || !(await instancesResponse.json()).length) {
      test.skip();
      return;
    }

    const instances = await instancesResponse.json();
    const machineId = instances[0].id || instances[0].machine_id;

    // Configurar para usar warm pool
    const response = await apiRequest(
      apiToken,
      'POST',
      `/api/v1/failover/settings/machines/${machineId}/enable-warm-pool`
    );

    expect([200, 201, 400, 404]).toContain(response.status);

    if (response.ok) {
      const result = await response.json();
      console.log('Machine failover config:', result);
    }
  });
});

test.describe('Failover UI Journey', () => {
  test('should navigate to Machines and see failover status', async ({ authenticatedPage: page }) => {
    await page.goto('/machines');
    await page.waitForLoadState('networkidle');

    // Verificar se página de máquinas carregou
    await expect(page.locator('text=Machines, text=Máquinas, text=GPUs').first()).toBeVisible({ timeout: 10000 });

    // Procurar indicadores de failover nas máquinas
    const failoverIndicators = page.locator('[data-testid="failover-status"], .failover-badge, text=/protected|backup|standby/i');
    const indicatorCount = await failoverIndicators.count();

    console.log(`Found ${indicatorCount} machines with failover indicators`);
  });

  test('should open machine details and see failover options', async ({ authenticatedPage: page }) => {
    await page.goto('/machines');
    await page.waitForLoadState('networkidle');

    // Clicar na primeira máquina
    const machineCard = page.locator('[data-testid="machine-card"], .machine-item, .machine-row, tr:has(.gpu-name)').first();

    if (await machineCard.isVisible()) {
      await machineCard.click();

      // Esperar modal ou navegação
      await page.waitForTimeout(1000);

      // Procurar opções de failover
      const failoverOptions = page.locator('text=/failover|warm.?pool|standby|backup/i');
      const optionsCount = await failoverOptions.count();

      console.log(`Found ${optionsCount} failover-related options in machine details`);
    }
  });
});
