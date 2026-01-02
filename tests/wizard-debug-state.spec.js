// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Wizard State Debugging', () => {
  test('Debug React state after clicking EUA', async ({ page }) => {
    console.log('\n🔍 Starting state debugging...\n');

    // Navigate to wizard
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('📍 Initial state');

    // Try to access React state
    const initialState = await page.evaluate(() => {
      // Try to find React Fiber root
      const root = document.querySelector('#root');
      if (root && root._reactRootContainer) {
        return { hasReact: true, type: 'legacy' };
      }

      // Try to find React 18 root
      const keys = Object.keys(root || {});
      const reactKey = keys.find(key => key.startsWith('__reactContainer'));

      return {
        hasReact: !!reactKey,
        type: reactKey ? 'react18' : 'unknown',
        rootKeys: keys.slice(0, 5)
      };
    });

    console.log('React state detection:', initialState);

    // Get button element
    const euaButton = page.locator('button:has-text("EUA")').first();

    // Check initial button state
    const beforeClick = await euaButton.evaluate(el => ({
      className: el.className,
      dataTestId: el.getAttribute('data-testid'),
      ariaPressed: el.getAttribute('aria-pressed'),
      disabled: el.disabled
    }));

    console.log('\n📋 EUA button BEFORE click:', beforeClick);

    // Check Próximo button before click
    const nextButton = page.locator('button:has-text("Próximo")').first();
    const nextBeforeClick = await nextButton.evaluate(el => ({
      disabled: el.disabled,
      className: el.className
    }));

    console.log('📋 Próximo button BEFORE click:', nextBeforeClick);

    // Click EUA
    console.log('\n👆 Clicking EUA button...');
    await euaButton.click();

    // Wait for React to update
    await page.waitForTimeout(500);

    // Check button state after click
    const afterClick = await euaButton.evaluate(el => ({
      className: el.className,
      dataTestId: el.getAttribute('data-testid'),
      ariaPressed: el.getAttribute('aria-pressed'),
      disabled: el.disabled
    }));

    console.log('\n📋 EUA button AFTER click:', afterClick);

    // Check if className changed
    if (beforeClick.className !== afterClick.className) {
      console.log('✅ Button className changed!');
      console.log('   Before:', beforeClick.className);
      console.log('   After:', afterClick.className);
    } else {
      console.log('⚠️  Button className DID NOT change');
    }

    // Check Próximo button after click
    const nextAfterClick = await nextButton.evaluate(el => ({
      disabled: el.disabled,
      className: el.className
    }));

    console.log('\n📋 Próximo button AFTER click:', nextAfterClick);

    if (nextBeforeClick.disabled !== nextAfterClick.disabled) {
      console.log('✅ Próximo button disabled state changed!');
      console.log('   Before:', nextBeforeClick.disabled);
      console.log('   After:', nextAfterClick.disabled);
    } else {
      console.log('⚠️  Próximo button disabled state DID NOT change');
    }

    // Try to check React DevTools hook
    const reactDevTools = await page.evaluate(() => {
      if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__) {
        const hook = window.__REACT_DEVTOOLS_GLOBAL_HOOK__;
        return {
          hasHook: true,
          renderers: hook.renderers ? hook.renderers.size : 0
        };
      }
      return { hasHook: false };
    });

    console.log('\n🔧 React DevTools:', reactDevTools);

    // Listen for console logs from the page
    const consoleLogs = [];
    page.on('console', msg => {
      if (msg.text().includes('selectedLocation') || msg.text().includes('region')) {
        consoleLogs.push(msg.text());
      }
    });

    // Click again to see if there are any console logs
    console.log('\n👆 Clicking EUA again to trigger any console logs...');
    await euaButton.click();
    await page.waitForTimeout(500);

    if (consoleLogs.length > 0) {
      console.log('\n📝 Console logs related to selection:');
      consoleLogs.forEach(log => console.log('  -', log));
    } else {
      console.log('\n⚠️  No console logs related to selection');
    }

    // Take a screenshot
    await page.screenshot({
      path: 'test-results/wizard-state-debug.png',
      fullPage: true
    });
    console.log('\n📸 Screenshot saved to test-results/wizard-state-debug.png');
  });

  test('Check if onClick handler is attached', async ({ page }) => {
    console.log('\n🔍 Checking onClick handler...\n');

    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    const euaButton = page.locator('button:has-text("EUA")').first();

    // Check if button has onClick handler
    const hasOnClick = await euaButton.evaluate(el => {
      // Check for React event listeners
      const keys = Object.keys(el);
      const reactKey = keys.find(key => key.startsWith('__react'));

      if (reactKey) {
        const reactProps = el[reactKey];
        return {
          hasReactKey: true,
          hasOnClick: reactProps && reactProps.onClick !== undefined,
          propsKeys: reactProps ? Object.keys(reactProps).slice(0, 10) : []
        };
      }

      return {
        hasReactKey: false,
        hasOnClick: typeof el.onclick === 'function',
        allKeys: keys.slice(0, 20)
      };
    });

    console.log('🔗 Event handler check:', JSON.stringify(hasOnClick, null, 2));

    // Try to manually trigger the event
    console.log('\n🧪 Manually dispatching click event...');
    await euaButton.evaluate(el => {
      const event = new MouseEvent('click', {
        view: window,
        bubbles: true,
        cancelable: true
      });
      el.dispatchEvent(event);
    });

    await page.waitForTimeout(500);

    // Check Próximo button
    const nextButton = page.locator('button:has-text("Próximo")').first();
    const isEnabled = await nextButton.isEnabled();
    console.log('📋 Próximo button enabled after manual click:', isEnabled);
  });
});
