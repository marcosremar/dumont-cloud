import { test } from '@playwright/test';

test('complete wizard flow documentation', async ({ page }) => {
  console.log('=== WIZARD MODAL FLOW DOCUMENTATION ===\n');

  // Navigate
  await page.goto('http://localhost:4893/login?auto_login=demo');
  await page.waitForTimeout(3000);

  // SCREEN 1: Initial state with welcome modal
  console.log('SCREEN 1: Welcome Modal (overlays everything)');
  await page.screenshot({ path: '/tmp/flow-1-welcome-modal.png', fullPage: true });
  console.log('  - Shows: "Bem-vindo à Dumont Cloud marcosremar!"');
  console.log('  - Buttons: "Pular" and "Começar"');
  console.log('  - This modal blocks access to main UI');
  console.log('  - Screenshot saved: /tmp/flow-1-welcome-modal.png\n');

  // Close the welcome modal by clicking "Pular"
  const pularBtn = page.locator('button:has-text("Pular")');
  if (await pularBtn.isVisible()) {
    await pularBtn.click();
    await page.waitForTimeout(1000);
  }

  // SCREEN 2: Main dashboard with "Nova Instância GPU" card
  console.log('SCREEN 2: Dashboard with GPU Instance Card');
  await page.screenshot({ path: '/tmp/flow-2-dashboard-main.png', fullPage: true });
  console.log('  - Shows: Main dashboard with machine cards');
  console.log('  - Card header: "Nova Instância GPU"');
  console.log('  - Mode selector: "Guiado" and "Avançado" buttons');
  console.log('  - These buttons switch between wizard and advanced mode');
  console.log('  - Screenshot saved: /tmp/flow-2-dashboard-main.png\n');

  // Scroll to the Nova Instância GPU card
  const guiadoBtn = page.locator('[data-testid="config-guided"]');
  await guiadoBtn.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);

  // Take focused screenshot of the card
  const card = page.locator('text="Nova Instância GPU"').locator('..');
  await page.screenshot({ path: '/tmp/flow-3-mode-selector-closeup.png', fullPage: true });
  console.log('SCREEN 3: Close-up of Mode Selector');
  console.log('  - "Guiado" button: data-testid="config-guided"');
  console.log('  - "Avançado" button: data-testid="config-advanced"');
  console.log('  - Active mode shown with bg-brand-500 (blue background)');
  console.log('  - Screenshot saved: /tmp/flow-3-mode-selector-closeup.png\n');

  // Check current mode
  const guiadoActive = await page.locator('[data-testid="config-guided"].bg-brand-500').count();
  const avancadoActive = await page.locator('[data-testid="config-advanced"].bg-brand-500').count();
  console.log('Current mode:');
  console.log(`  - Guiado active: ${guiadoActive > 0}`);
  console.log(`  - Avançado active: ${avancadoActive > 0}\n`);

  // Click Avançado to see the difference
  const avancadoBtn = page.locator('[data-testid="config-advanced"]');
  await avancadoBtn.click();
  await page.waitForTimeout(1000);

  await page.screenshot({ path: '/tmp/flow-4-advanced-mode.png', fullPage: true });
  console.log('SCREEN 4: Advanced Mode (after clicking Avançado)');
  console.log('  - Shows advanced configuration options');
  console.log('  - Screenshot saved: /tmp/flow-4-advanced-mode.png\n');

  // Switch back to Guiado
  await guiadoBtn.click();
  await page.waitForTimeout(1000);

  await page.screenshot({ path: '/tmp/flow-5-guided-mode.png', fullPage: true });
  console.log('SCREEN 5: Guided Mode (after clicking Guiado)');
  console.log('  - Shows step-by-step wizard interface');
  console.log('  - Steps: 1/4 Região, 2/4 Hardware, 3/4 Estratégia, 4/4 Provisionar');
  console.log('  - Screenshot saved: /tmp/flow-5-guided-mode.png\n');

  console.log('=== SUMMARY ===');
  console.log('Layout Structure:');
  console.log('1. Welcome Modal (can be skipped with "Pular")');
  console.log('2. Dashboard with "Nova Instância GPU" card');
  console.log('3. Mode selector: Guiado | Avançado buttons');
  console.log('4. Clicking them toggles between wizard and advanced modes');
  console.log('5. Both buttons are ALWAYS visible (not inside a modal)');
  console.log('6. They control what content shows below them in the card\n');

  console.log('Element Locations:');
  console.log('- Guiado button: [data-testid="config-guided"]');
  console.log('- Avançado button: [data-testid="config-advanced"]');
  console.log('- Parent: Inline-flex container with bg-white/5 rounded-lg');
  console.log('- Card header: "Nova Instância GPU"');
});
