#!/bin/bash

# Fine-Tuning Vibe Test Runner
# This script runs the Fine-Tuning journey vibe test for Dumont Cloud

set -e

echo "=========================================="
echo "Fine-Tuning Vibe Test Runner"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Playwright is installed
if ! command -v npx &> /dev/null; then
    echo -e "${RED}Error: npx not found. Please install Node.js and npm.${NC}"
    exit 1
fi

# Check if chromium is installed
if ! npx playwright --version &> /dev/null; then
    echo -e "${YELLOW}Playwright not found. Installing...${NC}"
    npm install
    npx playwright install chromium
fi

# Check if backend is running
echo "Checking if backend is running..."
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${YELLOW}⚠ Backend not detected at http://localhost:5000${NC}"
    echo "Make sure to start the backend: python src/main.py"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if frontend is running
echo "Checking if frontend is running..."
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${YELLOW}⚠ Frontend not detected at http://localhost:5173${NC}"
    echo "Make sure to start the frontend: cd web && npm run dev"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "Running Fine-Tuning Vibe Test"
echo "=========================================="
echo ""

# Parse command line arguments
MODE="normal"
if [ "$1" == "--headed" ]; then
    MODE="headed"
    echo "Mode: Headed (visible browser)"
elif [ "$1" == "--ui" ]; then
    MODE="ui"
    echo "Mode: UI (Playwright Inspector)"
elif [ "$1" == "--debug" ]; then
    MODE="debug"
    echo "Mode: Debug (step-by-step)"
else
    echo "Mode: Normal (headless)"
    echo "Tip: Use --headed, --ui, or --debug for interactive modes"
fi

echo ""
echo "Test: tests/vibe/finetune-journey-vibe.spec.js"
echo "Project: chromium"
echo ""
echo "⚠️  WARNING: This test creates a REAL fine-tuning job!"
echo "The job will be provisioned on GCP via SkyPilot."
echo "Estimated cost: ~$1.50/hour for A100 40GB"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Test cancelled."
    exit 0
fi

echo ""
echo "Starting test..."
echo ""

# Run the test based on mode
if [ "$MODE" == "headed" ]; then
    npx playwright test tests/vibe/finetune-journey-vibe.spec.js --project=chromium --headed
elif [ "$MODE" == "ui" ]; then
    npx playwright test tests/vibe/finetune-journey-vibe.spec.js --ui
elif [ "$MODE" == "debug" ]; then
    npx playwright test tests/vibe/finetune-journey-vibe.spec.js --debug
else
    npx playwright test tests/vibe/finetune-journey-vibe.spec.js --project=chromium
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo -e "${GREEN}✓ Test PASSED${NC}"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Check the Fine-Tuning dashboard: http://localhost:5173/app/finetune"
    echo "2. Monitor the job logs"
    echo "3. Wait for completion (~30-60 min)"
    echo "4. Don't forget to cancel the job if testing only!"
    echo ""
else
    echo ""
    echo "=========================================="
    echo -e "${RED}✗ Test FAILED${NC}"
    echo "=========================================="
    echo ""
    echo "Debug steps:"
    echo "1. Check test-results/ for screenshots and videos"
    echo "2. Run with --headed to see the browser"
    echo "3. Run with --debug to step through the test"
    echo "4. Check backend logs for API errors"
    echo ""
    exit 1
fi
