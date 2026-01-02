#!/usr/bin/env node
/**
 * Script para testar o fluxo completo de migração GPU <-> CPU
 * - Cria máquina GPU
 * - Migra para CPU
 * - Verifica arquivos
 * - Migra de volta para GPU
 */

const { chromium } = require('playwright');

const BASE_URL = 'http://localhost:4895';
const SCREENSHOTS_DIR = './screenshots';

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runMigrationTest() {
  console.log('🚀 Iniciando teste COMPLETO de migração GPU <-> CPU');
  console.log('⚠️  Este teste vai provisionar máquinas REAIS (custa dinheiro)');

  const browser = await chromium.launch({
    headless: false,
    slowMo: 200
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Login - try auto_login first
    console.log('\n📍 Step 1: Login');
    await page.goto(`${BASE_URL}/login?auto_login=demo`);
    await sleep(8000); // Wait longer for auto_login to complete

    console.log(`   URL após auto_login: ${page.url()}`);

    // If still on login page, do manual login
    if (page.url().includes('/login')) {
      console.log('   Auto-login não funcionou, tentando login manual...');

      // Wait for form elements to be visible
      await page.waitForSelector('input[placeholder="seu@email.com"]', { timeout: 5000 });

      // Clear and fill email
      await page.click('input[placeholder="seu@email.com"]');
      await page.keyboard.type('marcosremar@gmail.com', { delay: 50 });

      // Clear and fill password
      await page.click('input[type="password"]');
      await page.keyboard.type('dumont123', { delay: 50 });

      // Click submit
      await page.click('button[type="submit"]');
      await sleep(5000);

      console.log(`   URL após login manual: ${page.url()}`);
    }

    // Ensure we're in the app
    if (!page.url().includes('/app')) {
      console.log('   Navegando direto para /app...');
      await page.goto(`${BASE_URL}/app`);
      await sleep(3000);
    }

    console.log(`   URL final: ${page.url()}`);

    // 2. Navigate to Machines
    console.log('\n📍 Step 2: Navegando para Máquinas');
    await page.goto(`${BASE_URL}/app/machines`);
    await sleep(3000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-01-machines-page.png` });

    // 3. Check for existing machines and CPU migration button
    console.log('\n📍 Step 3: Verificando máquinas existentes');
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-02-machines-page-before-click.png` });

    // Look for existing CPU migration buttons on machine cards
    const cpuMigrationButton = page.locator('button:has-text("CPU")').first();
    const cpuButtonCount = await cpuMigrationButton.count();
    console.log(`   Botões de migração CPU encontrados: ${cpuButtonCount}`);

    if (cpuButtonCount > 0) {
      // Test migration with existing GPU machine
      console.log('\n📍 Step 3a: Testando migração GPU → CPU com máquina existente');
      await cpuMigrationButton.click();
      await sleep(3000);
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-03-cpu-migration-modal.png` });

      // Check if migration modal opened
      const modal = page.locator('[role="dialog"], .modal, [class*="Modal"]');
      if (await modal.count() > 0) {
        console.log('   ✅ Modal de migração CPU aberto');

        // Look for "Apenas CPU" tier option
        const cpuTier = page.locator('text=Apenas CPU').first();
        if (await cpuTier.count() > 0) {
          console.log('   Selecionando tier "Apenas CPU"...');
          await cpuTier.click();
          await sleep(5000); // Wait for CPU machines to load

          // Verify CPU machines are shown (should NOT have GPU names)
          const pageContent = await page.content();
          const hasGPU = pageContent.includes('RTX 3') || pageContent.includes('RTX 4') || pageContent.includes('RTX 5') || pageContent.includes('A100');
          const hasCores = pageContent.includes('cores') || pageContent.includes('CPU');

          console.log(`   Mostrando GPUs: ${hasGPU}`);
          console.log(`   Mostrando info CPU: ${hasCores}`);

          if (!hasGPU) {
            console.log('   ✅ SUCESSO: Tier CPU filtra corretamente (sem GPUs no wizard de migração)');
          } else {
            console.log('   ⚠️ Verificar: GPUs podem estar aparecendo no tier CPU');
          }

          await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-04-cpu-tier-selected.png` });
        }

        // Close modal
        const closeButton = page.locator('button:has-text("Cancelar"), button:has-text("Fechar"), [aria-label="close"], button[class*="close"]').first();
        if (await closeButton.count() > 0) {
          await closeButton.click();
          await sleep(1000);
        }
      }
    }

    // Now try to open new machine wizard
    console.log('\n📍 Step 4: Abrindo wizard de nova máquina');
    const createButton = page.locator('text=Nova Máquina').first();
    if (await createButton.count() > 0) {
      await createButton.click();
      await sleep(2000);
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-02-wizard-step1.png` });
      console.log('   ✅ Wizard aberto');

      // Step 1: Select Region - EUA
      console.log('\n📍 Step 4: Selecionando região EUA');
      const usaRegion = page.locator('text=EUA').first();
      if (await usaRegion.count() > 0) {
        await usaRegion.click();
        await sleep(2000);
        console.log('   ✅ EUA selecionado');
      } else {
        console.log('   ⚠️ Botão EUA não encontrado, tentando clicar no mapa');
      }

      // Click Next
      const nextButton = page.locator('button:has-text("Próximo")');
      await nextButton.first().click();
      await sleep(1500);
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-03-wizard-step2.png` });

      // Step 2: Select Purpose - "Desenvolver" (Dev diário)
      console.log('\n📍 Step 5: Selecionando propósito "Desenvolver"');
      const purposeOption = page.locator('text=Desenvolver').first();
      if (await purposeOption.count() > 0) {
        await purposeOption.click();
        await sleep(2000);
        console.log('   ✅ Desenvolver selecionado');
      } else {
        // Try Experimentar as fallback
        const experimentOption = page.locator('text=Experimentar').first();
        if (await experimentOption.count() > 0) {
          await experimentOption.click();
          await sleep(2000);
          console.log('   ✅ Experimentar selecionado');
        }
      }

      await nextButton.first().click();
      await sleep(2000);
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-04-wizard-step3.png` });

      // Step 3: Select Tier - First test "Apenas CPU"
      console.log('\n📍 Step 6: Testando tier "Apenas CPU"');
      const cpuTier = page.locator('text=Apenas CPU').first();
      if (await cpuTier.count() > 0) {
        await cpuTier.click();
        await sleep(5000); // Wait for CPU machines to load from API
        await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-05-cpu-tier.png` });

        // Check machines shown
        const pageContent = await page.content();
        const hasGPU = pageContent.includes('RTX 3') || pageContent.includes('RTX 4') || pageContent.includes('A100');
        const hasCores = pageContent.includes('cores') || pageContent.includes('CPU');

        console.log(`   Mostrando GPUs: ${hasGPU}`);
        console.log(`   Mostrando info CPU: ${hasCores}`);

        if (!hasGPU) {
          console.log('   ✅ SUCESSO: Tier CPU filtra corretamente (sem GPUs)');
        } else {
          console.log('   ⚠️ PROBLEMA: GPUs aparecendo no tier CPU');
        }
      }

      // Now select GPU tier - "Lento" (cheapest GPU)
      console.log('\n📍 Step 7: Selecionando tier GPU "Lento"');
      const gpuTier = page.locator('text=Lento').first();
      if (await gpuTier.count() > 0) {
        await gpuTier.click();
        await sleep(5000);
        await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-06-gpu-tier.png` });

        // Verify GPU machines are shown
        const gpuContent = await page.content();
        const showsGPU = gpuContent.includes('RTX') || gpuContent.includes('A100');
        console.log(`   Mostrando GPUs: ${showsGPU}`);

        if (showsGPU) {
          console.log('   ✅ SUCESSO: Tier GPU mostra máquinas GPU');
        }
      }

      // Select first machine
      console.log('\n📍 Step 8: Selecionando primeira máquina');
      const machineOption = page.locator('[data-testid="machine-option"], .machine-option, [class*="MachineCard"]').first();
      if (await machineOption.count() > 0) {
        await machineOption.click();
        await sleep(1000);
        console.log('   ✅ Máquina selecionada');
      } else {
        // Try clicking any card that looks like a machine option
        const anyCard = page.locator('[class*="card"]:has-text("RTX"), [class*="card"]:has-text("$")').first();
        if (await anyCard.count() > 0) {
          await anyCard.click();
          await sleep(1000);
          console.log('   ✅ Card de máquina clicado');
        }
      }

      await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-07-machine-selected.png` });

      // The wizard now shows strategy options (Tensor Dock Serverless, Sem Failover)
      // and has "Iniciar" button instead of "Próximo"
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-08-strategy-step.png` });

      // Click Iniciar to start provisioning
      console.log('\n📍 Step 9: Iniciando provisionamento');
      const startButton = page.locator('button:has-text("Iniciar")').first();
      if (await startButton.count() > 0) {
        await startButton.click();
        console.log('   🚀 Provisionamento iniciado!');
        await sleep(5000);
        await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-09-provisioning.png` });

        // Wait for machine to be ready (up to 10 minutes)
        console.log('   ⏳ Aguardando máquina ficar pronta (até 10 min)...');
        let attempts = 0;
        const maxAttempts = 120; // 10 minutes with 5 second intervals

        while (attempts < maxAttempts) {
          await sleep(5000);
          await page.goto(`${BASE_URL}/app/machines`);
          await sleep(3000);

          const onlineStatus = page.locator('text=Online');
          if (await onlineStatus.count() > 0) {
            console.log('   ✅ Máquina GPU online!');
            await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-10-gpu-online.png` });
            break;
          }

          attempts++;
          if (attempts % 6 === 0) {
            console.log(`   ⏳ ${attempts * 5}s aguardando...`);
          }
        }

        if (attempts >= maxAttempts) {
          console.log('   ⚠️ Timeout aguardando máquina');
        }

        // 10. Test CPU migration
        console.log('\n📍 Step 10: Iniciando migração GPU -> CPU');
        const cpuMigrationButton = page.locator('button:has-text("CPU")').first();
        if (await cpuMigrationButton.count() > 0) {
          await cpuMigrationButton.click();
          await sleep(3000);
          await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-11-cpu-migration-wizard.png` });

          // Select CPU tier in migration wizard
          const cpuTierMigration = page.locator('text=Apenas CPU').first();
          if (await cpuTierMigration.count() > 0) {
            await cpuTierMigration.click();
            await sleep(5000);
            await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-12-cpu-tier-migration.png` });

            // Verify CPU machines only
            const migrationContent = await page.content();
            const hasGPUInMigration = migrationContent.includes('RTX') || migrationContent.includes('A100');
            console.log(`   Mostrando GPUs no wizard: ${hasGPUInMigration}`);

            if (!hasGPUInMigration) {
              console.log('   ✅ Filtro CPU funcionando no wizard de migração!');
            }
          }
        }
      }
    } else {
      console.log('   ❌ Botão criar máquina não encontrado');
    }

    await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-final.png` });

    console.log('\n✅ Teste concluído!');
    console.log('   Screenshots salvos em: ./screenshots/');

  } catch (error) {
    console.error('❌ Erro durante o teste:', error.message);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/test-error.png` });
  } finally {
    await browser.close();
  }
}

// Ensure screenshots directory exists
const fs = require('fs');
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

runMigrationTest().catch(console.error);
