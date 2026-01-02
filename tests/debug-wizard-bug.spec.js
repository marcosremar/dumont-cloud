const { test, expect } = require('@playwright/test');

test.describe('Debug Wizard Bug', () => {
  test.use({ storageState: { cookies: [], origins: [] } }); // No auth needed

  test('Reproduce wizard step reset bug', async ({ page }) => {
    // Array para capturar console logs
    const consoleLogs = [];
    const consoleErrors = [];
    const networkRequests = [];

    // Capturar console.log
    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push({
        type: msg.type(),
        text: text,
        timestamp: new Date().toISOString()
      });
      console.log(`[BROWSER ${msg.type().toUpperCase()}]`, text);
    });

    // Capturar erros JavaScript
    page.on('pageerror', error => {
      consoleErrors.push({
        message: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      });
      console.log('[BROWSER ERROR]', error.message);
    });

    // Capturar network requests
    page.on('request', request => {
      if (request.url().includes('api') || request.url().includes('offers') || request.url().includes('vast')) {
        networkRequests.push({
          method: request.method(),
          url: request.url(),
          headers: request.headers(),
          timestamp: new Date().toISOString()
        });
        console.log(`[NETWORK REQUEST] ${request.method()} ${request.url()}`);
      }
    });

    // Capturar responses
    page.on('response', async response => {
      if (response.url().includes('api') || response.url().includes('offers') || response.url().includes('vast')) {
        const status = response.status();
        let body = null;
        try {
          body = await response.text();
        } catch (e) {
          body = '<unable to read>';
        }
        console.log(`[NETWORK RESPONSE] ${status} ${response.url()}`);
        if (status >= 400) {
          console.log(`[RESPONSE ERROR] ${body}`);
        }
      }
    });

    console.log('\n=== STEP 1: Navegando para /demo-app ===');
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    console.log('\n=== STEP 2: Setting demo_mode in localStorage ===');
    await page.evaluate(() => {
      localStorage.setItem('demo_mode', 'true');
    });

    // Verificar se está no Step 1
    console.log('\n=== STEP 3: Verificando Step 1 ===');
    const step1Visible = await page.locator('text=/EUA|USA|Estados Unidos/i').isVisible().catch(() => false);
    console.log('Step 1 (EUA) visível?', step1Visible);

    if (step1Visible) {
      console.log('\n=== STEP 4: Clicando em "EUA" ===');
      await page.locator('text=/EUA|USA|Estados Unidos/i').first().click();
      await page.waitForTimeout(500);

      console.log('\n=== STEP 5: Clicando em "Próximo" ===');
      const nextButton = page.locator('button:has-text("Próximo")');
      await nextButton.click();
      await page.waitForTimeout(1000);

      // Verificar se chegou no Step 2
      console.log('\n=== STEP 6: Verificando Step 2 ===');
      const step2Visible = await page.locator('text=/Desenvolver|Development|Treinar|Gaming/i').isVisible().catch(() => false);
      console.log('Step 2 (Desenvolver) visível?', step2Visible);

      if (step2Visible) {
        console.log('\n=== STEP 7: Clicando em "Desenvolver" ===');

        // Screenshot antes de clicar
        await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/debug-before-desenvolver.png', fullPage: true });

        await page.locator('text=/Desenvolver|Development/i').first().click();
        await page.waitForTimeout(2000);

        // Screenshot depois de clicar
        await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/debug-after-desenvolver.png', fullPage: true });

        // Verificar qual step está visível agora
        const step1AfterClick = await page.locator('text=/EUA|USA|Estados Unidos/i').isVisible().catch(() => false);
        const step2AfterClick = await page.locator('text=/Desenvolver|Development|Treinar|Gaming/i').isVisible().catch(() => false);
        const step3AfterClick = await page.locator('text=/Selecionar|Select|Máquinas|Machines/i').isVisible().catch(() => false);

        console.log('\n=== RESULTADO APÓS CLICAR EM "DESENVOLVER" ===');
        console.log('Voltou para Step 1 (EUA)?', step1AfterClick);
        console.log('Ainda está no Step 2 (Desenvolver)?', step2AfterClick);
        console.log('Avançou para Step 3 (Máquinas)?', step3AfterClick);

        if (step1AfterClick) {
          console.log('\n🐛 BUG CONFIRMADO: Wizard voltou para Step 1!');
        } else if (step3AfterClick) {
          console.log('\n✅ Wizard funcionou corretamente: avançou para Step 3');
        } else if (step2AfterClick) {
          console.log('\n⚠️ Wizard permaneceu no Step 2 (esperado: ir para Step 3)');
        }
      } else {
        console.log('❌ Não conseguiu chegar no Step 2');
      }
    } else {
      console.log('❌ Não encontrou Step 1');
    }

    // Salvar todos os logs em arquivo
    const debugReport = {
      consoleLogs,
      consoleErrors,
      networkRequests,
      timestamp: new Date().toISOString()
    };

    await page.evaluate((report) => {
      console.log('\n=== DEBUG REPORT ===');
      console.log(JSON.stringify(report, null, 2));
    }, debugReport);

    // Salvar em arquivo JSON
    const fs = require('fs');
    fs.writeFileSync(
      '/Users/marcos/CascadeProjects/dumontcloud/tests/wizard-debug-report.json',
      JSON.stringify(debugReport, null, 2)
    );

    console.log('\n✅ Debug report salvo em: tests/wizard-debug-report.json');
    console.log('✅ Screenshots salvos em: tests/debug-before-desenvolver.png e debug-after-desenvolver.png');
  });
});
