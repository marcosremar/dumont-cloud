const { test, expect } = require('@playwright/test');

test.describe('Debug Start/Iniciar Button', () => {
  test.beforeEach(async ({ page }) => {
    // Use demo mode directly
    await page.goto('http://localhost:5173/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
  });

  test('Debug Start/Iniciar button on stopped machine', async ({ page }) => {
    console.log('=== DEBUGGING START/INICIAR BUTTON ===');

    // Take screenshot before
    console.log('1. Taking screenshot before...');
    await page.screenshot({ path: '/tmp/before-click.png', fullPage: true });

    // Set up console listener
    const consoleMessages = [];
    page.on('console', msg => {
      consoleMessages.push({ type: msg.type(), text: msg.text() });
    });

    // Find all machines
    console.log('2. Finding machines...');

    // Wait for machines to appear (bilingual)
    await expect(page.getByRole('heading', { name: /My Machines|Minhas Máquinas|Mis Máquinas/i })).toBeVisible();

    // Find offline machines (they have "Start/Iniciar" button) - bilingual
    const iniciarButtons = page.locator('button').filter({ hasText: /^Start$|^Iniciar$/i });
    const buttonCount = await iniciarButtons.count();
    console.log(`Found ${buttonCount} Start/Iniciar buttons (offline machines)`);

    if (buttonCount === 0) {
      console.log('No offline machines available to test');
      test.skip();
      return;
    }

    // Click the first Start/Iniciar button
    console.log('3. Clicking first Start/Iniciar button...');
    await iniciarButtons.first().click();

    // Wait for action
    await page.waitForTimeout(2000);

    // Check for toast notification
    console.log('4. Checking for toast notification...');
    const hasToast = await page.locator('text=/Iniciando|Starting|Ligando/i').isVisible().catch(() => false);
    console.log(`Toast visible: ${hasToast}`);

    // Take screenshot after
    console.log('5. Taking screenshot after...');
    await page.screenshot({ path: '/tmp/after-click.png', fullPage: true });

    console.log('=== TEST COMPLETE ===');
  });
});
