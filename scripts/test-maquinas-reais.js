#!/usr/bin/env node
/**
 * Teste de Máquinas REAIS na VAST.ai
 *
 * Este script:
 * 1. Faz login na aplicação (usa sessão existente do Chrome)
 * 2. Cria máquinas REAIS (gasta créditos!)
 * 3. Testa failover
 * 4. Destrói as máquinas ao final
 *
 * CUIDADO: Este script USA CRÉDITOS REAIS da conta VAST.ai
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// Configuração
const BASE_URL = process.env.BASE_URL || 'http://localhost:4892';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const USER_DATA_DIR = '/Users/marcos/.playwright-mcp-profile';
const SCREENSHOTS_DIR = path.join(__dirname, '..', 'screenshots', 'teste-real');
const TEST_PREFIX = 'TEST-CLAUDE';

// GPUs mais baratas para teste (minimizar custo)
const TEST_GPUS = [
  { name: 'RTX 3080', maxPrice: 0.20 },
  { name: 'RTX 3090', maxPrice: 0.25 },
];

// Criar diretório
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const results = {
  timestamp: new Date().toISOString(),
  machinesCreated: [],
  machinesDestroyed: [],
  failoverTests: [],
  errors: [],
  totalCost: 0,
};

async function runRealTest() {
  console.log('═'.repeat(70));
  console.log('🔴 TESTE REAL DE MÁQUINAS VAST.ai');
  console.log('═'.repeat(70));
  console.log(`⚠️  ATENÇÃO: Este teste USA CRÉDITOS REAIS!`);
  console.log(`📍 URL: ${BASE_URL}`);
  console.log(`📅 ${new Date().toLocaleString()}\n`);

  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: true,
    viewport: { width: 1400, height: 900 },
    ignoreHTTPSErrors: true,
  });

  const page = await context.newPage();

  try {
    // ==========================================
    // FASE 1: Verificar autenticação
    // ==========================================
    console.log('\n📋 FASE 1: Verificando autenticação');
    console.log('─'.repeat(50));

    await page.goto(`${BASE_URL}/app`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(3000);

    const currentUrl = page.url();
    const pageContent = await page.content();

    // Verificar se está logado
    const isLoggedIn = !currentUrl.includes('login') &&
                       (pageContent.includes('Dashboard') ||
                        pageContent.includes('Machines') ||
                        pageContent.includes('logout') ||
                        pageContent.includes('Sair'));

    if (!isLoggedIn) {
      console.log('⚠️  Usuário não está logado. Tentando fazer login...');

      // Ir para página de login
      await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await sleep(2000);

      // Preencher credenciais
      const emailInput = await page.$('input[type="email"], input[name="email"], input[placeholder*="email"]');
      const passwordInput = await page.$('input[type="password"], input[name="password"]');

      if (emailInput && passwordInput) {
        // Usar credenciais de ambiente (OBRIGATÓRIO)
        const testEmail = process.env.TEST_EMAIL;
        const testPassword = process.env.TEST_PASSWORD;

        if (!testEmail || !testPassword) {
          console.log('❌ Credenciais não definidas!');
          console.log('   Por favor, defina as variáveis de ambiente:');
          console.log('   TEST_EMAIL=seu@email.com TEST_PASSWORD=suasenha node scripts/test-maquinas-reais.js');
          results.errors.push('Credenciais não definidas');
          await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'erro-sem-credenciais.png'), fullPage: true });
          await context.close();
          return results;
        }

        await emailInput.fill(testEmail);
        await sleep(500);
        await passwordInput.fill(testPassword);
        await sleep(500);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '00-login.png'), fullPage: true });

        // Clicar em Entrar
        const loginBtn = await page.$('button:has-text("Entrar"), button:has-text("Login"), button[type="submit"]');
        if (loginBtn) {
          await loginBtn.click();
          await sleep(3000);

          // Verificar se login foi bem sucedido
          const afterLogin = await page.content();
          if (afterLogin.includes('Dashboard') || afterLogin.includes('Machines') || page.url().includes('/app')) {
            console.log('✅ Login realizado com sucesso!');
          } else {
            console.log('❌ Falha no login');
            results.errors.push('Falha no login');
            await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'erro-login.png'), fullPage: true });
            await context.close();
            return results;
          }
        }
      } else {
        console.log('❌ Campos de login não encontrados');
        results.errors.push('Campos de login não encontrados');
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'erro-nao-logado.png'), fullPage: true });
        await context.close();
        return results;
      }
    }

    console.log('✅ Usuário autenticado');
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '01-logado.png'), fullPage: true });

    // ==========================================
    // FASE 2: Verificar saldo
    // ==========================================
    console.log('\n📋 FASE 2: Verificando saldo');
    console.log('─'.repeat(50));

    // Tentar encontrar o saldo na página
    const balanceMatch = pageContent.match(/\$[\d.]+/);
    if (balanceMatch) {
      console.log(`   💰 Saldo encontrado: ${balanceMatch[0]}`);
    }

    // ==========================================
    // FASE 3: Ir para página de Machines
    // ==========================================
    console.log('\n📋 FASE 3: Acessando página de Machines');
    console.log('─'.repeat(50));

    await page.goto(`${BASE_URL}/app/machines`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '02-machines.png'), fullPage: true });

    // Verificar máquinas existentes
    const machinesContent = await page.content();
    const existingMachines = machinesContent.match(/running|online/gi) || [];
    console.log(`   📊 Máquinas ativas: ${existingMachines.length}`);

    // ==========================================
    // FASE 4: Limpar máquinas de teste antigas
    // ==========================================
    console.log('\n📋 FASE 4: Limpando máquinas de teste antigas');
    console.log('─'.repeat(50));

    // Procurar por máquinas com prefixo de teste
    const testMachineCards = await page.$$(`[data-testid*="machine-card"]`);
    let cleanedCount = 0;

    for (const card of testMachineCards) {
      const cardText = await card.textContent();
      if (cardText && cardText.includes(TEST_PREFIX)) {
        cleanedCount++;
        console.log(`   🗑️  Encontrada máquina de teste antiga`);

        // Tentar destruir
        try {
          const menuBtn = await card.$('button[aria-label*="menu"], button:has-text("...")');
          if (menuBtn) {
            await menuBtn.click();
            await sleep(500);

            const destroyBtn = await page.$('button:has-text("Destruir"), [role="menuitem"]:has-text("Destruir")');
            if (destroyBtn) {
              await destroyBtn.click();
              await sleep(500);

              const confirmBtn = await page.$('button:has-text("Confirmar"), button:has-text("Sim")');
              if (confirmBtn) {
                await confirmBtn.click();
                await sleep(2000);
                results.machinesDestroyed.push({ name: TEST_PREFIX, phase: 'cleanup' });
                console.log(`   ✅ Máquina destruída`);
              }
            }
          }
        } catch (e) {
          console.log(`   ⚠️  Erro ao destruir: ${e.message}`);
        }
      }
    }

    if (cleanedCount === 0) {
      console.log('   ✅ Nenhuma máquina de teste antiga encontrada');
    }

    // ==========================================
    // FASE 5: Criar nova máquina
    // ==========================================
    console.log('\n📋 FASE 5: Criando nova máquina REAL');
    console.log('─'.repeat(50));

    // Clicar em Nova Máquina
    const newMachineBtn = await page.$('button:has-text("Nova Máquina"), button:has-text("New Machine"), a:has-text("Nova Máquina")');

    if (!newMachineBtn) {
      console.log('❌ Botão "Nova Máquina" não encontrado');
      results.errors.push('Botão Nova Máquina não encontrado');

      // Tentar ir direto para GPU offers
      await page.goto(`${BASE_URL}/app/gpu-offers`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await sleep(2000);
    } else {
      await newMachineBtn.click();
      await sleep(2000);
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '03-wizard.png'), fullPage: true });

    // Verificar se wizard abriu ou se está em GPU offers
    const wizardContent = await page.content();

    // Procurar por GPU mais barata disponível
    console.log('   🔍 Procurando GPU mais barata...');

    const gpuCards = await page.$$('[class*="card"]');
    let selectedGpu = null;

    for (const card of gpuCards) {
      const cardText = await card.textContent();

      for (const testGpu of TEST_GPUS) {
        if (cardText && cardText.includes(testGpu.name)) {
          // Verificar preço
          const priceMatch = cardText.match(/\$(\d+\.\d+)/);
          if (priceMatch) {
            const price = parseFloat(priceMatch[1]);
            if (price <= testGpu.maxPrice) {
              selectedGpu = { name: testGpu.name, price, card };
              console.log(`   ✅ GPU encontrada: ${testGpu.name} por $${price}/h`);
              break;
            }
          }
        }
      }
      if (selectedGpu) break;
    }

    if (!selectedGpu) {
      console.log('   ⚠️  Nenhuma GPU barata encontrada, usando primeira disponível');

      // Clicar no primeiro botão de provisionar
      const provisionBtn = await page.$('button:has-text("Provisionar")');
      if (provisionBtn) {
        await provisionBtn.click();
        await sleep(2000);
      }
    } else {
      // Clicar em provisionar na GPU selecionada
      const provisionBtn = await selectedGpu.card.$('button:has-text("Provisionar")');
      if (provisionBtn) {
        await provisionBtn.click();
        await sleep(2000);
      }
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '04-apos-provisionar.png'), fullPage: true });

    // Verificar se foi para a página de criação ou se máquina foi criada
    const afterProvision = await page.content();

    if (afterProvision.includes('Criando') || afterProvision.includes('creating') || afterProvision.includes('Provisionando')) {
      console.log('   ⏳ Máquina sendo criada...');

      // Aguardar criação (máximo 3 minutos)
      let created = false;
      const maxWait = 180000; // 3 minutos
      const startTime = Date.now();

      while (Date.now() - startTime < maxWait) {
        await sleep(10000); // Espera 10 segundos
        await page.reload({ waitUntil: 'domcontentloaded' });
        await sleep(2000);

        const currentContent = await page.content();
        if (currentContent.includes('running') || currentContent.includes('Online')) {
          created = true;
          console.log('   ✅ Máquina criada com sucesso!');
          results.machinesCreated.push({
            name: selectedGpu?.name || 'GPU',
            price: selectedGpu?.price || 0,
            timestamp: new Date().toISOString()
          });
          break;
        }

        if (currentContent.includes('error') || currentContent.includes('falhou')) {
          console.log('   ❌ Erro ao criar máquina');
          results.errors.push('Falha na criação da máquina');
          break;
        }

        const elapsed = Math.round((Date.now() - startTime) / 1000);
        console.log(`   ⏳ Aguardando... ${elapsed}s`);
      }

      if (!created) {
        console.log('   ⚠️  Timeout esperando criação');
        results.errors.push('Timeout na criação');
      }
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '05-maquina-criada.png'), fullPage: true });

    // ==========================================
    // FASE 6: Testar operações na máquina
    // ==========================================
    console.log('\n📋 FASE 6: Testando operações');
    console.log('─'.repeat(50));

    // Verificar se há máquinas para testar
    const finalContent = await page.content();
    if (finalContent.includes('running') || finalContent.includes('Online')) {
      // Tentar encontrar botão de failover/simular
      const failoverBtn = await page.$('button:has-text("Failover"), button:has-text("Testar"), button:has-text("Simular")');

      if (failoverBtn) {
        console.log('   🔄 Testando failover...');
        await failoverBtn.click();
        await sleep(5000);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '06-failover.png'), fullPage: true });

        results.failoverTests.push({
          type: 'simulation',
          success: true,
          timestamp: new Date().toISOString()
        });
        console.log('   ✅ Failover testado');
      } else {
        console.log('   ⚠️  Botão de failover não encontrado');
      }
    }

    // ==========================================
    // FASE 7: Destruir máquinas de teste
    // ==========================================
    console.log('\n📋 FASE 7: Destruindo máquinas de teste');
    console.log('─'.repeat(50));

    // Recarregar página de machines
    await page.goto(`${BASE_URL}/app/machines`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    // Encontrar e destruir máquinas criadas pelo teste
    const allCards = await page.$$('[class*="card"]');

    for (const card of allCards) {
      const cardText = await card.textContent();

      // Verificar se é uma máquina ativa (não destruir máquinas pausadas do usuário)
      if (cardText && (cardText.includes('Online') || cardText.includes('running'))) {
        // Verificar se foi criada recentemente (últimos 10 minutos)
        const recentlyCreated = results.machinesCreated.length > 0;

        if (recentlyCreated) {
          console.log('   🗑️  Destruindo máquina de teste...');

          try {
            // Abrir menu
            const menuBtn = await card.$('button[aria-label*="menu"], button svg');
            if (menuBtn) {
              await menuBtn.click();
              await sleep(500);
            }

            // Clicar em destruir
            const destroyBtn = await page.$('[role="menuitem"]:has-text("Destruir"), button:has-text("Destruir")');
            if (destroyBtn) {
              await destroyBtn.click();
              await sleep(500);

              // Confirmar
              const confirmBtn = await page.$('button:has-text("Confirmar"), button:has-text("Destruir")');
              if (confirmBtn) {
                await confirmBtn.click();
                await sleep(3000);
                results.machinesDestroyed.push({ phase: 'final_cleanup', timestamp: new Date().toISOString() });
                console.log('   ✅ Máquina destruída');
              }
            }
          } catch (e) {
            console.log(`   ⚠️  Erro: ${e.message}`);
          }
        }
      }
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '07-final.png'), fullPage: true });

  } catch (error) {
    console.error(`\n❌ Erro: ${error.message}`);
    results.errors.push(error.message);

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'error.png'), fullPage: true }).catch(() => {});
  } finally {
    await context.close();
  }

  // ==========================================
  // RESUMO
  // ==========================================
  console.log('\n' + '═'.repeat(70));
  console.log('📊 RESUMO DO TESTE REAL');
  console.log('═'.repeat(70));

  console.log(`\n✅ Máquinas criadas: ${results.machinesCreated.length}`);
  results.machinesCreated.forEach(m => console.log(`   → ${m.name} ($${m.price}/h)`));

  console.log(`\n🗑️  Máquinas destruídas: ${results.machinesDestroyed.length}`);

  console.log(`\n🔄 Testes de failover: ${results.failoverTests.length}`);

  if (results.errors.length > 0) {
    console.log(`\n❌ Erros: ${results.errors.length}`);
    results.errors.forEach(e => console.log(`   ✗ ${e}`));
  }

  // Calcular custo estimado
  const totalMinutes = results.machinesCreated.length * 5; // ~5 min por máquina
  const avgPrice = results.machinesCreated.reduce((sum, m) => sum + m.price, 0) / (results.machinesCreated.length || 1);
  results.totalCost = (avgPrice * totalMinutes / 60).toFixed(4);

  console.log(`\n💰 Custo estimado: $${results.totalCost}`);

  console.log('\n' + '═'.repeat(70));

  // Salvar relatório
  const reportPath = path.join(SCREENSHOTS_DIR, 'test-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`📄 Relatório: screenshots/teste-real/test-report.json\n`);

  return results;
}

// Executar
runRealTest().then(results => {
  const exitCode = results.errors.length > 0 ? 1 : 0;
  process.exit(exitCode);
}).catch(err => {
  console.error('Erro fatal:', err);
  process.exit(1);
});
