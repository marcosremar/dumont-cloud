#!/bin/bash
cd /Users/marcos/CascadeProjects/dumontcloud/tests
BASE_URL=http://localhost:4895 npx playwright test wizard-manual-navigation.spec.js --headed --project=wizard-navigation --timeout=600000
