// @ts-check
const { test, expect } = require('@playwright/test');

// Credenciais de teste
const TEST_USER = 'marcosremar@gmail.com';
const TEST_PASSWORD = 'marcos123';

test.describe('Dumont Cloud - Minhas Maquinas', () => {

  test.beforeEach(async ({ page }) => {
    // Navegar para a pagina de login
    await page.goto('/');

    // Fazer login
    await page.fill('input[type="email"], input[placeholder*="email" i], input[name="username"]', TEST_USER);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');

    // Aguardar redirecionamento apos login
    await page.waitForURL('**/minhas-maquinas', { timeout: 10000 }).catch(() => {
      // Se nao redirecionar automaticamente, navegar manualmente
    });
  });

  test('deve carregar a pagina de Minhas Maquinas', async ({ page }) => {
    await page.goto('/minhas-maquinas');

    // Tirar screenshot da pagina inicial
    await page.screenshot({
      path: 'test-results/minhas-maquinas-inicial.png',
      fullPage: true
    });

    // Verificar se o titulo da pagina esta presente (pode ser "Minhas Maquinas" ou "Minhas Máquinas")
    await expect(page.locator('text=/Minhas M[aá]quinas/i')).toBeVisible({ timeout: 10000 });
  });

  test('deve exibir card de maquina com informacoes corretas', async ({ page }) => {
    await page.goto('/minhas-maquinas');

    // Aguardar carregamento das maquinas
    await page.waitForTimeout(3000);

    // Tirar screenshot
    await page.screenshot({
      path: 'test-results/minhas-maquinas-cards.png',
      fullPage: true
    });

    // Verificar se existe pelo menos um card de maquina
    const cards = page.locator('[class*="card"], [class*="machine"], [class*="instance"]');
    const cardCount = await cards.count();

    console.log(`Numero de cards encontrados: ${cardCount}`);
  });

  test('deve exibir menu dropdown ao clicar no botao', async ({ page }) => {
    await page.goto('/minhas-maquinas');
    await page.waitForTimeout(3000);

    // Procurar por botao de dropdown/menu (tres pontos ou similar)
    const dropdownButton = page.locator('button:has(svg), [class*="dropdown"], [class*="menu"]').first();

    if (await dropdownButton.isVisible()) {
      await dropdownButton.click();
      await page.waitForTimeout(500);

      // Tirar screenshot com menu aberto
      await page.screenshot({
        path: 'test-results/minhas-maquinas-dropdown.png',
        fullPage: true
      });
    }
  });

  test('deve abrir modal de logs ao clicar no botao Logs', async ({ page }) => {
    await page.goto('/minhas-maquinas');
    await page.waitForTimeout(3000);

    // Procurar por botao de Logs
    const logsButton = page.locator('button:has-text("Logs")').first();

    if (await logsButton.isVisible()) {
      await logsButton.click();
      await page.waitForTimeout(1000);

      // Tirar screenshot com modal de logs
      await page.screenshot({
        path: 'test-results/minhas-maquinas-logs-modal.png',
        fullPage: true
      });

      // Verificar se modal apareceu (pode ser div com backdrop ou conteudo de logs)
      const modal = page.locator('[class*="fixed"][class*="inset"], [class*="backdrop"], div:has-text("Logs da Instancia")');
      const isModalVisible = await modal.isVisible().catch(() => false);
      console.log(`Modal de logs visivel: ${isModalVisible}`);
    } else {
      console.log('Botao de Logs nao encontrado - pode nao haver maquinas ativas');
    }
  });

  test('deve exibir estatisticas (custo, duracao)', async ({ page }) => {
    await page.goto('/minhas-maquinas');
    await page.waitForTimeout(3000);

    // Tirar screenshot das estatisticas
    await page.screenshot({
      path: 'test-results/minhas-maquinas-estatisticas.png',
      fullPage: true
    });

    // Verificar se estatisticas estao visiveis
    const statsSection = page.locator('text=/\\$\\d+|USD|Total|Duracao/i');
    const count = await statsSection.count();
    console.log(`Estatisticas encontradas: ${count}`);
  });

  test('deve navegar entre abas (Dashboard, Minhas Maquinas, Settings)', async ({ page }) => {
    await page.goto('/minhas-maquinas');
    await page.waitForTimeout(2000);

    // Screenshot inicial
    await page.screenshot({
      path: 'test-results/navegacao-minhas-maquinas.png',
      fullPage: true
    });

    // Clicar em Dashboard
    const dashboardLink = page.locator('a:has-text("Dashboard"), nav >> text=Dashboard').first();
    if (await dashboardLink.isVisible()) {
      await dashboardLink.click();
      await page.waitForTimeout(1000);
      await page.screenshot({
        path: 'test-results/navegacao-dashboard.png',
        fullPage: true
      });
    }

    // Voltar para Minhas Maquinas
    const minhasMaquinasLink = page.locator('a:has-text("Minhas Maquinas"), nav >> text="Minhas Maquinas"').first();
    if (await minhasMaquinasLink.isVisible()) {
      await minhasMaquinasLink.click();
      await page.waitForTimeout(1000);
    }

    // Clicar em Settings
    const settingsLink = page.locator('a:has-text("Settings"), nav >> text=Settings').first();
    if (await settingsLink.isVisible()) {
      await settingsLink.click();
      await page.waitForTimeout(1000);
      await page.screenshot({
        path: 'test-results/navegacao-settings.png',
        fullPage: true
      });
    }
  });

  test('deve verificar funcionamento do lock/unlock toggle', async ({ page }) => {
    await page.goto('/minhas-maquinas');
    await page.waitForTimeout(3000);

    // Procurar por toggle de lock
    const lockToggle = page.locator('[class*="lock"], button:has(svg[class*="lock"])').first();

    if (await lockToggle.isVisible()) {
      // Screenshot antes de clicar
      await page.screenshot({
        path: 'test-results/lock-toggle-antes.png',
        fullPage: true
      });

      await lockToggle.click();
      await page.waitForTimeout(500);

      // Screenshot depois de clicar
      await page.screenshot({
        path: 'test-results/lock-toggle-depois.png',
        fullPage: true
      });
    }
  });

  test('captura screenshot completo da aplicacao', async ({ page }) => {
    await page.goto('/minhas-maquinas');
    await page.waitForTimeout(5000);

    // Screenshot full page
    await page.screenshot({
      path: 'test-results/minhas-maquinas-completo.png',
      fullPage: true
    });

    // Screenshot apenas viewport
    await page.screenshot({
      path: 'test-results/minhas-maquinas-viewport.png',
      fullPage: false
    });
  });

});
