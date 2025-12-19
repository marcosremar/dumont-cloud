const { test, expect } = require('@playwright/test');

test.describe('Comprehensive Iniciar Button Debug', () => {

  test('Debug Iniciar button functionality', async ({ page }) => {
    console.log('\n' + '='.repeat(80));
    console.log('DEBUGGING INICIAR BUTTON ON MACHINES PAGE');
    console.log('='.repeat(80) + '\n');

    // Set up console and error listeners
    const consoleLogs = [];
    const pageErrors = [];

    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push({ type: msg.type(), text });
      console.log(`[BROWSER ${msg.type().toUpperCase()}] ${text}`);
    });

    page.on('pageerror', error => {
      pageErrors.push(error.message);
      console.log(`[PAGE ERROR] ${error.message}`);
    });

    // Step 1: Navigate to demo app machines page directly
    console.log('\n📍 Step 1: Navigating to demo machines page...');
    const targetUrl = 'http://localhost:5173/demo-app/machines';
    console.log(`   URL: ${targetUrl}`);

    try {
      await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
      console.log('   ✅ Page loaded');
    } catch (e) {
      console.log(`   ❌ Error loading page: ${e.message}`);

      // Try login first
      console.log('\n🔐 Attempting login first...');
      await page.goto('http://localhost:5173/login');
      await page.fill('input[type="email"]', 'test@test.com');
      await page.fill('input[type="password"]', 'test123');
      await page.click('button[type="submit"]');
      await page.waitForURL('**/app/**', { timeout: 10000 });

      // Navigate to machines again
      await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
      console.log('   ✅ Logged in and navigated to machines');
    }

    await page.waitForTimeout(2000);

    // Take initial screenshot
    await page.screenshot({ path: '/tmp/iniciar-debug-01-initial.png', fullPage: true });
    console.log('   📸 Screenshot saved: /tmp/iniciar-debug-01-initial.png');

    // Step 2: Verify demo mode
    console.log('\n🎮 Step 2: Verifying demo mode...');
    const currentUrl = page.url();
    console.log(`   Current URL: ${currentUrl}`);

    const isDemoMode = await page.evaluate(() => {
      return window.location.pathname.startsWith('/demo-app') ||
             new URLSearchParams(window.location.search).get('demo') === 'true';
    });
    console.log(`   Is Demo Mode: ${isDemoMode}`);

    if (!isDemoMode) {
      console.log('   ⚠️  WARNING: Not in demo mode! Button behavior may differ.');
    }

    // Step 3: Find all machine cards
    console.log('\n🖥️  Step 3: Finding machine cards...');

    // Wait for machines to load
    try {
      await page.waitForSelector('text=/Minhas Máquinas/i', { timeout: 5000 });
      console.log('   ✅ Machines page header found');
    } catch (e) {
      console.log('   ⚠️  Machines header not found, continuing anyway...');
    }

    // Find machine cards - try multiple selectors
    const cardSelectors = [
      '[class*="flex flex-col p-3"]',
      '[class*="flex-col"][class*="rounded-lg"]',
      'div.flex.flex-col'
    ];

    let machineCards = [];
    for (const selector of cardSelectors) {
      machineCards = await page.locator(selector).all();
      if (machineCards.length > 0) {
        console.log(`   ✅ Found ${machineCards.length} cards using selector: ${selector}`);
        break;
      }
    }

    if (machineCards.length === 0) {
      console.log('   ❌ No machine cards found!');
      await page.screenshot({ path: '/tmp/iniciar-debug-02-no-cards.png', fullPage: true });
      throw new Error('No machine cards found on page');
    }

    // Step 4: Find stopped machine
    console.log('\n🔍 Step 4: Looking for stopped machines...');

    let stoppedMachine = null;
    let stoppedMachineIndex = -1;
    let stoppedMachineName = '';

    for (let i = 0; i < machineCards.length; i++) {
      const card = machineCards[i];

      // Get machine name
      const nameElement = card.locator('span.text-white.font-semibold').first();
      const name = await nameElement.textContent().catch(() => 'Unknown');

      // Check for stopped status - try multiple methods
      const hasStoppedText = await card.locator('text=/stopped/i').count() > 0;
      const statusBadge = await card.locator('[class*="StatusBadge"], [class*="status"]').textContent().catch(() => '');

      console.log(`   Card ${i}: ${name} - Status badge: "${statusBadge}" - Has "stopped" text: ${hasStoppedText}`);

      if (hasStoppedText || statusBadge.toLowerCase().includes('stopped')) {
        stoppedMachine = card;
        stoppedMachineIndex = i;
        stoppedMachineName = name;
        console.log(`   ✅ Found stopped machine: ${name} at index ${i}`);
        break;
      }
    }

    if (!stoppedMachine) {
      console.log('   ⚠️  No stopped machine found. Listing all machines:');
      for (let i = 0; i < machineCards.length; i++) {
        const card = machineCards[i];
        const name = await card.locator('span.text-white.font-semibold').first().textContent().catch(() => 'Unknown');
        const allText = await card.textContent();
        console.log(`      Machine ${i}: ${name}`);
        console.log(`         Text content: ${allText.substring(0, 200)}...`);
      }

      await page.screenshot({ path: '/tmp/iniciar-debug-03-no-stopped.png', fullPage: true });
      throw new Error('No stopped machine found to test');
    }

    // Step 5: Find Iniciar button
    console.log('\n🔘 Step 5: Finding Iniciar button...');

    // Highlight the stopped machine card
    await stoppedMachine.evaluate(el => {
      el.style.outline = '3px solid red';
      el.style.outlineOffset = '2px';
    });

    await page.screenshot({ path: '/tmp/iniciar-debug-04-stopped-highlighted.png', fullPage: true });
    console.log('   📸 Screenshot with highlighted card: /tmp/iniciar-debug-04-stopped-highlighted.png');

    // Find Iniciar button
    const iniciarButton = stoppedMachine.locator('button:has-text("Iniciar")');
    const buttonCount = await iniciarButton.count();
    console.log(`   Found ${buttonCount} "Iniciar" button(s)`);

    if (buttonCount === 0) {
      console.log('   ❌ No Iniciar button found!');
      const allButtons = await stoppedMachine.locator('button').all();
      console.log(`   Found ${allButtons.length} buttons in this card:`);
      for (let i = 0; i < allButtons.length; i++) {
        const btnText = await allButtons[i].textContent();
        console.log(`      Button ${i}: "${btnText}"`);
      }

      await page.screenshot({ path: '/tmp/iniciar-debug-05-no-button.png', fullPage: true });
      throw new Error('Iniciar button not found');
    }

    // Step 6: Inspect button properties
    console.log('\n🔬 Step 6: Inspecting button properties...');

    const buttonInfo = await iniciarButton.evaluate(btn => {
      return {
        visible: btn.offsetParent !== null,
        disabled: btn.disabled,
        text: btn.textContent,
        className: btn.className,
        hasOnClick: typeof btn.onclick === 'function',
        onClickAttr: btn.getAttribute('onClick'),
        computedDisplay: window.getComputedStyle(btn).display,
        computedVisibility: window.getComputedStyle(btn).visibility,
        computedPointerEvents: window.getComputedStyle(btn).pointerEvents,
      };
    });

    console.log('   Button properties:');
    console.log(`      - Visible: ${buttonInfo.visible}`);
    console.log(`      - Disabled: ${buttonInfo.disabled}`);
    console.log(`      - Text: "${buttonInfo.text}"`);
    console.log(`      - ClassName: ${buttonInfo.className}`);
    console.log(`      - Has onclick: ${buttonInfo.hasOnClick}`);
    console.log(`      - onClick attr: ${buttonInfo.onClickAttr}`);
    console.log(`      - Display: ${buttonInfo.computedDisplay}`);
    console.log(`      - Visibility: ${buttonInfo.computedVisibility}`);
    console.log(`      - Pointer events: ${buttonInfo.computedPointerEvents}`);

    // Highlight the button
    await iniciarButton.evaluate(btn => {
      btn.style.outline = '3px solid lime';
      btn.style.outlineOffset = '2px';
    });

    await page.screenshot({ path: '/tmp/iniciar-debug-06-button-highlighted.png', fullPage: true });
    console.log('   📸 Screenshot with highlighted button: /tmp/iniciar-debug-06-button-highlighted.png');

    // Step 7: Click the button
    console.log('\n👆 Step 7: Clicking Iniciar button...');
    console.log(`   Machine: ${stoppedMachineName}`);

    // Scroll button into view
    await iniciarButton.scrollIntoViewIfNeeded();

    // Click
    console.log('   🖱️  Clicking...');
    await iniciarButton.click();
    console.log('   ✅ Click executed');

    // Step 8: Monitor for changes
    console.log('\n⏱️  Step 8: Monitoring for changes (waiting 3 seconds)...');

    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/iniciar-debug-07-after-1s.png', fullPage: true });

    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/iniciar-debug-08-after-2s.png', fullPage: true });

    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/iniciar-debug-09-after-3s.png', fullPage: true });

    console.log('   📸 Screenshots saved at 1s, 2s, 3s intervals');

    // Step 9: Check for toast
    console.log('\n🍞 Step 9: Checking for demo toast...');

    const toastSelector = '[class*="fixed bottom-6 right-6"]';
    const toastCount = await page.locator(toastSelector).count();
    console.log(`   Toast elements found: ${toastCount}`);

    if (toastCount > 0) {
      const toastText = await page.locator(toastSelector).textContent();
      const toastClasses = await page.locator(toastSelector).getAttribute('class');
      console.log(`   ✅ Toast visible!`);
      console.log(`      Text: "${toastText}"`);
      console.log(`      Classes: ${toastClasses}`);
    } else {
      console.log('   ❌ No toast found');
    }

    // Step 10: Check status change
    console.log('\n📊 Step 10: Checking machine status...');

    // Re-query the card at the same index
    const allCards = await page.locator(cardSelectors[0]).all();
    const updatedCard = allCards[stoppedMachineIndex];

    const statusAfter = await updatedCard.locator('[class*="StatusBadge"], [class*="status"]').textContent().catch(() => '');
    const hasRunning = statusAfter.toLowerCase().includes('running');

    console.log(`   Status badge now: "${statusAfter}"`);
    console.log(`   Is running: ${hasRunning}`);

    if (hasRunning) {
      console.log('   ✅ Machine status changed to running!');
    } else {
      console.log('   ❌ Machine status did NOT change');
    }

    // Final screenshot
    await page.screenshot({ path: '/tmp/iniciar-debug-10-final.png', fullPage: true });
    console.log('   📸 Final screenshot: /tmp/iniciar-debug-10-final.png');

    // Step 11: Summary
    console.log('\n' + '='.repeat(80));
    console.log('DEBUG SUMMARY');
    console.log('='.repeat(80));
    console.log(`Demo Mode: ${isDemoMode}`);
    console.log(`Machine Cards Found: ${machineCards.length}`);
    console.log(`Stopped Machine: ${stoppedMachineName} (index ${stoppedMachineIndex})`);
    console.log(`Iniciar Button Found: ${buttonCount > 0}`);
    console.log(`Button Visible: ${buttonInfo.visible}`);
    console.log(`Button Disabled: ${buttonInfo.disabled}`);
    console.log(`Toast Appeared: ${toastCount > 0}`);
    console.log(`Status Changed: ${hasRunning}`);
    console.log(`Console Logs: ${consoleLogs.length}`);
    console.log(`Page Errors: ${pageErrors.length}`);
    console.log('='.repeat(80) + '\n');

    if (pageErrors.length > 0) {
      console.log('⚠️  PAGE ERRORS DETECTED:');
      pageErrors.forEach((err, i) => {
        console.log(`   ${i + 1}. ${err}`);
      });
    }

    console.log('\n📁 All screenshots saved to /tmp/iniciar-debug-*.png');
    console.log('\n✅ Debug test completed!\n');
  });
});
