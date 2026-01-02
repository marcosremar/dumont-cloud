import { test, expect } from '@playwright/test';

/**
 * Interactive test to inspect wizard console and network activity
 * Run with: BASE_URL=http://localhost:4896 npx playwright test wizard-inspect-console.spec.ts --headed --project=chromium
 */

test.describe('Wizard Console Inspector', () => {

  test('Inspect Step 2 console and network', async ({ page }) => {
    // Capture ALL console messages
    const allLogs: any[] = [];

    page.on('console', msg => {
      allLogs.push({
        type: msg.type(),
        text: msg.text(),
        location: msg.location(),
      });
    });

    // Capture all network activity
    const networkLog: any[] = [];

    page.on('request', req => {
      networkLog.push({
        type: 'request',
        url: req.url(),
        method: req.method(),
        headers: req.headers(),
      });
    });

    page.on('response', async res => {
      const req = networkLog.find(r => r.url === res.url() && r.type === 'request');
      if (req) {
        req.status = res.status();
        req.statusText = res.statusText();

        // Try to get response body for API calls
        if (res.url().includes('/api/')) {
          try {
            const body = await res.text();
            req.responseBody = body.substring(0, 500); // First 500 chars
          } catch (e) {
            req.responseBody = '<unable to read>';
          }
        }
      }
    });

    console.log('\n🚀 Starting wizard inspection...\n');

    // Step 1: Login
    await page.goto('http://localhost:4896/login?auto_login=demo');
    await page.waitForURL('**/app**', { timeout: 15000 });
    console.log('✅ Logged in\n');

    // Step 2: Navigate to Step 2
    const regionBtn = page.locator('button:has-text("EUA")').first();
    await regionBtn.waitFor({ state: 'visible', timeout: 5000 });
    await regionBtn.click();
    console.log('✅ Region selected\n');

    const nextBtn = page.locator('button:has-text("Próximo")').first();
    await nextBtn.click();
    await page.waitForTimeout(2000);
    console.log('✅ Moved to Step 2\n');

    // Step 3: Select a tier
    const rapidoBtn = page.locator('button:has-text("Rápido"), button:has-text("Experimentar")').first();
    const hasTierBtn = await rapidoBtn.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasTierBtn) {
      console.log('Clicking tier button...\n');
      await rapidoBtn.click();
      await page.waitForTimeout(3000); // Wait for any API calls
    }

    // Step 4: Dump all console logs
    console.log('=====================================');
    console.log('📋 CONSOLE LOGS');
    console.log('=====================================\n');

    const errorLogs = allLogs.filter(l => l.type === 'error');
    const warningLogs = allLogs.filter(l => l.type === 'warning');
    const infoLogs = allLogs.filter(l => l.type === 'log' || l.type === 'info');

    console.log(`❌ ERRORS (${errorLogs.length}):`);
    errorLogs.forEach((log, i) => {
      console.log(`  ${i + 1}. ${log.text}`);
      if (log.location) {
        console.log(`     Location: ${log.location.url}:${log.location.lineNumber}`);
      }
    });

    console.log(`\n⚠️  WARNINGS (${warningLogs.length}):`);
    warningLogs.slice(0, 5).forEach((log, i) => {
      console.log(`  ${i + 1}. ${log.text}`);
    });

    console.log(`\nℹ️  INFO/LOG (${infoLogs.length} total, showing first 10):`);
    infoLogs.slice(0, 10).forEach((log, i) => {
      console.log(`  ${i + 1}. ${log.text}`);
    });

    // Step 5: Dump network activity
    console.log('\n=====================================');
    console.log('🌐 NETWORK ACTIVITY');
    console.log('=====================================\n');

    const apiCalls = networkLog.filter(r => r.url.includes('/api/'));
    console.log(`Total API calls: ${apiCalls.length}\n`);

    apiCalls.forEach((call, i) => {
      console.log(`${i + 1}. ${call.method} ${new URL(call.url).pathname}`);
      console.log(`   Status: ${call.status || 'pending'} ${call.statusText || ''}`);
      if (call.responseBody) {
        console.log(`   Response: ${call.responseBody}`);
      }
      console.log('');
    });

    // Check for offers endpoint specifically
    const offersCall = apiCalls.find(c => c.url.includes('/instances/offers'));
    if (offersCall) {
      console.log('✅ /api/v1/instances/offers WAS CALLED');
      console.log(`   Status: ${offersCall.status}`);
      console.log(`   Response: ${offersCall.responseBody || 'N/A'}`);
    } else {
      console.log('❌ /api/v1/instances/offers WAS NOT CALLED');
    }

    // Step 6: Check localStorage
    console.log('\n=====================================');
    console.log('💾 LOCALSTORAGE');
    console.log('=====================================\n');

    const demoMode = await page.evaluate(() => localStorage.getItem('demo_mode'));
    const authToken = await page.evaluate(() => localStorage.getItem('access_token'));

    console.log(`demo_mode: ${demoMode}`);
    console.log(`access_token: ${authToken ? 'present (length: ' + authToken.length + ')' : 'not found'}`);

    // Take final screenshot
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-console-inspect.png',
      fullPage: true,
    });

    console.log('\n📸 Screenshot saved: wizard-console-inspect.png\n');

    // Pause for manual inspection if running headed
    // await page.pause();
  });
});
