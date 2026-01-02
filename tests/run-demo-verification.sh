#!/bin/bash

# Script to run demo mode verification test
# This verifies that machines are displayed in Step 2 of the wizard when in demo mode

cd /Users/marcos/CascadeProjects/dumontcloud/tests

# Run the test with BASE_URL set to localhost:4894
BASE_URL=http://localhost:4894 npx playwright test verify-demo-machines.spec.js --headed

# Show the screenshot
if [ -f "test-results/demo-machines-step2.png" ]; then
  echo ""
  echo "Screenshot saved at: test-results/demo-machines-step2.png"
  echo "Opening screenshot..."
  open test-results/demo-machines-step2.png
fi
