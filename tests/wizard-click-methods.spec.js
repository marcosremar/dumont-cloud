// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Wizard Click Methods Comparison', () => {
  test('Compare different click methods', async ({ page }) => {
    console.log('\n🧪 Testing different click methods...\n');

    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    const euaButton = page.locator('button[data-testid="region-eua"]');
    const nextButton = page.locator('button:has-text("Próximo")');

    // Method 1: Playwright .click()
    console.log('📍 Method 1: Playwright .click()');
    const nextDisabledBefore = await nextButton.isDisabled();
    console.log(`   Próximo disabled BEFORE: ${nextDisabledBefore}`);

    await euaButton.click();
    await page.waitForTimeout(500);

    const nextDisabledAfter1 = await nextButton.isDisabled();
    console.log(`   Próximo disabled AFTER: ${nextDisabledAfter1}`);
    console.log(`   Result: ${nextDisabledAfter1 ? '❌ FAILED' : '✅ WORKS'}`);

    // Reload page for next test
    await page.reload();
    await page.waitForTimeout(2000);

    // Method 2: .click({ force: true })
    console.log('\n📍 Method 2: Playwright .click({ force: true })');
    const nextDisabled2Before = await nextButton.isDisabled();
    console.log(`   Próximo disabled BEFORE: ${nextDisabled2Before}`);

    await euaButton.click({ force: true });
    await page.waitForTimeout(500);

    const nextDisabledAfter2 = await nextButton.isDisabled();
    console.log(`   Próximo disabled AFTER: ${nextDisabledAfter2}`);
    console.log(`   Result: ${nextDisabledAfter2 ? '❌ FAILED' : '✅ WORKS'}`);

    // Reload page for next test
    await page.reload();
    await page.waitForTimeout(2000);

    // Method 3: Direct dispatchEvent
    console.log('\n📍 Method 3: dispatchEvent (MouseEvent)');
    const nextDisabled3Before = await nextButton.isDisabled();
    console.log(`   Próximo disabled BEFORE: ${nextDisabled3Before}`);

    await euaButton.evaluate(el => {
      el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    });
    await page.waitForTimeout(500);

    const nextDisabledAfter3 = await nextButton.isDisabled();
    console.log(`   Próximo disabled AFTER: ${nextDisabledAfter3}`);
    console.log(`   Result: ${nextDisabledAfter3 ? '❌ FAILED' : '✅ WORKS'}`);

    // Reload page for next test
    await page.reload();
    await page.waitForTimeout(2000);

    // Method 4: Trigger via pointer events
    console.log('\n📍 Method 4: Sequence of pointer events');
    const nextDisabled4Before = await nextButton.isDisabled();
    console.log(`   Próximo disabled BEFORE: ${nextDisabled4Before}`);

    await euaButton.dispatchEvent('pointerdown');
    await page.waitForTimeout(50);
    await euaButton.dispatchEvent('pointerup');
    await euaButton.dispatchEvent('click');
    await page.waitForTimeout(500);

    const nextDisabledAfter4 = await nextButton.isDisabled();
    console.log(`   Próximo disabled AFTER: ${nextDisabledAfter4}`);
    console.log(`   Result: ${nextDisabledAfter4 ? '❌ FAILED' : '✅ WORKS'}`);

    // Reload page for next test
    await page.reload();
    await page.waitForTimeout(2000);

    // Method 5: Use locator.click() with timeout
    console.log('\n📍 Method 5: .click() with delay before check');
    const nextDisabled5Before = await nextButton.isDisabled();
    console.log(`   Próximo disabled BEFORE: ${nextDisabled5Before}`);

    await euaButton.click();
    console.log('   Waiting 2000ms for React to update...');
    await page.waitForTimeout(2000);

    const nextDisabledAfter5 = await nextButton.isDisabled();
    console.log(`   Próximo disabled AFTER: ${nextDisabledAfter5}`);
    console.log(`   Result: ${nextDisabledAfter5 ? '❌ FAILED' : '✅ WORKS'}`);

    // Reload page for next test
    await page.reload();
    await page.waitForTimeout(2000);

    // Method 6: Click and wait for element state change
    console.log('\n📍 Method 6: Click and wait for state attribute');
    const nextDisabled6Before = await nextButton.isDisabled();
    console.log(`   Próximo disabled BEFORE: ${nextDisabled6Before}`);

    await euaButton.click();

    // Try to wait for any state change
    try {
      await page.waitForFunction(() => {
        const next = document.querySelector('button:has-text("Próximo")');
        return next && !next.disabled;
      }, { timeout: 3000 });
      console.log('   ✅ State changed within 3 seconds');
    } catch (e) {
      console.log('   ❌ State did NOT change within 3 seconds');
    }

    const nextDisabledAfter6 = await nextButton.isDisabled();
    console.log(`   Próximo disabled AFTER: ${nextDisabledAfter6}`);
    console.log(`   Result: ${nextDisabledAfter6 ? '❌ FAILED' : '✅ WORKS'}`);

    console.log('\n📊 SUMMARY:');
    console.log('   All methods tested. Check results above.');
  });

  test('Verify button has correct data-testid', async ({ page }) => {
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Check all region buttons
    const regionButtons = await page.locator('button[data-testid^="region-"]').all();
    console.log(`\n📋 Found ${regionButtons.length} region buttons:`);

    for (const button of regionButtons) {
      const testId = await button.getAttribute('data-testid');
      const text = await button.textContent();
      console.log(`   - ${testId}: "${text}"`);
    }

    // Verify EUA button exists
    const euaButton = page.locator('button[data-testid="region-eua"]');
    const count = await euaButton.count();
    console.log(`\n📍 EUA button with data-testid="region-eua": ${count} found`);

    expect(count).toBe(1);
  });
});
