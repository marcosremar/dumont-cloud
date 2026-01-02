// Visual Test: Wizard Real Machines (Post-Fix)
// This script tests that the wizard shows REAL machines after localStorage.removeItem('demo_mode')

import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 1000 });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Enable network logging to track API calls
  const apiCalls = [];
  page.on('request', request => {
    if (request.url().includes('/api/')) {
      apiCalls.push({
        url: request.url(),
        method: request.method()
      });
      console.log(`📡 API Request: ${request.method()} ${request.url()}`);
    }
  });

  page.on('response', async response => {
    if (response.url().includes('/api/v1/instances/offers')) {
      console.log(`✅ Offers API called: ${response.status()}`);
      try {
        const body = await response.json();
        console.log(`📊 Offers response:`, JSON.stringify(body, null, 2));
      } catch (e) {
        console.log('Could not parse offers response');
      }
    }
  });

  try {
    console.log('1️⃣  Navigating to login with auto_login=demo...');
    await page.goto('http://localhost:4896/login?auto_login=demo');

    console.log('2️⃣  CRITICAL: Removing demo_mode from localStorage...');
    await page.evaluate(() => {
      localStorage.removeItem('demo_mode');
      console.log('✅ demo_mode removed. Current localStorage:', localStorage);
    });

    console.log('3️⃣  Waiting for auto-login to complete...');
    await page.waitForURL('**/app**', { timeout: 10000 });
    console.log('✅ Login complete, now at:', page.url());

    console.log('4️⃣  Dashboard should show wizard by default...');
    // Wait for wizard form to be visible
    await page.waitForSelector('[data-testid="wizard-form"], #wizard-form-section', { timeout: 5000 });
    console.log('✅ Wizard is visible on dashboard');

    console.log('5️⃣  Step 1: Selecting a region...');
    // Step 1 is about location - find region buttons (EUA, Europa, Asia, America do Sul)
    const euaButton = page.locator('[data-testid="region-eua"]').first();
    const europaButton = page.locator('[data-testid="region-europa"]').first();

    if (await euaButton.isVisible()) {
      console.log('✅ Found region selector, selecting "EUA"...');
      await euaButton.click();
      await page.waitForTimeout(500);
    } else if (await europaButton.isVisible()) {
      console.log('✅ Found region selector, selecting "Europa"...');
      await europaButton.click();
      await page.waitForTimeout(500);
    } else {
      console.log('⚠️  No region buttons found, may already be selected');
    }

    console.log('6️⃣  Moving to Step 2 (Hardware)...');
    // Click "Próximo" to advance to hardware selection
    const nextButton = page.locator('button:has-text("Próximo"), button:has-text("Next")').first();
    if (await nextButton.isVisible()) {
      await nextButton.click();
      console.log('✅ Clicked "Próximo" to advance to Step 2');
    }

    await page.waitForTimeout(2000);

    console.log('7️⃣  Looking for GPU tier buttons (Rápido/Equilibrado)...');
    const rapidoButton = page.locator('button:has-text("Rápido")').first();
    const equilibradoButton = page.locator('button:has-text("Equilibrado")').first();

    if (await rapidoButton.isVisible()) {
      console.log('✅ Found "Rápido" tier, clicking...');
      await rapidoButton.click();
    } else if (await equilibradoButton.isVisible()) {
      console.log('✅ Found "Equilibrado" tier, clicking...');
      await equilibradoButton.click();
    } else {
      console.log('⚠️  No tier buttons found, may already be on hardware selection');
    }

    console.log('8️⃣  Waiting for machines to load...');
    await page.waitForTimeout(3000);

    // Check if /api/v1/instances/offers was called
    const offersApiCalled = apiCalls.some(call => call.url.includes('/api/v1/instances/offers'));
    console.log(`\n${'='.repeat(60)}`);
    console.log(`API /api/v1/instances/offers called: ${offersApiCalled ? '✅ YES' : '❌ NO'}`);
    console.log(`${'='.repeat(60)}\n`);

    console.log('9️⃣  Looking for real machine cards (RTX 4090, RTX 3090, etc)...');

    // Check for machine cards
    const machineCards = await page.locator('[data-testid*="machine"], .machine-card, [class*="card"]').count();
    console.log(`Found ${machineCards} potential machine cards`);

    // Look for specific GPU names
    const pageContent = await page.content();
    const hasRTX4090 = pageContent.includes('RTX 4090') || pageContent.includes('RTX_4090');
    const hasRTX3090 = pageContent.includes('RTX 3090') || pageContent.includes('RTX_3090');
    const hasRealGPU = pageContent.includes('RTX') || pageContent.includes('NVIDIA') || pageContent.includes('Tesla');

    console.log(`\n${'='.repeat(60)}`);
    console.log('REAL MACHINES DETECTION:');
    console.log(`  - Contains "RTX 4090": ${hasRTX4090 ? '✅ YES' : '❌ NO'}`);
    console.log(`  - Contains "RTX 3090": ${hasRTX3090 ? '✅ YES' : '❌ NO'}`);
    console.log(`  - Contains real GPU names: ${hasRealGPU ? '✅ YES' : '❌ NO'}`);
    console.log(`${'='.repeat(60)}\n`);

    // Take screenshot
    const screenshotPath = '/Users/marcos/CascadeProjects/dumontcloud/web/wizard-real-machines-test.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`📸 Screenshot saved to: ${screenshotPath}`);

    // Summary
    console.log(`\n${'='.repeat(60)}`);
    console.log('TEST SUMMARY:');
    console.log(`  1. Auto-login: ✅`);
    console.log(`  2. demo_mode removed: ✅`);
    console.log(`  3. Wizard opened: ✅`);
    console.log(`  4. API /offers called: ${offersApiCalled ? '✅' : '❌'}`);
    console.log(`  5. Real machines shown: ${hasRealGPU ? '✅' : '❌'}`);
    console.log(`${'='.repeat(60)}\n`);

    console.log('✅ Test complete. Browser will stay open for 10 seconds for manual inspection...');
    await page.waitForTimeout(10000);

  } catch (error) {
    console.error('❌ Test failed:', error);
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/web/wizard-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();
