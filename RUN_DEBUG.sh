#!/bin/bash

echo "=============================================="
echo "  Iniciar Button Debug Test Runner"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}This script will help you debug the Iniciar button issue.${NC}"
echo ""

# Check if dev server is running
echo -e "${YELLOW}Checking if dev server is running...${NC}"
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Dev server is running on port 5173${NC}"
else
    echo -e "${RED}✗ Dev server is NOT running!${NC}"
    echo ""
    echo "Please start the dev server first:"
    echo "  cd /home/ubuntu/dumont-cloud/web"
    echo "  npm run dev"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo ""
echo -e "${BLUE}Select a debug method:${NC}"
echo "  1) Quick Debug Test (recommended - shows console logs)"
echo "  2) Comprehensive Debug Test (detailed with screenshots)"
echo "  3) Props Flow Debug (React internals)"
echo "  4) Run all tests"
echo "  5) Open Manual Debug Tool in browser"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}Running Quick Debug Test...${NC}"
        echo ""
        cd /home/ubuntu/dumont-cloud
        npx playwright test tests/quick-debug.spec.js
        echo ""
        echo -e "${GREEN}Test complete!${NC}"
        echo ""
        echo "Screenshots saved to:"
        echo "  /tmp/quick-debug-before.png"
        echo "  /tmp/quick-debug-after-1s.png"
        echo "  /tmp/quick-debug-after-2s.png"
        echo "  /tmp/quick-debug-after-3s.png"
        ;;
    2)
        echo ""
        echo -e "${YELLOW}Running Comprehensive Debug Test...${NC}"
        echo ""
        cd /home/ubuntu/dumont-cloud
        npx playwright test tests/debug-iniciar-comprehensive.spec.js
        echo ""
        echo -e "${GREEN}Test complete!${NC}"
        echo ""
        echo "Screenshots saved to /tmp/iniciar-debug-*.png"
        ;;
    3)
        echo ""
        echo -e "${YELLOW}Running Props Flow Debug...${NC}"
        echo ""
        cd /home/ubuntu/dumont-cloud
        npx playwright test tests/debug-props-flow.spec.js
        ;;
    4)
        echo ""
        echo -e "${YELLOW}Running all debug tests...${NC}"
        echo ""
        cd /home/ubuntu/dumont-cloud
        npx playwright test tests/quick-debug.spec.js
        npx playwright test tests/debug-props-flow.spec.js
        npx playwright test tests/debug-iniciar-comprehensive.spec.js
        ;;
    5)
        echo ""
        echo -e "${YELLOW}Opening manual debug tool...${NC}"
        echo ""
        echo "Manual debug tool location:"
        echo "  file:///home/ubuntu/dumont-cloud/tests/manual-debug-iniciar.html"
        echo ""
        echo "Open this file in your browser to use the manual debugging tool."
        echo ""
        if command -v xdg-open > /dev/null; then
            xdg-open /home/ubuntu/dumont-cloud/tests/manual-debug-iniciar.html
        elif command -v open > /dev/null; then
            open /home/ubuntu/dumont-cloud/tests/manual-debug-iniciar.html
        else
            echo "Please open this file manually in your browser."
        fi
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}Debug Tips:${NC}"
echo "  1. Check the console output above for [DEBUG] messages"
echo "  2. Look for 'Iniciar button clicked' message"
echo "  3. Look for 'handleStart called' message"
echo "  4. Look for 'showDemoToast called' message"
echo ""
echo "  If you see all these messages, the button IS working!"
echo "  If not, there's an issue with the React component or build."
echo ""
echo -e "${BLUE}For more info, see:${NC}"
echo "  /home/ubuntu/dumont-cloud/INICIAR_BUTTON_DEBUG_SUMMARY.md"
echo ""
