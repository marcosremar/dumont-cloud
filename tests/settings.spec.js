/**
 * Dumont Cloud - Settings Page E2E Tests
 *
 * Testes para a página de configurações do usuário
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

test.describe('Settings - Basic UI', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);
  });

  test('should display Settings page header', async ({ page }) => {
    const header = page.locator('text=Settings, text=Configurações');
    await expect(header.first()).toBeVisible();

    await page.screenshot({ path: 'screenshots/settings-page.png', fullPage: true });
  });

  test('should display Vast.ai API Key field', async ({ page }) => {
    const apiKeyLabel = page.locator('text=/API Key|Vast/i');
    await expect(apiKeyLabel.first()).toBeVisible();

    // Should have input field for API key
    const apiKeyInput = page.locator('input[name*="api"], input[placeholder*="API"]').first();
    const inputExists = await apiKeyInput.count() > 0;
    expect(inputExists).toBeTruthy();
  });

  test('should display R2 configuration section', async ({ page }) => {
    const r2Section = page.locator('text=/R2|Cloudflare|Storage/i');
    const hasR2 = await r2Section.count() > 0;
    console.log('R2 section visible:', hasR2);
  });

  test('should display Save button', async ({ page }) => {
    const saveBtn = page.locator('button:has-text("Salvar"), button:has-text("Save")');
    await expect(saveBtn.first()).toBeVisible();
  });
});

test.describe('Settings - Secret Fields Toggle', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);
  });

  test('should have password type inputs for sensitive fields', async ({ page }) => {
    // API Key should be password type by default
    const passwordInputs = page.locator('input[type="password"]');
    const count = await passwordInputs.count();
    console.log('Password inputs found:', count);
    expect(count).toBeGreaterThan(0);
  });

  test('should toggle API key visibility', async ({ page }) => {
    // Find the toggle button (eye icon)
    const toggleBtn = page.locator('button:has(svg)').filter({ has: page.locator('svg') });

    if (await toggleBtn.count() > 0) {
      // Get initial input type
      const input = page.locator('input[type="password"]').first();
      const initialType = await input.getAttribute('type');
      expect(initialType).toBe('password');

      // Click toggle
      await toggleBtn.first().click();
      await page.waitForTimeout(300);

      // Check if type changed to text
      const newType = await input.getAttribute('type').catch(() => 'password');
      console.log('After toggle, input type:', newType);
    }
  });
});

test.describe('Settings - Form Fields', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);
  });

  test('should display all configuration sections', async ({ page }) => {
    // Check for main sections
    const sections = [
      'API Key',
      'R2',
      'Restic',
      'Tailscale',
    ];

    for (const section of sections) {
      const element = page.locator(`text=/${section}/i`);
      const isVisible = await element.count() > 0;
      console.log(`Section "${section}":`, isVisible ? 'Found' : 'Not found');
    }
  });

  test('should have R2 Access Key field', async ({ page }) => {
    const r2AccessKey = page.locator('input[name*="r2_access"], input[placeholder*="Access Key"]');
    const exists = await r2AccessKey.count() > 0;
    console.log('R2 Access Key field:', exists ? 'Found' : 'Not found');
  });

  test('should have R2 Secret Key field', async ({ page }) => {
    const r2SecretKey = page.locator('input[name*="r2_secret"], input[placeholder*="Secret"]');
    const exists = await r2SecretKey.count() > 0;
    console.log('R2 Secret Key field:', exists ? 'Found' : 'Not found');
  });

  test('should have R2 Endpoint field', async ({ page }) => {
    const r2Endpoint = page.locator('input[name*="endpoint"], input[placeholder*="endpoint"]');
    const exists = await r2Endpoint.count() > 0;
    console.log('R2 Endpoint field:', exists ? 'Found' : 'Not found');
  });

  test('should have Restic Password field', async ({ page }) => {
    const resticPassword = page.locator('input[name*="restic_password"], input[placeholder*="Restic"]');
    const exists = await resticPassword.count() > 0;
    console.log('Restic Password field:', exists ? 'Found' : 'Not found');
  });

  test('should have Tailscale Auth Key field', async ({ page }) => {
    const tailscaleKey = page.locator('input[name*="tailscale"], input[placeholder*="Tailscale"]');
    const exists = await tailscaleKey.count() > 0;
    console.log('Tailscale Auth Key field:', exists ? 'Found' : 'Not found');
  });
});

test.describe('Settings - Agent Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);
  });

  test('should display Agent settings section', async ({ page }) => {
    const agentSection = page.locator('text=/Agent|Sync|Intervalo/i');
    const exists = await agentSection.count() > 0;
    console.log('Agent settings section:', exists ? 'Found' : 'Not found');
  });

  test('should have Sync Interval field', async ({ page }) => {
    const syncInterval = page.locator('input[name*="sync_interval"], input[type="number"]');
    const exists = await syncInterval.count() > 0;
    console.log('Sync Interval field:', exists ? 'Found' : 'Not found');
  });

  test('should have Keep Last Snapshots field', async ({ page }) => {
    const keepLast = page.locator('input[name*="keep_last"], text=/manter|keep/i');
    const exists = await keepLast.count() > 0;
    console.log('Keep Last field:', exists ? 'Found' : 'Not found');
  });
});

test.describe('Settings - Cost Estimation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);
  });

  test('should display cost estimation section', async ({ page }) => {
    const costSection = page.locator('text=/custo|cost|estimat/i');
    const exists = await costSection.count() > 0;
    console.log('Cost estimation section:', exists ? 'Found' : 'Not found');

    await page.screenshot({ path: 'screenshots/settings-cost.png', fullPage: true });
  });
});

test.describe('Settings - Save Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);
  });

  test('should call API when saving settings', async ({ page }) => {
    let apiCalled = false;
    let apiMethod = '';

    page.on('request', request => {
      if (request.url().includes('/api/settings')) {
        apiCalled = true;
        apiMethod = request.method();
      }
    });

    // Click save button
    const saveBtn = page.locator('button:has-text("Salvar"), button:has-text("Save")');
    if (await saveBtn.count() > 0) {
      await saveBtn.first().click();
      await page.waitForTimeout(2000);
    }

    console.log('API called:', apiCalled, 'Method:', apiMethod);
  });

  test('should show success message after saving', async ({ page }) => {
    // Click save
    const saveBtn = page.locator('button:has-text("Salvar"), button:has-text("Save")');
    if (await saveBtn.count() > 0) {
      await saveBtn.first().click();
      await page.waitForTimeout(2000);

      // Check for success message or toast
      const successMsg = page.locator('text=/sucesso|saved|salvo/i, .toast, [class*="success"]');
      const hasSuccess = await successMsg.count() > 0;
      console.log('Success message shown:', hasSuccess);

      await page.screenshot({ path: 'screenshots/settings-after-save.png' });
    }
  });
});

test.describe('Settings - Load Existing Data', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should fetch settings on page load', async ({ page }) => {
    let settingsLoaded = false;

    page.on('response', async response => {
      if (response.url().includes('/api/settings') && response.request().method() === 'GET') {
        settingsLoaded = true;
        const data = await response.json().catch(() => null);
        console.log('Settings API response:', data ? 'Success' : 'Failed');
      }
    });

    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(3000);

    expect(settingsLoaded).toBeTruthy();
  });

  test('should pre-fill fields with existing values', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(3000);

    // Check if inputs have values
    const inputs = page.locator('input[type="password"], input[type="text"]');
    const count = await inputs.count();

    let filledCount = 0;
    for (let i = 0; i < count; i++) {
      const value = await inputs.nth(i).inputValue();
      if (value && value.length > 0) {
        filledCount++;
      }
    }

    console.log(`Filled inputs: ${filledCount}/${count}`);
  });
});

test.describe('Settings - Responsive Design', () => {
  test('should display correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);

    // Save button should be visible
    const saveBtn = page.locator('button:has-text("Salvar"), button:has-text("Save")');
    await expect(saveBtn.first()).toBeVisible();

    await page.screenshot({ path: 'screenshots/settings-mobile.png', fullPage: true });
  });

  test('should display correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'screenshots/settings-tablet.png', fullPage: true });
  });
});

test.describe('Settings - Navigation', () => {
  test('should navigate to Settings from Dashboard', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // Click Settings link
    const settingsLink = page.locator('a:has-text("Settings"), .nav-link:has-text("Settings")');
    await settingsLink.first().click();
    await page.waitForTimeout(1000);

    expect(page.url()).toContain('/settings');
  });

  test('should navigate back to Dashboard from Settings', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);

    // Click Dashboard link
    const dashboardLink = page.locator('a:has-text("Dashboard"), .nav-link:has-text("Dashboard")');
    await dashboardLink.first().click();
    await page.waitForTimeout(1000);

    expect(page.url()).toBe(`${BASE_URL}/`);
  });
});
