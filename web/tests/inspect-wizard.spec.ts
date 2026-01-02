import { test, expect } from '@playwright/test';

test('inspect wizard modal layout', async ({ page }) => {
  console.log('Navigating to demo login with auto_login...');
  await page.goto('http://localhost:4893/login?auto_login=demo');

  // Wait for auto-login to complete
  await page.waitForTimeout(3000);

  // Check current URL
  const currentUrl = page.url();
  console.log('Current URL:', currentUrl);

  // Take initial screenshot
  await page.screenshot({ path: '/tmp/wizard-initial.png', fullPage: true });
  console.log('Initial screenshot saved');

  // Check for modal
  const modal = page.locator('[role="dialog"]');
  const modalVisible = await modal.isVisible().catch(() => false);
  console.log('Modal visible:', modalVisible);

  // Check for buttons
  const guiadoButton = page.locator('text="Guiado"');
  const avancadoButton = page.locator('text="Avançado"');
  const pularButton = page.locator('text="Pular tudo"');

  const hasGuiado = await guiadoButton.isVisible().catch(() => false);
  const hasAvancado = await avancadoButton.isVisible().catch(() => false);
  const hasPular = await pularButton.isVisible().catch(() => false);

  console.log('Guiado button visible:', hasGuiado);
  console.log('Avançado button visible:', hasAvancado);
  console.log('Pular button visible:', hasPular);

  // Get all text content
  const bodyText = await page.locator('body').textContent();
  console.log('\n=== PAGE CONTENT (first 800 chars) ===');
  console.log(bodyText?.substring(0, 800));

  // If Guiado button exists, click it and see what happens
  if (hasGuiado) {
    console.log('\n=== CLICKING GUIADO BUTTON ===');
    await guiadoButton.click();
    await page.waitForTimeout(1500);

    const afterClickText = await page.locator('body').textContent();
    console.log('After Guiado click (first 800 chars):');
    console.log(afterClickText?.substring(0, 800));

    await page.screenshot({ path: '/tmp/wizard-after-guiado.png', fullPage: true });
    console.log('After-Guiado screenshot saved');
  }

  // Try clicking Avançado if available
  if (hasAvancado) {
    console.log('\n=== CLICKING AVANÇADO BUTTON ===');

    // First, refresh or go back to initial state
    await page.reload();
    await page.waitForTimeout(2000);

    const avancadoBtn = page.locator('text="Avançado"');
    if (await avancadoBtn.isVisible().catch(() => false)) {
      await avancadoBtn.click();
      await page.waitForTimeout(1500);

      const afterAvancadoText = await page.locator('body').textContent();
      console.log('After Avançado click (first 800 chars):');
      console.log(afterAvancadoText?.substring(0, 800));

      await page.screenshot({ path: '/tmp/wizard-after-avancado.png', fullPage: true });
      console.log('After-Avançado screenshot saved');
    }
  }
});
