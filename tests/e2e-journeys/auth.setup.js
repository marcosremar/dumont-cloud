// @ts-check
const { test: setup, expect } = require('@playwright/test');
const path = require('path');

const authFile = path.join(__dirname, '../.auth/user.json');

/**
 * Setup de autenticação global
 * Este setup roda UMA vez antes de todos os testes
 * e salva o estado de autenticação para reutilização
 */
setup('authenticate', async ({ page }) => {
  // 1. Vai para login
  console.log('📍 Navigating to /login');
  await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
  console.log('✅ Login page loaded');

  // 2. Aguarda o formulário carregar
  await page.waitForLoadState('networkidle');
  console.log('✅ Network idle reached');

  // 3. Preenche credenciais - o formulário usa textbox genérico
  // Primeiro textbox é Username, segundo é Password
  const usernameInput = page.getByRole('textbox').first();
  const passwordInput = page.locator('input[type="password"]');
  const submitButton = page.getByRole('button', { name: /login|entrar/i });

  console.log('🔐 Filling credentials');
  await usernameInput.fill('test@test.com');
  await passwordInput.fill('test123');

  // 4. Click login e aguarda navegação
  console.log('📤 Submitting login');
  await submitButton.click();

  // 5. Aguarda o token ser armazenado no localStorage
  console.log('⏳ Waiting for auth_token to be stored...');
  await page.waitForFunction(() => {
    const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
    return token && token.length > 10;
  }, { timeout: 10000 });

  console.log('✅ Auth token stored');

  // 6. Verifica se navegou para uma página autenticada
  await page.waitForTimeout(500);
  const currentUrl = page.url();
  console.log('📍 Current URL after login:', currentUrl);

  // 7. Salva estado de autenticação
  await page.context().storageState({ path: authFile });

  // 8. Remove demo_mode flag to ensure real API usage in tests
  await page.evaluate(() => {
    localStorage.removeItem('demo_mode');
  });

  // 9. Verifica o token salvo
  const token = await page.evaluate(() => localStorage.getItem('auth_token'));
  console.log('🔑 Token saved:', token ? `${token.substring(0, 20)}...` : 'NONE');

  // 10. Salva estado final (sem demo_mode)
  await page.context().storageState({ path: authFile });

  console.log('✅ Autenticação salva em', authFile);
});
