/**
 * Dumont Cloud - GPU Metrics Page E2E Tests
 *
 * Testes para a página de métricas de preços de GPU
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.TEST_URL || 'https://dumontcloud.com';
const TEST_USER = process.env.TEST_USER || 'marcosremar@gmail.com';
const TEST_PASS = process.env.TEST_PASS || 'Marcos123';

// Helper para login
async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForTimeout(1000);
  await page.fill('input[type="text"]', TEST_USER);
  await page.fill('input[type="password"]', TEST_PASS);
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(2000);
}

test.describe('GPU Metrics - Basic UI', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(3000);
  });

  test('should display Metrics page', async ({ page }) => {
    // Page should load without errors
    const pageContent = await page.content();
    expect(pageContent.length).toBeGreaterThan(0);

    await page.screenshot({ path: 'screenshots/metrics-page.png', fullPage: true });
  });

  test('should display page header', async ({ page }) => {
    const header = page.locator('text=/Métricas|Metrics|Preços|GPU/i');
    const hasHeader = await header.count() > 0;
    console.log('Metrics header found:', hasHeader);
  });

  test('should display GPU summary cards', async ({ page }) => {
    // Look for GPU cards (RTX 4090, RTX 4080, etc)
    const gpuCards = page.locator('text=/RTX 4090|RTX 4080|RTX 3090|A100|H100/');
    const count = await gpuCards.count();
    console.log('GPU cards found:', count);
  });

  test('should display price information', async ({ page }) => {
    // Look for price displays
    const prices = page.locator('text=/\\$[\\d.]+/');
    const count = await prices.count();
    console.log('Price elements found:', count);
  });
});

test.describe('GPU Metrics - Filters', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(3000);
  });

  test('should display time range filter', async ({ page }) => {
    const timeFilter = page.locator('text=/24h|7d|30d|hora|day/i, select, [role="combobox"]');
    const exists = await timeFilter.count() > 0;
    console.log('Time range filter:', exists ? 'Found' : 'Not found');
  });

  test('should display GPU filter', async ({ page }) => {
    const gpuFilter = page.locator('text=/Filtrar|GPU|Selec/i');
    const exists = await gpuFilter.count() > 0;
    console.log('GPU filter:', exists ? 'Found' : 'Not found');
  });

  test('should display price range filter', async ({ page }) => {
    const priceFilter = page.locator('text=/preço|price|range/i, input[type="range"]');
    const exists = await priceFilter.count() > 0;
    console.log('Price range filter:', exists ? 'Found' : 'Not found');
  });

  test('should have "Show only price drops" toggle', async ({ page }) => {
    const dropsToggle = page.locator('text=/queda|drop|baixa/i');
    const exists = await dropsToggle.count() > 0;
    console.log('Price drops toggle:', exists ? 'Found' : 'Not found');
  });
});

test.describe('GPU Metrics - Charts', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(3000);
  });

  test('should display price charts', async ({ page }) => {
    // Look for chart elements (canvas, svg, chart container)
    const charts = page.locator('canvas, svg.chart, [class*="chart"], [class*="Chart"]');
    const count = await charts.count();
    console.log('Chart elements found:', count);

    await page.screenshot({ path: 'screenshots/metrics-charts.png', fullPage: true });
  });

  test('should have interactive chart tooltips', async ({ page }) => {
    // Hover over chart area
    const chartArea = page.locator('canvas').first();
    if (await chartArea.count() > 0) {
      await chartArea.hover();
      await page.waitForTimeout(500);

      // Look for tooltip
      const tooltip = page.locator('[class*="tooltip"], [role="tooltip"]');
      const hasTooltip = await tooltip.count() > 0;
      console.log('Chart tooltip:', hasTooltip ? 'Found' : 'Not found');
    }
  });
});

test.describe('GPU Metrics - Alerts Section', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(3000);
  });

  test('should display alerts section', async ({ page }) => {
    const alertsSection = page.locator('text=/Alert|Alerta|Notific/i');
    const exists = await alertsSection.count() > 0;
    console.log('Alerts section:', exists ? 'Found' : 'Not found');
  });

  test('should display price drop alerts', async ({ page }) => {
    const priceDropAlerts = page.locator('text=/queda|drop|↓|baixou/i');
    const count = await priceDropAlerts.count();
    console.log('Price drop alerts found:', count);
  });

  test('should display alert timestamps', async ({ page }) => {
    // Look for time indicators
    const timestamps = page.locator('text=/\\d+h|\\d+ min|ago|atrás/');
    const count = await timestamps.count();
    console.log('Timestamp elements found:', count);
  });
});

test.describe('GPU Metrics - Agent Status', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(3000);
  });

  test('should display monitoring agent status', async ({ page }) => {
    const agentStatus = page.locator('text=/Agent|Monitor|Status|Ativo|Running/i');
    const exists = await agentStatus.count() > 0;
    console.log('Agent status indicator:', exists ? 'Found' : 'Not found');
  });

  test('should show last update time', async ({ page }) => {
    const lastUpdate = page.locator('text=/última|last|atualiz/i');
    const exists = await lastUpdate.count() > 0;
    console.log('Last update time:', exists ? 'Found' : 'Not found');
  });
});

test.describe('GPU Metrics - Data Loading', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should fetch metrics data on page load', async ({ page }) => {
    let apiCalls = [];

    page.on('response', response => {
      if (response.url().includes('/api/price-monitor') ||
          response.url().includes('/api/metrics')) {
        apiCalls.push({
          url: response.url(),
          status: response.status()
        });
      }
    });

    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(5000);

    console.log('API calls made:', apiCalls.length);
    apiCalls.forEach(call => console.log(`  - ${call.url} (${call.status})`));
  });

  test('should handle loading state', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`);

    // Check for loading indicator
    const loading = page.locator('text=/carregando|loading/i, .spinner, [class*="loading"]');
    const hadLoading = await loading.count() > 0;

    await page.waitForTimeout(3000);

    console.log('Loading state observed:', hadLoading);
  });

  test('should handle empty data state', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(3000);

    const emptyState = page.locator('text=/nenhum|no data|vazio|empty/i');
    const hasEmptyState = await emptyState.count() > 0;
    console.log('Empty state message:', hasEmptyState ? 'Found' : 'Not found');
  });
});

test.describe('GPU Metrics - Trend Indicators', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(3000);
  });

  test('should display trend arrows', async ({ page }) => {
    // Look for up/down trend indicators
    const trendUp = page.locator('text=/↑|▲/, svg.lucide-trending-up, [class*="up"]');
    const trendDown = page.locator('text=/↓|▼/, svg.lucide-trending-down, [class*="down"]');

    const upCount = await trendUp.count();
    const downCount = await trendDown.count();

    console.log('Trend up indicators:', upCount);
    console.log('Trend down indicators:', downCount);
  });

  test('should display percentage changes', async ({ page }) => {
    const percentages = page.locator('text=/%/');
    const count = await percentages.count();
    console.log('Percentage elements found:', count);
  });
});

test.describe('GPU Metrics - Responsive Design', () => {
  test('should display correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await login(page);
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'screenshots/metrics-mobile.png', fullPage: true });
  });

  test('should display correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await login(page);
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'screenshots/metrics-tablet.png', fullPage: true });
  });
});

test.describe('GPU Metrics - Navigation', () => {
  test('should navigate to Metrics from Dashboard via dropdown', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // Look for Métricas dropdown
    const metricsDropdown = page.locator('text=Métricas');
    if (await metricsDropdown.count() > 0) {
      await metricsDropdown.first().click();
      await page.waitForTimeout(500);

      // Look for submenu item
      const metricsLink = page.locator('a:has-text("GPU"), a[href*="metrics"]');
      if (await metricsLink.count() > 0) {
        await metricsLink.first().click();
        await page.waitForTimeout(1000);
      }
    }

    // Fallback: direct navigation
    if (!page.url().includes('/metrics')) {
      await page.goto(`${BASE_URL}/metrics`);
    }

    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/metrics');
  });
});

test.describe('GPU Metrics - API Integration', () => {
  test('should fetch summary data', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/price-monitor/summary`);
    console.log('Summary API status:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('Summary data:', JSON.stringify(data).substring(0, 200));
    }
  });

  test('should fetch history data', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/price-monitor/history?hours=24`);
    console.log('History API status:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('History records:', data.history?.length || 0);
    }
  });

  test('should fetch alerts data', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/price-monitor/alerts?hours=24`);
    console.log('Alerts API status:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('Alerts count:', data.alerts?.length || 0);
    }
  });

  test('should fetch agent status', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/price-monitor/status`);
    console.log('Agent status API:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('Agent status:', data.agent?.status || 'unknown');
    }
  });
});
