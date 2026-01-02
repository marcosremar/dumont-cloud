const { chromium } = require('@playwright/test');

(async () => {
  console.log('=== TESTE DO WIZARD - SELEÇÃO DE REGIÃO ===\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Ativar console log
  page.on('console', msg => console.log('  [BROWSER]', msg.text()));

  try {
    // 1. Navegar
    console.log('1. Navegando para http://localhost:4898/demo-app');
    await page.goto('http://localhost:4898/demo-app');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // 2. Verificar que wizard está aberto
    const wizardTitle = page.locator('h3:has-text("Nova Instância GPU")');
    const isVisible = await wizardTitle.isVisible();
    console.log(`2. Wizard visível: ${isVisible}`);

    if (!isVisible) {
      console.log('   ❌ Wizard não está aberto!');
      return;
    }

    // 3. Screenshot inicial
    await page.screenshot({ path: 'step1-initial.png', fullPage: true });
    console.log('   ✓ Screenshot: step1-initial.png');

    // 4. Verificar botões de região
    console.log('\n3. VERIFICANDO BOTÕES DE REGIÃO:');
    const euaButton = page.locator('button:has-text("EUA")').first();
    const europaButton = page.locator('button:has-text("Europa")').first();

    console.log(`   EUA visível: ${await euaButton.isVisible()}`);
    console.log(`   Europa visível: ${await europaButton.isVisible()}`);

    // 5. Clicar em EUA
    console.log('\n4. CLICANDO EM "EUA":');
    await euaButton.click();
    await page.waitForTimeout(500);

    // Screenshot após clique
    await page.screenshot({ path: 'step1-after-eua.png', fullPage: true });
    console.log('   ✓ Screenshot: step1-after-eua.png');

    // 6. Verificar se apareceu indicador de seleção
    console.log('\n5. VERIFICANDO INDICADORES DE SELEÇÃO:');

    // Verificar classes do botão
    const euaClasses = await euaButton.getAttribute('class');
    console.log(`   Classes do botão EUA: ${euaClasses}`);

    const hasSelectedClass = euaClasses?.includes('selected') || euaClasses?.includes('bg-blue') || euaClasses?.includes('ring');
    console.log(`   Tem classe de seleção: ${hasSelectedClass}`);

    // Verificar aria-pressed
    const ariaPressed = await euaButton.getAttribute('aria-pressed');
    console.log(`   aria-pressed: ${ariaPressed}`);

    // Verificar se há badge/checkmark
    const hasBadge = await page.locator('button:has-text("EUA") >> text=✓').isVisible().catch(() => false);
    console.log(`   Badge ✓ visível: ${hasBadge}`);

    // 7. Verificar estado do botão "Próximo"
    console.log('\n6. VERIFICANDO BOTÃO "PRÓXIMO":');
    const nextButton = page.locator('button:has-text("Próximo")').first();
    const isNextVisible = await nextButton.isVisible();
    const isNextDisabled = await nextButton.isDisabled();

    console.log(`   Próximo visível: ${isNextVisible}`);
    console.log(`   Próximo desabilitado: ${isNextDisabled}`);

    if (!isNextDisabled) {
      console.log('\n7. CLICANDO EM "PRÓXIMO":');
      await nextButton.click();
      await page.waitForTimeout(1000);

      // Screenshot step 2
      await page.screenshot({ path: 'step2.png', fullPage: true });
      console.log('   ✓ Screenshot: step2.png');

      // Verificar se avançou para step 2
      const step2Title = page.locator('text=/2\/4|Hardware|GPU/');
      const isStep2 = await step2Title.isVisible();
      console.log(`   Avançou para Step 2: ${isStep2}`);

      if (isStep2) {
        console.log('\n   ✅ SUCESSO! Wizard navegou do Step 1 para Step 2');
      } else {
        console.log('\n   ❌ FALHA! Não avançou para Step 2');
      }
    } else {
      console.log('\n   ⚠️  Botão "Próximo" está desabilitado após clicar em EUA');
      console.log('   Possível bug: seleção não está funcionando corretamente');
    }

    // 8. Inspecionar estado do Redux/React
    console.log('\n8. INSPECIONANDO ESTADO DA APLICAÇÃO:');
    const stateInfo = await page.evaluate(() => {
      // Tentar acessar Redux store
      if (window.__REDUX_DEVTOOLS_EXTENSION__) {
        return { hasRedux: true, note: 'Redux detectado' };
      }
      return { hasRedux: false, note: 'Redux não acessível via window' };
    });
    console.log(`   Redux: ${JSON.stringify(stateInfo)}`);

    // Verificar localStorage
    const localStorage = await page.evaluate(() => {
      return Object.keys(window.localStorage).map(key => ({
        key,
        value: window.localStorage.getItem(key)?.substring(0, 100)
      }));
    });
    console.log('   LocalStorage:');
    localStorage.forEach(item => {
      console.log(`     ${item.key}: ${item.value}`);
    });

  } catch (error) {
    console.error('\n❌ ERRO:', error.message);
    console.error(error.stack);
  } finally {
    console.log('\n=== TESTE CONCLUÍDO ===');
    console.log('Screenshots salvos:');
    console.log('  - step1-initial.png');
    console.log('  - step1-after-eua.png');
    console.log('  - step2.png');

    await page.waitForTimeout(2000);
    await browser.close();
  }
})();
