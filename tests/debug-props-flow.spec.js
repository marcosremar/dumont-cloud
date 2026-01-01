const { test, expect } = require('@playwright/test');

test.describe('Debug Props Flow', () => {

  test('Verify handleStart is passed correctly to MachineCard', async ({ page }) => {
    console.log('\n=== DEBUGGING PROPS FLOW ===\n');

    // Navigate to machines page
    await page.goto('http://localhost:5173/app/machines', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // Inject debugging code into the page
    const debugInfo = await page.evaluate(() => {
      // Find React Fiber
      const findReactFiber = (dom) => {
        for (const key in dom) {
          if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
            return dom[key];
          }
        }
        return null;
      };

      // Find all machine cards
      const cards = Array.from(document.querySelectorAll('[class*="flex flex-col p-3"]'));

      const results = cards.map((card, index) => {
        // Find Start/Iniciar button (bilingual)
        const buttons = Array.from(card.querySelectorAll('button'));
        const iniciarBtn = buttons.find(btn =>
          btn.textContent?.includes('Iniciar') || btn.textContent?.includes('Start')
        );

        if (!iniciarBtn) {
          return {
            index,
            hasStartButton: false,
            machineName: card.querySelector('span.text-white.font-semibold')?.textContent || 'Unknown'
          };
        }

        // Check for React props
        const fiber = findReactFiber(iniciarBtn);

        let hasOnClick = false;
        let onClickSource = '';

        // Check DOM onclick
        if (iniciarBtn.onclick) {
          hasOnClick = true;
          onClickSource = 'DOM onclick property';
        }

        // Check React props via fiber
        if (fiber && fiber.memoizedProps && fiber.memoizedProps.onClick) {
          hasOnClick = true;
          onClickSource = 'React props.onClick';
        }

        // Check via getAttribute
        if (iniciarBtn.getAttribute('onClick')) {
          hasOnClick = true;
          onClickSource = 'onClick attribute';
        }

        return {
          index,
          machineName: card.querySelector('span.text-white.font-semibold')?.textContent || 'Unknown',
          status: card.querySelector('[class*="StatusBadge"]')?.textContent || 'Unknown',
          hasStartButton: true,
          hasOnClick,
          onClickSource,
          buttonText: iniciarBtn.textContent,
          buttonDisabled: iniciarBtn.disabled,
          fiberExists: !!fiber,
          hasMemoizedProps: !!(fiber && fiber.memoizedProps)
        };
      });

      return results;
    });

    console.log('Debug Info:');
    console.log(JSON.stringify(debugInfo, null, 2));

    debugInfo.forEach(info => {
      console.log(`\nMachine ${info.index}: ${info.machineName}`);
      console.log(`  Status: ${info.status}`);
      console.log(`  Has Start/Iniciar Button: ${info.hasStartButton}`);
      if (info.hasStartButton) {
        console.log(`  Has onClick Handler: ${info.hasOnClick}`);
        console.log(`  onClick Source: ${info.onClickSource}`);
        console.log(`  Button Text: ${info.buttonText}`);
        console.log(`  Button Disabled: ${info.buttonDisabled}`);
        console.log(`  React Fiber Exists: ${info.fiberExists}`);
        console.log(`  Has Memoized Props: ${info.hasMemoizedProps}`);
      }
    });

    console.log('\n=== END DEBUG ===\n');
  });
});
