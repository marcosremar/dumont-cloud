const { chromium } = require('playwright');

async function testProduction() {
  console.log('🚀 Iniciando teste de produção...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Capturar todas as requisições e respostas
  page.on('request', request => {
    if (request.url().includes('/api/')) {
      console.log(`📤 REQUEST: ${request.method()} ${request.url()}`);
      const headers = request.headers();
      if (headers['authorization']) {
        console.log(`   Authorization: ${headers['authorization'].substring(0, 50)}...`);
      }
    }
  });

  // Capturar erros do console
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
      console.log('❌ Console Error:', msg.text());
    }
  });

  // Capturar requisições com erro
  const httpErrors = [];
  page.on('response', response => {
    if (response.status() >= 400) {
      httpErrors.push(`${response.status()}: ${response.url()}`);
      console.log(`❌ HTTP ${response.status()}: ${response.url()}`);
    }
  });

  try {
    // 1. Acessar página de login
    console.log('1️⃣ Acessando https://cloud.dumontai.com...');
    await page.goto('https://cloud.dumontai.com', { waitUntil: 'networkidle', timeout: 30000 });
    await page.screenshot({ path: '/tmp/prod-1-home.png' });
    console.log('   ✅ Página carregada');
    console.log('   📍 URL:', page.url());

    // Aguardar a página carregar completamente
    await page.waitForTimeout(2000);

    // 2. Clicar no botão de Login na landing page
    console.log('\n2️⃣ Clicando no botão Login...');

    let loginButton = await page.$('a:has-text("Login")') ||
                      await page.$('button:has-text("Login")') ||
                      await page.$('a[href*="login"]');

    if (loginButton) {
      await loginButton.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: '/tmp/prod-2-login-page.png' });
      console.log('   ✅ Página de login carregada');
      console.log('   📍 URL:', page.url());
    } else {
      console.log('   ⚠️ Botão de login não encontrado na landing page');
    }

    // 3. Fazer login - procurar campos de forma mais flexível
    console.log('\n3️⃣ Preenchendo credenciais...');

    // Verificar se há um formulário de login
    const pageContent = await page.content();
    console.log('   📝 Procurando campos de login...');

    // Tentar diferentes seletores para o campo de email/username
    let emailField = await page.$('input[name="email"]') ||
                     await page.$('input[type="email"]') ||
                     await page.$('input[name="username"]') ||
                     await page.$('input[type="text"]') ||
                     await page.$('input[placeholder*="email"]') ||
                     await page.$('input[placeholder*="Email"]') ||
                     await page.$('input[placeholder*="usuario"]') ||
                     await page.$('input[placeholder*="usuário"]');

    if (!emailField) {
      console.log('   ❌ Campo de email não encontrado');
      // Listar todos os inputs na página
      const inputs = await page.$$('input');
      console.log(`   📝 Encontrados ${inputs.length} inputs na página`);
      for (let i = 0; i < inputs.length; i++) {
        const type = await inputs[i].getAttribute('type');
        const name = await inputs[i].getAttribute('name');
        const placeholder = await inputs[i].getAttribute('placeholder');
        console.log(`      Input ${i}: type="${type}", name="${name}", placeholder="${placeholder}"`);
      }
      await page.screenshot({ path: '/tmp/prod-2-no-login-field.png' });
    } else {
      console.log('   ✅ Campo de email encontrado');
      await emailField.fill('marcosremar@gmail.com');

      // Procurar campo de senha
      let passwordField = await page.$('input[type="password"]') ||
                          await page.$('input[name="password"]');

      if (passwordField) {
        console.log('   ✅ Campo de senha encontrado');
        await passwordField.fill('dumont123');
        await page.screenshot({ path: '/tmp/prod-2-login-filled.png' });

        // Procurar botão de submit
        let submitButton = await page.$('button[type="submit"]') ||
                           await page.$('button:has-text("Login")') ||
                           await page.$('button:has-text("Entrar")') ||
                           await page.$('button:has-text("Sign In")');

        if (submitButton) {
          console.log('   ✅ Botão de login encontrado');
          await submitButton.click();
          console.log('   ⏳ Aguardando resposta...');

          // Aguardar navegação ou resposta
          await page.waitForTimeout(5000);
          await page.screenshot({ path: '/tmp/prod-3-after-login.png' });

          const currentUrl = page.url();
          console.log(`   📍 URL após login: ${currentUrl}`);

          if (currentUrl.includes('/app') || currentUrl.includes('/dashboard') || currentUrl.includes('/machines')) {
            console.log('   ✅ Login bem-sucedido!');

            // 3. Navegar para máquinas
            console.log('\n3️⃣ Procurando página de máquinas...');

            // Aguardar sidebar carregar
            await page.waitForTimeout(2000);

            // Procurar link de máquinas
            let machinesLink = await page.$('a[href*="machine"]') ||
                               await page.$('a:has-text("Máquinas")') ||
                               await page.$('a:has-text("Machines")') ||
                               await page.$('a:has-text("GPU")') ||
                               await page.$('button:has-text("Máquinas")') ||
                               await page.$('button:has-text("Machines")');

            if (machinesLink) {
              console.log('   ✅ Link de máquinas encontrado');
              await machinesLink.click();
              await page.waitForTimeout(3000);
              await page.screenshot({ path: '/tmp/prod-4-machines.png' });
              console.log('   📍 URL:', page.url());

              // 4. Tentar reservar máquina
              console.log('\n4️⃣ Procurando opção de reservar máquina...');

              // Procurar botão de reservar/rent/create
              let reserveButton = await page.$('button:has-text("Reservar")') ||
                                  await page.$('button:has-text("Rent")') ||
                                  await page.$('button:has-text("Create")') ||
                                  await page.$('button:has-text("Alugar")') ||
                                  await page.$('button:has-text("Nova Máquina")') ||
                                  await page.$('button:has-text("New Machine")');

              // Procurar também por "Criar máquina", "+ Nova Máquina" e link no header
              if (!reserveButton) {
                reserveButton = await page.$('button:has-text("Criar máquina")') ||
                                await page.$('button:has-text("Nova Máquina")') ||
                                await page.$('a:has-text("Nova Máquina")');
              }

              if (reserveButton) {
                console.log('   ✅ Botão de criar/reservar encontrado');
                await reserveButton.click();
                await page.waitForTimeout(3000);
                await page.screenshot({ path: '/tmp/prod-5-reserve-clicked.png' });
                console.log('   📍 URL:', page.url());

                // Verificar se abriu modal ou navegou - procurar por failover options
                const hasFailoverOptions = await page.$('.failover-options, .failover-card');
                const hasOnboardingModal = await page.$('.onboarding-modal, .onboarding-overlay');

                if (hasFailoverOptions) {
                  console.log('   ✅ Wizard com opções de Failover encontrado!');
                  await page.screenshot({ path: '/tmp/prod-6-failover-wizard.png' });
                } else if (hasOnboardingModal) {
                  console.log('   ✅ Modal de Onboarding encontrado');
                  // Navegar pelos passos para encontrar failover
                  for (let i = 0; i < 4; i++) {
                    const nextBtn = await page.$('.next-btn, button:has-text("Próximo"), button:has-text("Começar")');
                    if (nextBtn) {
                      await nextBtn.click();
                      await page.waitForTimeout(500);
                    }
                  }
                  await page.screenshot({ path: '/tmp/prod-6-failover-wizard.png' });
                  const failoverNow = await page.$('.failover-options');
                  if (failoverNow) {
                    console.log('   ✅ Passo de Failover encontrado no wizard!');
                  }
                } else {
                  console.log('   ⚠️ Modal/Wizard não encontrado');
                  await page.screenshot({ path: '/tmp/prod-6-modal.png' });
                }
              } else {
                console.log('   ⚠️ Botão de reservar não encontrado');
                // Listar todos os botões
                const buttons = await page.$$('button');
                console.log(`   📝 Encontrados ${buttons.length} botões na página`);
                for (let i = 0; i < Math.min(buttons.length, 10); i++) {
                  const text = await buttons[i].textContent();
                  console.log(`      Button ${i}: "${text.trim()}"`);
                }
              }
            } else {
              console.log('   ⚠️ Link de máquinas não encontrado');
              // Listar todos os links
              const links = await page.$$('a');
              console.log(`   📝 Encontrados ${links.length} links na página`);
              for (let i = 0; i < Math.min(links.length, 10); i++) {
                const href = await links[i].getAttribute('href');
                const text = await links[i].textContent();
                console.log(`      Link ${i}: href="${href}", text="${text.trim().substring(0, 30)}"`);
              }
            }
          } else {
            console.log('   ❌ Login falhou - ainda na página de login');
          }
        } else {
          console.log('   ❌ Botão de submit não encontrado');
        }
      } else {
        console.log('   ❌ Campo de senha não encontrado');
      }
    }

    // Screenshot final
    await page.screenshot({ path: '/tmp/prod-final.png', fullPage: true });
    console.log('\n📸 Screenshots salvos em /tmp/prod-*.png');

    // Resumo de erros
    console.log('\n📊 RESUMO DE ERROS:');
    console.log(`   Console Errors: ${consoleErrors.length}`);
    consoleErrors.forEach(e => console.log(`     - ${e.substring(0, 100)}`));
    console.log(`   HTTP Errors: ${httpErrors.length}`);
    httpErrors.forEach(e => console.log(`     - ${e}`));

  } catch (error) {
    console.log('\n❌ ERRO:', error.message);
    await page.screenshot({ path: '/tmp/prod-error.png' });
  } finally {
    await browser.close();
  }

  console.log('\n✅ Teste finalizado!');
}

testProduction().catch(console.error);
