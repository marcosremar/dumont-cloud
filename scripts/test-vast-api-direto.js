#!/usr/bin/env node
/**
 * Teste DIRETO via API VAST.ai
 *
 * Usa a API key da VAST.ai para:
 * 1. Listar ofertas de GPU disponíveis
 * 2. Criar uma máquina de teste (mais barata)
 * 3. Verificar status
 * 4. Destruir a máquina
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

// Carregar .env
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const VAST_API_KEY = process.env.VAST_API_KEY;
const SCREENSHOTS_DIR = path.join(__dirname, '..', 'screenshots', 'teste-api');

if (!VAST_API_KEY) {
  console.error('❌ VAST_API_KEY não encontrada no .env');
  process.exit(1);
}

// Criar diretório
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

const results = {
  timestamp: new Date().toISOString(),
  offers: [],
  machinesCreated: [],
  machinesDestroyed: [],
  errors: [],
};

// Helper para fazer requests à API VAST
function vastRequest(method, endpoint, data = null) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'console.vast.ai',
      port: 443,
      path: `/api/v0${endpoint}`,
      method: method,
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${VAST_API_KEY}`,
      },
    };

    if (data) {
      options.headers['Content-Type'] = 'application/json';
    }

    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(body);
          if (res.statusCode >= 400) {
            reject(new Error(`HTTP ${res.statusCode}: ${JSON.stringify(json)}`));
          } else {
            resolve(json);
          }
        } catch (e) {
          resolve(body);
        }
      });
    });

    req.on('error', reject);

    if (data) {
      req.write(JSON.stringify(data));
    }

    req.end();
  });
}

async function runTest() {
  console.log('═'.repeat(70));
  console.log('🔴 TESTE DIRETO API VAST.ai');
  console.log('═'.repeat(70));
  console.log(`⚠️  ATENÇÃO: Este teste USA CRÉDITOS REAIS!`);
  console.log(`📅 ${new Date().toLocaleString()}\n`);

  try {
    // ==========================================
    // FASE 1: Verificar saldo
    // ==========================================
    console.log('\n📋 FASE 1: Verificando saldo');
    console.log('─'.repeat(50));

    const userInfo = await vastRequest('GET', '/users/current/');
    console.log(`   💰 Saldo: $${userInfo.credit?.toFixed(2) || 'N/A'}`);
    console.log(`   📧 Email: ${userInfo.email || 'N/A'}`);

    if (userInfo.credit < 0.10) {
      console.log('❌ Saldo insuficiente para teste (mínimo $0.10)');
      results.errors.push('Saldo insuficiente');
      return results;
    }

    // ==========================================
    // FASE 2: Listar instâncias existentes
    // ==========================================
    console.log('\n📋 FASE 2: Listando instâncias existentes');
    console.log('─'.repeat(50));

    const instances = await vastRequest('GET', '/instances/');
    console.log(`   📊 Instâncias ativas: ${instances.instances?.length || 0}`);

    if (instances.instances?.length > 0) {
      for (const inst of instances.instances) {
        console.log(`   → ${inst.machine_id}: ${inst.gpu_name} (${inst.actual_status})`);
      }
    }

    // ==========================================
    // FASE 3: Buscar ofertas de GPU mais baratas
    // ==========================================
    console.log('\n📋 FASE 3: Buscando GPUs mais baratas');
    console.log('─'.repeat(50));

    // Buscar ofertas com filtro de preço baixo
    // Formato correto da API VAST.ai: operadores como {"eq": true}
    const query = encodeURIComponent(JSON.stringify({
      rentable: { eq: true },
      order: [["dph_total", "asc"]],
      limit: 10
    }));
    const offers = await vastRequest('GET', `/bundles/?q=${query}`);

    if (offers.offers?.length > 0) {
      console.log(`   📊 Ofertas encontradas: ${offers.offers.length}`);

      // Mostrar top 5 mais baratas
      const top5 = offers.offers.slice(0, 5);
      for (const offer of top5) {
        console.log(`   → ${offer.gpu_name}: $${offer.dph_total?.toFixed(3)}/h (${offer.num_gpus}x GPU, ${offer.gpu_ram}MB VRAM)`);
        results.offers.push({
          id: offer.id,
          gpu: offer.gpu_name,
          price: offer.dph_total,
          vram: offer.gpu_ram,
        });
      }

      // ==========================================
      // FASE 4: Criar instância de teste
      // ==========================================
      console.log('\n📋 FASE 4: Criando instância de teste');
      console.log('─'.repeat(50));

      // Selecionar a mais barata
      const cheapest = top5[0];
      console.log(`   🎯 Selecionada: ${cheapest.gpu_name} por $${cheapest.dph_total?.toFixed(3)}/h`);

      // Configuração mínima para teste
      const createRequest = {
        client_id: 'me',
        image: 'pytorch/pytorch:latest',
        disk: 10, // Mínimo de disco
        label: 'TEST-CLAUDE-AUTO',
      };

      console.log('   ⏳ Criando instância...');

      try {
        const createResult = await vastRequest('PUT', `/asks/${cheapest.id}/`, createRequest);
        console.log('   ✅ Instância criada!');
        console.log(`   → ID: ${createResult.new_contract}`);

        results.machinesCreated.push({
          id: createResult.new_contract,
          gpu: cheapest.gpu_name,
          price: cheapest.dph_total,
          timestamp: new Date().toISOString(),
        });

        // ==========================================
        // FASE 5: Aguardar inicialização (30s)
        // ==========================================
        console.log('\n📋 FASE 5: Aguardando inicialização');
        console.log('─'.repeat(50));

        await new Promise(r => setTimeout(r, 30000));

        // Verificar status
        const updatedInstances = await vastRequest('GET', '/instances/');
        const newInstance = updatedInstances.instances?.find(i => i.id === createResult.new_contract);

        if (newInstance) {
          console.log(`   📊 Status: ${newInstance.actual_status}`);
          console.log(`   📍 Host: ${newInstance.ssh_host || 'N/A'}`);
          console.log(`   🔑 SSH Port: ${newInstance.ssh_port || 'N/A'}`);
        }

        // ==========================================
        // FASE 6: Destruir instância
        // ==========================================
        console.log('\n📋 FASE 6: Destruindo instância de teste');
        console.log('─'.repeat(50));

        await vastRequest('DELETE', `/instances/${createResult.new_contract}/`);
        console.log('   ✅ Instância destruída!');

        results.machinesDestroyed.push({
          id: createResult.new_contract,
          timestamp: new Date().toISOString(),
        });

      } catch (createError) {
        console.log(`   ❌ Erro ao criar: ${createError.message}`);
        results.errors.push(createError.message);
      }

    } else {
      console.log('   ⚠️  Nenhuma oferta disponível');
      results.errors.push('Sem ofertas disponíveis');
    }

  } catch (error) {
    console.error(`\n❌ Erro: ${error.message}`);
    results.errors.push(error.message);
  }

  // ==========================================
  // RESUMO
  // ==========================================
  console.log('\n' + '═'.repeat(70));
  console.log('📊 RESUMO DO TESTE');
  console.log('═'.repeat(70));

  console.log(`\n🎮 Ofertas encontradas: ${results.offers.length}`);
  console.log(`✅ Máquinas criadas: ${results.machinesCreated.length}`);
  console.log(`🗑️  Máquinas destruídas: ${results.machinesDestroyed.length}`);

  if (results.errors.length > 0) {
    console.log(`\n❌ Erros: ${results.errors.length}`);
    results.errors.forEach(e => console.log(`   ✗ ${e}`));
  }

  console.log('\n' + '═'.repeat(70));

  // Salvar relatório
  const reportPath = path.join(SCREENSHOTS_DIR, 'test-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`📄 Relatório: screenshots/teste-api/test-report.json\n`);

  return results;
}

// Executar
runTest().then(results => {
  const exitCode = results.errors.length > 0 ? 1 : 0;
  process.exit(exitCode);
}).catch(err => {
  console.error('Erro fatal:', err);
  process.exit(1);
});
