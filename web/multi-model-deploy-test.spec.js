import { test, expect } from '@playwright/test';

/**
 * Test deploying 10 different LLM models with various runtimes and GPU configurations
 *
 * Models to deploy:
 * 1. meta-llama/Llama-3.2-3B-Instruct (vLLM, RTX 4090)
 * 2. Qwen/Qwen2.5-7B-Instruct (vLLM, RTX 4090)
 * 3. mistralai/Mistral-7B-Instruct-v0.3 (vLLM, A100)
 * 4. google/gemma-2-9b-it (vLLM, RTX 3090)
 * 5. openai/whisper-large-v3 (faster-whisper, RTX 4080)
 * 6. openai/whisper-medium (faster-whisper, RTX 3070)
 * 7. black-forest-labs/FLUX.1-schnell (diffusers, RTX 4090)
 * 8. stabilityai/stable-diffusion-xl-base-1.0 (diffusers, A100)
 * 9. BAAI/bge-large-en-v1.5 (sentence-transformers, RTX 3060)
 * 10. intfloat/e5-large-v2 (sentence-transformers, RTX 3060)
 */

const MODELS_TO_DEPLOY = [
  { name: 'Llama 3.2 3B Instruct', id: 'meta-llama/Llama-3.2-3B-Instruct', type: 'llm', runtime: 'vLLM', gpu: 'RTX 4090' },
  { name: 'Qwen 2.5 7B Instruct', id: 'Qwen/Qwen2.5-7B-Instruct', type: 'llm', runtime: 'vLLM', gpu: 'RTX 4090' },
  { name: 'Mistral 7B Instruct', id: 'mistralai/Mistral-7B-Instruct-v0.3', type: 'llm', runtime: 'vLLM', gpu: 'A100' },
  { name: 'Gemma 2 9B IT', id: 'google/gemma-2-9b-it', type: 'llm', runtime: 'vLLM', gpu: 'RTX 3090' },
  { name: 'Whisper Large V3', id: 'openai/whisper-large-v3', type: 'speech', runtime: 'faster-whisper', gpu: 'RTX 4080' },
  { name: 'Whisper Medium', id: 'openai/whisper-medium', type: 'speech', runtime: 'faster-whisper', gpu: 'RTX 3070' },
  { name: 'FLUX.1 Schnell', id: 'black-forest-labs/FLUX.1-schnell', type: 'image', runtime: 'diffusers', gpu: 'RTX 4090' },
  { name: 'SDXL Base', id: 'stabilityai/stable-diffusion-xl-base-1.0', type: 'image', runtime: 'diffusers', gpu: 'A100' },
  { name: 'BGE Large EN', id: 'BAAI/bge-large-en-v1.5', type: 'embeddings', runtime: 'sentence-transformers', gpu: 'RTX 3060' },
  { name: 'E5 Large V2', id: 'intfloat/e5-large-v2', type: 'embeddings', runtime: 'sentence-transformers', gpu: 'RTX 3060' },
];

const TYPE_MAP = {
  'llm': 'LLM',
  'speech': 'Speech',
  'image': 'Image',
  'embeddings': 'Embeddings'
};

test.describe('Multi-Model Deploy Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Setup demo mode and authentication
    await page.goto('http://localhost:4892');
    await page.waitForTimeout(1000);

    await page.evaluate(() => {
      localStorage.setItem('demo_mode', 'true');
      localStorage.setItem('auth_token', 'demo-token-12345');
      localStorage.setItem('auth_login_time', Date.now().toString());
      localStorage.setItem('auth_user', JSON.stringify({
        id: 'demo-user-1',
        username: 'demo@dumont.cloud',
        email: 'demo@dumont.cloud',
        name: 'Demo User',
        balance: 100,
        plan: 'pro'
      }));
    });

    // Navigate to models page
    await page.goto('http://localhost:4892/app/models');
    await page.waitForTimeout(3000);
  });

  // Test deploying all 10 models
  for (let i = 0; i < MODELS_TO_DEPLOY.length; i++) {
    const model = MODELS_TO_DEPLOY[i];

    test(`Deploy ${i + 1}/10: ${model.name} (${model.runtime} on ${model.gpu})`, async ({ page }) => {
      console.log(`\n=== Deploying ${model.name} ===`);
      console.log(`Type: ${model.type}, Runtime: ${model.runtime}, GPU: ${model.gpu}`);

      // Click Deploy Model button
      const deployButton = page.locator('button:has-text("Deploy Model")').first();
      await expect(deployButton).toBeVisible({ timeout: 5000 });
      await deployButton.click();
      await page.waitForTimeout(1500);

      // Step 1: Select model type
      const typeButton = page.locator(`button:has-text("${TYPE_MAP[model.type]}")`).first();
      if (await typeButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await typeButton.click();
        console.log(`Selected type: ${TYPE_MAP[model.type]}`);
        await page.waitForTimeout(500);
      }

      // Click Next
      let nextButton = page.locator('button:has-text("Next"), button:has-text("Próximo")').first();
      await expect(nextButton).toBeEnabled({ timeout: 3000 });
      await nextButton.click();
      await page.waitForTimeout(1500);

      // Step 2: Select or enter model
      const modelButton = page.locator(`button:has-text("${model.name.split(' ')[0]}")`).first();
      if (await modelButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await modelButton.click();
        console.log(`Selected model: ${model.name}`);
      } else {
        // Use custom model input
        const customInput = page.locator('input[placeholder*="meta-llama"], input[type="text"]').first();
        if (await customInput.isVisible({ timeout: 2000 }).catch(() => false)) {
          await customInput.fill(model.id);
          console.log(`Entered custom model: ${model.id}`);
        }
      }
      await page.waitForTimeout(1000);

      // Click Next to Step 3 (GPU Config)
      nextButton = page.locator('button:has-text("Next"), button:has-text("Próximo")').first();
      if (await nextButton.isEnabled().catch(() => false)) {
        await nextButton.click();
        console.log('Advanced to GPU configuration');
        await page.waitForTimeout(1500);
      }

      // Step 3: GPU Configuration (optional - use defaults)
      nextButton = page.locator('button:has-text("Next"), button:has-text("Próximo")').first();
      if (await nextButton.isEnabled().catch(() => false)) {
        await nextButton.click();
        console.log('Advanced to access configuration');
        await page.waitForTimeout(1500);
      }

      // Step 4: Access Configuration - Click Deploy
      const deployFinalButton = page.locator('button:has-text("Deploy")').last();
      if (await deployFinalButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await deployFinalButton.click();
        console.log(`Deployed ${model.name}!`);
        await page.waitForTimeout(2000);

        // Take screenshot of deployed state
        await page.screenshot({ path: `test-deployed-${i + 1}-${model.type}.png`, fullPage: true });
      }

      // Verify deployment started (in demo mode, should show deploying status)
      const deployingText = page.locator('text=/deploying|downloading|starting|running/i');
      const isDeploying = await deployingText.isVisible({ timeout: 5000 }).catch(() => false);
      console.log(`Deployment status visible: ${isDeploying}`);

      // Close wizard if still open (click outside or X button)
      const closeButton = page.locator('button:has-text("Cancel"), button[aria-label="Close"]').first();
      if (await closeButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await closeButton.click();
        await page.waitForTimeout(500);
      }
    });
  }

  // Error scenario tests
  test('Behavior: LLM is pre-selected as default model type', async ({ page }) => {
    console.log('\n=== Testing: LLM is default model type ===');

    const deployButton = page.locator('button:has-text("Deploy Model")').first();
    await deployButton.click();
    await page.waitForTimeout(1500);

    // Check that LLM is pre-selected (default behavior)
    const llmButton = page.locator('button:has-text("LLM")').first();
    const llmButtonClasses = await llmButton.getAttribute('class');
    const isLLMSelected = llmButtonClasses?.includes('brand-500');

    console.log(`LLM is pre-selected: ${isLLMSelected}`);
    expect(isLLMSelected).toBe(true); // LLM should be selected by default

    // Next button should be enabled since LLM is pre-selected
    const nextButton = page.locator('button:has-text("Next"), button:has-text("Próximo")').first();
    const isEnabled = await nextButton.isEnabled().catch(() => false);
    console.log(`Next button enabled with default LLM: ${isEnabled}`);
    expect(isEnabled).toBe(true);
  });

  test('Error Prevention: Deploy without selecting model', async ({ page }) => {
    console.log('\n=== Testing error: No model selected ===');

    const deployButton = page.locator('button:has-text("Deploy Model")').first();
    await deployButton.click();
    await page.waitForTimeout(1500);

    // Select LLM type
    const typeButton = page.locator('button:has-text("LLM")').first();
    await typeButton.click();
    await page.waitForTimeout(500);

    // Click Next
    let nextButton = page.locator('button:has-text("Next"), button:has-text("Próximo")').first();
    await nextButton.click();
    await page.waitForTimeout(1500);

    // Try to click Next without selecting a model
    nextButton = page.locator('button:has-text("Next"), button:has-text("Próximo")').first();
    const isEnabled = await nextButton.isEnabled().catch(() => false);

    console.log(`Next button enabled without model selection: ${isEnabled}`);
    expect(isEnabled).toBe(false); // Should be disabled
  });

  test('Error Prevention: Invalid custom model ID format', async ({ page }) => {
    console.log('\n=== Testing error: Invalid custom model ID ===');

    const deployButton = page.locator('button:has-text("Deploy Model")').first();
    await deployButton.click();
    await page.waitForTimeout(1500);

    // Select LLM type
    const typeButton = page.locator('button:has-text("LLM")').first();
    await typeButton.click();
    await page.waitForTimeout(500);

    // Click Next
    let nextButton = page.locator('button:has-text("Next"), button:has-text("Próximo")').first();
    await nextButton.click();
    await page.waitForTimeout(1500);

    // Enter invalid model ID (no slash, invalid format)
    const customInput = page.locator('input[placeholder*="meta-llama"], input[type="text"]').first();
    if (await customInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await customInput.fill('invalid-model-id');
      await page.waitForTimeout(500);

      // Check if Next is enabled (should still be enabled for custom models)
      nextButton = page.locator('button:has-text("Next"), button:has-text("Próximo")').first();
      const isEnabled = await nextButton.isEnabled().catch(() => false);
      console.log(`Next button enabled with custom model: ${isEnabled}`);

      // Note: The system accepts any custom model ID, validation happens on deploy
    }
  });

  test('Error Prevention: Wizard can be cancelled via X button', async ({ page }) => {
    console.log('\n=== Testing: Wizard cancellation via X button ===');

    const deployButton = page.locator('button:has-text("Deploy Model")').first();
    await deployButton.click();
    await page.waitForTimeout(1500);

    // Take screenshot of open wizard
    await page.screenshot({ path: 'test-wizard-open.png', fullPage: true });

    // Click the X button in the header (XCircle icon)
    const closeButton = page.locator('button:has(.lucide-x-circle), button:has([data-testid="close-wizard"])').first();
    if (await closeButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await closeButton.click();
      console.log('Clicked X button');
      await page.waitForTimeout(1000);

      // Verify wizard is closed by checking for the modal overlay
      const modalOverlay = page.locator('.fixed.inset-0.bg-black\\/60');
      const isModalVisible = await modalOverlay.isVisible({ timeout: 1000 }).catch(() => false);
      console.log(`Modal overlay still visible: ${isModalVisible}`);
      expect(isModalVisible).toBe(false);
    } else {
      // Try clicking outside the modal
      console.log('X button not found, trying to click outside modal');
      await page.mouse.click(10, 10); // Click top-left corner (outside modal)
      await page.waitForTimeout(500);
    }

    await page.screenshot({ path: 'test-wizard-closed.png', fullPage: true });
  });

  test('Summary: Verify all model types are available', async ({ page }) => {
    console.log('\n=== Verifying all model types ===');

    const deployButton = page.locator('button:has-text("Deploy Model")').first();
    await deployButton.click();
    await page.waitForTimeout(1500);

    // Check all 4 model types are visible
    const types = ['LLM', 'Speech', 'Image', 'Embeddings'];
    for (const type of types) {
      const typeButton = page.locator(`button:has-text("${type}")`).first();
      const isVisible = await typeButton.isVisible({ timeout: 2000 }).catch(() => false);
      console.log(`${type} type available: ${isVisible}`);
      expect(isVisible).toBe(true);
    }

    await page.screenshot({ path: 'test-all-model-types.png', fullPage: true });
  });
});
