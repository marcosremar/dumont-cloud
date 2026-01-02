const { test, expect } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

/**
 * TESTE SIMPLIFICADO - DATA ATTRIBUTES GPU
 *
 * Foco: Verificar se os cards de GPU têm os data attributes corretos
 */
test.describe('Wizard GPU - Data Attributes Test', () => {
  test('Deve verificar data attributes nos cards de GPU', async ({ page }) => {
    const screenshotsDir = path.join(__dirname, '..', 'screenshots');

    console.log('\n========================================');
    console.log('TESTE DATA ATTRIBUTES - GPU CARDS');
    console.log('========================================\n');

    // PASSO 1: Navegar direto para demo-app
    console.log('PASSO 1: Navegando para /demo-app');
    await page.goto('http://localhost:4894/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: path.join(screenshotsDir, 'gpu-attr-01-initial.png'),
      fullPage: true
    });
    console.log('📸 Screenshot salvo: gpu-attr-01-initial.png\n');

    // PASSO 2: Selecionar região EUA
    console.log('PASSO 2: Selecionando região EUA');
    const euaButton = page.locator('button:has-text("EUA")').first();
    await euaButton.click();
    await page.waitForTimeout(1000);
    console.log('✅ Região selecionada\n');

    // Clicar em Próximo
    const proximoBtn1 = page.locator('button:has-text("Próximo")').first();
    await proximoBtn1.click();
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: path.join(screenshotsDir, 'gpu-attr-02-step2.png'),
      fullPage: true
    });

    // PASSO 3: Selecionar propósito (qualquer um)
    console.log('PASSO 3: Selecionando propósito');

    // Tentar clicar no primeiro card visível de propósito
    const purposeCards = page.locator('[class*="rounded"]').filter({ hasText: /CPU|Experimentar|Desenvolver|Treinar|Produção/i });
    const firstPurpose = purposeCards.first();

    if (await firstPurpose.isVisible({ timeout: 2000 })) {
      await firstPurpose.click();
      await page.waitForTimeout(1000);
      console.log('✅ Propósito selecionado\n');
    } else {
      console.log('⚠️ Nenhum card de propósito encontrado - continuando...\n');
    }

    // Clicar em Próximo novamente
    const proximoBtn2 = page.locator('button:has-text("Próximo")').first();
    if (await proximoBtn2.isVisible({ timeout: 2000 })) {
      await proximoBtn2.click();
      await page.waitForTimeout(2000);
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'gpu-attr-03-before-gpus.png'),
      fullPage: true
    });

    // PASSO 4: AGUARDAR GPUs CARREGAREM
    console.log('PASSO 4: Aguardando GPUs carregarem...');
    console.log('Esperando até 20 segundos pela lista de GPUs...\n');

    let gpusCarregadas = false;
    let tentativas = 0;

    while (!gpusCarregadas && tentativas < 20) {
      tentativas++;
      await page.waitForTimeout(1000);

      // Verificar se há cards com data-gpu-card
      const countDataAttr = await page.locator('[data-gpu-card="true"]').count();

      // Ou verificar por texto de GPU
      const countByText = await page.locator('text=/RTX|A100|H100|Tesla|GeForce/i').count();

      console.log(`[${tentativas}s] data-gpu-card: ${countDataAttr} | GPUs por texto: ${countByText}`);

      if (countDataAttr > 0 || countByText > 0) {
        gpusCarregadas = true;
        console.log(`\n✅ GPUs detectadas após ${tentativas} segundos!\n`);
        break;
      }
    }

    // Screenshot CRÍTICO quando GPUs aparecerem (ou timeout)
    await page.screenshot({
      path: path.join(screenshotsDir, 'gpu-attr-04-GPU-LIST-CRITICAL.png'),
      fullPage: true
    });
    console.log('📸 Screenshot CRÍTICO: gpu-attr-04-GPU-LIST-CRITICAL.png\n');

    // PASSO 5: VERIFICAR DATA ATTRIBUTES
    console.log('========================================');
    console.log('PASSO 5: VERIFICANDO DATA ATTRIBUTES');
    console.log('========================================\n');

    const gpuCardsWithDataAttr = page.locator('[data-gpu-card="true"]');
    const cardCount = await gpuCardsWithDataAttr.count();

    console.log(`Total de cards com [data-gpu-card="true"]: ${cardCount}\n`);

    if (cardCount === 0) {
      console.log('❌ ERRO: Nenhum card com data-gpu-card="true" encontrado!\n');

      // Debug: salvar HTML
      const html = await page.content();
      fs.writeFileSync(
        path.join(screenshotsDir, 'gpu-attr-page-source.html'),
        html
      );
      console.log('HTML salvo em: gpu-attr-page-source.html\n');

      // Verificar se há GPUs sem data attributes
      const gpuByText = await page.locator('text=/RTX\\s*\\d{4}/i').count();
      console.log(`GPUs encontradas por texto (sem data attr): ${gpuByText}\n`);

      if (gpuByText > 0) {
        console.log('⚠️ PROBLEMA: GPUs existem mas NÃO TÊM data attributes!\n');
        console.log('Ação necessária: Adicionar data-gpu-card, data-gpu-name, data-selected aos cards\n');
      }

    } else {
      console.log('✅ Cards com data attributes encontrados!\n');

      // Analisar primeiros 3 cards
      for (let i = 0; i < Math.min(cardCount, 3); i++) {
        const card = gpuCardsWithDataAttr.nth(i);

        const gpuName = await card.getAttribute('data-gpu-name');
        const isSelected = await card.getAttribute('data-selected');
        const cardText = await card.textContent();

        console.log(`Card ${i + 1}:`);
        console.log(`  ✓ data-gpu-card: true`);
        console.log(`  ✓ data-gpu-name: ${gpuName || 'AUSENTE'}`);
        console.log(`  ✓ data-selected: ${isSelected || 'AUSENTE'}`);
        console.log(`  ✓ Texto: ${cardText.substring(0, 80).replace(/\s+/g, ' ').trim()}...`);
        console.log('');
      }

      // PASSO 6: TESTAR SELEÇÃO
      console.log('========================================');
      console.log('PASSO 6: TESTANDO SELEÇÃO DE GPU');
      console.log('========================================\n');

      const firstCard = gpuCardsWithDataAttr.first();

      // Estado antes do clique
      const selectedBefore = await firstCard.getAttribute('data-selected');
      console.log(`Estado ANTES do clique: data-selected="${selectedBefore}"\n`);

      // Screenshot antes
      await page.screenshot({
        path: path.join(screenshotsDir, 'gpu-attr-05-before-click.png'),
        fullPage: true
      });

      // CLICAR
      await firstCard.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);

      console.log('🖱️ Clicando no primeiro card...\n');
      await firstCard.click();
      await page.waitForTimeout(1500);

      // Estado depois do clique
      const selectedAfter = await firstCard.getAttribute('data-selected');
      console.log(`Estado DEPOIS do clique: data-selected="${selectedAfter}"\n`);

      if (selectedBefore !== selectedAfter) {
        console.log(`✅ SUCESSO! data-selected mudou: "${selectedBefore}" → "${selectedAfter}"\n`);
      } else {
        console.log(`⚠️ AVISO: data-selected NÃO mudou (manteve "${selectedAfter}")\n`);
      }

      // Screenshot depois
      await page.screenshot({
        path: path.join(screenshotsDir, 'gpu-attr-06-after-click.png'),
        fullPage: true
      });

      // PASSO 7: Verificar botão Próximo habilitado
      console.log('========================================');
      console.log('PASSO 7: VERIFICANDO BOTÃO PRÓXIMO');
      console.log('========================================\n');

      const nextBtn = page.locator('button:has-text("Próximo")').first();

      if (await nextBtn.isVisible({ timeout: 2000 })) {
        const isEnabled = await nextBtn.isEnabled();
        console.log(`Botão "Próximo": ${isEnabled ? 'HABILITADO ✅' : 'DESABILITADO ❌'}\n`);

        if (isEnabled) {
          console.log('🖱️ Clicando em "Próximo"...\n');
          await nextBtn.click();
          await page.waitForTimeout(2000);

          await page.screenshot({
            path: path.join(screenshotsDir, 'gpu-attr-07-after-next.png'),
            fullPage: true
          });
          console.log('✅ Wizard avançou!\n');
        }
      }
    }

    // Screenshot final
    await page.screenshot({
      path: path.join(screenshotsDir, 'gpu-attr-08-final.png'),
      fullPage: true
    });

    // RESUMO
    console.log('========================================');
    console.log('RESUMO DO TESTE');
    console.log('========================================');
    console.log(`Cards com [data-gpu-card="true"]: ${cardCount}`);
    console.log(`GPUs carregadas: ${gpusCarregadas ? 'SIM ✅' : 'NÃO ❌'}`);
    console.log(`Screenshots salvos: 8+`);
    console.log(`Diretório: ${screenshotsDir}`);
    console.log('========================================\n');

    // Asserção
    if (cardCount > 0) {
      expect(cardCount).toBeGreaterThan(0);
      console.log('✅ TESTE PASSOU\n');
    } else {
      console.log('❌ TESTE FALHOU - Nenhum card com data attributes\n');
      throw new Error('Nenhum card de GPU com data-gpu-card="true" encontrado');
    }
  });
});
