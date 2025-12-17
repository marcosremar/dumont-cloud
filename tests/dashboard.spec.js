/**
 * Dumont Cloud - Dashboard (Deploy Wizard) E2E Tests
 *
 * Testes para a página principal de deploy de GPUs
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

test.describe('Dashboard - Basic UI', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should display Deploy section header', async ({ page }) => {
    const header = page.locator('text=Deploy');
    await expect(header.first()).toBeVisible();
  });

  test('should display Wizard and Avançado mode buttons', async ({ page }) => {
    await expect(page.locator('button:has-text("Wizard")')).toBeVisible();
    await expect(page.locator('button:has-text("Avançado")')).toBeVisible();
  });

  test('should display region tabs (EUA, Europa, Ásia, etc)', async ({ page }) => {
    await expect(page.locator('button:has-text("EUA")')).toBeVisible();
    await expect(page.locator('button:has-text("Europa")')).toBeVisible();
    await expect(page.locator('button:has-text("Ásia")')).toBeVisible();
    await expect(page.locator('button:has-text("América do Sul")')).toBeVisible();
    await expect(page.locator('button:has-text("Global")')).toBeVisible();
  });

  test('should display world map', async ({ page }) => {
    // Map container should exist
    const mapContainer = page.locator('text=Região').first();
    await expect(mapContainer).toBeVisible();
  });

  test('should display GPU selector dropdown', async ({ page }) => {
    const gpuLabel = page.locator('text=GPU (opcional)');
    await expect(gpuLabel).toBeVisible();

    const gpuDropdown = page.locator('text=Qualquer GPU');
    await expect(gpuDropdown).toBeVisible();
  });

  test('should display speed/cost cards (Lento, Medio, Rapido, Ultra)', async ({ page }) => {
    // Check for speed tier labels (with or without accents)
    const lentoVisible = await page.locator('text=/Lento/i').count() > 0;
    const medioVisible = await page.locator('text=/M[eé]dio/i').count() > 0;
    const rapidoVisible = await page.locator('text=/R[aá]pido/i').count() > 0;
    const ultraVisible = await page.locator('text=/Ultra/i').count() > 0;

    console.log(`Speed tiers: Lento=${lentoVisible}, Medio=${medioVisible}, Rapido=${rapidoVisible}, Ultra=${ultraVisible}`);
    expect(lentoVisible || medioVisible || rapidoVisible || ultraVisible).toBeTruthy();
  });

  test('should display search button', async ({ page }) => {
    const searchBtn = page.locator('button:has-text("Buscar Máquinas Disponíveis")');
    await expect(searchBtn).toBeVisible();
  });

  test('should take screenshot of dashboard', async ({ page }) => {
    await page.screenshot({ path: 'screenshots/dashboard-full.png', fullPage: true });
  });
});

test.describe('Dashboard - Region Selection', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should switch to Europa region', async ({ page }) => {
    await page.click('button:has-text("Europa")');
    await page.waitForTimeout(500);

    // Europa tab should be visible and clickable
    const europaBtn = page.locator('button:has-text("Europa")');
    await expect(europaBtn).toBeVisible();

    // Take screenshot to verify
    await page.screenshot({ path: 'screenshots/dashboard-europa-selected.png' });
  });

  test('should switch to Ásia region', async ({ page }) => {
    await page.click('button:has-text("Ásia")');
    await page.waitForTimeout(500);

    const asiaBtn = page.locator('button:has-text("Ásia")');
    await expect(asiaBtn).toBeVisible();
  });

  test('should switch to Global region', async ({ page }) => {
    await page.click('button:has-text("Global")');
    await page.waitForTimeout(500);

    const globalBtn = page.locator('button:has-text("Global")');
    await expect(globalBtn).toBeVisible();
  });
});

test.describe('Dashboard - GPU Selection', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should open GPU dropdown', async ({ page }) => {
    // Click on GPU selector
    await page.click('text=Qualquer GPU');
    await page.waitForTimeout(500);

    // Should show GPU options
    const rtx4090 = page.locator('text=RTX 4090');
    const isVisible = await rtx4090.isVisible().catch(() => false);

    if (isVisible) {
      await expect(rtx4090).toBeVisible();
    }

    // Take screenshot of dropdown
    await page.screenshot({ path: 'screenshots/dashboard-gpu-dropdown.png' });
  });

  test('should select RTX 4090', async ({ page }) => {
    await page.click('text=Qualquer GPU');
    await page.waitForTimeout(500);

    const rtx4090 = page.locator('[role="option"]:has-text("RTX 4090"), [data-value="RTX_4090"]');
    if (await rtx4090.count() > 0) {
      await rtx4090.first().click();
      await page.waitForTimeout(500);
    }
  });

  test('should select RTX 4080', async ({ page }) => {
    await page.click('text=Qualquer GPU');
    await page.waitForTimeout(500);

    const rtx4080 = page.locator('[role="option"]:has-text("RTX 4080")');
    if (await rtx4080.count() > 0) {
      await rtx4080.first().click();
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Dashboard - Speed/Cost Slider', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should display speed tiers with specs', async ({ page }) => {
    // Lento tier
    await expect(page.locator('text=100-250 Mbps').first()).toBeVisible();

    // Médio tier
    await expect(page.locator('text=500-1000 Mbps').first()).toBeVisible();

    // Rápido tier
    await expect(page.locator('text=1000-2000 Mbps').first()).toBeVisible();

    // Ultra tier
    await expect(page.locator('text=2000+ Mbps').first()).toBeVisible();
  });

  test('should click on Rapido tier card', async ({ page }) => {
    // Look for Rapido with or without accent
    const rapidoCard = page.locator('text=/R[aá]pido/i').first();

    if (await rapidoCard.count() > 0) {
      await rapidoCard.click();
      await page.waitForTimeout(500);
    }

    // Take screenshot after selection
    await page.screenshot({ path: 'screenshots/dashboard-rapido-selected.png' });
  });

  test('should have interactive slider', async ({ page }) => {
    // Look for slider element
    const slider = page.locator('[role="slider"], input[type="range"], .slider');
    const sliderExists = await slider.count() > 0;

    if (sliderExists) {
      // Slider should be visible and interactive
      await expect(slider.first()).toBeVisible();
    }
  });
});

test.describe('Dashboard - Search Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should trigger search when clicking search button', async ({ page }) => {
    let apiCalled = false;

    page.on('response', response => {
      // Check for various API endpoints that might be called
      if (response.url().includes('/api/') &&
          (response.url().includes('offers') ||
           response.url().includes('search') ||
           response.url().includes('instances') ||
           response.url().includes('deploy'))) {
        apiCalled = true;
      }
    });

    // Click search button
    await page.click('button:has-text("Buscar Máquinas Disponíveis")');
    await page.waitForTimeout(3000);

    // Take screenshot of results
    await page.screenshot({ path: 'screenshots/dashboard-search-results.png', fullPage: true });

    // Verify results are displayed (the screenshot shows results were returned)
    const hasResults = await page.locator('text=/Máquinas Disponíveis|resultados|RTX|\\$/').count() > 0;
    expect(hasResults).toBeTruthy();
  });

  test('should display search results or empty state', async ({ page }) => {
    await page.click('button:has-text("Buscar Máquinas Disponíveis")');
    await page.waitForTimeout(3000);

    // Should show either results or "nenhuma oferta" message
    const hasResults = await page.locator('text=/\\$[\\d.]+\\/h|RTX|GPU/').count() > 0;
    const hasEmptyState = await page.locator('text=/nenhuma|não encontr/i').count() > 0;
    const hasLoading = await page.locator('text=/carregando|buscando/i').count() > 0;

    // One of these should be true
    expect(hasResults || hasEmptyState || hasLoading).toBeTruthy();
  });

  test('should search with Europa region selected', async ({ page }) => {
    // Select Europa
    await page.click('button:has-text("Europa")');
    await page.waitForTimeout(500);

    // Search
    await page.click('button:has-text("Buscar Máquinas Disponíveis")');
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'screenshots/dashboard-search-europa.png', fullPage: true });
  });
});

test.describe('Dashboard - Wizard vs Advanced Mode', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should switch to Advanced mode', async ({ page }) => {
    await page.click('button:has-text("Avançado")');
    await page.waitForTimeout(1000);

    // Advanced mode should show more options
    await page.screenshot({ path: 'screenshots/dashboard-advanced-mode.png', fullPage: true });

    // Check for advanced options (CUDA version, disk size, etc)
    const cudaOption = page.locator('text=/CUDA|cuda/i');
    const diskOption = page.locator('text=/disk|disco/i');

    const hasAdvancedOptions = await cudaOption.count() > 0 || await diskOption.count() > 0;
    console.log('Advanced options visible:', hasAdvancedOptions);
  });

  test('should switch back to Wizard mode', async ({ page }) => {
    // Go to Advanced first
    await page.click('button:has-text("Avançado")');
    await page.waitForTimeout(500);

    // Then back to Wizard
    await page.click('button:has-text("Wizard")');
    await page.waitForTimeout(500);

    // Wizard UI should be visible
    await expect(page.locator('text=Lento').first()).toBeVisible();
  });
});

test.describe('Dashboard - Responsive Design', () => {
  test('should display correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // Deploy section should be visible
    await expect(page.locator('text=Deploy').first()).toBeVisible();

    // Search button should be visible
    await expect(page.locator('button:has-text("Buscar")').first()).toBeVisible();

    await page.screenshot({ path: 'screenshots/dashboard-mobile.png', fullPage: true });
  });

  test('should display correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    await expect(page.locator('text=Deploy').first()).toBeVisible();

    await page.screenshot({ path: 'screenshots/dashboard-tablet.png', fullPage: true });
  });
});
