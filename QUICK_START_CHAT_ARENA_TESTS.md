# Chat Arena Testing - Quick Start

## TL;DR - Run This

```bash
# Make scripts executable
chmod +x quick-test-chat-arena.sh

# Run the test
./quick-test-chat-arena.sh
```

That's it! The test will open a browser and test the Chat Arena UI with your local Ollama models.

## What This Tests

1. Navigates to http://localhost:4896/chat-arena
2. Opens the model selector
3. Selects both available models (llama3.2:1b and qwen2.5:0.5b)
4. Types "Olá, como você está?"
5. Sends the message
6. Waits for both models to respond
7. Verifies responses are received
8. Takes screenshots at each step

## Prerequisites

Before running, make sure you have:

1. **Ollama running**
   ```bash
   ollama serve
   ```

2. **Models installed**
   ```bash
   ollama pull llama3.2:1b
   ollama pull qwen2.5:0.5b
   ```

3. **Web app running on port 4896**
   ```bash
   cd web
   npm run dev
   ```

4. **Playwright installed**
   ```bash
   npm install -D @playwright/test
   npx playwright install chromium
   ```

## Check Prerequisites

Run this first to verify everything is ready:

```bash
chmod +x tests/check-chat-arena-ready.sh
./tests/check-chat-arena-ready.sh
```

## Test Options

### Option 1: Quick Test (Recommended)
```bash
./quick-test-chat-arena.sh
```
Fast, headed mode, shows browser.

### Option 2: Full Test Suite
```bash
chmod +x test-chat-arena-complete.sh
./test-chat-arena-complete.sh
```
Runs all tests: debug, main, and comprehensive.

### Option 3: Debug Mode
```bash
npx playwright test tests/chat-arena-debug.spec.js --headed
```
Verbose logging, useful when things don't work.

### Option 4: Headless (Background)
```bash
chmod +x run-chat-arena-test-headless.sh
./run-chat-arena-test-headless.sh
```
No browser window, good for automation.

## Understanding Results

### Success
```
✅ SUCCESS: Chat Arena is working! Models responded successfully.
```
Everything works! Check `tests/screenshots/` for visual proof.

### Partial Success
```
⚠️ PARTIAL: Some responses received
```
One model responded but not both. Check screenshots to see which one failed.

### Failure
```
❌ FAILURE: Errors occurred during model inference.
```
Models couldn't respond. Check error messages in console output.

## Screenshots

After running tests, check these folders:

- **tests/screenshots/** - All test screenshots
- **playwright-report/** - HTML test report

View HTML report:
```bash
npx playwright show-report
```

## Troubleshooting

### No models found
```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Should show llama3.2:1b and qwen2.5:0.5b
```

### Connection errors
```bash
# Check web app
curl http://localhost:4896/

# Check API
curl http://localhost:4896/api/v1/chat/models
```

### Test timeout
Normal! Model inference on CPU can take 15-30 seconds. The test waits up to 30s.

## Files Created

All in `/Users/marcos/CascadeProjects/dumontcloud/`:

**Test Files:**
- `tests/chat-arena-local-test.spec.js` - Main test
- `tests/chat-arena-debug.spec.js` - Debug test
- `tests/chat-arena-comprehensive.spec.js` - Full report test

**Runner Scripts:**
- `quick-test-chat-arena.sh` - Quick test (use this)
- `test-chat-arena-complete.sh` - Full suite
- `run-chat-arena-test.sh` - Main test headed
- `run-chat-arena-test-headless.sh` - Main test headless
- `tests/check-chat-arena-ready.sh` - Prerequisites check

**Documentation:**
- `QUICK_START_CHAT_ARENA_TESTS.md` - This file
- `CHAT_ARENA_TEST_SUMMARY.md` - Detailed summary
- `tests/CHAT_ARENA_TESTING.md` - Complete guide

## Manual Test (If Automated Fails)

1. Open http://localhost:4896/chat-arena in your browser
2. Click "Selecionar Modelos"
3. Click both model checkboxes
4. Press Escape to close dropdown
5. Type "Olá, como você está?" in the input
6. Press Enter
7. Wait 10-20 seconds
8. You should see responses from both models

Compare what you see with the screenshots in `tests/screenshots/`.

## Common Commands

```bash
# Quick test
./quick-test-chat-arena.sh

# Check prerequisites
./tests/check-chat-arena-ready.sh

# Debug test
npx playwright test tests/chat-arena-debug.spec.js --headed

# View report
npx playwright show-report

# Run specific test
npx playwright test tests/chat-arena-local-test.spec.js -g "should test Chat Arena UI"

# Interactive mode
npx playwright test tests/chat-arena-local-test.spec.js --ui
```

## Next Steps

1. Run `./quick-test-chat-arena.sh`
2. If it passes, you're done!
3. If it fails, run `./tests/check-chat-arena-ready.sh`
4. If still failing, run debug test
5. Check screenshots to see what happened

## Support

For detailed troubleshooting, see:
- `CHAT_ARENA_TEST_SUMMARY.md` - Full troubleshooting guide
- `tests/CHAT_ARENA_TESTING.md` - Complete testing documentation

## That's It!

You now have a complete test suite for the Chat Arena UI. Just run `./quick-test-chat-arena.sh` and you're good to go!
