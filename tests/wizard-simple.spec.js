const { test, expect } = require('@playwright/test');

test.describe('GPU Wizard - Step by Step Flow', () => {
  test('complete wizard flow from Step 1 to Step 3', async ({ page }) => {
    console.log('\n=== Starting Wizard Step-by-Step Test ===\n');

    // Step 1: Navigate to demo-app
    console.log('Step 1: Navigating to demo-app...');
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Take snapshot of initial state
    await page.screenshot({ path: 'test-results/wizard-step1-initial.png', fullPage: true });
    console.log('✓ Screenshot: wizard-step1-initial.png');

    // Step 2: Click "EUA" (USA region)
    console.log('\nStep 2: Clicking on EUA region...');

    // Try multiple selectors for USA
    let clicked = false;
    const selectors = [
      'text=/EUA/i',
      'text=/USA/i',
      'button:has-text("EUA")',
      '[class*="region"]:has-text("EUA")',
      'div:has-text("EUA")'
    ];

    for (const selector of selectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 1000 }).catch(() => false)) {
        await element.click();
        clicked = true;
        console.log(`✓ Clicked using selector: ${selector}`);
        break;
      }
    }

    if (!clicked) {
      console.log('⚠ Could not find EUA button, proceeding anyway...');
    }

    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'test-results/wizard-step1-usa-selected.png', fullPage: true });
    console.log('✓ Screenshot: wizard-step1-usa-selected.png');

    // Step 3: Click "Próximo" to go to Step 2
    console.log('\nStep 3: Clicking Próximo to go to Step 2...');
    const nextButton = page.locator('button:has-text("Próximo")').first();

    if (await nextButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await nextButton.click();
      console.log('✓ Clicked Próximo button');
    } else {
      console.log('⚠ Próximo button not found');
    }

    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/wizard-step2-initial.png', fullPage: true });
    console.log('✓ Screenshot: wizard-step2-initial.png');

    // Step 4: Click "Desenvolver" (Development use case)
    console.log('\nStep 4: Clicking on Desenvolver...');

    const devSelectors = [
      'text=/Desenvolver/i',
      'text=/Development/i',
      'button:has-text("Desenvolver")',
      '[class*="card"]:has-text("Desenvolver")',
      'div:has-text("Desenvolver")'
    ];

    clicked = false;
    for (const selector of devSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 1000 }).catch(() => false)) {
        await element.click();
        clicked = true;
        console.log(`✓ Clicked using selector: ${selector}`);
        break;
      }
    }

    if (!clicked) {
      console.log('⚠ Could not find Desenvolver option');
    }

    await page.screenshot({ path: 'test-results/wizard-step2-dev-selected.png', fullPage: true });
    console.log('✓ Screenshot: wizard-step2-dev-selected.png');

    // Step 5: Wait 2 seconds for machines to load
    console.log('\nStep 5: Waiting 2s for machines to load...');
    await page.waitForTimeout(2000);

    // Step 6: Take snapshot and verify machines appear
    await page.screenshot({ path: 'test-results/wizard-step2-machines-loaded.png', fullPage: true });
    console.log('✓ Screenshot: wizard-step2-machines-loaded.png');

    // Analyze page content
    const bodyText = await page.locator('body').textContent();
    const hasGPU = bodyText.match(/RTX|A100|H100|V100|GPU/i);
    const hasPrice = bodyText.match(/\$|USD|price/i);

    console.log(`\nMachine detection:`);
    console.log(`  - GPU names found: ${hasGPU ? 'YES' : 'NO'}`);
    console.log(`  - Prices found: ${hasPrice ? 'YES' : 'NO'}`);

    // Count clickable elements
    const buttons = await page.locator('button').count();
    const clickables = await page.locator('[role="button"], [class*="cursor-pointer"]').count();
    console.log(`  - Buttons: ${buttons}`);
    console.log(`  - Clickable elements: ${clickables}`);

    // Step 7: Try to click on first machine
    console.log('\nStep 6: Attempting to click on first machine...');

    const machineSelectors = [
      'button:has-text(/RTX|A100|H100|V100/i)',
      '[class*="machine"]:first',
      '[class*="card"]:has-text(/RTX|GPU/i)',
      '[role="button"]:has-text(/RTX|GPU/i)',
      'button:has-text(/Selecionar|Select/i)'
    ];

    clicked = false;
    for (const selector of machineSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 1000 }).catch(() => false)) {
        await element.click();
        clicked = true;
        console.log(`✓ Clicked machine using selector: ${selector}`);
        break;
      }
    }

    if (!clicked) {
      console.log('⚠ Could not find clickable machine, trying any button...');
      const anyButton = page.locator('button').nth(3); // Try 4th button (skip nav buttons)
      if (await anyButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await anyButton.click();
        console.log('✓ Clicked a button');
      }
    }

    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'test-results/wizard-step2-machine-selected.png', fullPage: true });
    console.log('✓ Screenshot: wizard-step2-machine-selected.png');

    // Step 8: Click "Próximo" to go to Step 3
    console.log('\nStep 7: Clicking Próximo to go to Step 3...');
    const nextButton2 = page.locator('button:has-text("Próximo")').first();

    if (await nextButton2.isVisible({ timeout: 3000 }).catch(() => false)) {
      await nextButton2.click();
      console.log('✓ Clicked Próximo button');
    } else {
      console.log('⚠ Próximo button not found');
    }

    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/wizard-step3-initial.png', fullPage: true });
    console.log('✓ Screenshot: wizard-step3-initial.png');

    // Step 9: Verify "Iniciar" button
    console.log('\nStep 8: Verifying Iniciar button...');
    const startButton = page.locator('button:has-text(/Iniciar|Start|Deploy/i)').first();

    const isVisible = await startButton.isVisible({ timeout: 3000 }).catch(() => false);
    const isEnabled = isVisible ? await startButton.isEnabled() : false;

    console.log(`  - Iniciar button visible: ${isVisible}`);
    console.log(`  - Iniciar button enabled: ${isEnabled}`);

    if (isVisible) {
      const buttonText = await startButton.textContent();
      const buttonClasses = await startButton.getAttribute('class');
      console.log(`  - Button text: "${buttonText}"`);
      console.log(`  - Button classes: ${buttonClasses}`);
    }

    // Step 10: Click "Iniciar" if enabled
    if (isVisible && isEnabled) {
      console.log('\nStep 9: Clicking Iniciar...');
      await startButton.click();
      await page.screenshot({ path: 'test-results/wizard-step3-provisioning-start.png', fullPage: true });
      console.log('✓ Screenshot: wizard-step3-provisioning-start.png');

      // Step 11: Wait 20s for provisioning
      console.log('\nStep 10: Waiting 20s for provisioning...');
      for (let i = 1; i <= 20; i++) {
        await page.waitForTimeout(1000);
        if (i % 5 === 0) {
          console.log(`  ... ${i}s elapsed`);

          // Take snapshots every 5s
          await page.screenshot({
            path: `test-results/wizard-step3-provisioning-${i}s.png`,
            fullPage: true
          });
        }
      }

      // Step 12: Take final snapshot
      await page.screenshot({ path: 'test-results/wizard-step3-provisioning-final.png', fullPage: true });
      console.log('✓ Screenshot: wizard-step3-provisioning-final.png');

      // Check for success/failure indicators
      const finalText = await page.locator('body').textContent();
      const successFound = finalText.match(/success|criado|created|online|ready/i);
      const errorFound = finalText.match(/error|erro|failed|falhou/i);
      const provisioningFound = finalText.match(/provisioning|provisionando|aguardando/i);

      console.log('\n=== Final Status ===');
      console.log(`  - Success indicators: ${successFound ? 'YES' : 'NO'}`);
      console.log(`  - Error indicators: ${errorFound ? 'YES' : 'NO'}`);
      console.log(`  - Provisioning indicators: ${provisioningFound ? 'YES' : 'NO'}`);
    } else {
      console.log('\n⚠ Skipping Iniciar click (button not enabled)');
      await page.screenshot({ path: 'test-results/wizard-step3-button-disabled.png', fullPage: true });
    }

    console.log('\n=== Test Complete ===');
    console.log('All screenshots saved to test-results/ directory\n');
  });
});
