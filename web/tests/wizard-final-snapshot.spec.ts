import { test } from '@playwright/test';

test('final wizard modal snapshot', async ({ page }) => {
  console.log('Navigating to auto-login...');
  await page.goto('http://localhost:4893/login?auto_login=demo');
  await page.waitForTimeout(3000);

  // Take initial screenshot showing welcome modal
  await page.screenshot({ path: '/tmp/wizard-screen-1-welcome.png', fullPage: true });
  console.log('Screenshot 1: Welcome modal saved');

  // Scroll the Guiado/Avançado buttons into view
  const guiadoButton = page.locator('[data-testid="config-guided"]');
  await guiadoButton.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);

  // Take screenshot showing the mode selector
  await page.screenshot({ path: '/tmp/wizard-screen-2-mode-selector.png', fullPage: true });
  console.log('Screenshot 2: Mode selector (Guiado/Avançado) saved');

  // Get bounding box to understand positioning
  const box = await guiadoButton.boundingBox();
  console.log('Guiado button position:', box);

  // Click Guiado and see what happens
  console.log('\nClicking Guiado button...');
  await guiadoButton.click({ force: true });
  await page.waitForTimeout(1000);

  const afterClickText = await page.locator('body').textContent();
  console.log('Text after Guiado click contains:');
  console.log('  - "Região":', afterClickText?.includes('Região'));
  console.log('  - "Hardware":', afterClickText?.includes('Hardware'));
  console.log('  - "Estratégia":', afterClickText?.includes('Estratégia'));

  await page.screenshot({ path: '/tmp/wizard-screen-3-after-guiado.png', fullPage: true });
  console.log('Screenshot 3: After Guiado click saved');

  // Check what step we're on
  const step1 = page.locator('[data-testid="wizard-step-1"]');
  const step1Active = await step1.evaluate(el => el.classList.contains('active'));
  console.log('Step 1 (Região) active:', step1Active);

  console.log('\n=== ANALYSIS ===');
  console.log('The wizard modal has multiple screens:');
  console.log('1. Welcome screen with "Começar" button');
  console.log('2. Mode selection with "Guiado" and "Avançado" buttons');
  console.log('3. Step-by-step wizard (Região, Hardware, Estratégia, Provisionar)');
  console.log('\nClicking "Guiado" or "Avançado" determines wizard behavior but may not visually change much');
});
