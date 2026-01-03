#!/bin/bash

# Quick Chat Arena Test
# One-command test for immediate feedback

echo "🚀 Quick Chat Arena Test"
echo ""

# Ensure screenshots directory exists
mkdir -p tests/screenshots

# Quick check
echo "Quick checks:"
echo -n "  Ollama: "
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓"
else
    echo "✗ (not running - start with: ollama serve)"
    exit 1
fi

echo -n "  Web app: "
if curl -s http://localhost:4896/ > /dev/null 2>&1; then
    echo "✓"
else
    echo "✗ (not running - check port 4896)"
    exit 1
fi

echo ""
echo "Running test..."
echo ""

# Run the main test
npx playwright test tests/chat-arena-local-test.spec.js \
    --headed \
    --project=chromium \
    --workers=1 \
    --timeout=120000 \
    --reporter=line

echo ""
echo "Done! Check tests/screenshots/ for results."
