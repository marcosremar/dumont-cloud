#!/bin/bash

# Complete Chat Arena Test Suite
# Runs all checks and tests in sequence

clear

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           Chat Arena Complete Test Suite                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Readiness Check
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 1: Readiness Check${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

chmod +x tests/check-chat-arena-ready.sh
./tests/check-chat-arena-ready.sh

read -p "
Press Enter to continue with tests, or Ctrl+C to abort..."

# Step 2: Run Debug Test
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 2: Debug Test (Verbose Logging)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Running debug test to inspect UI in detail..."
echo ""

npx playwright test tests/chat-arena-debug.spec.js --headed --project=chromium

echo ""
read -p "Debug test complete. Press Enter to continue..."

# Step 3: Run Main Test
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 3: Main Test Suite${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Running main test suite..."
echo ""

npx playwright test tests/chat-arena-local-test.spec.js --headed --project=chromium

echo ""
read -p "Main test complete. Press Enter to continue..."

# Step 4: Run Comprehensive Test
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 4: Comprehensive Test (with JSON Report)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Running comprehensive test with detailed reporting..."
echo ""

npx playwright test tests/chat-arena-comprehensive.spec.js --headed --project=chromium

# Step 5: Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}TEST SUITE COMPLETE${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Results saved to:"
echo "  📸 Screenshots: tests/screenshots/"
echo "  📊 JSON Report: tests/screenshots/test-report.json"
echo "  📄 HTML Report: playwright-report/"
echo ""
echo "To view HTML report:"
echo "  npx playwright show-report"
echo ""

# Show test report if it exists
if [ -f "tests/screenshots/test-report.json" ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Quick Summary from JSON Report:${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Check if jq is available
    if command -v jq > /dev/null 2>&1; then
        echo "Test Success: $(cat tests/screenshots/test-report.json | jq -r '.success')"
        echo "Total Tests: $(cat tests/screenshots/test-report.json | jq '.tests | length')"
        echo "Screenshots: $(cat tests/screenshots/test-report.json | jq '.screenshots | length')"
        echo "Errors: $(cat tests/screenshots/test-report.json | jq '.errors | length')"
    else
        echo "Install 'jq' to see formatted report: brew install jq"
        echo "Or view the file directly: cat tests/screenshots/test-report.json"
    fi
    echo ""
fi

# List screenshots
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Screenshots Captured:${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
ls -lh tests/screenshots/*.png 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    All Tests Complete!                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
