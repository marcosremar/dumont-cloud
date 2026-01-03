/**
 * Jobs Page E2E Tests
 * Tests for creating, viewing, and managing GPU jobs
 */
const { test, expect } = require('@playwright/test');

// Job configurations for testing - 10 different combinations
const JOB_CONFIGS = [
  {
    name: 'LLM Fine-tuning Job',
    source: 'huggingface',
    hf_repo: 'unsloth/llama-3-8b-Instruct',
    gpu_type: 'RTX 4090',
    disk_size: 100,
    timeout: 480,
    command: 'python train.py --epochs 3',
    pip_packages: 'transformers, accelerate, bitsandbytes'
  },
  {
    name: 'Whisper Transcription',
    source: 'huggingface',
    hf_repo: 'openai/whisper-large-v3',
    gpu_type: 'RTX 3090',
    disk_size: 50,
    timeout: 120,
    command: 'python transcribe.py --model large',
    pip_packages: 'faster-whisper, torch'
  },
  {
    name: 'SDXL Image Generation',
    source: 'huggingface',
    hf_repo: 'stabilityai/stable-diffusion-xl-base-1.0',
    gpu_type: 'RTX 4080',
    disk_size: 80,
    timeout: 60,
    command: 'python generate.py --prompt "landscape"',
    pip_packages: 'diffusers, torch, safetensors'
  },
  {
    name: 'Git Repo Training',
    source: 'git',
    git_url: 'https://github.com/example/ml-project.git',
    git_branch: 'main',
    gpu_type: 'A100',
    disk_size: 200,
    timeout: 720,
    command: 'bash run_training.sh',
    pip_packages: ''
  },
  {
    name: 'Command Only Job',
    source: 'command',
    gpu_type: 'RTX 3080',
    disk_size: 30,
    timeout: 30,
    command: 'nvidia-smi && python -c "import torch; print(torch.cuda.is_available())"',
    pip_packages: 'torch'
  },
  {
    name: 'Embeddings Generation',
    source: 'huggingface',
    hf_repo: 'BAAI/bge-large-en-v1.5',
    gpu_type: 'RTX 4090',
    disk_size: 40,
    timeout: 60,
    command: 'python generate_embeddings.py',
    pip_packages: 'sentence-transformers, faiss-gpu'
  },
  {
    name: 'Model Quantization',
    source: 'huggingface',
    hf_repo: 'meta-llama/Llama-2-7b-hf',
    hf_revision: 'main',
    gpu_type: 'H100',
    disk_size: 150,
    timeout: 240,
    command: 'python quantize.py --bits 4',
    pip_packages: 'auto-gptq, transformers'
  },
  {
    name: 'Benchmark Test',
    source: 'command',
    gpu_type: 'RTX 4090',
    disk_size: 20,
    timeout: 15,
    command: 'python -c "import torch; x = torch.randn(10000,10000).cuda(); print(x.sum())"',
    pip_packages: 'torch'
  },
  {
    name: 'Data Processing',
    source: 'git',
    git_url: 'https://github.com/example/data-pipeline.git',
    gpu_type: 'RTX 3090',
    disk_size: 100,
    timeout: 180,
    command: 'python process_data.py --batch-size 64',
    pip_packages: 'pandas, numpy, cudf'
  },
  {
    name: 'Vision Model Training',
    source: 'huggingface',
    hf_repo: 'microsoft/florence-2-base',
    gpu_type: 'RTX 4080',
    disk_size: 60,
    timeout: 360,
    command: 'python train_vision.py',
    pip_packages: 'timm, torchvision, albumentations'
  }
];

test.describe('Jobs Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to Jobs page
    await page.goto('/app/jobs');

    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display Jobs page correctly', async ({ page }) => {
    // Check page title - use exact match for the h1 title
    await expect(page.getByRole('heading', { name: 'Jobs', exact: true })).toBeVisible();

    // Check for New Job button
    await expect(page.getByRole('button', { name: /new job|novo job/i })).toBeVisible();

    // Check for refresh button
    await expect(page.locator('button').filter({ has: page.locator('svg') }).first()).toBeVisible();
  });

  test('should open job creation modal', async ({ page }) => {
    // Click New Job button
    await page.getByRole('button', { name: /new job|novo job/i }).click();

    // Wait for modal to appear
    await page.waitForTimeout(500);

    // Modal should be visible - look for the modal heading which is "New Job" or "Novo Job"
    await expect(page.locator('.fixed.inset-0 h2')).toBeVisible();

    // Check form fields are present
    await expect(page.locator('input[placeholder*="Fine-tune"]').or(page.locator('input[placeholder*="fine-tune"]')).or(page.locator('input').first())).toBeVisible();
    await expect(page.getByRole('button', { name: /hugging face/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /git/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /command/i })).toBeVisible();
  });

  test('should validate required fields', async ({ page }) => {
    // Open modal
    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Try to submit without filling required fields
    await page.getByRole('button', { name: /create and run|criar e executar/i }).click();

    // Should show validation - form shouldn't submit and modal should still be visible
    await expect(page.locator('.fixed.inset-0 h2')).toBeVisible();
  });

  test('should switch between source types', async ({ page }) => {
    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Test Hugging Face source - it's the default, look for the HF repo input
    await page.getByRole('button', { name: /hugging face/i }).click();
    await expect(page.locator('input[placeholder*="unsloth"]').or(page.locator('input[placeholder*="Instruct"]'))).toBeVisible();

    // Test Git source
    await page.getByRole('button', { name: /git/i }).click();
    await expect(page.locator('input[placeholder*="github.com"]')).toBeVisible();

    // Test Command source
    await page.getByRole('button', { name: /command/i }).click();
    // Command textarea should be visible
    await expect(page.locator('textarea')).toBeVisible();
  });

  test('should select different GPU types', async ({ page }) => {
    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Find GPU select
    const gpuSelect = page.locator('select').first();

    // Test selecting different GPUs
    const gpuTypes = ['RTX 3080', 'RTX 3090', 'RTX 4080', 'RTX 4090', 'A100', 'H100'];

    for (const gpu of gpuTypes) {
      await gpuSelect.selectOption(gpu);
      await expect(gpuSelect).toHaveValue(gpu);
    }
  });

  test('should adjust disk size and timeout', async ({ page }) => {
    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Find disk size input
    const diskInput = page.locator('input[type="number"]').first();
    await diskInput.fill('100');
    await expect(diskInput).toHaveValue('100');

    // Find timeout input
    const timeoutInput = page.locator('input[type="number"]').nth(1);
    await timeoutInput.fill('120');
    await expect(timeoutInput).toHaveValue('120');
  });

  test('should close modal on cancel', async ({ page }) => {
    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Modal should be visible
    await expect(page.locator('.fixed.inset-0 h2')).toBeVisible();

    // Click cancel
    await page.getByRole('button', { name: /cancel|cancelar/i }).click();

    // Modal should be closed
    await expect(page.locator('.fixed.inset-0')).not.toBeVisible();
  });

  test('should display how it works section', async ({ page }) => {
    // Look for the info box - use the specific h4 heading text
    await expect(page.getByRole('heading', { name: 'How does Job mode work?' })).toBeVisible();
  });
});

test.describe('Job Creation - Multiple Jobs', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/app/jobs');
    await page.waitForLoadState('networkidle');
  });

  // Create test for each job configuration
  for (let i = 0; i < JOB_CONFIGS.length; i++) {
    const config = JOB_CONFIGS[i];

    test(`should fill form for job ${i + 1}: ${config.name}`, async ({ page }) => {
      // Open modal
      await page.getByRole('button', { name: /new job|novo job/i }).click();
      await page.waitForTimeout(500);
      await expect(page.locator('.fixed.inset-0 h2')).toBeVisible();

      // Fill job name - first text input in the modal
      const nameInput = page.locator('.fixed.inset-0 input[type="text"]').first();
      await nameInput.fill(config.name);

      // Select source type
      if (config.source === 'huggingface') {
        await page.getByRole('button', { name: /hugging face/i }).click();
        await page.waitForTimeout(200);
        // Find the HF repo input by placeholder
        const hfInput = page.locator('input[placeholder*="unsloth"]').or(page.locator('input[placeholder*="Instruct"]'));
        await hfInput.fill(config.hf_repo);
        if (config.hf_revision) {
          const revisionInput = page.locator('input[placeholder*="main"]').or(page.locator('input[placeholder*="v1.0"]'));
          await revisionInput.fill(config.hf_revision);
        }
      } else if (config.source === 'git') {
        await page.getByRole('button', { name: /git/i }).click();
        await page.waitForTimeout(200);
        const gitUrlInput = page.locator('input[placeholder*="github.com"]');
        await gitUrlInput.fill(config.git_url);
        if (config.git_branch) {
          const branchInput = page.locator('input[placeholder="main"]');
          await branchInput.fill(config.git_branch);
        }
      } else {
        await page.getByRole('button', { name: /command/i }).click();
        await page.waitForTimeout(200);
      }

      // Fill command in textarea
      if (config.command) {
        const commandTextarea = page.locator('textarea');
        await commandTextarea.fill(config.command);
      }

      // Select GPU
      const gpuSelect = page.locator('select').first();
      await gpuSelect.selectOption(config.gpu_type);

      // Fill disk size
      const diskInput = page.locator('input[type="number"]').first();
      await diskInput.fill(config.disk_size.toString());

      // Fill timeout
      const timeoutInput = page.locator('input[type="number"]').nth(1);
      await timeoutInput.fill(config.timeout.toString());

      // Fill pip packages if provided
      if (config.pip_packages) {
        const pipInput = page.locator('input[placeholder*="transformers"]').or(page.locator('input[placeholder*="accelerate"]'));
        await pipInput.fill(config.pip_packages);
      }

      // Verify form is filled correctly
      await expect(nameInput).toHaveValue(config.name);
      await expect(gpuSelect).toHaveValue(config.gpu_type);

      // Take screenshot of filled form
      await page.screenshot({ path: `tests/screenshots/job-${i + 1}-${config.source}.png`, fullPage: true });

      // Close modal (don't actually submit in demo mode)
      await page.getByRole('button', { name: /cancel|cancelar/i }).click();
    });
  }
});

test.describe('Jobs Error Prevention', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/app/jobs');
    await page.waitForLoadState('networkidle');
  });

  test('should prevent empty job name submission', async ({ page }) => {
    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Leave name empty, fill other required fields
    await page.getByRole('button', { name: /command/i }).click();
    await page.locator('textarea').fill('echo test');

    // Try to submit
    await page.getByRole('button', { name: /create and run|criar e executar/i }).click();

    // Modal should still be visible (validation failed due to HTML5 required)
    await expect(page.locator('.fixed.inset-0 h2')).toBeVisible();
  });

  test('should prevent invalid disk size', async ({ page }) => {
    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Try to set disk size below minimum
    const diskInput = page.locator('input[type="number"]').first();
    await diskInput.fill('5'); // Below minimum of 10

    // Check if input has validation
    const minValue = await diskInput.getAttribute('min');
    expect(parseInt(minValue)).toBeGreaterThanOrEqual(10);
  });

  test('should prevent invalid timeout', async ({ page }) => {
    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Check timeout input constraints
    const timeoutInput = page.locator('input[type="number"]').nth(1);
    const minTimeout = await timeoutInput.getAttribute('min');
    const maxTimeout = await timeoutInput.getAttribute('max');

    expect(parseInt(minTimeout)).toBeGreaterThanOrEqual(10);
    expect(parseInt(maxTimeout)).toBeLessThanOrEqual(1440);
  });

  test('should require HuggingFace repo when source is huggingface', async ({ page }) => {
    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Fill name
    const nameInput = page.locator('.fixed.inset-0 input[type="text"]').first();
    await nameInput.fill('Test Job');

    // Select HuggingFace but don't fill repo
    await page.getByRole('button', { name: /hugging face/i }).click();

    // Try to submit
    await page.getByRole('button', { name: /create and run|criar e executar/i }).click();

    // Modal should still be visible (validation failed)
    await expect(page.locator('.fixed.inset-0 h2')).toBeVisible();
  });

  test('should require Git URL when source is git', async ({ page }) => {
    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Fill name
    const nameInput = page.locator('.fixed.inset-0 input[type="text"]').first();
    await nameInput.fill('Test Job');

    // Select Git but don't fill URL
    await page.getByRole('button', { name: /git/i }).click();

    // Try to submit
    await page.getByRole('button', { name: /create and run|criar e executar/i }).click();

    // Modal should still be visible (validation failed)
    await expect(page.locator('.fixed.inset-0 h2')).toBeVisible();
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Intercept API calls and return error
    await page.route('**/api/v1/jobs', async route => {
      await route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Internal Server Error' })
      });
    });

    await page.getByRole('button', { name: /new job|novo job/i }).click();
    await page.waitForTimeout(500);

    // Fill valid form
    const nameInput = page.locator('.fixed.inset-0 input[type="text"]').first();
    await nameInput.fill('Test Job');
    await page.getByRole('button', { name: /command/i }).click();
    await page.locator('textarea').fill('echo test');

    // Try to submit
    await page.getByRole('button', { name: /create and run|criar e executar/i }).click();

    // Wait for error response
    await page.waitForTimeout(1000);

    // Either shows alert or stays in modal - both are acceptable error handling
    const hasModal = await page.locator('.fixed.inset-0').isVisible();
    expect(hasModal).toBe(true); // Should still be in modal after error
  });
});

test.describe('Jobs UI/UX', () => {
  test('should be responsive', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/app/jobs');
    await page.waitForLoadState('networkidle');

    // Page should still be usable - check for exact title
    await expect(page.getByRole('heading', { name: 'Jobs', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: /new job|novo job/i })).toBeVisible();
  });

  test('should show loading state', async ({ page }) => {
    // Slow down network
    await page.route('**/api/v1/jobs', async route => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.continue();
    });

    await page.goto('/app/jobs');

    // Should show loading indicator or spinner
    const loadingText = page.getByText(/loading|carregando/i);
    const spinner = page.locator('.animate-spin');

    // Either loading text or spinner should be visible
    const hasLoading = await loadingText.isVisible().catch(() => false);
    const hasSpinner = await spinner.isVisible().catch(() => false);
    expect(hasLoading || hasSpinner).toBe(true);
  });

  test('should show empty state when no jobs', async ({ page }) => {
    // Mock empty jobs response - intercept before navigation
    await page.route('**/api/v1/jobs**', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ jobs: [], total: 0 })
        });
      } else {
        await route.continue();
      }
    });

    await page.goto('/app/jobs');
    // Don't use networkidle - it can timeout. Just wait for DOM to load
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Should show empty state - look for the specific empty state text or icon
    const emptyText = page.getByText(/no jobs created|nenhum job criado/i);
    const emptyIcon = page.locator('.border-dashed');

    const hasEmptyText = await emptyText.isVisible().catch(() => false);
    const hasEmptyIcon = await emptyIcon.isVisible().catch(() => false);

    expect(hasEmptyText || hasEmptyIcon).toBe(true);
  });
});
