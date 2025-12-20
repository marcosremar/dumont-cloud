import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

async function testButtons() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/demo-app`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1000);

    // Test 1: Initial state
    await page.screenshot({ path: '/tmp/btn-initial.png', fullPage: true });
    console.log('✅ Screenshot: Initial state');

    // Test 2: Click on Europa button
    console.log('Clicking Europa button...');
    await page.click('button:has-text("Europa")');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: '/tmp/btn-europa-click.png', fullPage: true });
    console.log('✅ Screenshot: After clicking Europa button');

    // Test 3: Clear and click on EUA button
    const clearBtn = page.locator('button[title="Remover seleção"]');
    if (await clearBtn.isVisible()) {
      await clearBtn.click();
      await page.waitForTimeout(500);
    }

    console.log('Clicking EUA button...');
    await page.click('button:has-text("EUA")');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: '/tmp/btn-eua-click.png', fullPage: true });
    console.log('✅ Screenshot: After clicking EUA button');

    console.log('\n✅ All button tests completed!');

  } catch (err) {
    console.error(`❌ Error: ${err.message}`);
  } finally {
    await browser.close();
  }
}

testButtons();
