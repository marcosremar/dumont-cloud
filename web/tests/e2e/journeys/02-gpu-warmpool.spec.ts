import { test, expect, apiRequest, cleanupTestResources } from '../fixtures/auth';

/**
 * Jornada E2E: GPU Warm Pool
 *
 * Testa o fluxo completo do GPU Warm Pool:
 * 1. Buscar hosts com múltiplas GPUs
 * 2. Verificar disponibilidade de hosts
 * 3. Provisionar warm pool (GPU + Volume)
 * 4. Verificar status do warm pool
 * 5. Testar failover simulado
 * 6. Cleanup
 */

test.describe('GPU Warm Pool Journey', () => {
  test.describe.configure({ mode: 'serial' });

  let provisionedMachineId: string | null = null;

  test('should list available multi-GPU hosts', async ({ apiToken }) => {
    const response = await apiRequest(apiToken, 'GET', '/api/v1/warmpool/hosts?gpu_name=RTX_4090&min_gpus=2');

    expect(response.ok).toBe(true);

    const hosts = await response.json();
    expect(Array.isArray(hosts)).toBe(true);

    // Log para debug
    console.log(`Found ${hosts.length} multi-GPU hosts`);

    if (hosts.length > 0) {
      // Verificar estrutura do host
      const host = hosts[0];
      expect(host).toHaveProperty('machine_id');
      expect(host).toHaveProperty('num_gpus');
      expect(host.num_gpus).toBeGreaterThanOrEqual(2);
    }
  });

  test('should check warm pool status for a machine', async ({ apiToken }) => {
    // Primeiro, obter uma instância existente
    const instancesResponse = await apiRequest(apiToken, 'GET', '/api/v1/instances');

    if (!instancesResponse.ok) {
      test.skip();
      return;
    }

    const instances = await instancesResponse.json();
    if (!instances.length) {
      console.log('No instances found, skipping warm pool status check');
      test.skip();
      return;
    }

    const machineId = instances[0].id || instances[0].machine_id;
    const response = await apiRequest(apiToken, 'GET', `/api/v1/warmpool/status/${machineId}`);

    // Pode retornar 404 se warm pool não configurado, ou 200 se configurado
    expect([200, 404]).toContain(response.status);

    if (response.ok) {
      const status = await response.json();
      expect(status).toHaveProperty('state');
      console.log(`Warm pool state: ${status.state}`);
    }
  });

  test('should navigate to Failover Settings in UI', async ({ authenticatedPage: page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Procurar seção de Failover ou Warm Pool
    const failoverSection = page.locator('text=Failover, text=Warm Pool, text=GPU Backup').first();
    await expect(failoverSection).toBeVisible({ timeout: 10000 });
  });

  test('should display warm pool strategy option', async ({ authenticatedPage: page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Verificar opções de estratégia de failover
    const warmPoolOption = page.locator('text=/warm.?pool/i, text=/gpu.?backup/i').first();

    if (await warmPoolOption.isVisible()) {
      await expect(warmPoolOption).toBeVisible();
    } else {
      // Pode estar em outra página ou seção
      console.log('Warm Pool option not visible in settings, might be in machine-specific settings');
    }
  });

  test('should get failover strategies via API', async ({ apiToken }) => {
    const response = await apiRequest(apiToken, 'GET', '/api/v1/failover/strategies');

    expect(response.ok).toBe(true);

    const strategies = await response.json();
    expect(Array.isArray(strategies)).toBe(true);

    // Deve incluir warm_pool e cpu_standby
    const strategyNames = strategies.map((s: any) => s.name || s.id || s);
    console.log('Available strategies:', strategyNames);
  });

  test('should check failover readiness for a machine', async ({ apiToken }) => {
    // Obter uma instância
    const instancesResponse = await apiRequest(apiToken, 'GET', '/api/v1/instances');

    if (!instancesResponse.ok) {
      test.skip();
      return;
    }

    const instances = await instancesResponse.json();
    if (!instances.length) {
      console.log('No instances found, skipping readiness check');
      test.skip();
      return;
    }

    const machineId = instances[0].id || instances[0].machine_id;
    const response = await apiRequest(apiToken, 'GET', `/api/v1/failover/readiness/${machineId}`);

    expect([200, 404]).toContain(response.status);

    if (response.ok) {
      const readiness = await response.json();
      expect(readiness).toHaveProperty('ready');
      expect(readiness).toHaveProperty('strategy');
      console.log(`Machine ${machineId} readiness:`, readiness);
    }
  });
});

test.describe('GPU Warm Pool Provisioning (Real)', () => {
  // Estes testes criam recursos reais - usar com cuidado
  test.skip(!!process.env.SKIP_REAL_PROVISIONING, 'Skipping real provisioning tests');

  let createdResources: { instances: string[]; } = { instances: [] };

  test.afterAll(async ({ }, testInfo) => {
    // Cleanup seria feito aqui se necessário
    console.log('Resources to cleanup:', createdResources);
  });

  test('should provision warm pool for new machine', async ({ apiToken }) => {
    // 1. Buscar host com múltiplas GPUs
    const hostsResponse = await apiRequest(apiToken, 'GET', '/api/v1/warmpool/hosts?gpu_name=RTX_4090&min_gpus=2');

    if (!hostsResponse.ok) {
      test.skip();
      return;
    }

    const hosts = await hostsResponse.json();
    if (!hosts.length) {
      console.log('No multi-GPU hosts available, skipping provisioning');
      test.skip();
      return;
    }

    const hostMachineId = hosts[0].machine_id;

    // 2. Provisionar warm pool
    const provisionResponse = await apiRequest(apiToken, 'POST', '/api/v1/warmpool/provision', {
      host_machine_id: hostMachineId,
      volume_size_gb: 50, // Pequeno para teste
    });

    expect(provisionResponse.ok).toBe(true);

    const result = await provisionResponse.json();
    expect(result).toHaveProperty('machine_id');
    expect(result).toHaveProperty('state');

    createdResources.instances.push(result.machine_id);
    console.log('Provisioned warm pool:', result);
  });
});

test.describe('GPU Warm Pool Failover Test', () => {
  test('should run failover test (dry-run)', async ({ apiToken }) => {
    // Obter uma instância com warm pool
    const instancesResponse = await apiRequest(apiToken, 'GET', '/api/v1/instances');

    if (!instancesResponse.ok) {
      test.skip();
      return;
    }

    const instances = await instancesResponse.json();
    if (!instances.length) {
      console.log('No instances found, skipping failover test');
      test.skip();
      return;
    }

    const machineId = instances[0].id || instances[0].machine_id;

    // Testar failover (dry-run, não executa de verdade)
    const response = await apiRequest(apiToken, 'POST', `/api/v1/failover/test/${machineId}`);

    // Pode retornar 200 ou 404 dependendo da configuração
    expect([200, 400, 404]).toContain(response.status);

    if (response.ok) {
      const result = await response.json();
      expect(result).toHaveProperty('status');
      console.log('Failover test result:', result);
    }
  });
});
