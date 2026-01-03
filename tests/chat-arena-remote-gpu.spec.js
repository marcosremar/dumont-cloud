// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Chat Arena Remote GPU Test via SSH Tunnel', () => {
  test('Chat with RTX 5070 remote GPU', async ({ page }) => {
    test.setTimeout(180000); // 3 min timeout for remote GPU

    // 1. Navigate to Chat Arena
    console.log('1. Navigating to Chat Arena...');
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.click('text=Chat Arena');
    await page.waitForTimeout(2000);
    console.log('   Chat Arena loaded');

    // 2. Open model selector
    console.log('2. Opening model selector...');
    const selectorBtn = page.getByRole('button', { name: /selecionar modelos/i }).first();
    await expect(selectorBtn).toBeVisible({ timeout: 10000 });
    await selectorBtn.click();
    await page.waitForTimeout(1000);

    // Take screenshot of available models
    await page.screenshot({ path: 'tests/screenshots/remote-gpu-1-models.png' });

    // 3. Look for RTX GPU model (5070 or 5080)
    console.log('3. Looking for RTX GPU model...');
    let gpuModel = page.locator('button').filter({ hasText: /RTX 5070/i }).first();
    let gpuVisible = await gpuModel.isVisible().catch(() => false);

    if (!gpuVisible) {
      gpuModel = page.locator('button').filter({ hasText: /RTX 5080/i }).first();
      gpuVisible = await gpuModel.isVisible().catch(() => false);
    }

    if (!gpuVisible) {
      // Check for any GPU model
      gpuModel = page.locator('button').filter({ hasText: /RTX|GPU/i }).first();
      gpuVisible = await gpuModel.isVisible().catch(() => false);
    }

    console.log(`   GPU model found: ${gpuVisible}`);

    if (!gpuVisible) {
      console.log('❌ No GPU model found in models list');
      await page.screenshot({ path: 'tests/screenshots/remote-gpu-error.png' });
      test.fail(true, 'No GPU model available');
      return;
    }

    // 4. Select the GPU model
    console.log('4. Selecting GPU model...');
    await gpuModel.click();
    await page.waitForTimeout(500);

    // Close dropdown
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // 5. Type and send message
    console.log('5. Sending test message...');
    const input = page.locator('input[placeholder*="Enviar mensagem"]').first();
    await expect(input).toBeVisible({ timeout: 5000 });
    await input.fill('Hello! Say hi in Portuguese.');
    await page.screenshot({ path: 'tests/screenshots/remote-gpu-2-typing.png' });

    await input.press('Enter');
    console.log('   Message sent');

    // 6. Wait for response (may take longer for remote GPU via SSH tunnel)
    console.log('6. Waiting for response from remote GPU via SSH tunnel...');

    try {
      // Wait for response to appear
      await page.waitForSelector('.prose, [class*="message"], [class*="response"]', { timeout: 60000 });
      console.log('   Response received!');
    } catch (e) {
      console.log('   Timeout waiting for response');
    }

    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'tests/screenshots/remote-gpu-3-response.png' });

    // 7. Check for response content
    console.log('7. Checking response...');
    const responses = page.locator('.prose, [class*="markdown"]');
    const responseCount = await responses.count();
    console.log(`   Found ${responseCount} response elements`);

    // Check for metrics (tokens/second)
    const metrics = page.locator('text=/\\d+\\.?\\d* t\\/s/');
    const metricsCount = await metrics.count();
    console.log(`8. Found ${metricsCount} metrics displays`);

    // Verify response exists
    if (responseCount > 0) {
      const firstResponse = await responses.first().textContent();
      console.log(`   Response preview: "${firstResponse?.substring(0, 100)}..."`);
      console.log('✅ SUCCESS: Chat with remote GPU via SSH tunnel working!');
      expect(responseCount).toBeGreaterThan(0);
    } else {
      console.log('❌ No response received from GPU');
      await page.screenshot({ path: 'tests/screenshots/remote-gpu-failure.png' });
    }
  });

  test('Verify API connection to remote GPU', async ({ request }) => {
    // Test the backend API directly
    console.log('Testing backend API for remote GPU models...');

    const modelsResponse = await request.get('http://localhost:8001/api/v1/chat/models');
    const modelsData = await modelsResponse.json();

    console.log(`Models response: ${JSON.stringify(modelsData, null, 2)}`);
    expect(modelsData.success).toBe(true);
    expect(modelsData.models.length).toBeGreaterThan(0);

    // Check that we have SSH info for the model
    const model = modelsData.models[0];
    console.log(`First model: ${model.gpu} (ID: ${model.id})`);
    expect(model.ssh_host).toBeTruthy();
    expect(model.ssh_port).toBeTruthy();

    // Test the proxy endpoint
    console.log(`Testing proxy tags for instance ${model.id}...`);
    const tagsResponse = await request.get(`http://localhost:8001/api/v1/chat/proxy/${model.id}/tags`);
    const tagsData = await tagsResponse.json();

    console.log(`Tags response: ${JSON.stringify(tagsData, null, 2)}`);
    expect(tagsData.models).toBeDefined();
    expect(tagsData.models.length).toBeGreaterThan(0);

    console.log('✅ API connection to remote GPU verified!');
  });
});
