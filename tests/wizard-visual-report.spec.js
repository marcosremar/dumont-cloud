const { test, expect } = require('@playwright/test');

test.describe('Wizard - Relatório Visual Completo', () => {
  test('Capturar screenshots de alta qualidade de cada passo', async ({ page }) => {
    // Configurar viewport maior para screenshots melhores
    await page.setViewportSize({ width: 1920, height: 1080 });

    console.log('📸 Iniciando captura visual do wizard...\n');

    // Login
    await page.goto('http://localhost:4894/login?auto_login=demo');
    await page.waitForURL('**/app**', { timeout: 10000 });
    await page.waitForTimeout(2000);

    // Screenshot 1: Dashboard com wizard aberto
    await page.screenshot({ 
      path: 'tests/screenshots/visual-01-wizard-initial.png', 
      fullPage: false 
    });
    console.log('✅ Screenshot 1: Wizard inicial');

    // Screenshot 2: Regiões disponíveis (zoom no mapa)
    await page.screenshot({ 
      path: 'tests/screenshots/visual-02-regions.png', 
      fullPage: false 
    });
    console.log('✅ Screenshot 2: Seleção de regiões');

    // Selecionar EUA
    await page.locator('button:has-text("EUA")').first().click();
    await page.waitForTimeout(1000);

    await page.screenshot({ 
      path: 'tests/screenshots/visual-03-region-selected.png', 
      fullPage: false 
    });
    console.log('✅ Screenshot 3: Região EUA selecionada');

    // Avançar para Hardware
    await page.locator('button:has-text("Próximo")').click();
    await page.waitForTimeout(2000);

    // Screenshot 4: Use cases
    await page.screenshot({ 
      path: 'tests/screenshots/visual-04-use-cases.png', 
      fullPage: false 
    });
    console.log('✅ Screenshot 4: Seleção de propósito');

    // Selecionar "Treinar modelo"
    const trainButton = page.locator('[data-testid="use-case-train"]');
    if (await trainButton.isVisible({ timeout: 2000 })) {
      await trainButton.click();
      await page.waitForTimeout(3000); // Aguardar GPUs carregarem
    }

    // Screenshot 5: Máquinas carregadas
    await page.screenshot({ 
      path: 'tests/screenshots/visual-05-machines-list.png', 
      fullPage: true // Página completa para ver todas as GPUs
    });
    console.log('✅ Screenshot 5: Lista de máquinas');

    // Selecionar primeira máquina
    const firstMachine = page.locator('[data-testid^="machine-"]').first();
    if (await firstMachine.isVisible({ timeout: 2000 })) {
      await firstMachine.click();
      await page.waitForTimeout(1500);
    }

    await page.screenshot({ 
      path: 'tests/screenshots/visual-06-machine-selected.png', 
      fullPage: false 
    });
    console.log('✅ Screenshot 6: Máquina selecionada');

    // Avançar para Estratégia
    await page.locator('button:has-text("Próximo")').click();
    await page.waitForTimeout(2000);

    // Screenshot 7: Estratégias de failover
    await page.screenshot({ 
      path: 'tests/screenshots/visual-07-failover-strategies.png', 
      fullPage: true // Página completa para ver todas as opções
    });
    console.log('✅ Screenshot 7: Estratégias de failover');

    // Screenshot 8: Detalhes de uma estratégia (já selecionada por padrão)
    await page.screenshot({ 
      path: 'tests/screenshots/visual-08-strategy-details.png', 
      fullPage: false 
    });
    console.log('✅ Screenshot 8: Detalhes da estratégia');

    // Tentar clicar em "Iniciar" (pode estar como "Próximo")
    const actionButton = page.locator('button:has-text(/Próximo|Iniciar/)').first();
    const isVisible = await actionButton.isVisible({ timeout: 2000 });
    
    if (isVisible) {
      const btnText = await actionButton.textContent();
      console.log(`\n🔘 Clicando em "${btnText}"...`);
      await actionButton.click();
      await page.waitForTimeout(3000);
    }

    // Screenshot 9: Tela de provisionamento
    await page.screenshot({ 
      path: 'tests/screenshots/visual-09-provisioning.png', 
      fullPage: false 
    });
    console.log('✅ Screenshot 9: Provisionamento iniciado');

    // Aguardar um pouco mais
    await page.waitForTimeout(3000);

    // Screenshot 10: Estado final
    await page.screenshot({ 
      path: 'tests/screenshots/visual-10-final-state.png', 
      fullPage: true 
    });
    console.log('✅ Screenshot 10: Estado final');

    console.log('\n📸 Captura visual concluída! Veja os arquivos em tests/screenshots/visual-*.png\n');
  });
});
