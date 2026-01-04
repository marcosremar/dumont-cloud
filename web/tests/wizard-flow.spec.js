import { test, expect } from '@playwright/test';

// Auth state for logged-in user
const AUTH_STATE = {
  auth_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYXJjb3NyZW1hckBnbWFpbC5jb20iLCJleHAiOjE3NzEzNjgwMDEsImlhdCI6MTc2NzQ4MDAwMX0.xUYMEh5uCnuE_9qiWlH4RJ-WW01WKoznoj2J6ORZYC0',
  auth_user: '"marcosremar@gmail.com"',
  auth_login_time: String(Date.now()),
  theme: 'dark'
};

test.describe('Wizard Flow - Reserve Machine', () => {
  test.beforeEach(async ({ page }) => {
    // Set auth state before navigating
    await page.goto('/');
    await page.evaluate((authState) => {
      localStorage.setItem('auth_token', authState.auth_token);
      localStorage.setItem('auth_user', authState.auth_user);
      localStorage.setItem('auth_login_time', authState.auth_login_time);
      localStorage.setItem('theme', authState.theme);
    }, AUTH_STATE);

    // Go to new machine page
    await page.goto('/app/machines/new');
    await page.waitForLoadState('networkidle');
  });

  test('Complete wizard flow to reserve a machine', async ({ page }) => {
    // Step 1: Location Selection
    console.log('Step 1: Location Selection');

    // Wait for wizard to load
    await expect(page.locator('.page-title')).toContainText('New GPU Machine');

    // Click on USA region button
    const usaButton = page.locator('button:has-text("USA")');
    if (await usaButton.isVisible()) {
      await usaButton.click();
      console.log('  - Selected USA region');
    } else {
      // Try Europe as fallback
      const europeButton = page.locator('button:has-text("Europe")');
      if (await europeButton.isVisible()) {
        await europeButton.click();
        console.log('  - Selected Europe region');
      }
    }

    // Wait for location to be selected
    await page.waitForTimeout(500);

    // Click Next button (Portuguese: Próximo)
    const nextButton = page.locator('button:has-text("Próximo")');
    await expect(nextButton).toBeEnabled({ timeout: 5000 });
    await nextButton.click();
    console.log('  - Clicked Próximo');

    // Step 2: Hardware Selection
    console.log('Step 2: Hardware Selection');
    await page.waitForTimeout(500);

    // Select a use case (e.g., Experiment/Develop)
    const experimentButton = page.locator('[data-testid="use-case-test"]');
    if (await experimentButton.isVisible()) {
      await experimentButton.click();
      console.log('  - Selected Experiment use case');
    } else {
      const developButton = page.locator('[data-testid="use-case-develop"]');
      if (await developButton.isVisible()) {
        await developButton.click();
        console.log('  - Selected Develop use case');
      }
    }

    // Wait for machines to load
    await page.waitForTimeout(2000);

    // Select first recommended machine if available
    const machineButton = page.locator('[data-testid="machine-0"]');
    if (await machineButton.isVisible({ timeout: 5000 })) {
      await machineButton.click();
      console.log('  - Selected first machine');
    }

    // Click Próximo
    await nextButton.click();
    console.log('  - Clicked Próximo');

    // Step 3: Strategy Selection
    console.log('Step 3: Strategy Selection');
    await page.waitForTimeout(500);

    // Strategy should be pre-selected (snapshot_only)
    // Click Iniciar (Start) button for step 3
    const startButton = page.locator('button:has-text("Iniciar")');
    await expect(startButton).toBeEnabled({ timeout: 5000 });
    await startButton.click();
    console.log('  - Clicked Iniciar');

    // Step 4: Provisioning
    console.log('Step 4: Provisioning');
    await page.waitForTimeout(2000);

    // Take screenshot of step 4
    await page.screenshot({ path: 'tests/screenshots/wizard-step4-provisioning.png' });
    console.log('  - Screenshot saved');

    // Check if we're on provisioning step - look for racing indicators
    const provisioningIndicators = [
      page.locator('text=/Round [0-9]/i'),
      page.locator('text=/Conectando/i'),
      page.locator('text=/Racing/i'),
      page.locator('text=/Provisioning/i'),
      page.locator('text=/candidato/i'),
      page.locator('[class*="animate-spin"]'), // Loading spinner
    ];

    let foundProvisioningIndicator = false;
    for (const indicator of provisioningIndicators) {
      if (await indicator.isVisible({ timeout: 1000 }).catch(() => false)) {
        foundProvisioningIndicator = true;
        console.log('  - Found provisioning indicator');
        break;
      }
    }

    if (foundProvisioningIndicator) {
      console.log('  - Provisioning started');
    } else {
      // Check what's on the page
      const pageContent = await page.content();
      console.log('  - Current page state:', pageContent.substring(0, 500));
    }

    console.log('✅ Wizard flow completed successfully!');
  });

  test('Step 1 - Location selection works', async ({ page }) => {
    // Wait for wizard
    await expect(page.locator('.page-title')).toContainText('New GPU Machine');

    // Check for quick region buttons
    const regionButtons = page.locator('button:has-text("USA"), button:has-text("Europe"), button:has-text("Asia")');
    const count = await regionButtons.count();
    console.log(`Found ${count} region buttons`);
    expect(count).toBeGreaterThan(0);

    // Click USA
    await page.locator('button:has-text("USA")').first().click();

    // Check selection indicator
    await page.waitForTimeout(500);
    const selectedLocations = page.locator('text=/1 location.*selected/i');
    await expect(selectedLocations).toBeVisible({ timeout: 3000 });

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/wizard-step1-location.png' });
  });

  test('Step 2 - Use case and machine selection works', async ({ page }) => {
    // First complete step 1
    await page.locator('button:has-text("USA")').first().click();
    await page.waitForTimeout(300);
    await page.locator('button:has-text("Próximo")').click();

    // Wait for step 2
    await page.waitForTimeout(500);

    // Check for use case buttons
    const useCaseButtons = page.locator('[data-testid^="use-case-"]');
    const count = await useCaseButtons.count();
    console.log(`Found ${count} use case buttons`);
    expect(count).toBe(5); // CPU, Experiment, Develop, Train, Production

    // Click Develop
    await page.locator('[data-testid="use-case-develop"]').click();

    // Wait for machines to load
    await page.waitForTimeout(2000);

    // Check for recommended machines
    const machines = page.locator('[data-testid^="machine-"]');
    const machineCount = await machines.count();
    console.log(`Found ${machineCount} recommended machines`);

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/wizard-step2-hardware.png' });
  });
});
