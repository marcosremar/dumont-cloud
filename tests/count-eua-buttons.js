const { chromium } = require('@playwright/test');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto('http://localhost:4898/demo-app');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2000);

  // Count all buttons with "EUA"
  const euaButtons = await page.locator('button:has-text("EUA")').all();
  console.log(`\nTotal buttons with "EUA": ${euaButtons.length}\n`);

  for (let i = 0; i < euaButtons.length; i++) {
    const button = euaButtons[i];
    const text = await button.textContent();
    const testId = await button.getAttribute('data-testid');
    const className = await button.getAttribute('class');

    console.log(`Button ${i + 1}:`);
    console.log(`  Text: ${text.trim()}`);
    console.log(`  data-testid: ${testId}`);
    console.log(`  Class (first 80 chars): ${className?.substring(0, 80)}...`);
    console.log('');
  }

  await browser.close();
})();
