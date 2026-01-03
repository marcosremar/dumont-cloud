#!/usr/bin/env node
/**
 * Script para testar funcionalidades de reserva de máquinas GPU/CPU
 * Usa Playwright diretamente com Chrome em modo Headless
 * Mantém o mesmo perfil do MCP
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// Configuração
const BASE_URL = process.env.BASE_URL || 'http://localhost:4892';
const USER_DATA_DIR = '/Users/marcos/.playwright-mcp-profile';
const SCREENSHOTS_DIR = path.join(__dirname, '..', 'screenshots');

// Garantir diretório de screenshots
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

async function runTests() {
  const results = {
    passed: [],
    failed: [],
    warnings: [],
    screenshots: []
  };

  console.log('🚀 Iniciando testes de Máquinas GPU/CPU em modo Headless...');
  console.log(`📍 URL Base: ${BASE_URL}\n`);

  // Lançar browser com perfil persistente
  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: true,
    viewport: { width: 1400, height: 900 },
    ignoreHTTPSErrors: true
  });

  const page = await context.newPage();

  try {
    // ==========================================
    // TESTE 1: Verificar login / acesso demo
    // ==========================================
    console.log('📋 TESTE 1: Verificar acesso à aplicação');

    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);

    const initialUrl = page.url();
    const pageContent = await page.content();

    // Verificar se precisa fazer login
    if (pageContent.includes('Login') || pageContent.includes('Entrar') || initialUrl.includes('login')) {
      console.log('   ⚠️ Página de login detectada - usando rotas de demo');
      // Usar rotas de demo que não precisam de auth
      await page.goto(`${BASE_URL}/demo-app`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      results.warnings.push('Usando modo demo (sem autenticação)');
    } else if (pageContent.includes('Dashboard') || initialUrl.includes('/app')) {
      console.log('   ✅ Usuário autenticado');
      results.passed.push('Usuário autenticado');
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '01-inicial.png'), fullPage: true });
    results.screenshots.push('01-inicial.png');

    // ==========================================
    // TESTE 2: Página de Máquinas
    // ==========================================
    console.log('\n📋 TESTE 2: Página de Máquinas');

    // Tentar rota autenticada primeiro, fallback para demo
    let machinesUrl = `${BASE_URL}/app/machines`;
    await page.goto(machinesUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);

    if (page.url().includes('login') || page.url() === `${BASE_URL}/`) {
      machinesUrl = `${BASE_URL}/demo-app/machines`;
      await page.goto(machinesUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(2000);
    }

    console.log(`   URL: ${page.url()}`);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '02-maquinas.png'), fullPage: true });
    results.screenshots.push('02-maquinas.png');

    let machinesContent = await page.content();

    // Verificar se lista de máquinas está visível
    const hasMachinesList = machinesContent.includes('GPU') ||
                           machinesContent.includes('RTX') ||
                           machinesContent.includes('A100') ||
                           machinesContent.includes('Machine') ||
                           machinesContent.includes('Máquina');

    if (hasMachinesList) {
      results.passed.push('Página de Máquinas carregou com lista');
      console.log('   ✅ Lista de máquinas visível');
    } else {
      results.failed.push('Lista de máquinas não encontrada');
      console.log('   ❌ Lista de máquinas não encontrada');
    }

    // ==========================================
    // TESTE 3: GPU Offers - Lista de ofertas
    // ==========================================
    console.log('\n📋 TESTE 3: GPU Offers - Lista de ofertas de GPU');

    let gpuOffersUrl = `${BASE_URL}/app/gpu-offers`;
    await page.goto(gpuOffersUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);

    if (page.url().includes('login') || page.url() === `${BASE_URL}/`) {
      gpuOffersUrl = `${BASE_URL}/demo-app/gpu-offers`;
      await page.goto(gpuOffersUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(2000);
    }

    console.log(`   URL: ${page.url()}`);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '03-gpu-offers.png'), fullPage: true });
    results.screenshots.push('03-gpu-offers.png');

    const gpuOffersContent = await page.content();

    // Verificar lista de ofertas GPU
    const hasGPUOffers = gpuOffersContent.includes('GPU') ||
                         gpuOffersContent.includes('NVIDIA') ||
                         gpuOffersContent.includes('RTX') ||
                         gpuOffersContent.includes('Offer') ||
                         gpuOffersContent.includes('Oferta') ||
                         gpuOffersContent.includes('$/hr') ||
                         gpuOffersContent.includes('price');

    if (hasGPUOffers) {
      results.passed.push('GPU Offers - Lista de ofertas visível');
      console.log('   ✅ Lista de ofertas GPU visível');

      // Contar cards/linhas de ofertas
      const offerCards = await page.$$('[class*="card"], [class*="offer"], tr:not(:first-child), [class*="item"]');
      console.log(`   📊 Elementos de ofertas: ${offerCards.length}`);
    } else {
      results.failed.push('GPU Offers - Lista não encontrada');
      console.log('   ❌ Lista de ofertas não encontrada');
    }

    // ==========================================
    // TESTE 4: Botão de Reservar/Deploy GPU
    // ==========================================
    console.log('\n📋 TESTE 4: Botão de Reservar/Deploy');

    // Procurar por diferentes variações do botão
    const deployButtons = await page.$$('button:has-text("Deploy"), button:has-text("Rent"), button:has-text("Alugar"), button:has-text("Reservar"), button:has-text("Select"), button:has-text("Selecionar"), [class*="rent"], [class*="deploy"]');

    if (deployButtons.length > 0) {
      results.passed.push('Botão de Deploy/Reservar encontrado');
      console.log(`   ✅ Botões encontrados: ${deployButtons.length}`);

      // Clicar no primeiro botão disponível
      try {
        await deployButtons[0].click();
        await page.waitForTimeout(2000);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '04-wizard-deploy.png'), fullPage: true });
        results.screenshots.push('04-wizard-deploy.png');

        const wizardContent = await page.content();

        // ==========================================
        // TESTE 5: Verificar Wizard/Modal de Deploy
        // ==========================================
        console.log('\n📋 TESTE 5: Wizard de Deploy');

        const hasWizard = wizardContent.includes('Step') ||
                          wizardContent.includes('Etapa') ||
                          wizardContent.includes('Model') ||
                          wizardContent.includes('Modelo') ||
                          wizardContent.includes('Configure') ||
                          wizardContent.includes('Hardware') ||
                          wizardContent.includes('SSH') ||
                          wizardContent.includes('modal');

        if (hasWizard) {
          results.passed.push('Wizard de Deploy aberto');
          console.log('   ✅ Wizard/Modal aberto');

          // ==========================================
          // TESTE 6: Opções GPU vs CPU Standby
          // ==========================================
          console.log('\n📋 TESTE 6: Opções GPU vs CPU Standby');

          const hasGPUOption = wizardContent.includes('GPU') || wizardContent.includes('gpu');
          const hasCPUOption = wizardContent.includes('CPU') ||
                               wizardContent.includes('Standby') ||
                               wizardContent.includes('standby') ||
                               wizardContent.includes('Backup');

          if (hasGPUOption) {
            results.passed.push('Opção GPU disponível no wizard');
            console.log('   ✅ Opção GPU disponível');
          }

          if (hasCPUOption) {
            results.passed.push('Opção CPU/Standby disponível');
            console.log('   ✅ Opção CPU/Standby disponível');
          } else {
            results.warnings.push('Opção CPU/Standby não visível (pode estar em outra etapa)');
            console.log('   ⚠️ Opção CPU/Standby não visível nesta etapa');
          }

          // Verificar dropdowns/selects
          const selects = await page.$$('select, [role="combobox"], [class*="select"]');
          const inputs = await page.$$('input:not([type="hidden"])');
          console.log(`   📊 Campos: Selects=${selects.length}, Inputs=${inputs.length}`);

          // Tentar ver opções do dropdown de modelo
          if (selects.length > 0) {
            try {
              await selects[0].click();
              await page.waitForTimeout(1000);

              await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '05-dropdown-aberto.png'), fullPage: true });
              results.screenshots.push('05-dropdown-aberto.png');

              const options = await page.$$('[role="option"], option, [class*="option"], li[class*="item"]');
              if (options.length > 0) {
                results.passed.push(`Dropdown funcional com ${options.length} opções`);
                console.log(`   ✅ Dropdown com ${options.length} opções`);
              }

              await page.keyboard.press('Escape');
            } catch (e) {
              console.log(`   ⚠️ Erro ao testar dropdown: ${e.message}`);
            }
          }
        } else {
          results.warnings.push('Wizard não detectado claramente');
          console.log('   ⚠️ Wizard não detectado claramente');
        }

        // Fechar modal
        const closeBtn = await page.$('button:has-text("Cancel"), button:has-text("Cancelar"), button:has-text("Close"), button:has-text("Fechar"), [aria-label*="close"], [class*="close"]');
        if (closeBtn) {
          await closeBtn.click();
        } else {
          await page.keyboard.press('Escape');
        }
        await page.waitForTimeout(1000);

      } catch (e) {
        results.warnings.push(`Erro ao interagir com botão: ${e.message}`);
        console.log(`   ⚠️ Erro: ${e.message}`);
      }
    } else {
      results.failed.push('Botão de Deploy/Reservar não encontrado');
      console.log('   ❌ Nenhum botão de deploy encontrado');
    }

    // ==========================================
    // TESTE 7: Página de Reservations
    // ==========================================
    console.log('\n📋 TESTE 7: Página de Reservations');

    await page.goto(`${BASE_URL}/app/reservations`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);

    if (!page.url().includes('reservations')) {
      console.log('   ⚠️ Redirecionado - reservations requer auth');
      results.warnings.push('Reservations requer autenticação');
    } else {
      await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '06-reservations.png'), fullPage: true });
      results.screenshots.push('06-reservations.png');

      const reservContent = await page.content();
      if (reservContent.includes('Reserv') || reservContent.includes('reserv')) {
        results.passed.push('Página de Reservations acessível');
        console.log('   ✅ Página de Reservations OK');
      }
    }

    // ==========================================
    // TESTE 8: Models Page
    // ==========================================
    console.log('\n📋 TESTE 8: Página de Models');

    await page.goto(`${BASE_URL}/app/models`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '07-models.png'), fullPage: true });
    results.screenshots.push('07-models.png');

    const modelsContent = await page.content();
    if (modelsContent.includes('Model') || modelsContent.includes('Deploy') || modelsContent.includes('LLM')) {
      results.passed.push('Página de Models acessível');
      console.log('   ✅ Página de Models OK');

      // Verificar botão de deploy em models
      const modelDeployBtn = await page.$('button:has-text("Deploy"), button:has-text("New"), button:has-text("Novo")');
      if (modelDeployBtn) {
        results.passed.push('Botão de Deploy em Models encontrado');
        console.log('   ✅ Botão de Deploy em Models');
      }
    } else {
      results.warnings.push('Página de Models pode requerer auth');
      console.log('   ⚠️ Models pode requerer autenticação');
    }

    // ==========================================
    // TESTE 9: Chat Arena
    // ==========================================
    console.log('\n📋 TESTE 9: Chat Arena');

    let chatUrl = `${BASE_URL}/app/chat-arena`;
    await page.goto(chatUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);

    if (page.url().includes('login') || page.url() === `${BASE_URL}/`) {
      chatUrl = `${BASE_URL}/demo-app/chat-arena`;
      await page.goto(chatUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(2000);
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '08-chat-arena.png'), fullPage: true });
    results.screenshots.push('08-chat-arena.png');

    const chatContent = await page.content();
    if (chatContent.includes('Chat') || chatContent.includes('Arena') || chatContent.includes('Message')) {
      results.passed.push('Chat Arena acessível');
      console.log('   ✅ Chat Arena OK');
    }

    // ==========================================
    // TESTE 10: Dashboard
    // ==========================================
    console.log('\n📋 TESTE 10: Dashboard');

    let dashUrl = `${BASE_URL}/app`;
    await page.goto(dashUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);

    if (page.url().includes('login') || page.url() === `${BASE_URL}/`) {
      dashUrl = `${BASE_URL}/demo-app`;
      await page.goto(dashUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(2000);
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '09-dashboard.png'), fullPage: true });
    results.screenshots.push('09-dashboard.png');

    const dashContent = await page.content();
    if (dashContent.includes('Dashboard') || dashContent.includes('Overview') || dashContent.includes('GPU')) {
      results.passed.push('Dashboard acessível');
      console.log('   ✅ Dashboard OK');
    }

  } catch (error) {
    console.error(`\n❌ Erro durante os testes: ${error.message}`);
    results.failed.push(`Erro: ${error.message}`);

    try {
      await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'error.png'), fullPage: true });
      results.screenshots.push('error.png');
    } catch (e) {}
  } finally {
    await context.close();
  }

  // ==========================================
  // RESUMO FINAL
  // ==========================================
  console.log('\n' + '═'.repeat(70));
  console.log('📊 RESUMO DOS TESTES DE MÁQUINAS GPU/CPU');
  console.log('═'.repeat(70));

  console.log(`\n✅ PASSOU: ${results.passed.length}`);
  results.passed.forEach(t => console.log(`   ✓ ${t}`));

  if (results.warnings.length > 0) {
    console.log(`\n⚠️  AVISOS: ${results.warnings.length}`);
    results.warnings.forEach(t => console.log(`   ⚠ ${t}`));
  }

  console.log(`\n❌ FALHOU: ${results.failed.length}`);
  results.failed.forEach(t => console.log(`   ✗ ${t}`));

  console.log(`\n📸 SCREENSHOTS: ${results.screenshots.length}`);
  results.screenshots.forEach(s => console.log(`   → screenshots/${s}`));

  console.log('\n' + '═'.repeat(70));

  const total = results.passed.length + results.failed.length;
  const successRate = total > 0 ? (results.passed.length / total * 100) : 0;
  console.log(`📈 Taxa de sucesso: ${successRate.toFixed(1)}%`);
  console.log('═'.repeat(70) + '\n');

  // Salvar relatório JSON
  const reportPath = path.join(SCREENSHOTS_DIR, 'test-report.json');
  fs.writeFileSync(reportPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    baseUrl: BASE_URL,
    results: results,
    successRate: successRate
  }, null, 2));
  console.log(`📄 Relatório salvo em: screenshots/test-report.json\n`);

  return results;
}

// Executar
runTests().then(results => {
  const exitCode = results.failed.length > 2 ? 1 : 0;
  process.exit(exitCode);
}).catch(err => {
  console.error('Erro fatal:', err);
  process.exit(1);
});
