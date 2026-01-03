const { chromium } = require('playwright');

async function debugChatArena() {
  console.log('Debug: Check actual HTML of messages...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto('http://localhost:4893/demo-app/chat-arena', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Select models
    const selectorBtn = page.locator('button:has-text("Selecionar Modelos")').first();
    await selectorBtn.click();
    await page.waitForTimeout(500);

    const modelButtons = page.locator('.max-h-64 button');
    for (let i = 0; i < 2; i++) {
      await modelButtons.nth(i).click();
      await page.waitForTimeout(200);
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // Type and send
    const chatInput = page.locator('input[placeholder*="mensagem"]').first();
    await chatInput.fill('Test');
    await chatInput.press('Enter');
    await page.waitForTimeout(4000);

    // Get container HTML
    const convContainers = page.locator('.flex-1.overflow-y-auto.p-4');
    const html = await convContainers.first().innerHTML();

    console.log('Container HTML:');
    console.log('---');
    console.log(html);
    console.log('---');

    // Check for patterns
    console.log('\nPattern matching:');
    console.log('  bg-purple-600:', (html.match(/bg-purple-600/g) || []).length);
    console.log('  bg-[#1c2128]:', (html.match(/bg-\[#1c2128\]/g) || []).length);
    console.log('  #1c2128:', (html.match(/#1c2128/g) || []).length);
    console.log('  1c2128:', (html.match(/1c2128/g) || []).length);
    console.log('  prose:', (html.match(/prose/g) || []).length);
    console.log('  rounded-xl:', (html.match(/rounded-xl/g) || []).length);

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

debugChatArena().catch(console.error);
