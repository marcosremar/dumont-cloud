// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Simple Wizard Flow', () => {
  test('EUA selection enables Próximo button', async ({ page }) => {
    // Navigate
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Get locators
    const euaButton = page.locator('button[data-testid="region-eua"]');
    const nextButton = page.locator('button:has-text("Próximo")');

    // Check initial state
    console.log('Initial state:');
    const initialDisabled = await nextButton.isDisabled();
    console.log(`  Próximo button disabled: ${initialDisabled}`);
    expect(initialDisabled).toBe(true);

    // Click EUA
    console.log('\nClicking EUA button...');
    await euaButton.click();

    // Wait a bit for React
    await page.waitForTimeout(500);

    // Check new state
    console.log('\nAfter click:');
    const afterDisabled = await nextButton.isDisabled();
    console.log(`  Próximo button disabled: ${afterDisabled}`);

    // This should pass
    expect(afterDisabled, 'Próximo button should be enabled after clicking EUA').toBe(false);

    console.log('\n✅ Test passed!');
  });
});
