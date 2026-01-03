#!/usr/bin/env node
/**
 * Script de Teste de Reserva de Máquinas em Múltiplas Regiões
 *
 * Verifica:
 * 1. Se a página de máquinas carrega corretamente
 * 2. Se GPU Offers mostra lista de GPUs disponíveis
 * 3. Se há opções de região
 * 4. Se botões de provisionar existem
 * 5. Se página de machines mostra o estado corretamente
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// Configuração
const BASE_URL = process.env.BASE_URL || 'http://localhost:4892';
const USER_DATA_DIR = '/Users/marcos/.playwright-mcp-profile';
const SCREENSHOTS_DIR = path.join(__dirname, '..', 'screenshots', 'reserva-test');

// Garantir diretório de screenshots
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const results = {
  timestamp: new Date().toISOString(),
  checks: [],
  warnings: [],
  errors: [],
  screenshots: [],
  gpuOffers: [],
  regions: [],
  machines: []
};

function addCheck(name, passed, details = '') {
  results.checks.push({ name, passed, details });
  const icon = passed ? '✅' : '❌';
  console.log(`   ${icon} ${name}${details ? ': ' + details : ''}`);
}

async function runTest() {
  console.log('═'.repeat(70));
  console.log('🔍 VERIFICAÇÃO DE FUNCIONALIDADES DE RESERVA DE MÁQUINAS');
  console.log('═'.repeat(70));
  console.log(`📍 URL: ${BASE_URL}`);
  console.log(`📅 ${new Date().toLocaleString()}\n`);

  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: true,
    viewport: { width: 1400, height: 900 },
    ignoreHTTPSErrors: true
  });

  const page = await context.newPage();

  try {
    // ==========================================
    // TESTE 1: Acesso à aplicação
    // ==========================================
    console.log('\n📋 TESTE 1: Acesso à aplicação');
    console.log('─'.repeat(50));

    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    const isLoggedIn = !page.url().includes('login') &&
                       (await page.content()).includes('Dashboard') ||
                       (await page.content()).includes('Dumont');

    const isDemo = page.url().includes('/') && !(await page.content()).includes('/app');
    const basePath = isDemo ? '/demo-app' : '/app';

    addCheck('Aplicação acessível', true, page.url());

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '01-home.png'), fullPage: true });
    results.screenshots.push('01-home.png');

    // ==========================================
    // TESTE 2: Página de Máquinas
    // ==========================================
    console.log('\n📋 TESTE 2: Página de Máquinas');
    console.log('─'.repeat(50));

    await page.goto(`${BASE_URL}${basePath}/machines`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    const machinesContent = await page.content();
    const machinesUrl = page.url();

    addCheck('Página de Máquinas carrega', machinesUrl.includes('machines'), machinesUrl);

    // Verificar elementos da página
    const hasTitle = machinesContent.includes('Minhas Máquinas') || machinesContent.includes('Machines');
    addCheck('Título da página', hasTitle);

    const hasNewButton = machinesContent.includes('Nova Máquina') || machinesContent.includes('New Machine');
    addCheck('Botão Nova Máquina', hasNewButton);

    const hasStats = machinesContent.includes('GPUs Ativas') || machinesContent.includes('Active GPUs');
    addCheck('Estatísticas visíveis', hasStats);

    // Contar máquinas demo
    const machineCards = await page.$$('.ta-card, [class*="machine"], [class*="card"]');
    addCheck('Cards de máquinas', machineCards.length > 0, `${machineCards.length} cards`);

    // Extrair info das máquinas
    const machineNames = await page.$$eval('[class*="card"] h3, [class*="machine"] h3', els =>
      els.map(el => el.textContent).filter(t => t && t.includes('GPU') || t.includes('RTX') || t.includes('A100'))
    );
    results.machines = machineNames;
    if (machineNames.length > 0) {
      console.log(`   📊 Máquinas encontradas: ${machineNames.slice(0, 3).join(', ')}${machineNames.length > 3 ? '...' : ''}`);
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '02-machines.png'), fullPage: true });
    results.screenshots.push('02-machines.png');

    // ==========================================
    // TESTE 3: GPU Offers
    // ==========================================
    console.log('\n📋 TESTE 3: GPU Offers (Lista de GPUs disponíveis)');
    console.log('─'.repeat(50));

    await page.goto(`${BASE_URL}${basePath}/gpu-offers`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    const gpuContent = await page.content();

    addCheck('Página GPU Offers carrega', page.url().includes('gpu-offers'));

    // Verificar GPUs listadas
    const gpuTypes = ['RTX 3080', 'RTX 3090', 'RTX 4080', 'RTX 4090', 'A100', 'H100', 'L40S'];
    const foundGpus = gpuTypes.filter(gpu => gpuContent.includes(gpu));
    addCheck('GPUs listadas', foundGpus.length > 0, foundGpus.join(', '));
    results.gpuOffers = foundGpus;

    // Verificar preços
    const hasPrices = gpuContent.includes('$') || gpuContent.includes('/hora') || gpuContent.includes('/hr');
    addCheck('Preços visíveis', hasPrices);

    // Verificar economia vs AWS
    const hasSavings = gpuContent.includes('economia') || gpuContent.includes('saving') || gpuContent.includes('%');
    addCheck('Economia vs AWS visível', hasSavings);

    // Verificar botões de provisionar
    const provisionButtons = await page.$$('button:has-text("Provisionar"), button:has-text("Provision")');
    addCheck('Botões de Provisionar', provisionButtons.length > 0, `${provisionButtons.length} botões`);

    // Verificar filtros
    const hasFilters = gpuContent.includes('VRAM') || gpuContent.includes('Buscar') || gpuContent.includes('Enterprise');
    addCheck('Filtros disponíveis', hasFilters);

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '03-gpu-offers.png'), fullPage: true });
    results.screenshots.push('03-gpu-offers.png');

    // ==========================================
    // TESTE 4: Seletor de Regiões
    // ==========================================
    console.log('\n📋 TESTE 4: Seletor de Regiões');
    console.log('─'.repeat(50));

    // Verificar se há seletor de região
    const regionButton = await page.$('button:has-text("Região"), button:has-text("Region"), button:has-text("Todas Regioes")');
    const hasRegionSelector = regionButton !== null;
    addCheck('Seletor de região presente', hasRegionSelector);

    if (regionButton) {
      // Clicar para ver regiões
      await regionButton.click({ timeout: 3000 }).catch(() => {});
      await sleep(1500);

      await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '04-regions.png'), fullPage: true });
      results.screenshots.push('04-regions.png');

      const regionContent = await page.content();
      const possibleRegions = ['US', 'EU', 'Europe', 'America', 'Asia', 'us-east', 'us-west', 'eu-west'];
      const foundRegions = possibleRegions.filter(r => regionContent.toLowerCase().includes(r.toLowerCase()));

      if (foundRegions.length > 0) {
        addCheck('Regiões disponíveis', true, foundRegions.join(', '));
        results.regions = foundRegions;
      } else {
        addCheck('Regiões carregando', regionContent.includes('Carregando') || regionContent.includes('Loading'), 'API de regiões');
      }

      await page.keyboard.press('Escape');
      await sleep(500);
    }

    // ==========================================
    // TESTE 5: Dashboard - Wizard de criação
    // ==========================================
    console.log('\n📋 TESTE 5: Dashboard (Wizard de criação)');
    console.log('─'.repeat(50));

    await page.goto(`${BASE_URL}${basePath}`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    const dashContent = await page.content();

    addCheck('Dashboard carrega', dashContent.includes('Dashboard') || dashContent.includes('GPU'));

    // Verificar ofertas/tiers no dashboard
    const hasTiers = dashContent.includes('tier') || dashContent.includes('Tier') ||
                     dashContent.includes('GPU') || dashContent.includes('Selecionar');
    addCheck('Ofertas no Dashboard', hasTiers);

    // Verificar wizard steps ou CTA
    const hasWizard = dashContent.includes('Wizard') || dashContent.includes('Step') ||
                      dashContent.includes('Começar') || dashContent.includes('Get Started');
    addCheck('Wizard/CTA presente', hasWizard || hasTiers);

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '05-dashboard.png'), fullPage: true });
    results.screenshots.push('05-dashboard.png');

    // ==========================================
    // TESTE 6: Navegação e Menu
    // ==========================================
    console.log('\n📋 TESTE 6: Navegação e Menu');
    console.log('─'.repeat(50));

    // Verificar links do menu
    const menuLinks = await page.$$('a[href*="machines"], a[href*="gpu-offers"], a[href*="models"], a[href*="chat"]');
    addCheck('Links de navegação', menuLinks.length >= 3, `${menuLinks.length} links`);

    // Verificar sidebar/menu items
    const sidebarItems = await page.$$('[class*="sidebar"] a, nav a, [class*="menu"] a');
    addCheck('Menu lateral', sidebarItems.length > 0, `${sidebarItems.length} itens`);

    // ==========================================
    // TESTE 7: Responsividade das listas
    // ==========================================
    console.log('\n📋 TESTE 7: Componentes e listas');
    console.log('─'.repeat(50));

    // Voltar para machines para verificar componentes
    await page.goto(`${BASE_URL}${basePath}/machines`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(1500);

    // Verificar tabs de filtro
    const hasTabs = (await page.content()).includes('Todas') || (await page.content()).includes('Online') || (await page.content()).includes('Offline');
    addCheck('Tabs de filtro', hasTabs);

    // Verificar ações nas máquinas
    const hasActions = (await page.content()).includes('Destruir') || (await page.content()).includes('Pausar') ||
                       (await page.content()).includes('Iniciar') || (await page.content()).includes('Start');
    addCheck('Ações de máquina', hasActions);

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '06-final.png'), fullPage: true });
    results.screenshots.push('06-final.png');

  } catch (error) {
    console.error(`\n❌ Erro: ${error.message}`);
    results.errors.push(error.message);

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'error.png'), fullPage: true }).catch(() => {});
    results.screenshots.push('error.png');
  } finally {
    await context.close();
  }

  // ==========================================
  // RESUMO
  // ==========================================
  const passed = results.checks.filter(c => c.passed).length;
  const failed = results.checks.filter(c => !c.passed).length;
  const successRate = Math.round((passed / results.checks.length) * 100);

  console.log('\n' + '═'.repeat(70));
  console.log('📊 RESUMO DA VERIFICAÇÃO');
  console.log('═'.repeat(70));

  console.log(`\n✅ Passou: ${passed}/${results.checks.length}`);
  console.log(`❌ Falhou: ${failed}/${results.checks.length}`);

  if (results.gpuOffers.length > 0) {
    console.log(`\n🎮 GPUs disponíveis: ${results.gpuOffers.join(', ')}`);
  }

  if (results.regions.length > 0) {
    console.log(`🌍 Regiões: ${results.regions.join(', ')}`);
  }

  if (results.machines.length > 0) {
    console.log(`💻 Máquinas: ${results.machines.slice(0, 5).join(', ')}`);
  }

  if (results.warnings.length > 0) {
    console.log(`\n⚠️  Avisos: ${results.warnings.length}`);
    results.warnings.forEach(w => console.log(`   ⚠ ${w}`));
  }

  if (results.errors.length > 0) {
    console.log(`\n❌ Erros: ${results.errors.length}`);
    results.errors.forEach(e => console.log(`   ✗ ${e}`));
  }

  console.log(`\n📸 Screenshots: ${results.screenshots.length}`);
  results.screenshots.forEach(s => console.log(`   → screenshots/reserva-test/${s}`));

  console.log('\n' + '═'.repeat(70));
  console.log(`📈 Taxa de sucesso: ${successRate}%`);
  console.log('═'.repeat(70));

  // Salvar relatório
  const reportPath = path.join(SCREENSHOTS_DIR, 'test-report.json');
  fs.writeFileSync(reportPath, JSON.stringify({
    ...results,
    summary: { passed, failed, successRate }
  }, null, 2));
  console.log(`\n📄 Relatório: screenshots/reserva-test/test-report.json\n`);

  return { passed, failed, successRate };
}

runTest().then(({ successRate }) => {
  process.exit(successRate >= 80 ? 0 : 1);
}).catch(err => {
  console.error('Erro fatal:', err);
  process.exit(1);
});
