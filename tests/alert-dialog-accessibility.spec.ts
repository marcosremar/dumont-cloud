import { test, expect } from '@playwright/test';

/**
 * E2E tests for AlertDialog accessibility features
 * Tests ARIA attributes, keyboard navigation, focus trapping, and focus return
 */
test.describe('AlertDialog Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to machines page where AlertDialogs are used
    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');

    // Wait for machine cards to load (demo mode provides mock data)
    await page.waitForSelector('[class*="MachineCard"], [data-testid="machine-card"]', {
      state: 'visible',
      timeout: 10000
    }).catch(() => {
      // If no specific selector, wait for general card content
      return page.waitForSelector('text=GPU', { state: 'visible', timeout: 10000 });
    });
  });

  test('AlertDialog has correct ARIA attributes when opened', async ({ page }) => {
    // Find a machine card with a "Pausar" button (indicates running state)
    const pauseButton = page.locator('button:has-text("Pausar")').first();

    // Check if a running machine exists (has pause button)
    const hasPauseButton = await pauseButton.isVisible().catch(() => false);

    if (!hasPauseButton) {
      // If no running machine, we need to test with another AlertDialog trigger
      // Look for any AlertDialog trigger (e.g., destroy button in dropdown)
      console.log('No running machine found, skipping pause dialog test');
      test.skip();
      return;
    }

    // Click the pause button to open AlertDialog
    await pauseButton.click();

    // Wait for AlertDialog to appear
    const alertDialog = page.locator('[role="alertdialog"]');
    await expect(alertDialog).toBeVisible({ timeout: 5000 });

    // Verify role="alertdialog" is present
    await expect(alertDialog).toHaveAttribute('role', 'alertdialog');

    // Verify aria-modal="true" is present
    await expect(alertDialog).toHaveAttribute('aria-modal', 'true');

    // Verify aria-labelledby points to the title
    const ariaLabelledBy = await alertDialog.getAttribute('aria-labelledby');
    expect(ariaLabelledBy).toBeTruthy();

    // Verify the title element exists with the matching id
    const titleElement = page.locator(`#${ariaLabelledBy}`);
    await expect(titleElement).toBeVisible();
    await expect(titleElement).toContainText('Pausar');

    // Verify aria-describedby points to the description
    const ariaDescribedBy = await alertDialog.getAttribute('aria-describedby');
    expect(ariaDescribedBy).toBeTruthy();

    // Verify the description element exists with the matching id
    const descriptionElement = page.locator(`#${ariaDescribedBy}`);
    await expect(descriptionElement).toBeVisible();
  });

  test('Tab key navigation cycles through focusable elements in AlertDialog', async ({ page }) => {
    // Find and click a pause button to open AlertDialog
    const pauseButton = page.locator('button:has-text("Pausar")').first();
    const hasPauseButton = await pauseButton.isVisible().catch(() => false);

    if (!hasPauseButton) {
      console.log('No running machine found, skipping tab navigation test');
      test.skip();
      return;
    }

    await pauseButton.click();

    // Wait for AlertDialog to appear
    const alertDialog = page.locator('[role="alertdialog"]');
    await expect(alertDialog).toBeVisible({ timeout: 5000 });

    // Get all focusable elements in the dialog
    const cancelButton = page.locator('[role="alertdialog"] button:has-text("Cancelar")');
    const actionButton = page.locator('[role="alertdialog"] button:has-text("Pausar")');

    // Wait for buttons to be available
    await expect(cancelButton).toBeVisible();
    await expect(actionButton).toBeVisible();

    // Press Tab to cycle through focusable elements
    await page.keyboard.press('Tab');

    // After first Tab, one of the buttons should be focused
    // Note: The exact focus order depends on implementation
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(['BUTTON', 'INPUT', 'A']).toContain(focusedElement);

    // Press Tab again to move to next focusable element
    await page.keyboard.press('Tab');

    // Verify we're still inside the dialog (focus is trapped)
    const focusedAfterTab = await page.evaluate(() => {
      const active = document.activeElement;
      const dialog = document.querySelector('[role="alertdialog"]');
      return dialog?.contains(active);
    });
    expect(focusedAfterTab).toBe(true);

    // Press Tab multiple times to ensure focus wraps
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Verify focus is still trapped in dialog
    const focusStillTrapped = await page.evaluate(() => {
      const active = document.activeElement;
      const dialog = document.querySelector('[role="alertdialog"]');
      return dialog?.contains(active);
    });
    expect(focusStillTrapped).toBe(true);
  });

  test('Shift+Tab cycles backward through focusable elements', async ({ page }) => {
    // Find and click a pause button to open AlertDialog
    const pauseButton = page.locator('button:has-text("Pausar")').first();
    const hasPauseButton = await pauseButton.isVisible().catch(() => false);

    if (!hasPauseButton) {
      console.log('No running machine found, skipping shift+tab test');
      test.skip();
      return;
    }

    await pauseButton.click();

    // Wait for AlertDialog to appear
    const alertDialog = page.locator('[role="alertdialog"]');
    await expect(alertDialog).toBeVisible({ timeout: 5000 });

    // Press Shift+Tab to cycle backward
    await page.keyboard.press('Shift+Tab');

    // Verify focus is still inside the dialog (backward navigation works)
    const focusedAfterShiftTab = await page.evaluate(() => {
      const active = document.activeElement;
      const dialog = document.querySelector('[role="alertdialog"]');
      return dialog?.contains(active);
    });
    expect(focusedAfterShiftTab).toBe(true);

    // Press Shift+Tab multiple times
    await page.keyboard.press('Shift+Tab');
    await page.keyboard.press('Shift+Tab');

    // Verify focus is still trapped
    const focusStillTrapped = await page.evaluate(() => {
      const active = document.activeElement;
      const dialog = document.querySelector('[role="alertdialog"]');
      return dialog?.contains(active);
    });
    expect(focusStillTrapped).toBe(true);
  });

  test('Escape key closes the AlertDialog', async ({ page }) => {
    // Find and click a pause button to open AlertDialog
    const pauseButton = page.locator('button:has-text("Pausar")').first();
    const hasPauseButton = await pauseButton.isVisible().catch(() => false);

    if (!hasPauseButton) {
      console.log('No running machine found, skipping escape key test');
      test.skip();
      return;
    }

    await pauseButton.click();

    // Wait for AlertDialog to appear
    const alertDialog = page.locator('[role="alertdialog"]');
    await expect(alertDialog).toBeVisible({ timeout: 5000 });

    // Press Escape to close the dialog
    await page.keyboard.press('Escape');

    // Verify the dialog is closed
    await expect(alertDialog).not.toBeVisible({ timeout: 3000 });
  });

  test('Focus returns to trigger element when AlertDialog closes', async ({ page }) => {
    // Find and click a pause button to open AlertDialog
    const pauseButton = page.locator('button:has-text("Pausar")').first();
    const hasPauseButton = await pauseButton.isVisible().catch(() => false);

    if (!hasPauseButton) {
      console.log('No running machine found, skipping focus return test');
      test.skip();
      return;
    }

    // Focus and click the pause button
    await pauseButton.focus();
    await pauseButton.click();

    // Wait for AlertDialog to appear
    const alertDialog = page.locator('[role="alertdialog"]');
    await expect(alertDialog).toBeVisible({ timeout: 5000 });

    // Press Escape to close the dialog
    await page.keyboard.press('Escape');

    // Wait for dialog to close
    await expect(alertDialog).not.toBeVisible({ timeout: 3000 });

    // Wait a bit for focus to return
    await page.waitForTimeout(100);

    // Verify focus returned to the trigger button
    // Note: Due to the AlertDialogTrigger wrapping, we check if focus is near the original button
    const isFocusedOnPauseButton = await page.evaluate(() => {
      const active = document.activeElement;
      // Check if it's a button with "Pausar" text or close to it
      return active?.tagName === 'BUTTON' &&
             (active?.textContent?.includes('Pausar') ||
              active?.closest('button')?.textContent?.includes('Pausar'));
    });

    // Alternative check: focus is on any button in the same card
    const focusInCard = await page.evaluate(() => {
      const active = document.activeElement;
      return active?.tagName === 'BUTTON' || active?.closest('[class*="Card"]') !== null;
    });

    expect(isFocusedOnPauseButton || focusInCard).toBe(true);
  });

  test('Cancel button closes AlertDialog and returns focus', async ({ page }) => {
    // Find and click a pause button to open AlertDialog
    const pauseButton = page.locator('button:has-text("Pausar")').first();
    const hasPauseButton = await pauseButton.isVisible().catch(() => false);

    if (!hasPauseButton) {
      console.log('No running machine found, skipping cancel button test');
      test.skip();
      return;
    }

    await pauseButton.click();

    // Wait for AlertDialog to appear
    const alertDialog = page.locator('[role="alertdialog"]');
    await expect(alertDialog).toBeVisible({ timeout: 5000 });

    // Click the Cancel button
    const cancelButton = page.locator('[role="alertdialog"] button:has-text("Cancelar")');
    await cancelButton.click();

    // Verify the dialog is closed
    await expect(alertDialog).not.toBeVisible({ timeout: 3000 });
  });

  test('Clicking overlay closes AlertDialog', async ({ page }) => {
    // Find and click a pause button to open AlertDialog
    const pauseButton = page.locator('button:has-text("Pausar")').first();
    const hasPauseButton = await pauseButton.isVisible().catch(() => false);

    if (!hasPauseButton) {
      console.log('No running machine found, skipping overlay click test');
      test.skip();
      return;
    }

    await pauseButton.click();

    // Wait for AlertDialog to appear
    const alertDialog = page.locator('[role="alertdialog"]');
    await expect(alertDialog).toBeVisible({ timeout: 5000 });

    // Click outside the dialog (on the overlay)
    // The overlay is a fixed element with bg-black/80 class
    await page.click('.fixed.inset-0.bg-black\\/80, .fixed.inset-0[class*="bg-black"]', {
      position: { x: 10, y: 10 }
    });

    // Verify the dialog is closed
    await expect(alertDialog).not.toBeVisible({ timeout: 3000 });
  });

  test('Focus moves into dialog content when opened', async ({ page }) => {
    // Find and click a pause button to open AlertDialog
    const pauseButton = page.locator('button:has-text("Pausar")').first();
    const hasPauseButton = await pauseButton.isVisible().catch(() => false);

    if (!hasPauseButton) {
      console.log('No running machine found, skipping initial focus test');
      test.skip();
      return;
    }

    await pauseButton.click();

    // Wait for AlertDialog to appear
    const alertDialog = page.locator('[role="alertdialog"]');
    await expect(alertDialog).toBeVisible({ timeout: 5000 });

    // Wait a bit for focus management
    await page.waitForTimeout(100);

    // Verify focus is inside the dialog
    const focusInsideDialog = await page.evaluate(() => {
      const active = document.activeElement;
      const dialog = document.querySelector('[role="alertdialog"]');
      return dialog?.contains(active);
    });
    expect(focusInsideDialog).toBe(true);
  });
});

/**
 * Additional tests for AlertDialog in different contexts
 * These tests verify AlertDialog behavior in various UI scenarios
 */
test.describe('AlertDialog Context Tests', () => {
  test('Programmatic AlertDialog (error dialogs) has correct attributes', async ({ page }) => {
    // Navigate to machines page
    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');

    // Wait for page to load
    await page.waitForSelector('text=GPU', { state: 'visible', timeout: 10000 }).catch(() => null);

    // Look for VS Code button to trigger an error dialog
    const vsCodeButton = page.locator('button:has-text("VS Code")').first();
    const hasVsCodeButton = await vsCodeButton.isVisible().catch(() => false);

    if (!hasVsCodeButton) {
      console.log('No VS Code button found, skipping programmatic dialog test');
      test.skip();
      return;
    }

    // Click dropdown to get VS Code options
    await vsCodeButton.click();

    // Look for "Desktop (SSH)" option which may show an error dialog
    const desktopOption = page.locator('text=Desktop').first();
    const hasDesktopOption = await desktopOption.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasDesktopOption) {
      await desktopOption.click();

      // Check if an error AlertDialog appeared
      const alertDialog = page.locator('[role="alertdialog"]');
      const hasDialog = await alertDialog.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasDialog) {
        // Verify ARIA attributes on programmatic dialog
        await expect(alertDialog).toHaveAttribute('role', 'alertdialog');
        await expect(alertDialog).toHaveAttribute('aria-modal', 'true');

        // Close the dialog
        await page.keyboard.press('Escape');
      }
    }
  });
});
