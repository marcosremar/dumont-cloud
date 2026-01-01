#!/bin/bash
# ==============================================================================
# Failover Tests Runner Script
# ==============================================================================
# This script runs all failover-related E2E tests and generates an HTML report.
#
# Prerequisites:
#   1. Node.js installed
#   2. Playwright installed (run: npm install)
#   3. Frontend running at localhost:5173 (run: cd ../web && npm run dev)
#
# Usage:
#   chmod +x run-failover-tests.sh
#   ./run-failover-tests.sh
#
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Failover Tests Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the tests directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    npm install
fi

# Check if Playwright browsers are installed
if ! npx playwright --version > /dev/null 2>&1; then
    echo -e "${YELLOW}Installing Playwright browsers...${NC}"
    npx playwright install chromium
fi

# Check if frontend is running
echo -e "${YELLOW}Checking if frontend is running at localhost:5173...${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ | grep -q "200\|301\|302"; then
    echo -e "${GREEN}Frontend is running!${NC}"
else
    echo -e "${RED}Frontend is NOT running!${NC}"
    echo -e "${YELLOW}Please start the frontend first:${NC}"
    echo "  cd ../web && npm run dev"
    echo ""
    echo -e "${YELLOW}Then run this script again.${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Running Failover Tests...${NC}"
echo ""

# Run all failover tests with demo mode
export USE_DEMO_MODE=true

# Test files to run
TEST_FILES=(
    "e2e-journeys/cpu-standby-failover.spec.js"
    "e2e-journeys/failover-complete-journeys.spec.js"
    "e2e-journeys/failover-strategy-selection.spec.js"
)

# Run each test file
TOTAL_PASSED=0
TOTAL_FAILED=0
RESULTS=()

for test_file in "${TEST_FILES[@]}"; do
    echo -e "${YELLOW}Running: ${test_file}${NC}"

    if npx playwright test "$test_file" --reporter=line 2>&1 | tee -a playwright-output.log; then
        echo -e "${GREEN}PASSED: ${test_file}${NC}"
        RESULTS+=("${GREEN}PASSED${NC}: $test_file")
        ((TOTAL_PASSED++))
    else
        echo -e "${RED}FAILED: ${test_file}${NC}"
        RESULTS+=("${RED}FAILED${NC}: $test_file")
        ((TOTAL_FAILED++))
    fi
    echo ""
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Test Results Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

for result in "${RESULTS[@]}"; do
    echo -e "  $result"
done

echo ""
echo -e "Total: ${GREEN}${TOTAL_PASSED} passed${NC}, ${RED}${TOTAL_FAILED} failed${NC}"
echo ""

# Generate HTML report
echo -e "${YELLOW}Generating HTML report...${NC}"
npx playwright show-report &

echo ""
echo -e "${GREEN}Done!${NC}"
echo -e "HTML report should open in your browser automatically."
echo "If not, run: npx playwright show-report"
