const puppeteer = require('puppeteer');

// Helper para esperar
const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Teste para verificar bugs reportados:
 * 1. Filtro de região Europa não funciona
 * 2. Múltiplas máquinas sendo criadas
 */
async function testRegionFilterBug() {
  console.log('🧪 TESTE: Verificando bugs de região e múltiplas máquinas\n');

  const browser = await puppeteer.launch({
    headless: false,  // Mostrar browser para debugging
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 900 });

  // Capturar logs do console
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('POST') && text.includes('instances')) {
      console.log('🌐 API CALL:', text);
    }
  });

  // Capturar requests de rede
  const createRequests = [];
  page.on('request', request => {
    if (request.url().includes('/api/v1/instances') && request.method() === 'POST') {
      console.log('📤 CREATE REQUEST:', request.url());
      createRequests.push({
        url: request.url(),
        method: request.method(),
        postData: request.postData(),
      });
    }
  });

  try {
    // 1. Login
    console.log('📍 STEP 1: Fazendo login...');
    await page.goto('http://dumontcloud.orb.local:4890/login');
    await page.waitForSelector('input[type="text"], input[type="email"]', { timeout: 10000 });

    await page.type('input[type="text"], input[type="email"]', 'marcosremar@gmail.com');
    await page.type('input[type="password"]', 'dumont123');

    const loginButton = await page.$('button[type="submit"]');
    await loginButton.click();

    // Aguardar redirect para /app
    await page.waitForNavigation({ timeout: 15000 });
    console.log('✅ Login realizado\n');

    // 2. Ir para GPU Offers
    console.log('📍 STEP 2: Navegando para GPU Offers...');
    await page.goto('http://dumontcloud.orb.local:4890/app/gpu-offers');
    await page.waitForSelector('h1, h2', { timeout: 10000 });
    await wait(3000); // Aguardar carregar ofertas
    console.log('✅ Página de GPU Offers carregada\n');

    // 3. Selecionar filtro Europa
    console.log('📍 STEP 3: Selecionando filtro EUROPA...');

    // Procurar pelo dropdown/select de região
    const regionSelectors = [
      'select[name="region"]',
      'select[id="region"]',
      'select[aria-label*="egião"]',
      'select[aria-label*="Region"]',
      'select',
    ];

    let regionSelect = null;
    for (const selector of regionSelectors) {
      try {
        const element = await page.$(selector);
        if (element) {
          const options = await element.$$('option');
          for (const opt of options) {
            const value = await opt.getProperty('value');
            const text = await opt.getProperty('textContent');
            const valueText = await value.jsonValue();
            const optionText = await text.jsonValue();

            if (valueText.includes('EU') || optionText.includes('Europa') || optionText.includes('Europe')) {
              regionSelect = element;
              console.log(`✅ Encontrou select de região: ${selector}`);
              break;
            }
          }
        }
        if (regionSelect) break;
      } catch (e) {
        // Continuar tentando
      }
    }

    if (regionSelect) {
      await page.select(regionSelect, 'EU'); // ou o valor correto
      console.log('✅ Filtro Europa selecionado');
      await wait(2000); // Aguardar filtrar
    } else {
      console.log('⚠️  Filtro de região não encontrado - pode estar em formato diferente');
    }

    // 4. Verificar se as ofertas são da Europa
    console.log('\n📍 STEP 4: Verificando regiões das ofertas...');

    // Pegar todos os textos da página que podem ser localizações
    const pageText = await page.evaluate(() => document.body.innerText);

    const nonEuropeanLocations = [
      'South Korea', 'KR', 'Korea',
      'China', 'CN', 'Shaanxi',
      'Canada', 'CA', 'Quebec',
      'Wisconsin', 'US',
      'Norway', 'NO', // Noruega tecnicamente é Europa mas não é EU
    ];

    const foundLocations = nonEuropeanLocations.filter(loc => pageText.includes(loc));

    if (foundLocations.length > 0) {
      console.log('❌ BUG CONFIRMADO: Filtro Europa NÃO funciona!');
      console.log('   Localizações não-europeias encontradas:', foundLocations);
    } else {
      console.log('✅ Filtro Europa parece estar funcionando');
    }

    // 5. Aguardar um pouco para não criar máquinas
    console.log('\n📍 STEP 5: Teste completo!');
    console.log('⚠️  NÃO vou clicar para criar máquina para evitar custos');
    console.log('   Se precisar testar criação, descomente o código abaixo\n');

    /*
    // CÓDIGO PARA TESTAR CRIAÇÃO (descomentado apenas se necessário)
    const deployButton = await page.$('button:has-text("Deploy"), button:has-text("Criar")');
    if (deployButton) {
      console.log('📍 Clicando em botão de deploy...');
      await deployButton.click();
      await wait(5000);

      console.log(`📊 Total de requisições CREATE: ${createRequests.length}`);
      if (createRequests.length > 1) {
        console.log('❌ BUG CONFIRMADO: Múltiplas requisições CREATE!');
        createRequests.forEach((req, i) => {
          console.log(`   Request ${i + 1}:`, req.url);
        });
      } else {
        console.log('✅ Apenas 1 requisição CREATE');
      }
    }
    */

    // Manter browser aberto para inspeção
    console.log('\n🔍 Browser permanecerá aberto para inspeção...');
    console.log('   Pressione Ctrl+C para fechar\n');
    await wait(60000); // 1 minuto

  } catch (error) {
    console.error('❌ Erro durante teste:', error.message);
  } finally {
    await browser.close();
  }
}

testRegionFilterBug().catch(console.error);
