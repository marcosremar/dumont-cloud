/**
 * Deploy Model Interface E2E Tests
 * Tests model catalog, wizard flow, search, HuggingFace import, and deploy
 */
const { test, expect } = require('@playwright/test');

// Sample models from the comprehensive catalog
const SAMPLE_LLM_MODELS = [
  { id: 'meta-llama/Llama-4-Scout-17B-16E-Instruct', name: 'Llama 4 Scout 17B' },
  { id: 'meta-llama/Llama-3.2-3B-Instruct', name: 'Llama 3.2 3B Instruct' },
  { id: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B', name: 'DeepSeek R1 Distill 1.5B' },
  { id: 'Qwen/Qwen2.5-7B-Instruct', name: 'Qwen 2.5 7B Instruct' },
  { id: 'mistralai/Mistral-7B-Instruct-v0.3', name: 'Mistral 7B Instruct v0.3' },
  { id: 'google/gemma-2-9b-it', name: 'Gemma 2 9B IT' },
  { id: 'microsoft/Phi-4-mini-instruct', name: 'Phi 4 Mini' },
];

const SAMPLE_IMAGE_MODELS = [
  { id: 'black-forest-labs/FLUX.1-schnell', name: 'FLUX.1 Schnell' },
  { id: 'stabilityai/stable-diffusion-3.5-large', name: 'SD 3.5 Large' },
];

const SAMPLE_SPEECH_MODELS = [
  { id: 'openai/whisper-large-v3', name: 'Whisper Large V3' },
  { id: 'openai/whisper-large-v3-turbo', name: 'Whisper Large V3 Turbo' },
];

const SAMPLE_EMBEDDING_MODELS = [
  { id: 'BAAI/bge-large-en-v1.5', name: 'BGE Large EN v1.5' },
  { id: 'BAAI/bge-m3', name: 'BGE M3 (Multilingual)' },
];

// GPU options
const GPU_OPTIONS = [
  'RTX 3080 (10GB)',
  'RTX 3090 (24GB)',
  'RTX 4080 (16GB)',
  'RTX 4090 (24GB)',
  'A100 (40/80GB)',
  'H100 (80GB)',
];

// Runtime options
const RUNTIME_OPTIONS = {
  llm: ['vLLM', 'Ollama', 'Text Generation Inference (TGI)', 'SGLang'],
  speech: ['Faster Whisper', 'OpenAI Whisper'],
  image: ['Diffusers', 'ComfyUI', 'Automatic1111'],
  embeddings: ['Sentence Transformers', 'Text Embeddings Inference (TEI)'],
};

test.describe('Deploy Model Page Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/app/models');
    await page.waitForLoadState('domcontentloaded');
    // Wait for the page title to appear
    await page.waitForSelector('h1:has-text("Models")', { timeout: 10000 });
  });

  test('should display deploy model page header', async ({ page }) => {
    await expect(page.locator('h1:has-text("Models")')).toBeVisible();
    await expect(page.locator('button:has-text("Deploy Model")')).toBeVisible();
  });

  test('should show HuggingFace import section', async ({ page }) => {
    await expect(page.locator('text=Deploy from HuggingFace')).toBeVisible();
    await expect(page.locator('input[placeholder*="huggingface.co"]')).toBeVisible();
  });

  test('should display tabs for Popular Models and My Deploys', async ({ page }) => {
    await expect(page.locator('button:has-text("Modelos Populares")')).toBeVisible();
    await expect(page.locator('button:has-text("Meus Deploys")')).toBeVisible();
  });

  test('should display LLM models on popular tab', async ({ page }) => {
    // LLM section should be visible
    await expect(page.locator('text=LLMs (Chat/Completion)')).toBeVisible();
    await expect(page.locator('text=vLLM Runtime')).toBeVisible();

    // At least some featured models should be visible
    await expect(page.locator('button:has-text("Llama 4 Scout 17B")')).toBeVisible();
    await expect(page.locator('button:has-text("Llama 3.2 3B Instruct")')).toBeVisible();
  });

  test('should display Image models section', async ({ page }) => {
    await expect(page.locator('text=Image Generation')).toBeVisible();
    await expect(page.locator('text=Diffusers Runtime')).toBeVisible();
    await expect(page.locator('button:has-text("FLUX.1 Schnell")')).toBeVisible();
  });

  test('should display Speech models section', async ({ page }) => {
    await expect(page.locator('text=Speech Recognition')).toBeVisible();
    await expect(page.locator('text=Faster-Whisper')).toBeVisible();
    await expect(page.locator('button:has-text("Whisper Large V3")').first()).toBeVisible();
  });

  test('should display Embeddings models section', async ({ page }) => {
    await expect(page.locator('text=Embeddings')).toBeVisible();
    await expect(page.locator('text=Sentence-Transformers')).toBeVisible();
    await expect(page.locator('button:has-text("BGE Large EN")').first()).toBeVisible();
  });
});

test.describe('Deploy Wizard Modal Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/app/models');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('h1:has-text("Models")', { timeout: 10000 });
  });

  test('should open deploy wizard modal', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.waitForTimeout(500);

    await expect(page.locator('h2:has-text("Deploy Model")')).toBeVisible();
    await expect(page.locator('text=Step 1 of 4')).toBeVisible();
  });

  test('should display all model types in Step 1', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.waitForTimeout(500);

    // Verify model types are visible
    await expect(page.locator('text=LLM (Chat/Completion)')).toBeVisible();
    await expect(page.locator('text=Speech-to-Text (Whisper)')).toBeVisible();
    await expect(page.locator('text=Image Generation (Diffusion)')).toBeVisible();
    await expect(page.locator('text=Text Embeddings')).toBeVisible();
  });

  test('should navigate through all 4 wizard steps', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.waitForTimeout(500);

    // Step 1: Select LLM type
    await expect(page.locator('text=Step 1 of 4')).toBeVisible();
    await page.click('button:has-text("LLM (Chat/Completion)")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Step 2: Select model
    await expect(page.locator('text=Step 2 of 4')).toBeVisible();
    await expect(page.locator('text=Choose model')).toBeVisible();
    // Select first featured model
    await page.click('button:has-text("Llama 4 Scout 17B")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Step 3: GPU Configuration
    await expect(page.locator('text=Step 3 of 4')).toBeVisible();
    await expect(page.locator('text=GPU Configuration')).toBeVisible();
    await expect(page.locator('text=Runtime')).toBeVisible();
    await expect(page.locator('text=vLLM')).toBeVisible();
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Step 4: Access Configuration
    await expect(page.locator('text=Step 4 of 4')).toBeVisible();
    await expect(page.locator('text=Access Configuration')).toBeVisible();
    await expect(page.locator('text=Deploy Summary')).toBeVisible();
    await expect(page.locator('button:has-text("Deploy")')).toBeVisible();
  });

  test('should show search functionality in Step 2', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.click('button:has-text("LLM (Chat/Completion)")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Verify search input exists
    const searchInput = page.locator('input[placeholder*="Buscar modelo"]');
    await expect(searchInput).toBeVisible();

    // Type search query
    await searchInput.fill('deepseek');
    await page.waitForTimeout(300);

    // Should filter to DeepSeek models
    await expect(page.locator('button:has-text("DeepSeek V3")')).toBeVisible();
    await expect(page.locator('button:has-text("DeepSeek R1")')).toBeVisible();
  });

  test('should show all models when clicking Ver Todos', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.click('button:has-text("LLM (Chat/Completion)")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Click show all models button
    await page.click('button:has-text("Ver Todos os Modelos")');
    await page.waitForTimeout(300);

    // Should show non-featured models too (like TinyLlama)
    await expect(page.locator('button:has-text("TinyLlama 1.1B")')).toBeVisible();
  });

  test('should support HuggingFace URL import in wizard', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.click('button:has-text("LLM (Chat/Completion)")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Find HuggingFace input in wizard
    const hfInput = page.locator('input[placeholder*="huggingface.co/org/model"]');
    await expect(hfInput).toBeVisible();

    // Enter HuggingFace URL
    await hfInput.fill('meta-llama/Llama-3.2-1B-Instruct');
    await page.waitForTimeout(300);

    // Next button should be enabled
    await expect(page.locator('button:has-text("Next")')).toBeEnabled();
  });

  test('should display runtime options for LLM', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.click('button:has-text("LLM (Chat/Completion)")');
    await page.click('button:has-text("Next")');

    // Select a model
    await page.click('button:has-text("Llama 3.2 3B Instruct")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Verify runtime options
    await expect(page.locator('text=Runtime')).toBeVisible();
    await expect(page.locator('button:has-text("vLLM")')).toBeVisible();
    await expect(page.locator('button:has-text("Ollama")')).toBeVisible();
    await expect(page.locator('button:has-text("Text Generation Inference")')).toBeVisible();
    await expect(page.locator('button:has-text("SGLang")')).toBeVisible();
  });

  test('should display GPU options in Step 3', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.click('button:has-text("LLM (Chat/Completion)")');
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("Llama 3.2 3B Instruct")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Verify GPU dropdown
    await expect(page.locator('text=GPU Type')).toBeVisible();
    const gpuSelect = page.locator('select').first();
    await expect(gpuSelect).toBeVisible();

    // Check GPU options
    await expect(page.locator('option:has-text("RTX 4090")')).toBeVisible();
    await expect(page.locator('option:has-text("A100")')).toBeVisible();
    await expect(page.locator('option:has-text("H100")')).toBeVisible();
  });

  test('should display access type options in Step 4', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.click('button:has-text("LLM (Chat/Completion)")');
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("Llama 3.2 1B Instruct")');
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Verify access type options
    await expect(page.locator('text=Access Type')).toBeVisible();
    await expect(page.locator('button:has-text("Private")')).toBeVisible();
    await expect(page.locator('button:has-text("Public")')).toBeVisible();
  });

  test('should show deploy summary in Step 4', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.click('button:has-text("LLM (Chat/Completion)")');
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("Llama 3.2 1B Instruct")');
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Verify summary shows correct information
    await expect(page.locator('text=Deploy Summary')).toBeVisible();
    await expect(page.locator('text=Type:')).toBeVisible();
    await expect(page.locator('text=LLM')).toBeVisible();
    await expect(page.locator('text=Model:')).toBeVisible();
    await expect(page.locator('text=Llama-3.2-1B-Instruct')).toBeVisible();
    await expect(page.locator('text=GPU:')).toBeVisible();
  });

  test('should go back through wizard steps', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.click('button:has-text("LLM (Chat/Completion)")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // On Step 2
    await expect(page.locator('text=Step 2 of 4')).toBeVisible();

    // Go back to Step 1
    await page.click('button:has-text("Back")');
    await page.waitForTimeout(500);
    await expect(page.locator('text=Step 1 of 4')).toBeVisible();
  });

  test('should close wizard with cancel button', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.waitForTimeout(500);
    await expect(page.locator('h2:has-text("Deploy Model")')).toBeVisible();

    // Click cancel
    await page.click('button:has-text("Cancel")');
    await page.waitForTimeout(500);

    // Modal should be closed
    await expect(page.locator('h2:has-text("Deploy Model")')).not.toBeVisible();
  });

  test('should close wizard with X button', async ({ page }) => {
    await page.click('button:has-text("Deploy Model")');
    await page.waitForTimeout(500);
    await expect(page.locator('h2:has-text("Deploy Model")')).toBeVisible();

    // Click X button (close icon in header)
    const closeButton = page.locator('button').filter({ has: page.locator('svg[class*="XCircle"]') }).first();
    if (await closeButton.isVisible()) {
      await closeButton.click();
    } else {
      // Try clicking by position relative to the modal header
      await page.locator('button:near(:text("Deploy Model"))').last().click();
    }
    await page.waitForTimeout(500);

    // Modal should be closed
    await expect(page.locator('h2:has-text("Deploy Model")')).not.toBeVisible();
  });
});

test.describe('Quick Deploy from Popular Models', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/app/models');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('h1:has-text("Models")', { timeout: 10000 });
  });

  test('should open wizard at Step 3 when clicking popular LLM model', async ({ page }) => {
    // Click a popular model card
    await page.click('button:has-text("Llama 3.2 3B Instruct")');
    await page.waitForTimeout(500);

    // Should skip to Step 3 with model pre-selected
    await expect(page.locator('text=Step 3 of 4')).toBeVisible();
    await expect(page.locator('text=GPU Configuration')).toBeVisible();
  });

  test('should open wizard at Step 3 when clicking popular Image model', async ({ page }) => {
    await page.click('button:has-text("FLUX.1 Schnell")');
    await page.waitForTimeout(500);

    await expect(page.locator('text=Step 3 of 4')).toBeVisible();
    await expect(page.locator('text=GPU Configuration')).toBeVisible();
  });

  test('should open wizard at Step 3 when clicking popular Speech model', async ({ page }) => {
    await page.click('button:has-text("Whisper Large V3")');
    await page.waitForTimeout(500);

    await expect(page.locator('text=Step 3 of 4')).toBeVisible();
  });

  test('should open wizard at Step 3 when clicking popular Embedding model', async ({ page }) => {
    await page.click('button:has-text("BGE Large EN v1.5")');
    await page.waitForTimeout(500);

    await expect(page.locator('text=Step 3 of 4')).toBeVisible();
  });
});

test.describe('HuggingFace Import Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/app/models');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('h1:has-text("Models")', { timeout: 10000 });
  });

  test('should detect LLM model type from HuggingFace URL', async ({ page }) => {
    const hfInput = page.locator('input[placeholder*="huggingface.co/meta-llama"]');
    await hfInput.fill('https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct');
    await page.waitForTimeout(500);

    // Should show detected type
    await expect(page.locator('text=LLM')).toBeVisible();
    await expect(page.locator('button:has-text("Deploy")').first()).toBeEnabled();
  });

  test('should detect Image model type from HuggingFace URL', async ({ page }) => {
    const hfInput = page.locator('input[placeholder*="huggingface.co/meta-llama"]');
    await hfInput.fill('https://huggingface.co/black-forest-labs/FLUX.1-schnell');
    await page.waitForTimeout(500);

    // Should show detected type as image
    await expect(page.locator('text=IMAGE').or(page.locator('text=image'))).toBeVisible();
  });

  test('should detect Embedding model type from HuggingFace URL', async ({ page }) => {
    const hfInput = page.locator('input[placeholder*="huggingface.co/meta-llama"]');
    await hfInput.fill('https://huggingface.co/BAAI/bge-large-en-v1.5');
    await page.waitForTimeout(500);

    // Should show detected type as embeddings
    await expect(page.locator('text=EMBEDDINGS').or(page.locator('text=embeddings'))).toBeVisible();
  });

  test('should detect Speech model type from HuggingFace URL', async ({ page }) => {
    const hfInput = page.locator('input[placeholder*="huggingface.co/meta-llama"]');
    await hfInput.fill('https://huggingface.co/openai/whisper-large-v3');
    await page.waitForTimeout(500);

    // Should show detected type as speech
    await expect(page.locator('text=SPEECH').or(page.locator('text=speech'))).toBeVisible();
  });

  test('should enable deploy button with valid HuggingFace URL', async ({ page }) => {
    const hfInput = page.locator('input[placeholder*="huggingface.co/meta-llama"]');
    const deployBtn = page.locator('button:has-text("Deploy")').first();

    // Initially disabled
    await expect(deployBtn).toBeDisabled();

    // Enter valid URL
    await hfInput.fill('meta-llama/Llama-3.2-1B-Instruct');
    await page.waitForTimeout(500);

    // Should be enabled
    await expect(deployBtn).toBeEnabled();
  });
});

test.describe('Model Search Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/app/models');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('h1:has-text("Models")', { timeout: 10000 });
    await page.click('button:has-text("Deploy Model")');
    await page.waitForTimeout(500);
    await page.click('button:has-text("LLM (Chat/Completion)")');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);
  });

  test('should filter models by search query', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Buscar modelo"]');
    await searchInput.fill('qwen');
    await page.waitForTimeout(300);

    // Should show Qwen models
    await expect(page.locator('button:has-text("Qwen 3 235B")')).toBeVisible();
    await expect(page.locator('button:has-text("Qwen 2.5 7B")')).toBeVisible();

    // Should not show non-Qwen models
    await expect(page.locator('button:has-text("Llama 4 Scout")')).not.toBeVisible();
  });

  test('should filter models by partial name', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Buscar modelo"]');
    await searchInput.fill('mistral');
    await page.waitForTimeout(300);

    await expect(page.locator('button:has-text("Mistral 7B")')).toBeVisible();
    await expect(page.locator('button:has-text("Mixtral")')).toBeVisible();
  });

  test('should filter models by size', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Buscar modelo"]');
    await searchInput.fill('70B');
    await page.waitForTimeout(300);

    await expect(page.locator('button:has-text("Llama 3.3 70B")')).toBeVisible();
    await expect(page.locator('button:has-text("Llama 3.1 70B")')).toBeVisible();
  });

  test('should show no results message when no matches', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Buscar modelo"]');
    await searchInput.fill('nonexistentmodel12345');
    await page.waitForTimeout(300);

    await expect(page.locator('text=Nenhum modelo encontrado')).toBeVisible();
  });

  test('should clear search and show all models', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Buscar modelo"]');

    // Search for something
    await searchInput.fill('deepseek');
    await page.waitForTimeout(300);

    // Clear search
    await searchInput.clear();
    await page.waitForTimeout(300);

    // Should show featured models again
    await expect(page.locator('button:has-text("Llama 4 Scout")')).toBeVisible();
  });
});

test.describe('Demo Mode Deploy Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to demo mode
    await page.goto('/demo-app/models');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('h1:has-text("Models")', { timeout: 10000 });
  });

  test('should complete deploy in demo mode', async ({ page }) => {
    // Click popular model to open wizard
    await page.click('button:has-text("Llama 3.2 3B Instruct")');
    await page.waitForTimeout(500);

    // Step 3: GPU Config
    await expect(page.locator('text=Step 3 of 4')).toBeVisible();
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(500);

    // Step 4: Access Config
    await expect(page.locator('text=Step 4 of 4')).toBeVisible();
    await page.click('button:has-text("Deploy")');
    await page.waitForTimeout(1000);

    // Should close wizard and show deploying model
    await expect(page.locator('h2:has-text("Deploy Model")')).not.toBeVisible();

    // Switch to My Deploys tab
    await page.click('button:has-text("Meus Deploys")');
    await page.waitForTimeout(500);

    // Should show the new model card
    await expect(page.locator('text=Llama-3.2-3B-Instruct').or(page.locator('text=Llama 3.2 3B'))).toBeVisible();
  });
});
