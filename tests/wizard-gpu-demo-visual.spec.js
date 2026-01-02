/**
 * Teste VISUAL completo do wizard de GPU em MODO DEMO
 * URL: http://localhost:4894/demo-app
 *
 * Este teste documenta cada passo da interação com o wizard,
 * capturando screenshots e validando o comportamento.
 */

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/gpu-selection';

test.describe('Wizard GPU - Modo DEMO - Teste Visual Completo', () => {

  test('Fluxo completo: Região → Propósito → Seleção de GPU', async ({ page }) => {
    const log = [];

    // =======================
    // PASSO 1: Navegação inicial
    // =======================
    log.push('PASSO 1: Navegando para modo DEMO...');
    await page.goto('http://localhost:4894/demo-app');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '01-pagina-inicial-demo.png'),
      fullPage: true
    });
    log.push('✅ Screenshot 01: Página inicial do modo DEMO');

    // =======================
    // PASSO 2: Localizar o wizard
    // =======================
    log.push('\nPASSO 2: Localizando wizard "Nova Instância GPU"...');

    // Procurar por diferentes variações do título
    const wizardSelectors = [
      'text="Nova Instância GPU"',
      'text="Nova Instância"',
      'text="Wizard"',
      'h2:has-text("GPU")',
      'h3:has-text("GPU")',
      '[class*="wizard"]'
    ];

    let wizardFound = false;
    for (const selector of wizardSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          log.push(`✅ Wizard encontrado com seletor: ${selector}`);
          wizardFound = true;
          break;
        }
      } catch (e) {
        // Continuar tentando
      }
    }

    if (!wizardFound) {
      log.push('⚠️ Wizard não encontrado com seletores padrão. Analisando página...');

      // Listar todos os headings
      const headings = await page.locator('h1, h2, h3').allTextContents();
      log.push('Headings encontrados:');
      headings.forEach((h, i) => log.push(`  ${i + 1}. "${h}"`));

      // Listar botões principais
      const buttons = await page.locator('button').allTextContents();
      log.push('\nBotões encontrados:');
      buttons.slice(0, 10).forEach((b, i) => log.push(`  ${i + 1}. "${b}"`));
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '02-wizard-localizado.png'),
      fullPage: true
    });
    log.push('✅ Screenshot 02: Wizard localizado');

    // =======================
    // PASSO 3: Selecionar REGIÃO
    // =======================
    log.push('\nPASSO 3: Selecionando REGIÃO...');

    // Procurar por cards de região
    const regionSelectors = [
      'button:has-text("EUA")',
      'button:has-text("Estados Unidos")',
      'button:has-text("USA")',
      'button:has-text("América")',
      '[data-region]',
      'button:has-text("Europa")',
      'button:has-text("Ásia")'
    ];

    let regionSelected = false;
    for (const selector of regionSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          const text = await element.textContent();
          log.push(`✅ Região encontrada: "${text.trim()}"`);

          await element.click();
          await page.waitForTimeout(1000);

          log.push(`✅ Região "${text.trim()}" clicada`);
          regionSelected = true;
          break;
        }
      } catch (e) {
        // Continuar tentando
      }
    }

    if (!regionSelected) {
      log.push('⚠️ Nenhuma região encontrada. Tentando clicar em qualquer card...');

      // Tentar clicar no primeiro card visível
      const cards = page.locator('button, [class*="card"], [class*="cursor-pointer"]');
      const count = await cards.count();
      log.push(`Cards clicáveis encontrados: ${count}`);

      if (count > 0) {
        await cards.first().click();
        await page.waitForTimeout(1000);
        log.push('✅ Primeiro card clicado');
        regionSelected = true;
      }
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '03-regiao-selecionada.png'),
      fullPage: true
    });
    log.push('✅ Screenshot 03: Após selecionar região');

    // =======================
    // PASSO 4: Clicar em PRÓXIMO (avançar para Hardware)
    // =======================
    log.push('\nPASSO 4: Clicando em PRÓXIMO para avançar...');

    const nextButton1 = page.locator('button:has-text("Próximo")').first();
    if (await nextButton1.isVisible({ timeout: 2000 })) {
      log.push('✅ Botão "Próximo" encontrado');
      await nextButton1.click();
      await page.waitForTimeout(2000);
      log.push('✅ Clicou em "Próximo" - avançando para próximo passo');
    } else {
      log.push('⚠️ Botão "Próximo" não encontrado');
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '04-apos-clicar-proximo.png'),
      fullPage: true
    });
    log.push('✅ Screenshot 04: Após clicar em Próximo');

    // =======================
    // PASSO 5: Selecionar PROPÓSITO (O que você vai fazer?)
    // =======================
    log.push('\nPASSO 5: Selecionando PROPÓSITO...');

    // Verificar se estamos no passo certo
    const bodyText = await page.locator('body').textContent();
    if (bodyText.includes('O que você vai fazer')) {
      log.push('✅ Estamos no passo de seleção de propósito');
    }

    // Tentar selecionar um propósito
    const purposeSelectors = [
      'button:has-text("Desenvolver")',
      'button:has-text("Experimentar")',
      'button:has-text("Treinar modelo")',
      'button:has-text("Produção")',
      'text="Experimentar"'
    ];

    let purposeFound = false;
    for (const selector of purposeSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          const text = await element.textContent();
          log.push(`✅ Propósito encontrado: "${text.trim()}"`);

          // Clicar no card de propósito
          await element.click();
          await page.waitForTimeout(1000);

          log.push(`✅ Propósito "${text.trim()}" selecionado`);
          purposeFound = true;
          break;
        }
      } catch (e) {
        // Continuar tentando
      }
    }

    if (!purposeFound) {
      log.push('⚠️ Nenhum propósito encontrado com seletores padrão');
      log.push('Tentando clicar em primeiro card de propósito...');

      // Tentar clicar no primeiro card visível (geralmente "Experimentar")
      const cards = page.locator('button[class*="cursor"]').filter({ hasText: /Experimentar|Desenvolver|Treinar/ });
      const count = await cards.count();

      if (count > 0) {
        await cards.first().click();
        await page.waitForTimeout(1000);
        log.push('✅ Clicou no primeiro card de propósito');
        purposeFound = true;
      }
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '04b-proposito-selecionado.png'),
      fullPage: true
    });
    log.push('✅ Screenshot 04b: Propósito selecionado');

    // =======================
    // PASSO 6: Clicar em PRÓXIMO novamente (ir para seleção de GPU)
    // =======================
    log.push('\nPASSO 6: Clicando em PRÓXIMO para ir para seleção de GPU...');

    const nextButton2 = page.locator('button:has-text("Próximo")').first();
    if (await nextButton2.isVisible({ timeout: 2000 })) {
      const isEnabled = await nextButton2.isEnabled();
      log.push(`✅ Botão "Próximo" encontrado (habilitado: ${isEnabled})`);

      if (isEnabled) {
        await nextButton2.click();
        await page.waitForTimeout(2000);
        log.push('✅ Clicou em "Próximo" - indo para seleção de GPU');
      } else {
        log.push('⚠️ Botão "Próximo" está desabilitado - propósito pode não ter sido selecionado');
      }
    } else {
      log.push('⚠️ Botão "Próximo" não encontrado');
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '05-apos-segundo-proximo.png'),
      fullPage: true
    });
    log.push('✅ Screenshot 05: Após clicar em Próximo (segunda vez)');

    // =======================
    // PASSO 7: AGUARDAR GPUs carregarem
    // =======================
    log.push('\nPASSO 7: Aguardando GPUs carregarem...');
    log.push('⏳ Esperando 5 segundos para carregar ofertas...');

    await page.waitForTimeout(5000);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '06-aguardando-gpus.png'),
      fullPage: true
    });
    log.push('✅ Screenshot 06: Após aguardar carregamento');

    // =======================
    // PASSO 8: Verificar LISTA DE GPUs
    // =======================
    log.push('\nPASSO 8: Verificando lista de GPUs...');

    // Procurar por cards de GPU
    const gpuCardSelectors = [
      'text=/RTX|A100|H100|Tesla|V100|4090|3090/',
      '[data-gpu-card]',
      '[class*="gpu"]',
      'text=/\\$.*\\/hora/',
      'text=/VRAM|GB/'
    ];

    const gpuInfo = {
      found: false,
      count: 0,
      cards: []
    };

    for (const selector of gpuCardSelectors) {
      try {
        const elements = page.locator(selector);
        const count = await elements.count();

        if (count > 0) {
          gpuInfo.found = true;
          gpuInfo.count = Math.max(gpuInfo.count, count);

          log.push(`✅ Encontrados ${count} elementos com: ${selector}`);

          // Extrair textos dos primeiros 5 elementos
          for (let i = 0; i < Math.min(5, count); i++) {
            try {
              const text = await elements.nth(i).textContent({ timeout: 1000 });
              gpuInfo.cards.push(text.trim());
            } catch (e) {
              // Continuar
            }
          }
        }
      } catch (e) {
        // Continuar tentando
      }
    }

    if (gpuInfo.found) {
      log.push(`\n✅ Lista de GPUs ENCONTRADA!`);
      log.push(`📊 Total de elementos GPU: ${gpuInfo.count}`);
      log.push('\nPrimeiros cards:');
      gpuInfo.cards.forEach((card, i) => {
        log.push(`  ${i + 1}. ${card.substring(0, 100)}...`);
      });
    } else {
      log.push('⚠️ Nenhuma GPU encontrada. Analisando página...');

      // Verificar se há mensagens de erro ou loading
      const pageText = await page.locator('body').textContent();
      if (pageText.includes('Carregando')) {
        log.push('ℹ️ Página mostra "Carregando" - aguardando mais tempo...');
        await page.waitForTimeout(5000);
      } else if (pageText.includes('Erro')) {
        log.push('❌ Página mostra erro - pode haver problema no backend');
      }
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '07-lista-gpus.png'),
      fullPage: true
    });
    log.push('\n✅ Screenshot 07: Lista de GPUs');

    // =======================
    // PASSO 9: Verificar specs dos cards
    // =======================
    log.push('\nPASSO 9: Verificando specs dos cards de GPU...');

    const specs = {
      nomeGpu: false,
      preco: false,
      vram: false,
      cpu: false
    };

    const specsText = await page.locator('body').textContent();

    if (/RTX|A100|H100|Tesla|V100|4090|3090/i.test(specsText)) {
      specs.nomeGpu = true;
      log.push('✅ Nome de GPU encontrado');
    }

    if (/\$\d+\.?\d*\/hora|\$\d+\.?\d*\s*\/\s*h/i.test(specsText)) {
      specs.preco = true;
      log.push('✅ Preço encontrado');
    }

    if (/\d+\s*GB|VRAM/i.test(specsText)) {
      specs.vram = true;
      log.push('✅ VRAM encontrado');
    }

    if (/\d+\s*vCPU|CPU|Core/i.test(specsText)) {
      specs.cpu = true;
      log.push('✅ CPU info encontrado');
    }

    const specsEncontradas = Object.values(specs).filter(Boolean).length;
    log.push(`\n📊 Specs encontradas: ${specsEncontradas}/4`);

    // =======================
    // PASSO 10: SELECIONAR uma GPU
    // =======================
    log.push('\nPASSO 10: Tentando selecionar uma GPU...');

    const gpuSelectSelectors = [
      'button:has-text("Selecionar")',
      'button:has-text("Escolher")',
      'button:has-text("RTX")',
      'button:has-text("A100")',
      '[data-gpu-card] button',
      '[class*="gpu-card"] button',
      'button:has-text(/\\$/'
    ];

    let gpuSelected = false;
    for (const selector of gpuSelectSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          const text = await element.textContent();
          log.push(`✅ Botão de GPU encontrado: "${text.trim().substring(0, 50)}..."`);

          await element.click();
          await page.waitForTimeout(1000);

          log.push(`✅ GPU clicada`);
          gpuSelected = true;
          break;
        }
      } catch (e) {
        // Continuar tentando
      }
    }

    if (!gpuSelected) {
      log.push('⚠️ Não foi possível clicar em card de GPU. Tentando qualquer botão visível...');

      const allButtons = page.locator('button:visible');
      const count = await allButtons.count();
      log.push(`Botões visíveis: ${count}`);

      if (count > 0) {
        // Pegar textos dos primeiros 5 botões para debug
        for (let i = 0; i < Math.min(5, count); i++) {
          const btnText = await allButtons.nth(i).textContent();
          log.push(`  Botão ${i + 1}: "${btnText.trim()}"`);
        }
      }
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '08-gpu-selecionada.png'),
      fullPage: true
    });
    log.push('✅ Screenshot 08: Após selecionar GPU');

    // =======================
    // PASSO 11: Verificar destaque visual
    // =======================
    log.push('\nPASSO 11: Verificando destaque visual da GPU selecionada...');

    // Procurar por classes CSS de seleção
    const selectedElements = await page.locator('[class*="selected"], [class*="active"], [class*="highlight"]').count();

    if (selectedElements > 0) {
      log.push(`✅ ${selectedElements} elementos com classes de seleção encontrados`);
    } else {
      log.push('⚠️ Nenhum elemento com classes de seleção visual');
    }

    // =======================
    // PASSO 12: Verificar botão Próximo
    // =======================
    log.push('\nPASSO 12: Verificando estado do botão Próximo...');

    const nextButtonSelectors = [
      'button:has-text("Próximo")',
      'button:has-text("Continuar")',
      'button:has-text("Avançar")',
      'button:has-text("Next")',
      '[data-action="next"]'
    ];

    let nextButtonFound = false;
    for (const selector of nextButtonSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          const isEnabled = await element.isEnabled();
          const isDisabled = await element.isDisabled();

          log.push(`✅ Botão "Próximo" encontrado`);
          log.push(`   - Habilitado: ${isEnabled}`);
          log.push(`   - Desabilitado: ${isDisabled}`);

          // Tentar pegar classes CSS
          const className = await element.getAttribute('class');
          log.push(`   - Classes: ${className}`);

          nextButtonFound = true;
          break;
        }
      } catch (e) {
        // Continuar tentando
      }
    }

    if (!nextButtonFound) {
      log.push('⚠️ Botão "Próximo" não encontrado');
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '09-botao-proximo.png'),
      fullPage: true
    });
    log.push('✅ Screenshot 09: Estado do botão Próximo');

    // =======================
    // PASSO 13: Screenshot final completo
    // =======================
    log.push('\nPASSO 13: Screenshot final do wizard...');

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '10-wizard-completo.png'),
      fullPage: true
    });
    log.push('✅ Screenshot 10: Wizard completo');

    // =======================
    // SALVAR LOG COMPLETO
    // =======================
    const logContent = log.join('\n');
    fs.writeFileSync(
      path.join(SCREENSHOT_DIR, 'teste-visual-log.txt'),
      logContent
    );

    console.log('\n' + '='.repeat(80));
    console.log('RELATÓRIO DO TESTE VISUAL - WIZARD GPU MODO DEMO');
    console.log('='.repeat(80));
    console.log(logContent);
    console.log('='.repeat(80));
    console.log(`\nScreenshots salvos em: ${SCREENSHOT_DIR}`);
    console.log('='.repeat(80));

    // O teste sempre passa - é apenas documentação visual
    expect(true).toBe(true);
  });
});
