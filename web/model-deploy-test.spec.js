import { test, expect } from '@playwright/test';

test.describe('Model Deploy Functionality Tests', () => {
  test('Navigate to models page and test deploy wizard', async ({ page }) => {
    const consoleMessages = [];
    const networkRequests = [];
    const failedRequests = [];

    // Capture console messages
    page.on('console', msg => {
      const msgText = msg.text();
      const type = msg.type();
      consoleMessages.push({ type, text: msgText });
      if (type === 'error') {
        console.log(`[CONSOLE ${type.toUpperCase()}] ${msgText}`);
      }
    });

    // Capture failed requests
    page.on('requestfailed', request => {
      const url = request.url();
      const failure = request.failure();
      failedRequests.push({ url, failure });
      console.log(`[REQUEST FAILED] ${url} - ${failure ? failure.errorText : 'unknown'}`);
    });

    console.log('\n=== STEP 1: Login with demo mode ===');
    // First go to the app to set up localStorage
    await page.goto('http://localhost:4892');
    await page.waitForTimeout(1000);

    // Explicitly set demo_mode, auth token, and user in localStorage
    await page.evaluate(() => {
      localStorage.setItem('demo_mode', 'true');
      localStorage.setItem('auth_token', 'demo-token-12345');
      localStorage.setItem('auth_login_time', Date.now().toString());
      localStorage.setItem('auth_user', JSON.stringify({
        id: 'demo-user-1',
        username: 'demo@dumont.cloud',
        email: 'demo@dumont.cloud',
        name: 'Demo User',
        balance: 100,
        plan: 'pro'
      }));
    });
    console.log('Demo mode and user set explicitly in localStorage');

    // Verify demo mode is set
    const demoMode = await page.evaluate(() => localStorage.getItem('demo_mode'));
    console.log('Demo mode in localStorage:', demoMode);
    expect(demoMode).toBe('true');

    console.log('\n=== STEP 2: Navigate to /app/models ===');
    await page.goto('http://localhost:4892/app/models');
    await page.waitForTimeout(4000); // Wait for i18n and data to load

    // Take screenshot
    await page.screenshot({
      path: 'test-models-page.png',
      fullPage: true
    });
    console.log('Screenshot saved: test-models-page.png');

    console.log('\n=== STEP 3: Verify page loads correctly ===');
    const currentUrl = page.url();
    console.log('Current URL:', currentUrl);

    // Check for welcome modal and skip if present
    const skipButton = page.locator('button:has-text("Pular tudo")');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      console.log('Clicked "Pular tudo" button');
      await page.waitForTimeout(500);
    }

    console.log('\n=== STEP 4: Look for Deploy Model button ===');

    // Try different selectors for the deploy button
    const deployButtonSelectors = [
      'button:has-text("Deploy Model")',
      'button:has-text("Deploy")',
      'button:has(.lucide-rocket)',
    ];

    let deployButton = null;
    for (const selector of deployButtonSelectors) {
      try {
        const btn = page.locator(selector).first();
        if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
          deployButton = btn;
          console.log(`Found deploy button with selector: ${selector}`);
          break;
        }
      } catch (e) {
        // Continue to next selector
      }
    }

    if (!deployButton) {
      console.log('Deploy button not found');
      const buttons = await page.locator('button').all();
      console.log(`Page has ${buttons.length} buttons`);
      for (let i = 0; i < Math.min(buttons.length, 10); i++) {
        const text = await buttons[i].textContent();
        console.log(`  Button ${i}: "${text?.trim()}"`);
      }
      await page.screenshot({ path: 'test-no-deploy-button.png', fullPage: true });
      throw new Error('Deploy button not found on the page');
    }

    console.log('\n=== STEP 5: Click Deploy Model button ===');
    await deployButton.click();
    await page.waitForTimeout(1500);

    await page.screenshot({ path: 'test-deploy-wizard-opened.png', fullPage: true });
    console.log('Screenshot saved: test-deploy-wizard-opened.png');

    console.log('\n=== STEP 6: Select LLM type (Step 1 of Wizard) ===');

    // Look for LLM type button
    const llmTypeButton = page.locator('button:has-text("LLM")').first();
    if (await llmTypeButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('Found LLM type button');
      await llmTypeButton.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: 'test-llm-type-selected.png', fullPage: true });
    }

    console.log('\n=== STEP 7: Click Next to go to Step 2 ===');

    const nextButton = page.locator('button:has-text("Next"), button:has-text("Próximo")').first();
    if (await nextButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await nextButton.click();
      console.log('Clicked next button');
      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'test-wizard-step-2.png', fullPage: true });

      console.log('\n=== STEP 8: Select Llama model ===');

      // Wait for models to be visible in step 2
      await page.waitForTimeout(1000);

      // List all visible buttons for debugging
      const allButtons = await page.locator('button').all();
      console.log(`Step 2 has ${allButtons.length} buttons`);

      // Try to find Llama model button
      const llamaButton = page.locator('button:has-text("Llama 3.2")').first();
      if (await llamaButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await llamaButton.click();
        console.log('Selected Llama 3.2 model');
        await page.waitForTimeout(1000);
        await page.screenshot({ path: 'test-model-selected.png', fullPage: true });
      } else {
        console.log('Llama model button NOT visible, trying alternatives...');
        // Try any model button
        const anyModelBtn = page.locator('button:has-text(/Llama|Qwen|Mistral|Gemma/i)').first();
        if (await anyModelBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await anyModelBtn.click();
          console.log('Selected alternative model');
          await page.waitForTimeout(1000);
        } else {
          console.log('No model buttons found!');
          await page.screenshot({ path: 'test-no-models.png', fullPage: true });
        }
      }

      // Navigate through remaining steps (step 3 and 4)
      for (let step = 2; step <= 3; step++) {
        console.log(`\nTrying to advance from step ${step} to step ${step + 1}...`);
        await page.waitForTimeout(500);

        // Check if Next button is enabled
        const nextBtn = page.locator('button:has-text("Next"), button:has-text("Próximo")').first();
        const isVisible = await nextBtn.isVisible({ timeout: 2000 }).catch(() => false);
        const isEnabled = await nextBtn.isEnabled().catch(() => false);
        console.log(`Next button visible: ${isVisible}, enabled: ${isEnabled}`);

        if (isVisible && isEnabled) {
          await nextBtn.click();
          console.log(`Advanced to step ${step + 1}`);
          await page.waitForTimeout(2000);
          await page.screenshot({ path: `test-wizard-step-${step + 1}.png`, fullPage: true });
        } else {
          console.log(`Cannot advance - button not enabled at step ${step}`);
          await page.screenshot({ path: `test-stuck-at-step-${step}.png`, fullPage: true });
          break;
        }
      }
    } else {
      console.log('Next button not visible at step 1');
    }

    console.log('\n=== STEP 9: Click Deploy button ===');

    // Look for the final deploy button (not Next but Deploy with Rocket icon)
    const deployFinalButton = page.locator('button:has-text("Deploy")').last();
    if (await deployFinalButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await deployFinalButton.click();
      console.log('Clicked Deploy button');
      await page.waitForTimeout(3000);
      await page.screenshot({ path: 'test-deploy-submitted.png', fullPage: true });

      // Check if deployment started
      const deployingStatus = page.locator('text=/deploying|downloading|starting/i');
      if (await deployingStatus.isVisible({ timeout: 3000 }).catch(() => false)) {
        console.log('Deployment started - status shows deploying/downloading/starting');
      }
    }

    console.log('\n=== FINAL SCREENSHOT ===');
    await page.screenshot({ path: 'test-final.png', fullPage: true });

    console.log('\n=== SUMMARY ===');
    console.log(`Total console messages: ${consoleMessages.length}`);
    console.log(`Total network requests: ${networkRequests.length}`);
    console.log(`Total failed requests: ${failedRequests.length}`);

    const errors = consoleMessages.filter(m => m.type === 'error');
    if (errors.length > 0) {
      console.log(`\nConsole Errors (${errors.length}):`);
      errors.forEach(err => console.log(`  ${err.text}`));
    }

    await page.waitForTimeout(2000);
  });
});
