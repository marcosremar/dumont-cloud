#!/bin/bash
cd /Users/marcos/CascadeProjects/dumontcloud/web
npx playwright test test-model-deploy.spec.js --headed --timeout=120000
