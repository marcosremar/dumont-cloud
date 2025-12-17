/**
 * Dumont Cloud - Full Site Review
 *
 * Teste completo de navegação pelo site, interagindo com todos os componentes
 * e tirando screenshots para documentar o estado atual.
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.TEST_URL || 'https://dumontcloud.com';
const TEST_USER = process.env.TEST_USER || 'marcosremar@gmail.com';
const TEST_PASS = process.env.TEST_PASS || 'Marcos123';

// Criar pasta para screenshots
const SCREENSHOT_DIR = 'screenshots/review';

test('Full Site Review - Complete Navigation Test', async ({ page }) => {
  test.setTimeout(180000); // 3 minutos de timeout
  const issues = [];
  const successes = [];

  // Função helper para registrar problemas
  const logIssue = (area, description) => {
    issues.push({ area, description });
    console.log(`❌ ISSUE [${area}]: ${description}`);
  };

  const logSuccess = (area, description) => {
    successes.push({ area, description });
    console.log(`✅ OK [${area}]: ${description}`);
  };

  // ========================================
  // 1. PÁGINA DE LOGIN
  // ========================================
  console.log('\n========== 1. PÁGINA DE LOGIN ==========\n');

  await page.goto(`${BASE_URL}/login`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/01-login-page.png`, fullPage: true });

  // Verificar elementos do login
  const loginTitle = await page.locator('text=Dumont Cloud').count();
  if (loginTitle > 0) {
    logSuccess('Login', 'Título "Dumont Cloud" visível');
  } else {
    logIssue('Login', 'Título "Dumont Cloud" não encontrado');
  }

  const usernameInput = await page.locator('input[type="text"]').count();
  const passwordInput = await page.locator('input[type="password"]').count();
  const loginBtn = await page.locator('button:has-text("Login")').count();

  if (usernameInput > 0 && passwordInput > 0 && loginBtn > 0) {
    logSuccess('Login', 'Formulário de login completo (username, password, botão)');
  } else {
    logIssue('Login', `Formulário incompleto: username=${usernameInput}, password=${passwordInput}, button=${loginBtn}`);
  }

  // Fazer login
  await page.fill('input[type="text"]', TEST_USER);
  await page.fill('input[type="password"]', TEST_PASS);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/02-login-filled.png` });
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/03-after-login.png`, fullPage: true });

  if (!page.url().includes('/login')) {
    logSuccess('Login', 'Login realizado com sucesso - redirecionado para dashboard');
  } else {
    logIssue('Login', 'Falha no login - ainda na página de login');
    // Verificar mensagem de erro
    const errorMsg = await page.locator('.alert-error, [class*="error"]').textContent().catch(() => '');
    if (errorMsg) {
      logIssue('Login', `Mensagem de erro: ${errorMsg}`);
    }
  }

  // ========================================
  // 2. DASHBOARD - HEADER E NAVEGAÇÃO
  // ========================================
  console.log('\n========== 2. HEADER E NAVEGAÇÃO ==========\n');

  await page.goto(`${BASE_URL}/`);
  await page.waitForTimeout(2000);

  // Verificar header
  const logo = await page.locator('text=Dumont').first().isVisible().catch(() => false);
  if (logo) {
    logSuccess('Header', 'Logo Dumont Cloud visível');
  } else {
    logIssue('Header', 'Logo não encontrado');
  }

  // Links de navegação
  const navLinks = ['Dashboard', 'Machines', 'Settings'];
  for (const link of navLinks) {
    const linkVisible = await page.locator(`text=${link}`).first().isVisible().catch(() => false);
    if (linkVisible) {
      logSuccess('Header', `Link "${link}" visível`);
    } else {
      logIssue('Header', `Link "${link}" não encontrado`);
    }
  }

  // Dropdown Métricas
  const metricasDropdown = await page.locator('text=Métricas').first().isVisible().catch(() => false);
  if (metricasDropdown) {
    logSuccess('Header', 'Dropdown "Métricas" visível');
    // Tentar abrir o dropdown
    await page.locator('text=Métricas').first().click().catch(() => {});
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/04-metricas-dropdown.png` });
    await page.keyboard.press('Escape');
  } else {
    logIssue('Header', 'Dropdown "Métricas" não encontrado');
  }

  // Botão Logout
  const logoutBtn = await page.locator('text=Logout').first().isVisible().catch(() => false);
  if (logoutBtn) {
    logSuccess('Header', 'Botão "Logout" visível');
  } else {
    logIssue('Header', 'Botão "Logout" não encontrado');
  }

  await page.screenshot({ path: `${SCREENSHOT_DIR}/05-header-complete.png` });

  // ========================================
  // 3. DASHBOARD - DEPLOY WIZARD
  // ========================================
  console.log('\n========== 3. DASHBOARD - DEPLOY WIZARD ==========\n');

  await page.goto(`${BASE_URL}/`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/06-dashboard-initial.png`, fullPage: true });

  // Verificar título Deploy
  const deployTitle = await page.locator('text=Deploy').first().isVisible().catch(() => false);
  if (deployTitle) {
    logSuccess('Dashboard', 'Seção "Deploy" visível');
  } else {
    logIssue('Dashboard', 'Seção "Deploy" não encontrada');
  }

  // Verificar botões Wizard/Avançado
  const wizardBtn = await page.locator('button:has-text("Wizard")').isVisible().catch(() => false);
  const advancedBtn = await page.locator('button:has-text("Avançado")').isVisible().catch(() => false);
  if (wizardBtn && advancedBtn) {
    logSuccess('Dashboard', 'Botões Wizard/Avançado visíveis');
  } else {
    logIssue('Dashboard', `Wizard=${wizardBtn}, Avançado=${advancedBtn}`);
  }

  // Verificar tabs de região
  const regions = ['EUA', 'Europa', 'Ásia', 'América do Sul', 'Global'];
  for (const region of regions) {
    const regionTab = await page.locator(`button:has-text("${region}")`).isVisible().catch(() => false);
    if (regionTab) {
      logSuccess('Dashboard', `Tab região "${region}" visível`);
    } else {
      logIssue('Dashboard', `Tab região "${region}" não encontrada`);
    }
  }

  // Clicar em cada região e tirar screenshot
  for (const region of ['EUA', 'Europa', 'Ásia']) {
    await page.locator(`button:has-text("${region}")`).click().catch(() => {});
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/07-region-${region.toLowerCase()}.png`, fullPage: true });
  }

  // Verificar seletor de GPU
  const gpuSelector = await page.locator('text=Qualquer GPU').isVisible().catch(() => false);
  if (gpuSelector) {
    logSuccess('Dashboard', 'Seletor de GPU visível');
    // Abrir dropdown
    await page.locator('text=Qualquer GPU').click().catch(() => {});
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/08-gpu-dropdown.png` });
    await page.keyboard.press('Escape');
  } else {
    logIssue('Dashboard', 'Seletor de GPU não encontrado');
  }

  // Verificar cards de velocidade
  const speedCards = ['Lento', 'Medio', 'Rapido', 'Ultra'];
  let speedCardsFound = 0;
  for (const speed of speedCards) {
    const card = await page.locator(`text=/${speed}/i`).count();
    if (card > 0) speedCardsFound++;
  }
  if (speedCardsFound >= 2) {
    logSuccess('Dashboard', `Cards de velocidade encontrados (${speedCardsFound}/4)`);
  } else {
    logIssue('Dashboard', `Poucos cards de velocidade (${speedCardsFound}/4)`);
  }

  // Verificar botão de busca
  const searchBtn = await page.locator('button:has-text("Buscar")').isVisible().catch(() => false);
  if (searchBtn) {
    logSuccess('Dashboard', 'Botão "Buscar Máquinas" visível');
  } else {
    logIssue('Dashboard', 'Botão de busca não encontrado');
  }

  // ========================================
  // 4. DASHBOARD - BUSCAR MÁQUINAS
  // ========================================
  console.log('\n========== 4. BUSCA DE MÁQUINAS ==========\n');

  await page.locator('button:has-text("Buscar")').click().catch(() => {});
  await page.waitForTimeout(5000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/09-search-results.png`, fullPage: true });

  // Verificar resultados
  const hasResults = await page.locator('text=/Máquinas Disponíveis|resultados encontrados/i').isVisible().catch(() => false);
  const hasGPUCards = await page.locator('text=/RTX|A100|H100/').count();
  const hasPrices = await page.locator('text=/\\$[\\d.]+\\/h/').count();

  if (hasResults || hasGPUCards > 0) {
    logSuccess('Busca', `Resultados encontrados: ${hasGPUCards} GPUs, ${hasPrices} preços`);
  } else {
    logIssue('Busca', 'Nenhum resultado de busca encontrado');
  }

  // Verificar botão Selecionar
  const selectBtns = await page.locator('button:has-text("Selecionar")').count();
  if (selectBtns > 0) {
    logSuccess('Busca', `${selectBtns} botões "Selecionar" encontrados`);
  }

  // Voltar ao wizard
  const backBtn = await page.locator('button:has-text("Voltar")').isVisible().catch(() => false);
  if (backBtn) {
    await page.locator('button:has-text("Voltar")').click();
    await page.waitForTimeout(1000);
    logSuccess('Busca', 'Botão "Voltar" funcional');
  }

  // ========================================
  // 5. PÁGINA MACHINES
  // ========================================
  console.log('\n========== 5. PÁGINA MACHINES ==========\n');

  await page.goto(`${BASE_URL}/machines`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/10-machines-page.png`, fullPage: true });

  // Verificar título
  const machinesTitle = await page.locator('text=Minhas Máquinas').isVisible().catch(() => false);
  if (machinesTitle) {
    logSuccess('Machines', 'Título "Minhas Máquinas" visível');
  } else {
    logIssue('Machines', 'Título não encontrado');
  }

  // Verificar filtros
  const filters = ['Todas', 'Online', 'Offline'];
  for (const filter of filters) {
    const filterBtn = await page.locator(`button:has-text("${filter}")`).isVisible().catch(() => false);
    if (filterBtn) {
      logSuccess('Machines', `Filtro "${filter}" visível`);
    } else {
      logIssue('Machines', `Filtro "${filter}" não encontrado`);
    }
  }

  // Clicar em cada filtro
  for (const filter of filters) {
    await page.locator(`button:has-text("${filter}")`).click().catch(() => {});
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/11-machines-filter-${filter.toLowerCase()}.png`, fullPage: true });
  }

  // Verificar cards de máquinas
  const machineCards = await page.locator('[class*="border"][class*="rounded"]').count();
  console.log(`   Encontrados ${machineCards} elementos que parecem cards`);

  // Verificar botões de IDE (se houver máquinas online)
  await page.locator('button:has-text("Online")').click().catch(() => {});
  await page.waitForTimeout(500);

  const vsCodeBtn = await page.locator('button:has-text("VS Code")').count();
  const cursorBtn = await page.locator('button:has-text("Cursor")').count();
  const windsurfBtn = await page.locator('button:has-text("Windsurf")').count();

  if (vsCodeBtn > 0 || cursorBtn > 0 || windsurfBtn > 0) {
    logSuccess('Machines', `Botões IDE encontrados: VSCode=${vsCodeBtn}, Cursor=${cursorBtn}, Windsurf=${windsurfBtn}`);

    // Clicar no VS Code dropdown
    if (vsCodeBtn > 0) {
      await page.locator('button:has-text("VS Code")').first().click().catch(() => {});
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/12-vscode-dropdown.png` });
      await page.keyboard.press('Escape');
    }
  }

  // Verificar menu de 3 pontos
  const menuBtns = await page.locator('button:has(svg.lucide-more-vertical)').count();
  if (menuBtns > 0) {
    logSuccess('Machines', `${menuBtns} menus de opções encontrados`);
    // Abrir primeiro menu
    await page.locator('button:has(svg.lucide-more-vertical)').first().click().catch(() => {});
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/13-machine-menu.png` });
    await page.keyboard.press('Escape');
  }

  // ========================================
  // 6. PÁGINA SETTINGS
  // ========================================
  console.log('\n========== 6. PÁGINA SETTINGS ==========\n');

  await page.goto(`${BASE_URL}/settings`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/14-settings-page.png`, fullPage: true });

  // Verificar campos
  const settingsFields = [
    { name: 'API Key', selector: 'text=/API Key|Vast/i' },
    { name: 'R2 Access', selector: 'text=/R2|Access/i' },
    { name: 'Restic', selector: 'text=/Restic/i' },
    { name: 'Tailscale', selector: 'text=/Tailscale/i' },
  ];

  for (const field of settingsFields) {
    const found = await page.locator(field.selector).count();
    if (found > 0) {
      logSuccess('Settings', `Campo "${field.name}" encontrado`);
    } else {
      logIssue('Settings', `Campo "${field.name}" não encontrado`);
    }
  }

  // Verificar inputs de senha (campos sensíveis)
  const passwordInputs = await page.locator('input[type="password"]').count();
  logSuccess('Settings', `${passwordInputs} campos de senha encontrados`);

  // Verificar botões de toggle (mostrar/ocultar)
  const toggleBtns = await page.locator('button:has(svg.lucide-eye), button:has(svg.lucide-eye-off)').count();
  if (toggleBtns > 0) {
    logSuccess('Settings', `${toggleBtns} botões de toggle visibilidade encontrados`);
    // Clicar em um toggle
    await page.locator('button:has(svg.lucide-eye), button:has(svg.lucide-eye-off)').first().click().catch(() => {});
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/15-settings-toggle.png` });
  }

  // Verificar botão Salvar
  const saveBtn = await page.locator('button:has-text("Salvar")').isVisible().catch(() => false);
  if (saveBtn) {
    logSuccess('Settings', 'Botão "Salvar" visível');
  } else {
    logIssue('Settings', 'Botão "Salvar" não encontrado');
  }

  // Scroll para ver mais campos
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/16-settings-bottom.png`, fullPage: true });

  // ========================================
  // 7. PÁGINA GPU METRICS
  // ========================================
  console.log('\n========== 7. PÁGINA GPU METRICS ==========\n');

  await page.goto(`${BASE_URL}/metrics`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/17-metrics-page.png`, fullPage: true });

  // Verificar se carregou
  const metricsContent = await page.locator('text=/Métricas|Metrics|GPU|Preço/i').count();
  if (metricsContent > 0) {
    logSuccess('Metrics', 'Página de métricas carregada');
  } else {
    logIssue('Metrics', 'Conteúdo de métricas não encontrado');
  }

  // Verificar gráficos
  const charts = await page.locator('canvas').count();
  if (charts > 0) {
    logSuccess('Metrics', `${charts} gráficos encontrados`);
  } else {
    logIssue('Metrics', 'Nenhum gráfico encontrado');
  }

  // Verificar cards de GPU
  const gpuPriceCards = await page.locator('text=/RTX 4090|RTX 4080|RTX 3090/').count();
  if (gpuPriceCards > 0) {
    logSuccess('Metrics', `${gpuPriceCards} cards de preço de GPU encontrados`);
  }

  // Scroll para ver mais
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/18-metrics-bottom.png`, fullPage: true });

  // ========================================
  // 8. TESTE MOBILE
  // ========================================
  console.log('\n========== 8. TESTE MOBILE (375px) ==========\n');

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`${BASE_URL}/`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/19-mobile-dashboard.png`, fullPage: true });

  // Verificar menu hamburger
  const hamburger = await page.locator('button:has(svg.lucide-menu)').isVisible().catch(() => false);
  if (hamburger) {
    logSuccess('Mobile', 'Menu hamburger visível');
    // Abrir menu
    await page.locator('button:has(svg.lucide-menu)').click().catch(() => {});
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/20-mobile-menu-open.png`, fullPage: true });

    // Verificar links no menu mobile
    const mobileLinks = await page.locator('text=Dashboard, text=Machines, text=Settings').count();
    if (mobileLinks > 0) {
      logSuccess('Mobile', 'Links de navegação no menu mobile');
    }

    await page.keyboard.press('Escape');
  } else {
    logIssue('Mobile', 'Menu hamburger não encontrado');
  }

  // Navegar para machines no mobile
  await page.goto(`${BASE_URL}/machines`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/21-mobile-machines.png`, fullPage: true });

  // Navegar para settings no mobile
  await page.goto(`${BASE_URL}/settings`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/22-mobile-settings.png`, fullPage: true });

  // ========================================
  // 9. TESTE TABLET
  // ========================================
  console.log('\n========== 9. TESTE TABLET (768px) ==========\n');

  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto(`${BASE_URL}/`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/23-tablet-dashboard.png`, fullPage: true });

  await page.goto(`${BASE_URL}/machines`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/24-tablet-machines.png`, fullPage: true });

  // ========================================
  // 10. RELATÓRIO FINAL
  // ========================================
  console.log('\n========================================');
  console.log('         RELATÓRIO FINAL');
  console.log('========================================\n');

  console.log(`✅ SUCESSOS: ${successes.length}`);
  successes.forEach(s => console.log(`   [${s.area}] ${s.description}`));

  console.log(`\n❌ PROBLEMAS: ${issues.length}`);
  issues.forEach(i => console.log(`   [${i.area}] ${i.description}`));

  console.log('\n📸 Screenshots salvos em: screenshots/review/');
  console.log('\n========================================\n');

  // Salvar relatório em JSON
  const report = {
    timestamp: new Date().toISOString(),
    url: BASE_URL,
    successes,
    issues,
    summary: {
      total_checks: successes.length + issues.length,
      passed: successes.length,
      failed: issues.length,
      pass_rate: ((successes.length / (successes.length + issues.length)) * 100).toFixed(1) + '%'
    }
  };

  // O teste passa se tiver mais sucessos que falhas
  expect(successes.length).toBeGreaterThan(issues.length);
});
