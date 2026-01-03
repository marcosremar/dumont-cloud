// Fireworks.ai Authenticated Exploration
// This script opens the browser in non-headless mode so you can log in manually
// Then it will explore and document the fine-tuning interface
// Generated: 2026-01-03

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const screenshotsDir = path.join(__dirname, '../screenshots/fireworks-exploration');
if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

test.use({
  headless: false,
  viewport: { width: 1920, height: 1080 }
});

test.describe('Fireworks.ai Authenticated Exploration', () => {

  test('Manual login and exploration', async ({ page }) => {
    console.log('\n=== FIREWORKS.AI EXPLORATION ===\n');

    // Step 1: Navigate to login
    console.log('Step 1: Navigating to Fireworks.ai app...');
    await page.goto('https://app.fireworks.ai/login', { waitUntil: 'networkidle' });

    await page.screenshot({
      path: path.join(screenshotsDir, '10-login-page.png'),
      fullPage: true
    });

    console.log('\n📸 Screenshot saved: 10-login-page.png');
    console.log('\n⏸️  PLEASE LOG IN MANUALLY IN THE BROWSER');
    console.log('   Use any of the login options (Google, GitHub, LinkedIn, or Email)');
    console.log('   The test will wait for you to complete the login...\n');

    // Wait for successful login - look for common post-login indicators
    // This will wait up to 5 minutes for login
    try {
      await page.waitForURL(url =>
        !url.includes('/login') &&
        !url.includes('accounts.google.com') &&
        !url.includes('github.com/login') &&
        !url.includes('linkedin.com'),
        { timeout: 300000 } // 5 minutes
      );

      console.log('✅ Login detected! Current URL:', page.url());

      // Wait for page to stabilize
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000);

    } catch (e) {
      console.log('⚠️  Login timeout or cancelled. Current URL:', page.url());
      throw new Error('Please complete login within 5 minutes');
    }

    // Step 2: Take screenshot of post-login page
    console.log('\nStep 2: Capturing post-login dashboard...');
    await page.screenshot({
      path: path.join(screenshotsDir, '11-post-login-dashboard.png'),
      fullPage: true
    });
    console.log('📸 Screenshot saved: 11-post-login-dashboard.png');

    // Document dashboard structure
    const dashboardInfo = await page.evaluate(() => {
      const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4')).map(h => ({
        tag: h.tagName,
        text: h.textContent.trim().substring(0, 100)
      }));

      const navLinks = Array.from(document.querySelectorAll('nav a, aside a, [role="navigation"] a')).map(l => ({
        text: l.textContent.trim(),
        href: l.href
      }));

      const buttons = Array.from(document.querySelectorAll('button')).map(b => ({
        text: b.textContent.trim().substring(0, 50),
        classes: b.className
      }));

      return { headings, navLinks, buttons: buttons.slice(0, 20) };
    });

    console.log('\nDashboard Structure:');
    console.log('Headings:', JSON.stringify(dashboardInfo.headings, null, 2));
    console.log('Navigation Links:', JSON.stringify(dashboardInfo.navLinks, null, 2));

    // Step 3: Look for fine-tuning related navigation
    console.log('\nStep 3: Looking for fine-tuning navigation...');

    const finetuneNavigation = [
      { selector: 'a:has-text("Fine-tune")', name: 'Fine-tune' },
      { selector: 'a:has-text("Fine-Tune")', name: 'Fine-Tune' },
      { selector: 'a:has-text("Finetune")', name: 'Finetune' },
      { selector: 'a:has-text("Models")', name: 'Models' },
      { selector: 'a:has-text("Training")', name: 'Training' },
      { selector: 'a:has-text("Jobs")', name: 'Jobs' },
      { selector: 'a[href*="fine"]', name: 'Fine-tune (href)' },
      { selector: 'a[href*="model"]', name: 'Models (href)' },
      { selector: 'a[href*="train"]', name: 'Training (href)' },
    ];

    let finetuneFound = false;
    for (const nav of finetuneNavigation) {
      try {
        const element = await page.locator(nav.selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          const href = await element.getAttribute('href');
          console.log(`✅ Found: ${nav.name} -> ${href}`);

          // Click and navigate
          await element.click();
          await page.waitForLoadState('networkidle');
          await page.waitForTimeout(2000);

          await page.screenshot({
            path: path.join(screenshotsDir, `12-${nav.name.toLowerCase().replace(/\s+/g, '-')}.png`),
            fullPage: true
          });
          console.log(`📸 Screenshot saved: 12-${nav.name.toLowerCase().replace(/\s+/g, '-')}.png`);

          finetuneFound = true;
          break;
        }
      } catch (e) {
        // Try next option
        continue;
      }
    }

    if (!finetuneFound) {
      console.log('⚠️  Fine-tuning navigation not found automatically.');
      console.log('   Please manually navigate to the fine-tuning page...');
      console.log('   The test will wait 2 minutes for you to navigate...\n');

      await page.waitForTimeout(120000); // Wait 2 minutes
    }

    // Step 4: Document current page (should be fine-tuning or models page)
    console.log('\nStep 4: Analyzing current page...');
    console.log('Current URL:', page.url());

    await page.screenshot({
      path: path.join(screenshotsDir, '13-current-interface.png'),
      fullPage: true
    });
    console.log('📸 Screenshot saved: 13-current-interface.png');

    const interfaceInfo = await page.evaluate(() => {
      // Get all form elements
      const inputs = Array.from(document.querySelectorAll('input')).map(i => ({
        type: i.type,
        name: i.name,
        placeholder: i.placeholder,
        id: i.id,
        value: i.type !== 'password' ? i.value : '[hidden]'
      }));

      const selects = Array.from(document.querySelectorAll('select')).map(s => ({
        name: s.name,
        id: s.id,
        options: Array.from(s.options).map(o => o.textContent.trim())
      }));

      const textareas = Array.from(document.querySelectorAll('textarea')).map(t => ({
        name: t.name,
        placeholder: t.placeholder,
        id: t.id
      }));

      // Get all labels
      const labels = Array.from(document.querySelectorAll('label')).map(l => ({
        text: l.textContent.trim().substring(0, 100),
        for: l.getAttribute('for')
      }));

      // Get all tables
      const tables = Array.from(document.querySelectorAll('table')).map(t => ({
        headers: Array.from(t.querySelectorAll('th')).map(th => th.textContent.trim()),
        rowCount: t.querySelectorAll('tr').length
      }));

      // Get all cards
      const cards = Array.from(document.querySelectorAll('[class*="card"], [class*="Card"]')).map(c => ({
        text: c.textContent.trim().substring(0, 150),
        classes: c.className
      }));

      return { inputs, selects, textareas, labels, tables, cards };
    });

    console.log('\n=== PAGE INTERFACE ANALYSIS ===');
    console.log('\nInputs:', JSON.stringify(interfaceInfo.inputs.slice(0, 20), null, 2));
    console.log('\nSelects:', JSON.stringify(interfaceInfo.selects, null, 2));
    console.log('\nTextareas:', JSON.stringify(interfaceInfo.textareas, null, 2));
    console.log('\nLabels:', JSON.stringify(interfaceInfo.labels.slice(0, 30), null, 2));
    console.log('\nTables:', JSON.stringify(interfaceInfo.tables, null, 2));
    console.log('\nCards:', JSON.stringify(interfaceInfo.cards.slice(0, 10), null, 2));

    // Step 5: Look for "Create" or "New" buttons
    console.log('\nStep 5: Looking for job creation buttons...');

    const createButtons = await page.evaluate(() => {
      const allButtons = Array.from(document.querySelectorAll('button, a[role="button"]'));
      return allButtons
        .filter(b => {
          const text = b.textContent.toLowerCase();
          return text.includes('create') ||
                 text.includes('new') ||
                 text.includes('start') ||
                 text.includes('fine') ||
                 text.includes('train');
        })
        .map(b => ({
          text: b.textContent.trim(),
          tag: b.tagName,
          classes: b.className,
          disabled: b.disabled || b.getAttribute('aria-disabled') === 'true'
        }));
    });

    console.log('Create/New buttons found:', JSON.stringify(createButtons, null, 2));

    // Try to click a create button if found
    if (createButtons.length > 0) {
      const buttonText = createButtons[0].text;
      console.log(`\nTrying to click: "${buttonText}"`);

      try {
        const createBtn = page.locator(`button:has-text("${buttonText}"), a[role="button"]:has-text("${buttonText}")`).first();
        if (await createBtn.isVisible({ timeout: 2000 })) {
          await createBtn.click();
          await page.waitForLoadState('networkidle');
          await page.waitForTimeout(2000);

          await page.screenshot({
            path: path.join(screenshotsDir, '14-creation-form.png'),
            fullPage: true
          });
          console.log('📸 Screenshot saved: 14-creation-form.png');

          // Analyze the creation form
          const formInfo = await page.evaluate(() => {
            const allInputs = Array.from(document.querySelectorAll('input, select, textarea')).map(i => ({
              tag: i.tagName,
              type: i.type || 'select',
              name: i.name,
              id: i.id,
              placeholder: i.placeholder,
              label: i.labels?.[0]?.textContent?.trim() || null
            }));

            const allLabels = Array.from(document.querySelectorAll('label')).map(l => ({
              text: l.textContent.trim(),
              for: l.getAttribute('for')
            }));

            const sliders = Array.from(document.querySelectorAll('input[type="range"]')).map(s => ({
              min: s.min,
              max: s.max,
              step: s.step,
              value: s.value,
              name: s.name
            }));

            return { allInputs, allLabels, sliders };
          });

          console.log('\n=== CREATION FORM ANALYSIS ===');
          console.log('All Inputs:', JSON.stringify(formInfo.allInputs, null, 2));
          console.log('All Labels:', JSON.stringify(formInfo.allLabels, null, 2));
          console.log('Sliders:', JSON.stringify(formInfo.sliders, null, 2));
        }
      } catch (e) {
        console.log('Could not click create button:', e.message);
      }
    }

    // Step 6: Save all collected data
    const explorationData = {
      timestamp: new Date().toISOString(),
      loginUrl: 'https://app.fireworks.ai/login',
      postLoginUrl: page.url(),
      dashboardInfo,
      interfaceInfo,
      createButtons
    };

    fs.writeFileSync(
      path.join(screenshotsDir, 'authenticated-exploration-data.json'),
      JSON.stringify(explorationData, null, 2)
    );

    console.log('\n✅ Exploration complete!');
    console.log('📁 All data saved to:', screenshotsDir);
    console.log('\nGenerated files:');
    console.log('  - 10-login-page.png');
    console.log('  - 11-post-login-dashboard.png');
    console.log('  - 12-*.png (navigation screenshots)');
    console.log('  - 13-current-interface.png');
    console.log('  - 14-creation-form.png (if found)');
    console.log('  - authenticated-exploration-data.json');

    // Keep browser open for final manual exploration
    console.log('\n⏸️  Browser will stay open for 5 minutes for manual exploration...');
    console.log('   Feel free to navigate and explore the interface.');
    console.log('   Press Ctrl+C to close when done.\n');

    await page.waitForTimeout(300000); // Keep open for 5 minutes
  });
});
