/**
 * Teste de INSPEÇÃO do DOM - Wizard GPU
 *
 * Este teste navega até o passo de seleção de GPU e captura:
 * - HTML completo do wizard
 * - Lista de todos os elementos clicáveis
 * - Estrutura dos cards de GPU
 * - Textos visíveis
 */

const { test } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const OUTPUT_DIR = '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/gpu-selection';

test('Inspecionar estrutura HTML do wizard de GPU', async ({ page }) => {
  console.log('\n🔍 Iniciando inspeção do wizard de GPU...\n');

  // =======================
  // 1. Navegar para DEMO
  // =======================
  console.log('📍 Navegando para modo DEMO...');
  await page.goto('http://localhost:4894/demo-app');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // =======================
  // 2. Selecionar REGIÃO
  // =======================
  console.log('📍 Selecionando região EUA...');
  await page.locator('button:has-text("EUA")').first().click();
  await page.waitForTimeout(1000);

  // =======================
  // 3. Clicar PRÓXIMO
  // =======================
  console.log('📍 Clicando em Próximo (1ª vez)...');
  await page.locator('button:has-text("Próximo")').first().click();
  await page.waitForTimeout(2000);

  // =======================
  // 4. Selecionar PROPÓSITO
  // =======================
  console.log('📍 Selecionando propósito...');
  await page.locator('button:has-text("Desenvolver")').first().click();
  await page.waitForTimeout(1000);

  // =======================
  // 5. Clicar PRÓXIMO (ir para GPUs)
  // =======================
  console.log('📍 Clicando em Próximo (2ª vez - ir para GPUs)...');
  const nextBtn = page.locator('button:has-text("Próximo")').first();
  const isEnabled = await nextBtn.isEnabled();

  console.log(`   Botão Próximo habilitado: ${isEnabled}`);

  if (isEnabled) {
    await nextBtn.click();
    await page.waitForTimeout(3000);
    console.log('✅ Avançou para passo de GPU');
  } else {
    console.log('⚠️ Botão Próximo desabilitado - propósito pode não ter sido selecionado');
  }

  // =======================
  // 6. Aguardar GPUs carregarem
  // =======================
  console.log('📍 Aguardando GPUs carregarem...');
  await page.waitForTimeout(5000);

  // =======================
  // 7. CAPTURAR INFORMAÇÕES DO DOM
  // =======================
  console.log('\n🔍 Iniciando captura de informações...\n');

  const report = {
    timestamp: new Date().toISOString(),
    url: page.url(),
    sections: {}
  };

  // 7.1 - Capturar HTML completo do wizard
  console.log('📝 Capturando HTML completo do wizard...');
  const wizardHTML = await page.locator('[class*="wizard"], [class*="modal"]').first().innerHTML().catch(() => 'N/A');
  fs.writeFileSync(
    path.join(OUTPUT_DIR, 'wizard-complete-html.html'),
    wizardHTML
  );
  report.sections.wizardHtml = wizardHTML.length > 0 ? `${wizardHTML.length} caracteres` : 'Não encontrado';

  // 7.2 - Listar TODOS os botões visíveis
  console.log('📝 Listando todos os botões visíveis...');
  const buttons = await page.locator('button:visible').evaluateAll(elements =>
    elements.map((el, i) => ({
      index: i,
      text: el.textContent?.trim(),
      className: el.className,
      disabled: el.disabled,
      type: el.type,
      dataAttributes: Array.from(el.attributes)
        .filter(attr => attr.name.startsWith('data-'))
        .map(attr => `${attr.name}="${attr.value}"`)
        .join(' ')
    }))
  );
  report.sections.buttons = buttons;
  console.log(`   Encontrados ${buttons.length} botões`);

  // 7.3 - Listar todos os elementos com classe "card"
  console.log('📝 Listando elementos tipo card...');
  const cards = await page.locator('[class*="card"]:visible, [class*="Card"]:visible').evaluateAll(elements =>
    elements.map((el, i) => ({
      index: i,
      text: el.textContent?.trim().substring(0, 200),
      className: el.className,
      tagName: el.tagName,
      hasButton: el.querySelector('button') !== null,
      dataAttributes: Array.from(el.attributes)
        .filter(attr => attr.name.startsWith('data-'))
        .map(attr => `${attr.name}="${attr.value}"`)
        .join(' ')
    }))
  );
  report.sections.cards = cards;
  console.log(`   Encontrados ${cards.length} cards`);

  // 7.4 - Procurar por nomes de GPU
  console.log('📝 Procurando por nomes de GPU...');
  const bodyText = await page.locator('body').textContent();
  const gpuNames = [
    'RTX 4090', 'RTX 3090', 'RTX 3080', 'RTX 4080',
    'A100', 'H100', 'V100', 'A40', 'A6000',
    'Tesla', 'GeForce', 'Quadro'
  ];

  const foundGpus = gpuNames.filter(name => bodyText.includes(name));
  report.sections.gpuNamesFound = foundGpus;
  console.log(`   GPUs encontradas no texto: ${foundGpus.length > 0 ? foundGpus.join(', ') : 'Nenhuma'}`);

  // 7.5 - Procurar por preços
  console.log('📝 Procurando por preços...');
  const pricePattern = /\$\d+\.?\d*\s*\/?\s*(hora|h|hr)/gi;
  const prices = bodyText.match(pricePattern) || [];
  report.sections.prices = prices;
  console.log(`   Preços encontrados: ${prices.length} (${prices.slice(0, 5).join(', ')})`);

  // 7.6 - Listar todos os headings
  console.log('📝 Listando headings...');
  const headings = await page.locator('h1, h2, h3, h4').evaluateAll(elements =>
    elements.map(el => ({
      level: el.tagName,
      text: el.textContent?.trim(),
      visible: el.offsetParent !== null
    }))
  );
  report.sections.headings = headings.filter(h => h.visible);
  console.log(`   Headings visíveis: ${headings.filter(h => h.visible).length}`);

  // 7.7 - Verificar indicador de passo atual
  console.log('📝 Verificando indicador de passo...');
  const stepIndicators = await page.locator('[class*="step"], [class*="Step"]').evaluateAll(elements =>
    elements.map(el => ({
      text: el.textContent?.trim(),
      className: el.className,
      isActive: el.className.includes('active') || el.className.includes('current')
    }))
  );
  report.sections.stepIndicators = stepIndicators;
  console.log(`   Indicadores de passo: ${stepIndicators.length}`);

  // 7.8 - Capturar elementos com data-attributes relacionados a GPU
  console.log('📝 Procurando elementos com data-attributes de GPU...');
  const gpuElements = await page.locator('[data-gpu], [data-offer], [data-machine]').evaluateAll(elements =>
    elements.map((el, i) => ({
      index: i,
      tagName: el.tagName,
      text: el.textContent?.trim().substring(0, 100),
      attributes: Array.from(el.attributes).map(attr => `${attr.name}="${attr.value}"`).join(' ')
    }))
  );
  report.sections.gpuElements = gpuElements;
  console.log(`   Elementos com data-gpu/offer/machine: ${gpuElements.length}`);

  // 7.9 - Verificar se há tabela ou grid
  console.log('📝 Procurando por tabelas ou grids...');
  const tables = await page.locator('table, [role="table"], [class*="grid"], [class*="Grid"]').count();
  report.sections.tablesOrGrids = tables;
  console.log(`   Tabelas/grids encontrados: ${tables}`);

  // 7.10 - Capturar texto de TODOS os elementos visíveis (primeiros 50 chars de cada)
  console.log('📝 Capturando textos visíveis...');
  const allTexts = await page.locator('*:visible').evaluateAll(elements =>
    elements
      .map(el => el.textContent?.trim())
      .filter(text => text && text.length > 5 && text.length < 200)
      .slice(0, 50) // Primeiros 50 textos únicos
  );
  const uniqueTexts = [...new Set(allTexts)];
  report.sections.visibleTexts = uniqueTexts;
  console.log(`   Textos únicos capturados: ${uniqueTexts.length}`);

  // =======================
  // 8. SALVAR RELATÓRIO
  // =======================
  const reportPath = path.join(OUTPUT_DIR, 'dom-inspection-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`\n✅ Relatório salvo em: ${reportPath}`);

  // =======================
  // 9. CRIAR RESUMO LEGÍVEL
  // =======================
  const summary = `
# Relatório de Inspeção do DOM - Wizard GPU

**Data:** ${report.timestamp}
**URL:** ${report.url}

## Resumo

### Botões Encontrados (${buttons.length})
${buttons.slice(0, 10).map(b => `- [${b.index}] "${b.text}" (disabled: ${b.disabled})`).join('\n')}
${buttons.length > 10 ? `\n... e mais ${buttons.length - 10} botões` : ''}

### Cards Encontrados (${cards.length})
${cards.slice(0, 5).map(c => `- [${c.index}] ${c.text}`).join('\n')}
${cards.length > 5 ? `\n... e mais ${cards.length - 5} cards` : ''}

### GPUs Detectadas
${foundGpus.length > 0 ? foundGpus.map(g => `- ${g}`).join('\n') : '❌ Nenhuma GPU detectada no texto'}

### Preços Encontrados (${prices.length})
${prices.slice(0, 10).join('\n')}

### Headings Visíveis
${headings.filter(h => h.visible).map(h => `- ${h.level}: ${h.text}`).join('\n')}

### Indicadores de Passo
${stepIndicators.map(s => `- ${s.text} (active: ${s.isActive})`).join('\n')}

### Elementos com Data Attributes de GPU
${gpuElements.length > 0 ? gpuElements.map(e => `- ${e.tagName}: ${e.text}`).join('\n') : '❌ Nenhum elemento com data-gpu/offer/machine'}

### Textos Visíveis (amostra)
${uniqueTexts.slice(0, 20).map(t => `- ${t}`).join('\n')}

---

**Arquivos Gerados:**
- dom-inspection-report.json (dados completos)
- wizard-complete-html.html (HTML do wizard)
- dom-inspection-summary.md (este arquivo)
`;

  fs.writeFileSync(
    path.join(OUTPUT_DIR, 'dom-inspection-summary.md'),
    summary
  );

  console.log('\n✅ Resumo legível salvo em: dom-inspection-summary.md');

  // Screenshot final
  await page.screenshot({
    path: path.join(OUTPUT_DIR, 'dom-inspection-final.png'),
    fullPage: true
  });

  console.log('\n🎉 Inspeção completa!\n');
});
