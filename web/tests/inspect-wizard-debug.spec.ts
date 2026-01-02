import { test, expect } from '@playwright/test';

test('inspect wizard with console logging', async ({ page }) => {
  // Capture console messages
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.type(), msg.text()));

  // Capture errors
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));

  // Capture network failures
  page.on('requestfailed', request =>
    console.log('REQUEST FAILED:', request.url(), request.failure()?.errorText)
  );

  console.log('Navigating to demo login with auto_login...');
  await page.goto('http://localhost:4893/login?auto_login=demo', {
    waitUntil: 'domcontentloaded'
  });

  // Wait longer for React to load
  await page.waitForTimeout(5000);

  // Check current URL
  console.log('Current URL:', page.url());

  // Check if there's any HTML
  const html = await page.content();
  console.log('\n=== HTML LENGTH ===');
  console.log(html.length, 'characters');

  // Check for React root
  const hasRoot = await page.locator('#root').isVisible().catch(() => false);
  console.log('Has #root element:', hasRoot);

  if (hasRoot) {
    const rootContent = await page.locator('#root').innerHTML();
    console.log('\n=== ROOT CONTENT (first 1000 chars) ===');
    console.log(rootContent.substring(0, 1000));
  }

  // Take screenshot
  await page.screenshot({ path: '/tmp/wizard-debug.png', fullPage: true });
  console.log('Screenshot saved to /tmp/wizard-debug.png');
});
