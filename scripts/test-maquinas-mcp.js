#!/usr/bin/env node
/**
 * Script para testar funcionalidades de reserva de máquinas GPU/CPU
 * Controla o Playwright MCP com Chrome em modo Headless
 */

const { spawn } = require('child_process');

// Configuração
const BASE_URL = 'http://localhost:5173';
const USER_DATA_DIR = '/Users/marcos/.playwright-mcp-profile';

class PlaywrightMCPController {
  constructor() {
    this.mcpProcess = null;
    this.requestId = 0;
    this.pendingRequests = new Map();
    this.buffer = '';
  }

  async start() {
    return new Promise((resolve, reject) => {
      console.log('🚀 Iniciando Playwright MCP em modo headless...');

      this.mcpProcess = spawn('npx', [
        '@playwright/mcp@latest',
        '--headless',
        '--user-data-dir', USER_DATA_DIR
      ], {
        stdio: ['pipe', 'pipe', 'pipe']
      });

      this.mcpProcess.stdout.on('data', (data) => {
        this.buffer += data.toString();
        this.processBuffer();
      });

      this.mcpProcess.stderr.on('data', (data) => {
        const msg = data.toString();
        if (msg.includes('Listening') || msg.includes('ready')) {
          console.log('✅ MCP Server pronto');
          resolve();
        }
        // Log erros importantes
        if (msg.includes('Error') || msg.includes('error')) {
          console.error('⚠️ MCP:', msg.trim());
        }
      });

      this.mcpProcess.on('error', reject);

      // Timeout para inicialização
      setTimeout(() => resolve(), 2000);
    });
  }

  processBuffer() {
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.trim()) {
        try {
          const response = JSON.parse(line);
          if (response.id && this.pendingRequests.has(response.id)) {
            const { resolve, reject } = this.pendingRequests.get(response.id);
            this.pendingRequests.delete(response.id);
            if (response.error) {
              reject(new Error(response.error.message));
            } else {
              resolve(response.result);
            }
          }
        } catch (e) {
          // Ignorar linhas não-JSON
        }
      }
    }
  }

  async call(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++this.requestId;
      const request = {
        jsonrpc: '2.0',
        id,
        method,
        params
      };

      this.pendingRequests.set(id, { resolve, reject });
      this.mcpProcess.stdin.write(JSON.stringify(request) + '\n');

      // Timeout de 30 segundos
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error('Timeout'));
        }
      }, 30000);
    });
  }

  async callTool(name, args = {}) {
    return this.call('tools/call', { name, arguments: args });
  }

  async navigate(url) {
    console.log(`📍 Navegando para: ${url}`);
    return this.callTool('browser_navigate', { url });
  }

  async snapshot() {
    return this.callTool('browser_snapshot', {});
  }

  async click(element, ref) {
    console.log(`🖱️ Clicando em: ${element}`);
    return this.callTool('browser_click', { element, ref });
  }

  async type(element, ref, text) {
    console.log(`⌨️ Digitando em: ${element}`);
    return this.callTool('browser_type', { element, ref, text });
  }

  async waitFor(text) {
    console.log(`⏳ Aguardando: ${text}`);
    return this.callTool('browser_wait_for', { text });
  }

  async screenshot(filename) {
    console.log(`📸 Screenshot: ${filename}`);
    return this.callTool('browser_take_screenshot', { filename });
  }

  async close() {
    if (this.mcpProcess) {
      this.mcpProcess.kill();
      console.log('🔴 MCP encerrado');
    }
  }
}

// Função para extrair ref de um elemento no snapshot
function findRef(snapshotText, searchText) {
  const lines = snapshotText.split('\n');
  for (const line of lines) {
    if (line.toLowerCase().includes(searchText.toLowerCase())) {
      const match = line.match(/\[ref=([^\]]+)\]/);
      if (match) return match[1];
    }
  }
  return null;
}

// Testes principais
async function runTests() {
  const mcp = new PlaywrightMCPController();
  const results = {
    passed: [],
    failed: [],
    screenshots: []
  };

  try {
    await mcp.start();

    // 1. Navegar para a aplicação
    console.log('\n📋 TESTE 1: Navegação para a aplicação');
    await mcp.navigate(BASE_URL);
    await new Promise(r => setTimeout(r, 2000));

    let snapshot = await mcp.snapshot();
    let snapshotText = JSON.stringify(snapshot);
    console.log('Snapshot inicial obtido');

    // Verificar se carregou
    if (snapshotText.includes('Dumont') || snapshotText.includes('Dashboard') || snapshotText.includes('Máquinas')) {
      results.passed.push('Aplicação carregou corretamente');
      console.log('✅ Aplicação carregou');
    } else {
      results.failed.push('Aplicação não carregou corretamente');
      console.log('❌ Aplicação não carregou');
    }

    // 2. Navegar para página de Máquinas/GPUs
    console.log('\n📋 TESTE 2: Página de Máquinas/GPUs');

    // Tentar encontrar link para Máquinas
    snapshot = await mcp.snapshot();
    snapshotText = JSON.stringify(snapshot);

    // Procurar por links de navegação
    const maquinasRef = findRef(snapshotText, 'Máquinas') || findRef(snapshotText, 'GPUs') || findRef(snapshotText, 'Machines');

    if (maquinasRef) {
      await mcp.click('Máquinas/GPUs', maquinasRef);
      await new Promise(r => setTimeout(r, 2000));
      results.passed.push('Link para Máquinas encontrado');
    } else {
      // Tentar navegar direto
      await mcp.navigate(`${BASE_URL}/machines`);
      await new Promise(r => setTimeout(r, 2000));
    }

    snapshot = await mcp.snapshot();
    snapshotText = JSON.stringify(snapshot);
    await mcp.screenshot('screenshots/01-pagina-maquinas.png');
    results.screenshots.push('01-pagina-maquinas.png');

    // 3. Verificar lista de GPUs disponíveis
    console.log('\n📋 TESTE 3: Lista de GPUs disponíveis');

    if (snapshotText.includes('GPU') || snapshotText.includes('RTX') || snapshotText.includes('A100') || snapshotText.includes('H100')) {
      results.passed.push('Lista de GPUs visível');
      console.log('✅ GPUs listadas');
    } else {
      results.failed.push('Lista de GPUs não encontrada');
      console.log('❌ GPUs não listadas');
    }

    // 4. Verificar opções de reserva
    console.log('\n📋 TESTE 4: Opções de reserva de máquinas');

    // Procurar botão de Deploy/Reservar
    const deployRef = findRef(snapshotText, 'Deploy') || findRef(snapshotText, 'Reservar') || findRef(snapshotText, 'Alugar');

    if (deployRef) {
      results.passed.push('Botão de Deploy/Reservar encontrado');
      console.log('✅ Botão de reserva encontrado');

      await mcp.click('Botão Deploy', deployRef);
      await new Promise(r => setTimeout(r, 2000));

      snapshot = await mcp.snapshot();
      snapshotText = JSON.stringify(snapshot);
      await mcp.screenshot('screenshots/02-wizard-reserva.png');
      results.screenshots.push('02-wizard-reserva.png');
    } else {
      results.failed.push('Botão de Deploy/Reservar não encontrado');
      console.log('❌ Botão de reserva não encontrado');
    }

    // 5. Verificar opções GPU vs CPU
    console.log('\n📋 TESTE 5: Opções GPU vs CPU');

    if (snapshotText.includes('GPU') && (snapshotText.includes('CPU') || snapshotText.includes('Standby'))) {
      results.passed.push('Opções GPU e CPU disponíveis');
      console.log('✅ Opções GPU/CPU disponíveis');
    } else if (snapshotText.includes('GPU')) {
      results.passed.push('Opção GPU disponível');
      console.log('✅ Opção GPU disponível');
    }

    // 6. Verificar wizard de configuração
    console.log('\n📋 TESTE 6: Wizard de configuração de máquina');

    // Verificar se há steps/etapas no wizard
    const hasWizard = snapshotText.includes('Step') || snapshotText.includes('Etapa') ||
                      snapshotText.includes('Próximo') || snapshotText.includes('Next') ||
                      snapshotText.includes('Modelo') || snapshotText.includes('Hardware');

    if (hasWizard) {
      results.passed.push('Wizard de configuração funcional');
      console.log('✅ Wizard funcionando');

      await mcp.screenshot('screenshots/03-wizard-config.png');
      results.screenshots.push('03-wizard-config.png');
    } else {
      results.failed.push('Wizard de configuração não encontrado');
      console.log('❌ Wizard não encontrado');
    }

    // 7. Testar navegação para outras seções
    console.log('\n📋 TESTE 7: Navegação entre seções');

    // Tentar ir para Models
    await mcp.navigate(`${BASE_URL}/models`);
    await new Promise(r => setTimeout(r, 2000));

    snapshot = await mcp.snapshot();
    snapshotText = JSON.stringify(snapshot);

    if (snapshotText.includes('Model') || snapshotText.includes('Modelo') || snapshotText.includes('LLM')) {
      results.passed.push('Página de Modelos acessível');
      console.log('✅ Página de Modelos OK');
    }

    await mcp.screenshot('screenshots/04-pagina-modelos.png');
    results.screenshots.push('04-pagina-modelos.png');

    // 8. Verificar Chat Arena
    console.log('\n📋 TESTE 8: Chat Arena');

    await mcp.navigate(`${BASE_URL}/chat-arena`);
    await new Promise(r => setTimeout(r, 2000));

    snapshot = await mcp.snapshot();
    snapshotText = JSON.stringify(snapshot);

    if (snapshotText.includes('Chat') || snapshotText.includes('Arena') || snapshotText.includes('Message')) {
      results.passed.push('Chat Arena acessível');
      console.log('✅ Chat Arena OK');
    }

    await mcp.screenshot('screenshots/05-chat-arena.png');
    results.screenshots.push('05-chat-arena.png');

    // Resumo
    console.log('\n' + '='.repeat(50));
    console.log('📊 RESUMO DOS TESTES');
    console.log('='.repeat(50));
    console.log(`✅ Passou: ${results.passed.length}`);
    results.passed.forEach(t => console.log(`   - ${t}`));
    console.log(`❌ Falhou: ${results.failed.length}`);
    results.failed.forEach(t => console.log(`   - ${t}`));
    console.log(`📸 Screenshots: ${results.screenshots.length}`);
    results.screenshots.forEach(s => console.log(`   - ${s}`));
    console.log('='.repeat(50));

  } catch (error) {
    console.error('❌ Erro durante os testes:', error.message);
    results.failed.push(`Erro: ${error.message}`);
  } finally {
    await mcp.close();
  }

  return results;
}

// Executar
runTests().then(results => {
  const exitCode = results.failed.length > 0 ? 1 : 0;
  process.exit(exitCode);
}).catch(err => {
  console.error('Erro fatal:', err);
  process.exit(1);
});
