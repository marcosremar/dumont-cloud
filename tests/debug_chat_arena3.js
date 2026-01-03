const { chromium } = require('playwright');

async function debugChatArena() {
  console.log('Debug: Using same flow as test...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto('http://localhost:4893/demo-app/chat-arena', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Same as test: Open model selector (use the header button)
    console.log('2. Opening model selector...');
    const selectorBtn = page.locator('button:has-text("Selecionar Modelos")').first();
    await selectorBtn.click();
    await page.waitForTimeout(500);
    console.log('   OK: Selector opened\n');

    // Same as test: Select multiple models
    console.log('3. Selecting multiple models...');
    const modelButtons = page.locator('.max-h-64 button');
    const modelCount = await modelButtons.count();
    console.log(`   Found ${modelCount} models available`);

    let selectedCount = 0;
    for (let i = 0; i < Math.min(2, modelCount); i++) {
      await modelButtons.nth(i).click();
      await page.waitForTimeout(200);
      selectedCount++;
    }
    console.log(`   OK: Selected ${selectedCount} models\n`);

    // Close dropdown
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // Check panels
    console.log('4. Checking comparison panels...');
    const panels = page.locator('.bg-\\[\\#161b22\\].border.border-white\\/5.rounded-xl');
    const panelCount = await panels.count();
    console.log(`   Found ${panelCount} chat panel(s)\n`);

    // Same as test: Type and send message
    console.log('5. Sending test message...');
    const chatInput = page.locator('input[placeholder*="mensagem"], input[placeholder*="message"]').first();
    await chatInput.fill('Compare the number 42 - give a brief fun fact');
    await page.waitForTimeout(100);

    // Send message - USING THE BUTTON LIKE THE TEST
    const sendBtn = page.locator('button:has(svg)').last();
    await sendBtn.click();
    console.log('   Message sent\n');

    // Wait longer
    console.log('6. Waiting for responses...');
    await page.waitForTimeout(5000);

    // Check what we got
    console.log('Checking for content:');

    // Simple text search
    const bodyText = await page.locator('body').textContent();

    // Check for demo responses
    if (bodyText.includes('modo demonstração') ||
        bodyText.includes('linguagem') ||
        bodyText.includes('Compare')) {
      console.log('  Found response text in page');
    }

    // Check counts like the test
    const assistantMessages = page.locator('div[class*="bg-"][class*="1c2128"]');
    const responseCount = await assistantMessages.count();
    console.log(`  Assistant messages (test selector): ${responseCount}`);

    const userMessages = page.locator('div[class*="bg-purple"]');
    const userCount = await userMessages.count();
    console.log(`  User messages (test selector): ${userCount}`);

    const proseContent = await page.locator('.prose').count();
    console.log(`  Prose elements: ${proseContent}`);

    // Try other selectors
    const roundedXl = await page.locator('.rounded-xl.p-3').count();
    console.log(`  Rounded message boxes: ${roundedXl}`);

    const textSm = await page.locator('.text-sm.bg-purple-600, .text-sm.text-gray-200').count();
    console.log(`  Text-sm messages: ${textSm}`);

    // Check if messages are in the conversation containers
    const convContainers = page.locator('.flex-1.overflow-y-auto.p-4');
    const convCount = await convContainers.count();
    console.log(`  Conversation containers: ${convCount}`);

    if (convCount > 0) {
      const firstConvHtml = await convContainers.first().innerHTML();
      console.log(`  First container HTML length: ${firstConvHtml.length}`);

      if (firstConvHtml.includes('Hello') || firstConvHtml.includes('Compare')) {
        console.log('  User message found in container');
      }
      if (firstConvHtml.includes('demonstração') || firstConvHtml.includes('demo')) {
        console.log('  Demo response found in container');
      }
    }

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/chat-arena-debug3.png', fullPage: true });
    console.log('\nScreenshot saved');

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

debugChatArena().catch(console.error);
