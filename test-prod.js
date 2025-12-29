const { chromium } = require('playwright');

async function testProduction() {
  console.log('🚀 Iniciando teste de produção...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Capturar erros do console
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('❌ ERRO:', msg.text());
    }
  });

  // Capturar requisições com erro
  page.on('response', response => {
    if (response.status() >= 400) {
      console.log(`❌ HTTP ${response.status()}: ${response.url()}`);
    }
  });

  try {
    // 1. Acessar página de login
    console.log('1️⃣ Acessando https://cloud.dumontai.com...');
    await page.goto('https://cloud.dumontai.com', { waitUntil: 'networkidle' });
    await page.screenshot({ path: '/tmp/test-1-home.png' });
    console.log('   ✅ Página carregada');

    // 2. Fazer login
    console.log('\n2️⃣ Fazendo login...');
    await page.fill('input[type="text"], input[type="email"]', 'marcosremar@gmail.com');
    await page.fill('input[type="password"]', 'dumont123');
    await page.screenshot({ path: '/tmp/test-2-login-filled.png' });

    await page.click('button[type="submit"]');
    console.log('   ✅ Credenciais enviadas');

    // Aguardar resposta
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/test-3-after-login.png' });

    const currentUrl = page.url();
    console.log(`   📍 URL atual: ${currentUrl}`);

    if (currentUrl.includes('/app') || currentUrl.includes('/dashboard')) {
      console.log('   ✅ Login bem-sucedido!');
    } else {
      console.log('   ❌ Login falhou - ainda na página de login');
    }

    // 3. Verificar dashboard/máquinas
    console.log('\n3️⃣ Procurando opção de máquinas...');
    await page.waitForTimeout(2000);

    // Procurar link/botão de máquinas
    const machinesLink = await page.$('text=Máquinas') ||
                         await page.$('text=Machines') ||
                         await page.$('text=GPU') ||
                         await page.$('a[href*="machine"]');

    if (machinesLink) {
      await machinesLink.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: '/tmp/test-4-machines.png' });
      console.log('   ✅ Página de máquinas acessada');
    } else {
      console.log('   ⚠️ Link de máquinas não encontrado');
      await page.screenshot({ path: '/tmp/test-4-dashboard.png' });
    }

    // 4. Verificar conteúdo da página
    console.log('\n4️⃣ Verificando conteúdo...');
    const pageContent = await page.content();

    if (pageContent.includes('error') || pageContent.includes('Error') || pageContent.includes('falha')) {
      console.log('   ⚠️ Possíveis erros detectados na página');
    }

    // Capturar screenshot final
    await page.screenshot({ path: '/tmp/test-5-final.png', fullPage: true });
    console.log('\n📸 Screenshots salvos em /tmp/test-*.png');

  } catch (error) {
    console.log('\n❌ ERRO:', error.message);
    await page.screenshot({ path: '/tmp/test-error.png' });
  } finally {
    await browser.close();
  }

  console.log('\n✅ Teste finalizado!');
}

testProduction().catch(console.error);
