const { test, expect } = require('@playwright/test');

test.describe('Debug Iniciar Button', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="email"]', 'test@test.com');
    await page.fill('input[type="password"]', 'test123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/app/**', { timeout: 10000 });
  });

  test('Debug Iniciar button on stopped machine', async ({ page }) => {
    console.log('=== DEBUGGING INICIAR BUTTON ===');

    // Navigate to machines page
    console.log('1. Navigating to machines page...');
    await page.goto('http://localhost:5173/app/machines');
    await page.waitForLoadState('networkidle');

    // Take screenshot before
    console.log('2. Taking screenshot before...');
    await page.screenshot({ path: '/tmp/before-click.png', fullPage: true });

    // Set up console listener
    const consoleMessages = [];
    page.on('console', msg => {
      consoleMessages.push({ type: msg.type(), text: msg.text() });
      console.log(`[CONSOLE ${msg.type()}]: ${msg.text()}`);
    });

    // Set up error listener
    const pageErrors = [];
    page.on('pageerror', error => {
      pageErrors.push(error.message);
      console.log(`[PAGE ERROR]: ${error.message}`);
    });

    // Find all machines
    console.log('3. Finding machines...');
    const machineCards = await page.locator('[class*="flex flex-col p-3"]').all();
    console.log(`Found ${machineCards.length} machine cards`);

    // Find a stopped machine
    let stoppedMachine = null;
    let stoppedMachineIndex = -1;

    for (let i = 0; i < machineCards.length; i++) {
      const card = machineCards[i];
      const hasStoppedBadge = await card.locator('text=/stopped/i').count() > 0;

      if (hasStoppedBadge) {
        stoppedMachine = card;
        stoppedMachineIndex = i;
        console.log(`4. Found stopped machine at index ${i}`);

        // Get machine name
        const machineName = await card.locator('span.text-white.font-semibold').first().textContent();
        console.log(`   Machine name: ${machineName}`);
        break;
      }
    }

    if (!stoppedMachine) {
      console.log('ERROR: No stopped machine found!');
      console.log('Let me check all status badges...');
      const allBadges = await page.locator('[class*="StatusBadge"]').allTextContents();
      console.log('All status badges:', allBadges);

      // Take screenshot
      await page.screenshot({ path: '/tmp/no-stopped-machine.png', fullPage: true });
      throw new Error('No stopped machine found to test');
    }

    // Find the Iniciar button
    console.log('5. Looking for Iniciar button...');
    const iniciarButton = stoppedMachine.locator('button:has-text("Iniciar")');
    const buttonCount = await iniciarButton.count();
    console.log(`   Found ${buttonCount} Iniciar button(s)`);

    if (buttonCount === 0) {
      console.log('ERROR: Iniciar button not found!');
      const allButtons = await stoppedMachine.locator('button').allTextContents();
      console.log('All buttons in this card:', allButtons);
      await page.screenshot({ path: '/tmp/no-iniciar-button.png', fullPage: true });
      throw new Error('Iniciar button not found');
    }

    // Check button properties
    console.log('6. Checking button properties...');
    const isVisible = await iniciarButton.isVisible();
    const isEnabled = await iniciarButton.isEnabled();
    const buttonText = await iniciarButton.textContent();

    console.log(`   Visible: ${isVisible}`);
    console.log(`   Enabled: ${isEnabled}`);
    console.log(`   Text: ${buttonText}`);

    // Check if onClick handler is set
    console.log('7. Checking onClick handler...');
    const hasOnClick = await iniciarButton.evaluate(el => {
      return typeof el.onclick === 'function' || el.getAttribute('onClick') !== null;
    });
    console.log(`   Has onClick: ${hasOnClick}`);

    // Click the button
    console.log('8. Clicking Iniciar button...');
    await iniciarButton.click();

    // Wait a bit for any action
    await page.waitForTimeout(3000);

    // Check for demo toast
    console.log('9. Checking for demo toast...');
    const toast = await page.locator('[class*="fixed bottom-6 right-6"]').count();
    console.log(`   Toast count: ${toast}`);

    if (toast > 0) {
      const toastText = await page.locator('[class*="fixed bottom-6 right-6"]').textContent();
      console.log(`   Toast message: ${toastText}`);
    }

    // Check if machine status changed
    console.log('10. Checking machine status after click...');
    await page.waitForTimeout(2500); // Wait for demo simulation

    const updatedCard = machineCards[stoppedMachineIndex];
    const hasRunningBadge = await updatedCard.locator('text=/running/i').count() > 0;
    console.log(`   Machine is now running: ${hasRunningBadge}`);

    // Take screenshot after
    console.log('11. Taking screenshot after...');
    await page.screenshot({ path: '/tmp/after-click.png', fullPage: true });

    // Print console messages
    console.log('\n=== CONSOLE MESSAGES ===');
    consoleMessages.forEach(msg => {
      console.log(`[${msg.type}] ${msg.text}`);
    });

    // Print errors
    console.log('\n=== PAGE ERRORS ===');
    if (pageErrors.length === 0) {
      console.log('No errors');
    } else {
      pageErrors.forEach(err => console.log(err));
    }

    console.log('\n=== TEST COMPLETE ===');
    console.log('Screenshots saved to:');
    console.log('- /tmp/before-click.png');
    console.log('- /tmp/after-click.png');
  });
});
