const { chromium } = require('playwright');
const path = require('path');

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const OUTPUT_DIR = path.join(__dirname, '../../artifacts/screenshots');

async function capture(pagePath, outputName) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}${pagePath}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);

    const screenshotPath = path.join(OUTPUT_DIR, outputName);
    await page.screenshot({
      path: screenshotPath,
      fullPage: true
    });

    console.log(`✅ Screenshot salvo: ${screenshotPath}`);
  } catch (err) {
    console.error(`❌ Erro: ${err.message}`);
  } finally {
    await browser.close();
  }
}

const pagePath = process.argv[2] || '/demo-app';
const outputName = process.argv[3] || 'screenshot.png';

capture(pagePath, outputName);
