const { test, expect } = require('@playwright/test');

test.use({ storageState: { cookies: [], origins: [] } });

test('complete GPU wizard flow', async ({ page }) => {
  // Go to login with demo mode
  await page.goto('/login?auto_login=demo');
  await page.waitForURL('**/app**', { timeout: 10000 });

  console.log('=== Logged in, at /app ===');

  // Step 1: Select a region
  console.log('Step 1: Selecting region EUA...');
  await page.locator('button').filter({ hasText: 'EUA' }).click();
  await page.waitForTimeout(500);

  // Click Next
  console.log('Clicking Próximo...');
  await page.locator('button').filter({ hasText: 'Próximo' }).click();
  await page.waitForTimeout(1000);

  // Step 2: Select a tier
  console.log('Step 2: Looking for tier options...');
  await page.screenshot({ path: 'step2-hardware.png', fullPage: true });

  // Try to find tier cards/buttons
  const starterTier = page.locator('text=Starter').first();
  const basicoTier = page.locator('text=Básico').first();
  const profTier = page.locator('text=Profissional').first();

  if (await starterTier.count() > 0) {
    console.log('Found Starter tier, clicking...');
    await starterTier.click();
  } else if (await basicoTier.count() > 0) {
    console.log('Found Básico tier, clicking...');
    await basicoTier.click();
  } else if (await profTier.count() > 0) {
    console.log('Found Profissional tier, clicking...');
    await profTier.click();
  } else {
    console.log('No tier found, listing all buttons...');
    const allButtons = await page.locator('button').all();
    for (const btn of allButtons.slice(0, 10)) {
      const text = await btn.textContent();
      console.log('  Button:', text?.substring(0, 50));
    }
  }

  await page.waitForTimeout(3000);

  // Take screenshot after selecting tier
  await page.screenshot({ path: 'step2-after-tier.png', fullPage: true });

  // Check for GPU offers in the page
  const pageContent = await page.content();
  if (pageContent.includes('RTX') || pageContent.includes('GPU') || pageContent.includes('offers')) {
    console.log('SUCCESS: Found GPU-related content on page!');
  }

  // Look for machine cards
  const machineCards = page.locator('[class*="machine"], [class*="offer"], [class*="gpu"]');
  const cardCount = await machineCards.count();
  console.log(`Found ${cardCount} machine/offer cards`);

  console.log('\nTest completed. Check screenshots: step2-hardware.png, step2-after-tier.png');
});
