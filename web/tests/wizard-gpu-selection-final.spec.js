import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Wizard GPU Selection - Final Visual Test', () => {
  test('Should display GPU list and allow selection', async ({ page }) => {
    const screenshotsDir = path.join(__dirname, '..', 'screenshots');

    console.log('=== TESTE VISUAL DETALHADO - WIZARD GPU ===\n');

    // 1. Fazer login manual (auto_login não está funcionando 100%)
    console.log('1. Fazendo login...');
    await page.goto('http://localhost:4894/login');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Preencher email e senha
    const emailInput = page.locator('input[type="email"]').first();
    const passwordInput = page.locator('input[type="password"]').first();
    const loginButton = page.locator('button:has-text("Entrar")').first();

    await emailInput.fill('marcosremar@gmail.com');
    await passwordInput.fill('dumont123');
    await page.screenshot({ path: path.join(screenshotsDir, 'wizard-gpu-01-login-filled.png'), fullPage: true });

    await loginButton.click();
    console.log('Aguardando redirecionamento...');
    await page.waitForTimeout(5000);

    await page.screenshot({ path: path.join(screenshotsDir, 'wizard-gpu-02-after-login.png'), fullPage: true });

    const currentUrl = page.url();
    console.log(`URL atual: ${currentUrl}`);

    // Se não redirecionou para /app, tentar navegar manualmente
    if (!currentUrl.includes('/app')) {
      console.log('Navegando manualmente para /app...');
      await page.goto('http://localhost:4894/app');
      await page.waitForTimeout(3000);
    }

    await page.screenshot({ path: path.join(screenshotsDir, 'wizard-gpu-03-dashboard.png'), fullPage: true });
    console.log('✅ Login completo\n');

    // 2. Verificar se estamos no Dashboard (wizard)
    console.log('2. Analisando Dashboard/Wizard...');
    const pageContent = await page.content();

    // Salvar HTML para análise
    fs.writeFileSync(
      path.join(screenshotsDir, 'wizard-gpu-page-source.html'),
      pageContent
    );

    // Buscar por elementos do wizard
    const wizardKeywords = ['Região', 'Region', 'EUA', 'USA', 'GPU', 'Wizard', 'Assistente'];
    const foundKeywords = wizardKeywords.filter(kw => pageContent.includes(kw));
    console.log(`Palavras-chave encontradas: ${foundKeywords.join(', ') || 'Nenhuma'}`);

    // 3. Procurar e clicar em botões de navegação do wizard
    console.log('\n3. Navegando pelo wizard...');

    // Procurar botão de região/EUA
    const possibleRegionSelectors = [
      'button:has-text("EUA")',
      'button:has-text("USA")',
      'div:has-text("EUA")',
      '[data-region]',
      '[role="button"]:has-text("EUA")'
    ];

    let regionClicked = false;
    for (const selector of possibleRegionSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 1000 })) {
          console.log(`Clicando em região: ${selector}`);
          await element.click();
          await page.waitForTimeout(1000);
          regionClicked = true;
          break;
        }
      } catch (e) {
        // Continuar tentando
      }
    }

    await page.screenshot({ path: path.join(screenshotsDir, 'wizard-gpu-04-after-region.png'), fullPage: true });
    console.log(`Região clicada: ${regionClicked ? '✅' : '❌'}`);

    // Procurar botão "Próximo"
    const nextSelectors = [
      'button:has-text("Próximo")',
      'button:has-text("Next")',
      'button:has-text("Continuar")',
      'button[type="submit"]'
    ];

    for (const selector of nextSelectors) {
      try {
        const btn = page.locator(selector).first();
        if (await btn.isVisible({ timeout: 1000 })) {
          console.log(`Clicando em: ${selector}`);
          await btn.click();
          await page.waitForTimeout(2000);
          break;
        }
      } catch (e) {
        // Continuar
      }
    }

    await page.screenshot({ path: path.join(screenshotsDir, 'wizard-gpu-05-step2.png'), fullPage: true });

    // 4. Selecionar propósito (se houver)
    console.log('\n4. Selecionando propósito...');

    const purposeKeywords = ['Machine Learning', 'Deep Learning', 'Treinamento', 'Training', 'Inferência'];
    for (const kw of purposeKeywords) {
      try {
        const element = page.locator(`button:has-text("${kw}"), div:has-text("${kw}")`).first();
        if (await element.isVisible({ timeout: 1000 })) {
          console.log(`Selecionando: ${kw}`);
          await element.click();
          await page.waitForTimeout(1000);
          break;
        }
      } catch (e) {
        // Continuar
      }
    }

    await page.screenshot({ path: path.join(screenshotsDir, 'wizard-gpu-06-after-purpose.png'), fullPage: true });

    // Clicar em próximo novamente
    for (const selector of nextSelectors) {
      try {
        const btn = page.locator(selector).first();
        if (await btn.isVisible({ timeout: 1000 })) {
          await btn.click();
          await page.waitForTimeout(2000);
          break;
        }
      } catch (e) {
        // Continuar
      }
    }

    await page.screenshot({ path: path.join(screenshotsDir, 'wizard-gpu-07-step3.png'), fullPage: true });

    // 5. *** FOCO PRINCIPAL: Lista de GPUs ***
    console.log('\n5. *** AGUARDANDO LISTA DE GPUs ***');
    await page.waitForTimeout(5000); // Aguardar carregar GPUs da API

    await page.screenshot({
      path: path.join(screenshotsDir, 'wizard-gpu-08-GPU-LIST-CRITICAL.png'),
      fullPage: true
    });
    console.log('📸 SCREENSHOT CRÍTICO DA LISTA DE GPUs SALVO');

    // 6. Analisar GPUs na página
    console.log('\n6. Analisando GPUs na página...');

    const currentContent = await page.content();

    // Procurar por indicadores de GPU
    const gpuPatterns = [
      /RTX\s*\d{4}/gi,
      /GeForce/gi,
      /Tesla/gi,
      /A100/gi,
      /H100/gi,
      /\$\s*[\d.]+\/h/gi,
      /VRAM.*\d+\s*GB/gi
    ];

    const gpuMatches = {};
    for (const pattern of gpuPatterns) {
      const matches = currentContent.match(pattern) || [];
      if (matches.length > 0) {
        gpuMatches[pattern.source] = matches.slice(0, 5); // Primeiros 5
      }
    }

    console.log('GPUs encontradas:', JSON.stringify(gpuMatches, null, 2));

    // Contar cards/containers visíveis
    const cardSelectors = [
      '[class*="card"]',
      '[class*="offer"]',
      '[class*="gpu"]',
      '[class*="rounded"][class*="border"]'
    ];

    let maxCardCount = 0;
    for (const selector of cardSelectors) {
      const count = await page.locator(selector).count();
      if (count > maxCardCount) {
        maxCardCount = count;
        console.log(`Encontrado ${count} elementos com seletor: ${selector}`);
      }
    }

    console.log(`\n📊 TOTAL ESTIMADO DE CARDS: ${maxCardCount}`);

    // 7. Verificar estrutura de um card específico
    console.log('\n7. Verificando estrutura dos cards...');

    // Procurar por cards que contenham informações de GPU
    const gpuCards = page.locator('text=/RTX|GeForce|A100|H100/i').locator('..').locator('..');

    const cardCount = await gpuCards.count();
    console.log(`Cards com nomes de GPU: ${cardCount}`);

    if (cardCount > 0) {
      const firstCard = gpuCards.first();
      const cardText = await firstCard.textContent();
      console.log(`\n🔍 Primeiro card encontrado:\n${cardText.substring(0, 200)}...`);

      // Verificar elementos
      const hasGpuName = /RTX|GeForce|Tesla|A100|H100/i.test(cardText);
      const hasPrice = /\$|USD|\/h/i.test(cardText);
      const hasVRAM = /VRAM|GB/i.test(cardText);
      const hasLocation = /US|CA|EU|Asia/i.test(cardText);

      console.log('\nElementos no card:');
      console.log(`  - Nome GPU: ${hasGpuName ? '✅' : '❌'}`);
      console.log(`  - Preço: ${hasPrice ? '✅' : '❌'}`);
      console.log(`  - VRAM: ${hasVRAM ? '✅' : '❌'}`);
      console.log(`  - Localização: ${hasLocation ? '✅' : '❌'}`);

      // 8. Tentar clicar em uma GPU
      console.log('\n8. Tentando clicar em GPU...');

      await firstCard.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);

      await page.screenshot({
        path: path.join(screenshotsDir, 'wizard-gpu-09-before-click.png'),
        fullPage: true
      });

      try {
        await firstCard.click();
        console.log('✅ Clique realizado');
        await page.waitForTimeout(1500);
      } catch (error) {
        console.log(`❌ Erro ao clicar: ${error.message}`);
      }

      await page.screenshot({
        path: path.join(screenshotsDir, 'wizard-gpu-10-after-click.png'),
        fullPage: true
      });

      // 9. Verificar seleção
      console.log('\n9. Verificando seleção...');

      const selectedElements = await page.locator('[class*="selected"], [aria-selected="true"]').count();
      console.log(`Elementos com indicador de seleção: ${selectedElements}`);

      // 10. Verificar botão Próximo
      console.log('\n10. Verificando botão Próximo...');

      for (const selector of nextSelectors) {
        try {
          const btn = page.locator(selector).first();
          if (await btn.isVisible({ timeout: 1000 })) {
            const isEnabled = await btn.isEnabled();
            console.log(`${selector}: ${isEnabled ? 'HABILITADO ✅' : 'DESABILITADO ❌'}`);
          }
        } catch (e) {
          // Ignorar
        }
      }

    } else {
      console.log('❌ NENHUM CARD DE GPU ENCONTRADO!');
      console.log('Possíveis causas:');
      console.log('  1. API não está retornando ofertas');
      console.log('  2. Componente não está renderizando os cards');
      console.log('  3. Ainda não navegou até a etapa de seleção de GPU');
    }

    // Screenshot final
    await page.screenshot({
      path: path.join(screenshotsDir, 'wizard-gpu-11-final.png'),
      fullPage: true
    });

    console.log('\n=== RESUMO ===');
    console.log(`GPUs detectadas no HTML: ${Object.keys(gpuMatches).length > 0 ? '✅' : '❌'}`);
    console.log(`Cards encontrados: ${cardCount}`);
    console.log(`Screenshots salvos: 11`);
    console.log(`Diretório: ${screenshotsDir}`);
    console.log('\n=== TESTE CONCLUÍDO ===');
  });
});
