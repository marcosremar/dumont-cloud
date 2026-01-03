#!/bin/bash

# Chat Arena Local Test Runner
# This script runs the Chat Arena UI test against localhost:4896

echo "=================================="
echo "Chat Arena Local Ollama Test"
echo "=================================="
echo ""
echo "Testing Chat Arena UI at http://localhost:4896/chat-arena"
echo ""

# Ensure screenshots directory exists
mkdir -p tests/screenshots

# Run the test
npx playwright test tests/chat-arena-local-test.spec.js \
  --headed \
  --project=chromium \
  --workers=1 \
  --reporter=list

echo ""
echo "=================================="
echo "Test complete!"
echo "Check tests/screenshots/ for visual results"
echo "=================================="
