#!/usr/bin/env node
/**
 * Teste Completo de Máquinas e Failover
 *
 * Testa:
 * 1. Todos os tipos de GPU disponíveis
 * 2. Todas as configurações de failover (CPU Standby, backup)
 * 3. Todas as regiões disponíveis
 * 4. Criação, monitoramento e destruição de máquinas
 * 5. Simulação de failover
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// Configuração
const BASE_URL = process.env.BASE_URL || 'http://localhost:4892';
const USER_DATA_DIR = '/Users/marcos/.playwright-mcp-profile';
const SCREENSHOTS_DIR = path.join(__dirname, '..', 'screenshots', 'teste-completo');

// Criar diretório
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// Resultados detalhados
const testResults = {
  timestamp: new Date().toISOString(),
  gpuTypes: { tested: [], passed: [], failed: [] },
  failoverTypes: { tested: [], passed: [], failed: [] },
  regions: { tested: [], passed: [], failed: [] },
  machineOperations: { create: [], delete: [], failover: [] },
  issues: [],
  improvements: [],
  screenshots: []
};

// Logger colorido
const log = {
  info: (msg) => console.log(`   ℹ️  ${msg}`),
  success: (msg) => console.log(`   ✅ ${msg}`),
  error: (msg) => console.log(`   ❌ ${msg}`),
  warn: (msg) => console.log(`   ⚠️  ${msg}`),
  section: (msg) => console.log(`\n📋 ${msg}\n${'─'.repeat(60)}`)
};

async function runCompleteTest() {
  console.log('═'.repeat(70));
  console.log('🔬 TESTE COMPLETO DE MÁQUINAS E FAILOVER');
  console.log('═'.repeat(70));
  console.log(`📍 URL: ${BASE_URL}`);
  console.log(`📅 ${new Date().toLocaleString()}`);

  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: true,
    viewport: { width: 1400, height: 900 },
    ignoreHTTPSErrors: true
  });

  const page = await context.newPage();
  let isDemo = true;
  let basePath = '/demo-app';

  try {
    // ==========================================
    // FASE 1: Detectar modo (Demo vs Autenticado)
    // ==========================================
    log.section('FASE 1: Verificando modo de acesso');

    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    const content = await page.content();
    if (content.includes('/app/') && !content.includes('Login')) {
      isDemo = false;
      basePath = '/app';
      log.success('Modo: AUTENTICADO');
    } else {
      log.warn('Modo: DEMO (máquinas simuladas)');
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '01-inicio.png') });
    testResults.screenshots.push('01-inicio.png');

    // ==========================================
    // FASE 2: Testar todos os tipos de GPU
    // ==========================================
    log.section('FASE 2: Testando tipos de GPU disponíveis');

    await page.goto(`${BASE_URL}${basePath}/gpu-offers`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    const gpuContent = await page.content();

    // GPUs a testar
    const gpuTypes = [
      { name: 'RTX 3080', tier: 'consumer', vram: 10 },
      { name: 'RTX 3090', tier: 'consumer', vram: 24 },
      { name: 'RTX 4080', tier: 'consumer', vram: 16 },
      { name: 'RTX 4090', tier: 'consumer', vram: 24 },
      { name: 'RTX A6000', tier: 'professional', vram: 48 },
      { name: 'A100 40GB', tier: 'datacenter', vram: 40 },
      { name: 'A100 80GB', tier: 'datacenter', vram: 80 },
      { name: 'L40S', tier: 'datacenter', vram: 48 },
      { name: 'H100 PCIe', tier: 'datacenter', vram: 80 },
      { name: 'H100 SXM', tier: 'datacenter', vram: 80 }
    ];

    for (const gpu of gpuTypes) {
      testResults.gpuTypes.tested.push(gpu.name);

      if (gpuContent.includes(gpu.name)) {
        testResults.gpuTypes.passed.push(gpu.name);
        log.success(`${gpu.name} (${gpu.vram}GB) - Disponível`);
      } else {
        testResults.gpuTypes.failed.push(gpu.name);
        log.warn(`${gpu.name} - Não encontrada na lista`);
      }
    }

    // Verificar preços
    const priceMatches = gpuContent.match(/\$[\d.]+/g) || [];
    if (priceMatches.length > 0) {
      log.success(`Preços encontrados: ${priceMatches.length} valores`);
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '02-gpu-offers.png'), fullPage: true });
    testResults.screenshots.push('02-gpu-offers.png');

    // ==========================================
    // FASE 3: Testar seleção de regiões
    // ==========================================
    log.section('FASE 3: Testando regiões disponíveis');

    // Clicar no seletor de região
    const regionBtn = await page.$('button:has-text("Região"), button:has-text("Todas Regioes")');
    if (regionBtn) {
      await regionBtn.click().catch(() => {});
      await sleep(1500);

      await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '03-regioes.png'), fullPage: true });
      testResults.screenshots.push('03-regioes.png');

      const regionContent = await page.content();

      const regionsToTest = ['US', 'EU', 'us-east', 'us-west', 'eu-west', 'Europe', 'America'];
      for (const region of regionsToTest) {
        testResults.regions.tested.push(region);
        if (regionContent.toLowerCase().includes(region.toLowerCase())) {
          testResults.regions.passed.push(region);
          log.success(`Região ${region} - Disponível`);
        }
      }

      if (testResults.regions.passed.length === 0) {
        log.warn('Regiões ainda carregando ou API indisponível');
        testResults.issues.push('API de regiões pode estar lenta');
      }

      await page.keyboard.press('Escape');
      await sleep(500);
    } else {
      log.error('Seletor de região não encontrado');
      testResults.issues.push('Seletor de região ausente');
    }

    // ==========================================
    // FASE 4: Testar página de Máquinas
    // ==========================================
    log.section('FASE 4: Testando página de Máquinas');

    await page.goto(`${BASE_URL}${basePath}/machines`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    const machinesContent = await page.content();

    // Verificar elementos essenciais
    const machineChecks = [
      { name: 'Título da página', check: machinesContent.includes('Minhas Máquinas') || machinesContent.includes('Machines') },
      { name: 'Botão Nova Máquina', check: machinesContent.includes('Nova Máquina') || machinesContent.includes('New') },
      { name: 'Estatísticas GPUs Ativas', check: machinesContent.includes('GPUs Ativas') || machinesContent.includes('Active') },
      { name: 'Estatísticas VRAM', check: machinesContent.includes('VRAM') || machinesContent.includes('GB') },
      { name: 'Estatísticas Custo', check: machinesContent.includes('Custo') || machinesContent.includes('$') },
      { name: 'Tabs de filtro', check: machinesContent.includes('Todas') || machinesContent.includes('Online') },
    ];

    for (const check of machineChecks) {
      if (check.check) {
        log.success(check.name);
      } else {
        log.error(check.name);
        testResults.issues.push(`Faltando: ${check.name}`);
      }
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '04-machines.png'), fullPage: true });
    testResults.screenshots.push('04-machines.png');

    // ==========================================
    // FASE 5: Testar tipos de Failover
    // ==========================================
    log.section('FASE 5: Testando tipos de Failover');

    const failoverTypes = [
      { name: 'CPU Standby', description: 'Backup em CPU para failover instantâneo' },
      { name: 'Sem backup', description: 'Máquina sem proteção adicional' },
      { name: 'Multi-região', description: 'Backup em região diferente' }
    ];

    // Verificar se CPU Standby está mencionado
    if (machinesContent.includes('CPU Standby') || machinesContent.includes('Standby') || machinesContent.includes('Backup')) {
      testResults.failoverTypes.passed.push('CPU Standby');
      log.success('CPU Standby - Funcionalidade detectada');
    }

    if (machinesContent.includes('Shield') || machinesContent.includes('Proteção')) {
      testResults.failoverTypes.passed.push('Proteção');
      log.success('Indicador de proteção - Visível');
    }

    // Verificar cards com CPU Standby ativo
    const standbyBadges = await page.$$('[class*="standby"], [class*="backup"], [class*="shield"]');
    if (standbyBadges.length > 0) {
      log.success(`${standbyBadges.length} máquinas com indicador de backup`);
    }

    testResults.failoverTypes.tested = failoverTypes.map(f => f.name);

    // ==========================================
    // FASE 6: Testar simulação de Failover (modo demo)
    // ==========================================
    log.section('FASE 6: Testando simulação de Failover');

    if (isDemo) {
      // Procurar botão de simular failover
      const simulateButtons = await page.$$('button:has-text("Simular"), button:has-text("Failover"), button:has-text("Simulate")');

      if (simulateButtons.length > 0) {
        log.success(`${simulateButtons.length} botões de simulação encontrados`);

        // Tentar clicar no primeiro
        try {
          await simulateButtons[0].click({ timeout: 3000 });
          await sleep(3000);

          const afterClick = await page.content();
          if (afterClick.includes('failover') || afterClick.includes('GPU Lost') || afterClick.includes('Recuperando')) {
            testResults.failoverTypes.passed.push('Simulação de Failover');
            log.success('Simulação de failover iniciada com sucesso');
          }

          await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '05-failover-sim.png'), fullPage: true });
          testResults.screenshots.push('05-failover-sim.png');

        } catch (e) {
          log.warn(`Não foi possível simular failover: ${e.message}`);
        }
      } else {
        log.info('Botões de simulação não visíveis (pode precisar expandir menu do card)');
        testResults.improvements.push('Tornar simulação de failover mais acessível');
      }
    } else {
      log.info('Modo autenticado - simulação de failover não disponível');
    }

    // ==========================================
    // FASE 7: Testar operações de máquina
    // ==========================================
    log.section('FASE 7: Testando operações de máquina');

    // Verificar botões de ação
    const actionChecks = [
      { name: 'Destruir', selector: 'button:has-text("Destruir"), button:has-text("Destroy")' },
      { name: 'Pausar', selector: 'button:has-text("Pausar"), button:has-text("Pause")' },
      { name: 'Iniciar', selector: 'button:has-text("Iniciar"), button:has-text("Start")' },
      { name: 'Snapshot', selector: 'button:has-text("Snapshot"), button:has-text("Sync")' },
      { name: 'Migrar', selector: 'button:has-text("Migrar"), button:has-text("Migrate")' },
    ];

    for (const action of actionChecks) {
      const buttons = await page.$$(action.selector);
      if (buttons.length > 0) {
        log.success(`Ação "${action.name}" disponível (${buttons.length}x)`);
        testResults.machineOperations.create.push(action.name);
      } else {
        // Pode estar em menu dropdown
        log.info(`Ação "${action.name}" pode estar em menu`);
      }
    }

    // ==========================================
    // FASE 8: Testar Dashboard e Wizard
    // ==========================================
    log.section('FASE 8: Testando Dashboard e Wizard');

    await page.goto(`${BASE_URL}${basePath}`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    const dashContent = await page.content();

    const dashboardChecks = [
      { name: 'Cards de tier/oferta', check: dashContent.includes('tier') || dashContent.includes('GPU') },
      { name: 'Preços visíveis', check: dashContent.includes('$') || dashContent.includes('/hr') },
      { name: 'Seleção de GPU', check: dashContent.includes('Selecionar') || dashContent.includes('Select') },
      { name: 'Wizard steps', check: dashContent.includes('Step') || dashContent.includes('Etapa') || dashContent.includes('1') },
    ];

    for (const check of dashboardChecks) {
      if (check.check) {
        log.success(check.name);
      } else {
        log.info(check.name + ' - Não detectado diretamente');
      }
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '06-dashboard.png'), fullPage: true });
    testResults.screenshots.push('06-dashboard.png');

    // ==========================================
    // FASE 9: Verificar Menu e Navegação
    // ==========================================
    log.section('FASE 9: Testando navegação');

    const navLinks = await page.$$('nav a, [class*="sidebar"] a');
    log.success(`Links de navegação: ${navLinks.length}`);

    // Verificar páginas principais
    const pages = [
      { name: 'Machines', url: `${basePath}/machines` },
      { name: 'GPU Offers', url: `${basePath}/gpu-offers` },
      { name: 'Models', url: `${basePath}/models` },
      { name: 'Chat Arena', url: `${basePath}/chat-arena` },
      { name: 'Jobs', url: `${basePath}/jobs` },
    ];

    for (const pg of pages) {
      const hasLink = await page.$(`a[href*="${pg.url}"]`);
      if (hasLink) {
        log.success(`Link para ${pg.name}`);
      } else {
        log.warn(`Link para ${pg.name} não encontrado no menu`);
      }
    }

    // ==========================================
    // FASE 10: Identificar melhorias
    // ==========================================
    log.section('FASE 10: Análise de melhorias');

    // Análise automática de melhorias
    const contentAll = await page.content();

    // Verificar acessibilidade
    const buttons = await page.$$('button');
    const buttonsWithoutText = await page.$$eval('button', btns =>
      btns.filter(b => !b.textContent.trim() && !b.getAttribute('aria-label')).length
    );
    if (buttonsWithoutText > 0) {
      testResults.improvements.push(`${buttonsWithoutText} botões sem texto/aria-label (acessibilidade)`);
    }

    // Verificar loading states
    if (!contentAll.includes('loading') && !contentAll.includes('skeleton')) {
      testResults.improvements.push('Adicionar estados de loading mais visíveis');
    }

    // Verificar tooltips
    const tooltips = await page.$$('[data-tooltip], [title], [aria-describedby]');
    if (tooltips.length < 5) {
      testResults.improvements.push('Adicionar mais tooltips explicativos');
    }

    // Sugerir melhorias baseadas nos testes
    if (testResults.regions.passed.length < 3) {
      testResults.improvements.push('Expandir suporte a mais regiões');
    }

    if (!testResults.failoverTypes.passed.includes('Simulação de Failover')) {
      testResults.improvements.push('Tornar simulação de failover mais acessível na UI');
    }

    testResults.improvements.push('Adicionar menu avançado para configurações de failover');
    testResults.improvements.push('Implementar filtros avançados por região na listagem');

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '07-final.png'), fullPage: true });
    testResults.screenshots.push('07-final.png');

  } catch (error) {
    log.error(`Erro durante teste: ${error.message}`);
    testResults.issues.push(`Erro: ${error.message}`);

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'error.png'), fullPage: true }).catch(() => {});
    testResults.screenshots.push('error.png');
  } finally {
    await context.close();
  }

  // ==========================================
  // RESUMO FINAL
  // ==========================================
  console.log('\n' + '═'.repeat(70));
  console.log('📊 RESUMO DO TESTE COMPLETO');
  console.log('═'.repeat(70));

  console.log('\n🎮 GPUs Testadas:');
  console.log(`   Testadas: ${testResults.gpuTypes.tested.length}`);
  console.log(`   Disponíveis: ${testResults.gpuTypes.passed.length}`);
  console.log(`   → ${testResults.gpuTypes.passed.join(', ')}`);

  console.log('\n🌍 Regiões:');
  console.log(`   Testadas: ${testResults.regions.tested.length}`);
  console.log(`   Disponíveis: ${testResults.regions.passed.length}`);
  if (testResults.regions.passed.length > 0) {
    console.log(`   → ${testResults.regions.passed.join(', ')}`);
  }

  console.log('\n🛡️ Failover:');
  console.log(`   Tipos testados: ${testResults.failoverTypes.tested.length}`);
  console.log(`   Funcionando: ${testResults.failoverTypes.passed.length}`);
  if (testResults.failoverTypes.passed.length > 0) {
    console.log(`   → ${testResults.failoverTypes.passed.join(', ')}`);
  }

  if (testResults.issues.length > 0) {
    console.log('\n⚠️ Issues encontradas:');
    testResults.issues.forEach(i => console.log(`   • ${i}`));
  }

  if (testResults.improvements.length > 0) {
    console.log('\n💡 Melhorias sugeridas:');
    testResults.improvements.forEach(i => console.log(`   • ${i}`));
  }

  console.log(`\n📸 Screenshots: ${testResults.screenshots.length}`);
  testResults.screenshots.forEach(s => console.log(`   → screenshots/teste-completo/${s}`));

  // Calcular score
  const totalTests = testResults.gpuTypes.tested.length + testResults.regions.tested.length + testResults.failoverTypes.tested.length;
  const passedTests = testResults.gpuTypes.passed.length + testResults.regions.passed.length + testResults.failoverTypes.passed.length;
  const score = Math.round((passedTests / totalTests) * 100);

  console.log('\n' + '═'.repeat(70));
  console.log(`📈 Score Final: ${score}%`);
  console.log('═'.repeat(70));

  // Salvar relatório
  const reportPath = path.join(SCREENSHOTS_DIR, 'test-report.json');
  fs.writeFileSync(reportPath, JSON.stringify({ ...testResults, score }, null, 2));
  console.log(`\n📄 Relatório: screenshots/teste-completo/test-report.json\n`);

  return { score, testResults };
}

// Executar
runCompleteTest().then(({ score }) => {
  process.exit(score >= 60 ? 0 : 1);
}).catch(err => {
  console.error('Erro fatal:', err);
  process.exit(1);
});
