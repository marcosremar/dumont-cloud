#!/bin/bash

# Script para executar Vibe Tests do Dumont Cloud
# Este script facilita a execução dos testes de comportamento real

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Dumont Cloud - Vibe Tests Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if dev server is running
if ! curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${YELLOW}Dev server not running on localhost:5173${NC}"
    echo -e "${YELLOW}Starting dev server...${NC}"
    cd web && npm run dev > /tmp/vite-dev.log 2>&1 &
    DEV_SERVER_PID=$!
    echo -e "${GREEN}Dev server started (PID: $DEV_SERVER_PID)${NC}"
    echo "Waiting for server to be ready..."
    sleep 5
    cd ..
else
    echo -e "${GREEN}Dev server already running${NC}"
fi

# Parse arguments
TEST_FILE=""
MODE="headless"
REPORTER="list"

while [[ $# -gt 0 ]]; do
    case $1 in
        --ui)
            MODE="ui"
            shift
            ;;
        --headed)
            MODE="headed"
            shift
            ;;
        --html)
            REPORTER="html"
            shift
            ;;
        --failover)
            TEST_FILE="tests/vibe/failover-journey-vibe.spec.js"
            shift
            ;;
        *)
            TEST_FILE="$1"
            shift
            ;;
    esac
done

# Default to all vibe tests if no file specified
if [ -z "$TEST_FILE" ]; then
    TEST_FILE="tests/vibe/"
    echo -e "${BLUE}Running ALL vibe tests${NC}"
else
    echo -e "${BLUE}Running: ${TEST_FILE}${NC}"
fi

echo ""

# Build command
CMD="npx playwright test ${TEST_FILE} --project=chromium"

if [ "$MODE" == "ui" ]; then
    CMD="${CMD} --ui"
    echo -e "${YELLOW}Running in UI mode (visual debugger)${NC}"
elif [ "$MODE" == "headed" ]; then
    CMD="${CMD} --headed"
    echo -e "${YELLOW}Running in headed mode (visible browser)${NC}"
else
    echo -e "${YELLOW}Running in headless mode${NC}"
fi

if [ "$REPORTER" == "html" ]; then
    CMD="${CMD} --reporter=html"
    echo -e "${YELLOW}HTML report will be generated${NC}"
fi

echo ""
echo -e "${BLUE}Command: ${CMD}${NC}"
echo ""

# Run the tests
eval $CMD
TEST_EXIT_CODE=$?

# If HTML report was generated, show it
if [ "$REPORTER" == "html" ]; then
    echo ""
    echo -e "${GREEN}Opening HTML report...${NC}"
    npx playwright show-report
fi

# Exit with test exit code
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Some tests failed (exit code: $TEST_EXIT_CODE)${NC}"
    echo -e "${RED}========================================${NC}"
fi

exit $TEST_EXIT_CODE
