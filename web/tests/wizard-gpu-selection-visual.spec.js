import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Wizard GPU Selection - Visual Detailed Test', () => {
  test('Should display GPU list and allow selection', async ({ page }) => {
    const screenshotsDir = path.join(__dirname, '..', 'screenshots');

    console.log('=== INICIANDO TESTE VISUAL DO WIZARD GPU ===');

    // 1. Login automático
    console.log('1. Fazendo login automático...');
    await page.goto('http://localhost:4894/login?auto_login=demo');
    await page.waitForURL('**/app**', { timeout: 10000 });
    await page.screenshot({ path: path.join(screenshotsDir, 'gpu-wizard-01-after-login.png'), fullPage: true });
    console.log('✅ Login realizado - Screenshot salvo');

    // 2. Verificar que estamos no Dashboard (wizard)
    console.log('\n2. Verificando Dashboard/Wizard...');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(screenshotsDir, 'gpu-wizard-02-dashboard-initial.png'), fullPage: true });

    // Verificar se wizard está visível
    const hasWizard = await page.locator('text=/Assistente|Wizard|Região|Region/i').isVisible().catch(() => false);
    console.log(`Wizard visível: ${hasWizard}`);

    // 3. Selecionar região (EUA)
    console.log('\n3. Selecionando região EUA...');

    // Procurar por diferentes formas de seletor de região
    const regionSelectors = [
      'text="EUA"',
      'text="USA"',
      'button:has-text("EUA")',
      'button:has-text("USA")',
      '[data-region="usa"]',
      '[data-region="eua"]'
    ];

    let regionSelected = false;
    for (const selector of regionSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible().catch(() => false)) {
        console.log(`Encontrado seletor de região: ${selector}`);
        await element.click();
        regionSelected = true;
        await page.waitForTimeout(1000);
        break;
      }
    }

    await page.screenshot({ path: path.join(screenshotsDir, 'gpu-wizard-03-after-region-selection.png'), fullPage: true });
    console.log(`Região selecionada: ${regionSelected}`);

    // 4. Clicar em "Próximo" se houver
    console.log('\n4. Procurando botão Próximo/Next...');
    const nextButtonSelectors = [
      'button:has-text("Próximo")',
      'button:has-text("Next")',
      'button:has-text("Continuar")',
      'button:has-text("Continue")'
    ];

    for (const selector of nextButtonSelectors) {
      const btn = page.locator(selector);
      if (await btn.isVisible().catch(() => false)) {
        console.log(`Clicando em: ${selector}`);
        await btn.click();
        await page.waitForTimeout(2000);
        break;
      }
    }

    await page.screenshot({ path: path.join(screenshotsDir, 'gpu-wizard-04-after-first-next.png'), fullPage: true });

    // 5. Selecionar propósito (qualquer um)
    console.log('\n5. Selecionando propósito...');

    const purposeSelectors = [
      'text="Machine Learning"',
      'text="Deep Learning"',
      'text="Treinamento"',
      'text="Training"',
      'text="Inferência"',
      'text="Inference"'
    ];

    for (const selector of purposeSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible().catch(() => false)) {
        console.log(`Selecionando propósito: ${selector}`);
        await element.click();
        await page.waitForTimeout(1000);
        break;
      }
    }

    await page.screenshot({ path: path.join(screenshotsDir, 'gpu-wizard-05-after-purpose-selection.png'), fullPage: true });

    // Clicar em próximo novamente
    for (const selector of nextButtonSelectors) {
      const btn = page.locator(selector);
      if (await btn.isVisible().catch(() => false)) {
        console.log(`Clicando em próximo novamente: ${selector}`);
        await btn.click();
        await page.waitForTimeout(2000);
        break;
      }
    }

    await page.screenshot({ path: path.join(screenshotsDir, 'gpu-wizard-06-after-second-next.png'), fullPage: true });

    // 6. *** FOCO PRINCIPAL: Aguardar lista de GPUs carregar ***
    console.log('\n6. *** AGUARDANDO LISTA DE GPUs CARREGAR ***');

    // Aguardar indicadores de carregamento
    await page.waitForTimeout(3000);

    // Procurar por diferentes indicadores de GPUs
    const gpuIndicators = [
      'text=/RTX|GeForce|Tesla|A100|H100|4090|3090/i',
      'text=/VRAM|GB/i',
      'text=/\\$/i', // Preço
      '[class*="gpu"]',
      '[data-gpu]',
      'text=/GPU/i'
    ];

    console.log('Procurando por indicadores de GPU na página...');
    let gpusFound = false;
    for (const indicator of gpuIndicators) {
      const elements = await page.locator(indicator).count();
      if (elements > 0) {
        console.log(`✅ Encontrado ${elements} elementos com: ${indicator}`);
        gpusFound = true;
      }
    }

    // Screenshot CRÍTICO da lista de GPUs
    await page.screenshot({ path: path.join(screenshotsDir, 'gpu-wizard-07-GPU-LIST-CRITICAL.png'), fullPage: true });
    console.log('📸 SCREENSHOT CRÍTICO DA LISTA DE GPUs SALVO');

    // 7. Verificar estrutura dos cards de GPU
    console.log('\n7. Verificando estrutura dos cards de GPU...');

    // Procurar por cards/containers de GPU
    const gpuCardSelectors = [
      '[class*="gpu"][class*="card"]',
      '[class*="offer"]',
      '[data-gpu-card]',
      '[class*="rounded"][class*="border"]'
    ];

    let gpuCards = null;
    for (const selector of gpuCardSelectors) {
      const cards = page.locator(selector);
      const count = await cards.count();
      if (count > 0) {
        console.log(`Encontrado ${count} cards com seletor: ${selector}`);
        gpuCards = cards;
        break;
      }
    }

    if (gpuCards) {
      const cardCount = await gpuCards.count();
      console.log(`\n📊 TOTAL DE CARDS ENCONTRADOS: ${cardCount}`);

      // Analisar primeiro card
      if (cardCount > 0) {
        console.log('\n🔍 Analisando primeiro card:');
        const firstCard = gpuCards.first();
        const cardText = await firstCard.textContent();
        console.log(`Conteúdo do card:\n${cardText}`);

        // Verificar elementos esperados
        const hasGpuName = /RTX|GeForce|Tesla|A100|H100|4090|3090/i.test(cardText);
        const hasPrice = /\$|USD|\/h/i.test(cardText);
        const hasVRAM = /VRAM|GB/i.test(cardText);

        console.log(`- Nome GPU: ${hasGpuName ? '✅' : '❌'}`);
        console.log(`- Preço: ${hasPrice ? '✅' : '❌'}`);
        console.log(`- VRAM: ${hasVRAM ? '✅' : '❌'}`);
      }
    } else {
      console.log('❌ NENHUM CARD DE GPU ENCONTRADO!');
    }

    // 8. Tentar CLICAR em uma GPU
    console.log('\n8. Tentando clicar em uma GPU...');

    if (gpuCards && await gpuCards.count() > 0) {
      const firstCard = gpuCards.first();

      // Scroll até o card
      await firstCard.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);

      // Screenshot antes do clique
      await page.screenshot({ path: path.join(screenshotsDir, 'gpu-wizard-08-before-gpu-click.png'), fullPage: true });

      // Tentar clicar
      try {
        await firstCard.click();
        console.log('✅ Clique na GPU realizado');
        await page.waitForTimeout(1000);
      } catch (error) {
        console.log(`❌ Erro ao clicar na GPU: ${error.message}`);
      }

      // 9. Screenshot após selecionar
      await page.screenshot({ path: path.join(screenshotsDir, 'gpu-wizard-09-after-gpu-click.png'), fullPage: true });
      console.log('📸 Screenshot após clique salvo');

      // 10. Verificar se GPU ficou destacada/selecionada
      console.log('\n10. Verificando se GPU está selecionada...');

      // Procurar por indicadores visuais de seleção
      const selectionIndicators = [
        '[class*="selected"]',
        '[class*="active"]',
        '[class*="highlighted"]',
        '[aria-selected="true"]',
        '[data-selected="true"]'
      ];

      let isSelected = false;
      for (const indicator of selectionIndicators) {
        const selectedElements = await page.locator(indicator).count();
        if (selectedElements > 0) {
          console.log(`✅ Indicador de seleção encontrado: ${indicator} (${selectedElements} elementos)`);
          isSelected = true;
        }
      }

      console.log(`GPU parece selecionada: ${isSelected ? '✅' : '❌'}`);

      // 11. Verificar se botão "Próximo" está habilitado
      console.log('\n11. Verificando botão Próximo...');

      for (const selector of nextButtonSelectors) {
        const btn = page.locator(selector);
        if (await btn.isVisible().catch(() => false)) {
          const isEnabled = await btn.isEnabled();
          const isDisabled = await btn.isDisabled();
          console.log(`Botão ${selector}:`);
          console.log(`  - Habilitado: ${isEnabled ? '✅' : '❌'}`);
          console.log(`  - Desabilitado: ${isDisabled ? '✅' : '❌'}`);
        }
      }

    } else {
      console.log('❌ NÃO FOI POSSÍVEL CLICAR - NENHUM CARD ENCONTRADO');
    }

    // Screenshot final
    await page.screenshot({ path: path.join(screenshotsDir, 'gpu-wizard-10-final-state.png'), fullPage: true });

    // Capturar HTML completo para análise
    console.log('\n📝 Capturando HTML completo...');
    const htmlContent = await page.content();
    fs.writeFileSync(
      path.join(screenshotsDir, 'gpu-wizard-page-source.html'),
      htmlContent
    );
    console.log('HTML salvo em: gpu-wizard-page-source.html');

    // Capturar console logs
    const logs = [];
    page.on('console', msg => logs.push(`${msg.type()}: ${msg.text()}`));

    console.log('\n=== RESUMO DO TESTE ===');
    console.log(`GPUs encontradas: ${gpusFound ? '✅' : '❌'}`);
    console.log(`Total de screenshots: 10+`);
    console.log(`Diretório: ${screenshotsDir}`);
    console.log('\n=== TESTE CONCLUÍDO ===');
  });
});
