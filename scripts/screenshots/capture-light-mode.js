const { chromium } = require('playwright');
const path = require('path');

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const OUTPUT_DIR = path.join(__dirname, '../../artifacts/screenshots');

async function captureLightMode() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/demo-app`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);

    // Try to find and click the theme toggle button
    try {
      // Look for common theme toggle selectors
      const themeButton = await page.locator('button[aria-label*="theme"], button[title*="theme"], button:has-text("tema"), [data-theme-toggle]').first();
      if (await themeButton.isVisible()) {
        await themeButton.click();
        await page.waitForTimeout(1000);
      } else {
        // Try alternative selectors - look for moon/sun icons
        const iconButton = await page.locator('button:has(svg)').filter({ hasText: /moon|sun|tema/i }).first();
        if (await iconButton.count() > 0) {
          await iconButton.click();
          await page.waitForTimeout(1000);
        }
      }
    } catch (e) {
      console.log('⚠️  Não foi possível encontrar botão de tema, continuando...');
    }

    const screenshotPath = path.join(OUTPUT_DIR, 'dashboard-light-mode.png');
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

captureLightMode();
