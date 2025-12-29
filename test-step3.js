const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://cloud.dumontai.com/login');
  await page.waitForTimeout(1000);
  await page.fill('input[type="email"], input[name="email"], input[type="text"]', 'marcosremar@gmail.com');
  await page.fill('input[type="password"]', 'dumont123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  await page.goto('https://cloud.dumontai.com/app/machines');
  await page.waitForTimeout(2000);

  const btn = await page.$('button:has-text("Nova Máquina"), a:has-text("Nova Máquina")');
  if (btn) await btn.click();
  await page.waitForTimeout(2000);

  // Passo 1
  await page.screenshot({ path: '/tmp/step1.png' });
  console.log('Passo 1 capturado');

  // Avançar para passo 2
  let nextBtn = await page.$('button:has-text("Começar")');
  if (nextBtn) await nextBtn.click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/step2.png' });
  console.log('Passo 2 capturado');

  // Avançar para passo 3 (FAILOVER)
  nextBtn = await page.$('button:has-text("Próximo")');
  if (nextBtn) await nextBtn.click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/step3-failover.png' });
  console.log('Passo 3 (Failover) capturado');

  // Verificar conteúdo
  const html = await page.content();
  console.log('Tem Snapshot Only:', html.includes('Snapshot Only'));
  console.log('Tem Sem Failover:', html.includes('Sem Failover'));
  console.log('Tem Proteção Failover:', html.includes('Proteção'));

  await browser.close();
})();
