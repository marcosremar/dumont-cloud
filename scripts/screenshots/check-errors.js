const { chromium } = require('playwright');

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

async function checkErrors() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  const errors = [];
  const warnings = [];

  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    if (type === 'error') {
      errors.push(text);
    } else if (type === 'warning') {
      warnings.push(text);
    }
  });

  page.on('pageerror', error => {
    errors.push(`Page Error: ${error.message}`);
  });

  try {
    await page.goto(`${BASE_URL}/demo-app`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);

    console.log('\n=== ERROS ===');
    if (errors.length > 0) {
      errors.forEach(err => console.log(`❌ ${err}`));
    } else {
      console.log('✅ Nenhum erro encontrado');
    }

    console.log('\n=== AVISOS ===');
    if (warnings.length > 0) {
      warnings.slice(0, 5).forEach(warn => console.log(`⚠️  ${warn}`));
    } else {
      console.log('✅ Nenhum aviso');
    }

  } catch (err) {
    console.error(`❌ Erro ao carregar página: ${err.message}`);
  } finally {
    await browser.close();
  }
}

checkErrors();
