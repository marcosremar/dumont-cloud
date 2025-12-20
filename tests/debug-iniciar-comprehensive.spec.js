const { test, expect } = require('@playwright/test');

test.describe('Comprehensive Iniciar Button Debug', () => {

  test('Debug Iniciar button functionality', async ({ page }) => {
    console.log('\n' + '='.repeat(80));
    console.log('DEBUGGING INICIAR BUTTON ON MACHINES PAGE');
    console.log('='.repeat(80) + '\n');

    // Set up console and error listeners
    const consoleLogs = [];
    const pageErrors = [];

    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push({ type: msg.type(), text });
    });

    page.on('pageerror', error => {
      pageErrors.push(error.message);
      console.log(`[PAGE ERROR] ${error.message}`);
    });

    // Navigate to demo app machines page directly
    console.log('\n📍 Step 1: Navigating to demo machines page...');
    await page.goto('http://localhost:5173/app/machines');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    console.log('   ✅ Page loaded');

    // Take initial screenshot
    await page.screenshot({ path: '/tmp/iniciar-debug-01-initial.png', fullPage: true });
    console.log('   📸 Screenshot saved');

    // Verify we're in demo mode
    console.log('\n🎮 Step 2: Verifying demo mode...');
    const currentUrl = page.url();
    console.log(`   Current URL: ${currentUrl}`);
    const isDemoMode = currentUrl.includes('/app');
    console.log(`   Is Demo Mode: ${isDemoMode}`);

    // Wait for page heading
    console.log('\n🖥️  Step 3: Finding machine cards...');
    await expect(page.getByRole('heading', { name: 'Minhas Máquinas' })).toBeVisible();
    console.log('   ✅ Machines page header found');

    // Count GPU names on page
    const gpuCount = await page.locator('text=/RTX \\d{4}|A100|H100/').count();
    console.log(`   Found ${gpuCount} GPUs on page`);

    // Find Iniciar buttons (offline machines)
    console.log('\n🔍 Step 4: Looking for Iniciar buttons...');
    const iniciarButtons = page.locator('button:has-text("Iniciar")');
    const buttonCount = await iniciarButtons.count();
    console.log(`   Found ${buttonCount} "Iniciar" button(s)`);

    if (buttonCount === 0) {
      console.log('   ⚠️  No offline machines to test');
      await page.screenshot({ path: '/tmp/iniciar-debug-no-offline.png', fullPage: true });
      test.skip();
      return;
    }

    // Get button info
    console.log('\n🔬 Step 5: Inspecting first button...');
    const firstButton = iniciarButtons.first();

    const buttonInfo = await firstButton.evaluate(btn => {
      return {
        visible: btn.offsetParent !== null,
        disabled: btn.disabled,
        text: btn.textContent?.trim(),
        className: btn.className,
      };
    });

    console.log('   Button properties:');
    console.log(`      - Visible: ${buttonInfo.visible}`);
    console.log(`      - Disabled: ${buttonInfo.disabled}`);
    console.log(`      - Text: "${buttonInfo.text}"`);

    // Click the button
    console.log('\n👆 Step 6: Clicking Iniciar button...');
    await firstButton.scrollIntoViewIfNeeded();
    await firstButton.click();
    console.log('   ✅ Click executed');

    // Wait and check
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/iniciar-debug-02-after-click.png', fullPage: true });

    // Check for toast
    console.log('\n🍞 Step 7: Checking for feedback...');
    const hasToast = await page.locator('text=/Iniciando|Starting|Ligando/i').isVisible().catch(() => false);
    console.log(`   Toast visible: ${hasToast}`);

    // Summary
    console.log('\n' + '='.repeat(80));
    console.log('DEBUG SUMMARY');
    console.log('='.repeat(80));
    console.log(`Demo Mode: ${isDemoMode}`);
    console.log(`GPU Count: ${gpuCount}`);
    console.log(`Iniciar Buttons Found: ${buttonCount}`);
    console.log(`Toast Appeared: ${hasToast}`);
    console.log(`Page Errors: ${pageErrors.length}`);
    console.log('='.repeat(80) + '\n');

    console.log('\n✅ Debug test completed!\n');
  });
});
