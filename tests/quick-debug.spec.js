const { test, expect } = require('@playwright/test');

test('Quick debug - Click Start/Iniciar and check console', async ({ page }) => {
  // Collect console logs
  const logs = [];
  page.on('console', msg => {
    logs.push({ type: msg.type(), text: msg.text() });
    console.log(`[${msg.type().toUpperCase()}]`, msg.text());
  });

  // Collect errors
  const errors = [];
  page.on('pageerror', err => {
    errors.push(err.message);
    console.error('[PAGE ERROR]', err.message);
  });

  console.log('\n=== Quick Debug Test ===\n');

  // Navigate to demo machines page
  console.log('1. Navigating to /app/machines...');
  await page.goto('http://localhost:5173/app/machines');
  await page.waitForTimeout(2000);

  console.log('2. Taking initial screenshot...');
  await page.screenshot({ path: '/tmp/quick-debug-before.png', fullPage: true });

  console.log('3. Looking for stopped machines...');
  const stoppedCards = await page.locator('text=/stopped/i').first().locator('..').locator('..').locator('..');
  const count = await stoppedCards.count();
  console.log(`   Found ${count} elements with "stopped" status`);

  if (count === 0) {
    console.log('   Trying alternative method...');
    // Alternative: find all cards and check each one
    const allCards = await page.locator('[class*="flex flex-col p-3"]').all();
    console.log(`   Found ${allCards.length} total machine cards`);

    for (let i = 0; i < allCards.length; i++) {
      const card = allCards[i];
      const text = await card.textContent();
      console.log(`   Card ${i}: ${text.substring(0, 100)}...`);
    }
  }

  console.log('4. Finding Start/Iniciar button...');
  const iniciarButton = page.locator('button').filter({ hasText: /^Start$|^Iniciar$/i }).first();

  const exists = await iniciarButton.count() > 0;
  console.log(`   Button exists: ${exists}`);

  if (!exists) {
    console.log('   ERROR: No Start/Iniciar button found!');
    await page.screenshot({ path: '/tmp/quick-debug-no-button.png', fullPage: true });
    throw new Error('No Start/Iniciar button found');
  }

  console.log('5. Clicking Start/Iniciar button...');
  await iniciarButton.click();

  console.log('6. Waiting 3 seconds for changes...');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/quick-debug-after-1s.png', fullPage: true });

  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/quick-debug-after-2s.png', fullPage: true });

  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/quick-debug-after-3s.png', fullPage: true });

  console.log('7. Summary:');
  console.log(`   Total console logs: ${logs.length}`);
  console.log(`   Total errors: ${errors.length}`);

  console.log('\n=== Console Logs ===');
  logs.forEach(log => {
    console.log(`[${log.type}] ${log.text}`);
  });

  if (errors.length > 0) {
    console.log('\n=== Errors ===');
    errors.forEach(err => {
      console.log(err);
    });
  }

  console.log('\n=== Screenshots ===');
  console.log('- /tmp/quick-debug-before.png');
  console.log('- /tmp/quick-debug-after-1s.png');
  console.log('- /tmp/quick-debug-after-2s.png');
  console.log('- /tmp/quick-debug-after-3s.png');

  console.log('\n=== Test Complete ===\n');
});
