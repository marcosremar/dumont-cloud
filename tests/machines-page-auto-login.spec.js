const { test, expect } = require('@playwright/test');

test.describe('Machines Page - Auto Login Test', () => {
  const BASE_URL = 'http://localhost:4894';

  test('should auto-login and navigate to machines page', async ({ page }) => {
    // Track console errors and warnings
    const consoleMessages = [];
    const pageErrors = [];

    page.on('console', msg => {
      consoleMessages.push({
        type: msg.type(),
        text: msg.text(),
        location: msg.location()
      });
    });

    page.on('pageerror', err => {
      pageErrors.push({
        message: err.message,
        stack: err.stack
      });
    });

    // Step 1: Navigate to login with auto_login=demo
    console.log('Step 1: Navigating to login with auto_login=demo...');
    await page.goto(`${BASE_URL}/login?auto_login=demo`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    // Step 2: Wait for redirect to /app
    console.log('Step 2: Waiting for redirect to /app...');
    await page.waitForURL('**/app**', { timeout: 15000 });
    console.log('Successfully redirected to:', page.url());

    // Give a moment for the app to initialize
    await page.waitForTimeout(1000);

    // Step 3: Navigate to /app/machines
    console.log('Step 3: Navigating to /app/machines...');
    await page.goto(`${BASE_URL}/app/machines`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    // Wait for page to load
    await page.waitForSelector('main', { timeout: 10000 });
    await page.waitForTimeout(2000);

    // Take initial screenshot
    await page.screenshot({
      path: 'test-results/machines-page-initial.png',
      fullPage: true
    });

    // Step 4: Verify page title "Minhas Máquinas"
    console.log('Step 4: Verifying page title...');
    const titleElement = await page.locator('h1:has-text("Minhas Máquinas")').first();
    await expect(titleElement).toBeVisible({ timeout: 10000 });
    console.log('✓ Page title "Minhas Máquinas" found');

    // Step 5: Verify "Nova Máquina" button
    console.log('Step 5: Verifying "Nova Máquina" button...');
    const novaMaquinaButton = await page.locator('a:has-text("Nova Máquina")').first();
    await expect(novaMaquinaButton).toBeVisible({ timeout: 5000 });
    console.log('✓ "Nova Máquina" button found');

    // Step 6: Check for stats cards
    console.log('Step 6: Checking for stats cards...');
    const statsCards = await page.locator('.stat-card').count();
    console.log(`Found ${statsCards} stat cards`);
    expect(statsCards).toBeGreaterThan(0);

    // Step 7: Check for filter tabs
    console.log('Step 7: Checking for filter tabs...');
    const filterTabs = await page.locator('.ta-tab').count();
    console.log(`Found ${filterTabs} filter tabs`);
    expect(filterTabs).toBeGreaterThan(0);

    // Step 8: Check content area - either machines or empty state
    console.log('Step 8: Checking content area...');
    const hasEmptyState = await page.locator('text=Nenhuma máquina').count() > 0;
    const hasMachineCards = await page.locator('[data-testid*="machine-card"]').count() > 0
      || await page.locator('.grid.grid-cols-1.md\\:grid-cols-2').first().isVisible().catch(() => false);

    console.log('Empty state visible:', hasEmptyState);
    console.log('Machine cards present:', hasMachineCards);

    // Either empty state or machine cards should be present
    expect(hasEmptyState || hasMachineCards).toBeTruthy();

    // Step 9: Take final screenshot
    await page.screenshot({
      path: 'test-results/machines-page-final.png',
      fullPage: true
    });

    // Step 10: Check for critical JavaScript errors
    console.log('Step 10: Analyzing console messages...');
    const criticalErrors = pageErrors.filter(e =>
      e.message.includes('ReferenceError') ||
      e.message.includes('is not defined') ||
      e.message.includes('TypeError') ||
      e.message.includes('Cannot read')
    );

    const consoleErrors = consoleMessages.filter(m =>
      m.type === 'error' &&
      !m.text.includes('favicon') && // Ignore favicon errors
      !m.text.includes('DevTools') // Ignore DevTools messages
    );

    console.log('\n=== Console Errors ===');
    consoleErrors.forEach(err => {
      console.log(`[${err.type}] ${err.text}`);
    });

    console.log('\n=== Page Errors ===');
    criticalErrors.forEach(err => {
      console.error(`${err.message}\n${err.stack}`);
    });

    // Report findings
    console.log('\n=== Test Summary ===');
    console.log('✓ Auto-login successful');
    console.log('✓ Redirected to /app');
    console.log('✓ Navigated to /app/machines');
    console.log('✓ Page title "Minhas Máquinas" present');
    console.log('✓ "Nova Máquina" button present');
    console.log(`✓ ${statsCards} stats cards found`);
    console.log(`✓ ${filterTabs} filter tabs found`);
    console.log(`✓ Content area: ${hasEmptyState ? 'Empty state' : 'Machine cards'}`);
    console.log(`Console errors: ${consoleErrors.length}`);
    console.log(`Critical JS errors: ${criticalErrors.length}`);

    // Fail test if there are critical errors
    expect(criticalErrors).toHaveLength(0);
  });

  test('should verify machines page interactive elements', async ({ page }) => {
    // Navigate with auto-login
    await page.goto(`${BASE_URL}/login?auto_login=demo`);
    await page.waitForURL('**/app**', { timeout: 15000 });
    await page.goto(`${BASE_URL}/app/machines`);
    await page.waitForSelector('main', { timeout: 10000 });
    await page.waitForTimeout(1500);

    console.log('Testing interactive elements...');

    // Test filter tabs
    const allTab = await page.locator('.ta-tab:has-text("Todas")').first();
    const onlineTab = await page.locator('.ta-tab:has-text("Online")').first();
    const offlineTab = await page.locator('.ta-tab:has-text("Offline")').first();

    if (await allTab.isVisible()) {
      console.log('✓ All tabs are visible');

      // Click on Online tab
      await onlineTab.click();
      await page.waitForTimeout(500);
      console.log('✓ Clicked "Online" tab');

      // Click on Offline tab
      await offlineTab.click();
      await page.waitForTimeout(500);
      console.log('✓ Clicked "Offline" tab');

      // Click back to All tab
      await allTab.click();
      await page.waitForTimeout(500);
      console.log('✓ Clicked "Todas" tab');
    }

    // Test "Nova Máquina" button navigation
    const novaMaquinaButton = await page.locator('a:has-text("Nova Máquina")').first();
    const buttonHref = await novaMaquinaButton.getAttribute('href');
    console.log(`"Nova Máquina" button href: ${buttonHref}`);
    expect(buttonHref).toBeTruthy();

    // Take screenshot of interactive state
    await page.screenshot({
      path: 'test-results/machines-page-interactive.png',
      fullPage: true
    });

    console.log('✓ Interactive elements test complete');
  });

  test('should verify page responsiveness', async ({ page }) => {
    // Navigate with auto-login
    await page.goto(`${BASE_URL}/login?auto_login=demo`);
    await page.waitForURL('**/app**', { timeout: 15000 });
    await page.goto(`${BASE_URL}/app/machines`);
    await page.waitForSelector('main', { timeout: 10000 });
    await page.waitForTimeout(1500);

    console.log('Testing page responsiveness...');

    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: 'test-results/machines-page-mobile.png',
      fullPage: true
    });
    console.log('✓ Mobile viewport (375x812) rendered');

    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: 'test-results/machines-page-tablet.png',
      fullPage: true
    });
    console.log('✓ Tablet viewport (768x1024) rendered');

    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: 'test-results/machines-page-desktop.png',
      fullPage: true
    });
    console.log('✓ Desktop viewport (1920x1080) rendered');

    console.log('✓ Responsiveness test complete');
  });
});
