# Chat Arena Testing - Complete Summary

## Overview
This document provides a complete summary of the Chat Arena UI testing setup for local Ollama models at http://localhost:4896/chat-arena.

## What Was Created

### Test Files
1. **chat-arena-local-test.spec.js** - Main test suite with comprehensive UI testing
2. **chat-arena-debug.spec.js** - Verbose debugging test with detailed logging
3. **chat-arena-comprehensive.spec.js** - Full E2E test with JSON report generation

### Helper Scripts
1. **run-chat-arena-test.sh** - Run tests in headed mode (watch the browser)
2. **run-chat-arena-test-headless.sh** - Run tests in headless mode (background)
3. **check-chat-arena-ready.sh** - Pre-flight check for all prerequisites

### Documentation
1. **CHAT_ARENA_TESTING.md** - Comprehensive testing guide
2. **CHAT_ARENA_TEST_SUMMARY.md** - This summary document

## Quick Start

### 1. Prerequisites Check
```bash
cd /Users/marcos/CascadeProjects/dumontcloud
chmod +x tests/check-chat-arena-ready.sh
./tests/check-chat-arena-ready.sh
```

This will verify:
- Ollama is running
- Models (llama3.2:1b and qwen2.5:0.5b) are installed
- Web app is running on port 4896
- Playwright is installed
- All test files exist

### 2. Run the Tests

**Option A: Quick Test (Recommended for first run)**
```bash
chmod +x run-chat-arena-test.sh
./run-chat-arena-test.sh
```
This runs in headed mode so you can see what's happening.

**Option B: Debug Test (If issues occur)**
```bash
npx playwright test tests/chat-arena-debug.spec.js --headed
```
This provides verbose logging and detailed screenshots.

**Option C: Comprehensive Test (Full report)**
```bash
npx playwright test tests/chat-arena-comprehensive.spec.js --headed
```
This generates a JSON report with all test results.

**Option D: Headless Mode (CI/CD)**
```bash
./run-chat-arena-test-headless.sh
```
This runs without opening a browser window.

## Test Flow

The tests follow these steps:

1. **Navigate** to http://localhost:4896/chat-arena
2. **Verify** page loads with "Chat Arena" heading
3. **Click** "Selecionar Modelos" button
4. **Inspect** available models in dropdown
5. **Select** llama3.2:1b (or first available model)
6. **Select** qwen2.5:0.5b (or second available model)
7. **Close** dropdown (Escape key)
8. **Type** test message: "Olá, como você está?"
9. **Send** message (Enter key)
10. **Wait** for responses (up to 30 seconds)
11. **Verify** both models respond
12. **Report** results and save screenshots

## Expected Results

### Success Scenario
```
✅ Step 1: PASS - Navigated to Chat Arena
✅ Step 2: PASS - Found 2 models from API
✅ Step 3: PASS - Model selector opened
✅ Step 4: PASS - Found 2 models
✅ Step 5: PASS - Selected 2 models
✅ Step 6: PASS - Chat interface ready
✅ Step 7: PASS - Message sent
✅ Step 8: PASS - Responses received
✅ Step 9: PASS - Both models responded

Overall: ✅ SUCCESS
```

### Common Issues

#### Issue: No models found
**Symptoms**: "Found 0 local model(s)"

**Causes**:
- Ollama not running
- Models not installed
- API not configured

**Solutions**:
```bash
# Check Ollama
ollama serve

# Install models
ollama pull llama3.2:1b
ollama pull qwen2.5:0.5b

# Verify API
curl http://localhost:4896/api/v1/chat/models
```

#### Issue: Connection errors
**Symptoms**: "Erro de conexão" or "Failed to fetch"

**Causes**:
- Ollama proxy not configured
- CORS issues
- Wrong port

**Solutions**:
1. Check backend proxy configuration for `/ollama`
2. Verify port 4896 is correct
3. Check browser console for CORS errors

#### Issue: Timeout waiting for responses
**Symptoms**: Test waits 30s but no responses

**Causes**:
- Models are slow (normal for CPU inference)
- Models are stuck
- API connection failed

**Solutions**:
1. Run manually: `ollama run llama3.2:1b "test"`
2. Check Ollama logs for errors
3. Increase timeout in test (edit line with `waitTime = 30000`)

## Screenshots

All tests save screenshots to `/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/`:

### Main Test Screenshots
- `chat-arena-step1-initial.png` - Initial page
- `chat-arena-step2-model-selector.png` - Dropdown open
- `chat-arena-step3-models-selected.png` - Models selected
- `chat-arena-step4-message-typed.png` - Message in input
- `chat-arena-step5-loading.png` - Loading state
- `chat-arena-step6-responses.png` - Model responses
- `chat-arena-step7-final.png` - Final state

### Debug Test Screenshots
- `debug-1-initial.png` through `debug-9-final.png`

### Comprehensive Test Screenshots
- `01-navigation.png` through `10-final-state.png`
- Plus `test-report.json` with detailed results

## Test Reports

### JSON Report (Comprehensive Test)
Located at: `tests/screenshots/test-report.json`

Contains:
- Timestamp
- All test steps with pass/fail/warn status
- Detailed error messages
- Screenshot references
- Model information
- Response content samples

### HTML Report (All Tests)
```bash
npx playwright show-report
```

Opens an interactive HTML report in your browser.

## Customization

### Change Test Message
Edit the test file and change:
```javascript
const testMessage = 'Olá, como você está?';
```

### Change Wait Time
Edit the test file and change:
```javascript
const waitTime = 25000; // milliseconds
```

### Change Models
The tests automatically use whatever models are available in the API response. To use specific models, you would need to modify the model selection logic.

### Add More Test Cases
Add new test cases to any `.spec.js` file:
```javascript
test('my new test case', async ({ page }) => {
  // Your test code here
});
```

## Debugging

### Enable Verbose Playwright Logging
```bash
DEBUG=pw:api npx playwright test tests/chat-arena-debug.spec.js --headed
```

### Record Trace
```bash
npx playwright test tests/chat-arena-local-test.spec.js --trace on
```

Then view:
```bash
npx playwright show-trace trace.zip
```

### Slow Motion (Watch actions)
```bash
npx playwright test tests/chat-arena-local-test.spec.js --headed --slow-mo=1000
```

### Interactive UI Mode
```bash
npx playwright test tests/chat-arena-local-test.spec.js --ui
```

## CI/CD Integration

To run in CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Install dependencies
  run: npm install

- name: Install Playwright
  run: npx playwright install --with-deps chromium

- name: Check prerequisites
  run: ./tests/check-chat-arena-ready.sh

- name: Run Chat Arena tests
  run: npx playwright test tests/chat-arena-comprehensive.spec.js

- name: Upload screenshots
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: chat-arena-screenshots
    path: tests/screenshots/

- name: Upload test report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-report
    path: tests/screenshots/test-report.json
```

## Manual Testing (If Automated Tests Fail)

1. Open browser to http://localhost:4896/chat-arena
2. Verify "Chat Arena" heading appears
3. Click "Selecionar Modelos" button
4. Verify dropdown shows "Local CPU - Llama 3.2 1B" and "Local CPU - Qwen 2.5 0.5B"
5. Click both models (should see checkmarks)
6. Press Escape or click outside to close
7. Verify two chat panels appear side by side
8. Type "Olá, como você está?" in input field
9. Press Enter
10. Wait 10-20 seconds
11. Verify both models show responses (not errors)

If any step fails, check the corresponding test screenshot to see what the UI looked like.

## Troubleshooting Checklist

- [ ] Ollama running: `curl http://localhost:11434/api/tags`
- [ ] Models installed: `ollama list | grep -E "llama3.2:1b|qwen2.5:0.5b"`
- [ ] Web app running: `curl http://localhost:4896/`
- [ ] API accessible: `curl http://localhost:4896/api/v1/chat/models`
- [ ] Playwright installed: `npx playwright --version`
- [ ] Test files exist: `ls tests/chat-arena-*.spec.js`
- [ ] Screenshots dir: `ls tests/screenshots/`
- [ ] No port conflicts: `lsof -i :4896 -i :11434`

## Support

If tests continue to fail after following this guide:

1. Run the readiness check: `./tests/check-chat-arena-ready.sh`
2. Run the debug test: `npx playwright test tests/chat-arena-debug.spec.js --headed`
3. Check all screenshots in `tests/screenshots/`
4. Review the JSON report: `tests/screenshots/test-report.json`
5. Compare screenshots with manual testing
6. Check browser console in debug test output

## File Locations

All files are in: `/Users/marcos/CascadeProjects/dumontcloud/`

- Test files: `tests/chat-arena-*.spec.js`
- Helper scripts: `run-chat-arena-test*.sh`, `tests/check-chat-arena-ready.sh`
- Documentation: `tests/CHAT_ARENA_TESTING.md`, `CHAT_ARENA_TEST_SUMMARY.md`
- Screenshots: `tests/screenshots/`
- Reports: `tests/screenshots/test-report.json`, `playwright-report/`

## Next Steps

1. Run the readiness check
2. Run the main test in headed mode
3. Review screenshots
4. If successful, integrate into your CI/CD
5. If issues, run debug test and share screenshots

Good luck with your testing!
