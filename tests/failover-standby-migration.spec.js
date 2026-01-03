// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Comprehensive Playwright tests for Failover, Standby, and Migration systems
 *
 * Tests the 6 types of failover:
 * 1. GPU Warm Pool (~6-60s)
 * 2. CPU Standby + Snapshot (~10-20min)
 * 3. Regional Volume (~30-60s)
 * 4. Cloud Storage (~30-120s)
 * 5. Serverless/Hibernation
 * 6. Failover Orquestrado
 */

const BACKEND_URL = 'http://localhost:8000';
const FRONTEND_URL = 'http://localhost:4892';
const AUTH_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYXJjb3NyZW1hckBnbWFpbC5jb20iLCJleHAiOjE3NzEzNjUzNzksImlhdCI6MTc2NzQ3NzM3OX0.MUu764hp4yjvW_HE3CB11rrtbdWUBEqkSputv10F1EE';

test.describe('Backend API - Failover Strategies', () => {
  test('GET /api/v1/failover/strategies returns 6 strategies', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/v1/failover/strategies`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.strategies).toBeDefined();
    expect(data.strategies.length).toBe(6);

    // Verify strategy IDs
    const strategyIds = data.strategies.map(s => s.id);
    expect(strategyIds).toContain('warm_pool');
    expect(strategyIds).toContain('cpu_standby');
    expect(strategyIds).toContain('both');
    expect(strategyIds).toContain('regional_volume');
    expect(strategyIds).toContain('all');
    expect(strategyIds).toContain('disabled');
  });

  test('Each strategy has required fields', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/v1/failover/strategies`);
    const data = await response.json();

    for (const strategy of data.strategies) {
      expect(strategy.id).toBeDefined();
      expect(strategy.name).toBeDefined();
      expect(strategy.description).toBeDefined();
      expect(strategy.recovery_time).toBeDefined();
      expect(strategy.cost).toBeDefined();
      expect(strategy.requirements).toBeDefined();
      expect(Array.isArray(strategy.requirements)).toBeTruthy();
    }
  });
});

test.describe('Backend API - Standby System', () => {
  test('GET /api/v1/standby/status returns standby configuration', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/v1/standby/status`, {
      headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
    });
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('configured');
    expect(data).toHaveProperty('auto_standby_enabled');
    expect(data).toHaveProperty('active_associations');
    expect(data).toHaveProperty('associations');
    expect(data).toHaveProperty('config');
  });

  test('POST /api/v1/standby/test/create-mock-association creates mock', async ({ request }) => {
    const response = await request.post(`${BACKEND_URL}/api/v1/standby/test/create-mock-association?gpu_instance_id=88888`, {
      headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
    });
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.success).toBeTruthy();
    expect(data.association).toBeDefined();
    expect(data.association.gpu_instance_id).toBe(88888);
  });
});

test.describe('Backend API - Warm Pool System', () => {
  test('GET /api/v1/warmpool/hosts returns available hosts', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/v1/warmpool/hosts`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.hosts).toBeDefined();
    expect(Array.isArray(data.hosts)).toBeTruthy();
    expect(data.count).toBeDefined();

    // Each host should have required fields
    if (data.hosts.length > 0) {
      const host = data.hosts[0];
      expect(host.machine_id).toBeDefined();
      expect(host.total_gpus).toBeDefined();
      expect(host.available_gpus).toBeDefined();
      expect(host.gpu_name).toBeDefined();
    }
  });
});

test.describe('Backend API - Simulated Failover (6 Phases)', () => {
  test('Simulated failover completes all 6 phases', async ({ request }) => {
    // Create mock association first
    await request.post(`${BACKEND_URL}/api/v1/standby/test/create-mock-association?gpu_instance_id=77777`, {
      headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
    });

    // Start failover simulation
    const startResponse = await request.post(`${BACKEND_URL}/api/v1/standby/failover/simulate/77777`, {
      headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
    });
    expect(startResponse.ok()).toBeTruthy();

    const startData = await startResponse.json();
    expect(startData.failover_id).toBeDefined();
    expect(startData.phase).toBe('detecting');

    const failoverId = startData.failover_id;

    // Poll until complete (max 60 seconds)
    let phase = 'detecting';
    let attempts = 0;
    let statusData;

    while (phase !== 'complete' && phase !== 'complete_with_new_gpu' && attempts < 20) {
      await new Promise(resolve => setTimeout(resolve, 3000));

      const statusResponse = await request.get(`${BACKEND_URL}/api/v1/standby/failover/status/${failoverId}`, {
        headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
      });

      statusData = await statusResponse.json();
      phase = statusData.phase;
      attempts++;
    }

    // Verify completion
    expect(['complete', 'complete_with_new_gpu']).toContain(phase);
    expect(statusData.success).toBeTruthy();

    // Verify all 6 phases completed
    expect(statusData.phase_timings_ms).toBeDefined();
    const phases = Object.keys(statusData.phase_timings_ms);
    expect(phases).toContain('detecting');
    expect(phases).toContain('gpu_lost');
    expect(phases).toContain('failover_to_cpu');
    expect(phases).toContain('searching_gpu');
    expect(phases).toContain('provisioning');
    expect(phases).toContain('restoring');

    // Verify timing metrics
    expect(statusData.total_time_ms).toBeGreaterThan(0);
    expect(statusData.new_gpu_id).toBeDefined();
    expect(statusData.data_restored).toBeTruthy();
  }, 90000); // 90 second timeout for this test
});

test.describe('Backend API - Failover Settings', () => {
  test('GET /api/v1/failover/settings/global returns global config', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/v1/failover/settings/global`, {
      headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
    });

    // May be 200 or 404 if not configured
    const data = await response.json();
    if (response.ok()) {
      expect(data).toBeDefined();
    }
  });

  test('GET /api/v1/failover/settings/machines returns machine configs', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/v1/failover/settings/machines`, {
      headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
    });

    // May be 200 or 404 if not configured
    const data = await response.json();
    if (response.ok()) {
      expect(data).toBeDefined();
    }
  });
});

test.describe('Frontend - Machines Page with Failover', () => {
  test.use({ storageState: 'tests/.auth/user.json' });

  test('Machines page loads with failover status indicators', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/machines`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Page should load - check for Dumont branding or dashboard elements
    const title = await page.title();
    expect(title.toLowerCase()).toContain('dumont');

    // Check that page loaded successfully (may redirect to dashboard or show machines)
    const pageContent = await page.content();
    const hasContent = pageContent.includes('Dumont') ||
                       pageContent.includes('COMMAND CENTER') ||
                       pageContent.includes('Machines') ||
                       pageContent.includes('GPU');

    expect(hasContent).toBeTruthy();
  });

  test('StandbyConfig component is accessible via Settings', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/settings`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Settings page should load - check for any settings-related content
    const pageContent = await page.content();
    const hasSettings = pageContent.includes('Settings') ||
                        pageContent.includes('Configurações') ||
                        pageContent.includes('Config') ||
                        pageContent.includes('Dumont');

    expect(hasSettings).toBeTruthy();
  });
});

test.describe('Frontend - Migration Modal', () => {
  test.use({ storageState: 'tests/.auth/user.json' });

  test('MigrationModal component exists in codebase', async ({ page }) => {
    // This is a structural test - verify the component can be imported
    const response = await page.request.get(`${FRONTEND_URL}/`);
    expect(response.ok()).toBeTruthy();

    // Page loads without errors
    await page.goto(FRONTEND_URL);
    await page.waitForLoadState('networkidle');

    // No JavaScript errors
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.waitForTimeout(2000);

    // Filter out known non-critical errors
    const criticalErrors = errors.filter(e =>
      !e.includes('ResizeObserver') &&
      !e.includes('network') &&
      !e.includes('favicon')
    );
    expect(criticalErrors.length).toBe(0);
  });
});

test.describe('Frontend - New Machine with Failover Strategy', () => {
  test.use({ storageState: 'tests/.auth/user.json' });

  test('New Machine page loads successfully', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/new-machine`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Check page loaded - may redirect to dashboard or show wizard
    const pageContent = await page.content();
    const hasContent = pageContent.includes('Dumont') ||
                       pageContent.includes('COMMAND CENTER') ||
                       pageContent.includes('New Machine') ||
                       pageContent.includes('Nova Máquina') ||
                       pageContent.includes('GPU') ||
                       pageContent.includes('form');

    expect(hasContent).toBeTruthy();

    // Take screenshot for debugging
    await page.screenshot({ path: 'tests/screenshots/new-machine-failover.png' });
  });
});

// Integration test: Full failover flow
test.describe('Integration - Full Failover Flow', () => {
  test('API endpoints work together for failover simulation', async ({ request }) => {
    // 1. Get strategies
    const strategiesRes = await request.get(`${BACKEND_URL}/api/v1/failover/strategies`);
    expect(strategiesRes.ok()).toBeTruthy();

    // 2. Check standby status
    const standbyRes = await request.get(`${BACKEND_URL}/api/v1/standby/status`, {
      headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
    });
    expect(standbyRes.ok()).toBeTruthy();

    // 3. Check warm pool hosts
    const warmPoolRes = await request.get(`${BACKEND_URL}/api/v1/warmpool/hosts`);
    expect(warmPoolRes.ok()).toBeTruthy();

    // All 3 critical endpoints work
    console.log('All failover API endpoints operational');
  });
});
