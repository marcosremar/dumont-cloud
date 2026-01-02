const { test, expect } = require('@playwright/test');

test('Visual Check - GPUs aparecem ao selecionar tier', async ({ page }) => {
  console.log('=== TESTE VISUAL: VERIFICAR SE GPUs APARECEM NO WIZARD ===\n');

  // PASSO 1: Navegar para login com auto-login
  console.log('PASSO 1: Navegando para http://localhost:4895/login?auto_login=demo');
  await page.goto('http://localhost:4895/login?auto_login=demo');

  // PASSO 2: Aguardar redirecionamento para /app
  console.log('PASSO 2: Aguardando redirecionamento para /app...');
  await page.waitForURL('**/app**', { timeout: 10000 });
  await page.waitForLoadState('networkidle');
  console.log('   Redirecionado com sucesso para:', page.url());

  // Screenshot da dashboard inicial
  await page.screenshot({ path: 'test-results/01-dashboard-inicial.png', fullPage: true });
  console.log('   Screenshot salvo: 01-dashboard-inicial.png\n');

  // PASSO 3: Clicar no botão "Novo Deploy" ou similar
  console.log('PASSO 3: Procurando botão para abrir wizard...');

  // Tentar diferentes variações do botão
  const newDeployButton = page.locator('button:has-text("Experimentar")')
    .or(page.locator('button:has-text("Novo Deploy")'))
    .or(page.locator('button:has-text("Nova Máquina")'))
    .or(page.locator('button:has-text("Buscar Máquinas")'))
    .or(page.locator('button:has-text("Deploy")'))
    .or(page.locator('[data-testid="new-deploy"]'));

  const buttonCount = await newDeployButton.count();
  console.log(`   Encontrados ${buttonCount} botões de deploy`);

  if (buttonCount === 0) {
    // Listar todos os botões visíveis para debug
    const allButtons = await page.locator('button:visible').all();
    console.log('\n   DEBUG: Todos os botões visíveis:');
    for (let i = 0; i < Math.min(allButtons.length, 10); i++) {
      const text = await allButtons[i].textContent();
      console.log(`     - "${text?.trim()}"`);
    }
  } else {
    console.log('   Clicando no botão de deploy...');
    await newDeployButton.first().click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'test-results/02-wizard-aberto.png', fullPage: true });
    console.log('   Screenshot salvo: 02-wizard-aberto.png\n');
  }

  // PASSO 4: Selecionar uma localização (Reino Unido)
  console.log('PASSO 4: Selecionando localização...');

  // Procurar por botões de região
  const regionButtons = {
    'Reino Unido': page.locator('button:has-text("Reino Unido")'),
    'UK': page.locator('button:has-text("UK")'),
    'United Kingdom': page.locator('button:has-text("United Kingdom")'),
    'Europa': page.locator('button:has-text("Europa")'),
    'EUA': page.locator('button:has-text("EUA")').or(page.locator('button:has-text("USA")')),
  };

  let regionSelected = false;
  for (const [name, locator] of Object.entries(regionButtons)) {
    const count = await locator.count();
    console.log(`   - "${name}": ${count} encontrado(s)`);

    if (count > 0 && !regionSelected) {
      console.log(`   Selecionando "${name}"...`);
      await locator.first().click();
      await page.waitForTimeout(500);
      regionSelected = true;
    }
  }

  if (!regionSelected) {
    console.log('   AVISO: Nenhuma região encontrada. Listando elementos h2/h3:');
    const headings = await page.locator('h2, h3').all();
    for (const h of headings) {
      const text = await h.textContent();
      console.log(`     - "${text?.trim()}"`);
    }
  }

  await page.screenshot({ path: 'test-results/03-regiao-selecionada.png', fullPage: true });
  console.log('   Screenshot salvo: 03-regiao-selecionada.png\n');

  // PASSO 5: Avançar para Step 2
  console.log('PASSO 5: Avançando para Step 2...');

  const nextButton = page.locator('button:has-text("Próximo")')
    .or(page.locator('button:has-text("Next")'))
    .or(page.locator('button:has-text("Continuar")'));

  const nextCount = await nextButton.count();
  console.log(`   Botão "Próximo": ${nextCount} encontrado(s)`);

  if (nextCount > 0) {
    await nextButton.first().click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'test-results/04-step2-inicio.png', fullPage: true });
    console.log('   Screenshot salvo: 04-step2-inicio.png\n');
  }

  // PASSO 6: Selecionar um tier de performance
  console.log('PASSO 6: Selecionando tier de performance...');

  // Procurar por tiers
  const tiers = {
    'Experimentar': page.locator('button:has-text("Experimentar")'),
    'Desenvolver': page.locator('button:has-text("Desenvolver")'),
    'Produção': page.locator('button:has-text("Produção")'),
    'Performance': page.locator('button:has-text("Performance")'),
    'Budget': page.locator('button:has-text("Budget")'),
    'Premium': page.locator('button:has-text("Premium")'),
    'Rápido': page.locator('button:has-text("Rápido")'),
    'Equilibrado': page.locator('button:has-text("Equilibrado")'),
  };

  let tierSelected = false;
  for (const [name, locator] of Object.entries(tiers)) {
    const count = await locator.count();
    console.log(`   - Tier "${name}": ${count} encontrado(s)`);

    if (count > 0 && !tierSelected) {
      console.log(`   Selecionando tier "${name}"...`);
      await locator.first().click();
      await page.waitForTimeout(2000); // Aguardar carregamento das GPUs
      tierSelected = true;
    }
  }

  await page.screenshot({ path: 'test-results/05-tier-selecionado.png', fullPage: true });
  console.log('   Screenshot salvo: 05-tier-selecionado.png\n');

  // PASSO 7: VERIFICAÇÃO VISUAL - Verificar se aparecem máquinas/GPUs
  console.log('PASSO 7: VERIFICANDO SE GPUs APARECEM...\n');

  // Aguardar um pouco mais para garantir que a lista carregue
  await page.waitForTimeout(2000);

  // Procurar por indicadores de loading
  const loadingIndicators = page.locator('text=/loading|carregando|aguarde/i');
  const loadingCount = await loadingIndicators.count();
  console.log(`   Indicadores de loading: ${loadingCount}`);

  // Procurar por lista de máquinas/GPUs
  const gpuCards = page.locator('[data-testid*="gpu"]')
    .or(page.locator('[data-testid*="machine"]'))
    .or(page.locator('.gpu-card'))
    .or(page.locator('.machine-card'));

  const gpuCardCount = await gpuCards.count();
  console.log(`   Cards de GPU encontrados: ${gpuCardCount}`);

  // Procurar por nomes de GPUs comuns
  const gpuNames = [
    'RTX 4090', 'RTX 4080', 'RTX 3090', 'RTX 3080',
    'A100', 'H100', 'V100', 'T4',
    'GPU', 'VRAM', 'CUDA'
  ];

  console.log('\n   Procurando por nomes de GPUs no conteúdo:');
  let foundGpuNames = [];
  for (const gpuName of gpuNames) {
    const found = await page.locator(`text="${gpuName}"`).count();
    if (found > 0) {
      console.log(`     ENCONTRADO: "${gpuName}" (${found} ocorrências)`);
      foundGpuNames.push(gpuName);
    }
  }

  // Procurar por mensagens de erro
  const errorMessages = page.locator('text=/erro|error|falha|failed|sem resultados|no results/i');
  const errorCount = await errorMessages.count();
  console.log(`\n   Mensagens de erro: ${errorCount}`);

  if (errorCount > 0) {
    console.log('   AVISO: Possível erro detectado. Mensagens:');
    const errors = await errorMessages.all();
    for (let i = 0; i < Math.min(errors.length, 5); i++) {
      const text = await errors[i].textContent();
      console.log(`     - "${text?.trim()}"`);
    }
  }

  // Procurar por listas vazias
  const emptyMessages = page.locator('text=/vazio|empty|nenhum|none|não encontrado|nenhuma máquina/i');
  const emptyCount = await emptyMessages.count();
  console.log(`   Mensagens de lista vazia: ${emptyCount}`);

  // Screenshot final
  await page.screenshot({ path: 'test-results/06-verificacao-final.png', fullPage: true });
  console.log('\n   Screenshot salvo: 06-verificacao-final.png');

  // Salvar HTML completo para análise detalhada
  const html = await page.content();
  const fs = require('fs');
  fs.writeFileSync('test-results/wizard-page-complete.html', html);
  console.log('   HTML completo salvo: wizard-page-complete.html');

  // RESUMO FINAL
  console.log('\n=== RESUMO DA VERIFICAÇÃO VISUAL ===');
  console.log(`URL atual: ${page.url()}`);
  console.log(`Tier selecionado: ${tierSelected ? 'SIM' : 'NÃO'}`);
  console.log(`Cards de GPU encontrados: ${gpuCardCount}`);
  console.log(`Indicadores de loading: ${loadingCount}`);
  console.log(`Mensagens de erro: ${errorCount}`);
  console.log(`Mensagens de lista vazia: ${emptyCount}`);
  console.log(`GPUs identificadas: ${foundGpuNames.join(', ') || 'Nenhuma'}`);

  let testStatus = '';
  if (foundGpuNames.length > 0 || gpuCardCount > 0) {
    console.log('\n STATUS: TESTE PASSOU - GPUs APARECEM NA LISTA');
    testStatus = 'PASSOU';
  } else if (loadingCount > 0) {
    console.log('\n STATUS: AINDA CARREGANDO (aguardar mais tempo)');
    testStatus = 'LOADING';
  } else if (errorCount > 0) {
    console.log('\n STATUS: TESTE FALHOU - ERRO DETECTADO');
    testStatus = 'FALHOU';
  } else if (emptyCount > 0) {
    console.log('\n STATUS: TESTE FALHOU - LISTA VAZIA (sem GPUs disponíveis)');
    testStatus = 'FALHOU';
  } else {
    console.log('\n STATUS: INDETERMINADO (verificar screenshots)');
    testStatus = 'INDETERMINADO';
  }

  console.log('\n=== TESTE CONCLUÍDO ===');
  console.log('Verifique os screenshots em test-results/');
  console.log('');

  // Asserção final
  expect(foundGpuNames.length).toBeGreaterThan(0);
});
