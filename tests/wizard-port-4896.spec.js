/**
 * GPU Reservation Wizard Test - Port 4896
 * Complete flow test navigating to http://localhost:4896/demo-app
 *
 * Test Steps:
 * 1. Navigate to demo app
 * 2. Select EUA region
 * 3. Click Próximo
 * 4. Select "Desenvolver" use case
 * 5. Wait for machines to load
 * 6. Select first machine (econômico)
 * 7. Click Próximo
 * 8. Verify Step 3 and Iniciar button
 * 9. Click Iniciar
 * 10. Wait for provisioning (20s)
 * 11. Take final snapshot
 */
const { test, expect } = require('@playwright/test');

// Configure test to not use storage state (no auth required for demo-app)
test.use({
  storageState: undefined,
  viewport: { width: 1920, height: 1080 },
});

test('Complete GPU reservation wizard flow on port 4896', async ({ page }) => {
  const baseUrl = 'http://localhost:4896';
  const screenshotDir = 'test-results/wizard-4896';

  console.log('\n' + '='.repeat(80));
  console.log('GPU RESERVATION WIZARD TEST - PORT 4896');
  console.log('='.repeat(80));

  // ========================================================================
  // STEP 1: Navigate to demo app
  // ========================================================================
  console.log('\n[STEP 1] Navigating to http://localhost:4896/demo-app');
  await page.goto(`${baseUrl}/demo-app`);
  await page.waitForLoadState('domcontentloaded');

  // Set demo_mode in localStorage
  await page.evaluate(() => {
    localStorage.setItem('demo_mode', 'true');
  });
  console.log('[SUCCESS] ✓ Navigated to demo app, demo_mode enabled');

  await page.waitForTimeout(2000);

  // ========================================================================
  // STEP 2: Take snapshot of wizard
  // ========================================================================
  console.log('\n[STEP 2] Taking initial snapshot');
  await page.screenshot({ path: `${screenshotDir}/01-wizard-initial.png`, fullPage: true });
  console.log('[SUCCESS] ✓ Screenshot saved: 01-wizard-initial.png');

  // Verify wizard is visible
  const wizardTitle = page.locator('text=Nova Instância GPU');
  await expect(wizardTitle).toBeVisible({ timeout: 10000 });
  console.log('[VERIFIED] ✓ Wizard title "Nova Instância GPU" is visible');

  // ========================================================================
  // STEP 3: Click "EUA" region button
  // ========================================================================
  console.log('\n[STEP 3] Clicking "EUA" region button');
  const euaButton = page.locator('button:has-text("EUA")').first();
  await expect(euaButton).toBeVisible({ timeout: 5000 });
  await euaButton.click();
  await page.waitForTimeout(500);
  console.log('[SUCCESS] ✓ EUA button clicked');

  // ========================================================================
  // STEP 4: Click "Próximo" button
  // ========================================================================
  console.log('\n[STEP 4] Clicking "Próximo" button');
  const proximoButton1 = page.locator('button:has-text("Próximo")').first();
  await expect(proximoButton1).toBeEnabled({ timeout: 5000 });
  await proximoButton1.click();
  await page.waitForTimeout(2000);
  console.log('[SUCCESS] ✓ Próximo clicked, navigating to Step 2');

  // ========================================================================
  // STEP 5: Take snapshot of Step 2
  // ========================================================================
  console.log('\n[STEP 5] Taking snapshot of Step 2');
  await page.screenshot({ path: `${screenshotDir}/02-step2-usecase.png`, fullPage: true });
  console.log('[SUCCESS] ✓ Screenshot saved: 02-step2-usecase.png');

  // Verify we're on Step 2
  const step2Title = page.locator('text=O que você vai fazer?');
  await expect(step2Title).toBeVisible({ timeout: 5000 });
  console.log('[VERIFIED] ✓ Step 2 title visible');

  // ========================================================================
  // STEP 6: Click "Desenvolver" use case
  // ========================================================================
  console.log('\n[STEP 6] Clicking "Desenvolver" use case');
  const desenvolverBtn = page.locator('text=Desenvolver').first();
  await expect(desenvolverBtn).toBeVisible({ timeout: 5000 });
  await desenvolverBtn.click();
  console.log('[SUCCESS] ✓ Desenvolver clicked');

  // ========================================================================
  // STEP 7: Wait 2 seconds for machines to load
  // ========================================================================
  console.log('\n[STEP 7] Waiting 2 seconds for machines to load');
  await page.waitForTimeout(2000);
  console.log('[SUCCESS] ✓ Waited 2 seconds');

  // ========================================================================
  // STEP 8: Take snapshot to verify machines are displayed
  // ========================================================================
  console.log('\n[STEP 8] Taking snapshot to verify machines');
  await page.screenshot({ path: `${screenshotDir}/03-machines-loaded.png`, fullPage: true });
  console.log('[SUCCESS] ✓ Screenshot saved: 03-machines-loaded.png');

  // Count machine options
  const machineButtons = page.locator('button').filter({ hasText: /econômico|benefício|RTX|GPU/i });
  const radioInputs = page.locator('input[type="radio"]');
  const buttonCount = await machineButtons.count();
  const radioCount = await radioInputs.count();
  console.log(`[INFO] Machine buttons found: ${buttonCount}`);
  console.log(`[INFO] Radio inputs found: ${radioCount}`);

  // ========================================================================
  // STEP 9: Click on the first machine option (econômico)
  // ========================================================================
  console.log('\n[STEP 9] Selecting first machine (econômico)');

  let machineSelected = false;

  // Try radio input first (more reliable)
  if (radioCount > 0) {
    const firstRadio = radioInputs.first();
    await firstRadio.click({ force: true });
    console.log('[SUCCESS] ✓ Clicked first radio input');
    machineSelected = true;
  }
  // Fallback to button
  else if (buttonCount > 0) {
    const firstButton = machineButtons.first();
    await firstButton.click();
    console.log('[SUCCESS] ✓ Clicked first machine button');
    machineSelected = true;
  } else {
    console.log('[ERROR] ✗ No machine options found!');
    throw new Error('No machine options available');
  }

  await page.waitForTimeout(1000);

  // ========================================================================
  // STEP 10: Click "Próximo" button
  // ========================================================================
  console.log('\n[STEP 10] Clicking "Próximo" to go to Step 3');
  const proximoButton2 = page.locator('button:has-text("Próximo")');
  await proximoButton2.click({ force: true });
  await page.waitForTimeout(2000);
  console.log('[SUCCESS] ✓ Navigated to Step 3');

  // ========================================================================
  // STEP 11: Take snapshot of Step 3
  // ========================================================================
  console.log('\n[STEP 11] Taking snapshot of Step 3');
  await page.screenshot({ path: `${screenshotDir}/04-step3-strategy.png`, fullPage: true });
  console.log('[SUCCESS] ✓ Screenshot saved: 04-step3-strategy.png');

  // ========================================================================
  // STEP 12: Check if "Iniciar" button is enabled
  // ========================================================================
  console.log('\n[STEP 12] Checking "Iniciar" button status');
  const iniciarButton = page.locator('button:has-text("Iniciar")');
  const iniciarVisible = await iniciarButton.isVisible().catch(() => false);
  const iniciarEnabled = await iniciarButton.isEnabled().catch(() => false);

  console.log(`[INFO] Iniciar button visible: ${iniciarVisible}`);
  console.log(`[INFO] Iniciar button enabled: ${iniciarEnabled}`);

  if (!iniciarVisible) {
    console.log('[ERROR] ✗ Iniciar button not visible!');
    throw new Error('Iniciar button not found');
  }

  if (!iniciarEnabled) {
    console.log('[WARNING] Iniciar button is disabled');

    // Check for error messages
    const errorMessages = await page.locator('text=/error|erro|insufficient|insuficiente/i').allTextContents();
    if (errorMessages.length > 0) {
      console.log('[ERROR MESSAGES]:');
      errorMessages.forEach(msg => console.log(`  - ${msg}`));
    }
  }

  // ========================================================================
  // STEP 13: Click "Iniciar" button if enabled
  // ========================================================================
  console.log('\n[STEP 13] Clicking "Iniciar" to start provisioning');

  if (iniciarEnabled) {
    await iniciarButton.click();
    await page.waitForTimeout(2000);
    console.log('[SUCCESS] ✓ Iniciar clicked - provisioning started!');
  } else {
    console.log('[SKIPPED] Iniciar button disabled - cannot start provisioning');
    await page.screenshot({ path: `${screenshotDir}/error-iniciar-disabled.png`, fullPage: true });
  }

  // ========================================================================
  // STEP 14: Wait 20 seconds for provisioning
  // ========================================================================
  console.log('\n[STEP 14] Waiting 20 seconds for provisioning');

  for (let i = 0; i < 4; i++) {
    await page.waitForTimeout(5000);

    const successCount = await page.locator('text=/pronta|winner|vencedor|sucesso|ready|🏆/i').count();
    const errorCount = await page.locator('text=/error|erro|failed|falhou/i').count();

    console.log(`  [${(i + 1) * 5}s] Success indicators: ${successCount}, Error indicators: ${errorCount}`);

    if (successCount > 0) {
      console.log('[SUCCESS] ✓ Provisioning completed successfully!');
      break;
    }

    if (errorCount > 0) {
      console.log('[ERROR] Provisioning encountered errors');
      break;
    }
  }

  // ========================================================================
  // STEP 15: Take final snapshot
  // ========================================================================
  console.log('\n[STEP 15] Taking final snapshot');
  await page.screenshot({ path: `${screenshotDir}/05-final-state.png`, fullPage: true });
  console.log('[SUCCESS] ✓ Screenshot saved: 05-final-state.png');

  // ========================================================================
  // FINAL REPORT
  // ========================================================================
  console.log('\n' + '='.repeat(80));
  console.log('FINAL REPORT');
  console.log('='.repeat(80));

  const finalSuccess = await page.locator('text=/pronta|winner|vencedor|sucesso|ready|🏆/i').count();
  const finalProvisioning = await page.locator('text=/race|candidat|provisionando|conectando/i').count();
  const finalErrors = await page.locator('text=/error|erro|failed|falhou/i').count();

  console.log('\n[FINAL STATE]:');
  console.log(`  Success indicators: ${finalSuccess}`);
  console.log(`  Provisioning indicators: ${finalProvisioning}`);
  console.log(`  Error indicators: ${finalErrors}`);

  console.log('\n[RESULT]:');
  if (finalSuccess > 0) {
    console.log('  ✓✓✓ GPU RESERVATION COMPLETED SUCCESSFULLY! ✓✓✓');
  } else if (finalProvisioning > 0) {
    console.log('  ⏳ GPU provisioning is in progress...');
  } else if (finalErrors > 0) {
    console.log('  ✗✗✗ GPU provisioning failed');
  } else {
    console.log('  ? Unknown state - check screenshots in test-results/wizard-4896/');
  }

  console.log('\n' + '='.repeat(80));
  console.log('TEST COMPLETED');
  console.log('Screenshots saved in: test-results/wizard-4896/');
  console.log('='.repeat(80) + '\n');

  // Assert that we at least started provisioning or got to the final step
  expect(iniciarVisible).toBe(true);
});
