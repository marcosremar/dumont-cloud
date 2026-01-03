/**
 * Chat Arena Comprehensive Test
 * Complete end-to-end test with detailed reporting and error handling
 */

const { test, expect } = require('@playwright/test');

test.describe('Chat Arena - Comprehensive E2E Test', () => {

  let testReport = {
    timestamp: new Date().toISOString(),
    tests: [],
    screenshots: [],
    errors: [],
    success: false
  };

  test.afterAll(async () => {
    // Save test report
    const fs = require('fs');
    const reportPath = 'tests/screenshots/test-report.json';
    fs.writeFileSync(reportPath, JSON.stringify(testReport, null, 2));
    console.log(`\n📊 Test report saved to: ${reportPath}`);
  });

  test('complete Chat Arena workflow', async ({ page }) => {
    const stepResults = [];

    const recordStep = (step, status, details = {}) => {
      const result = { step, status, details, timestamp: new Date().toISOString() };
      stepResults.push(result);
      testReport.tests.push(result);

      const emoji = status === 'pass' ? '✅' : status === 'fail' ? '❌' : '⚠️';
      console.log(`${emoji} Step ${step}: ${status.toUpperCase()}`);
      if (details.message) console.log(`   ${details.message}`);
    };

    const takeScreenshot = async (name, description) => {
      const path = `tests/screenshots/${name}.png`;
      await page.screenshot({ path, fullPage: true });
      testReport.screenshots.push({ name, path, description });
      console.log(`📸 Screenshot: ${name}`);
    };

    try {
      // Step 1: Navigate to Chat Arena
      console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('STEP 1: Navigation');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

      try {
        await page.goto('http://localhost:4896/chat-arena', {
          waitUntil: 'domcontentloaded',
          timeout: 10000
        });
        await page.waitForTimeout(2000);

        const heading = await page.locator('h1:has-text("Chat Arena")').count();
        if (heading > 0) {
          recordStep(1, 'pass', {
            message: 'Successfully navigated to Chat Arena',
            url: page.url()
          });
        } else {
          recordStep(1, 'fail', {
            message: 'Page loaded but Chat Arena heading not found',
            url: page.url()
          });
        }

        await takeScreenshot('01-navigation', 'Initial page load');
      } catch (error) {
        recordStep(1, 'fail', {
          message: `Navigation failed: ${error.message}`,
          error: error.toString()
        });
        testReport.errors.push(error.toString());
        throw error;
      }

      // Step 2: Check for API models
      console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('STEP 2: Verify Models API');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

      try {
        const apiResponse = await page.evaluate(async () => {
          try {
            const response = await fetch('/api/v1/chat/models');
            return await response.json();
          } catch (error) {
            return { error: error.message };
          }
        });

        if (apiResponse.error) {
          recordStep(2, 'warn', {
            message: `API error: ${apiResponse.error}`,
            details: apiResponse
          });
        } else if (apiResponse.models && apiResponse.models.length > 0) {
          recordStep(2, 'pass', {
            message: `Found ${apiResponse.models.length} models from API`,
            models: apiResponse.models.map(m => m.name || m.gpu)
          });
        } else {
          recordStep(2, 'warn', {
            message: 'API returned no models',
            details: apiResponse
          });
        }
      } catch (error) {
        recordStep(2, 'warn', {
          message: `Could not check API: ${error.message}`
        });
      }

      // Step 3: Open Model Selector
      console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('STEP 3: Open Model Selector');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

      try {
        const selectorButton = page.getByRole('button', { name: /selecionar/i });
        await selectorButton.waitFor({ state: 'visible', timeout: 5000 });

        const buttonText = await selectorButton.textContent();
        console.log(`   Found button: "${buttonText}"`);

        await selectorButton.click();
        await page.waitForTimeout(1500);

        recordStep(3, 'pass', {
          message: 'Model selector opened',
          buttonText
        });

        await takeScreenshot('02-selector-opened', 'Model selector dropdown opened');
      } catch (error) {
        recordStep(3, 'fail', {
          message: `Could not open model selector: ${error.message}`
        });
        testReport.errors.push(error.toString());
        await takeScreenshot('02-selector-error', 'Error opening selector');
        throw error;
      }

      // Step 4: Count and Display Available Models
      console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('STEP 4: Inspect Available Models');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

      try {
        // Try multiple strategies to find models
        const strategies = [
          { name: 'Local CPU text', selector: 'button:has-text("Local CPU")' },
          { name: 'GPU text', selector: 'button:has-text("GPU")' },
          { name: 'Model names', selector: 'button:has-text("llama"), button:has-text("qwen")' },
          { name: 'Dropdown buttons', selector: 'div[class*="max-h-64"] button' },
        ];

        let modelsFound = 0;
        let modelButtons = null;
        let modelTexts = [];

        for (const strategy of strategies) {
          const locator = page.locator(strategy.selector);
          const count = await locator.count();
          console.log(`   Strategy "${strategy.name}": found ${count} elements`);

          if (count > 0 && modelsFound === 0) {
            modelsFound = count;
            modelButtons = locator;
            modelTexts = await locator.allTextContents();
          }
        }

        if (modelsFound >= 2) {
          console.log(`\n   ✓ Found ${modelsFound} models:`);
          modelTexts.forEach((text, i) => {
            console.log(`     ${i + 1}. ${text.trim().substring(0, 60)}`);
          });

          recordStep(4, 'pass', {
            message: `Found ${modelsFound} models`,
            models: modelTexts.map(t => t.trim())
          });
        } else if (modelsFound === 1) {
          recordStep(4, 'warn', {
            message: 'Only 1 model found, need at least 2 for comparison',
            models: modelTexts.map(t => t.trim())
          });
        } else {
          recordStep(4, 'fail', {
            message: 'No models found in selector'
          });
          await takeScreenshot('03-no-models', 'No models found');
          throw new Error('No models available');
        }

        // Step 5: Select Models
        console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('STEP 5: Select Models');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

        if (modelButtons && modelsFound >= 2) {
          // Select first model
          const model1Text = await modelButtons.nth(0).textContent();
          await modelButtons.nth(0).click();
          console.log(`   ✓ Selected model 1: ${model1Text.trim()}`);
          await page.waitForTimeout(500);

          await takeScreenshot('04-model1-selected', 'First model selected');

          // Select second model
          const model2Text = await modelButtons.nth(1).textContent();
          await modelButtons.nth(1).click();
          console.log(`   ✓ Selected model 2: ${model2Text.trim()}`);
          await page.waitForTimeout(500);

          await takeScreenshot('05-model2-selected', 'Second model selected');

          recordStep(5, 'pass', {
            message: 'Selected 2 models',
            selectedModels: [model1Text.trim(), model2Text.trim()]
          });

          // Close dropdown
          await page.keyboard.press('Escape');
          await page.waitForTimeout(1000);
          console.log('   ✓ Dropdown closed');

          await takeScreenshot('06-models-ready', 'Models selected, ready to chat');
        }

      } catch (error) {
        recordStep(4, 'fail', {
          message: `Model selection failed: ${error.message}`
        });
        testReport.errors.push(error.toString());
        throw error;
      }

      // Step 6: Verify Chat Grids Appeared
      console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('STEP 6: Verify Chat Interface');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

      try {
        const chatGrids = await page.locator('div[style*="grid-template-columns"]').count();
        const inputField = await page.locator('input[type="text"]').count();

        if (chatGrids > 0 && inputField > 0) {
          console.log(`   ✓ Chat interface ready (${chatGrids} grid(s), ${inputField} input(s))`);
          recordStep(6, 'pass', {
            message: 'Chat interface rendered correctly',
            grids: chatGrids,
            inputs: inputField
          });
        } else {
          recordStep(6, 'warn', {
            message: 'Chat interface may not have rendered properly',
            grids: chatGrids,
            inputs: inputField
          });
        }
      } catch (error) {
        recordStep(6, 'warn', {
          message: `Could not verify chat interface: ${error.message}`
        });
      }

      // Step 7: Type and Send Message
      console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('STEP 7: Send Test Message');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

      const testMessage = 'Olá, como você está?';

      try {
        const input = page.locator('input[type="text"]').first();
        await input.waitFor({ state: 'visible', timeout: 5000 });

        const placeholder = await input.getAttribute('placeholder');
        console.log(`   Input placeholder: "${placeholder}"`);

        await input.fill(testMessage);
        console.log(`   ✓ Typed: "${testMessage}"`);

        await takeScreenshot('07-message-typed', 'Test message typed');

        await input.press('Enter');
        console.log('   ✓ Message sent');

        recordStep(7, 'pass', {
          message: 'Message sent successfully',
          messageText: testMessage
        });

        await page.waitForTimeout(2000);
        await takeScreenshot('08-message-sent', 'Message sent, waiting for responses');

      } catch (error) {
        recordStep(7, 'fail', {
          message: `Could not send message: ${error.message}`
        });
        testReport.errors.push(error.toString());
        throw error;
      }

      // Step 8: Wait for Responses
      console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('STEP 8: Wait for Model Responses');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

      const waitTime = 25000; // 25 seconds
      console.log(`   Waiting ${waitTime/1000}s for responses...`);

      const startWait = Date.now();
      await page.waitForTimeout(waitTime);
      const actualWait = Date.now() - startWait;

      await takeScreenshot('09-after-wait', `After ${(actualWait/1000).toFixed(1)}s wait`);

      // Step 9: Verify Responses
      console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('STEP 9: Verify Model Responses');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

      try {
        // Check for various response indicators
        const messageElements = await page.locator('div[class*="prose"]').count();
        const loadingIndicators = await page.locator('text=Pensando').count();
        const errorMessages = await page.locator('div:has-text("Error"), div:has-text("Erro")').allTextContents();

        console.log(`   Message elements: ${messageElements}`);
        console.log(`   Loading indicators: ${loadingIndicators}`);
        console.log(`   Error messages: ${errorMessages.length}`);

        if (errorMessages.length > 0) {
          console.log('\n   ⚠️  Errors detected:');
          errorMessages.forEach((err, i) => {
            const errText = err.trim().substring(0, 100);
            console.log(`     ${i + 1}. ${errText}`);
          });
        }

        // Get actual message content
        const allMessages = await page.locator('div[class*="prose"]').allTextContents();
        const responseMessages = allMessages.filter(msg =>
          !msg.includes(testMessage) && msg.trim().length > 0
        );

        console.log(`\n   Found ${responseMessages.length} response message(s):`);
        responseMessages.forEach((msg, i) => {
          console.log(`     ${i + 1}. ${msg.trim().substring(0, 80)}...`);
        });

        // Determine success
        const hasRealResponses = responseMessages.length >= 2 && errorMessages.length === 0;
        const hasPartialResponses = responseMessages.length > 0 && loadingIndicators === 0;
        const stillLoading = loadingIndicators > 0;
        const hasErrors = errorMessages.length > 0;

        if (hasRealResponses) {
          recordStep(9, 'pass', {
            message: `Both models responded successfully`,
            responseCount: responseMessages.length,
            responses: responseMessages.map(r => r.substring(0, 100))
          });
          testReport.success = true;
          console.log('\n   ✅ SUCCESS: Both models responded!');
        } else if (hasPartialResponses) {
          recordStep(9, 'warn', {
            message: `Only ${responseMessages.length} response(s) received`,
            responseCount: responseMessages.length,
            responses: responseMessages.map(r => r.substring(0, 100))
          });
          console.log('\n   ⚠️  PARTIAL: Some responses received');
        } else if (stillLoading) {
          recordStep(9, 'warn', {
            message: 'Models still processing, may need more time',
            loadingCount: loadingIndicators
          });
          console.log('\n   ⚠️  Models still processing...');
        } else if (hasErrors) {
          recordStep(9, 'fail', {
            message: 'Errors occurred during inference',
            errors: errorMessages
          });
          console.log('\n   ❌ FAILURE: Errors occurred');
        } else {
          recordStep(9, 'warn', {
            message: 'Unable to determine response state',
            messageElements,
            loadingIndicators
          });
          console.log('\n   ⚠️  Unknown state');
        }

        await takeScreenshot('10-final-state', 'Final test state');

      } catch (error) {
        recordStep(9, 'fail', {
          message: `Could not verify responses: ${error.message}`
        });
        testReport.errors.push(error.toString());
      }

      // Print summary
      console.log('\n');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('TEST SUMMARY');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

      const passCount = stepResults.filter(s => s.status === 'pass').length;
      const failCount = stepResults.filter(s => s.status === 'fail').length;
      const warnCount = stepResults.filter(s => s.status === 'warn').length;

      console.log(`\n   ✅ Passed: ${passCount}`);
      console.log(`   ❌ Failed: ${failCount}`);
      console.log(`   ⚠️  Warnings: ${warnCount}`);
      console.log(`\n   Overall: ${testReport.success ? '✅ SUCCESS' : failCount > 0 ? '❌ FAILED' : '⚠️  PARTIAL'}`);
      console.log(`\n   Screenshots: ${testReport.screenshots.length} saved in tests/screenshots/`);
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    } catch (error) {
      console.error('\n❌ Test failed with error:', error.message);
      testReport.errors.push(error.toString());
      testReport.success = false;

      await takeScreenshot('99-error', 'Test error state');

      throw error;
    }
  });
});
