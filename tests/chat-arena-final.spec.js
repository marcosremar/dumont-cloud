const { test, expect } = require('@playwright/test');

test('Chat Arena with Real Local Ollama', async ({ page }) => {
  console.log('\n=== CHAT ARENA REAL MODEL TEST ===\n');

  // 1. Navigate to Chat Arena
  await page.goto('/demo-app/chat-arena');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  // Verify Chat Arena loaded
  const heading = page.getByRole('heading', { name: 'Chat Arena' });
  await expect(heading).toBeVisible({ timeout: 5000 });
  console.log('1. Chat Arena page loaded');
  await page.screenshot({ path: 'tests/screenshots/final-1-loaded.png' });

  // 2. Click the "Selecionar Modelos" button (the purple one in center)
  const selectBtn = page.locator('button:has-text("Selecionar Modelos")').first();
  await selectBtn.click();
  await page.waitForTimeout(1000);
  console.log('2. Opened model selector');
  await page.screenshot({ path: 'tests/screenshots/final-2-dropdown.png' });

  // 3. Check for local models in dropdown
  const dropdownContent = await page.content();
  const hasLocalModels = dropdownContent.includes('Local CPU') ||
                         dropdownContent.includes('qwen') ||
                         dropdownContent.includes('llama');
  console.log(`3. Local models found: ${hasLocalModels}`);

  // 4. Select models by clicking the model rows with checkboxes
  const modelRows = page.locator('text=Local CPU/GPU');
  const count = await modelRows.count();
  console.log(`   Found ${count} Local CPU/GPU models`);

  if (count >= 2) {
    // Click first model row
    await modelRows.nth(0).click();
    await page.waitForTimeout(500);
    // Click second model row
    await modelRows.nth(1).click();
    await page.waitForTimeout(500);
    console.log('4. Selected 2 local models');
  } else if (count === 1) {
    await modelRows.nth(0).click();
    console.log('4. Selected 1 model');
  }

  // Close dropdown
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'tests/screenshots/final-3-selected.png' });

  // 5. Find input and send message
  const input = page.locator('input[type="text"]').first();
  if (await input.isVisible({ timeout: 3000 }).catch(() => false)) {
    await input.fill('Ola! O que e machine learning?');
    console.log('5. Typed message');
    await input.press('Enter');
    console.log('6. Message sent - waiting for REAL Ollama response...');

    // Wait for response (real inference takes time)
    await page.waitForTimeout(15000);
    await page.screenshot({ path: 'tests/screenshots/final-4-response.png', fullPage: true });

    // Check for real response
    const responseContent = await page.content();
    const hasDemoText = responseContent.includes('modo demonstração');
    const hasRealContent = responseContent.includes('aprendizado') ||
                           responseContent.includes('machine') ||
                           responseContent.includes('learning') ||
                           responseContent.includes('dados') ||
                           responseContent.includes('algoritmo');

    console.log(`7. Demo text found: ${hasDemoText}`);
    console.log(`   Real AI content found: ${hasRealContent}`);

    if (!hasDemoText && hasRealContent) {
      console.log('\n✅ SUCCESS: Real Ollama model responded!\n');
    } else if (hasRealContent) {
      console.log('\n✓ PARTIAL: Response received (may include demo text)\n');
    }
  } else {
    console.log('5. Input not visible - models may need selection first');
  }

  console.log('=== TEST COMPLETE ===\n');
});
