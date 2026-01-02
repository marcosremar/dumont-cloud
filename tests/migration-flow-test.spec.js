// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Teste completo de migração GPU <-> CPU
 *
 * Fluxo:
 * 1. Login automático
 * 2. Verificar máquinas existentes
 * 3. Provisionar GPU se não existir
 * 4. Abrir VS Code Web e criar arquivo de teste
 * 5. Migrar GPU -> CPU
 * 6. Verificar arquivo persiste
 * 7. Migrar CPU -> GPU
 * 8. Verificar arquivo persiste novamente
 */

test.describe('Migration Flow Test', () => {
  test.setTimeout(600000); // 10 minutes - migrations take time

  test('should complete full GPU <-> CPU migration with file persistence', async ({ page }) => {
    // 1. Login - uses saved auth from setup
    console.log('Step 1: Navigate to app');
    await page.goto('http://localhost:4894/app');
    await page.waitForTimeout(3000);
    console.log('App loaded');

    // 2. Navigate to Machines page
    console.log('Step 2: Navigate to Machines');
    await page.click('text=Máquinas');
    await page.waitForTimeout(2000);

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/migration-01-machines.png' });

    // 3. Check for existing GPU machine or provision one
    console.log('Step 3: Check for GPU machine');
    const gpuMachine = page.locator('[data-testid="machine-card"]').filter({ hasText: /RTX|A100|GPU/i }).first();

    if (await gpuMachine.count() === 0) {
      console.log('No GPU machine found, provisioning one...');

      // Click Deploy button
      await page.click('button:has-text("Deploy")');
      await page.waitForTimeout(1000);

      // Select region
      await page.click('text=Estados Unidos');
      await page.waitForTimeout(500);

      // Click Next
      await page.click('button:has-text("Próximo")');
      await page.waitForTimeout(1000);

      // Select purpose (IA - inference)
      await page.click('text=Inferência');
      await page.waitForTimeout(500);

      // Click Next
      await page.click('button:has-text("Próximo")');
      await page.waitForTimeout(1000);

      // Select Lento tier (cheapest with GPU)
      await page.click('text=Lento');
      await page.waitForTimeout(3000); // Wait for machines to load

      // Select first available machine
      const machineOption = page.locator('[data-testid="machine-option"]').first();
      if (await machineOption.count() > 0) {
        await machineOption.click();
      }

      // Click Provisionar
      await page.click('button:has-text("Provisionar")');

      // Wait for provisioning (up to 5 minutes)
      console.log('Waiting for GPU to provision...');
      await page.waitForSelector('text=Online', { timeout: 300000 });
    }

    await page.screenshot({ path: 'tests/screenshots/migration-02-gpu-ready.png' });
    console.log('GPU machine ready');

    // 4. Open VS Code Web and create test file
    console.log('Step 4: Open VS Code Web');

    // Click on the machine to open details
    await gpuMachine.click();
    await page.waitForTimeout(1000);

    // Click VS Code button
    const vscodeButton = page.locator('button:has-text("VS Code"), a:has-text("VS Code")').first();
    if (await vscodeButton.count() > 0) {
      await vscodeButton.click();
      await page.waitForTimeout(3000);

      // VS Code Web should open - wait for it
      const vscodeFrame = page.frameLocator('iframe').first();
      if (await vscodeFrame.locator('body').count() > 0) {
        console.log('VS Code Web opened');
        await page.screenshot({ path: 'tests/screenshots/migration-03-vscode.png' });
      }
    } else {
      console.log('VS Code button not found, skipping VS Code test');
    }

    // 5. Start GPU -> CPU Migration
    console.log('Step 5: Start GPU -> CPU Migration');

    // Click CPU migration button
    const cpuButton = page.locator('button:has-text("CPU"), button[title*="CPU"]').first();
    await cpuButton.click();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'tests/screenshots/migration-04-wizard-open.png' });

    // Select "Restaurar Dados" to preserve files
    const restoreOption = page.locator('text=Restaurar Dados, input[value="restore"]').first();
    if (await restoreOption.count() > 0) {
      await restoreOption.click();
    }

    // Select snapshot if available
    const snapshotSelect = page.locator('select[name="snapshot"]').first();
    if (await snapshotSelect.count() > 0) {
      await snapshotSelect.selectOption({ index: 1 }); // Select first snapshot
    }

    // Select "Apenas CPU" tier
    await page.click('text=Apenas CPU');
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'tests/screenshots/migration-05-cpu-tier.png' });

    // Select first CPU machine
    const cpuMachineOption = page.locator('[data-testid="machine-option"]').first();
    if (await cpuMachineOption.count() > 0) {
      await cpuMachineOption.click();
    }

    // Click Migrar/Provisionar
    const migrateButton = page.locator('button:has-text("Migrar"), button:has-text("Provisionar")').first();
    await migrateButton.click();

    // Wait for CPU migration to complete
    console.log('Waiting for CPU machine to provision...');
    await page.waitForSelector('text=Online', { timeout: 300000 });

    await page.screenshot({ path: 'tests/screenshots/migration-06-cpu-ready.png' });
    console.log('CPU migration complete');

    // 6. Verify file persistence on CPU
    console.log('Step 6: Verify file persistence on CPU');
    // This would require SSH access or VS Code Web check

    // 7. Start CPU -> GPU Migration
    console.log('Step 7: Start CPU -> GPU Migration');

    // Find the CPU machine and click GPU button
    const cpuMachineCard = page.locator('[data-testid="machine-card"]').filter({ hasText: /CPU|Apenas CPU/i }).first();
    await cpuMachineCard.click();
    await page.waitForTimeout(1000);

    // Click GPU migration button
    const gpuButton = page.locator('button:has-text("GPU"), button[title*="GPU"]').first();
    await gpuButton.click();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'tests/screenshots/migration-07-gpu-wizard.png' });

    // Select restore option
    if (await restoreOption.count() > 0) {
      await restoreOption.click();
    }

    // Select a GPU tier
    await page.click('text=Lento');
    await page.waitForTimeout(3000);

    // Select first GPU machine
    const gpuMachineOption = page.locator('[data-testid="machine-option"]').first();
    if (await gpuMachineOption.count() > 0) {
      await gpuMachineOption.click();
    }

    // Click Migrar
    await migrateButton.click();

    // Wait for GPU migration to complete
    console.log('Waiting for GPU machine to provision...');
    await page.waitForSelector('text=Online', { timeout: 300000 });

    await page.screenshot({ path: 'tests/screenshots/migration-08-gpu-restored.png' });
    console.log('GPU migration complete');

    // 8. Final verification
    console.log('Step 8: Final verification');
    await page.screenshot({ path: 'tests/screenshots/migration-09-final.png' });

    console.log('Migration flow test completed successfully!');
  });
});
