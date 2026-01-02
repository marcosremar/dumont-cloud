const { test, expect } = require('@playwright/test');

test.describe('Quick wizard test', () => {
  test('Verify GPU wizard flow', async ({ page }) => {
    // 1. Navigate to demo-app
    console.log('Step 1: Navigating to http://localhost:4893/demo-app');
    await page.goto('http://localhost:4893/demo-app', { waitUntil: 'networkidle' });

    // 2. Wait 2s
    console.log('Step 2: Waiting 2 seconds...');
    await page.waitForTimeout(2000);

    // 3. Click on "EUA"
    console.log('Step 3: Clicking on "EUA" button');
    const euaButton = page.locator('button:has-text("EUA")');
    await expect(euaButton).toBeVisible({ timeout: 5000 });
    await euaButton.click();

    // 4. Wait 1s
    console.log('Step 4: Waiting 1 second...');
    await page.waitForTimeout(1000);

    // 5. Verify "EUA" badge appears
    console.log('Step 5: Verifying EUA badge appears');
    const euaText = page.locator('text="EUA"');
    const textCount = await euaText.count();
    console.log(`Found ${textCount} elements with "EUA" text`);
    expect(textCount).toBeGreaterThan(0);

    // 6. Verify "Próximo" button is enabled
    console.log('Step 6: Verifying "Próximo" button is enabled');
    const nextButton = page.locator('button:has-text("Próximo")');
    await expect(nextButton).toBeVisible();
    await expect(nextButton).toBeEnabled();

    // 7. Click "Próximo"
    console.log('Step 7: Clicking "Próximo" button');
    await nextButton.click();

    // 8. Wait for navigation
    await page.waitForTimeout(1000);

    // 9. Verify we're in Step 2 (Hardware)
    console.log('Step 8: Verifying Step 2 (Hardware)');
    const hardwareTitle = page.locator('text="O que você vai fazer?"');
    await expect(hardwareTitle).toBeVisible({ timeout: 5000 });

    console.log('✅ SUCCESS: All wizard steps completed successfully!');
  });
});
