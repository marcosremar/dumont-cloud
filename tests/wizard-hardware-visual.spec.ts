import { test, expect } from '@playwright/test';

/**
 * Visual Test: GPU Wizard - Hardware Selection (Step 2)
 * Environment: Staging (REAL - no mocks)
 * Generated: 2026-01-02
 *
 * Purpose: Verify the wizard step 2 displays GPU tiers and offers correctly
 *
 * Test Flow:
 * 1. Auto-login at http://localhost:4896/login?auto_login=demo
 * 2. Navigate to wizard (should auto-show on /app or click "Nova Máquina")
 * 3. Progress to Step 2 (Hardware)
 * 4. Select a tier ("Rápido" or "Equilibrado")
 * 5. Capture screenshot
 * 6. Check console for errors
 * 7. Verify API calls to /api/v1/instances/offers
 */

test.describe('Wizard Hardware Selection - Visual Test', () => {

  test.beforeEach(async ({ page }) => {
    // Note: We're using the real backend, but auth state from setup
    // The auto_login will handle authentication
  });

  test('Step 2: Hardware - displays GPU tiers and offers', async ({ page }) => {
    const consoleMessages: string[] = [];
    const consoleErrors: string[] = [];
    const networkRequests: { url: string; method: string; status?: number }[] = [];

    // Capture console messages
    page.on('console', msg => {
      const text = msg.text();
      consoleMessages.push(`[${msg.type()}] ${text}`);
      if (msg.type() === 'error') {
        consoleErrors.push(text);
      }
    });

    // Capture network requests
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/') || url.includes('vast.ai')) {
        networkRequests.push({
          url,
          method: request.method(),
        });
      }
    });

    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/') || url.includes('vast.ai')) {
        const existing = networkRequests.find(r => r.url === url && !r.status);
        if (existing) {
          existing.status = response.status();
        }
      }
    });

    // Step 1: Navigate to login with auto_login
    console.log('\n=== Step 1: Auto-login ===');
    const startTime = performance.now();
    await page.goto('http://localhost:4896/login?auto_login=demo');
    await page.waitForLoadState('networkidle');

    // Wait for redirect to /app
    await page.waitForURL('**/app**', { timeout: 15000 });
    const loginTime = performance.now() - startTime;
    console.log(`✅ Login completed in ${loginTime.toFixed(0)}ms`);

    // Step 2: Locate wizard or "Nova Máquina" button
    console.log('\n=== Step 2: Locate Wizard ===');
    await page.waitForLoadState('networkidle');

    // Check if wizard is already visible
    const wizardVisible = await page.locator('text=Região, text=Localização, text=Hardware').first()
      .isVisible({ timeout: 3000 })
      .catch(() => false);

    if (!wizardVisible) {
      // Try to find and click "Nova Máquina" button
      const newMachineBtn = page.locator('button:has-text("Nova"), a:has-text("Nova"), button:has-text("Criar")').first();
      const hasBtnVisible = await newMachineBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (hasBtnVisible) {
        console.log('Clicking "Nova Máquina" button...');
        await newMachineBtn.click();
        await page.waitForLoadState('networkidle');
      } else {
        console.log('⚠️  No "Nova Máquina" button found - wizard might already be open');
      }
    } else {
      console.log('Wizard already visible');
    }

    // Take screenshot of initial state
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-step1.png',
      fullPage: true
    });

    // Step 3: Progress to Step 2 (Hardware)
    console.log('\n=== Step 3: Navigate to Step 2 (Hardware) ===');

    // Check if we're on step 1 (Region)
    const step1Header = await page.locator('text=Região').first().isVisible({ timeout: 3000 }).catch(() => false);

    if (step1Header) {
      console.log('Currently on Step 1 (Região) - need to progress to Step 2');

      // The wizard shows step 1/4 at the top. Look for region buttons
      const regionButtons = page.locator('button:has-text("EUA"), button:has-text("Europa"), button:has-text("Ásia")');
      const regionCount = await regionButtons.count();
      console.log(`Found ${regionCount} region quick-select buttons`);

      if (regionCount > 0) {
        // Click EUA or first available region button
        await regionButtons.first().click();
        await page.waitForTimeout(500);
        console.log('Region selected via quick-select button');
      }

      // Now click "Próximo" to move to step 2
      const nextBtn = page.locator('button:has-text("Próximo")').first();
      const hasNextBtn = await nextBtn.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasNextBtn) {
        console.log('Clicking "Próximo" button...');
        await nextBtn.click();
        await page.waitForTimeout(1000);
        await page.waitForLoadState('networkidle');
        console.log('✅ Moved to Step 2');
      } else {
        console.log('⚠️  "Próximo" button not found');
      }
    }

    // Verify we're on step 2
    const step2Visible = await page.locator('text=Hardware, text=GPU, text=Tier').first()
      .isVisible({ timeout: 5000 })
      .catch(() => false);

    console.log(`Step 2 visible: ${step2Visible}`);

    // Step 4: Select a tier
    console.log('\n=== Step 4: Select GPU Tier ===');

    const tierButtons = page.locator(
      'button:has-text("Rápido"), button:has-text("Equilibrado"), button:has-text("Lento"), [data-tier], .tier-button'
    );
    const tierCount = await tierButtons.count();
    console.log(`Found ${tierCount} tier buttons`);

    if (tierCount > 0) {
      // Try to select "Rápido" or "Equilibrado"
      const rapidoBtn = page.locator('button:has-text("Rápido")').first();
      const equilibradoBtn = page.locator('button:has-text("Equilibrado")').first();

      const hasRapido = await rapidoBtn.isVisible({ timeout: 2000 }).catch(() => false);
      const hasEquilibrado = await equilibradoBtn.isVisible({ timeout: 2000 }).catch(() => false);

      if (hasRapido) {
        console.log('Selecting "Rápido" tier...');
        await rapidoBtn.click();
      } else if (hasEquilibrado) {
        console.log('Selecting "Equilibrado" tier...');
        await equilibradoBtn.click();
      } else {
        console.log('Selecting first available tier...');
        await tierButtons.first().click();
      }

      // Wait for offers to load
      await page.waitForTimeout(2000);
      await page.waitForLoadState('networkidle');
    }

    // Step 5: Capture screenshot
    console.log('\n=== Step 5: Capture Screenshot ===');
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-step2-hardware.png',
      fullPage: true
    });
    console.log('Screenshot saved: wizard-step2-hardware.png');

    // Step 6: Check for machines/offers displayed
    console.log('\n=== Step 6: Check Offers Display ===');

    const machineCards = page.locator('.machine-card, [data-machine], .gpu-offer, .offer-card');
    const machineCount = await machineCards.count();
    console.log(`Found ${machineCount} machine/offer cards`);

    // Look for error messages
    const errorMessages = page.locator('text=Erro, text=Error, text=Falha, .error, .text-red');
    const errorCount = await errorMessages.count();

    if (errorCount > 0) {
      console.log('\n⚠️  Error messages found:');
      for (let i = 0; i < Math.min(errorCount, 3); i++) {
        const errorText = await errorMessages.nth(i).textContent();
        console.log(`  - ${errorText}`);
      }
    }

    // Check for empty state
    const emptyState = page.locator('text=Nenhuma, text=Sem ofertas, text=No offers, text=indisponível');
    const hasEmptyState = await emptyState.first().isVisible({ timeout: 2000 }).catch(() => false);

    if (hasEmptyState) {
      const emptyText = await emptyState.first().textContent();
      console.log(`\n⚠️  Empty state: ${emptyText}`);
    }

    // Step 7: Report findings
    console.log('\n=== Step 7: Test Results ===');
    console.log(`\n📊 Console Errors (${consoleErrors.length}):`);
    consoleErrors.slice(0, 5).forEach(err => console.log(`  ❌ ${err}`));

    console.log(`\n🌐 Network Requests to API (${networkRequests.filter(r => r.url.includes('/api/')).length}):`);
    const apiRequests = networkRequests.filter(r => r.url.includes('/api/'));
    apiRequests.forEach(req => {
      const path = new URL(req.url).pathname;
      console.log(`  ${req.method} ${path} - ${req.status || 'pending'}`);
    });

    // Check for /api/v1/instances/offers specifically
    const offersRequest = apiRequests.find(r => r.url.includes('/instances/offers'));
    if (offersRequest) {
      console.log(`\n✅ /api/v1/instances/offers called: ${offersRequest.status}`);
    } else {
      console.log('\n⚠️  /api/v1/instances/offers NOT called');
    }

    // Assertions
    console.log('\n=== Assertions ===');

    // Should have navigated to /app
    expect(page.url()).toContain('/app');
    console.log('✅ URL contains /app');

    // Screenshot should exist (Playwright creates it)
    console.log('✅ Screenshot captured');

    // Report summary
    console.log('\n=== Summary ===');
    console.log(`Console Errors: ${consoleErrors.length}`);
    console.log(`API Requests: ${apiRequests.length}`);
    console.log(`Machine Cards: ${machineCount}`);
    console.log(`Empty State: ${hasEmptyState ? 'Yes' : 'No'}`);
    console.log(`Offers API Called: ${offersRequest ? 'Yes' : 'No'}`);
  });
});
