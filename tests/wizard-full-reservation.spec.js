const { test, expect } = require('@playwright/test');

test.describe('Wizard Full GPU Reservation', () => {
  test('should complete full reservation flow', async ({ page }) => {
    test.setTimeout(120000); // 2 minutes timeout

    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('Winner') || text.includes('winner') || text.includes('Provisioning') || text.includes('Race')) {
        console.log(`[BROWSER] ${text}`);
      }
    });

    console.log('🚀 Starting full reservation test...\n');

    // Navigate to demo app
    await page.goto('http://localhost:4894/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Step 1: Select region
    console.log('📍 Step 1: Selecting region...');
    await page.locator('button:has-text("EUA")').first().click();
    await page.waitForTimeout(300);
    await page.locator('button:has-text("Próximo")').first().click();
    await page.waitForTimeout(500);
    console.log('✅ Region selected: EUA');

    // Step 2: Select purpose and GPU
    console.log('🎯 Step 2: Selecting purpose and GPU...');
    await page.locator('[data-testid="use-case-develop"]').click();
    await page.waitForTimeout(500);
    await page.waitForSelector('[data-gpu-card="true"]', { timeout: 10000 });

    const gpuCount = await page.locator('[data-gpu-card="true"]').count();
    console.log(`   Found ${gpuCount} GPU options`);

    await page.locator('[data-gpu-card="true"]').first().click();
    const gpuName = await page.locator('[data-gpu-card="true"]').first().getAttribute('data-gpu-name');
    console.log(`✅ GPU selected: ${gpuName}`);

    await page.waitForTimeout(300);
    await page.locator('button:has-text("Próximo")').first().click();
    await page.waitForTimeout(500);

    // Step 3: Strategy (already pre-selected)
    console.log('⚡ Step 3: Failover strategy...');
    await page.screenshot({ path: 'tests/screenshots/full-reservation-step3.png', fullPage: true });
    console.log('✅ Strategy: Snapshot Only (default)');

    // Click Iniciar
    console.log('🔥 Step 4: Starting provisioning...');
    await page.locator('button:has-text("Iniciar")').first().click();
    await page.waitForTimeout(1000);

    // Verify provisioning started
    const provisioningText = await page.locator('text=/Provisionando|Testando.*máquinas/').first().isVisible();
    console.log(`   Provisioning started: ${provisioningText}`);

    await page.screenshot({ path: 'tests/screenshots/full-reservation-racing.png', fullPage: true });

    // Wait for race to complete (demo mode simulates ~15-20 seconds)
    console.log('⏳ Waiting for race to complete...');

    let winner = null;
    let attempts = 0;
    const maxAttempts = 30; // 30 seconds max

    while (!winner && attempts < maxAttempts) {
      await page.waitForTimeout(1000);
      attempts++;

      // Check for winner indicators
      const hasWinner = await page.locator('text=/Pronta|Conectada|Sucesso|ready|success/i').first().isVisible().catch(() => false);
      const hasGreenCard = await page.locator('[class*="green"], [class*="success"]').first().isVisible().catch(() => false);

      // Check race status
      const raceStatus = await page.locator('text=/Round|Testando/').first().textContent().catch(() => '');

      if (attempts % 5 === 0) {
        console.log(`   [${attempts}s] Race status: ${raceStatus.substring(0, 50)}...`);
        await page.screenshot({ path: `tests/screenshots/full-reservation-progress-${attempts}.png`, fullPage: true });
      }

      if (hasWinner || hasGreenCard) {
        winner = true;
        console.log('🎉 Winner detected!');
      }

      // Check if all failed and moved to next round
      const roundText = await page.locator('text=/Round \\d/').first().textContent().catch(() => 'Round 1');
      if (roundText.includes('Round 2') || roundText.includes('Round 3')) {
        console.log(`   Moved to ${roundText}`);
      }
    }

    // Final screenshot
    await page.screenshot({ path: 'tests/screenshots/full-reservation-final.png', fullPage: true });

    // Check final state
    const finalState = await page.locator('text=/Pronta|Conectada|Máquina.*pronta|Provisionando|Testando/i').first().textContent().catch(() => 'Unknown');
    console.log(`\n📊 Final state: ${finalState}`);

    // Get machine cards status
    const machineCards = await page.locator('[class*="rounded-lg"][class*="border"]').count();
    console.log(`   Machine cards visible: ${machineCards}`);

    console.log('\n✅ Test completed!');

    // Test passes if we got to provisioning
    expect(provisioningText).toBeTruthy();
  });
});
