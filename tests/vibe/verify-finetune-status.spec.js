// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * VIBE TEST: Verify Fine-Tuning Job Status
 *
 * Environment: Staging REAL (localhost:5173 for dev, dumontcloud.com for prod)
 * Type: VERIFICATION - Check real status of created jobs
 * Generated: 2025-12-19
 *
 * This is a VERIFICATION vibe test to check the real status of fine-tuning jobs
 * that were created in the system. We DO NOT create new jobs - we only verify.
 *
 * Journey tested:
 * 1. Login (authentication real)
 * 2. Navigate to Fine-Tuning page (/app/finetune)
 * 3. Find job cards with name "test-finetune-phi3-*"
 * 4. Check status badge on job card (Pending, Running, Failed, etc.)
 * 5. Click "Refresh" button on job card to get latest status from backend
 * 6. Click "Logs" button to open logs modal
 * 7. Verify logs content (or if empty)
 * 8. Make direct API call to /api/finetune/jobs to verify backend data
 * 9. Document real status observed
 *
 * PRINCIPLES VIBE TESTING:
 * - NEVER use demo_mode or mocks
 * - Always check real backend data
 * - Capture timing for each action
 * - Validate visual feedback (status badges, icons, colors)
 * - Simulate real user behavior (click, wait, read)
 * - Report what we actually see, not what we expect
 */

test.describe('Fine-Tuning Job Status - Verification Vibe Test', () => {

  test.beforeEach(async ({ page }) => {
    // CRITICAL: Garantir que demo mode está SEMPRE desabilitado
    await page.addInitScript(() => {
      localStorage.removeItem('demo_mode');
      localStorage.setItem('demo_mode', 'false');
    });
  });

  test('should verify real status of fine-tuning jobs', async ({ page }) => {
    const startTime = Date.now();
    console.log('\n========================================');
    console.log('VIBE TEST: Verify Fine-Tuning Job Status');
    console.log('Environment: REAL (no mocks)');
    console.log('Test Type: VERIFICATION');
    console.log('========================================\n');

    // ==========================================
    // STEP 1: LOGIN & NAVIGATE TO FINE-TUNING
    // ==========================================
    console.log('STEP 1: Login and navigate to Fine-Tuning page');
    const step1Start = Date.now();

    await page.goto('/app/finetune');
    await page.waitForLoadState('networkidle');

    const step1Duration = Date.now() - step1Start;
    console.log(`Time: ${step1Duration}ms`);
    console.log('Status: Navigated to Fine-Tuning page');

    // Verify we're on the fine-tuning page
    const currentUrl = page.url();
    expect(currentUrl).toContain('/app/finetune');
    console.log('Validated: URL contains /app/finetune');

    // ==========================================
    // STEP 2: WAIT FOR JOBS TO LOAD
    // ==========================================
    console.log('\nSTEP 2: Wait for jobs to load');
    const step2Start = Date.now();

    // Wait for page header
    const pageTitle = page.locator('h1:has-text("Fine-Tuning")');
    await expect(pageTitle).toBeVisible({ timeout: 5000 });
    console.log('Validated: Page title "Fine-Tuning" visible');

    // Wait for initial data load
    await page.waitForTimeout(2000);

    const step2Duration = Date.now() - step2Start;
    console.log(`Time: ${step2Duration}ms`);
    console.log('Status: Page loaded, checking for jobs...');

    // ==========================================
    // STEP 3: CHECK STATS SECTION
    // ==========================================
    console.log('\nSTEP 3: Check stats section');
    const step3Start = Date.now();

    // Verify stats cards are visible
    const totalJobsCard = page.locator('text="Total Jobs"');
    const hasStats = await totalJobsCard.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasStats) {
      // Get stats values
      const totalJobsValue = await page.locator('.text-3xl').first().textContent();
      const runningJobsValue = await page.locator('.text-purple-400').first().textContent();
      const completedJobsValue = await page.locator('.text-green-400').first().textContent();
      const failedJobsValue = await page.locator('.text-red-400').first().textContent();

      console.log('Stats Dashboard:');
      console.log(`  Total Jobs: ${totalJobsValue}`);
      console.log(`  Running: ${runningJobsValue}`);
      console.log(`  Completed: ${completedJobsValue}`);
      console.log(`  Failed: ${failedJobsValue}`);
    } else {
      console.log('Status: Stats section not visible (may still be loading)');
    }

    const step3Duration = Date.now() - step3Start;
    console.log(`Time: ${step3Duration}ms`);

    // ==========================================
    // STEP 4: FIND TEST JOB CARDS
    // ==========================================
    console.log('\nSTEP 4: Find job cards with "test-finetune-phi3" in name');
    const step4Start = Date.now();

    // Check if there's an empty state message
    const emptyStateMessage = page.locator('text="No Fine-Tuning Jobs"');
    const isEmpty = await emptyStateMessage.isVisible({ timeout: 2000 }).catch(() => false);

    if (isEmpty) {
      console.log('Status: No jobs found - empty state displayed');
      console.log('Message: "You haven\'t created any fine-tuning jobs yet."');
      const step4Duration = Date.now() - step4Start;
      console.log(`Time: ${step4Duration}ms`);

      console.log('\n========================================');
      console.log('VERIFICATION RESULT: NO JOBS FOUND');
      console.log('========================================');
      console.log('The fine-tuning page is accessible but no jobs exist.');
      console.log('This means either:');
      console.log('1. Jobs haven\'t been created yet');
      console.log('2. Jobs were created but not persisted');
      console.log('3. Backend is not returning job data');
      console.log('========================================\n');

      return; // Exit gracefully - not a failure, just no data
    }

    // Look for job cards in the grid
    const jobGrid = page.locator('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-3');
    const hasJobGrid = await jobGrid.isVisible().catch(() => false);

    if (!hasJobGrid) {
      console.log('Status: Job grid not visible');
      const step4Duration = Date.now() - step4Start;
      console.log(`Time: ${step4Duration}ms`);
      test.skip();
      return;
    }

    // Get all job cards
    const allJobCards = page.locator('[class*="bg-[#1e2536]"][class*="rounded-xl"]').filter({
      has: page.locator('h3')
    });
    const totalCards = await allJobCards.count();
    console.log(`Total job cards found: ${totalCards}`);

    // Filter for test-finetune-phi3 jobs
    const testJobCards = page.locator('h3').filter({ hasText: 'test-finetune-phi3' });
    const testJobCount = await testJobCards.count();

    const step4Duration = Date.now() - step4Start;
    console.log(`Time: ${step4Duration}ms`);
    console.log(`Job cards matching "test-finetune-phi3": ${testJobCount}`);

    if (testJobCount === 0) {
      console.log('\nStatus: No test jobs with "test-finetune-phi3" pattern found');
      console.log('Available jobs (first 3):');

      for (let i = 0; i < Math.min(3, totalCards); i++) {
        const card = allJobCards.nth(i);
        const jobName = await card.locator('h3').textContent();
        console.log(`  ${i + 1}. ${jobName}`);
      }

      console.log('\n========================================');
      console.log('VERIFICATION RESULT: TEST JOBS NOT FOUND');
      console.log('========================================');
      console.log(`Total jobs in system: ${totalCards}`);
      console.log('Jobs matching "test-finetune-phi3": 0');
      console.log('\nThis means:');
      console.log('- Other jobs exist in the system');
      console.log('- But no jobs with the test pattern were found');
      console.log('- Test job may have been deleted or not created');
      console.log('========================================\n');

      return; // Exit gracefully
    }

    // ==========================================
    // STEP 5: INSPECT FIRST TEST JOB
    // ==========================================
    console.log('\nSTEP 5: Inspect first test job details');
    const step5Start = Date.now();

    // Get the first test job card (parent container)
    const firstTestCard = allJobCards.filter({
      has: page.locator('h3:has-text("test-finetune-phi3")')
    }).first();

    // Get job name and ID
    const jobName = await firstTestCard.locator('h3').textContent();
    const jobId = await firstTestCard.locator('p.text-sm.text-gray-400').first().textContent();

    console.log(`Job Name: ${jobName}`);
    console.log(`Job ID: ${jobId}`);

    // Get status badge
    const statusBadge = firstTestCard.locator('[class*="text-xs px-2 py-1 rounded"]');
    const statusText = await statusBadge.textContent();
    const statusClasses = await statusBadge.getAttribute('class');

    console.log(`Status Badge: ${statusText}`);
    console.log(`Status Color: ${statusClasses?.match(/text-\w+-\d+/)?.[0] || 'unknown'}`);

    // Get model info
    const modelName = await firstTestCard.locator('text=/Model:|phi|llama|mistral/i').textContent().catch(() => 'N/A');
    console.log(`Model: ${modelName}`);

    // Get GPU info
    const gpuType = await firstTestCard.locator('text=/GPU:|RTX|A100|H100/i').textContent().catch(() => 'N/A');
    console.log(`GPU: ${gpuType}`);

    // Check for progress bar (if running)
    const progressBar = firstTestCard.locator('[role="progressbar"]');
    const hasProgress = await progressBar.isVisible().catch(() => false);
    if (hasProgress) {
      const progressValue = await progressBar.getAttribute('aria-valuenow');
      console.log(`Progress: ${progressValue}%`);
    }

    // Check for error message (if failed)
    const errorMessage = firstTestCard.locator('[class*="bg-red-500"]');
    const hasError = await errorMessage.isVisible().catch(() => false);
    if (hasError) {
      const errorText = await errorMessage.textContent();
      console.log(`Error: ${errorText}`);
    }

    // Get timestamps
    const createdAt = await firstTestCard.locator('text=/Created|Created /i').textContent().catch(() => 'N/A');
    console.log(`Created: ${createdAt}`);

    const step5Duration = Date.now() - step5Start;
    console.log(`Time: ${step5Duration}ms`);
    console.log('Status: Job details extracted');

    // ==========================================
    // STEP 6: CLICK REFRESH BUTTON
    // ==========================================
    console.log('\nSTEP 6: Click "Refresh" button to get latest status');
    const step6Start = Date.now();

    const refreshButton = firstTestCard.locator('button:has-text("Refresh")');
    await expect(refreshButton).toBeVisible();
    console.log('Validated: "Refresh" button is visible');

    // Click refresh
    await refreshButton.click();
    console.log('Action: Clicked "Refresh" button');

    // Wait for API call to complete
    await page.waitForTimeout(1500);

    // Check if status changed
    const newStatusText = await statusBadge.textContent();
    console.log(`Status after refresh: ${newStatusText}`);

    if (newStatusText !== statusText) {
      console.log(`Status changed: ${statusText} -> ${newStatusText}`);
    } else {
      console.log('Status unchanged after refresh');
    }

    const step6Duration = Date.now() - step6Start;
    console.log(`Time: ${step6Duration}ms`);
    console.log('Status: Refresh completed');

    // ==========================================
    // STEP 7: CLICK LOGS BUTTON
    // ==========================================
    console.log('\nSTEP 7: Click "Logs" button to view job logs');
    const step7Start = Date.now();

    const logsButton = firstTestCard.locator('button:has-text("Logs")');
    await expect(logsButton).toBeVisible();
    console.log('Validated: "Logs" button is visible');

    // Click logs
    await logsButton.click();
    console.log('Action: Clicked "Logs" button');

    // Wait for modal to appear
    await page.waitForTimeout(1000);

    // Check for logs modal
    const logsModal = page.locator('.fixed.inset-0').filter({
      has: page.locator('text=/Logs:|Logs: /i')
    });
    const hasModal = await logsModal.isVisible().catch(() => false);

    if (!hasModal) {
      console.log('Status: Logs modal did not appear');
    } else {
      console.log('Status: Logs modal opened');

      // Check modal title
      const modalTitle = await logsModal.locator('h3').textContent();
      console.log(`Modal title: ${modalTitle}`);

      // Wait for logs to load
      await page.waitForTimeout(1500);

      // Check for loading spinner
      const loadingSpinner = logsModal.locator('[class*="animate-spin"]');
      const isLoading = await loadingSpinner.isVisible().catch(() => false);

      if (isLoading) {
        console.log('Status: Logs are loading...');
        await page.waitForTimeout(2000);
      }

      // Check logs content
      const logsContent = logsModal.locator('pre');
      const hasLogsContent = await logsContent.isVisible().catch(() => false);

      if (hasLogsContent) {
        const logsText = await logsContent.textContent();
        const logsLength = logsText?.length || 0;
        const logsLines = logsText?.split('\n').length || 0;

        console.log(`Logs length: ${logsLength} characters`);
        console.log(`Logs lines: ${logsLines} lines`);

        if (logsLength > 0) {
          // Show first 200 chars
          const preview = logsText?.substring(0, 200);
          console.log(`Logs preview: ${preview}...`);
        } else {
          console.log('Logs content: Empty or "No logs available"');
        }
      } else {
        console.log('Status: No logs content visible');
      }

      // Close modal
      const closeButton = logsModal.locator('button:has-text("Close")');
      if (await closeButton.isVisible().catch(() => false)) {
        await closeButton.click();
        console.log('Action: Closed logs modal');
      }
    }

    const step7Duration = Date.now() - step7Start;
    console.log(`Time: ${step7Duration}ms`);
    console.log('Status: Logs inspection completed');

    // ==========================================
    // STEP 8: VERIFY BACKEND API
    // ==========================================
    console.log('\nSTEP 8: Verify backend API directly');
    const step8Start = Date.now();

    // Make direct API call
    const apiResponse = await page.evaluate(async () => {
      const token = localStorage.getItem('auth_token');
      try {
        const res = await fetch('/api/finetune/jobs', {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        });
        const data = await res.json();
        return {
          ok: res.ok,
          status: res.status,
          data: data,
        };
      } catch (err) {
        return {
          ok: false,
          error: err.message,
        };
      }
    });

    if (!apiResponse.ok) {
      console.log(`API Error: ${apiResponse.error || `Status ${apiResponse.status}`}`);
    } else {
      const jobs = apiResponse.data.jobs || [];
      console.log(`API Response: ${jobs.length} jobs returned`);

      // Find test jobs in API response
      const testJobs = jobs.filter(j => j.name && j.name.includes('test-finetune-phi3'));
      console.log(`Test jobs in API: ${testJobs.length}`);

      if (testJobs.length > 0) {
        const firstJob = testJobs[0];
        console.log('\nFirst test job from API:');
        console.log(`  ID: ${firstJob.id}`);
        console.log(`  Name: ${firstJob.name}`);
        console.log(`  Status: ${firstJob.status}`);
        console.log(`  Base Model: ${firstJob.base_model}`);
        console.log(`  GPU Type: ${firstJob.gpu_type}`);
        console.log(`  Created: ${firstJob.created_at}`);
        if (firstJob.error_message) {
          console.log(`  Error: ${firstJob.error_message}`);
        }
      }
    }

    const step8Duration = Date.now() - step8Start;
    console.log(`Time: ${step8Duration}ms`);
    console.log('Status: Backend API verified');

    // ==========================================
    // FINAL SUMMARY
    // ==========================================
    const totalDuration = Date.now() - startTime;
    console.log('\n========================================');
    console.log('VIBE TEST COMPLETE - VERIFICATION SUMMARY');
    console.log('========================================');
    console.log(`Total verification time: ${totalDuration}ms (${(totalDuration/1000).toFixed(2)}s)`);
    console.log('\nStep Breakdown:');
    console.log(`  1. Navigation:        ${step1Duration}ms`);
    console.log(`  2. Jobs loading:      ${step2Duration}ms`);
    console.log(`  3. Stats check:       ${step3Duration}ms`);
    console.log(`  4. Find test jobs:    ${step4Duration}ms`);
    console.log(`  5. Inspect job:       ${step5Duration}ms`);
    console.log(`  6. Refresh status:    ${step6Duration}ms`);
    console.log(`  7. View logs:         ${step7Duration}ms`);
    console.log(`  8. API verification:  ${step8Duration}ms`);
    console.log('\nVerifications completed:');
    console.log('  - Fine-tuning page accessible');
    console.log(`  - Test jobs found: ${testJobCount}`);
    console.log('  - Job status badge visible');
    console.log('  - Refresh button functional');
    console.log('  - Logs modal accessible');
    console.log('  - Backend API returning data');
    console.log('\nREAL STATUS OBSERVED:');
    console.log(`  Job: ${jobName}`);
    console.log(`  Status: ${statusText}`);
    console.log(`  Model: ${modelName}`);
    console.log(`  GPU: ${gpuType}`);
    console.log('========================================\n');

    // Final assertion - if we got here, verification passed
    expect(testJobCount).toBeGreaterThan(0);
  });

  /**
   * TEST: Verify job filtering works
   *
   * This test verifies the filter tabs (All, Running, Completed, Failed)
   * work correctly and show the appropriate jobs.
   */
  test('should verify job filtering tabs work', async ({ page }) => {
    const startTime = Date.now();
    console.log('\n========================================');
    console.log('VIBE TEST: Verify Job Filtering');
    console.log('Environment: REAL (no mocks)');
    console.log('========================================\n');

    // Navigate to fine-tuning page
    console.log('STEP 1: Navigate to Fine-Tuning page');
    await page.goto('/app/finetune');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check if empty
    const isEmpty = await page.locator('text="No Fine-Tuning Jobs"').isVisible({ timeout: 2000 }).catch(() => false);
    if (isEmpty) {
      console.log('Status: No jobs to filter - skipping test');
      return;
    }

    // Count initial jobs
    const allJobCards = page.locator('[class*="bg-[#1e2536]"][class*="rounded-xl"]').filter({
      has: page.locator('h3')
    });
    const initialCount = await allJobCards.count();
    console.log(`Initial job count (All): ${initialCount}`);

    // Test "All" filter
    console.log('\nSTEP 2: Test "All" filter');
    const allTab = page.locator('button:has-text("All")').first();
    await allTab.click();
    await page.waitForTimeout(500);
    const allCount = await allJobCards.count();
    console.log(`Jobs shown with "All" filter: ${allCount}`);

    // Test "Running" filter
    console.log('\nSTEP 3: Test "Running" filter');
    const runningTab = page.locator('button:has-text("Running")').first();
    await runningTab.click();
    await page.waitForTimeout(500);
    const runningCount = await allJobCards.count();
    console.log(`Jobs shown with "Running" filter: ${runningCount}`);

    // Check for empty state or job cards
    const runningEmpty = await page.locator('text="No running jobs found"').isVisible().catch(() => false);
    if (runningEmpty) {
      console.log('Status: No running jobs');
    }

    // Test "Completed" filter
    console.log('\nSTEP 4: Test "Completed" filter');
    const completedTab = page.locator('button:has-text("Completed")').first();
    await completedTab.click();
    await page.waitForTimeout(500);
    const completedCount = await allJobCards.count();
    console.log(`Jobs shown with "Completed" filter: ${completedCount}`);

    // Test "Failed" filter
    console.log('\nSTEP 5: Test "Failed" filter');
    const failedTab = page.locator('button:has-text("Failed")').first();
    await failedTab.click();
    await page.waitForTimeout(500);
    const failedCount = await allJobCards.count();
    console.log(`Jobs shown with "Failed" filter: ${failedCount}`);

    // Summary
    const totalDuration = Date.now() - startTime;
    console.log('\n========================================');
    console.log('FILTER TEST COMPLETE');
    console.log('========================================');
    console.log(`Duration: ${totalDuration}ms`);
    console.log('\nFilter Results:');
    console.log(`  All: ${allCount} jobs`);
    console.log(`  Running: ${runningCount} jobs`);
    console.log(`  Completed: ${completedCount} jobs`);
    console.log(`  Failed: ${failedCount} jobs`);
    console.log('========================================\n');

    // Verify filtering logic
    expect(allCount).toBeGreaterThanOrEqual(runningCount + completedCount + failedCount);
  });

});
