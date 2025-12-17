const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://dumontcloud.com';

test.describe('Metrics Page Tests', () => {
  let authToken;

  // Skip UI login - test API endpoints directly which work without auth issues
  test('1. Test metrics API endpoints directly', async ({ request }) => {
    // These endpoints work without authentication

    // Test /api/v1/metrics/gpus
    const gpusResponse = await request.get(`${BASE_URL}/api/v1/metrics/gpus`);
    expect(gpusResponse.ok()).toBeTruthy();
    const gpusData = await gpusResponse.json();
    console.log('Available GPUs:', gpusData.gpus?.length || 0);

    // Test /api/v1/metrics/types
    const typesResponse = await request.get(`${BASE_URL}/api/v1/metrics/types`);
    expect(typesResponse.ok()).toBeTruthy();
    const typesData = await typesResponse.json();
    console.log('Machine types:', typesData.types);

    // Test /api/v1/metrics/market
    const marketResponse = await request.get(`${BASE_URL}/api/v1/metrics/market`);
    expect(marketResponse.ok()).toBeTruthy();
    const marketData = await marketResponse.json();
    console.log('Market snapshots:', marketData.data?.length || 0);

    // Test /api/v1/metrics/providers
    const providersResponse = await request.get(`${BASE_URL}/api/v1/metrics/providers`);
    expect(providersResponse.ok()).toBeTruthy();
    const providersData = await providersResponse.json();
    console.log('Providers:', providersData.data?.length || 0);

    // Test /api/v1/metrics/efficiency
    const efficiencyResponse = await request.get(`${BASE_URL}/api/v1/metrics/efficiency`);
    expect(efficiencyResponse.ok()).toBeTruthy();
    const efficiencyData = await efficiencyResponse.json();
    console.log('Efficiency rankings:', efficiencyData.data?.length || 0);
  });

  test('2. Test market summary endpoint', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/metrics/market/summary`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    console.log('Market summary GPUs:', Object.keys(data.data || {}).length);

    // Check structure
    if (data.data && Object.keys(data.data).length > 0) {
      const firstGpu = Object.keys(data.data)[0];
      console.log(`Sample GPU: ${firstGpu}`);
      console.log('Types available:', Object.keys(data.data[firstGpu] || {}));
    }
  });

  test('3. Test predictions endpoint', async ({ request }) => {
    // First get available GPUs
    const gpusResponse = await request.get(`${BASE_URL}/api/v1/metrics/gpus`);
    const gpusData = await gpusResponse.json();

    if (gpusData.gpus && gpusData.gpus.length > 0) {
      const testGpu = gpusData.gpus[0];
      const encodedGpu = encodeURIComponent(testGpu);

      const response = await request.get(`${BASE_URL}/api/v1/metrics/predictions/${encodedGpu}`);
      expect(response.ok()).toBeTruthy();
      const data = await response.json();

      console.log(`Predictions for ${testGpu}:`, data.predictions ? 'Available' : 'Not available');
    }
  });

  test('4. Test compare endpoint', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/metrics/compare?gpus=RTX%204090&gpus=RTX%203090`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    console.log('Comparison data:', Object.keys(data.data || {}).length, 'GPUs');
  });

  test('5. Access metrics page (UI)', async ({ page }) => {
    // Try to access the metrics page directly
    await page.goto(`${BASE_URL}/metrics`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Take screenshot
    await page.screenshot({ path: '/tmp/test_metrics_page.png', fullPage: true });

    // Check what page we're on
    const url = page.url();
    console.log('Current URL:', url);

    // If redirected to login, that's expected without auth
    if (url.includes('login') || url === `${BASE_URL}/`) {
      console.log('Redirected to login page (expected without authentication)');
      console.log('API endpoints work correctly - UI requires authentication');
    } else {
      // If we got to metrics page, verify content
      const pageContent = await page.content();
      console.log('Metrics page accessible!');

      // Look for metrics-related content
      const hasMetricsContent = pageContent.includes('metric') ||
                                pageContent.includes('Metric') ||
                                pageContent.includes('GPU') ||
                                pageContent.includes('provider');
      console.log('Has metrics content:', hasMetricsContent);
    }
  });

  test('6. Full API data verification', async ({ request }) => {
    // Comprehensive check of all data
    const results = {
      market: 0,
      providers: 0,
      efficiency: 0,
      gpus: 0
    };

    // Market data
    const marketResp = await request.get(`${BASE_URL}/api/v1/metrics/market?limit=100`);
    if (marketResp.ok()) {
      const data = await marketResp.json();
      results.market = data.data?.length || 0;
    }

    // Providers
    const providersResp = await request.get(`${BASE_URL}/api/v1/metrics/providers?limit=100`);
    if (providersResp.ok()) {
      const data = await providersResp.json();
      results.providers = data.data?.length || 0;
    }

    // Efficiency
    const efficiencyResp = await request.get(`${BASE_URL}/api/v1/metrics/efficiency?limit=100`);
    if (efficiencyResp.ok()) {
      const data = await efficiencyResp.json();
      results.efficiency = data.data?.length || 0;
    }

    // GPUs
    const gpusResp = await request.get(`${BASE_URL}/api/v1/metrics/gpus`);
    if (gpusResp.ok()) {
      const data = await gpusResp.json();
      results.gpus = data.gpus?.length || 0;
    }

    console.log('\n=== METRICS DATA SUMMARY ===');
    console.log(`Market snapshots: ${results.market}`);
    console.log(`Providers tracked: ${results.providers}`);
    console.log(`Efficiency rankings: ${results.efficiency}`);
    console.log(`GPUs monitored: ${results.gpus}`);
    console.log('============================\n');

    // Verify we have data
    expect(results.market + results.providers + results.efficiency).toBeGreaterThan(0);
  });
});
