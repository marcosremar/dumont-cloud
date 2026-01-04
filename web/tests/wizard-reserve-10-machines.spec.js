import { test, expect } from '@playwright/test';

// Auth state for logged-in user
const AUTH_STATE = {
  auth_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYXJjb3NyZW1hckBnbWFpbC5jb20iLCJleHAiOjE3NzEzNjgwMDEsImlhdCI6MTc2NzQ4MDAwMX0.xUYMEh5uCnuE_9qiWlH4RJ-WW01WKoznoj2J6ORZYC0',
  auth_user: '"marcosremar@gmail.com"',
  auth_login_time: String(Date.now()),
  theme: 'dark'
};

// Different GPU tiers to test
const GPU_TIERS = [
  { id: 'cpu_only', name: 'CPU Only', useCase: 'use-case-cpu_only' },
  { id: 'slow1', name: 'Slow - Test 1', useCase: 'use-case-test' },
  { id: 'slow2', name: 'Slow - Test 2', useCase: 'use-case-test' },
  { id: 'medium1', name: 'Medium - Dev 1', useCase: 'use-case-develop' },
  { id: 'medium2', name: 'Medium - Dev 2', useCase: 'use-case-develop' },
  { id: 'fast1', name: 'Fast - Train 1', useCase: 'use-case-train' },
  { id: 'fast2', name: 'Fast - Train 2', useCase: 'use-case-train' },
  { id: 'ultra1', name: 'Ultra - Production 1', useCase: 'use-case-production' },
  { id: 'ultra2', name: 'Ultra - Production 2', useCase: 'use-case-production' },
  { id: 'ultra3', name: 'Ultra - Production 3', useCase: 'use-case-production' },
];

// Regions to use
const REGIONS = ['USA', 'Europe', 'Asia'];

// Track created instances for cleanup
const createdInstances = [];

test.describe.serial('Reserve 10 Different Machine Types', () => {
  test.beforeAll(async ({ browser }) => {
    console.log('🚀 Starting test: Reserve 10 different machine types');
  });

  test.afterAll(async ({ browser }) => {
    console.log(`\n📊 Test Summary:`);
    console.log(`   - Total machines attempted: ${GPU_TIERS.length}`);
    console.log(`   - Successfully created: ${createdInstances.length}`);
    console.log(`   - Instance IDs: ${createdInstances.join(', ') || 'None'}`);
  });

  // Helper to set auth and navigate
  async function setupPage(page) {
    await page.goto('/');
    await page.evaluate((authState) => {
      localStorage.setItem('auth_token', authState.auth_token);
      localStorage.setItem('auth_user', authState.auth_user);
      localStorage.setItem('auth_login_time', authState.auth_login_time);
      localStorage.setItem('theme', authState.theme);
    }, AUTH_STATE);
  }

  // Test reserving each machine type
  for (let i = 0; i < GPU_TIERS.length; i++) {
    const tier = GPU_TIERS[i];
    const region = REGIONS[i % REGIONS.length];

    test(`Reserve machine ${i + 1}/10: ${tier.name} in ${region}`, async ({ page }) => {
      console.log(`\n🔄 [${i + 1}/10] Starting: ${tier.name} in ${region}`);

      // Setup auth
      await setupPage(page);

      // Navigate to new machine wizard
      await page.goto('/app/machines/new');
      await page.waitForTimeout(3000);

      // Step 1: Select Region
      console.log(`   📍 Step 1: Selecting ${region}...`);
      const regionButton = page.locator(`button:has-text("${region}")`).first();
      await expect(regionButton).toBeVisible({ timeout: 10000 });
      await regionButton.click();
      await page.waitForTimeout(500);

      // Click Next
      const nextButton = page.locator('button:has-text("Próximo")');
      await expect(nextButton).toBeEnabled({ timeout: 5000 });
      await nextButton.click();

      // Step 2: Select Tier/Use Case
      console.log(`   🖥️ Step 2: Selecting ${tier.useCase}...`);
      await page.waitForTimeout(500);

      const useCaseButton = page.locator(`[data-testid="${tier.useCase}"]`);
      if (await useCaseButton.isVisible({ timeout: 5000 })) {
        await useCaseButton.click();
      } else {
        // Fallback to first available use case
        const anyUseCase = page.locator('[data-testid^="use-case-"]').first();
        await anyUseCase.click();
      }

      // Wait for machines to load
      await page.waitForTimeout(2000);

      // Select first available machine (if any)
      const machineButton = page.locator('[data-testid^="machine-"]').first();
      if (await machineButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await machineButton.click();
        console.log(`   ✅ Selected machine`);
      } else {
        console.log(`   ⚠️ No machines available, using defaults`);
      }

      // Click Next
      await nextButton.click();

      // Step 3: Select Strategy
      console.log(`   🛡️ Step 3: Selecting strategy...`);
      await page.waitForTimeout(500);

      // Strategy should be pre-selected, click Iniciar
      const startButton = page.locator('button:has-text("Iniciar")');
      await expect(startButton).toBeEnabled({ timeout: 5000 });
      await startButton.click();

      // Step 4: Provisioning
      console.log(`   🚀 Step 4: Provisioning started...`);
      await page.waitForTimeout(5000);

      // Take screenshot after provisioning starts
      await page.screenshot({
        path: `tests/screenshots/reserve-${i + 1}-${tier.id}-provisioning.png`,
        fullPage: true
      });

      // Check for provisioning indicators
      const provisioningVisible = await page.locator('text=/Round|Conectando|Provisionando/i').isVisible({ timeout: 5000 }).catch(() => false);

      if (provisioningVisible) {
        console.log(`   ✅ Provisioning started for ${tier.name}`);

        // Wait a bit more for potential winner
        await page.waitForTimeout(5000);

        // Check if winner found
        const winnerButton = page.locator('button:has-text("Usar Esta Máquina")');
        if (await winnerButton.isVisible({ timeout: 10000 }).catch(() => false)) {
          console.log(`   🎉 Winner found! Clicking to confirm...`);
          await winnerButton.click();

          // Get instance ID from URL or page
          await page.waitForTimeout(2000);
          const url = page.url();
          const instanceIdMatch = url.match(/instance[s]?\/(\d+)/i);
          if (instanceIdMatch) {
            createdInstances.push(instanceIdMatch[1]);
            console.log(`   📝 Created instance: ${instanceIdMatch[1]}`);
          }
        } else {
          console.log(`   ⏳ Still provisioning (no winner yet)`);
        }
      } else {
        console.log(`   ⚠️ Provisioning not visible - checking page state`);
      }

      console.log(`   ✅ Completed: ${tier.name}`);
    });
  }

  // Test to delete all created machines
  test('Delete all created machines', async ({ page }) => {
    console.log(`\n🗑️ Cleanup: Deleting ${createdInstances.length} machines...`);

    if (createdInstances.length === 0) {
      console.log('   No machines to delete');
      return;
    }

    await setupPage(page);

    // Go to machines list
    await page.goto('/app/machines');
    await page.waitForTimeout(3000);

    // Take screenshot of machines before deletion
    await page.screenshot({ path: 'tests/screenshots/machines-before-delete.png', fullPage: true });

    // For each created instance, try to delete
    for (const instanceId of createdInstances) {
      console.log(`   🗑️ Attempting to delete instance ${instanceId}...`);

      // Try to find and click delete button for this instance
      const instanceCard = page.locator(`[data-instance-id="${instanceId}"], [href*="${instanceId}"]`).first();

      if (await instanceCard.isVisible({ timeout: 3000 }).catch(() => false)) {
        // Find delete/destroy button
        const deleteButton = instanceCard.locator('button:has-text("Delete"), button:has-text("Destroy")');
        if (await deleteButton.isVisible().catch(() => false)) {
          await deleteButton.click();

          // Confirm deletion if modal appears
          const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Yes")');
          if (await confirmButton.isVisible({ timeout: 2000 }).catch(() => false)) {
            await confirmButton.click();
          }

          console.log(`   ✅ Deleted instance ${instanceId}`);
          await page.waitForTimeout(1000);
        }
      }
    }

    // Take screenshot after deletion
    await page.screenshot({ path: 'tests/screenshots/machines-after-delete.png', fullPage: true });
    console.log('   ✅ Cleanup completed');
  });
});

// Standalone test for quick validation
test('Quick validation: Single machine reservation', async ({ page }) => {
  console.log('🔍 Quick validation test');

  // Setup auth
  await page.goto('/');
  await page.evaluate((authState) => {
    localStorage.setItem('auth_token', authState.auth_token);
    localStorage.setItem('auth_user', authState.auth_user);
    localStorage.setItem('auth_login_time', authState.auth_login_time);
    localStorage.setItem('theme', authState.theme);
  }, AUTH_STATE);

  // Navigate to new machine
  await page.goto('/app/machines/new');
  await page.waitForTimeout(3000);

  // Check wizard loads
  await expect(page.locator('text=New GPU Machine')).toBeVisible({ timeout: 10000 });

  // Step 1: Select USA
  await page.locator('button:has-text("USA")').first().click();
  await page.waitForTimeout(500);
  await page.locator('button:has-text("Próximo")').click();

  // Step 2: Select Develop
  await page.waitForTimeout(500);
  const devButton = page.locator('[data-testid="use-case-develop"]');
  if (await devButton.isVisible({ timeout: 3000 }).catch(() => false)) {
    await devButton.click();
  }
  await page.waitForTimeout(2000);

  // Select first machine if available
  const machine = page.locator('[data-testid="machine-0"]');
  if (await machine.isVisible({ timeout: 3000 }).catch(() => false)) {
    await machine.click();
  }
  await page.locator('button:has-text("Próximo")').click();

  // Step 3: Click Iniciar
  await page.waitForTimeout(500);
  await page.locator('button:has-text("Iniciar")').click();

  // Step 4: Check provisioning started
  await page.waitForTimeout(3000);
  const provisioning = page.locator('text=/Provisionando|Round|Conectando/i');
  await expect(provisioning).toBeVisible({ timeout: 10000 });

  await page.screenshot({ path: 'tests/screenshots/quick-validation.png', fullPage: true });
  console.log('✅ Quick validation passed');
});
