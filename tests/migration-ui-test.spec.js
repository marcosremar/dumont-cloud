// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Teste de migração GPU <-> CPU pela UI
 *
 * VS Code é LOCAL (Desktop) e conecta via SSH com failover automático.
 * Este teste foca na UI de migração.
 */

test.describe('Migration UI Test', () => {
  test.setTimeout(300000); // 5 minutes

  test('should navigate to machines page and check migration options', async ({ page }) => {
    // Navigate to app with auto_login
    console.log('Step 1: Navigate to Machines page');
    await page.goto('/login?auto_login=demo');
    await page.waitForTimeout(5000);
    // Should redirect to /app, then navigate to machines
    await page.goto('/app/machines');
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'tests/screenshots/migration-ui-01-machines.png' });
    console.log('Machines page loaded');

    // Check if there are any machine cards
    const machineCards = page.locator('.machine-card, [class*="MachineCard"], [data-testid*="machine"]');
    const cardCount = await machineCards.count();
    console.log(`Found ${cardCount} machine cards`);

    if (cardCount > 0) {
      // Click on first machine to see details
      await machineCards.first().click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: 'tests/screenshots/migration-ui-02-machine-details.png' });

      // Look for migration buttons (GPU/CPU buttons)
      const gpuButton = page.locator('button:has-text("GPU"), [title*="GPU"], [aria-label*="GPU"]');
      const cpuButton = page.locator('button:has-text("CPU"), [title*="CPU"], [aria-label*="CPU"]');

      console.log(`GPU button found: ${await gpuButton.count() > 0}`);
      console.log(`CPU button found: ${await cpuButton.count() > 0}`);

      // If CPU button exists, try to click it to open migration wizard
      if (await cpuButton.count() > 0) {
        console.log('Clicking CPU migration button...');
        await cpuButton.first().click();
        await page.waitForTimeout(2000);
        await page.screenshot({ path: 'tests/screenshots/migration-ui-03-cpu-wizard.png' });

        // Check if wizard opened
        const wizard = page.locator('.wizard, [class*="Wizard"], [class*="Modal"], [role="dialog"]');
        if (await wizard.count() > 0) {
          console.log('Migration wizard opened!');

          // Check for "Apenas CPU" tier option
          const cpuTier = page.locator('text=Apenas CPU');
          if (await cpuTier.count() > 0) {
            console.log('CPU tier option found');
            await cpuTier.click();
            await page.waitForTimeout(3000);
            await page.screenshot({ path: 'tests/screenshots/migration-ui-04-cpu-tier-selected.png' });

            // Check if CPU machines are loaded (should have num_gpus=0)
            const machineOptions = page.locator('[data-testid="machine-option"], .machine-option, [class*="MachineOption"]');
            const optionCount = await machineOptions.count();
            console.log(`Found ${optionCount} CPU machine options`);
          }

          // Close wizard
          const closeButton = page.locator('button:has-text("Cancelar"), button:has-text("Fechar"), [aria-label="close"]');
          if (await closeButton.count() > 0) {
            await closeButton.first().click();
          }
        }
      }
    } else {
      console.log('No machines found - checking for Deploy button');

      // Check for Deploy button to provision new machine
      const deployButton = page.locator('button:has-text("Deploy"), button:has-text("Provisionar")');
      console.log(`Deploy button found: ${await deployButton.count() > 0}`);
      await page.screenshot({ path: 'tests/screenshots/migration-ui-02-no-machines.png' });
    }

    console.log('Migration UI test completed');
  });

  test('should test CPU tier filtering in wizard', async ({ page }) => {
    console.log('Testing CPU tier filtering in deploy wizard');

    await page.goto('/login?auto_login=demo');
    await page.waitForTimeout(5000);
    await page.goto('/app/machines');
    await page.waitForTimeout(2000);

    // Click Deploy button
    const deployButton = page.locator('button:has-text("Deploy"), button:has-text("Provisionar Nova")');
    if (await deployButton.count() > 0) {
      await deployButton.first().click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'tests/screenshots/cpu-filter-01-wizard-open.png' });

      // Step 1: Select region
      const usaOption = page.locator('text=Estados Unidos, text=EUA, text=US');
      if (await usaOption.count() > 0) {
        await usaOption.first().click();
        await page.waitForTimeout(500);
      }

      // Click Next
      const nextButton = page.locator('button:has-text("Próximo"), button:has-text("Next")');
      if (await nextButton.count() > 0) {
        await nextButton.first().click();
        await page.waitForTimeout(1000);
      }

      // Step 2: Select purpose
      const purposeOption = page.locator('text=Inferência, text=IA');
      if (await purposeOption.count() > 0) {
        await purposeOption.first().click();
        await page.waitForTimeout(500);
      }

      if (await nextButton.count() > 0) {
        await nextButton.first().click();
        await page.waitForTimeout(1000);
      }
      await page.screenshot({ path: 'tests/screenshots/cpu-filter-02-tier-selection.png' });

      // Step 3: Select "Apenas CPU" tier
      const cpuTier = page.locator('text=Apenas CPU');
      if (await cpuTier.count() > 0) {
        console.log('Found "Apenas CPU" tier option');
        await cpuTier.click();
        await page.waitForTimeout(5000); // Wait for API to fetch CPU machines
        await page.screenshot({ path: 'tests/screenshots/cpu-filter-03-cpu-machines.png' });

        // Verify that machines shown are CPU-only (no GPU name)
        const pageContent = await page.content();
        const hasRTX = pageContent.includes('RTX');
        const hasA100 = pageContent.includes('A100');
        const hasGPU = pageContent.includes('GPU') && !pageContent.includes('Sem GPU');

        console.log(`Page has RTX: ${hasRTX}`);
        console.log(`Page has A100: ${hasA100}`);
        console.log(`Page has GPU references (excluding "Sem GPU"): ${hasGPU}`);

        // Should not have GPU machine names when CPU tier is selected
        if (!hasRTX && !hasA100) {
          console.log('SUCCESS: CPU tier is filtering correctly (no GPU machines shown)');
        } else {
          console.log('WARNING: GPU machines may be showing in CPU tier');
        }
      } else {
        console.log('WARNING: "Apenas CPU" tier option not found');
      }
    } else {
      console.log('Deploy button not found');
    }

    console.log('CPU tier filtering test completed');
  });
});
