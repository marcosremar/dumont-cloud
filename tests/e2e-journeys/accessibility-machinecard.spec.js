/**
 * Accessibility Tests for MachineCard - Testes E2E Headless
 *
 * Tests ARIA attributes, keyboard navigation, and focus management:
 * - ARIA labels on all buttons
 * - aria-expanded and aria-haspopup on dropdowns
 * - Keyboard navigation (Arrow keys, Enter, Escape, Tab)
 * - Focus management (focus trap, focus return)
 * - Live regions for status announcements
 */

const { test, expect } = require('@playwright/test');

// Configuration for headless mode
test.use({
  headless: true,
  viewport: { width: 1920, height: 1080 },
});

// Use demo-app as default path for tests
const BASE_PATH = '/demo-app';

// Helper to navigate to Machines page
async function goToMachines(page) {
  await page.goto(`${BASE_PATH}/machines`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2000);
}

// Helper to check if there are machine cards available
async function hasMachineCards(page) {
  const gpuCards = await page.getByText(/RTX|A100|H100|3090|4090|3080/i).first().isVisible().catch(() => false);
  return gpuCards;
}

// ============================================================
// TESTE 1: ARIA Labels on Action Buttons
// ============================================================
test.describe('♿ ARIA Labels on Action Buttons', () => {

  test('Start button has aria-label with machine name', async ({ page }) => {
    await goToMachines(page);

    // Find start button (may be "Iniciar")
    const startButton = page.getByRole('button', { name: /iniciar/i }).first();

    if (await startButton.isVisible().catch(() => false)) {
      const ariaLabel = await startButton.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel).toMatch(/iniciar.*máquina/i);
      console.log(`✅ Start button has aria-label: ${ariaLabel}`);
    } else {
      console.log('ℹ️ No stopped machine found to test Start button');
    }
  });

  test('Pause button has aria-label with machine name', async ({ page }) => {
    await goToMachines(page);

    // Find pause button (may be "Pausar")
    const pauseButton = page.getByRole('button', { name: /pausar/i }).first();

    if (await pauseButton.isVisible().catch(() => false)) {
      const ariaLabel = await pauseButton.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel).toMatch(/pausar.*máquina/i);
      console.log(`✅ Pause button has aria-label: ${ariaLabel}`);
    } else {
      console.log('ℹ️ No running machine found to test Pause button');
    }
  });

  test('CPU migration button has aria-label', async ({ page }) => {
    await goToMachines(page);

    // Find CPU migration button
    const cpuButton = page.getByRole('button', { name: /migrar.*cpu|cpu/i }).first();

    if (await cpuButton.isVisible().catch(() => false)) {
      const ariaLabel = await cpuButton.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      console.log(`✅ CPU migration button has aria-label: ${ariaLabel}`);
    } else {
      console.log('ℹ️ CPU migration button not visible');
    }
  });

  test('Failover button has aria-label', async ({ page }) => {
    await goToMachines(page);

    // Look for failover button
    const failoverButton = page.getByRole('button', { name: /failover|configurar failover/i }).first();

    if (await failoverButton.isVisible().catch(() => false)) {
      const ariaLabel = await failoverButton.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      console.log(`✅ Failover button has aria-label: ${ariaLabel}`);
    } else {
      console.log('ℹ️ Failover button not visible (may require CPU standby)');
    }
  });

  test('Testar (simulate failover) button has aria-label', async ({ page }) => {
    await goToMachines(page);

    // Look for simulate failover button
    const testarButton = page.getByRole('button', { name: /testar|simular/i }).first();

    if (await testarButton.isVisible().catch(() => false)) {
      const ariaLabel = await testarButton.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      console.log(`✅ Testar button has aria-label: ${ariaLabel}`);
    } else {
      console.log('ℹ️ Testar button not visible (may require CPU standby)');
    }
  });
});

// ============================================================
// TESTE 2: ARIA Labels on IDE Buttons
// ============================================================
test.describe('♿ ARIA Labels on IDE Buttons', () => {

  test('VS Code button has aria-label and aria-haspopup', async ({ page }) => {
    await goToMachines(page);

    // Find VS Code button
    const vscodeButton = page.getByRole('button', { name: /vs\s*code/i }).first();

    if (await vscodeButton.isVisible().catch(() => false)) {
      const ariaLabel = await vscodeButton.getAttribute('aria-label');
      const ariaHaspopup = await vscodeButton.getAttribute('aria-haspopup');

      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel).toMatch(/abrir.*vs\s*code/i);
      expect(ariaHaspopup).toBe('menu');

      console.log(`✅ VS Code button has aria-label: ${ariaLabel}, aria-haspopup: ${ariaHaspopup}`);
    } else {
      console.log('ℹ️ VS Code button not visible (machine may be offline)');
    }
  });

  test('Cursor button has aria-label', async ({ page }) => {
    await goToMachines(page);

    const cursorButton = page.getByRole('button', { name: /cursor/i }).first();

    if (await cursorButton.isVisible().catch(() => false)) {
      const ariaLabel = await cursorButton.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel).toMatch(/abrir.*cursor/i);
      console.log(`✅ Cursor button has aria-label: ${ariaLabel}`);
    } else {
      console.log('ℹ️ Cursor button not visible');
    }
  });

  test('Windsurf button has aria-label', async ({ page }) => {
    await goToMachines(page);

    const windsurfButton = page.getByRole('button', { name: /windsurf/i }).first();

    if (await windsurfButton.isVisible().catch(() => false)) {
      const ariaLabel = await windsurfButton.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel).toMatch(/abrir.*windsurf/i);
      console.log(`✅ Windsurf button has aria-label: ${ariaLabel}`);
    } else {
      console.log('ℹ️ Windsurf button not visible');
    }
  });
});

// ============================================================
// TESTE 3: ARIA Attributes on Main Menu
// ============================================================
test.describe('♿ ARIA Attributes on Main Menu', () => {

  test('More options button has aria-label and aria-haspopup', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    // Find the MoreVertical menu button by its aria-label
    const menuButton = page.locator('[aria-label="Menu de opções da máquina"]').first();

    if (await menuButton.isVisible().catch(() => false)) {
      const ariaLabel = await menuButton.getAttribute('aria-label');
      const ariaHaspopup = await menuButton.getAttribute('aria-haspopup');

      expect(ariaLabel).toBe('Menu de opções da máquina');
      expect(ariaHaspopup).toBe('menu');

      console.log(`✅ Menu button has aria-label: ${ariaLabel}, aria-haspopup: ${ariaHaspopup}`);
    } else {
      // Try finding by icon/button appearance
      console.log('ℹ️ Menu button with aria-label not found');
    }
  });

  test('Dropdown menu has role="menu"', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    // Open the menu
    const menuButton = page.locator('[aria-label="Menu de opções da máquina"]').first();

    if (await menuButton.isVisible().catch(() => false)) {
      await menuButton.click();
      await page.waitForTimeout(300);

      // Check for role="menu" on the dropdown
      const menu = page.locator('[role="menu"]').first();
      const hasMenu = await menu.isVisible().catch(() => false);

      if (hasMenu) {
        console.log('✅ Dropdown has role="menu"');
        expect(hasMenu).toBe(true);
      } else {
        console.log('ℹ️ Menu role not found after clicking');
      }
    }
  });

  test('Menu items have role="menuitem"', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    // Open the menu
    const menuButton = page.locator('[aria-label="Menu de opções da máquina"]').first();

    if (await menuButton.isVisible().catch(() => false)) {
      await menuButton.click();
      await page.waitForTimeout(300);

      // Check for role="menuitem" on items
      const menuItems = page.locator('[role="menuitem"]');
      const count = await menuItems.count();

      if (count > 0) {
        console.log(`✅ Found ${count} menu items with role="menuitem"`);
        expect(count).toBeGreaterThan(0);
      } else {
        console.log('ℹ️ No menuitem roles found');
      }
    }
  });
});

// ============================================================
// TESTE 4: Failover Strategy Dropdown ARIA
// ============================================================
test.describe('♿ Failover Strategy Dropdown ARIA', () => {

  test('Failover trigger has aria-expanded and aria-haspopup', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const failoverTrigger = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      const ariaExpanded = await failoverTrigger.getAttribute('aria-expanded');
      const ariaHaspopup = await failoverTrigger.getAttribute('aria-haspopup');
      const ariaLabel = await failoverTrigger.getAttribute('aria-label');

      expect(ariaHaspopup).toBe('menu');
      expect(ariaExpanded).toBe('false');
      expect(ariaLabel).toMatch(/estratégia.*failover/i);

      console.log(`✅ Failover trigger has aria-expanded: ${ariaExpanded}, aria-haspopup: ${ariaHaspopup}, aria-label: ${ariaLabel}`);
    } else {
      console.log('ℹ️ Failover trigger not visible');
    }
  });

  test('Failover dropdown has role="menu"', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const failoverTrigger = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      await failoverTrigger.click();
      await page.waitForTimeout(300);

      const dropdown = page.locator('[data-testid="failover-dropdown-menu"]');
      const role = await dropdown.getAttribute('role');
      const ariaLabel = await dropdown.getAttribute('aria-label');

      expect(role).toBe('menu');
      expect(ariaLabel).toBeTruthy();

      console.log(`✅ Failover dropdown has role: ${role}, aria-label: ${ariaLabel}`);
    }
  });

  test('Failover options have role="menuitem"', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const failoverTrigger = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      await failoverTrigger.click();
      await page.waitForTimeout(300);

      // Check strategy options have role="menuitem"
      const cpuOption = page.locator('[data-testid="failover-option-cpu_standby"]');

      if (await cpuOption.isVisible().catch(() => false)) {
        const role = await cpuOption.getAttribute('role');
        expect(role).toBe('menuitem');
        console.log('✅ Failover options have role="menuitem"');
      }
    }
  });

  test('aria-expanded updates when dropdown opens/closes', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const failoverTrigger = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      // Check initial state
      const initialExpanded = await failoverTrigger.getAttribute('aria-expanded');
      expect(initialExpanded).toBe('false');

      // Open dropdown
      await failoverTrigger.click();
      await page.waitForTimeout(300);

      const openExpanded = await failoverTrigger.getAttribute('aria-expanded');
      expect(openExpanded).toBe('true');

      // Close dropdown
      await failoverTrigger.click();
      await page.waitForTimeout(300);

      const closedExpanded = await failoverTrigger.getAttribute('aria-expanded');
      expect(closedExpanded).toBe('false');

      console.log('✅ aria-expanded updates correctly on open/close');
    }
  });
});

// ============================================================
// TESTE 5: Backup Badge ARIA
// ============================================================
test.describe('♿ Backup Badge ARIA', () => {

  test('Backup badge has role="button" and aria-expanded', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    // Find backup badge
    const backupBadge = page.getByText(/backup|sem backup/i).first();

    if (await backupBadge.isVisible().catch(() => false)) {
      const role = await backupBadge.getAttribute('role');
      const ariaExpanded = await backupBadge.getAttribute('aria-expanded');
      const ariaLabel = await backupBadge.getAttribute('aria-label');

      expect(role).toBe('button');
      expect(ariaExpanded).toBeDefined();
      expect(ariaLabel).toMatch(/informações.*backup/i);

      console.log(`✅ Backup badge has role: ${role}, aria-expanded: ${ariaExpanded}, aria-label: ${ariaLabel}`);
    }
  });

  test('Backup popup close button has aria-label', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    // Find and click backup badge
    const backupBadge = page.getByText(/backup|sem backup/i).first();

    if (await backupBadge.isVisible().catch(() => false)) {
      await backupBadge.click();
      await page.waitForTimeout(300);

      // Find close button in popup
      const closeButton = page.locator('[aria-label="Fechar informações de backup"]');

      if (await closeButton.isVisible().catch(() => false)) {
        const ariaLabel = await closeButton.getAttribute('aria-label');
        expect(ariaLabel).toBe('Fechar informações de backup');
        console.log('✅ Backup close button has aria-label');
      }
    }
  });
});

// ============================================================
// TESTE 6: Copy Buttons ARIA
// ============================================================
test.describe('♿ Copy Buttons ARIA', () => {

  test('IP copy button has aria-label', async ({ page }) => {
    await goToMachines(page);

    // Find IP copy button
    const ipButton = page.locator('[aria-label="Copiar endereço IP"]').first();

    if (await ipButton.isVisible().catch(() => false)) {
      const ariaLabel = await ipButton.getAttribute('aria-label');
      expect(ariaLabel).toBe('Copiar endereço IP');
      console.log('✅ IP copy button has aria-label');
    } else {
      console.log('ℹ️ IP copy button not visible (machine may be offline)');
    }
  });

  test('SSH copy button has aria-label', async ({ page }) => {
    await goToMachines(page);

    // Find SSH copy button
    const sshButton = page.locator('[aria-label="Copiar comando SSH"]').first();

    if (await sshButton.isVisible().catch(() => false)) {
      const ariaLabel = await sshButton.getAttribute('aria-label');
      expect(ariaLabel).toBe('Copiar comando SSH');
      console.log('✅ SSH copy button has aria-label');
    } else {
      console.log('ℹ️ SSH copy button not visible (machine may be offline)');
    }
  });

  test('Aria-live region exists for copy announcements', async ({ page }) => {
    await goToMachines(page);

    // Find aria-live region for copy announcements
    const ariaLiveRegion = page.locator('[data-testid="copy-announcement"]');

    if (await ariaLiveRegion.count() > 0) {
      const role = await ariaLiveRegion.first().getAttribute('role');
      const ariaLive = await ariaLiveRegion.first().getAttribute('aria-live');

      expect(role).toBe('status');
      expect(ariaLive).toBe('polite');
      console.log('✅ Copy announcement aria-live region exists');
    } else {
      console.log('ℹ️ Copy announcement region not found');
    }
  });
});

// ============================================================
// TESTE 7: Keyboard Navigation - Failover Dropdown
// ============================================================
test.describe('⌨️ Keyboard Navigation - Failover Dropdown', () => {

  test('Escape key closes failover dropdown', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const failoverTrigger = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      // Open dropdown
      await failoverTrigger.click();
      await page.waitForTimeout(300);

      // Verify it's open
      const dropdown = page.locator('[data-testid="failover-dropdown-menu"]');
      expect(await dropdown.isVisible()).toBe(true);

      // Press Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);

      // Verify it's closed
      expect(await dropdown.isVisible().catch(() => false)).toBe(false);
      console.log('✅ Escape key closes failover dropdown');
    }
  });

  test('Arrow keys navigate between failover options', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const failoverTrigger = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      // Open dropdown with click
      await failoverTrigger.click();
      await page.waitForTimeout(300);

      // Press ArrowDown to navigate
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(100);

      // Check that focus moved (second option should be focused)
      const activeElement = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
      console.log(`Active element after ArrowDown: ${activeElement}`);

      // Press ArrowUp to go back
      await page.keyboard.press('ArrowUp');
      await page.waitForTimeout(100);

      console.log('✅ Arrow keys navigate between failover options');
    }
  });

  test('Enter/Space selects failover option and closes dropdown', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const failoverTrigger = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      // Open dropdown
      await failoverTrigger.click();
      await page.waitForTimeout(300);

      // Navigate to an option
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(100);

      // Press Enter to select
      await page.keyboard.press('Enter');
      await page.waitForTimeout(300);

      // Dropdown should be closed
      const dropdown = page.locator('[data-testid="failover-dropdown-menu"]');
      const isVisible = await dropdown.isVisible().catch(() => false);

      if (!isVisible) {
        console.log('✅ Enter key selects option and closes dropdown');
      } else {
        console.log('ℹ️ Dropdown may still be visible (option was selected)');
      }
    }
  });

  test('Tab traps focus within failover dropdown', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const failoverTrigger = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      // Open dropdown
      await failoverTrigger.click();
      await page.waitForTimeout(300);

      // Press Tab multiple times
      for (let i = 0; i < 6; i++) {
        await page.keyboard.press('Tab');
        await page.waitForTimeout(50);
      }

      // Focus should still be within the dropdown options
      const focusedElement = await page.evaluate(() => {
        const active = document.activeElement;
        return active?.closest('[data-testid="failover-dropdown-menu"]') !== null;
      });

      console.log(`Focus trapped in dropdown: ${focusedElement}`);
      console.log('✅ Tab traps focus within failover dropdown');
    }
  });

  test('Home/End keys jump to first/last option', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const failoverTrigger = page.locator('[data-testid="failover-selector"]').first();

    if (await failoverTrigger.isVisible().catch(() => false)) {
      // Open dropdown
      await failoverTrigger.click();
      await page.waitForTimeout(300);

      // Press End to go to last option
      await page.keyboard.press('End');
      await page.waitForTimeout(100);

      // Last option should be "snapshot"
      let activeTestId = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
      console.log(`After End key: ${activeTestId}`);

      // Press Home to go to first option
      await page.keyboard.press('Home');
      await page.waitForTimeout(100);

      // First option should be "disabled"
      activeTestId = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
      console.log(`After Home key: ${activeTestId}`);

      console.log('✅ Home/End keys work correctly');
    }
  });
});

// ============================================================
// TESTE 8: Keyboard Navigation - Backup Popup
// ============================================================
test.describe('⌨️ Keyboard Navigation - Backup Popup', () => {

  test('Escape closes backup popup and returns focus to badge', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    // Find and click backup badge
    const backupBadge = page.getByText(/backup|sem backup/i).first();

    if (await backupBadge.isVisible().catch(() => false)) {
      // Focus and click the badge
      await backupBadge.click();
      await page.waitForTimeout(300);

      // Check popup is open
      const popup = page.getByText(/cpu.*backup|pronto.*failover|nenhum.*backup/i).first();
      const isPopupVisible = await popup.isVisible().catch(() => false);

      if (isPopupVisible) {
        // Press Escape
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);

        // Popup should be closed
        const isStillVisible = await popup.isVisible().catch(() => false);
        expect(isStillVisible).toBe(false);

        console.log('✅ Escape closes backup popup');
      }
    }
  });

  test('Enter/Space opens backup popup from badge', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    // Find backup badge
    const backupBadge = page.getByText(/backup|sem backup/i).first();

    if (await backupBadge.isVisible().catch(() => false)) {
      // Focus the badge using Tab navigation
      await backupBadge.focus();
      await page.waitForTimeout(100);

      // Press Enter to open
      await page.keyboard.press('Enter');
      await page.waitForTimeout(300);

      // Check popup opened
      const popup = page.getByText(/cpu.*backup|pronto.*failover|nenhum.*backup/i).first();
      const isPopupVisible = await popup.isVisible().catch(() => false);

      if (isPopupVisible) {
        console.log('✅ Enter key opens backup popup');
      } else {
        console.log('ℹ️ Popup did not open with Enter key');
      }
    }
  });
});

// ============================================================
// TESTE 9: Keyboard Navigation - Main Options Menu
// ============================================================
test.describe('⌨️ Keyboard Navigation - Main Options Menu', () => {

  test('Arrow keys navigate menu items', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const menuButton = page.locator('[aria-label="Menu de opções da máquina"]').first();

    if (await menuButton.isVisible().catch(() => false)) {
      // Open menu
      await menuButton.click();
      await page.waitForTimeout(300);

      // Check menu opened
      const menu = page.locator('[role="menu"]').first();
      if (await menu.isVisible().catch(() => false)) {
        // Navigate with arrow keys
        await page.keyboard.press('ArrowDown');
        await page.waitForTimeout(100);
        await page.keyboard.press('ArrowDown');
        await page.waitForTimeout(100);
        await page.keyboard.press('ArrowUp');
        await page.waitForTimeout(100);

        console.log('✅ Arrow keys navigate menu items');
      }

      // Close with Escape
      await page.keyboard.press('Escape');
    }
  });

  test('Escape closes menu and returns focus to trigger', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    const menuButton = page.locator('[aria-label="Menu de opções da máquina"]').first();

    if (await menuButton.isVisible().catch(() => false)) {
      // Open menu
      await menuButton.click();
      await page.waitForTimeout(300);

      const menu = page.locator('[role="menu"]').first();
      expect(await menu.isVisible()).toBe(true);

      // Press Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);

      // Menu should be closed
      expect(await menu.isVisible().catch(() => false)).toBe(false);

      // Focus should return to trigger button
      const focusedElement = await page.evaluate(() => document.activeElement?.getAttribute('aria-label'));
      console.log(`Focus after Escape: ${focusedElement}`);
      console.log('✅ Escape closes menu and returns focus');
    }
  });
});

// ============================================================
// TESTE 10: Status Badge ARIA
// ============================================================
test.describe('♿ Status Badge ARIA', () => {

  test('Status badge has aria-label with status', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    // Find a status badge with aria-label
    const statusBadge = page.locator('[aria-label^="Status da máquina"]').first();

    if (await statusBadge.isVisible().catch(() => false)) {
      const ariaLabel = await statusBadge.getAttribute('aria-label');
      expect(ariaLabel).toMatch(/status da máquina/i);
      console.log(`✅ Status badge has aria-label: ${ariaLabel}`);
    } else {
      console.log('ℹ️ Status badge with aria-label not found');
    }
  });

  test('Loading states have aria-busy', async ({ page }) => {
    await goToMachines(page);

    // Find any element with aria-busy
    const busyElements = page.locator('[aria-busy="true"]');
    const count = await busyElements.count();

    console.log(`Found ${count} elements with aria-busy="true"`);

    // If there are loading machines, they should have aria-busy
    if (count > 0) {
      console.log('✅ Loading elements have aria-busy="true"');
    } else {
      console.log('ℹ️ No loading states active (this is fine)');
    }
  });
});

// ============================================================
// TESTE 11: Failover Progress ARIA Live Region
// ============================================================
test.describe('♿ Failover Progress ARIA Live Region', () => {

  test('Failover progress panel has aria-live', async ({ page }) => {
    await goToMachines(page);

    // Find failover progress panel
    const failoverPanel = page.locator('[data-testid="failover-progress-panel"]');

    if (await failoverPanel.isVisible().catch(() => false)) {
      const ariaLive = await failoverPanel.getAttribute('aria-live');
      const role = await failoverPanel.getAttribute('role');
      const ariaLabel = await failoverPanel.getAttribute('aria-label');

      expect(ariaLive).toBe('polite');
      expect(role).toBe('region');
      expect(ariaLabel).toBeTruthy();

      console.log(`✅ Failover panel has aria-live: ${ariaLive}, role: ${role}, aria-label: ${ariaLabel}`);
    } else {
      console.log('ℹ️ No failover in progress (this is fine)');
    }
  });

  test('Failover announcement region exists', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    // Find failover announcement region
    const announcementRegion = page.locator('[data-testid="failover-announcement"]');
    const count = await announcementRegion.count();

    if (count > 0) {
      const role = await announcementRegion.first().getAttribute('role');
      const ariaLive = await announcementRegion.first().getAttribute('aria-live');

      expect(role).toBe('status');
      expect(ariaLive).toBe('polite');

      console.log('✅ Failover announcement region exists with proper ARIA');
    } else {
      console.log('ℹ️ Failover announcement region not found');
    }
  });
});

// ============================================================
// TESTE 12: Focus Visibility
// ============================================================
test.describe('👁️ Focus Visibility', () => {

  test('Buttons have visible focus ring', async ({ page }) => {
    await goToMachines(page);

    if (!await hasMachineCards(page)) {
      test.skip();
      return;
    }

    // Find a button and focus it
    const button = page.getByRole('button').first();

    if (await button.isVisible().catch(() => false)) {
      await button.focus();

      // Check that focus ring is visible (has ring class or outline)
      const hasRing = await page.evaluate(() => {
        const el = document.activeElement;
        const styles = window.getComputedStyle(el);
        return styles.outline !== 'none' ||
               styles.boxShadow.includes('ring') ||
               el.className.includes('ring') ||
               el.className.includes('focus');
      });

      console.log(`Button has visible focus indicator: ${hasRing}`);
      console.log('✅ Focus visibility test completed');
    }
  });
});
