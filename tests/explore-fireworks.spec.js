// Exploration Script: Fireworks.ai Fine-Tuning Interface
// Purpose: Explore and document UI components for replication
// Generated: 2026-01-03

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

// Create screenshots directory
const screenshotsDir = path.join(__dirname, '../screenshots/fireworks-exploration');
if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

test.use({
  headless: false, // Show browser for visual confirmation
  viewport: { width: 1920, height: 1080 }
});

test.describe('Fireworks.ai Fine-Tuning Interface Exploration', () => {

  test('Explore Fireworks.ai fine-tuning interface', async ({ page }) => {
    console.log('\n=== Step 1: Navigate to Fireworks.ai ===');
    await page.goto('https://fireworks.ai', { waitUntil: 'networkidle' });

    // Take homepage snapshot
    await page.screenshot({
      path: path.join(screenshotsDir, '01-homepage.png'),
      fullPage: true
    });
    console.log('✓ Screenshot saved: 01-homepage.png');

    // Document homepage structure
    const homepage = await page.evaluate(() => {
      const headers = Array.from(document.querySelectorAll('h1, h2, h3')).map(h => ({
        tag: h.tagName,
        text: h.textContent.trim()
      }));

      const buttons = Array.from(document.querySelectorAll('button, a[role="button"]')).map(b => ({
        text: b.textContent.trim(),
        href: b.href || null
      }));

      const links = Array.from(document.querySelectorAll('nav a, header a')).map(l => ({
        text: l.textContent.trim(),
        href: l.href
      }));

      return { headers, buttons, links };
    });

    console.log('\nHomepage Structure:');
    console.log('Headers:', JSON.stringify(homepage.headers, null, 2));
    console.log('Navigation Links:', JSON.stringify(homepage.links, null, 2));
    console.log('Buttons:', JSON.stringify(homepage.buttons.slice(0, 10), null, 2)); // First 10 buttons

    // Wait a moment for any animations
    await page.waitForTimeout(2000);

    console.log('\n=== Step 2: Look for Model Library / Fine-Tuning Links ===');

    // Try to find fine-tuning related links
    const finetuneLinks = await page.evaluate(() => {
      const allLinks = Array.from(document.querySelectorAll('a'));
      return allLinks
        .filter(a => {
          const text = a.textContent.toLowerCase();
          const href = (a.href || '').toLowerCase();
          return text.includes('fine') ||
                 text.includes('model') ||
                 text.includes('library') ||
                 text.includes('train') ||
                 href.includes('fine') ||
                 href.includes('model') ||
                 href.includes('train');
        })
        .map(a => ({
          text: a.textContent.trim(),
          href: a.href,
          classes: a.className
        }));
    });

    console.log('Fine-tuning related links found:', JSON.stringify(finetuneLinks, null, 2));

    // Try common navigation patterns
    const navigationAttempts = [
      { selector: 'a:has-text("Models")', name: 'Models' },
      { selector: 'a:has-text("Model Library")', name: 'Model Library' },
      { selector: 'a:has-text("Fine-tune")', name: 'Fine-tune' },
      { selector: 'a:has-text("Fine-Tune")', name: 'Fine-Tune' },
      { selector: 'a:has-text("Platform")', name: 'Platform' },
      { selector: 'a:has-text("Console")', name: 'Console' },
      { selector: 'a:has-text("Dashboard")', name: 'Dashboard' },
      { selector: 'a[href*="console"]', name: 'Console (href)' },
      { selector: 'a[href*="dashboard"]', name: 'Dashboard (href)' },
      { selector: 'a[href*="fine"]', name: 'Fine-tune (href)' },
    ];

    let navigated = false;
    for (const attempt of navigationAttempts) {
      try {
        const element = await page.locator(attempt.selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          console.log(`\nFound navigation: ${attempt.name}`);
          const href = await element.getAttribute('href');
          console.log(`  URL: ${href}`);

          await element.click();
          await page.waitForLoadState('networkidle', { timeout: 10000 });
          navigated = true;

          await page.screenshot({
            path: path.join(screenshotsDir, `02-after-click-${attempt.name.toLowerCase().replace(/\s+/g, '-')}.png`),
            fullPage: true
          });
          console.log(`✓ Screenshot saved: 02-after-click-${attempt.name.toLowerCase().replace(/\s+/g, '-')}.png`);
          break;
        }
      } catch (e) {
        // Try next selector
        continue;
      }
    }

    if (!navigated) {
      console.log('\nNo direct navigation found. Looking for login/signup...');

      // Try to find login or get started
      const authLinks = await page.evaluate(() => {
        const allLinks = Array.from(document.querySelectorAll('a, button'));
        return allLinks
          .filter(a => {
            const text = a.textContent.toLowerCase();
            return text.includes('login') ||
                   text.includes('sign in') ||
                   text.includes('get started') ||
                   text.includes('sign up');
          })
          .map(a => ({
            text: a.textContent.trim(),
            href: a.href || null,
            tag: a.tagName
          }));
      });

      console.log('Auth/Get Started links:', JSON.stringify(authLinks, null, 2));
    }

    console.log('\n=== Step 3: Explore Current Page ===');

    // Take another screenshot of current state
    await page.screenshot({
      path: path.join(screenshotsDir, '03-current-page.png'),
      fullPage: true
    });
    console.log('✓ Screenshot saved: 03-current-page.png');

    // Document all form elements visible
    const formElements = await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input')).map(i => ({
        type: i.type,
        name: i.name,
        placeholder: i.placeholder,
        id: i.id,
        classes: i.className
      }));

      const selects = Array.from(document.querySelectorAll('select')).map(s => ({
        name: s.name,
        id: s.id,
        options: Array.from(s.options).map(o => o.textContent.trim()),
        classes: s.className
      }));

      const textareas = Array.from(document.querySelectorAll('textarea')).map(t => ({
        name: t.name,
        placeholder: t.placeholder,
        id: t.id,
        classes: t.className
      }));

      const buttons = Array.from(document.querySelectorAll('button')).map(b => ({
        text: b.textContent.trim(),
        type: b.type,
        classes: b.className
      }));

      return { inputs, selects, textareas, buttons };
    });

    console.log('\nForm Elements on Page:');
    console.log('Inputs:', JSON.stringify(formElements.inputs, null, 2));
    console.log('Selects:', JSON.stringify(formElements.selects, null, 2));
    console.log('Textareas:', JSON.stringify(formElements.textareas, null, 2));
    console.log('Buttons:', JSON.stringify(formElements.buttons.slice(0, 20), null, 2));

    // Look for cards/panels
    const cards = await page.evaluate(() => {
      const cardSelectors = [
        'div[class*="card"]',
        'div[class*="Card"]',
        'div[class*="panel"]',
        'div[class*="Panel"]',
        '[role="article"]',
        'article'
      ];

      const foundCards = [];
      cardSelectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(card => {
          foundCards.push({
            selector,
            text: card.textContent.trim().substring(0, 100),
            classes: card.className
          });
        });
      });

      return foundCards.slice(0, 10); // First 10 cards
    });

    console.log('\nCards/Panels found:', JSON.stringify(cards, null, 2));

    // Check for tabs
    const tabs = await page.evaluate(() => {
      const tabElements = Array.from(document.querySelectorAll('[role="tab"], .tab, [class*="tab"]'));
      return tabElements.map(tab => ({
        text: tab.textContent.trim(),
        role: tab.getAttribute('role'),
        classes: tab.className,
        selected: tab.getAttribute('aria-selected') === 'true'
      }));
    });

    console.log('\nTabs found:', JSON.stringify(tabs, null, 2));

    // Get page title and URL
    const pageInfo = {
      title: await page.title(),
      url: page.url()
    };

    console.log('\nCurrent Page Info:', JSON.stringify(pageInfo, null, 2));

    // Save all collected data to JSON
    const explorationData = {
      timestamp: new Date().toISOString(),
      homepage,
      finetuneLinks,
      authLinks: authLinks || [],
      formElements,
      cards,
      tabs,
      pageInfo
    };

    fs.writeFileSync(
      path.join(screenshotsDir, 'exploration-data.json'),
      JSON.stringify(explorationData, null, 2)
    );
    console.log('\n✓ Exploration data saved to exploration-data.json');

    // Keep browser open for a bit to see final state
    await page.waitForTimeout(3000);
  });
});
