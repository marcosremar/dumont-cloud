import { test } from '@playwright/test';

test('capture wizard modal states', async ({ page }) => {
  console.log('1. Navigating to demo login with auto_login...');
  await page.goto('http://localhost:4893/login?auto_login=demo');
  await page.waitForTimeout(3000);

  console.log('2. Taking screenshot of welcome screen...');
  await page.screenshot({ path: '/tmp/wizard-01-welcome.png', fullPage: true });

  // Click "Começar" button
  const comecarBtn = page.locator('button:has-text("Começar")');
  if (await comecarBtn.isVisible().catch(() => false)) {
    console.log('3. Clicking "Começar" button...');
    await comecarBtn.click({ force: true }); // Force click to bypass overlay
    await page.waitForTimeout(1500);

    console.log('4. Taking screenshot of mode selection (Guiado/Avançado)...');
    await page.screenshot({ path: '/tmp/wizard-02-mode-selection.png', fullPage: true });

    // Get the text around the buttons
    const bodyText = await page.locator('body').textContent();
    console.log('\n=== MODE SELECTION SCREEN TEXT (first 1000 chars) ===');
    console.log(bodyText?.substring(0, 1000));

    // Try clicking Guiado
    const guiadoBtn = page.locator('button:has-text("Guiado")');
    if (await guiadoBtn.isVisible().catch(() => false)) {
      console.log('\n5. Clicking "Guiado" button...');
      await guiadoBtn.click({ force: true });
      await page.waitForTimeout(1500);

      console.log('6. Taking screenshot after Guiado click...');
      await page.screenshot({ path: '/tmp/wizard-03-after-guiado.png', fullPage: true });

      const afterGuiadoText = await page.locator('body').textContent();
      console.log('\n=== AFTER GUIADO CLICK (first 800 chars) ===');
      console.log(afterGuiadoText?.substring(0, 800));
    }
  }

  // Go back and try Avançado
  console.log('\n7. Reloading to try Avançado path...');
  await page.reload();
  await page.waitForTimeout(3000);

  const comecarBtn2 = page.locator('button:has-text("Começar")');
  if (await comecarBtn2.isVisible().catch(() => false)) {
    console.log('8. Clicking "Começar" again...');
    await comecarBtn2.click({ force: true });
    await page.waitForTimeout(1500);

    const avancadoBtn = page.locator('button:has-text("Avançado")');
    if (await avancadoBtn.isVisible().catch(() => false)) {
      console.log('9. Clicking "Avançado" button...');
      await avancadoBtn.click({ force: true });
      await page.waitForTimeout(1500);

      console.log('10. Taking screenshot after Avançado click...');
      await page.screenshot({ path: '/tmp/wizard-04-after-avancado.png', fullPage: true });

      const afterAvancadoText = await page.locator('body').textContent();
      console.log('\n=== AFTER AVANÇADO CLICK (first 800 chars) ===');
      console.log(afterAvancadoText?.substring(0, 800));
    }
  }

  console.log('\n=== SNAPSHOTS COMPLETE ===');
  console.log('Files saved:');
  console.log('  /tmp/wizard-01-welcome.png');
  console.log('  /tmp/wizard-02-mode-selection.png');
  console.log('  /tmp/wizard-03-after-guiado.png');
  console.log('  /tmp/wizard-04-after-avancado.png');
});
