import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

async function testSearch() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/demo-app`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1000);

    // Type "Brasil" in the search field
    const searchInput = page.locator('input[placeholder*="Buscar país"]');
    await searchInput.fill('Brasil');
    await page.waitForTimeout(1500);

    // Take screenshot showing the search result
    await page.screenshot({ path: '/tmp/search-brasil-light.png', fullPage: true });
    console.log('✅ Screenshot saved: Brasil search (light mode)');

    // Clear and try another search
    await searchInput.clear();
    await searchInput.fill('Tokyo');
    await page.waitForTimeout(1500);

    await page.screenshot({ path: '/tmp/search-tokyo-light.png', fullPage: true });
    console.log('✅ Screenshot saved: Tokyo search (light mode)');

    // Switch to dark mode
    await page.evaluate(() => {
      localStorage.setItem('theme', 'dark');
      document.documentElement.classList.add('dark');
    });
    await page.waitForTimeout(500);

    // Clear and search for Germany
    await searchInput.clear();
    await searchInput.fill('Alemanha');
    await page.waitForTimeout(1500);

    await page.screenshot({ path: '/tmp/search-alemanha-dark.png', fullPage: true });
    console.log('✅ Screenshot saved: Alemanha search (dark mode)');

  } catch (err) {
    console.error(`❌ Error: ${err.message}`);
  } finally {
    await browser.close();
  }
}

testSearch();
