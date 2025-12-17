const { test, expect } = require('@playwright/test');

test('test dashboard search functionality', async ({ page }) => {
  // Acessa o frontend dev
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(2000);

  // Screenshot da página de login
  await page.screenshot({ path: 'screenshots/01-login.png', fullPage: true });
  console.log('Screenshot 1: Página de Login');

  // Faz login com usuário de teste
  await page.fill('input[type="text"], input[placeholder*="user"], input[name="username"]', 'test@test.com');
  await page.fill('input[type="password"]', 'test123');

  await page.screenshot({ path: 'screenshots/02-login-filled.png', fullPage: true });
  console.log('Screenshot 2: Login preenchido');

  // Clica no botão de login
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(3000);

  // Screenshot após login
  await page.screenshot({ path: 'screenshots/03-after-login.png', fullPage: true });
  console.log('Screenshot 3: Após login');

  // Verifica se chegou no Dashboard
  const deployText = page.locator('text=Deploy');
  if (await deployText.first().isVisible({ timeout: 5000 }).catch(() => false)) {
    console.log('Dashboard carregado com sucesso!');

    // Clica em "Avançado" para mudar de modo
    const advancedBtn = page.locator('button:has-text("Avançado")');
    if (await advancedBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await advancedBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: 'screenshots/04-advanced-mode.png', fullPage: true });
      console.log('Screenshot 4: Modo Avançado');
    }

    // Clica no botão de busca
    const searchBtn = page.locator('button:has-text("Buscar")');
    if (await searchBtn.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchBtn.first().click();
      console.log('Botão de busca clicado');

      // Aguarda resultado
      await page.waitForTimeout(5000);

      // Screenshot dos resultados
      await page.screenshot({ path: 'screenshots/05-search-results.png', fullPage: true });
      console.log('Screenshot 5: Resultados da busca');

      // Verifica se há resultados
      const resultsText = page.locator('text=/\\d+ resultados/');
      if (await resultsText.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        const text = await resultsText.first().textContent();
        console.log('Resultados encontrados:', text);
      }
    }
  } else {
    console.log('Dashboard não carregou - verificar autenticação');
  }

  // Screenshot final
  await page.screenshot({ path: 'screenshots/06-final.png', fullPage: true });
  console.log('Screenshot 6: Estado final');
});
