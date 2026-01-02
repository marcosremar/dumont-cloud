#!/bin/bash

# Test runner for Machines page tests
# Runs Playwright tests against http://localhost:4893

set -e

echo "=========================================="
echo "Dumont Cloud - Machines Page Test Runner"
echo "=========================================="
echo ""

# Check if server is running
echo "Checking if server is running on http://localhost:4893..."
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:4893 | grep -q "200\|301\|302"; then
    echo "ERROR: Server is not running on http://localhost:4893"
    echo "Please start the server first:"
    echo "  cd /Users/marcos/CascadeProjects/dumontcloud/web"
    echo "  npm run dev -- --port 4893"
    exit 1
fi

echo "Server is running!"
echo ""

# Navigate to tests directory
cd /Users/marcos/CascadeProjects/dumontcloud/tests

# Run the tests
echo "Running Machines page tests..."
echo ""

npx playwright test test-machines.spec.js --reporter=list

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "All tests passed!"
    echo "=========================================="
    echo ""
    echo "Screenshots saved to: test-results/"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "Some tests failed!"
    echo "=========================================="
    echo ""
    echo "Check the output above for details"
    echo "Screenshots saved to: test-results/"
    echo ""
    exit 1
fi
