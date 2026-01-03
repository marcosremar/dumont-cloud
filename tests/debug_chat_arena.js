const { chromium } = require('playwright');

async function debugChatArena() {
  console.log('Debugging Chat Arena...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Listen to console messages
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('Console ERROR:', msg.text());
    }
  });

  try {
    await page.goto('http://localhost:4893/demo-app/chat-arena', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    console.log('Page URL:', page.url());

    // Open selector and select models
    const selectorBtn = page.locator('button:has-text("Selecionar")');
    await selectorBtn.click();
    await page.waitForTimeout(500);

    const models = page.locator('.max-h-64 button');
    const modelCount = await models.count();
    console.log('Models found:', modelCount);

    // Select first 2
    for (let i = 0; i < Math.min(2, modelCount); i++) {
      const modelText = await models.nth(i).textContent();
      console.log(`Selecting model ${i+1}: ${modelText.substring(0, 30)}...`);
      await models.nth(i).click();
      await page.waitForTimeout(200);
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // Check panels
    console.log('\nChat panels check...');
    const panels = await page.locator('.flex.flex-col.bg-\\[\\#161b22\\]').count();
    console.log('Panels found:', panels);

    // Type message
    const input = page.locator('input[type="text"]').first();
    await input.fill('Hello test');

    // Send
    const sendBtn = page.locator('button').last();
    console.log('\nSending message...');
    await sendBtn.click();

    // Wait and check
    await page.waitForTimeout(4000);

    console.log('\nChecking for responses...');

    // Look for any message content
    const proseElements = await page.locator('.prose').count();
    console.log('Prose elements:', proseElements);

    const allText = await page.locator('body').textContent();
    if (allText.includes('modo demonstração') || allText.includes('demo')) {
      console.log('Demo response detected in page');
    }

    // Check for loading indicators
    const loading = await page.locator('.animate-bounce').count();
    console.log('Loading indicators:', loading);

    // Check conversation state
    const waitingText = await page.locator('text=/Aguardando mensagem/').count();
    console.log('Waiting message panels:', waitingText);

    // Get panel content
    const panelContent = page.locator('.flex-1.overflow-y-auto.p-4');
    const panelCount = await panelContent.count();
    console.log('\nPanel content areas:', panelCount);

    for (let i = 0; i < Math.min(3, panelCount); i++) {
      const content = await panelContent.nth(i).innerHTML();
      console.log(`Panel ${i+1} content length: ${content.length}`);
      if (content.length > 0) {
        console.log(`  Preview: ${content.substring(0, 200)}...`);
      }
    }

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/chat-arena-debug.png', fullPage: true });
    console.log('\nScreenshot saved to tests/screenshots/chat-arena-debug.png');

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

debugChatArena().catch(console.error);
