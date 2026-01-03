// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Teste de Filtragem de Regiões
 * Verifica se a seleção de região funciona corretamente no wizard de provisionamento
 */

test.describe('Region Filter', () => {
  test.beforeEach(async ({ page }) => {
    // Go directly to app (auth is handled by storageState from auth.setup.js)
    await page.goto('/app');

    // Wait for dashboard to load
    await expect(page.locator('text=Nova Instância GPU')).toBeVisible({ timeout: 15000 });
  });

  test('should filter GPUs by Europa region', async ({ page }) => {
    // Select Europa region
    await page.getByTestId('region-europa').click();

    // Verify region is selected
    await expect(page.locator('text=Europa').first()).toBeVisible();

    // Click Next to go to hardware selection
    await page.getByRole('button', { name: 'Próximo' }).click();

    // Select a use case to see GPUs
    await page.getByTestId('use-case-develop').click();

    // Verify GPUs are displayed - wait for loading to complete
    await expect(page.locator('text=Seleção de GPU')).toBeVisible({ timeout: 10000 });

    // Wait for loading to finish (spinner disappears or GPU cards appear)
    await expect(page.locator('text=Buscando máquinas')).toBeHidden({ timeout: 30000 });

    // Now check for GPU cards with price
    await expect(page.locator('text=/\\$\\d+\\.\\d+\\/h/').first()).toBeVisible({ timeout: 20000 });
  });

  test('should filter GPUs by Ásia region', async ({ page }) => {
    // Select Ásia region
    await page.getByTestId('region-asia').click();

    // Verify region is selected
    await expect(page.locator('text=Ásia').first()).toBeVisible();

    // Click Next
    await page.getByRole('button', { name: 'Próximo' }).click();

    // Select use case
    await page.getByTestId('use-case-develop').click();

    // Verify GPUs are displayed
    await expect(page.locator('text=Seleção de GPU')).toBeVisible({ timeout: 10000 });

    // Wait for loading to finish
    await expect(page.locator('text=Buscando máquinas')).toBeHidden({ timeout: 30000 });

    // Check for GPU cards with price
    await expect(page.locator('text=/\\$\\d+\\.\\d+\\/h/').first()).toBeVisible({ timeout: 20000 });
  });

  test('should filter GPUs by EUA region', async ({ page }) => {
    // Select EUA region
    await page.getByTestId('region-eua').click();

    // Verify region is selected
    await expect(page.locator('text=EUA').first()).toBeVisible();

    // Click Next
    await page.getByRole('button', { name: 'Próximo' }).click();

    // Select use case
    await page.getByTestId('use-case-develop').click();

    // Verify GPUs are displayed
    await expect(page.locator('text=Seleção de GPU')).toBeVisible({ timeout: 10000 });

    // Wait for loading to finish
    await expect(page.locator('text=Buscando máquinas')).toBeHidden({ timeout: 30000 });

    // Check for GPU cards with price
    await expect(page.locator('text=/\\$\\d+\\.\\d+\\/h/').first()).toBeVisible({ timeout: 20000 });
  });
});
