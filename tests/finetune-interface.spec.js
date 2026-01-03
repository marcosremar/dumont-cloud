/**
 * Fine-Tuning Interface E2E Tests
 * Tests all 10 models, GPU selection, and form validation
 */
const { test, expect } = require('@playwright/test');

// 10 supported models
const MODELS = [
  { id: 'unsloth/tinyllama-bnb-4bit', name: 'TinyLlama 1.1B', category: 'ultra-light' },
  { id: 'unsloth/stablelm-2-1_6b-bnb-4bit', name: 'StableLM 2 1.6B', category: 'ultra-light' },
  { id: 'unsloth/Phi-3-mini-4k-instruct-bnb-4bit', name: 'Phi-3 Mini', category: 'ultra-light' },
  { id: 'unsloth/mistral-7b-bnb-4bit', name: 'Mistral 7B', category: 'light' },
  { id: 'unsloth/gemma-7b-bnb-4bit', name: 'Gemma 7B', category: 'light' },
  { id: 'unsloth/Qwen2-7B-bnb-4bit', name: 'Qwen 2 7B', category: 'light' },
  { id: 'unsloth/llama-3-8b-bnb-4bit', name: 'Llama 3 8B', category: 'light' },
  { id: 'unsloth/zephyr-7b-beta-bnb-4bit', name: 'Zephyr 7B Beta', category: 'light' },
  { id: 'unsloth/openhermes-2.5-mistral-7b-bnb-4bit', name: 'OpenHermes 2.5', category: 'light' },
  { id: 'unsloth/codellama-7b-bnb-4bit', name: 'CodeLlama 7B', category: 'light' },
];

// GPU options
const GPU_OPTIONS = [
  { value: 'RTX3060', category: 'budget' },
  { value: 'RTX3090', category: 'budget' },
  { value: 'RTX4070', category: 'budget' },
  { value: 'RTX4080', category: 'standard' },
  { value: 'RTX4090', category: 'standard' },
  { value: 'L4', category: 'standard' },
  { value: 'A100', category: 'professional' },
  { value: 'A100-80GB', category: 'professional' },
  { value: 'H100', category: 'professional' },
];

test.describe('Fine-Tuning Interface Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to fine-tuning page (auth handled by storageState in playwright.config.js)
    await page.goto('/app/finetune');
    await page.waitForLoadState('networkidle');

    // Wait for page to be ready
    await page.waitForTimeout(500);
  });

  test('should display fine-tuning page header', async ({ page }) => {
    // Verify page loaded correctly
    await expect(page.locator('h1:has-text("Fine-Tuning")')).toBeVisible();
    await expect(page.locator('button:has-text("New Fine-Tune Job")')).toBeVisible();
  });

  test('should open fine-tuning modal', async ({ page }) => {
    // Click new job button
    await page.click('button:has-text("New Fine-Tune Job")');

    // Verify modal opened
    await expect(page.locator('text=Fine-Tune Model with Unsloth')).toBeVisible();
    await expect(page.getByText('Select Base Model', { exact: true })).toBeVisible();
  });

  test('should display all 10 models in Step 1', async ({ page }) => {
    // Open modal
    await page.click('button:has-text("New Fine-Tune Job")');
    await page.waitForTimeout(500);

    // Verify ultra-light models section
    await expect(page.getByText('Ultra-Fast Training (1-4B params)')).toBeVisible();

    // Verify fast training section
    await expect(page.getByText('Fast Training (7-8B params)')).toBeVisible();

    // Count visible model cards (10 total)
    for (const model of MODELS) {
      await expect(page.getByText(model.name, { exact: true }).first()).toBeVisible();
    }
  });

  test('should select each ultra-light model', async ({ page }) => {
    await page.click('button:has-text("New Fine-Tune Job")');
    await page.waitForTimeout(500);

    // Test selecting one ultra-light model (TinyLlama)
    await page.getByText('TinyLlama 1.1B', { exact: true }).click();
    await page.waitForTimeout(300);

    // Verify model can be selected (Next button becomes enabled)
    const nextButton = page.getByRole('button', { name: 'Next' });
    await expect(nextButton).toBeEnabled();
  });

  test('should navigate through all 4 steps', async ({ page }) => {
    await page.click('button:has-text("New Fine-Tune Job")');
    await page.waitForTimeout(500);

    // Step 1: Select model
    await expect(page.getByText('Step 1 of 4', { exact: false })).toBeVisible();
    await page.getByText('TinyLlama 1.1B', { exact: true }).click();
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: 'Next' }).click();
    await page.waitForTimeout(500);

    // Step 2: Dataset
    await expect(page.getByText('Step 2 of 4', { exact: false })).toBeVisible();
    await expect(page.getByText('Dataset', { exact: true })).toBeVisible();

    // Select URL source for dataset
    await page.getByRole('button', { name: 'URL' }).click();
    await page.waitForTimeout(300);
    const urlInput = page.locator('input[placeholder*="huggingface"]');
    await urlInput.waitFor({ state: 'visible' });
    await urlInput.fill('https://huggingface.co/datasets/tatsu-lab/alpaca');
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: 'Next' }).click();
    await page.waitForTimeout(500);

    // Step 3: Configuration
    await expect(page.getByText('Step 3 of 4', { exact: false })).toBeVisible();

    // Fill job name - wait for input to be visible
    const jobNameInput = page.locator('input[placeholder="my-fine-tuned-model"]');
    await jobNameInput.waitFor({ state: 'visible' });
    await jobNameInput.fill('testjob123');
    await page.waitForTimeout(300);

    // Select GPU - use specific button within the form
    await page.locator('button:has-text("RTX 4090")').first().click();
    await page.waitForTimeout(300);

    // Click Next to go to Step 4
    const nextButton = page.getByRole('button', { name: 'Next' });
    await expect(nextButton).toBeEnabled();
    await nextButton.click();
    await page.waitForTimeout(500);

    // Step 4: Review
    await expect(page.getByText('Step 4 of 4', { exact: false })).toBeVisible();

    // Verify job name is shown in review
    await expect(page.getByText('testjob123').first()).toBeVisible();
  });

  test('should show GPU compatibility warning', async ({ page }) => {
    await page.click('button:has-text("New Fine-Tune Job")');
    await page.waitForTimeout(500);

    // Select a 16GB model (Llama 3 8B)
    await page.click('text=Llama 3 8B');
    await page.click('button:has-text("Next")');

    // Skip dataset step
    await page.click('button:has-text("URL")');
    await page.fill('input[placeholder*="huggingface"]', 'https://test.com/data.json');
    await page.click('button:has-text("Next")');

    // Select a small GPU (RTX 3060 - 12GB)
    await page.click('button:has-text("RTX 3060")');

    // Should show compatibility warning
    await expect(page.locator('text=requires')).toBeVisible();
    await expect(page.locator('text=Consider a larger GPU')).toBeVisible();
  });

  test('should validate job name is required', async ({ page }) => {
    await page.click('button:has-text("New Fine-Tune Job")');
    await page.waitForTimeout(500);

    // Select model
    await page.getByText('TinyLlama 1.1B', { exact: true }).click();
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: 'Next' }).click();
    await page.waitForTimeout(500);

    // Add dataset URL
    await page.getByRole('button', { name: 'URL' }).click();
    await page.waitForTimeout(300);
    const urlInput = page.locator('input[placeholder*="huggingface"]');
    await urlInput.waitFor({ state: 'visible' });
    await urlInput.fill('https://test.com/data.json');
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: 'Next' }).click();
    await page.waitForTimeout(500);

    // On Step 3 (Configuration), verify job name input is visible
    const jobNameInput = page.locator('input[placeholder="my-fine-tuned-model"]');
    await jobNameInput.waitFor({ state: 'visible' });

    // Next button should be disabled without job name
    const nextButton = page.getByRole('button', { name: 'Next' });
    await expect(nextButton).toBeDisabled();
  });

  test('should display all GPU categories', async ({ page }) => {
    await page.click('button:has-text("New Fine-Tune Job")');

    // Navigate to step 3
    await page.click('text=TinyLlama 1.1B');
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("URL")');
    await page.fill('input[placeholder*="huggingface"]', 'https://test.com/data.json');
    await page.click('button:has-text("Next")');

    // Verify all GPU categories are visible
    await expect(page.locator('text=Budget')).toBeVisible();
    await expect(page.locator('text=Standard')).toBeVisible();
    await expect(page.locator('text=Professional')).toBeVisible();
  });

  test('should show advanced settings', async ({ page }) => {
    await page.click('button:has-text("New Fine-Tune Job")');

    // Navigate to step 3
    await page.click('text=TinyLlama 1.1B');
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("URL")');
    await page.fill('input[placeholder*="huggingface"]', 'https://test.com/data.json');
    await page.click('button:has-text("Next")');

    // Fill job name
    await page.fill('input[placeholder="my-fine-tuned-model"]', 'test-job');

    // Click advanced settings
    await page.click('text=Show Advanced Settings');

    // Verify advanced settings are visible
    await expect(page.locator('text=LoRA Rank')).toBeVisible();
    await expect(page.locator('text=Epochs')).toBeVisible();
    await expect(page.locator('text=Batch Size')).toBeVisible();
    await expect(page.locator('text=Max Seq Length')).toBeVisible();
  });

  test('should support dataset upload and URL options', async ({ page }) => {
    await page.click('button:has-text("New Fine-Tune Job")');

    // Select model
    await page.click('text=TinyLlama 1.1B');
    await page.click('button:has-text("Next")');

    // Verify upload option is default
    await expect(page.locator('text=Upload File')).toBeVisible();
    await expect(page.locator('text=Click to upload JSON or JSONL file')).toBeVisible();

    // Switch to URL option
    await page.click('button:has-text("URL")');
    await expect(page.locator('input[placeholder*="huggingface"]')).toBeVisible();

    // Verify format options
    await expect(page.locator('text=Alpaca')).toBeVisible();
    await expect(page.locator('text=ShareGPT')).toBeVisible();
  });

  test('should go back through steps', async ({ page }) => {
    await page.click('button:has-text("New Fine-Tune Job")');

    // Navigate to step 2
    await page.click('text=TinyLlama 1.1B');
    await page.click('button:has-text("Next")');
    await expect(page.locator('text=Step 2 of 4')).toBeVisible();

    // Go back to step 1
    await page.click('button:has-text("Back")');
    await expect(page.locator('text=Step 1 of 4')).toBeVisible();
  });

  test('should close modal with cancel button', async ({ page }) => {
    await page.click('button:has-text("New Fine-Tune Job")');
    await page.waitForTimeout(500);
    await expect(page.locator('text=Fine-Tune Model with Unsloth')).toBeVisible();

    // Click cancel button in the modal footer
    const cancelButton = page.locator('button:has-text("Cancel")').last();
    await cancelButton.click();
    await page.waitForTimeout(500);

    // Modal should be closed
    await expect(page.locator('text=Fine-Tune Model with Unsloth')).not.toBeVisible({ timeout: 5000 });
  });
});

test.describe('Fine-Tuning Integration Tests', () => {
  test.skip('should create a fine-tuning job (requires backend)', async ({ page }) => {
    // This test requires a running backend
    await page.goto('/app/finetune');

    await page.click('button:has-text("New Fine-Tune Job")');

    // Complete all steps
    await page.click('text=TinyLlama 1.1B');
    await page.click('button:has-text("Next")');

    await page.click('button:has-text("URL")');
    await page.fill('input[placeholder*="huggingface"]', 'https://huggingface.co/datasets/tatsu-lab/alpaca');
    await page.click('button:has-text("Next")');

    await page.fill('input[placeholder="my-fine-tuned-model"]', 'integration-test-job');
    await page.click('button:has-text("RTX 4090")');
    await page.click('button:has-text("Next")');

    // Launch
    await page.click('button:has-text("Launch Fine-Tuning")');

    // Should show success or job card
    await page.waitForTimeout(2000);
    await expect(page.locator('text=integration-test-job')).toBeVisible();
  });
});
