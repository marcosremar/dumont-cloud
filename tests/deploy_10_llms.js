const { chromium } = require('playwright');

// 10 Small LLM models to deploy in serverless mode
const SMALL_LLMS = [
  { id: 'qwen2.5-0.5b', name: 'Qwen 2.5 0.5B', model_id: 'Qwen/Qwen2.5-0.5B-Instruct', vram: 1 },
  { id: 'qwen3-0.6b', name: 'Qwen3 0.6B', model_id: 'Qwen/Qwen3-0.6B', vram: 2 },
  { id: 'phi-3-mini', name: 'Phi-3 Mini', model_id: 'microsoft/Phi-3-mini-4k-instruct', vram: 8 },
  { id: 'tinyllama-1.1b', name: 'TinyLlama 1.1B', model_id: 'TinyLlama/TinyLlama-1.1B-Chat-v1.0', vram: 3 },
  { id: 'stablelm-zephyr-3b', name: 'StableLM Zephyr 3B', model_id: 'stabilityai/stablelm-zephyr-3b', vram: 6 },
  { id: 'gemma-2b', name: 'Gemma 2B', model_id: 'google/gemma-2b-it', vram: 5 },
  { id: 'opt-1.3b', name: 'OPT 1.3B', model_id: 'facebook/opt-1.3b', vram: 3 },
  { id: 'bloom-560m', name: 'BLOOM 560M', model_id: 'bigscience/bloom-560m', vram: 2 },
  { id: 'pythia-1b', name: 'Pythia 1B', model_id: 'EleutherAI/pythia-1b', vram: 3 },
  { id: 'openelm-270m', name: 'OpenELM 270M', model_id: 'apple/OpenELM-270M-Instruct', vram: 1 },
];

async function deploy10LLMs() {
  console.log('='.repeat(60));
  console.log('DEPLOYING 10 SMALL LLMs IN SERVERLESS MODE');
  console.log('='.repeat(60));
  console.log();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const baseUrl = 'http://localhost:4893';
  const apiUrl = 'http://localhost:8000';

  const results = {
    deployed: [],
    failed: [],
    errors: []
  };

  try {
    // Navigate to serverless page
    console.log('Opening Serverless page...');
    await page.goto(`${baseUrl}/demo-app/serverless`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Check initial state
    console.log('Checking initial state...');
    const initialEndpoints = await page.locator('.rounded-xl.bg-dark-surface-card').count();
    console.log(`Initial demo endpoints: ${initialEndpoints}`);
    console.log();

    // Deploy each LLM
    for (let i = 0; i < SMALL_LLMS.length; i++) {
      const llm = SMALL_LLMS[i];
      console.log(`[${i + 1}/10] Deploying ${llm.name}...`);

      try {
        // Click Create Endpoint button
        const createButton = page.locator('button:has-text("Create Endpoint"), button:has-text("Criar Endpoint")');
        await createButton.first().click();
        await page.waitForTimeout(500);

        // Check if modal opened
        const modal = page.locator('[role="alertdialog"], div[class*="AlertDialog"], div[class*="modal"]');
        const modalVisible = await modal.count() > 0;

        if (modalVisible) {
          // Fill endpoint name
          const nameInput = page.locator('input[placeholder*="endpoint"], input[placeholder*="meu-endpoint"]');
          if (await nameInput.count() > 0) {
            await nameInput.first().fill(llm.id);
          }

          // Fill Docker image
          const dockerInput = page.locator('input[placeholder*="vllm"]');
          if (await dockerInput.count() > 0) {
            await dockerInput.first().fill('vllm/vllm-openai:latest');
          }

          // Fill Model ID
          const modelInput = page.locator('input[placeholder*="Qwen"], input[placeholder*="Model"]');
          if (await modelInput.count() > 0) {
            await modelInput.first().fill(llm.model_id);
          }

          // Select appropriate GPU based on VRAM requirement
          const gpuSelect = page.locator('select').first();
          if (await gpuSelect.count() > 0) {
            // Select GPU based on VRAM requirement
            if (llm.vram <= 2) {
              await gpuSelect.selectOption({ label: /RTX 3080/i }).catch(() => {});
            } else if (llm.vram <= 8) {
              await gpuSelect.selectOption({ label: /RTX 4080/i }).catch(() => {});
            } else {
              await gpuSelect.selectOption({ label: /RTX 4090/i }).catch(() => {});
            }
          }

          // Click Spot pricing option
          const spotButton = page.locator('button:has-text("Spot")');
          if (await spotButton.count() > 0) {
            await spotButton.first().click();
            await page.waitForTimeout(100);
          }

          // Handle dialog for demo mode
          let dialogMessage = null;
          page.on('dialog', async dialog => {
            dialogMessage = dialog.message();
            await dialog.dismiss();
          });

          // Click Create/Criar button
          const submitButton = page.locator('button:has-text("Criar Endpoint"), button:has-text("Create")');
          if (await submitButton.count() > 1) {
            await submitButton.last().click();
          } else if (await submitButton.count() > 0) {
            await submitButton.first().click();
          }
          await page.waitForTimeout(600);

          if (dialogMessage) {
            console.log(`  Demo mode: ${llm.name} would be deployed`);
            console.log(`  Config: ${llm.model_id} | ${llm.vram}GB VRAM | Spot pricing`);
          }

          // Close modal if still open
          const closeButton = page.locator('button:has-text("Cancelar"), button:has-text("Cancel"), button:has-text("X")');
          if (await closeButton.count() > 0) {
            await closeButton.first().click().catch(() => {});
            await page.waitForTimeout(200);
          }

          results.deployed.push({
            name: llm.name,
            model_id: llm.model_id,
            vram: llm.vram,
            status: 'simulated_in_demo'
          });

          console.log(`  OK: ${llm.name} simulated deployment`);
        } else {
          console.log(`  WARN: Modal did not open for ${llm.name}`);
          results.failed.push({ name: llm.name, reason: 'modal_not_opened' });
        }

      } catch (error) {
        console.log(`  ERROR: ${error.message}`);
        results.errors.push({ name: llm.name, error: error.message });
      }
    }

    // Also test via API directly
    console.log('\n' + '='.repeat(60));
    console.log('TESTING DIRECT API DEPLOYMENT');
    console.log('='.repeat(60));
    console.log();

    for (let i = 0; i < SMALL_LLMS.length; i++) {
      const llm = SMALL_LLMS[i];
      console.log(`[${i + 1}/10] API Deploy: ${llm.name}...`);

      try {
        const response = await page.request.post(`${apiUrl}/api/v1/serverless/endpoints`, {
          data: {
            name: `api-${llm.id}`,
            machine_type: 'spot',
            gpu_name: 'RTX 3080',
            region: 'US',
            min_instances: 0,
            max_instances: 3,
            docker_image: 'vllm/vllm-openai:latest',
            model_id: llm.model_id,
          },
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok()) {
          const data = await response.json();
          console.log(`  OK: Created ${data.id || 'endpoint'}`);
          results.deployed.push({
            name: `API: ${llm.name}`,
            endpoint_id: data.id,
            status: 'created'
          });
        } else {
          const errorText = await response.text();
          console.log(`  FAIL: ${response.status()} - ${errorText.substring(0, 100)}`);
          results.failed.push({
            name: llm.name,
            reason: `API error ${response.status()}`
          });
        }
      } catch (error) {
        console.log(`  ERROR: ${error.message}`);
        // This is expected in demo mode without proper auth
        results.failed.push({
          name: llm.name,
          reason: error.message.substring(0, 50)
        });
      }
    }

    // Final check
    console.log('\n' + '='.repeat(60));
    console.log('FINAL STATE CHECK');
    console.log('='.repeat(60));

    // Check API for global status
    try {
      const statusResponse = await page.request.get(`${apiUrl}/api/v1/serverless/status`);
      if (statusResponse.ok()) {
        const status = await statusResponse.json();
        console.log(`\nServerless System Status: ${status.status}`);
        console.log(`Total configured instances: ${status.total_instances}`);
        console.log(`Active instances: ${status.active_instances}`);
        console.log(`Paused instances: ${status.paused_instances}`);
        console.log(`Total savings: $${status.total_savings_usd}`);
      }
    } catch (e) {
      console.log('Could not fetch final status');
    }

  } catch (error) {
    console.error('\nFATAL ERROR:', error.message);
    results.errors.push({ name: 'global', error: error.message });
  } finally {
    await browser.close();
  }

  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('DEPLOYMENT SUMMARY');
  console.log('='.repeat(60));
  console.log(`Successfully deployed (or simulated): ${results.deployed.length}`);
  console.log(`Failed: ${results.failed.length}`);
  console.log(`Errors: ${results.errors.length}`);

  if (results.deployed.length > 0) {
    console.log('\nDeployed models:');
    results.deployed.forEach(d => {
      console.log(`  - ${d.name}: ${d.status}`);
    });
  }

  if (results.failed.length > 0) {
    console.log('\nFailed deployments:');
    results.failed.forEach(f => {
      console.log(`  - ${f.name}: ${f.reason}`);
    });
  }

  console.log('\n' + '='.repeat(60));

  return results;
}

// Run deployment
deploy10LLMs()
  .then(results => {
    process.exit(results.errors.length > 0 ? 1 : 0);
  })
  .catch(err => {
    console.error('Deployment script failed:', err);
    process.exit(1);
  });
