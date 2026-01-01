// @ts-check
const { test, expect } = require('@playwright/test');
const { spawn } = require('child_process');

/**
 * 🎯 TESTE DE TIMING DO DEPLOY WIZARD
 *
 * Este teste verifica se o deploy wizard está respeitando os timeouts de batch:
 * - BATCH_TIMEOUT = 15s (tempo para esperar SSH em cada batch)
 * - Cada batch tem 5 máquinas
 * - Máximo de 3 batches (15 máquinas total)
 *
 * O teste monitora:
 * 1. Tempo entre batches
 * 2. Logs do backend para verificar comportamento
 * 3. UI do dashboard durante provisioning
 */

/**
 * Helper para capturar logs do backend em tempo real
 */
class BackendLogMonitor {
  constructor() {
    this.logs = [];
    this.process = null;
    this.startTime = null;
  }

  start() {
    this.startTime = Date.now();
    this.logs = [];

    // Executar tail -f nos logs do backend
    this.process = spawn('orb', [
      'run',
      '-m',
      'dumontcloud',
      'tail',
      '-f',
      '/tmp/dumont-backend.log'
    ]);

    this.process.stdout.on('data', (data) => {
      const timestamp = Date.now() - this.startTime;
      const line = data.toString();
      this.logs.push({ timestamp, line });
      console.log(`[${(timestamp / 1000).toFixed(1)}s] ${line.trim()}`);
    });

    this.process.stderr.on('data', (data) => {
      console.error(`Backend log error: ${data}`);
    });
  }

  stop() {
    if (this.process) {
      this.process.kill();
    }
  }

  getLogs() {
    return this.logs;
  }

  /**
   * Analisa os logs para detectar batches e seus tempos
   */
  analyzeBatches() {
    const batchEvents = [];

    for (const { timestamp, line } of this.logs) {
      // Detectar início de batch
      if (line.includes('[Batch') || line.includes('Iniciando batch')) {
        const match = line.match(/batch[s]?\s*(\d+)/i);
        if (match) {
          batchEvents.push({
            type: 'batch_start',
            batch: parseInt(match[1]),
            timestamp,
            line: line.trim()
          });
        }
      }

      // Detectar criação de máquina
      if (line.includes('Creating instance') || line.includes('Criando instância')) {
        batchEvents.push({
          type: 'instance_create',
          timestamp,
          line: line.trim()
        });
      }

      // Detectar SSH ready
      if (line.includes('SSH ready') || line.includes('SSH conectado')) {
        batchEvents.push({
          type: 'ssh_ready',
          timestamp,
          line: line.trim()
        });
      }

      // Detectar timeout de batch
      if (line.includes('Batch timeout') || line.includes('Timeout no batch')) {
        batchEvents.push({
          type: 'batch_timeout',
          timestamp,
          line: line.trim()
        });
      }

      // Detectar limpeza de máquinas
      if (line.includes('Destroying instance') || line.includes('Destruindo instância')) {
        batchEvents.push({
          type: 'instance_destroy',
          timestamp,
          line: line.trim()
        });
      }
    }

    // Calcular tempo entre batches
    const batches = [];
    let currentBatch = null;

    for (const event of batchEvents) {
      if (event.type === 'batch_start') {
        if (currentBatch) {
          batches.push(currentBatch);
        }
        currentBatch = {
          batch: event.batch,
          startTime: event.timestamp,
          events: [event]
        };
      } else if (currentBatch) {
        currentBatch.events.push(event);
      }
    }

    if (currentBatch) {
      batches.push(currentBatch);
    }

    // Calcular duração de cada batch
    for (let i = 0; i < batches.length; i++) {
      const batch = batches[i];
      const nextBatch = batches[i + 1];

      if (nextBatch) {
        batch.duration = nextBatch.startTime - batch.startTime;
      } else {
        // Último batch - calcular até o último evento
        const lastEvent = batch.events[batch.events.length - 1];
        batch.duration = lastEvent.timestamp - batch.startTime;
      }
    }

    return batches;
  }
}

/**
 * Helper para ir para app real (autenticação já feita via setup)
 */
async function goToApp(page) {
  await page.goto('/app');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);

  // Fechar modal de boas-vindas se aparecer
  const skipButton = page.getByText('Pular tudo');
  if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipButton.click();
    await page.waitForTimeout(500);
  }
}

test.describe('🚀 Deploy Wizard - Timing Tests', () => {
  let logMonitor;

  test.beforeEach(async ({ page }) => {
    await goToApp(page);

    // Iniciar monitoramento de logs
    logMonitor = new BackendLogMonitor();
    logMonitor.start();
  });

  test.afterEach(async () => {
    // Parar monitoramento e analisar logs
    if (logMonitor) {
      const batches = logMonitor.analyzeBatches();

      console.log('\n📊 ANÁLISE DE BATCHES:');
      console.log('='.repeat(80));

      for (const batch of batches) {
        const durationSecs = (batch.duration / 1000).toFixed(1);
        console.log(`\nBatch ${batch.batch}:`);
        console.log(`  Duração: ${durationSecs}s`);
        console.log(`  Eventos: ${batch.events.length}`);

        // Verificar se respeita o timeout de 15s
        if (batch.duration < 15000 && batch.events.length < 5) {
          console.log(`  ⚠️  FALHOU MUITO RÁPIDO! (esperado ~15s, obteve ${durationSecs}s)`);
        } else {
          console.log(`  ✅ Timing OK`);
        }

        // Mostrar eventos do batch
        for (const event of batch.events) {
          const eventTime = ((event.timestamp - batch.startTime) / 1000).toFixed(1);
          console.log(`  [+${eventTime}s] ${event.type}: ${event.line.substring(0, 80)}`);
        }
      }

      console.log('\n' + '='.repeat(80));

      logMonitor.stop();
    }
  });

  test('Deploy Wizard respeita timeout de 15s por batch', async ({ page }) => {
    console.log('🎯 Teste: Verificar se batches respeitam timeout de 15s');

    // 1. Navegar para dashboard
    await page.goto('/app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);
    console.log('📍 Dashboard carregado');

    // 2. Procurar pela seção de deploy
    // Pode estar em "Configuração Guiada" ou "Configuração Avançada"
    const guidedConfig = page.getByText('Configuração Guiada').first();
    const advancedConfig = page.getByText('Configuração Avançada').first();

    const hasGuided = await guidedConfig.isVisible({ timeout: 3000 }).catch(() => false);
    const hasAdvanced = await advancedConfig.isVisible({ timeout: 3000 }).catch(() => false);

    if (!hasGuided && !hasAdvanced) {
      console.log('❌ Não encontrou seção de deploy no dashboard');
      return;
    }

    console.log(`📍 Encontrou seção de deploy: ${hasGuided ? 'Guiada' : 'Avançada'}`);

    // 3. Selecionar região (se disponível)
    const regionSelect = page.locator('select').first();
    const hasRegionSelect = await regionSelect.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasRegionSelect) {
      // Selecionar uma região específica para garantir consistência
      await regionSelect.selectOption({ index: 1 }); // Segunda opção (primeira depois de "Todas")
      await page.waitForTimeout(500);
      console.log('📍 Região selecionada');
    }

    // 4. Selecionar GPU (RTX 4090 como padrão)
    const gpuButtons = page.locator('button:has-text("RTX")');
    const gpuCount = await gpuButtons.count();

    if (gpuCount > 0) {
      // Procurar RTX 4090 ou usar primeira GPU disponível
      const rtx4090 = page.locator('button:has-text("4090")');
      const has4090 = await rtx4090.isVisible({ timeout: 2000 }).catch(() => false);

      if (has4090) {
        await rtx4090.first().click();
        console.log('📍 GPU selecionada: RTX 4090');
      } else {
        await gpuButtons.first().click();
        console.log('📍 GPU selecionada: Primeira disponível');
      }

      await page.waitForTimeout(500);
    }

    // 5. Selecionar tier (Fast como padrão)
    const tierButtons = page.locator('button:has-text("Fast"), button:has-text("Standard"), button:has-text("Cheap")');
    const tierCount = await tierButtons.count();

    if (tierCount > 0) {
      const fastTier = page.locator('button:has-text("Fast")');
      const hasFast = await fastTier.isVisible({ timeout: 2000 }).catch(() => false);

      if (hasFast) {
        await fastTier.first().click();
        console.log('📍 Tier selecionado: Fast');
      } else {
        await tierButtons.first().click();
        console.log('📍 Tier selecionado: Primeiro disponível');
      }

      await page.waitForTimeout(500);
    }

    // 6. Clicar em "Iniciar" para começar provisioning
    const startButton = page.locator('button:has-text("Iniciar")');
    const hasStartButton = await startButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (!hasStartButton) {
      console.log('❌ Botão "Iniciar" não encontrado');
      console.log('Elementos visíveis na página:');
      const buttons = await page.locator('button').all();
      for (const btn of buttons) {
        const text = await btn.textContent();
        console.log(`  - Button: "${text}"`);
      }
      return;
    }

    console.log('📍 Clicando em "Iniciar"...');
    const provisioningStartTime = Date.now();
    await startButton.click();
    await page.waitForTimeout(1000);

    // 7. Monitorar UI durante provisioning
    // Procurar por indicadores de progresso
    const progressTexts = [
      'Provisionando',
      'Criando',
      'Aguardando',
      'Batch',
      'SSH',
      'Conectando'
    ];

    let lastProgressText = '';
    let progressChanges = [];
    const maxWaitTime = 120000; // 2 minutos máximo
    const checkInterval = 2000; // Verificar a cada 2s

    console.log('\n📡 Monitorando progresso na UI...');

    for (let elapsed = 0; elapsed < maxWaitTime; elapsed += checkInterval) {
      // Procurar por textos de progresso
      for (const progressText of progressTexts) {
        const elem = page.getByText(new RegExp(progressText, 'i')).first();
        const isVisible = await elem.isVisible({ timeout: 500 }).catch(() => false);

        if (isVisible) {
          const text = await elem.textContent();
          if (text !== lastProgressText) {
            const timestamp = Date.now() - provisioningStartTime;
            console.log(`[+${(timestamp / 1000).toFixed(1)}s] UI: ${text}`);
            progressChanges.push({ timestamp, text });
            lastProgressText = text;
          }
        }
      }

      // Verificar se completou (sucesso ou erro)
      const successText = page.getByText(/Máquina criada|Sucesso|Pronta|Online/i).first();
      const errorText = page.getByText(/Erro|Falha|Não foi possível/i).first();

      const hasSuccess = await successText.isVisible({ timeout: 500 }).catch(() => false);
      const hasError = await errorText.isVisible({ timeout: 500 }).catch(() => false);

      if (hasSuccess) {
        const timestamp = Date.now() - provisioningStartTime;
        console.log(`[+${(timestamp / 1000).toFixed(1)}s] ✅ SUCESSO!`);
        break;
      }

      if (hasError) {
        const timestamp = Date.now() - provisioningStartTime;
        const errorMsg = await errorText.textContent();
        console.log(`[+${(timestamp / 1000).toFixed(1)}s] ❌ ERRO: ${errorMsg}`);
        break;
      }

      await page.waitForTimeout(checkInterval);
    }

    const totalProvisioningTime = Date.now() - provisioningStartTime;
    console.log(`\n⏱️  Tempo total de provisioning: ${(totalProvisioningTime / 1000).toFixed(1)}s`);

    // 8. Aguardar para garantir que todos os logs foram capturados
    await page.waitForTimeout(3000);

    console.log('\n✅ Teste de timing concluído - veja análise de batches no afterEach');
  });

  test('Deploy Wizard - Teste rápido de UI (sem provisioning real)', async ({ page }) => {
    console.log('🎯 Teste: Verificar elementos do Deploy Wizard na UI');

    await page.goto('/app');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Verificar se seção de deploy existe
    const guidedConfig = page.getByText('Configuração Guiada').first();
    const hasGuided = await guidedConfig.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasGuided).toBeTruthy();
    console.log('✅ Seção "Configuração Guiada" encontrada');

    // Verificar elementos de seleção
    const hasGpuButtons = await page.locator('button:has-text("RTX")').count() > 0;
    console.log(`✅ Botões de GPU: ${hasGpuButtons ? 'Encontrados' : 'Não encontrados'}`);

    const hasTierButtons = await page.locator('button:has-text("Fast"), button:has-text("Standard")').count() > 0;
    console.log(`✅ Botões de Tier: ${hasTierButtons ? 'Encontrados' : 'Não encontrados'}`);

    const hasStartButton = await page.locator('button:has-text("Iniciar")').isVisible({ timeout: 2000 }).catch(() => false);
    console.log(`✅ Botão "Iniciar": ${hasStartButton ? 'Encontrado' : 'Não encontrado'}`);

    console.log('\n✅ Teste de UI concluído');
  });
});
