const { chromium } = require('playwright');

async function debugChatArena() {
  console.log('Debug: Finding the correct send button...\n');

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

    // Type message
    const chatInput = page.locator('input[placeholder*="mensagem"]').first();
    await chatInput.fill('Test message');
    await page.waitForTimeout(100);

    // Find all buttons and log them
    console.log('Finding buttons...');
    const allButtons = page.locator('button');
    const buttonCount = await allButtons.count();
    console.log(`Total buttons: ${buttonCount}`);

    // Look for send button specifically
    const sendIcon = page.locator('button svg[class*="FiSend"], button:has(svg[stroke="currentColor"])');
    console.log(`Send icon buttons: ${await sendIcon.count()}`);

    // The send button should be in the input area
    const inputArea = page.locator('.bg-\\[\\#161b22\\].border.border-white\\/5.rounded-xl.p-4');
    const inputAreaButtons = inputArea.locator('button');
    console.log(`Buttons in input area: ${await inputAreaButtons.count()}`);

    // Try using Enter key instead
    console.log('\nUsing Enter key to send...');
    await chatInput.press('Enter');
    await page.waitForTimeout(4000);

    // Check results
    const convContainers = page.locator('.flex-1.overflow-y-auto.p-4');
    const firstConvHtml = await convContainers.first().innerHTML();
    console.log(`Container HTML length after Enter: ${firstConvHtml.length}`);

    if (firstConvHtml.length > 100) {
      console.log('SUCCESS: Messages received!');

      // Count messages
      const userMsgs = (firstConvHtml.match(/bg-purple-600/g) || []).length;
      const assistMsgs = (firstConvHtml.match(/bg-\[#1c2128\]/g) || []).length;
      console.log(`User messages: ${userMsgs}`);
      console.log(`Assistant messages: ${assistMsgs}`);
    }

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

debugChatArena().catch(console.error);
