import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

async function takeScreenshot() {
  const [,, theme, filename] = process.argv;

  if (!theme || !filename) {
    console.error('Usage: node take-advanced-screenshot.js <theme> <filename>');
    console.error('Example: node take-advanced-screenshot.js light advanced.png');
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    colorScheme: theme === 'dark' ? 'dark' : 'light'
  });
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/demo-app`, { waitUntil: 'networkidle', timeout: 30000 });

    // Set theme if needed
    if (theme === 'dark') {
      await page.evaluate(() => {
        localStorage.setItem('theme', 'dark');
        document.documentElement.classList.add('dark');
      });
      await page.waitForTimeout(500);
    }

    // Click on Avançado tab
    await page.click('text=Avançado');
    await page.waitForTimeout(1000);

    await page.screenshot({ path: filename, fullPage: true });
    console.log(`✅ Screenshot saved to ${filename}`);
  } catch (err) {
    console.error(`❌ Error taking screenshot: ${err.message}`);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

takeScreenshot();
