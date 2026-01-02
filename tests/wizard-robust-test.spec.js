// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Wizard Navigation - Robust Test with Waits', () => {
  let consoleLogs = [];
  let consoleErrors = [];

  test.beforeEach(async ({ page }) => {
    // Capture console messages
    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push({
        type: msg.type(),
        text: text,
        timestamp: new Date().toISOString()
      });

      if (msg.type() === 'error') {
        consoleErrors.push(text);
      }

      console.log(`[BROWSER ${msg.type().toUpperCase()}]:`, text);
    });

    // Capture page errors
    page.on('pageerror', error => {
      const errorMsg = `Page error: ${error.message}`;
      consoleErrors.push(errorMsg);
      console.error('[PAGE ERROR]:', error.message);
    });

    // Capture network errors
    page.on('requestfailed', request => {
      const errorMsg = `Failed request: ${request.url()} - ${request.failure()?.errorText}`;
      console.error('[NETWORK ERROR]:', errorMsg);
    });
  });

  test.afterEach(async () => {
    // Print summary of console logs
    console.log('\n========================================');
    console.log('CONSOLE LOGS SUMMARY');
    console.log('========================================');
    console.log(`Total logs: ${consoleLogs.length}`);
    console.log(`Errors: ${consoleErrors.length}`);

    if (consoleErrors.length > 0) {
      console.log('\nERRORS DETECTED:');
      consoleErrors.forEach((err, i) => {
        console.log(`  ${i + 1}. ${err}`);
      });
    }

    // Reset for next test
    consoleLogs = [];
    consoleErrors = [];
  });

  test('Wizard Step 1 → Step 2 with robust waits', async ({ page }) => {
    console.log('\n🚀 Starting wizard navigation test...\n');

    // Step 1: Navigate to demo-app
    console.log('📍 Step 1: Navigating to /demo-app');
    await page.goto('http://localhost:4898/demo-app');

    // Step 2: Wait for page to fully load
    console.log('⏳ Step 2: Waiting 2 seconds for page load');
    await page.waitForTimeout(2000);

    // Step 3: Take initial snapshot
    console.log('📸 Step 3: Taking initial snapshot');
    const initialContent = await page.content();
    console.log(`   - Page title: ${await page.title()}`);
    console.log(`   - URL: ${page.url()}`);
    console.log(`   - Content length: ${initialContent.length} chars`);

    // Verify we're on Step 1 (region selection)
    const step1Visible = await page.locator('text=/onde você está|região/i').isVisible({ timeout: 3000 }).catch(() => false);
    console.log(`   - Step 1 question visible: ${step1Visible}`);

    // Step 4: Look for "EUA" button
    console.log('🔍 Step 4: Looking for EUA button');
    const euaButton = page.locator('button:has-text("EUA")');
    const euaCount = await euaButton.count();
    console.log(`   - Found ${euaCount} EUA button(s)`);

    if (euaCount === 0) {
      // Log all visible buttons for debugging
      const allButtons = await page.locator('button').allTextContents();
      console.log('   - All buttons on page:', allButtons);
      throw new Error('EUA button not found');
    }

    // Step 5: Click "EUA"
    console.log('👆 Step 5: Clicking EUA button');
    await euaButton.first().click();

    // Step 6: Wait after click
    console.log('⏳ Step 6: Waiting 1 second after EUA click');
    await page.waitForTimeout(1000);

    // Step 7: Take snapshot to verify badge appeared
    console.log('📸 Step 7: Taking snapshot after EUA click');

    // Check for badge or active state
    const badgeVisible = await page.locator('text="EUA"').filter({ hasText: /^EUA$/}).count();
    console.log(`   - EUA badge/button count: ${badgeVisible}`);

    // Check if button has active/selected state
    const euaButtonState = await euaButton.first().getAttribute('class');
    console.log(`   - EUA button classes: ${euaButtonState}`);

    // Step 8: Check if "Próximo" button is enabled
    console.log('🔍 Step 8: Checking if Próximo button is enabled');
    const nextButton = page.locator('button:has-text("Próximo")');
    const nextButtonExists = await nextButton.count();
    console.log(`   - Próximo button count: ${nextButtonExists}`);

    if (nextButtonExists === 0) {
      const allButtons = await page.locator('button').allTextContents();
      console.log('   - All buttons:', allButtons);
      throw new Error('Próximo button not found');
    }

    const isEnabled = await nextButton.first().isEnabled();
    const buttonClasses = await nextButton.first().getAttribute('class');
    const isDisabled = await nextButton.first().getAttribute('disabled');

    console.log(`   - Is enabled: ${isEnabled}`);
    console.log(`   - Classes: ${buttonClasses}`);
    console.log(`   - Disabled attr: ${isDisabled}`);

    expect(isEnabled, 'Próximo button should be enabled after selecting EUA').toBe(true);

    // Step 9: Click "Próximo"
    console.log('👆 Step 9: Clicking Próximo button');
    await nextButton.first().click();

    // Step 10: Wait for transition
    console.log('⏳ Step 10: Waiting 2 seconds for step transition');
    await page.waitForTimeout(2000);

    // Step 11: Take snapshot and verify Step 2
    console.log('📸 Step 11: Taking snapshot to verify Step 2');

    // Look for Step 2 indicators
    const step2Question = await page.locator('text=/o que você vai fazer|desenvolver|treinar/i').count();
    console.log(`   - Step 2 question count: ${step2Question}`);

    // Look for "Desenvolver" option (common in Step 2)
    const desenvolverOption = await page.locator('text="Desenvolver"').count();
    console.log(`   - "Desenvolver" option count: ${desenvolverOption}`);

    // Check if we're still on Step 1 or moved to Step 2
    const stillOnStep1 = await page.locator('text=/onde você está|região/i').count();
    console.log(`   - Step 1 question still visible: ${stillOnStep1}`);

    // Get current URL (might have changed)
    console.log(`   - Current URL: ${page.url()}`);

    // Log all visible text for debugging
    const mainContent = await page.locator('main, [role="main"], .wizard-content').textContent().catch(() => '');
    console.log(`   - Main content preview: ${mainContent.substring(0, 200)}...`);

    // Verify we're on Step 2
    if (step2Question > 0 || desenvolverOption > 0) {
      console.log('✅ SUCCESS: Transitioned to Step 2');
    } else if (stillOnStep1 > 0) {
      console.log('❌ FAILURE: Still on Step 1');
      throw new Error('Did not transition to Step 2 - still showing Step 1 content');
    } else {
      console.log('⚠️  UNCLEAR: Cannot determine current step');
      // Take a screenshot for manual inspection
      await page.screenshot({ path: 'test-results/wizard-unclear-state.png', fullPage: true });
      console.log('   - Screenshot saved to test-results/wizard-unclear-state.png');
    }

    // Final assertion
    expect(
      step2Question > 0 || desenvolverOption > 0,
      'Should show Step 2 content (question about what to do or Desenvolver option)'
    ).toBe(true);

    console.log('\n🎉 Test completed successfully!\n');
  });

  test('Wizard - Detailed state inspection', async ({ page }) => {
    console.log('\n🔬 Starting detailed state inspection test...\n');

    await page.goto('http://localhost:4898/demo-app');
    await page.waitForTimeout(2000);

    // Inspect initial state
    console.log('📊 INITIAL STATE:');
    console.log('==================');

    // Get wizard state from window/Redux if available
    const wizardState = await page.evaluate(() => {
      // Try to access Redux state
      if (window.__REDUX_DEVTOOLS_EXTENSION__) {
        return { hasRedux: true };
      }

      // Try to access window state
      return {
        hasRedux: false,
        url: window.location.href,
        readyState: document.readyState
      };
    }).catch(() => ({}));

    console.log('Window state:', JSON.stringify(wizardState, null, 2));

    // Count all interactive elements
    const buttonCount = await page.locator('button').count();
    const inputCount = await page.locator('input').count();
    const linkCount = await page.locator('a').count();

    console.log(`Interactive elements: ${buttonCount} buttons, ${inputCount} inputs, ${linkCount} links`);

    // Get all button texts
    const buttonTexts = await page.locator('button').allTextContents();
    console.log('All buttons:', buttonTexts);

    // Click EUA and inspect state change
    console.log('\n📊 AFTER CLICKING EUA:');
    console.log('==================');

    await page.locator('button:has-text("EUA")').first().click();
    await page.waitForTimeout(1000);

    // Check for state changes in DOM
    const activeButtons = await page.locator('button[class*="active"], button[class*="selected"], button[aria-pressed="true"]').count();
    console.log(`Active/selected buttons: ${activeButtons}`);

    // Check data attributes
    const euaButtonData = await page.locator('button:has-text("EUA")').first().evaluate(el => ({
      className: el.className,
      ariaPPressed: el.getAttribute('aria-pressed'),
      dataSelected: el.getAttribute('data-selected'),
      disabled: el.disabled
    }));
    console.log('EUA button state:', euaButtonData);

    // Check Próximo button state
    const nextButtonData = await page.locator('button:has-text("Próximo")').first().evaluate(el => ({
      className: el.className,
      disabled: el.disabled,
      ariaDisabled: el.getAttribute('aria-disabled')
    }));
    console.log('Próximo button state:', nextButtonData);

    console.log('\n🔬 Inspection complete!\n');
  });
});
