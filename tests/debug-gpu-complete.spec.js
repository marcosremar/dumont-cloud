const { test, expect } = require('@playwright/test');

test.use({ storageState: { cookies: [], origins: [] } });

test('complete GPU wizard and see offers', async ({ page }) => {
  const apiCalls = [];

  // Monitor API calls
  page.on('response', async res => {
    if (res.url().includes('/api/')) {
      const status = res.status();
      const url = res.url();
      let body = '';
      try {
        body = await res.text();
        if (body.length > 200) body = body.substring(0, 200) + '...';
      } catch (e) {}
      apiCalls.push({ status, url, body });
    }
  });

  // Login
  await page.goto('/login?auto_login=demo');
  await page.waitForURL('**/app**', { timeout: 10000 });
  console.log('Logged in');

  // Step 1: Select region EUA
  await page.locator('button').filter({ hasText: 'EUA' }).click();
  console.log('Selected EUA');

  // Click Next
  await page.locator('button').filter({ hasText: 'Próximo' }).click();
  await page.waitForTimeout(500);
  console.log('Moved to Step 2');

  // Step 2: Click on "Experimentar" tier card
  const experimentarCard = page.locator('text=Experimentar').first();
  await experimentarCard.click();
  console.log('Clicked Experimentar tier');

  // Wait for API call to complete
  await page.waitForTimeout(3000);

  // Take screenshot
  await page.screenshot({ path: 'gpu-offers-result.png', fullPage: true });

  // Print API calls
  console.log('\n=== API Calls ===');
  apiCalls.forEach(call => {
    console.log(`[${call.status}] ${call.url}`);
    if (call.body) console.log(`    Response: ${call.body}`);
  });

  // Check page content for GPU offers
  const pageText = await page.locator('body').textContent();

  if (pageText.includes('RTX')) {
    console.log('\n✅ SUCCESS: Found RTX GPUs on page!');
  } else if (pageText.includes('Nenhuma')) {
    console.log('\n⚠️ No offers found (Nenhuma)');
  } else if (pageText.includes('erro') || pageText.includes('Erro')) {
    console.log('\n❌ Error message found on page');
  }

  // Look for offer cards
  const offerTexts = await page.locator('[class*="card"], [class*="offer"], [class*="machine"]').allTextContents();
  console.log(`\nFound ${offerTexts.length} card elements`);
  offerTexts.slice(0, 5).forEach((t, i) => {
    console.log(`Card ${i + 1}: ${t.substring(0, 100)}`);
  });
});
