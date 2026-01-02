/**
 * Debug test for Wizard - Captures console logs
 */

const { test, expect } = require('@playwright/test');

test.describe('Wizard Debug - Console Logs', () => {
  let consoleLogs = [];

  test.beforeEach(async ({ page }) => {
    // Capture ALL console messages
    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push({
        type: msg.type(),
        text: text
      });
      console.log(`[BROWSER ${msg.type().toUpperCase()}]:`, text);
    });

    // Navigate to demo app (baseURL is configured in playwright.config.js)
    await page.goto('/demo-app');
    await page.waitForLoadState('networkidle');

    // Set demo mode
    await page.evaluate(() => {
      localStorage.setItem('demo_mode', 'true');
    });

    // Reload to ensure demo mode is active
    await page.reload();
    await page.waitForLoadState('networkidle');
  });

  test('Wizard navigation - Step 1 to Step 2', async ({ page }) => {
    consoleLogs = []; // Reset logs

    console.log('\n=== TEST START: Wizard Navigation Debug ===\n');

    // Wait for wizard to be visible
    await page.waitForSelector('text=Região', { timeout: 10000 });
    console.log('✅ Wizard visible');

    // Step 1: Select region "EUA"
    console.log('\n--- Clicking region "EUA" ---');
    const regionButton = page.locator('button[data-testid="region-eua"]');
    await expect(regionButton).toBeVisible({ timeout: 5000 });
    await regionButton.click();
    await page.waitForTimeout(1000);

    // Check if selection was registered
    const selectedLocation = await page.locator('text=Estados Unidos').isVisible();
    console.log(`Selected location visible: ${selectedLocation}`);

    // Try to click "Próximo" button
    console.log('\n--- Clicking "Próximo" button ---');
    const nextButton = page.locator('button:has-text("Próximo")');
    await expect(nextButton).toBeVisible({ timeout: 5000 });

    const isEnabled = await nextButton.isEnabled();
    console.log(`Next button enabled: ${isEnabled}`);

    await nextButton.click();
    await page.waitForTimeout(2000);

    // Check current step
    const currentStepText = await page.textContent('[class*="text-brand-400"]');
    console.log(`Current step after click: ${currentStepText}`);

    // Check if we're on step 2
    const hardwareVisible = await page.locator('text=O que você vai fazer?').isVisible().catch(() => false);
    console.log(`Step 2 (Hardware) visible: ${hardwareVisible}`);

    // Print all console logs that start with 🔍 or ➡️
    console.log('\n=== RELEVANT CONSOLE LOGS ===');
    const relevantLogs = consoleLogs.filter(log =>
      log.text.includes('🔍') ||
      log.text.includes('➡️') ||
      log.text.includes('✅') ||
      log.text.includes('❌') ||
      log.text.includes('isStepComplete') ||
      log.text.includes('handleNext')
    );

    if (relevantLogs.length > 0) {
      relevantLogs.forEach(log => {
        console.log(`[${log.type}] ${log.text}`);
      });
    } else {
      console.log('No relevant logs found!');
      console.log('\nALL console logs:');
      consoleLogs.forEach(log => {
        console.log(`[${log.type}] ${log.text}`);
      });
    }

    console.log('\n=== TEST END ===\n');

    // Assertions
    expect(hardwareVisible).toBe(true);
  });

  test('Wizard state inspection', async ({ page }) => {
    console.log('\n=== Inspecting Wizard Internal State ===\n');

    // Wait for wizard
    await page.waitForSelector('text=Região', { timeout: 10000 });

    // Click region
    const regionButton = page.locator('button[data-testid="region-eua"]');
    await regionButton.click();
    await page.waitForTimeout(500);

    // Inspect React state via DOM
    const inspectState = await page.evaluate(() => {
      // Try to find the wizard component's data attributes or state
      const wizardElement = document.querySelector('[class*="space-y-6"]');

      // Check for step indicators
      const stepIndicators = Array.from(document.querySelectorAll('[class*="text-brand-400"]'));
      const currentStepNumbers = stepIndicators.map(el => el.textContent);

      // Check for selected location badge
      const locationBadge = document.querySelector('text=Estados Unidos');

      // Check next button state
      const nextButton = Array.from(document.querySelectorAll('button')).find(btn =>
        btn.textContent.includes('Próximo')
      );

      return {
        stepNumbers: currentStepNumbers,
        hasLocationBadge: !!locationBadge,
        nextButtonDisabled: nextButton?.disabled,
        nextButtonClass: nextButton?.className,
      };
    });

    console.log('Wizard state:', JSON.stringify(inspectState, null, 2));

    // Now click next and see what happens
    console.log('\n--- Before clicking Next ---');
    await page.locator('button:has-text("Próximo")').click();
    await page.waitForTimeout(1000);

    const stateAfterClick = await page.evaluate(() => {
      const stepIndicators = Array.from(document.querySelectorAll('[class*="text-brand-400"]'));
      const currentStepNumbers = stepIndicators.map(el => el.textContent);

      const hardwareSection = document.querySelector('text=O que você vai fazer?');

      return {
        stepNumbers: currentStepNumbers,
        hardwareSectionVisible: !!hardwareSection,
      };
    });

    console.log('\n--- After clicking Next ---');
    console.log('State after click:', JSON.stringify(stateAfterClick, null, 2));
  });
});
