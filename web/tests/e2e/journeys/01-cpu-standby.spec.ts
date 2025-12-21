import { test, expect, apiRequest, cleanupTestResources } from '../fixtures/auth';

/**
 * Jornada E2E: CPU Standby Configuration
 *
 * Testa o fluxo completo de configuração do CPU Standby:
 * 1. Navegar para Settings
 * 2. Configurar CPU Standby (zona, tipo de máquina, disco)
 * 3. Habilitar auto-failover
 * 4. Verificar estimativa de custo
 * 5. Salvar configuração
 * 6. Verificar status ativo
 */

test.describe('CPU Standby Journey', () => {
  test.describe.configure({ mode: 'serial' });

  test('should navigate to Settings and find Standby config', async ({ authenticatedPage: page }) => {
    // Navegar para Settings
    await page.click('text=Settings, a[href*="settings"], button:has-text("Configurações")');
    await page.waitForURL(/settings/);

    // Verificar que a seção de Standby existe
    await expect(page.locator('text=CPU Standby, text=Standby, text=Failover')).toBeVisible({ timeout: 10000 });
  });

  test('should configure CPU Standby settings', async ({ authenticatedPage: page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Encontrar seção de Standby
    const standbySection = page.locator('text=CPU Standby').first().locator('..').locator('..');

    // Habilitar Auto-Standby
    const enableToggle = page.locator('text=Habilitar Auto-Standby, text=Enable').first();
    if (await enableToggle.isVisible()) {
      await enableToggle.click();
    }

    // Selecionar zona GCP
    const zoneSelect = page.locator('select:near(:text("Zona"))').first();
    if (await zoneSelect.isVisible()) {
      await zoneSelect.selectOption('europe-west1-b');
    }

    // Selecionar tipo de máquina
    const machineSelect = page.locator('select:near(:text("Máquina"), select:near(:text("Machine")))').first();
    if (await machineSelect.isVisible()) {
      await machineSelect.selectOption('e2-standard-4');
    }

    // Configurar tamanho do disco
    const diskInput = page.locator('input[type="number"]:near(:text("Disco"), input:near(:text("Disk")))').first();
    if (await diskInput.isVisible()) {
      await diskInput.fill('100');
    }

    // Verificar estimativa de custo
    await expect(page.locator('text=/\\$[0-9]+.*mês|month/')).toBeVisible({ timeout: 5000 });

    // Salvar configuração
    await page.click('button:has-text("Salvar"), button:has-text("Save")');

    // Verificar sucesso
    await expect(page.locator('text=Salvo, text=Saved, text=sucesso, text=success')).toBeVisible({ timeout: 5000 });
  });

  test('should verify Standby status via API', async ({ apiToken }) => {
    const response = await apiRequest(apiToken, 'GET', '/api/v1/standby/status');
    expect(response.ok).toBe(true);

    const status = await response.json();
    expect(status).toHaveProperty('auto_standby_enabled');
  });

  test('should show pricing estimation', async ({ authenticatedPage: page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Verificar que mostra estimativa de preço
    const pricingVisible = await page.locator('text=/\\$[0-9]+/').count() > 0;
    expect(pricingVisible).toBe(true);
  });

  test('should configure auto-failover and auto-recovery', async ({ authenticatedPage: page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Habilitar auto-failover
    const failoverToggle = page.locator('text=Auto-Failover').first().locator('..').locator('input[type="checkbox"]');
    if (await failoverToggle.isVisible()) {
      await failoverToggle.check();
    }

    // Habilitar auto-recovery
    const recoveryToggle = page.locator('text=Auto-Recovery').first().locator('..').locator('input[type="checkbox"]');
    if (await recoveryToggle.isVisible()) {
      await recoveryToggle.check();
    }

    // Salvar
    await page.click('button:has-text("Salvar"), button:has-text("Save")');
    await expect(page.locator('text=Salvo, text=Saved, text=sucesso')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('CPU Standby API Tests', () => {
  test('should get standby pricing', async ({ apiToken }) => {
    const response = await apiRequest(
      apiToken,
      'GET',
      '/api/v1/standby/pricing?machine_type=e2-standard-4&disk_gb=100&spot=true'
    );
    expect(response.ok).toBe(true);

    const pricing = await response.json();
    expect(pricing).toHaveProperty('estimated_monthly_usd');
    expect(pricing.estimated_monthly_usd).toBeGreaterThan(0);
  });

  test('should list standby associations', async ({ apiToken }) => {
    const response = await apiRequest(apiToken, 'GET', '/api/v1/standby/associations');
    expect(response.ok).toBe(true);

    const associations = await response.json();
    expect(Array.isArray(associations)).toBe(true);
  });

  test('should configure standby via API', async ({ apiToken }) => {
    const config = {
      enabled: true,
      gcp_zone: 'europe-west1-b',
      gcp_machine_type: 'e2-standard-4',
      gcp_disk_size: 100,
      gcp_spot: true,
      sync_interval: 30,
      auto_failover: true,
      auto_recovery: true,
    };

    const response = await apiRequest(apiToken, 'POST', '/api/v1/standby/configure', config);
    expect(response.ok).toBe(true);
  });
});
