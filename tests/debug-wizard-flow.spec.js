const { test, expect } = require('@playwright/test');

test('Debug Wizard - Complete Flow to /offers API', async ({ page }) => {
  const apiRequests = [];
  const apiResponses = [];

  // Capture API calls
  page.on('request', request => {
    const url = request.url();
    if (url.includes('/api/')) {
      apiRequests.push({ method: request.method(), url });
      console.log(`[API REQUEST] ${request.method()} ${url}`);
    }
  });

  page.on('response', async response => {
    const url = response.url();
    if (url.includes('/api/')) {
      const status = response.status();
      console.log(`[API RESPONSE] ${status} ${url}`);

      try {
        const body = await response.json();
        apiResponses.push({ url, status, body });

        if (url.includes('/offers')) {
          console.log(`\n✓✓✓ /OFFERS RESPONSE ✓✓✓`);
          console.log(`Status: ${status}`);
          console.log(`Body: ${JSON.stringify(body, null, 2)}`);
        }
      } catch (e) {
        // Not JSON, ignore
      }
    }
  });

  console.log('\n=== STEP 1: Navigate with auto_login ===');
  await page.goto('http://localhost:4893/login?auto_login=demo');
  await page.waitForTimeout(2000);
  await page.waitForURL('**/app**', { timeout: 10000 });
  console.log('✓ Redirected to /app');

  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'test-results/flow-step1-initial.png', fullPage: true });

  console.log('\n=== STEP 2: Check current wizard state ===');
  const step1Active = await page.locator('[data-testid="wizard-step-1"]').isVisible();
  console.log(`Step 1 visible: ${step1Active}`);

  // Find region buttons
  const regionButtons = {
    eua: page.locator('button:has-text("EUA")'),
    europa: page.locator('button:has-text("Europa")'),
    asia: page.locator('button:has-text("Ásia")'),
    americaSul: page.locator('button:has-text("América do Sul")')
  };

  console.log('\nChecking region buttons:');
  for (const [name, locator] of Object.entries(regionButtons)) {
    const visible = await locator.isVisible().catch(() => false);
    console.log(`  ${name}: ${visible}`);
  }

  console.log('\n=== STEP 3: Select "América do Sul" region ===');
  const americaSulBtn = regionButtons.americaSul;
  if (await americaSulBtn.isVisible()) {
    await americaSulBtn.click();
    console.log('✓ Clicked "América do Sul"');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'test-results/flow-step3-region-selected.png', fullPage: true });
  } else {
    console.log('✗ "América do Sul" button not visible');
  }

  console.log('\n=== STEP 4: Click "Próximo" (Next) button ===');
  const nextButton = page.locator('button:has-text("Próximo")');
  if (await nextButton.isVisible()) {
    console.log('✓ "Próximo" button visible');

    // Check if it's enabled
    const isDisabled = await nextButton.getAttribute('disabled');
    console.log(`  Disabled: ${isDisabled !== null}`);

    if (isDisabled === null) {
      await nextButton.click();
      console.log('✓ Clicked "Próximo"');
      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'test-results/flow-step4-next-clicked.png', fullPage: true });
    } else {
      console.log('✗ "Próximo" button is disabled');
    }
  } else {
    console.log('✗ "Próximo" button not visible');
  }

  console.log('\n=== STEP 5: Check if we\'re on Hardware step (2/4) ===');
  const step2Active = await page.locator('button:has-text("2/4")').isVisible().catch(() => false);
  console.log(`Step 2 visible: ${step2Active}`);

  // Look for tier/hardware buttons
  const tierButtons = {
    desenvolver: page.locator('button').filter({ hasText: 'Desenvolver' }),
    producao: page.locator('button').filter({ hasText: 'Produção' }),
    treinar: page.locator('button').filter({ hasText: 'Treinar' })
  };

  console.log('\nChecking tier buttons:');
  for (const [name, locator] of Object.entries(tierButtons)) {
    const count = await locator.count();
    const visible = count > 0 && await locator.first().isVisible().catch(() => false);
    console.log(`  ${name}: ${visible} (count: ${count})`);
  }

  console.log('\n=== STEP 6: Select tier if visible ===');
  const desenvolverBtn = tierButtons.desenvolver.first();
  if (await desenvolverBtn.isVisible().catch(() => false)) {
    console.log('✓ "Desenvolver" button visible');
    await desenvolverBtn.click();
    console.log('✓ Clicked "Desenvolver"');
    await page.waitForTimeout(3000); // Wait for API calls
    await page.screenshot({ path: 'test-results/flow-step6-tier-selected.png', fullPage: true });
  } else {
    console.log('✗ Tier buttons not visible - might need different approach');
  }

  console.log('\n=== STEP 7: Final state check ===');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'test-results/flow-step7-final.png', fullPage: true });

  console.log('\n=== API SUMMARY ===');
  console.log(`Total API requests: ${apiRequests.length}`);
  apiRequests.forEach(req => {
    console.log(`  ${req.method} ${req.url}`);
  });

  console.log(`\nTotal API responses: ${apiResponses.length}`);
  apiResponses.forEach(res => {
    console.log(`  ${res.status} ${res.url}`);
  });

  const offersRequest = apiRequests.find(r => r.url.includes('/offers'));
  const offersResponse = apiResponses.find(r => r.url.includes('/offers'));

  console.log('\n=== CRITICAL: /offers endpoint ===');
  if (offersRequest) {
    console.log('✓ /offers request WAS made');
    console.log(`  ${offersRequest.method} ${offersRequest.url}`);
  } else {
    console.log('✗ /offers request was NOT made');
  }

  if (offersResponse) {
    console.log('✓ /offers response received');
    console.log(`  Status: ${offersResponse.status}`);
    console.log(`  Body sample: ${JSON.stringify(offersResponse.body).substring(0, 200)}...`);
  } else {
    console.log('✗ /offers response was NOT received');
  }
});
