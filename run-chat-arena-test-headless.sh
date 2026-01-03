#!/bin/bash

# Chat Arena Local Test Runner (Headless)
# This script runs the Chat Arena UI test in headless mode

echo "=================================="
echo "Chat Arena Local Ollama Test (Headless)"
echo "=================================="
echo ""

# Ensure screenshots directory exists
mkdir -p tests/screenshots

# Run the test in headless mode
npx playwright test tests/chat-arena-local-test.spec.js \
  --project=chromium \
  --workers=1 \
  --reporter=list

echo ""
echo "=================================="
echo "Test complete!"
echo "Check tests/screenshots/ for visual results"
echo "=================================="
