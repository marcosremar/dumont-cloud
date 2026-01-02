#!/bin/bash
# Run Failover Complete System Test
# This script runs the comprehensive E2E failover test suite

set -e

echo "======================================"
echo "Failover Complete System Test Runner"
echo "======================================"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
  echo "❌ Backend is not running on port 8000"
  echo "   Please start backend with: cd /Users/marcos/CascadeProjects/dumontcloud && uvicorn src.main:app --reload --port 8000"
  exit 1
fi

# Check if frontend is running on port 4890
if ! curl -s http://localhost:4890 > /dev/null 2>&1; then
  echo "❌ Frontend is not running on port 4890"
  echo "   Please start frontend with: cd /Users/marcos/CascadeProjects/dumontcloud/web && npm run dev -- --port 4890"
  exit 1
fi

echo "✅ Backend is running"
echo "✅ Frontend is running on port 4890"
echo ""

# Create screenshot directory if it doesn't exist
mkdir -p /Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/failover-complete

echo "🧪 Running Failover Complete System Test..."
echo ""
echo "⚠️  WARNING: This test will:"
echo "   - Create REAL GPU instances on Vast.ai (costs money)"
echo "   - Provision CPU Standby on GCP"
echo "   - Test failover mechanisms"
echo "   - Create and restore snapshots"
echo "   - Clean up all resources at the end"
echo ""
echo "   Estimated runtime: 5-10 minutes"
echo "   Estimated cost: ~$0.20-0.50"
echo ""

read -p "Continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Test cancelled."
  exit 0
fi

echo ""
echo "🚀 Starting test..."
echo ""

# Run the test
cd /Users/marcos/CascadeProjects/dumontcloud/tests

npx playwright test \
  --project=failover-complete-system \
  --headed \
  --reporter=line \
  e2e-journeys/failover-complete-system.spec.js

echo ""
echo "======================================"
echo "✅ Test Complete!"
echo "======================================"
echo ""
echo "📸 Screenshots saved to: tests/screenshots/failover-complete/"
echo "📊 View HTML report: npx playwright show-report"
echo ""
