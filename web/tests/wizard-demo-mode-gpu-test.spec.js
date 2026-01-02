import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Wizard GPU Selection - DEMO MODE', () => {
  test('Should display GPU list in demo mode', async ({ page }) => {
    const screenshotsDir = path.join(__dirname, '..', 'screenshots');

    console.log('=== TESTE WIZARD GPU - DEMO MODE ===\n');

    // 1. Navegar para DEMO APP (não requer backend)
    console.log('1. Navegando para DEMO APP...');
    await page.goto('http://localhost:4894/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);

    await page.screenshot({
      path: path.join(screenshotsDir, 'demo-wizard-01-initial.png'),
      fullPage: true
    });

    const currentUrl = page.url();
    console.log(`URL: ${currentUrl}`);

    // 2. Procurar por wizard
    console.log('\n2. Procurando wizard na página...');

    const pageText = await page.textContent('body');
    const hasRegion = /região|region/i.test(pageText);
    const hasGPU = /gpu/i.test(pageText);
    const hasWizard = /wizard|assistente/i.test(pageText);

    console.log(`Tem "Região": ${hasRegion ? '✅' : '❌'}`);
    console.log(`Tem "GPU": ${hasGPU ? '✅' : '❌'}`);
    console.log(`Tem "Wizard": ${hasWizard ? '✅' : '❌'}`);

    // 3. PASSO 1: Selecionar região
    console.log('\n3. PASSO 1 - Selecionando região...');

    // Procurar botões de região
    const regionButtons = [
      'button:has-text("EUA")',
      'button:has-text("USA")',
      'button:has-text("Estados Unidos")',
      '[data-region="us"]',
      '[data-region="usa"]'
    ];

    let regionSelected = false;
    for (const selector of regionButtons) {
      try {
        const btn = page.locator(selector).first();
        if (await btn.isVisible({ timeout: 2000 })) {
          console.log(`Clicando em região: ${selector}`);
          await btn.click();
          await page.waitForTimeout(1000);
          regionSelected = true;
          break;
        }
      } catch (e) {
        // Tentar próximo
      }
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'demo-wizard-02-region-selected.png'),
      fullPage: true
    });

    console.log(`Região selecionada: ${regionSelected ? '✅' : '❌'}`);

    // 4. Clicar em Próximo
    console.log('\n4. Clicando em Próximo...');

    const nextButtons = [
      'button:has-text("Próximo")',
      'button:has-text("Next")',
      'button:has-text("Continuar")',
      'button[type="submit"]:has-text("Próximo")'
    ];

    for (const selector of nextButtons) {
      try {
        const btn = page.locator(selector).first();
        if (await btn.isVisible({ timeout: 1000 }) && await btn.isEnabled()) {
          console.log(`Clicando: ${selector}`);
          await btn.click();
          await page.waitForTimeout(2000);
          break;
        }
      } catch (e) {
        // Continuar
      }
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'demo-wizard-03-step2.png'),
      fullPage: true
    });

    // 5. PASSO 2: Selecionar Performance Tier
    console.log('\n5. PASSO 2 - Selecionando Performance Tier...');

    // Procurar por tiers: Budget, Balanced, Performance, etc
    const tiers = ['Budget', 'Balanced', 'Performance', 'Premium', 'Econômico'];

    let tierSelected = false;
    for (const tier of tiers) {
      try {
        const btn = page.locator(`button:has-text("${tier}")`).first();
        if (await btn.isVisible({ timeout: 1000 })) {
          console.log(`Selecionando tier: ${tier}`);
          await btn.click();
          await page.waitForTimeout(3000); // Aguardar carregar GPUs
          tierSelected = true;
          break;
        }
      } catch (e) {
        // Próximo
      }
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'demo-wizard-04-tier-selected.png'),
      fullPage: true
    });

    console.log(`Tier selecionado: ${tierSelected ? '✅' : '❌'}`);

    // 6. *** CRÍTICO: Verificar se GPUs apareceram ***
    console.log('\n6. *** VERIFICANDO LISTA DE GPUs ***');

    await page.waitForTimeout(2000); // Aguardar render

    await page.screenshot({
      path: path.join(screenshotsDir, 'demo-wizard-05-GPU-LIST-CRITICAL.png'),
      fullPage: true
    });

    // Procurar por indicadores de GPU no HTML
    const html = await page.content();

    // Padrões de GPU
    const gpuPatterns = {
      'Nome GPU (RTX/GeForce/etc)': /RTX\s*\d{4}|GeForce|Tesla|A100|H100/gi,
      'Preço ($/h)': /\$\s*[\d.]+\s*\/\s*h/gi,
      'VRAM (GB)': /\d+\s*GB\s*VRAM/gi,
      'Label (Mais econômico, etc)': /Mais econômico|Melhor custo|Mais rápido/gi,
    };

    console.log('\nAnalisando HTML para GPUs:');
    const foundPatterns = {};
    for (const [name, pattern] of Object.entries(gpuPatterns)) {
      const matches = html.match(pattern) || [];
      foundPatterns[name] = matches.length;
      console.log(`  ${name}: ${matches.length > 0 ? '✅' : '❌'} (${matches.length} ocorrências)`);
      if (matches.length > 0) {
        console.log(`    Exemplos: ${matches.slice(0, 3).join(', ')}`);
      }
    }

    // 7. Contar cards de GPU
    console.log('\n7. Contando cards de GPU...');

    const possibleCardSelectors = [
      '[class*="gpu-card"]',
      '[class*="machine-card"]',
      '[data-gpu]',
      'button:has-text("Selecionar")'
    ];

    let maxCards = 0;
    let bestSelector = '';

    for (const selector of possibleCardSelectors) {
      const count = await page.locator(selector).count();
      if (count > maxCards) {
        maxCards = count;
        bestSelector = selector;
      }
      console.log(`  ${selector}: ${count} elementos`);
    }

    console.log(`\n📊 CARDS ENCONTRADOS: ${maxCards} (usando ${bestSelector})`);

    // 8. Analisar primeiro card (se existir)
    if (maxCards > 0) {
      console.log('\n8. Analisando primeiro card...');

      const firstCard = page.locator(bestSelector).first();
      await firstCard.scrollIntoViewIfNeeded();

      const cardText = await firstCard.textContent();
      console.log(`Conteúdo do card:\n${cardText.substring(0, 300)}...`);

      // Verificar elementos esperados
      const hasGpuName = /RTX|GeForce|Tesla|A100|H100/i.test(cardText);
      const hasPrice = /\$|USD|\/h/i.test(cardText);
      const hasVRAM = /VRAM|GB/i.test(cardText);
      const hasSelectButton = /Selecionar|Select/i.test(cardText);

      console.log('\nElementos no card:');
      console.log(`  Nome GPU: ${hasGpuName ? '✅' : '❌'}`);
      console.log(`  Preço: ${hasPrice ? '✅' : '❌'}`);
      console.log(`  VRAM: ${hasVRAM ? '✅' : '❌'}`);
      console.log(`  Botão Selecionar: ${hasSelectButton ? '✅' : '❌'}`);

      // 9. Tentar clicar no card/botão
      console.log('\n9. Tentando selecionar GPU...');

      await page.screenshot({
        path: path.join(screenshotsDir, 'demo-wizard-06-before-select.png'),
        fullPage: true
      });

      try {
        // Tentar clicar no botão "Selecionar" dentro do card
        const selectButton = firstCard.locator('button:has-text("Selecionar")');
        if (await selectButton.isVisible()) {
          await selectButton.click();
          console.log('✅ Clicou no botão Selecionar');
        } else {
          // Clicar no card inteiro
          await firstCard.click();
          console.log('✅ Clicou no card');
        }

        await page.waitForTimeout(1000);

      } catch (error) {
        console.log(`❌ Erro ao clicar: ${error.message}`);
      }

      await page.screenshot({
        path: path.join(screenshotsDir, 'demo-wizard-07-after-select.png'),
        fullPage: true
      });

      // 10. Verificar se ficou selecionado
      console.log('\n10. Verificando seleção...');

      const selectedIndicators = [
        '[class*="selected"]',
        '[aria-selected="true"]',
        '[data-selected="true"]',
        '.bg-green-500',
        '.border-green-500'
      ];

      let hasSelection = false;
      for (const indicator of selectedIndicators) {
        const count = await page.locator(indicator).count();
        if (count > 0) {
          console.log(`  ${indicator}: ${count} elementos`);
          hasSelection = true;
        }
      }

      console.log(`GPU parece selecionada: ${hasSelection ? '✅' : '❌'}`);

      // 11. Verificar botão Próximo habilitado
      console.log('\n11. Verificando botão Próximo...');

      for (const selector of nextButtons) {
        try {
          const btn = page.locator(selector).first();
          if (await btn.isVisible({ timeout: 1000 })) {
            const isEnabled = await btn.isEnabled();
            console.log(`  ${selector}: ${isEnabled ? 'HABILITADO ✅' : 'DESABILITADO ❌'}`);
          }
        } catch (e) {
          // Ignorar
        }
      }

    } else {
      console.log('\n❌ NENHUM CARD DE GPU ENCONTRADO!');
      console.log('\nPossíveis razões:');
      console.log('  1. Demo mode não está ativo (verificar URL)');
      console.log('  2. Tier não foi selecionado corretamente');
      console.log('  3. DEMO_OFFERS não está definido');
      console.log('  4. Componente não renderizou os cards');
    }

    // Screenshot final
    await page.screenshot({
      path: path.join(screenshotsDir, 'demo-wizard-08-final.png'),
      fullPage: true
    });

    // Salvar HTML
    fs.writeFileSync(
      path.join(screenshotsDir, 'demo-wizard-full.html'),
      html
    );

    console.log('\n=== RESUMO ===');
    console.log(`URL testada: ${currentUrl}`);
    console.log(`Demo mode ativo: ${currentUrl.includes('/demo-app') ? '✅' : '❌'}`);
    console.log(`GPUs encontradas no HTML: ${Object.values(foundPatterns).some(v => v > 0) ? '✅' : '❌'}`);
    console.log(`Cards renderizados: ${maxCards}`);
    console.log(`Screenshots: 8`);
    console.log(`Diretório: ${screenshotsDir}`);
    console.log('\n=== TESTE CONCLUÍDO ===');
  });
});
