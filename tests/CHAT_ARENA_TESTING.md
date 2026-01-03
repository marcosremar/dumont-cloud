# Chat Arena Testing Guide

This guide explains how to test the Chat Arena UI with local Ollama models.

## Prerequisites

1. **Local Ollama Running**: Ensure Ollama is running on your system
   ```bash
   ollama serve
   ```

2. **Models Installed**: You need at least 2 models installed
   ```bash
   ollama pull llama3.2:1b
   ollama pull qwen2.5:0.5b
   ```

3. **Application Running**: The web application should be running on port 4896
   ```bash
   # In the web directory
   npm run dev
   ```

4. **Playwright Installed**: Install Playwright if not already installed
   ```bash
   npm install -D @playwright/test
   npx playwright install chromium
   ```

## Test Files

### 1. Main Test Suite
**File**: `tests/chat-arena-local-test.spec.js`

This is the comprehensive test suite that:
- Navigates to Chat Arena
- Opens model selector
- Selects both available models (llama3.2:1b and qwen2.5:0.5b)
- Types a test message
- Sends it and waits for responses
- Verifies both models respond
- Tests export functionality

### 2. Debug Test
**File**: `tests/chat-arena-debug.spec.js`

This is a verbose debugging test that:
- Logs all browser console messages
- Logs network requests/responses
- Inspects page structure in detail
- Tries multiple selectors to find elements
- Takes screenshots at every step
- Provides detailed output for troubleshooting

## Running the Tests

### Option 1: Using Shell Scripts (Recommended)

**Headed mode** (watch the test run):
```bash
chmod +x run-chat-arena-test.sh
./run-chat-arena-test.sh
```

**Headless mode** (run in background):
```bash
chmod +x run-chat-arena-test-headless.sh
./run-chat-arena-test-headless.sh
```

### Option 2: Direct Playwright Commands

**Run main test (headed)**:
```bash
npx playwright test tests/chat-arena-local-test.spec.js --headed --project=chromium
```

**Run main test (headless)**:
```bash
npx playwright test tests/chat-arena-local-test.spec.js --project=chromium
```

**Run debug test (headed)**:
```bash
npx playwright test tests/chat-arena-debug.spec.js --headed --project=chromium
```

**Run specific test case**:
```bash
npx playwright test tests/chat-arena-local-test.spec.js -g "should test Chat Arena UI"
```

**Run with UI mode** (interactive):
```bash
npx playwright test tests/chat-arena-local-test.spec.js --ui
```

## Screenshots

All tests save screenshots to `tests/screenshots/` directory:

### Main Test Screenshots
- `chat-arena-step1-initial.png` - Initial page load
- `chat-arena-step2-model-selector.png` - Model selector opened
- `chat-arena-step3-models-selected.png` - After selecting models
- `chat-arena-step4-message-typed.png` - Message typed in input
- `chat-arena-step5-loading.png` - Loading state
- `chat-arena-step6-responses.png` - Model responses
- `chat-arena-step7-final.png` - Final state

### Debug Test Screenshots
- `debug-1-initial.png` through `debug-9-final.png` - Detailed step-by-step captures

## Expected Behavior

### Successful Test Run
1. Page loads with "Chat Arena" heading
2. "Selecionar Modelos" button is visible
3. Clicking opens dropdown showing 2 local models
4. Both models can be selected (checkmarks appear)
5. Chat grids appear for both models
6. Input field accepts message
7. After sending, both models show loading indicators
8. Both models respond within 30 seconds
9. Responses contain relevant Portuguese text

### Common Issues

#### No Models Found
**Symptoms**: Model selector is empty or shows "Nenhum modelo disponivel"

**Solutions**:
1. Verify Ollama is running: `curl http://localhost:11434/api/tags`
2. Check if models are installed: `ollama list`
3. Verify backend API: `curl http://localhost:4896/api/v1/chat/models`
4. Check browser console for CORS errors

#### Connection Errors
**Symptoms**: "Erro de conexão" or "Failed to fetch" messages

**Solutions**:
1. Ensure Ollama proxy is configured in backend
2. Check if port 4896 is correct
3. Verify CORS configuration
4. Check if `/ollama` proxy path is working

#### Slow Responses
**Symptoms**: Test times out waiting for responses

**Solutions**:
1. Models are actually running (check Ollama logs)
2. Increase timeout in test (currently 30s)
3. Use smaller/faster models
4. Check CPU/memory usage

#### Models Don't Respond
**Symptoms**: Loading indicators stay forever

**Solutions**:
1. Check browser console for errors
2. Check network tab for failed API calls
3. Verify Ollama API is responding: `ollama run llama3.2:1b "test"`
4. Check backend logs

## Debugging

### Enable Verbose Logging
```bash
DEBUG=pw:api npx playwright test tests/chat-arena-debug.spec.js --headed
```

### Trace Recording
```bash
npx playwright test tests/chat-arena-local-test.spec.js --trace on
```

Then view the trace:
```bash
npx playwright show-trace trace.zip
```

### Slow Motion
```bash
npx playwright test tests/chat-arena-local-test.spec.js --headed --slow-mo=1000
```

### Video Recording
Videos are automatically saved on failure in `test-results/` directory.

## Manual Testing Steps

If automated tests fail, try these manual steps:

1. Open browser to http://localhost:4896/chat-arena
2. Click "Selecionar Modelos" button
3. Verify models appear in dropdown
4. Click on "Local CPU - Llama 3.2 1B"
5. Click on "Local CPU - Qwen 2.5 0.5B"
6. Press Escape or click outside to close dropdown
7. Verify two chat panels appear side by side
8. Type "Olá, como você está?" in the input field
9. Press Enter or click send button
10. Wait for responses (should appear within 10-20 seconds)
11. Verify both models respond with Portuguese text

## Test Results Interpretation

### Console Output

**Success indicators**:
```
✓ Navigated to Chat Arena
✓ Model selector opened
✓ Selected first model
✓ Selected second model
✓ Responses received in 8.3s
✅ SUCCESS: Chat Arena is working! Models responded successfully.
```

**Failure indicators**:
```
⚠ Found 0 local model(s)
❌ FAILURE: Errors occurred during model inference.
⚠ PARTIAL: Models are still processing. May need more time.
```

### Screenshots Analysis

1. Check `step2-model-selector.png` for model availability
2. Check `step3-models-selected.png` for selection checkmarks
3. Check `step6-responses.png` for actual responses
4. Check `debug-*.png` files for detailed UI state

## CI/CD Integration

To run in CI/CD pipeline:

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install --with-deps chromium

# Run tests
npx playwright test tests/chat-arena-local-test.spec.js --reporter=html

# Generate report
npx playwright show-report
```

## Troubleshooting Checklist

- [ ] Ollama is running (`ollama serve`)
- [ ] Models are installed (`ollama list`)
- [ ] Web app is running on port 4896
- [ ] Backend API responds (`curl http://localhost:4896/api/v1/chat/models`)
- [ ] Ollama API responds (`curl http://localhost:11434/api/tags`)
- [ ] Playwright is installed (`npx playwright --version`)
- [ ] Screenshots directory exists (`mkdir -p tests/screenshots`)
- [ ] No port conflicts (4896, 11434)
- [ ] Sufficient disk space for models
- [ ] Sufficient RAM for model inference

## Support

If tests continue to fail:
1. Run the debug test for detailed logs
2. Check all screenshots in `tests/screenshots/`
3. Review browser console output
4. Check network requests in debug mode
5. Verify manual testing works first
