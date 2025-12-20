const { chromium } = require('playwright');
const path = require('path');

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const OUTPUT_DIR = path.join(__dirname, '../../artifacts/screenshots');

async function captureAIMode() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/demo-app`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(2000);

    // Click on AI Assistant button
    try {
      const aiButton = await page.locator('button:has-text("AI Assistant")').first();
      if (await aiButton.isVisible()) {
        await aiButton.click();
        await page.waitForTimeout(1500);
      }
    } catch (e) {
      console.log('⚠️  Não foi possível clicar no botão AI Assistant');
    }

    const screenshotPath = path.join(OUTPUT_DIR, 'dashboard-ai-mode.png');
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

captureAIMode();
