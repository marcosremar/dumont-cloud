import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

async function testMapFunctionality() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/demo-app`, { waitUntil: 'networkidle', timeout: 30000 });

    console.log('✅ Page loaded');

    // Test 1: Click on region button (Europa)
    console.log('\n📍 Test 1: Clicking Europa button...');
    await page.click('button:has-text("Europa")');
    await page.waitForTimeout(1000);
    console.log('✅ Europa button clicked');

    // Test 2: Click on another region (Ásia)
    console.log('\n📍 Test 2: Clicking Ásia button...');
    await page.click('button:has-text("Ásia")');
    await page.waitForTimeout(1000);
    console.log('✅ Ásia button clicked');

    // Test 3: Search for a country
    console.log('\n🔍 Test 3: Searching for "Brasil"...');
    const searchInput = await page.locator('input[placeholder*="Digite um país"]');
    await searchInput.fill('Brasil');
    await page.waitForTimeout(1000);
    console.log('✅ Search input filled');

    // Test 4: Clear search
    console.log('\n❌ Test 4: Clearing search...');
    await page.click('button:has(svg)'); // Click the X button
    await page.waitForTimeout(500);
    console.log('✅ Search cleared');

    // Test 5: Check zoom controls
    console.log('\n🔎 Test 5: Testing zoom controls...');
    const zoomInButton = await page.locator('button:has-text("+"), button:has(svg.lucide-plus)').first();
    if (await zoomInButton.count() > 0) {
      await zoomInButton.click();
      console.log('✅ Zoom in button clicked');
    } else {
      console.log('⚠️  Zoom in button not found');
    }

    await page.waitForTimeout(2000);

    console.log('\n✅ All tests completed!');
    console.log('Press Ctrl+C to close the browser...');

    // Keep browser open for inspection
    await page.waitForTimeout(30000);

  } catch (err) {
    console.error(`❌ Error: ${err.message}`);
  } finally {
    await browser.close();
  }
}

testMapFunctionality();
