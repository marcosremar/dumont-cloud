const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('Starting Model Deploy Test...\n');

try {
  // Run the test
  const result = execSync(
    'npx playwright test model-deploy-test.spec.js --reporter=list',
    {
      cwd: '/Users/marcos/CascadeProjects/dumontcloud/web',
      encoding: 'utf-8',
      stdio: 'inherit',
      timeout: 180000 // 3 minutes
    }
  );

  console.log('\n✓ Test completed successfully');
} catch (error) {
  console.error('\n✗ Test failed with error:');
  console.error(error.message);
  process.exit(1);
}
