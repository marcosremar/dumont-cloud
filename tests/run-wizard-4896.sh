#!/bin/bash

# Run the GPU reservation wizard test on port 4896
# This test navigates through the complete wizard flow

echo "========================================="
echo "GPU Reservation Wizard Test - Port 4896"
echo "========================================="
echo ""
echo "Test URL: http://localhost:4896/demo-app"
echo "Project: wizard-navigation (no auth required)"
echo ""

# Run the test
cd /Users/marcos/CascadeProjects/dumontcloud/tests
npx playwright test wizard-port-4896.spec.js --project=wizard-navigation --headed

echo ""
echo "========================================="
echo "Test completed!"
echo "Check screenshots in: test-results/wizard-4896/"
echo "========================================="
