const { test, expect } = require('@playwright/test');

test.use({ storageState: { cookies: [], origins: [] } });

test('debug GPU loading', async ({ page }) => {
  const logs = [];
  const networkCalls = [];

  // Capture console
  page.on('console', msg => {
    logs.push(`[${msg.type()}] ${msg.text()}`);
  });

  // Capture network
  page.on('request', req => {
    if (req.url().includes('/api/')) {
      networkCalls.push(`REQ: ${req.method()} ${req.url()}`);
    }
  });
  page.on('response', res => {
    if (res.url().includes('/api/')) {
      networkCalls.push(`RES: ${res.status()} ${res.url()}`);
    }
  });

  // Go to login with demo mode
  await page.goto('/login?auto_login=demo');
  await page.waitForTimeout(2000);

  console.log('=== After login ===');
  console.log('URL:', page.url());

  // Check if redirected to /app
  if (!page.url().includes('/app')) {
    console.log('Not redirected to /app, trying direct navigation');
    await page.goto('/app');
    await page.waitForTimeout(2000);
  }

  console.log('=== Page content ===');
  const bodyText = await page.locator('body').textContent();
  console.log('Body text (first 500 chars):', bodyText.substring(0, 500));

  // Try to find and click location
  const locationButton = page.locator('button, [role="button"]').filter({ hasText: /brasil|europe|usa|location/i }).first();
  if (await locationButton.count() > 0) {
    console.log('Found location button, clicking...');
    await locationButton.click();
    await page.waitForTimeout(1000);
  }

  // Try to advance to step 2
  const nextButton = page.locator('button').filter({ hasText: /next|próximo|continuar|avançar/i }).first();
  if (await nextButton.count() > 0) {
    console.log('Found next button, clicking...');
    await nextButton.click();
    await page.waitForTimeout(2000);
  }

  // Try to select a tier
  const tierButton = page.locator('button, [role="button"], div[class*="tier"], div[class*="card"]').filter({ hasText: /starter|básico|profissional|enterprise/i }).first();
  if (await tierButton.count() > 0) {
    console.log('Found tier button, clicking...');
    await tierButton.click();
    await page.waitForTimeout(3000);
  }

  console.log('\n=== Console logs ===');
  logs.forEach(l => console.log(l));

  console.log('\n=== Network calls ===');
  networkCalls.forEach(n => console.log(n));

  // Take screenshot
  await page.screenshot({ path: 'debug-gpu-screenshot.png', fullPage: true });
  console.log('\nScreenshot saved to debug-gpu-screenshot.png');
});
