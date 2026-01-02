#!/usr/bin/env node
/**
 * Teste completo de reserva de GPU pelo wizard
 * - Abre wizard "Nova Máquina"
 * - Seleciona região, propósito, tier
 * - Tenta fazer reserva
 * - Captura erros
 */

const { chromium } = require('playwright');

const BASE_URL = 'http://localhost:4895';
const SCREENSHOTS_DIR = './screenshots';

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runReservationTest() {
  console.log('🚀 Teste de Reserva de GPU pelo Wizard');
  console.log('⚠️  Este teste vai tentar reservar uma GPU REAL\n');

  const browser = await chromium.launch({
    headless: false,
    slowMo: 150
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  // Capture console messages
  const consoleErrors = [];
  const consoleLogs = [];
  page.on('console', msg => {
    const text = msg.text();
    const type = msg.type();
    if (type === 'error') {
      consoleErrors.push(text);
    }
    // Print ALL console output during test
    console.log(`   [BROWSER ${type}]`, text.substring(0, 300));
    consoleLogs.push(text);
  });

  // Capture network errors
  const networkErrors = [];
  page.on('requestfailed', request => {
    networkErrors.push(`${request.method()} ${request.url()} - ${request.failure().errorText}`);
  });

  try {
    // 1. Login
    console.log('📍 Step 1: Login');
    await page.goto(`${BASE_URL}/login?auto_login=demo`);

    // IMPORTANT: Set demo_mode in localStorage to bypass balance validation
    await page.evaluate(() => {
      localStorage.setItem('demo_mode', 'true');
    });

    await sleep(5000);
    console.log(`   URL: ${page.url()}`);

    // 2. Go to Machines page
    console.log('\n📍 Step 2: Navegando para Máquinas');
    await page.goto(`${BASE_URL}/app/machines`);
    await sleep(3000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-01-machines.png` });

    // 3. Click "Nova Máquina" button
    console.log('\n📍 Step 3: Abrindo wizard Nova Máquina');
    const novaButton = page.locator('text=Nova Máquina').first();
    if (await novaButton.count() > 0) {
      await novaButton.click();
      await sleep(2000);
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-02-wizard-open.png` });
      console.log('   ✅ Wizard aberto');
    } else {
      console.log('   ❌ Botão Nova Máquina não encontrado');
      return;
    }

    // 4. Step 1 - Select Region (EUA)
    console.log('\n📍 Step 4: Selecionando região EUA');
    const euaOption = page.locator('text=EUA').first();
    if (await euaOption.count() > 0) {
      await euaOption.click();
      await sleep(1000);
      console.log('   ✅ EUA selecionado');
    } else {
      console.log('   ⚠️ Opção EUA não encontrada, tentando Estados Unidos...');
      const usOption = page.locator('text=Estados Unidos').first();
      if (await usOption.count() > 0) {
        await usOption.click();
        await sleep(1000);
      }
    }

    // Click Next
    console.log('   Clicando Próximo...');
    const nextButton = page.locator('button:has-text("Próximo")').first();
    const isNextEnabled = await nextButton.isEnabled();
    console.log(`   Botão Próximo habilitado: ${isNextEnabled}`);

    if (isNextEnabled) {
      await nextButton.click();
      await sleep(2000);
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-03-step2.png` });
      console.log('   ✅ Avançou para Step 2');
    } else {
      console.log('   ❌ Botão Próximo desabilitado - precisa selecionar região');
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-error-step1.png` });
      return;
    }

    // 5. Step 2 - Select Purpose
    console.log('\n📍 Step 5: Selecionando propósito');

    // Try different purpose options
    const purposes = ['Desenvolver', 'Experimentar', 'Treinar', 'Produção'];
    let purposeSelected = false;

    for (const purpose of purposes) {
      const purposeOption = page.locator(`text=${purpose}`).first();
      if (await purposeOption.count() > 0) {
        await purposeOption.click();
        await sleep(1000);
        console.log(`   ✅ Propósito "${purpose}" selecionado`);
        purposeSelected = true;
        break;
      }
    }

    if (!purposeSelected) {
      console.log('   ⚠️ Nenhum propósito encontrado');
    }

    // Click Next
    console.log('   Clicando Próximo...');
    const nextButton2 = page.locator('button:has-text("Próximo")').first();
    const isNext2Enabled = await nextButton2.isEnabled();
    console.log(`   Botão Próximo habilitado: ${isNext2Enabled}`);

    if (isNext2Enabled) {
      await nextButton2.click();
      await sleep(3000);
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-04-step3.png` });
      console.log('   ✅ Avançou para Step 3 (Hardware)');
    } else {
      console.log('   ❌ Botão Próximo desabilitado');
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-error-step2.png` });
    }

    // 6. Step 3 - Select Tier/Hardware
    console.log('\n📍 Step 6: Selecionando tier de hardware');
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-05-tiers.png` });

    // Try to select a GPU tier (not "Apenas CPU")
    const tiers = ['Lento', 'Médio', 'Rápido', 'Ultra'];
    let tierSelected = false;

    for (const tier of tiers) {
      const tierOption = page.locator(`text=${tier}`).first();
      if (await tierOption.count() > 0) {
        await tierOption.click();
        await sleep(3000); // Wait for machines to load
        console.log(`   ✅ Tier "${tier}" selecionado`);
        tierSelected = true;
        await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-06-tier-selected.png` });
        break;
      }
    }

    if (!tierSelected) {
      console.log('   ⚠️ Nenhum tier encontrado, pode estar em modo diferente');
    }

    // 7. Wait for machines to load and select one
    console.log('\n📍 Step 7: Aguardando máquinas carregarem');
    await sleep(5000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-07-machines-loaded.png` });

    // Check page content for machines
    const pageContent = await page.content();
    const hasRTX = pageContent.includes('RTX');
    const hasPrice = pageContent.includes('$');
    const hasVRAM = pageContent.includes('VRAM') || pageContent.includes('GB');

    console.log(`   Mostrando GPUs (RTX): ${hasRTX}`);
    console.log(`   Mostrando preços ($): ${hasPrice}`);
    console.log(`   Mostrando VRAM: ${hasVRAM}`);

    // Try to click on a machine card
    console.log('\n📍 Step 8: Selecionando máquina');
    const machineCard = page.locator('[class*="card"]:has-text("RTX"), [class*="Card"]:has-text("$")').first();
    if (await machineCard.count() > 0) {
      await machineCard.click();
      await sleep(2000);
      console.log('   ✅ Máquina selecionada');
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-08-machine-selected.png` });
    } else {
      console.log('   ⚠️ Nenhum card de máquina encontrado');

      // Try alternative selector
      const anyClickable = page.locator('[data-testid*="machine"], .machine-option').first();
      if (await anyClickable.count() > 0) {
        await anyClickable.click();
        await sleep(2000);
      }
    }

    // 9. Select Strategy (IMPORTANT - this was missing!)
    console.log('\n📍 Step 9: Selecionando estratégia');
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-09-strategy.png` });

    // Try to select "Sem Failover" or "Tensor Dock Serverless"
    const strategies = ['Sem Failover', 'Tensor Dock Serverless'];
    let strategySelected = false;

    for (const strategy of strategies) {
      const strategyOption = page.locator(`text=${strategy}`).first();
      if (await strategyOption.count() > 0) {
        await strategyOption.click();
        await sleep(1500);
        console.log(`   ✅ Estratégia "${strategy}" selecionada`);
        strategySelected = true;
        await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-09b-strategy-selected.png` });
        break;
      }
    }

    if (!strategySelected) {
      console.log('   ⚠️ Nenhuma estratégia encontrada');
    }

    // 10. Look for final button
    console.log('\n📍 Step 10: Verificando botão Iniciar');
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-10-before-final.png` });

    // Check for "Iniciar" button - needs to be the actual button with Zap icon, not stepper
    // Use a more specific selector to avoid matching the stepper "Provisionar" step
    const finalButton = page.locator('button:has-text("Iniciar")').filter({ hasText: /^.*Iniciar$/ }).first();

    // If not found, try the button with exact text
    let buttonToClick = finalButton;
    if (await finalButton.count() === 0) {
      // Alternative: find button that contains Zap icon + Iniciar
      buttonToClick = page.locator('button >> text=Iniciar').last();
    }

    if (await buttonToClick.count() > 0) {
      const buttonText = await buttonToClick.innerText();
      const isFinalEnabled = await buttonToClick.isEnabled();
      console.log(`   Botão encontrado: "${buttonText.trim()}", habilitado: ${isFinalEnabled}`);

      if (isFinalEnabled) {
        console.log('   🚀 Clicando para iniciar reserva...');

        // Log what happens with more granularity
        console.log('   Waiting 500ms...');
        await sleep(500);
        console.log('   Now clicking...');
        await buttonToClick.click();
        console.log('   Clicked! Waiting 1s...');
        await sleep(1000);
        console.log('   Waiting more 4s...');
        await sleep(4000);
        await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-10-after-click.png` });

        // Check for provisioning status
        const provisioningContent = await page.content();
        const isProvisioning = provisioningContent.includes('Testando') ||
                               provisioningContent.includes('Provisionando') ||
                               provisioningContent.includes('Race') ||
                               provisioningContent.includes('aguard');

        console.log(`   Provisionamento iniciado: ${isProvisioning}`);

        if (isProvisioning) {
          console.log('   ✅ SUCESSO: Reserva iniciada!');
          await sleep(10000); // Wait to see progress
          await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-11-provisioning.png` });
        }
      } else {
        console.log('   ❌ Botão final desabilitado - falta selecionar algo');
      }
    } else {
      console.log('   ⚠️ Botão final não encontrado - pode precisar de mais passos');

      // Maybe need to click Next again
      const nextButton3 = page.locator('button:has-text("Próximo")').first();
      if (await nextButton3.count() > 0 && await nextButton3.isEnabled()) {
        console.log('   Tentando clicar Próximo novamente...');
        await nextButton3.click();
        await sleep(3000);
        await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-09b-after-next.png` });
      }
    }

    // 10. Report errors
    console.log('\n' + '='.repeat(50));
    console.log('📊 RELATÓRIO DE ERROS');
    console.log('='.repeat(50));

    if (consoleErrors.length > 0) {
      console.log('\n❌ Erros de Console:');
      consoleErrors.forEach((err, i) => console.log(`   ${i+1}. ${err.substring(0, 200)}`));
    } else {
      console.log('\n✅ Sem erros de console');
    }

    if (networkErrors.length > 0) {
      console.log('\n❌ Erros de Rede:');
      networkErrors.forEach((err, i) => console.log(`   ${i+1}. ${err}`));
    } else {
      console.log('\n✅ Sem erros de rede');
    }

    console.log('\n📸 Screenshots salvos em: ./screenshots/reservation-*.png');

  } catch (error) {
    console.error('\n❌ ERRO durante o teste:', error.message);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/reservation-error.png` });
  } finally {
    // Don't close browser immediately so we can see the result
    console.log('\n⏳ Aguardando 10s antes de fechar...');
    await sleep(10000);
    await browser.close();
  }
}

// Ensure screenshots directory exists
const fs = require('fs');
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

runReservationTest().catch(console.error);
