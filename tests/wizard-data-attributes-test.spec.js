const { test, expect } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

/**
 * TESTE WIZARD - NOVOS DATA ATTRIBUTES
 *
 * Testa a seleção de GPU usando os NOVOS data attributes:
 * - data-gpu-card="true"
 * - data-gpu-name="RTX 4090"
 * - data-selected="true/false"
 */
test.describe('Wizard - Teste Data Attributes (GPU Selection)', () => {
  test('Deve usar data attributes para selecionar GPU', async ({ page }) => {
    const screenshotsDir = path.join(__dirname, '..', 'screenshots');
    const logFile = path.join(screenshotsDir, 'wizard-data-attributes-log.txt');

    let logContent = '';
    const log = (message) => {
      const timestamp = new Date().toISOString();
      const logLine = `[${timestamp}] ${message}`;
      console.log(logLine);
      logContent += logLine + '\n';
    };

    log('==============================================');
    log('TESTE WIZARD - DATA ATTRIBUTES');
    log('URL: http://localhost:4894/demo-app');
    log('==============================================\n');

    // Capturar logs do console do browser
    page.on('console', msg => {
      log(`[BROWSER ${msg.type().toUpperCase()}] ${msg.text()}`);
    });

    // Capturar erros de página
    page.on('pageerror', error => {
      log(`[PAGE ERROR] ${error.message}`);
    });

    // PASSO 1: Navegar para demo-app
    log('\n📍 PASSO 1: Navegando para http://localhost:4894/demo-app');
    try {
      await page.goto('http://localhost:4894/demo-app', {
        waitUntil: 'domcontentloaded',
        timeout: 10000
      });
      log('✅ Página carregada com sucesso');
    } catch (error) {
      log(`❌ Erro ao carregar página: ${error.message}`);
      throw error;
    }

    await page.waitForTimeout(2000);
    await page.screenshot({
      path: path.join(screenshotsDir, 'data-attr-01-initial.png'),
      fullPage: true
    });
    log('📸 Screenshot: data-attr-01-initial.png');

    // PASSO 2: Selecionar região EUA
    log('\n📍 PASSO 2: Selecionando região EUA');

    const regionSelectors = [
      'button:has-text("EUA")',
      'button:has-text("USA")',
      '[data-region="usa"]',
      '[data-region="us"]',
      'div[role="button"]:has-text("EUA")'
    ];

    let regionSelected = false;
    for (const selector of regionSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          log(`Encontrado elemento: ${selector}`);
          await element.click();
          await page.waitForTimeout(1000);
          regionSelected = true;
          log('✅ Região EUA selecionada');
          break;
        }
      } catch (e) {
        log(`Seletor ${selector} não encontrado, tentando próximo...`);
      }
    }

    if (!regionSelected) {
      log('⚠️ Não foi possível selecionar região automaticamente');
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'data-attr-02-after-region.png'),
      fullPage: true
    });
    log('📸 Screenshot: data-attr-02-after-region.png');

    // Clicar em Próximo
    const nextButton = page.locator('button:has-text("Próximo"), button:has-text("Next")').first();
    if (await nextButton.isVisible({ timeout: 2000 })) {
      await nextButton.click();
      await page.waitForTimeout(1500);
      log('✅ Clicou em Próximo (Step 1 → Step 2)');
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'data-attr-03-step2.png'),
      fullPage: true
    });

    // PASSO 3: Selecionar propósito
    log('\n📍 PASSO 3: Selecionando propósito');

    const purposeOptions = ['Machine Learning', 'Training', 'Inference', 'Treinamento'];
    let purposeSelected = false;

    for (const purpose of purposeOptions) {
      try {
        const element = page.locator(`button:has-text("${purpose}"), div[role="button"]:has-text("${purpose}")`).first();
        if (await element.isVisible({ timeout: 1000 })) {
          log(`Selecionando propósito: ${purpose}`);
          await element.click();
          await page.waitForTimeout(1000);
          purposeSelected = true;
          log('✅ Propósito selecionado');
          break;
        }
      } catch (e) {
        // Continuar tentando
      }
    }

    if (!purposeSelected) {
      log('⚠️ Não foi possível selecionar propósito automaticamente');
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'data-attr-04-after-purpose.png'),
      fullPage: true
    });

    // Clicar em Próximo novamente
    if (await nextButton.isVisible({ timeout: 2000 })) {
      await nextButton.click();
      await page.waitForTimeout(2000);
      log('✅ Clicou em Próximo (Step 2 → Step 3 - GPU Selection)');
    }

    // PASSO 4: AGUARDAR GPUs carregarem
    log('\n📍 PASSO 4: AGUARDANDO GPUs carregarem...');
    log('Esperando mensagem "Buscando máquinas..." ou cards de GPU');

    // Esperar até 15 segundos para GPUs aparecerem
    let gpusLoaded = false;
    for (let i = 0; i < 15; i++) {
      await page.waitForTimeout(1000);

      const hasLoadingMessage = await page.locator('text=/buscando|loading|carregando/i').isVisible().catch(() => false);
      const hasGpuCards = await page.locator('[data-gpu-card="true"]').count() > 0;

      if (hasLoadingMessage) {
        log(`⏳ [${i+1}s] "Buscando máquinas..." visível`);
      }

      if (hasGpuCards) {
        log(`✅ [${i+1}s] GPUs carregadas!`);
        gpusLoaded = true;
        break;
      }
    }

    await page.waitForTimeout(2000); // Aguardar estabilizar
    await page.screenshot({
      path: path.join(screenshotsDir, 'data-attr-05-GPU-LIST-LOADED.png'),
      fullPage: true
    });
    log('📸 Screenshot CRÍTICO: data-attr-05-GPU-LIST-LOADED.png');

    // PASSO 5: Verificar data attributes
    log('\n📍 PASSO 5: Verificando DATA ATTRIBUTES dos cards de GPU');

    const gpuCards = page.locator('[data-gpu-card="true"]');
    const cardCount = await gpuCards.count();
    log(`Total de cards com [data-gpu-card="true"]: ${cardCount}`);

    if (cardCount === 0) {
      log('❌ ERRO: Nenhum card com data-gpu-card="true" encontrado!');
      log('Verificando estrutura da página...');

      const pageContent = await page.content();
      fs.writeFileSync(
        path.join(screenshotsDir, 'data-attr-page-source.html'),
        pageContent
      );
      log('HTML da página salvo em: data-attr-page-source.html');

      // Tentar encontrar indicadores de GPU sem data attributes
      const rtxCount = await page.locator('text=/RTX\\s*\\d{4}/i').count();
      const a100Count = await page.locator('text=/A100|H100/i').count();
      log(`GPUs encontradas por texto (RTX): ${rtxCount}`);
      log(`GPUs encontradas por texto (A100/H100): ${a100Count}`);
    } else {
      log('✅ Cards com data attributes encontrados!');

      // Analisar cada card
      for (let i = 0; i < Math.min(cardCount, 5); i++) {
        const card = gpuCards.nth(i);
        const gpuName = await card.getAttribute('data-gpu-name');
        const isSelected = await card.getAttribute('data-selected');

        log(`\nCard ${i + 1}:`);
        log(`  - data-gpu-name: ${gpuName}`);
        log(`  - data-selected: ${isSelected}`);

        // Verificar conteúdo do card
        const cardText = await card.textContent();
        log(`  - Texto visível: ${cardText.substring(0, 100).replace(/\n/g, ' ')}...`);
      }
    }

    // PASSO 6: Tirar screenshot quando GPUs aparecerem
    await page.screenshot({
      path: path.join(screenshotsDir, 'data-attr-06-GPUs-visible.png'),
      fullPage: true
    });
    log('\n📸 Screenshot: data-attr-06-GPUs-visible.png');

    // PASSO 7: Usar seletor [data-gpu-card="true"] para encontrar cards
    log('\n📍 PASSO 7: Usando seletor [data-gpu-card="true"]');

    if (cardCount > 0) {
      const firstCard = gpuCards.first();

      // Scroll até o card
      await firstCard.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);

      log('✅ Primeiro card encontrado e visível');

      // Verificar estado antes do clique
      const beforeClick = {
        gpuName: await firstCard.getAttribute('data-gpu-name'),
        selected: await firstCard.getAttribute('data-selected')
      };

      log(`Estado ANTES do clique:`);
      log(`  - GPU: ${beforeClick.gpuName}`);
      log(`  - Selected: ${beforeClick.selected}`);

      // PASSO 8: Clicar no PRIMEIRO card
      log('\n📍 PASSO 8: Clicando no PRIMEIRO card de GPU');

      await page.screenshot({
        path: path.join(screenshotsDir, 'data-attr-07-before-click.png'),
        fullPage: true
      });

      try {
        await firstCard.click();
        log('✅ Clique realizado com sucesso');
        await page.waitForTimeout(1500);
      } catch (error) {
        log(`❌ Erro ao clicar: ${error.message}`);
      }

      // PASSO 9: Verificar mudança de data-selected
      log('\n📍 PASSO 9: Verificando mudança de [data-selected]');

      const afterClick = {
        gpuName: await firstCard.getAttribute('data-gpu-name'),
        selected: await firstCard.getAttribute('data-selected')
      };

      log(`Estado DEPOIS do clique:`);
      log(`  - GPU: ${afterClick.gpuName}`);
      log(`  - Selected: ${afterClick.selected}`);

      if (beforeClick.selected !== afterClick.selected) {
        log(`✅ SUCESSO! data-selected mudou de "${beforeClick.selected}" para "${afterClick.selected}"`);
      } else {
        log(`⚠️ AVISO: data-selected não mudou (manteve "${afterClick.selected}")`);
      }

      await page.screenshot({
        path: path.join(screenshotsDir, 'data-attr-08-after-click.png'),
        fullPage: true
      });
      log('📸 Screenshot: data-attr-08-after-click.png');

      // PASSO 10: Clicar em Próximo e verificar avanço
      log('\n📍 PASSO 10: Clicando em Próximo e verificando avanço');

      const finalNextButton = page.locator('button:has-text("Próximo"), button:has-text("Next")').first();

      if (await finalNextButton.isVisible({ timeout: 2000 })) {
        const isEnabled = await finalNextButton.isEnabled();
        log(`Botão "Próximo" está ${isEnabled ? 'HABILITADO ✅' : 'DESABILITADO ❌'}`);

        if (isEnabled) {
          const urlBefore = page.url();
          await finalNextButton.click();
          await page.waitForTimeout(2000);
          const urlAfter = page.url();

          log(`URL antes: ${urlBefore}`);
          log(`URL depois: ${urlAfter}`);

          if (urlBefore !== urlAfter) {
            log('✅ Navegação detectada - wizard avançou!');
          } else {
            log('⚠️ URL não mudou - verificar se wizard mudou de step');
          }
        }
      } else {
        log('❌ Botão "Próximo" não encontrado');
      }

      await page.screenshot({
        path: path.join(screenshotsDir, 'data-attr-09-after-next.png'),
        fullPage: true
      });
      log('📸 Screenshot: data-attr-09-after-next.png');

    } else {
      log('❌ Impossível continuar - nenhum card de GPU encontrado');
    }

    // Screenshot final
    await page.screenshot({
      path: path.join(screenshotsDir, 'data-attr-10-final.png'),
      fullPage: true
    });

    // Salvar logs em arquivo
    fs.writeFileSync(logFile, logContent);

    // RESUMO FINAL
    log('\n==============================================');
    log('RESUMO DO TESTE');
    log('==============================================');
    log(`Cards com [data-gpu-card="true"]: ${cardCount}`);
    log(`GPUs carregadas: ${gpusLoaded ? 'SIM ✅' : 'NÃO ❌'}`);
    log(`Screenshots salvos: 10`);
    log(`Log completo: ${logFile}`);
    log(`Diretório: ${screenshotsDir}`);
    log('==============================================\n');

    // Asserções
    expect(cardCount).toBeGreaterThan(0);

    if (cardCount > 0) {
      const firstGpuName = await gpuCards.first().getAttribute('data-gpu-name');
      expect(firstGpuName).toBeTruthy();
      log(`✅ Teste PASSOU - GPU selecionável: ${firstGpuName}`);
    }
  });
});
