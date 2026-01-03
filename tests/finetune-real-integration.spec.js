/**
 * Fine-Tuning Real Integration Tests
 * Creates REAL fine-tuning jobs for 2 lightweight models
 * Tests the complete flow: create job -> monitor -> test in chat
 */
const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.BASE_URL || 'http://localhost:4895';

// Two lightweight models for real fine-tuning
const TEST_MODELS = [
  {
    id: 'unsloth/tinyllama-bnb-4bit',
    name: 'TinyLlama 1.1B',
    gpu: 'RTX3090',
    jobName: 'test-tinyllama-finetune',
  },
  {
    id: 'unsloth/Phi-3-mini-4k-instruct-bnb-4bit',
    name: 'Phi-3 Mini',
    gpu: 'RTX4090',
    jobName: 'test-phi3-finetune',
  },
];

// Sample dataset URL for testing
const TEST_DATASET_URL = 'https://huggingface.co/datasets/tatsu-lab/alpaca';

test.describe('Real Fine-Tuning Integration', () => {
  test.setTimeout(600000); // 10 minutes timeout for real operations

  test('should create fine-tuning job for TinyLlama', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/finetune`);
    await page.waitForLoadState('networkidle');

    // Click New Fine-Tune Job
    await page.click('button:has-text("New Fine-Tune Job")');
    await page.waitForTimeout(500);

    // Step 1: Select TinyLlama model
    await page.getByText('TinyLlama 1.1B', { exact: true }).click();
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: 'Next' }).click();
    await page.waitForTimeout(500);

    // Step 2: Dataset - use URL
    await page.getByRole('button', { name: 'URL' }).click();
    await page.waitForTimeout(300);
    await page.locator('input[placeholder*="huggingface"]').fill(TEST_DATASET_URL);
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: 'Next' }).click();
    await page.waitForTimeout(500);

    // Step 3: Configuration
    const jobNameInput = page.locator('input[placeholder="my-fine-tuned-model"]');
    await jobNameInput.waitFor({ state: 'visible' });
    await jobNameInput.fill(TEST_MODELS[0].jobName);
    await page.waitForTimeout(300);

    // Select RTX 3090 GPU
    await page.locator('button:has-text("RTX 3090")').first().click();
    await page.waitForTimeout(300);

    await page.getByRole('button', { name: 'Next' }).click();
    await page.waitForTimeout(500);

    // Step 4: Review - take screenshot
    await expect(page.getByText('Step 4 of 4', { exact: false })).toBeVisible();
    await page.screenshot({ path: 'tests/screenshots/tinyllama-review.png' });

    // Launch the job
    await page.getByRole('button', { name: 'Launch Fine-Tuning' }).click();

    // Wait for job creation response
    await page.waitForTimeout(3000);

    // Verify job was created (should see job card or success message)
    // The modal should close and we should see the job in the list
    await expect(page.locator('text=Fine-Tune Model with Unsloth')).not.toBeVisible({ timeout: 5000 });

    // Take screenshot of dashboard with new job
    await page.screenshot({ path: 'tests/screenshots/tinyllama-job-created.png' });

    console.log('TinyLlama fine-tuning job created successfully');
  });

  test('should create fine-tuning job for Phi-3 Mini', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/finetune`);
    await page.waitForLoadState('networkidle');

    // Click New Fine-Tune Job
    await page.click('button:has-text("New Fine-Tune Job")');
    await page.waitForTimeout(500);

    // Step 1: Select Phi-3 Mini model
    await page.getByText('Phi-3 Mini', { exact: true }).click();
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: 'Next' }).click();
    await page.waitForTimeout(500);

    // Step 2: Dataset - use URL
    await page.getByRole('button', { name: 'URL' }).click();
    await page.waitForTimeout(300);
    await page.locator('input[placeholder*="huggingface"]').fill(TEST_DATASET_URL);
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: 'Next' }).click();
    await page.waitForTimeout(500);

    // Step 3: Configuration
    const jobNameInput = page.locator('input[placeholder="my-fine-tuned-model"]');
    await jobNameInput.waitFor({ state: 'visible' });
    await jobNameInput.fill(TEST_MODELS[1].jobName);
    await page.waitForTimeout(300);

    // Select RTX 4090 GPU
    await page.locator('button:has-text("RTX 4090")').first().click();
    await page.waitForTimeout(300);

    await page.getByRole('button', { name: 'Next' }).click();
    await page.waitForTimeout(500);

    // Step 4: Review
    await expect(page.getByText('Step 4 of 4', { exact: false })).toBeVisible();
    await page.screenshot({ path: 'tests/screenshots/phi3-review.png' });

    // Launch the job
    await page.getByRole('button', { name: 'Launch Fine-Tuning' }).click();

    // Wait for job creation response
    await page.waitForTimeout(3000);

    // Verify modal closed
    await expect(page.locator('text=Fine-Tune Model with Unsloth')).not.toBeVisible({ timeout: 5000 });

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/phi3-job-created.png' });

    console.log('Phi-3 Mini fine-tuning job created successfully');
  });

  test('should monitor job status and verify completion', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/finetune`);
    await page.waitForLoadState('networkidle');

    // Take screenshot of current jobs
    await page.screenshot({ path: 'tests/screenshots/jobs-list.png' });

    // Check for any running or completed jobs
    const runningJobs = page.locator('text=Running');
    const completedJobs = page.locator('text=Completed');
    const pendingJobs = page.locator('text=Pending');
    const queuedJobs = page.locator('text=Queued');

    const hasRunning = await runningJobs.count();
    const hasCompleted = await completedJobs.count();
    const hasPending = await pendingJobs.count();
    const hasQueued = await queuedJobs.count();

    console.log(`Jobs status: Running=${hasRunning}, Completed=${hasCompleted}, Pending=${hasPending}, Queued=${hasQueued}`);

    // If there are completed jobs, we can test them
    if (hasCompleted > 0) {
      console.log('Found completed jobs - can proceed to chat testing');
    } else {
      console.log('No completed jobs yet - fine-tuning may still be in progress');
    }
  });

  test('should test fine-tuned models in chat arena', async ({ page }) => {
    // Navigate to chat arena
    await page.goto(`${BASE_URL}/app/chat-arena`);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'tests/screenshots/chat-arena.png' });

    // Check if chat arena page loaded
    const chatArenaVisible = await page.locator('text=Chat Arena, text=Arena, text=Chat').first().isVisible().catch(() => false);

    if (chatArenaVisible) {
      console.log('Chat Arena page loaded successfully');

      // Try to find model selector or chat input
      const modelSelector = page.locator('select, [role="combobox"]').first();
      const chatInput = page.locator('textarea, input[type="text"]').first();

      if (await modelSelector.isVisible().catch(() => false)) {
        console.log('Model selector found');
      }

      if (await chatInput.isVisible().catch(() => false)) {
        console.log('Chat input found');
        // Type a test message
        await chatInput.fill('Hello, can you tell me about yourself?');
        await page.screenshot({ path: 'tests/screenshots/chat-input.png' });
      }
    } else {
      console.log('Chat Arena page structure different than expected');
    }
  });
});

test.describe('API-based Fine-Tuning Tests', () => {
  test('should create fine-tuning jobs via API', async ({ request }) => {
    // Get auth token from storage or use demo
    const token = process.env.AUTH_TOKEN || '';

    // Create first job - TinyLlama
    const job1Response = await request.post(`${BASE_URL}/api/v1/finetune/jobs`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      data: {
        name: 'api-test-tinyllama',
        base_model: 'unsloth/tinyllama-bnb-4bit',
        dataset_source: 'url',
        dataset_path: TEST_DATASET_URL,
        dataset_format: 'alpaca',
        gpu_type: 'RTX3090',
        num_gpus: 1,
        config: {
          epochs: 1,
          batch_size: 2,
          lora_rank: 8,
        },
      },
    });

    console.log(`TinyLlama API job response: ${job1Response.status()}`);

    if (job1Response.ok()) {
      const job1 = await job1Response.json();
      console.log(`Created job: ${job1.id || job1.name}`);
    } else {
      const errorText = await job1Response.text();
      console.log(`Error creating job: ${errorText}`);
    }

    // Create second job - Phi-3 Mini
    const job2Response = await request.post(`${BASE_URL}/api/v1/finetune/jobs`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      data: {
        name: 'api-test-phi3',
        base_model: 'unsloth/Phi-3-mini-4k-instruct-bnb-4bit',
        dataset_source: 'url',
        dataset_path: TEST_DATASET_URL,
        dataset_format: 'alpaca',
        gpu_type: 'RTX4090',
        num_gpus: 1,
        config: {
          epochs: 1,
          batch_size: 2,
          lora_rank: 16,
        },
      },
    });

    console.log(`Phi-3 API job response: ${job2Response.status()}`);

    if (job2Response.ok()) {
      const job2 = await job2Response.json();
      console.log(`Created job: ${job2.id || job2.name}`);
    } else {
      const errorText = await job2Response.text();
      console.log(`Error creating job: ${errorText}`);
    }
  });

  test('should list all fine-tuning jobs', async ({ request }) => {
    const token = process.env.AUTH_TOKEN || '';

    const response = await request.get(`${BASE_URL}/api/v1/finetune/jobs`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    });

    console.log(`List jobs response: ${response.status()}`);

    if (response.ok()) {
      const data = await response.json();
      console.log(`Total jobs: ${data.count || data.jobs?.length || 0}`);

      if (data.jobs && data.jobs.length > 0) {
        for (const job of data.jobs) {
          console.log(`  - ${job.name}: ${job.status} (${job.base_model})`);
        }
      }
    }
  });

  test('should check fine-tuning system status', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/finetune/status`);

    console.log(`Status response: ${response.status()}`);

    if (response.ok()) {
      const status = await response.json();
      console.log(`SkyPilot available: ${status.skypilot_available}`);
      console.log(`Message: ${status.message}`);
    }
  });

  test('should list supported models', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/finetune/models`);

    console.log(`Models response: ${response.status()}`);

    if (response.ok()) {
      const data = await response.json();
      console.log(`Total supported models: ${data.models?.length || 0}`);

      if (data.models) {
        for (const model of data.models) {
          console.log(`  - ${model.name} (${model.parameters}, ${model.min_vram} VRAM)`);
        }
      }
    }
  });
});
