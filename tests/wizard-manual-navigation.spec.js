const { test, expect } = require('@playwright/test');

test.describe('Quick wizard test', () => {
  test('Verify GPU wizard flow - Regional selection and hardware step', async ({ page }) => {
    const baseURL = 'http://localhost:4893';
    console.log('Using baseURL:', baseURL);

    // 1. Navigate to demo-app
    console.log('Step 1: Navigating to /demo-app');
    await page.goto(baseURL + '/demo-app', { waitUntil: 'networkidle' });

    // 2. Wait 2s
    console.log('Step 2: Waiting 2 seconds...');
    await page.waitForTimeout(2000);

    // 3. Take a screenshot to see current state
    await page.screenshot({ path: 'step1-before-eua.png' });

    // 4. Click on "EUA" button
    console.log('Step 3: Clicking on "EUA" button');
    const euaButton = page.locator('button:has-text("EUA")');
    console.log('EUA button found:', await euaButton.count());
    await expect(euaButton).toBeVisible({ timeout: 5000 });
    await euaButton.click();

    // 5. Wait 1s
    console.log('Step 4: Waiting 1 second...');
    await page.waitForTimeout(1000);

    // 6. Take screenshot after EUA click
    await page.screenshot({ path: 'step2-after-eua.png' });

    // 7. Verify "EUA" badge appears
    console.log('Step 5: Verifying EUA badge appears');
    const euaText = page.locator('text="EUA"');
    const textCount = await euaText.count();
    console.log(`Found ${textCount} elements with "EUA" text`);
    expect(textCount).toBeGreaterThan(0);

    // 8. Verify "Próximo" button is enabled
    console.log('Step 6: Verifying "Próximo" button is enabled');
    const nextButton = page.locator('button:has-text("Próximo")');
    await expect(nextButton).toBeVisible();
    await expect(nextButton).toBeEnabled();

    // 9. Click "Próximo"
    console.log('Step 7: Clicking "Próximo" button');
    await nextButton.click();

    // 10. Wait for navigation
    await page.waitForTimeout(1500);

    // 11. Take screenshot after click
    await page.screenshot({ path: 'step3-after-proximo.png' });

    // 12. Verify we're in Step 2 (Hardware)
    console.log('Step 8: Verifying Step 2 (Hardware) - looking for "O que você vai fazer?"');

    // Try multiple selectors
    let foundHardwareStep = false;

    // Check for exact title
    const hardwareTitleExact = page.locator('text="O que você vai fazer?"');
    if (await hardwareTitleExact.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('Found: "O que você vai fazer?"');
      foundHardwareStep = true;
    }

    // Check for any hardware-related text
    if (!foundHardwareStep) {
      const hardwareAny = page.locator('text=/O que|hardware|Step.*2/i');
      const count = await hardwareAny.count();
      console.log(`Found ${count} hardware-related elements`);
      if (count > 0) {
        console.log('Hardware step content:', await hardwareAny.first().textContent());
        foundHardwareStep = true;
      }
    }

    // List all visible text for debugging
    if (!foundHardwareStep) {
      const allText = await page.locator('body').textContent();
      console.log('Page content sample:', allText.substring(0, 500));
    }

    expect(foundHardwareStep).toBeTruthy();
    console.log('✅ SUCCESS: All wizard steps completed successfully!');
  });
});
