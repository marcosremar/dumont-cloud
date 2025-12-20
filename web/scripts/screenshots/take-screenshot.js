import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

async function takeScreenshot() {
  const [,, route, theme, filename] = process.argv;

  if (!route || !theme || !filename) {
    console.error('Usage: node take-screenshot.js <route> <theme> <filename>');
    console.error('Example: node take-screenshot.js demo-app light dashboard.png');
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    colorScheme: theme === 'dark' ? 'dark' : 'light'
  });
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/${route}`, { waitUntil: 'networkidle', timeout: 30000 });

    // Set theme if needed
    if (theme === 'dark') {
      await page.evaluate(() => {
        localStorage.setItem('theme', 'dark');
        document.documentElement.classList.add('dark');
      });
      await page.waitForTimeout(500);
    }

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
