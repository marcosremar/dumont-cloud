const { test, expect } = require('@playwright/test');

test.describe('Wizard Debug Simple', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('Check wizard step behavior when clicking Desenvolver', async ({ page }) => {
    const logs = [];

    page.on('console', msg => {
      const text = msg.text();
      // Filter for relevant logs only
      if (text.includes('WizardForm') || text.includes('step') || text.includes('tier') || text.includes('Desenvolver')) {
        logs.push(text);
        console.log(`[CONSOLE] ${text}`);
      }
    });

    console.log('\n=== Step 1: Navigate to /demo-app ===');
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('networkidle');

    console.log('\n=== Step 2: Set demo_mode ===');
    await page.evaluate(() => {
      localStorage.setItem('demo_mode', 'true');
    });

    // Reload to apply demo mode
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    console.log('\n=== Step 3: Take initial screenshot ===');
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/wizard-initial.png', fullPage: true });

    // Look for Step 1 (region selection)
    const hasEUA = await page.locator('text=/EUA|Estados Unidos|USA/i').first().isVisible().catch(() => false);
    console.log('Has EUA (Step 1)?', hasEUA);

    if (!hasEUA) {
      console.log('⚠️ Step 1 not visible on initial load!');
      console.log('Page title:', await page.title());
      console.log('URL:', page.url());

      // Check what's actually on the page
      const bodyText = await page.locator('body').textContent();
      console.log('Body text (first 500 chars):', bodyText.substring(0, 500));
    } else {
      console.log('\n=== Step 4: Click on EUA ===');
      await page.locator('text=/EUA|Estados Unidos|USA/i').first().click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/wizard-after-eua.png', fullPage: true });

      console.log('\n=== Step 5: Click Próximo ===');
      const nextButton = page.locator('button:has-text("Próximo")').first();
      await nextButton.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/wizard-after-next.png', fullPage: true });

      // Check if we're on Step 2
      const hasDesenvolver = await page.locator('text=/Desenvolver|Development/i').isVisible().catch(() => false);
      console.log('Has Desenvolver (Step 2)?', hasDesenvolver);

      if (hasDesenvolver) {
        console.log('\n=== Step 6: Inject debug code to track currentStep ===');

        // Inject a MutationObserver to track DOM changes
        await page.evaluate(() => {
          window.stepChanges = [];

          // Observe the wizard container for changes
          const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
              if (mutation.type === 'childList' || mutation.type === 'attributes') {
                // Check which step is currently visible
                const step1 = document.querySelector('[id*="wizard"]')?.textContent?.includes('EUA');
                const step2 = document.querySelector('[id*="wizard"]')?.textContent?.includes('Desenvolver');
                const step3 = document.querySelector('[id*="wizard"]')?.textContent?.includes('Estratégia');

                window.stepChanges.push({
                  time: new Date().toISOString(),
                  step1Visible: step1,
                  step2Visible: step2,
                  step3Visible: step3,
                });
              }
            });
          });

          const wizardContainer = document.querySelector('#wizard-form-section') || document.body;
          observer.observe(wizardContainer, {
            childList: true,
            subtree: true,
            attributes: true
          });

          console.log('WizardForm: Debug observer attached');
        });

        console.log('\n=== Step 7: Click on Desenvolver ===');
        await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/wizard-before-desenvolver.png', fullPage: true });

        await page.locator('text=/Desenvolver|Development/i').first().click();

        // Wait a bit for any state changes
        await page.waitForTimeout(2000);

        await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/wizard-after-desenvolver.png', fullPage: true });

        // Check which step is visible now
        const step1After = await page.locator('text=/EUA|Estados Unidos|USA/i').isVisible().catch(() => false);
        const step2After = await page.locator('text=/Desenvolver|Development/i').isVisible().catch(() => false);
        const step3After = await page.locator('text=/Estratégia|Strategy|Failover/i').isVisible().catch(() => false);

        console.log('\n=== RESULTS AFTER CLICKING "DESENVOLVER" ===');
        console.log('Step 1 (EUA) visible?', step1After);
        console.log('Step 2 (Desenvolver) visible?', step2After);
        console.log('Step 3 (Estratégia) visible?', step3After);

        if (step1After) {
          console.log('\n🐛 BUG CONFIRMED: Wizard reset to Step 1!');
        } else if (step2After) {
          console.log('\n⚠️ Wizard stayed on Step 2 (expected: advance to Step 3 or show machines)');
        } else if (step3After) {
          console.log('\n✅ Wizard advanced to Step 3 (expected)');
        } else {
          console.log('\n❓ Unexpected state - none of the steps are visible');
        }

        // Get the step changes tracked by the observer
        const stepChanges = await page.evaluate(() => window.stepChanges);
        console.log('\n=== DOM Changes During Click ===');
        console.log(JSON.stringify(stepChanges, null, 2));

      } else {
        console.log('❌ Could not reach Step 2');
      }
    }

    console.log('\n=== All collected console logs ===');
    console.log(logs.join('\n'));
  });
});
