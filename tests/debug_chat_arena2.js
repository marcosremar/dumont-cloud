const { chromium } = require('playwright');

async function debugChatArena() {
  console.log('Debugging Chat Arena Responses...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Listen to console
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('Failed') || text.includes('Error') || msg.type() === 'error') {
      console.log(`[Console ${msg.type()}]: ${text.substring(0, 100)}`);
    }
  });

  try {
    await page.goto('http://localhost:4893/demo-app/chat-arena', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    console.log('Page loaded');

    // Open selector
    const selectorBtn = page.locator('button:has-text("Selecionar Modelos")').first();
    await selectorBtn.click();
    await page.waitForTimeout(500);

    // Select models
    const models = page.locator('.max-h-64 button');
    const count = await models.count();
    console.log(`Found ${count} models`);

    for (let i = 0; i < Math.min(2, count); i++) {
      await models.nth(i).click();
      await page.waitForTimeout(200);
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // Check selection badge
    const selectedBadge = await page.locator('text=/\\d+ selecionado/').textContent();
    console.log(`Selection: ${selectedBadge}`);

    // Type message
    const input = page.locator('input[placeholder*="mensagem"]');
    if (await input.count() > 0) {
      await input.fill('Hello test');
      console.log('Message typed');

      // Check if any model is loading
      const anyLoading = await page.locator('text=/loading|Pensando|Loading/i').count();
      console.log(`Loading indicators before send: ${anyLoading}`);

      // Send
      await page.keyboard.press('Enter');
      console.log('Message sent (Enter)');

      // Wait longer for demo response
      console.log('Waiting 5 seconds for response...');
      await page.waitForTimeout(5000);

      // Check loading state
      const loadingAfter = await page.locator('text=/Pensando/').count();
      console.log(`Loading indicators after wait: ${loadingAfter}`);

      // Look for any text that might be a response
      const pageText = await page.locator('body').textContent();

      // Check for demo response patterns
      const demoPatterns = [
        'modo demonstração',
        'linguagem',
        'modelo',
        'ajudar',
        'perguntas',
        'funcionalidade',
        'Arena',
      ];

      console.log('\nSearching for response patterns:');
      for (const pattern of demoPatterns) {
        const found = pageText.toLowerCase().includes(pattern.toLowerCase());
        if (found) {
          console.log(`  Found: "${pattern}"`);
        }
      }

      // Check for message elements
      console.log('\nChecking for message elements:');

      const userMessages = await page.locator('.bg-purple-600').count();
      console.log(`  User messages (purple): ${userMessages}`);

      const assistantMessages = await page.locator('.bg-\\[\\#1c2128\\]').count();
      console.log(`  Assistant messages (dark): ${assistantMessages}`);

      const proseElements = await page.locator('.prose').count();
      console.log(`  Prose elements: ${proseElements}`);

      const markdownElements = await page.locator('p, code, pre').count();
      console.log(`  Markdown-like elements: ${markdownElements}`);

      // Check conversation containers
      const convContainers = page.locator('.flex-1.overflow-y-auto.p-4.space-y-4');
      const convCount = await convContainers.count();
      console.log(`\nConversation containers: ${convCount}`);

      for (let i = 0; i < Math.min(2, convCount); i++) {
        const html = await convContainers.nth(i).innerHTML();
        console.log(`  Container ${i+1} length: ${html.length}`);
        if (html.length > 100) {
          // Has content
          console.log(`  Container ${i+1} has content!`);
          // Check for specific classes
          if (html.includes('bg-purple-600')) {
            console.log(`    - Has user message`);
          }
          if (html.includes('bg-[#1c2128]')) {
            console.log(`    - Has assistant message`);
          }
        }
      }

      // Take screenshot
      await page.screenshot({ path: 'tests/screenshots/chat-arena-debug2.png', fullPage: true });
      console.log('\nScreenshot saved');
    } else {
      console.log('Input not found!');
    }

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

debugChatArena().catch(console.error);
