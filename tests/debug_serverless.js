const { chromium } = require('playwright');

async function debugServerless() {
  console.log('Debug: Starting browser...');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('Debug: Navigating to serverless page...');
    await page.goto('http://localhost:4893/demo-app/serverless', { waitUntil: 'networkidle' });

    // Wait for page to fully load
    await page.waitForTimeout(2000);

    // Get page content
    const title = await page.title();
    console.log('Page title:', title);

    const url = page.url();
    console.log('Current URL:', url);

    // Get page HTML
    const bodyContent = await page.locator('body').innerHTML();
    console.log('\nPage HTML preview (first 2000 chars):');
    console.log(bodyContent.substring(0, 2000));

    // Take screenshot
    await page.screenshot({ path: 'tests/serverless_debug.png', fullPage: true });
    console.log('\nScreenshot saved to tests/serverless_debug.png');

    // Check for any errors in console
    console.log('\nChecking for console errors...');
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('Console error:', msg.text());
      }
    });

    // Try to find any text on page
    const allText = await page.locator('body').textContent();
    console.log('\nAll text on page (first 1000 chars):');
    console.log(allText.substring(0, 1000));

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

debugServerless().catch(console.error);
