// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * TESTE COMPLETO DO WIZARD DE GPU RESERVA
 *
 * Roteiro:
 * 1. Navegue para http://localhost:4898/demo-app (LIMPE localStorage antes)
 * 2. Tire um snapshot inicial
 * 3. Clique no botão "EUA"
 * 4. Tire um snapshot para ver se "EUA" foi selecionado (badge deve aparecer)
 * 5. Clique em "Próximo"
 * 6. Tire um snapshot - deve estar no Step 2 (Hardware)
 * 7. Clique em "Desenvolver"
 * 8. Aguarde 2s para as máquinas carregarem
 * 9. Tire um snapshot - deve mostrar as máquinas recomendadas
 * 10. Clique na primeira máquina
 * 11. Clique em "Próximo"
 * 12. Deve ir para Step 3 (Estratégia)
 * 13. Clique em "Iniciar"
 * 14. Aguarde 20s pelo provisionamento
 * 15. Tire snapshot final
 */

test.describe('Wizard Completo - GPU Reserva', () => {
  test.beforeEach(async ({ page }) => {
    // Limpar localStorage antes de cada teste
    await page.goto('http://localhost:4898/demo-app');
    await page.evaluate(() => localStorage.clear());
    console.log('✅ localStorage limpo');
  });

  test('Fluxo completo do wizard de reserva', async ({ page }) => {
    // STEP 1: Navegar para demo-app
    console.log('\n📍 STEP 1: Navegando para /demo-app...');
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // STEP 2: Snapshot inicial
    console.log('\n📸 STEP 2: Tirando snapshot inicial...');
    await page.screenshot({
      path: 'test-results/wizard-step-01-inicial.png',
      fullPage: true
    });

    // Verificar que o wizard está visível
    const wizardVisible = await page.locator('[role="dialog"], .wizard, [class*="wizard"]').isVisible().catch(() => false);
    console.log(`Wizard visível: ${wizardVisible}`);

    // STEP 3: Clicar no botão "EUA"
    console.log('\n🖱️  STEP 3: Clicando no botão "EUA"...');

    // Procurar botão com texto "EUA" ou "USA"
    const usaButton = page.locator('button:has-text("EUA"), button:has-text("USA")').first();
    const usaButtonVisible = await usaButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!usaButtonVisible) {
      console.log('⚠️ Botão EUA não encontrado. Verificando conteúdo da página...');
      const pageText = await page.locator('body').textContent();
      console.log('Conteúdo da página:', pageText?.substring(0, 500));

      // Tentar encontrar qualquer botão de região
      const regionButtons = await page.locator('button').all();
      console.log(`Total de botões na página: ${regionButtons.length}`);

      for (let i = 0; i < Math.min(5, regionButtons.length); i++) {
        const btnText = await regionButtons[i].textContent();
        console.log(`Botão ${i + 1}: "${btnText}"`);
      }
    }

    await expect(usaButton).toBeVisible({ timeout: 10000 });
    await usaButton.click();
    await page.waitForTimeout(1000);
    console.log('✅ Clicou em "EUA"');

    // STEP 4: Snapshot após seleção de EUA (badge deve aparecer)
    console.log('\n📸 STEP 4: Verificando se "EUA" foi selecionado...');
    await page.screenshot({
      path: 'test-results/wizard-step-02-eua-selecionado.png',
      fullPage: true
    });

    // Verificar se o badge/indicador de seleção apareceu
    const selectedBadge = await page.locator('[class*="selected"], [aria-pressed="true"], [class*="active"]').count();
    console.log(`Elementos com indicador de seleção: ${selectedBadge}`);

    // STEP 5: Aguardar botão Próximo ficar habilitado e clicar
    console.log('\n🖱️  STEP 5: Aguardando botão "Próximo" ficar habilitado...');
    const nextButton = page.locator('button:has-text("Próximo"), button:has-text("Next")').first();

    // Aguardar botão ficar visível
    await expect(nextButton).toBeVisible({ timeout: 5000 });

    // Aguardar botão ficar habilitado (não ter atributo disabled)
    await page.waitForFunction(
      () => {
        // Procurar botão que contém o texto "Próximo"
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b =>
          b.textContent.includes('Próximo') || b.textContent.includes('Next')
        );
        return btn && !btn.disabled && !btn.hasAttribute('disabled');
      },
      { timeout: 10000 }
    );

    console.log('✅ Botão "Próximo" habilitado!');
    await nextButton.click();
    await page.waitForTimeout(1500);
    console.log('✅ Clicou em "Próximo"');

    // STEP 6: Snapshot do Step 2 (Hardware)
    console.log('\n📸 STEP 6: Verificando Step 2 (Hardware)...');

    // Aguardar transição para Step 2 (verificar que o indicador 2/4 está ativo)
    await page.waitForSelector('button[class*="2/4"]:not([disabled])', { timeout: 10000 }).catch(() => {
      console.log('⚠️ Step 2 não ficou ativo. Verificando estado atual...');
    });

    await page.screenshot({
      path: 'test-results/wizard-step-03-hardware.png',
      fullPage: true
    });

    // Verificar se estamos no step 2 (Hardware)
    const step2Active = await page.locator('text="2/4"').isVisible().catch(() => false);
    console.log(`Step 2 visível: ${step2Active}`);

    // STEP 7: Clicar em "Desenvolver"
    console.log('\n🖱️  STEP 7: Procurando botão "Desenvolver"...');

    // Aguardar os botões de caso de uso aparecerem
    await page.waitForTimeout(1000);

    const desenvolverButton = page.locator('button:has-text("Desenvolver")').first();

    const desenvolverVisible = await desenvolverButton.isVisible({ timeout: 5000 }).catch(() => false);
    if (!desenvolverVisible) {
      console.log('⚠️ Botão "Desenvolver" não encontrado. Procurando alternativas...');
      const buttons = await page.locator('button').all();
      for (let i = 0; i < Math.min(15, buttons.length); i++) {
        const btnText = await buttons[i].textContent();
        if (btnText) console.log(`Botão ${i + 1}: "${btnText.substring(0, 50)}"`);
      }
    }

    await expect(desenvolverButton).toBeVisible({ timeout: 10000 });
    console.log('✅ Botão "Desenvolver" encontrado!');
    await desenvolverButton.click();
    console.log('✅ Clicou em "Desenvolver"');

    // STEP 8: Aguardar 2s para as máquinas carregarem
    console.log('\n⏳ STEP 8: Aguardando máquinas carregarem (2s)...');
    await page.waitForTimeout(2000);

    // STEP 9: Snapshot com máquinas recomendadas
    console.log('\n📸 STEP 9: Verificando máquinas recomendadas...');
    await page.screenshot({
      path: 'test-results/wizard-step-04-maquinas.png',
      fullPage: true
    });

    // Verificar se há máquinas listadas
    const machineCards = await page.locator('[class*="machine"], [class*="card"], [role="listitem"]').count();
    console.log(`Máquinas encontradas: ${machineCards}`);

    // STEP 10: Clicar na primeira máquina
    console.log('\n🖱️  STEP 10: Clicando na primeira máquina...');

    // Tentar diferentes seletores para encontrar a primeira máquina
    let machineClicked = false;

    const selectors = [
      '[class*="machine"]:first-of-type button, [class*="machine"]:first-of-type',
      '[class*="card"]:first-of-type button, [class*="card"]:first-of-type',
      '[role="listitem"]:first-of-type button, [role="listitem"]:first-of-type',
      'button:has-text("Selecionar")',
      'button:has-text("Select")'
    ];

    for (const selector of selectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
        await element.click();
        machineClicked = true;
        console.log(`✅ Clicou na máquina usando seletor: ${selector}`);
        break;
      }
    }

    if (!machineClicked) {
      console.log('⚠️ Não conseguiu clicar em nenhuma máquina. Procurando elementos clicáveis...');
      const clickables = await page.locator('button, [role="button"], [class*="clickable"]').all();
      console.log(`Total de elementos clicáveis: ${clickables.length}`);
    }

    await page.waitForTimeout(1000);

    // STEP 11: Clicar em "Próximo"
    console.log('\n🖱️  STEP 11: Clicando em "Próximo" novamente...');
    const nextButton2 = page.locator('button:has-text("Próximo"), button:has-text("Next")').first();
    await expect(nextButton2).toBeVisible({ timeout: 5000 });
    await nextButton2.click();
    await page.waitForTimeout(1500);
    console.log('✅ Clicou em "Próximo"');

    // STEP 12: Verificar Step 3 (Estratégia)
    console.log('\n📸 STEP 12: Verificando Step 3 (Estratégia)...');
    await page.screenshot({
      path: 'test-results/wizard-step-05-estrategia.png',
      fullPage: true
    });

    const step3Visible = await page.locator('text=/step 3|estratégia|strategy|iniciar/i').isVisible().catch(() => false);
    console.log(`Step 3 visível: ${step3Visible}`);

    // STEP 13: Clicar em "Iniciar"
    console.log('\n🖱️  STEP 13: Clicando em "Iniciar"...');
    const iniciarButton = page.locator('button:has-text("Iniciar"), button:has-text("Start"), button:has-text("Launch")').first();

    const iniciarVisible = await iniciarButton.isVisible({ timeout: 5000 }).catch(() => false);
    if (!iniciarVisible) {
      console.log('⚠️ Botão "Iniciar" não encontrado. Procurando alternativas...');
      const buttons = await page.locator('button').all();
      for (let i = 0; i < Math.min(10, buttons.length); i++) {
        const btnText = await buttons[i].textContent();
        console.log(`Botão ${i + 1}: "${btnText}"`);
      }
    }

    await expect(iniciarButton).toBeVisible({ timeout: 10000 });
    await iniciarButton.click();
    console.log('✅ Clicou em "Iniciar"');

    // STEP 14: Aguardar 20s pelo provisionamento
    console.log('\n⏳ STEP 14: Aguardando provisionamento (20s)...');
    await page.waitForTimeout(20000);

    // STEP 15: Snapshot final
    console.log('\n📸 STEP 15: Tirando snapshot final...');
    await page.screenshot({
      path: 'test-results/wizard-step-06-final.png',
      fullPage: true
    });

    // Verificar estado final
    const finalText = await page.locator('body').textContent();
    console.log('\n📊 Estado final da página:');
    console.log('- Contém "provisionamento":', finalText?.toLowerCase().includes('provisionamento'));
    console.log('- Contém "sucesso":', finalText?.toLowerCase().includes('sucesso'));
    console.log('- Contém "erro":', finalText?.toLowerCase().includes('erro'));

    console.log('\n✅ TESTE COMPLETO FINALIZADO!');
    console.log('📁 Screenshots salvos em: test-results/wizard-step-*.png');
  });
});
