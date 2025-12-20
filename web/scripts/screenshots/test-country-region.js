import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

async function testCountryRegion() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/demo-app`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1000);

    // Test 1: Initial state (no selection)
    await page.screenshot({ path: '/tmp/test-initial.png', fullPage: true });
    console.log('✅ Screenshot: Initial state');

    // Test 2: Select a REGION (Europa) - should highlight all European countries
    const searchInput = page.locator('input[placeholder*="Buscar país"]');
    await searchInput.fill('Europa');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: '/tmp/test-europa-region.png', fullPage: true });
    console.log('✅ Screenshot: Europa (region) - all countries highlighted');

    // Test 3: Clear and select a COUNTRY (Brasil) - should highlight only Brazil
    await searchInput.clear();
    await page.waitForTimeout(500);
    await searchInput.fill('Brasil');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: '/tmp/test-brasil-country.png', fullPage: true });
    console.log('✅ Screenshot: Brasil (country) - only Brazil highlighted');

    // Test 4: Clear and select another country (Japão)
    await searchInput.clear();
    await page.waitForTimeout(500);
    await searchInput.fill('Japão');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: '/tmp/test-japao-country.png', fullPage: true });
    console.log('✅ Screenshot: Japão (country) - only Japan highlighted');

    // Test 5: Click the X to clear selection
    const clearButton = page.locator('button[title="Remover seleção"]');
    await clearButton.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/test-cleared.png', fullPage: true });
    console.log('✅ Screenshot: Selection cleared - back to initial state');

    console.log('\n✅ All tests completed!');

  } catch (err) {
    console.error(`❌ Error: ${err.message}`);
  } finally {
    await browser.close();
  }
}

testCountryRegion();
