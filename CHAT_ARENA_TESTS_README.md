# Chat Arena Testing - Complete Package

This package provides comprehensive automated testing for the Chat Arena UI at http://localhost:4896/chat-arena with local Ollama models.

## What You Get

A complete test automation suite including:
- 3 test files with different detail levels
- 5 helper scripts for easy execution
- 4 documentation files
- Automatic screenshot capture
- JSON report generation
- Prerequisite checking

## Quick Start (30 seconds)

```bash
# 1. Make executable
chmod +x quick-test-chat-arena.sh

# 2. Run
./quick-test-chat-arena.sh
```

Done! Check `tests/screenshots/` for results.

## What Gets Tested

The test simulates a real user:

1. Opens http://localhost:4896/chat-arena
2. Clicks "Selecionar Modelos"
3. Selects llama3.2:1b
4. Selects qwen2.5:0.5b
5. Types: "Olá, como você está?"
6. Sends the message
7. Waits for both models to respond
8. Verifies responses are correct
9. Takes screenshots at every step

**Total time**: 15-30 seconds (depending on CPU speed)

## Prerequisites

You need:
- Ollama running: `ollama serve`
- Models installed: `ollama pull llama3.2:1b qwen2.5:0.5b`
- Web app on port 4896: `cd web && npm run dev`
- Playwright: `npx playwright install chromium`

**Check everything at once:**
```bash
./tests/check-chat-arena-ready.sh
```

## Files Created

### In Project Root

**Quick Start:**
- `QUICK_START_CHAT_ARENA_TESTS.md` - Start here
- `quick-test-chat-arena.sh` - Run this

**Complete Info:**
- `CHAT_ARENA_TEST_SUMMARY.md` - Detailed summary
- `CHAT_ARENA_TESTS_README.md` - This file

**Test Runners:**
- `test-chat-arena-complete.sh` - Full suite (all 3 tests)
- `run-chat-arena-test.sh` - Main test headed
- `run-chat-arena-test-headless.sh` - Main test headless

### In tests/ Directory

**Test Specs:**
- `chat-arena-local-test.spec.js` - Main test (recommended)
- `chat-arena-debug.spec.js` - Debug with verbose logging
- `chat-arena-comprehensive.spec.js` - Full report generation

**Documentation:**
- `CHAT_ARENA_TESTING.md` - Complete testing guide
- `EXPECTED_RESULTS.md` - What to expect at each step

**Helper:**
- `check-chat-arena-ready.sh` - Prerequisites checker

### Generated During Tests

**Screenshots:** (in `tests/screenshots/`)
- Main test: `chat-arena-step1.png` through `step7.png`
- Debug test: `debug-1.png` through `debug-9.png`
- Comprehensive: `01-navigation.png` through `10-final-state.png`

**Reports:**
- `tests/screenshots/test-report.json` - Detailed JSON report
- `playwright-report/` - Interactive HTML report

## Usage Scenarios

### Scenario 1: Quick Check
"Just want to see if it works"

```bash
./quick-test-chat-arena.sh
```

### Scenario 2: First Time Setup
"Never run this before, want to be sure"

```bash
# Check prerequisites
./tests/check-chat-arena-ready.sh

# Run with debug
npx playwright test tests/chat-arena-debug.spec.js --headed
```

### Scenario 3: Something's Broken
"Tests are failing, need to diagnose"

```bash
# Run debug test
npx playwright test tests/chat-arena-debug.spec.js --headed

# Check screenshots
open tests/screenshots/

# Check browser console output in terminal
```

### Scenario 4: Full Report Needed
"Need detailed documentation of test results"

```bash
# Run comprehensive test
npx playwright test tests/chat-arena-comprehensive.spec.js

# View JSON report
cat tests/screenshots/test-report.json

# Or with jq for formatting
cat tests/screenshots/test-report.json | jq .
```

### Scenario 5: CI/CD Integration
"Want to run in pipeline"

```bash
# Headless mode
./run-chat-arena-test-headless.sh

# Or direct
npx playwright test tests/chat-arena-local-test.spec.js --project=chromium

# HTML report
npx playwright show-report
```

### Scenario 6: Interactive Debugging
"Want to step through manually"

```bash
npx playwright test tests/chat-arena-local-test.spec.js --ui
```

## Understanding Results

### Console Output

**Success looks like:**
```
Step 1: Navigating to Chat Arena...
  ✓ Navigated to Chat Arena
  ✓ Chat Arena heading found

Step 3: Opening model selector...
  ✓ Model selector opened

  Found 2 local model(s)
  ✓ Selected first model (llama3.2:1b)
  ✓ Selected second model
  ✓ Model selector closed

Step 5: Typing test message...
  ✓ Typed message: "Olá, como você está?"

Step 6: Sending message...
  ✓ Message sent - waiting for responses...

Step 7: Waiting for model responses...
  ✓ Responses received in 8.3s

Step 8: Verifying responses...
  Message containers found: 4
  Has error messages: false
  Has response content: true

  ✅ SUCCESS: Chat Arena is working! Models responded successfully.
```

**Failure looks like:**
```
Step 1: Navigating to Chat Arena...
  ✓ Navigated to Chat Arena

Step 3: Opening model selector...
  ✓ Model selector opened

  Found 0 local model(s)
  ⚠ No models found

  ❌ FAILURE: No models available
```

### Screenshots

Open `tests/screenshots/` and check:

1. `step1-initial.png` - Did page load?
2. `step2-model-selector.png` - Are models listed?
3. `step3-models-selected.png` - Are checkmarks visible?
4. `step5-loading.png` - Is loading indicator shown?
5. `step6-responses.png` - Are responses visible?

Compare with `tests/EXPECTED_RESULTS.md` to see what they should look like.

### HTML Report

```bash
npx playwright show-report
```

Opens interactive report showing:
- Test timeline
- Pass/fail status
- Error details
- Screenshots inline
- Network requests
- Console logs

## Common Issues

### 1. No Models Found

**Symptoms:**
```
Found 0 local model(s)
```

**Fix:**
```bash
# Check Ollama
ollama list

# Should show:
# NAME              ID              SIZE
# llama3.2:1b       ...            ...
# qwen2.5:0.5b      ...            ...

# If missing:
ollama pull llama3.2:1b
ollama pull qwen2.5:0.5b
```

### 2. Connection Errors

**Symptoms:**
```
Error: Erro de conexão: verifique se o modelo está online
```

**Fix:**
```bash
# Test Ollama directly
curl http://localhost:11434/api/tags

# Test API
curl http://localhost:4896/api/v1/chat/models

# Check backend proxy configuration
```

### 3. Slow/Timeout

**Symptoms:**
```
⚠ Models still processing, may need more time
```

**Fix:**
- This is normal for CPU inference
- Wait longer or increase timeout in test
- Use smaller models
- Check CPU usage: `top` or `htop`

### 4. Models Respond with Errors

**Symptoms:**
Screenshot shows red error messages

**Fix:**
```bash
# Test model manually
ollama run llama3.2:1b "test"

# Check Ollama logs
# Should see model loading and responding
```

## Test Modes Explained

### 1. Main Test
**File**: `tests/chat-arena-local-test.spec.js`

- Standard test with good balance
- Clear step-by-step output
- 7 screenshots
- ~30 second runtime
- Best for regular testing

**Run with:**
```bash
./run-chat-arena-test.sh  # Headed
./run-chat-arena-test-headless.sh  # Headless
```

### 2. Debug Test
**File**: `tests/chat-arena-debug.spec.js`

- Very verbose logging
- Tries multiple selectors
- Shows all page elements
- 9 screenshots
- Logs browser console
- Logs network requests
- Best for troubleshooting

**Run with:**
```bash
npx playwright test tests/chat-arena-debug.spec.js --headed
```

### 3. Comprehensive Test
**File**: `tests/chat-arena-comprehensive.spec.js`

- Generates JSON report
- Structured step results
- Detailed error tracking
- Pass/warn/fail categorization
- 10 screenshots
- Best for documentation/CI

**Run with:**
```bash
npx playwright test tests/chat-arena-comprehensive.spec.js
```

## Advanced Usage

### Run Specific Test Case
```bash
npx playwright test tests/chat-arena-local-test.spec.js -g "should test Chat Arena UI"
```

### Debug Mode with Pause
Add to test:
```javascript
await page.pause();  // Opens Playwright Inspector
```

### Record New Test
```bash
npx playwright codegen http://localhost:4896/chat-arena
```

### Trace Everything
```bash
npx playwright test tests/chat-arena-local-test.spec.js --trace on
npx playwright show-trace trace.zip
```

### Slow Motion
```bash
npx playwright test tests/chat-arena-local-test.spec.js --headed --slow-mo=1000
```

### Video Recording
Videos saved automatically on failure in `test-results/`

### Screenshot on Every Action
```bash
npx playwright test tests/chat-arena-local-test.spec.js --screenshot=on
```

## Customization

### Change Test Message
Edit test file:
```javascript
const testMessage = 'Your custom message';
```

### Change Wait Time
Edit test file:
```javascript
const maxWaitTime = 60000; // 60 seconds
```

### Test Different Models
Models are auto-detected from API. To use specific ones, modify selection logic in test.

### Add More Assertions
```javascript
expect(await page.locator('h1').textContent()).toBe('Chat Arena');
```

## Integration

### GitHub Actions
```yaml
- name: Run Chat Arena Tests
  run: |
    npx playwright test tests/chat-arena-local-test.spec.js
- name: Upload Screenshots
  uses: actions/upload-artifact@v3
  with:
    name: screenshots
    path: tests/screenshots/
```

### GitLab CI
```yaml
test:chat-arena:
  script:
    - npx playwright test tests/chat-arena-local-test.spec.js
  artifacts:
    paths:
      - tests/screenshots/
    when: always
```

### Jenkins
```groovy
stage('Test Chat Arena') {
  steps {
    sh 'npx playwright test tests/chat-arena-local-test.spec.js'
  }
  post {
    always {
      archiveArtifacts 'tests/screenshots/**'
    }
  }
}
```

## Documentation Index

1. **QUICK_START_CHAT_ARENA_TESTS.md** - Start here, quick commands
2. **CHAT_ARENA_TESTS_README.md** - This file, complete overview
3. **CHAT_ARENA_TEST_SUMMARY.md** - Detailed summary and troubleshooting
4. **tests/CHAT_ARENA_TESTING.md** - Complete testing guide
5. **tests/EXPECTED_RESULTS.md** - Step-by-step expected behavior

Read in order:
1. Quick Start (if in a hurry)
2. This README (for understanding)
3. Test Summary (for details)
4. Testing Guide (for deep dive)
5. Expected Results (for validation)

## Support

Still stuck? Here's what to do:

1. Run readiness check: `./tests/check-chat-arena-ready.sh`
2. Run debug test: `npx playwright test tests/chat-arena-debug.spec.js --headed`
3. Check all screenshots in `tests/screenshots/`
4. Compare with `tests/EXPECTED_RESULTS.md`
5. Check console output for specific errors
6. Try manual testing to confirm UI works
7. Review browser console in debug test
8. Check network tab (in debug test output)

## Maintenance

### Update Playwright
```bash
npm install -D @playwright/test@latest
npx playwright install chromium
```

### Clean Screenshots
```bash
rm tests/screenshots/*.png
rm tests/screenshots/test-report.json
```

### Clean Reports
```bash
rm -rf playwright-report/
rm -rf test-results/
```

### Update Tests
Edit `.spec.js` files as needed. Tests are self-documenting with console.log statements.

## Contributing

To add new test scenarios:

1. Copy `tests/chat-arena-local-test.spec.js`
2. Rename to your scenario
3. Modify test steps
4. Update console output
5. Add to documentation

## License

Same as the main project.

## Summary

You now have a complete, production-ready test suite for Chat Arena:

- ✅ 3 test modes (main, debug, comprehensive)
- ✅ 5 helper scripts (check, run, quick)
- ✅ 4 documentation files
- ✅ Automatic screenshots
- ✅ JSON reports
- ✅ HTML reports
- ✅ CI/CD ready
- ✅ Easy to use
- ✅ Well documented

Just run `./quick-test-chat-arena.sh` and you're testing!

For questions or issues, check the documentation files or review the screenshots to see what's happening visually.

Happy testing! 🚀
