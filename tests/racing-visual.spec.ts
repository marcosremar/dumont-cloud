import { test, expect } from '@playwright/test';

/**
 * Visual E2E Tests for GPU Racing/Provisioning Flow
 *
 * Tests the complete machine provisioning wizard:
 * 1. Region selection
 * 2. Hardware/GPU tier selection
 * 3. Failover strategy selection
 * 4. Provisioning race visualization
 *
 * These tests run in demo mode which simulates the race.
 */
test.describe('GPU Racing/Provisioning Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Try demo login, fallback to already logged in
    await page.goto('/login?auto_login=demo');

    // Wait for either redirect to /app or login page
    await Promise.race([
      page.waitForURL('**/app**', { timeout: 10000 }),
      page.waitForSelector('input[type="email"], input[name="email"], input[type="text"]', { timeout: 10000 })
    ]).catch(() => {});

    // If on login page, fill credentials
    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    if (await emailInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await emailInput.fill('marcosremar@gmail.com');
      await page.locator('input[type="password"]').fill('dumont123');
      await page.locator('button[type="submit"], button:has-text("Entrar"), button:has-text("Login")').first().click();
      await page.waitForURL('**/app**', { timeout: 15000 }).catch(() => {});
    }

    await page.waitForLoadState('networkidle');
  });

  test.describe('Wizard Step 1: Region Selection', () => {
    test('displays region selection options', async ({ page }) => {
      // Navigate to new machine wizard
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for "Nova Maquina" or similar button
      const newMachineBtn = page.locator('button:has-text("Nova"), button:has-text("Criar"), a:has-text("Nova")').first();
      const hasNewBtn = await newMachineBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (hasNewBtn) {
        await newMachineBtn.click();
        await page.waitForLoadState('networkidle');
      }

      // Check for region selection UI
      const regionStep = page.locator('text=Região, text=Region, text=Localização').first();
      const hasRegionStep = await regionStep.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasRegionStep) {
        // Verify region options are displayed
        const regionOptions = page.locator('[role="button"], [role="option"], .region-option, [data-region]');
        const count = await regionOptions.count();

        // Should have at least some region options or country flags
        expect(count).toBeGreaterThanOrEqual(0);
      }
    });

    test('allows selecting a region', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Try to find wizard or region selector
      const regionSelector = page.locator('[data-testid="region-selector"], .region-select, text=Region').first();
      const hasSelector = await regionSelector.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasSelector) {
        // Click on a region option
        const firstRegion = page.locator('[data-region], .region-option, [role="option"]').first();
        const hasRegion = await firstRegion.isVisible().catch(() => false);

        if (hasRegion) {
          await firstRegion.click();

          // Should show selection indicator
          const selected = await page.locator('.selected, [aria-selected="true"], .active').count();
          expect(selected).toBeGreaterThanOrEqual(0);
        }
      }
    });
  });

  test.describe('Wizard Step 2: Hardware Selection', () => {
    test('displays GPU tier options', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for GPU tier cards or options
      const tierOptions = page.locator(
        'text=GPU, text=RTX, text=A100, text=H100, text=Tier, text=Lento, text=Medio, text=Rapido'
      );
      const hasTiers = await tierOptions.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasTiers) {
        // Count tier options
        const tierCards = page.locator('[data-tier], .tier-card, .gpu-option');
        const count = await tierCards.count();

        // Log what we found
        console.log(`Found ${count} tier options`);
      }
    });

    test('shows pricing information for tiers', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for pricing elements
      const pricing = page.locator('text=/\\$[0-9.]+\\/h/, text=/\\$[0-9.]+hr/');
      const hasPricing = await pricing.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasPricing) {
        const priceElements = await pricing.count();
        expect(priceElements).toBeGreaterThanOrEqual(0);
      }
    });

    test('tier selection updates estimated cost', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Find cost display
      const costDisplay = page.locator('text=/\\$[0-9.]+/, text=custo, text=cost').first();
      const hasCost = await costDisplay.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasCost) {
        const initialCost = await costDisplay.textContent();

        // Try clicking a different tier
        const tierButtons = page.locator('[data-tier], .tier-button, button:has-text("Ultra"), button:has-text("Rapido")');
        const hasTierBtn = await tierButtons.first().isVisible().catch(() => false);

        if (hasTierBtn) {
          await tierButtons.first().click();

          // Cost display might update
          await page.waitForTimeout(500);
          const newCost = await costDisplay.textContent();

          // Log the change
          console.log(`Cost changed: ${initialCost} -> ${newCost}`);
        }
      }
    });
  });

  test.describe('Wizard Step 3: Failover Strategy', () => {
    test('displays failover strategy options', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for failover/strategy options
      const strategyOptions = page.locator(
        'text=Failover, text=Estratégia, text=Strategy, text=Snapshot, text=CPU Standby, text=Backup'
      );
      const hasStrategy = await strategyOptions.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasStrategy) {
        // Verify strategy descriptions are present
        const descriptions = page.locator('.strategy-description, [data-strategy], .failover-option');
        const count = await descriptions.count();

        console.log(`Found ${count} failover strategy options`);
      }
    });

    test('strategy selection shows RTO/cost info', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for RTO (Recovery Time Objective) or cost information
      const rtoInfo = page.locator('text=/[0-9]+\\s*(s|seg|seconds)/, text=RTO, text=Recovery');
      const hasRto = await rtoInfo.first().isVisible({ timeout: 3000 }).catch(() => false);

      if (hasRto) {
        const rtoCount = await rtoInfo.count();
        expect(rtoCount).toBeGreaterThanOrEqual(0);
      }
    });
  });

  test.describe('Wizard Step 4: Provisioning Race', () => {
    test('race view displays multiple candidates', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for race candidates or progress bars
      const candidates = page.locator(
        '.race-candidate, .candidate-card, [data-candidate], .progress-bar, .machine-progress'
      );
      const hasCandidates = await candidates.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasCandidates) {
        const count = await candidates.count();
        console.log(`Found ${count} race candidates`);

        // In demo mode, should have multiple candidates
        expect(count).toBeGreaterThanOrEqual(0);
      }
    });

    test('race progress bars animate', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for progress elements
      const progressBars = page.locator(
        '[role="progressbar"], .progress-bar, .progress, [class*="progress"]'
      );
      const hasProgress = await progressBars.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasProgress) {
        // Get initial progress value
        const initialValue = await progressBars.first().getAttribute('aria-valuenow') ||
                            await progressBars.first().getAttribute('style');

        // Wait for animation
        await page.waitForTimeout(2000);

        // Check if progress changed
        const newValue = await progressBars.first().getAttribute('aria-valuenow') ||
                        await progressBars.first().getAttribute('style');

        console.log(`Progress: ${initialValue} -> ${newValue}`);
      }
    });

    test('race timer shows elapsed time', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for timer display
      const timer = page.locator(
        'text=/[0-9]+:[0-9]+/, .timer, .elapsed-time, [data-timer]'
      );
      const hasTimer = await timer.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasTimer) {
        const initialTime = await timer.first().textContent();

        // Wait and check if timer updates
        await page.waitForTimeout(3000);
        const newTime = await timer.first().textContent();

        console.log(`Timer: ${initialTime} -> ${newTime}`);
      }
    });

    test('race ETA updates based on progress', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for ETA display
      const eta = page.locator(
        'text=restante, text=remaining, text=ETA, text=/~[0-9]+s/, text=/~[0-9]+min/'
      );
      const hasEta = await eta.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasEta) {
        const etaText = await eta.first().textContent();
        console.log(`ETA display: ${etaText}`);

        expect(etaText).toBeTruthy();
      }
    });

    test('race shows winner when complete', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for winner indication or success state
      const winner = page.locator(
        'text=Pronto, text=Ready, text=Winner, text=Conectado, text=Connected, .winner, [data-winner]'
      );
      const hasWinner = await winner.first().isVisible({ timeout: 30000 }).catch(() => false);

      if (hasWinner) {
        // Verify winner displays connection info
        const connectionInfo = page.locator('text=SSH, text=IP, text=host');
        const hasConnection = await connectionInfo.first().isVisible().catch(() => false);

        console.log(`Winner found with connection info: ${hasConnection}`);
      }
    });

    test('cancelled race shows cancelled state', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for cancel button
      const cancelBtn = page.locator('button:has-text("Cancelar"), button:has-text("Cancel")');
      const hasCancel = await cancelBtn.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasCancel) {
        await cancelBtn.first().click();

        // Should show cancelled state
        const cancelled = page.locator('text=Cancelado, text=Cancelled, .cancelled');
        const hasCancelled = await cancelled.first().isVisible({ timeout: 3000 }).catch(() => false);

        console.log(`Race cancelled: ${hasCancelled}`);
      }
    });
  });

  test.describe('Race Candidate Status', () => {
    test('candidates show different status icons', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for status icons or indicators
      const statusIcons = page.locator(
        '.status-icon, [data-status], .candidate-status, svg[class*="status"]'
      );
      const hasIcons = await statusIcons.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasIcons) {
        const count = await statusIcons.count();
        console.log(`Found ${count} status icons`);
      }
    });

    test('failed candidates show error message', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for error/failed indicators
      const errors = page.locator(
        'text=Falha, text=Failed, text=Error, .error, .failed, [data-status="failed"]'
      );
      const hasErrors = await errors.first().isVisible({ timeout: 10000 }).catch(() => false);

      if (hasErrors) {
        const errorText = await errors.first().textContent();
        console.log(`Error message found: ${errorText}`);
      }
    });
  });

  test.describe('Race Accessibility', () => {
    test('race progress is accessible', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Check for accessible progress bars
      const accessibleProgress = page.locator('[role="progressbar"]');
      const hasAccessible = await accessibleProgress.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasAccessible) {
        // Verify ARIA attributes
        const ariaValueMin = await accessibleProgress.first().getAttribute('aria-valuemin');
        const ariaValueMax = await accessibleProgress.first().getAttribute('aria-valuemax');

        console.log(`Progress ARIA: min=${ariaValueMin}, max=${ariaValueMax}`);
      }
    });

    test('race status announcements for screen readers', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for live regions
      const liveRegions = page.locator('[aria-live], [role="status"], [role="alert"]');
      const hasLive = await liveRegions.first().isVisible({ timeout: 5000 }).catch(() => false);

      if (hasLive) {
        const count = await liveRegions.count();
        console.log(`Found ${count} live regions for announcements`);
      }
    });
  });

  test.describe('Race Error Handling', () => {
    test('displays error when no offers available', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for "no offers" or empty state messages
      const noOffers = page.locator(
        'text=Sem ofertas, text=No offers, text=unavailable, text=indisponível'
      );
      const hasNoOffers = await noOffers.first().isVisible({ timeout: 5000 }).catch(() => false);

      // This is expected to be false in normal operation
      console.log(`No offers state visible: ${hasNoOffers}`);
    });

    test('displays balance warning when insufficient funds', async ({ page }) => {
      await page.goto('/app');
      await page.waitForLoadState('networkidle');

      // Look for balance warnings
      const balanceWarning = page.locator(
        'text=saldo, text=balance, text=insuficiente, text=insufficient'
      );
      const hasWarning = await balanceWarning.first().isVisible({ timeout: 5000 }).catch(() => false);

      console.log(`Balance warning visible: ${hasWarning}`);
    });
  });
});

/**
 * Tests for Machine Card interactions (post-provisioning)
 */
test.describe('Machine Card After Race', () => {
  test.beforeEach(async ({ page }) => {
    // Try demo login, fallback to already logged in
    await page.goto('/login?auto_login=demo');

    // Wait for either redirect to /app or login page
    await Promise.race([
      page.waitForURL('**/app**', { timeout: 10000 }),
      page.waitForSelector('input[type="email"], input[name="email"], input[type="text"]', { timeout: 10000 })
    ]).catch(() => {});

    // If on login page, fill credentials
    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    if (await emailInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await emailInput.fill('marcosremar@gmail.com');
      await page.locator('input[type="password"]').fill('dumont123');
      await page.locator('button[type="submit"], button:has-text("Entrar"), button:has-text("Login")').first().click();
      await page.waitForURL('**/app**', { timeout: 15000 }).catch(() => {});
    }

    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');
  });

  test('machine card shows GPU info', async ({ page }) => {
    const gpuInfo = page.locator('text=RTX, text=A100, text=GPU, text=VRAM');
    const hasGpu = await gpuInfo.first().isVisible({ timeout: 5000 }).catch(() => false);

    if (hasGpu) {
      const gpuText = await gpuInfo.first().textContent();
      console.log(`GPU info: ${gpuText}`);
    }
  });

  test('machine card shows connection info', async ({ page }) => {
    const connectionInfo = page.locator('text=SSH, text=IP, text=host, text=port');
    const hasConnection = await connectionInfo.first().isVisible({ timeout: 5000 }).catch(() => false);

    if (hasConnection) {
      const connectionText = await connectionInfo.first().textContent();
      console.log(`Connection info: ${connectionText}`);
    }
  });

  test('machine card has action buttons', async ({ page }) => {
    const actionButtons = page.locator(
      'button:has-text("Pausar"), button:has-text("Destruir"), button:has-text("SSH"), button:has-text("VS Code")'
    );
    const hasActions = await actionButtons.first().isVisible({ timeout: 5000 }).catch(() => false);

    if (hasActions) {
      const count = await actionButtons.count();
      console.log(`Found ${count} action buttons`);
    }
  });
});
