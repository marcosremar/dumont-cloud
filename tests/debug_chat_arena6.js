const { chromium } = require('playwright');

async function debugChatArena() {
  console.log('Debug: Match exact test flow...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Navigate
    await page.goto('http://localhost:4893/demo-app/chat-arena', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    console.log('1. Page loaded');

    // 2. Open selector - SAME AS TEST
    const selectorBtn = page.locator('button:has-text("Selecionar Modelos")').first();
    await selectorBtn.click();
    await page.waitForTimeout(500);
    console.log('2. Selector opened');

    // 3. Select models - SAME AS TEST
    const modelButtons = page.locator('.max-h-64 button');
    const modelCount = await modelButtons.count();
    console.log(`3. Found ${modelCount} models`);

    for (let i = 0; i < Math.min(2, modelCount); i++) {
      await modelButtons.nth(i).click();
      await page.waitForTimeout(200);
    }
    console.log('   Selected 2 models');

    // Close dropdown
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // 4. Check panels - SAME AS TEST
    const panels = page.locator('.bg-\\[\\#161b22\\].border.border-white\\/5.rounded-xl');
    const panelCount = await panels.count();
    console.log(`4. Panels: ${panelCount}`);

    // 5. Send message - SAME AS TEST
    const chatInput = page.locator('input[placeholder*="mensagem"], input[placeholder*="message"]').first();
    await chatInput.fill('Compare the number 42 - give a brief fun fact');
    await page.waitForTimeout(100);
    await chatInput.press('Enter');
    console.log('5. Message sent');

    // 6. Wait - SAME AS TEST
    await page.waitForTimeout(4000);
    console.log('6. Waited 4s');

    // 7. Check containers - SAME AS TEST
    const convContainers = page.locator('.flex-1.overflow-y-auto.p-4');
    const containerCount = await convContainers.count();
    console.log(`7. Container count: ${containerCount}`);

    let totalUserMsgs = 0;
    let totalAssistMsgs = 0;

    for (let i = 0; i < containerCount; i++) {
      const html = await convContainers.nth(i).innerHTML();
      console.log(`   Container ${i}: ${html.length} chars`);

      const userMsgs = (html.match(/bg-purple-600/g) || []).length;
      const assistMsgs = (html.match(/1c2128/g) || []).length;

      console.log(`     User: ${userMsgs}, Assist: ${assistMsgs}`);

      totalUserMsgs += userMsgs;
      totalAssistMsgs += assistMsgs;
    }

    console.log(`\nTotal: User=${totalUserMsgs}, Assist=${totalAssistMsgs}`);

    // Also try different container selector
    console.log('\nAlternative selectors:');
    const alt1 = page.locator('.flex-1.overflow-y-auto');
    console.log(`  .flex-1.overflow-y-auto: ${await alt1.count()}`);

    const alt2 = page.locator('.space-y-4.custom-scrollbar');
    console.log(`  .space-y-4.custom-scrollbar: ${await alt2.count()}`);

    // Try container with more specific selector
    const msgContainer = page.locator('.flex.flex-col.bg-\\[\\#161b22\\] .flex-1.overflow-y-auto');
    const msgCount = await msgContainer.count();
    console.log(`  Panel message containers: ${msgCount}`);

    if (msgCount > 0) {
      const html = await msgContainer.first().innerHTML();
      console.log(`  First container: ${html.length} chars`);
      console.log(`    1c2128 matches: ${(html.match(/1c2128/g) || []).length}`);
    }

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

debugChatArena().catch(console.error);
