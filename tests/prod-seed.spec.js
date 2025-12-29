// Seed file for production testing
const { test } = require('@playwright/test');

test('setup production page', async ({ page }) => {
  await page.goto('https://cloud.dumontai.com');
});
