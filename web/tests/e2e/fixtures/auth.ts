import { test as base, expect, Page } from '@playwright/test';

/**
 * Fixture de autenticação para testes E2E
 *
 * Usa credenciais reais de staging para testar jornadas completas.
 */

// Credenciais de teste (staging)
const TEST_USER = {
  email: process.env.TEST_USER_EMAIL || 'test@dumontcloud.com',
  password: process.env.TEST_USER_PASSWORD || 'test123456',
};

// API Base URL
const API_BASE = process.env.API_BASE_URL || 'http://localhost:8766';

export interface AuthFixtures {
  authenticatedPage: Page;
  apiToken: string;
}

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    // Login via UI
    await page.goto('/login');

    // Espera carregar
    await page.waitForSelector('input[type="email"], input[name="email"], input[placeholder*="email"]', { timeout: 10000 });

    // Preenche credenciais
    await page.fill('input[type="email"], input[name="email"], input[placeholder*="email"]', TEST_USER.email);
    await page.fill('input[type="password"], input[name="password"]', TEST_USER.password);

    // Clica no botão de login
    await page.click('button[type="submit"], button:has-text("Login"), button:has-text("Entrar")');

    // Espera redirecionamento para dashboard
    await page.waitForURL(/\/(dashboard|machines|home)?$/, { timeout: 15000 });

    // Verifica se está logado
    await expect(page.locator('text=Machines, text=Dashboard, text=GPU').first()).toBeVisible({ timeout: 10000 });

    await use(page);
  },

  apiToken: async ({ }, use) => {
    // Login via API para obter token
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: TEST_USER.email,
        password: TEST_USER.password,
      }),
    });

    if (!response.ok) {
      throw new Error(`Login failed: ${response.status}`);
    }

    const data = await response.json();
    const token = data.access_token || data.token;

    await use(token);
  },
});

export { expect };

/**
 * Helper para fazer requests autenticados à API
 */
export async function apiRequest(
  token: string,
  method: string,
  path: string,
  data?: any
): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * Helper para limpar recursos criados durante testes
 */
export async function cleanupTestResources(token: string, resourceIds: {
  instances?: string[];
  snapshots?: string[];
  associations?: string[];
}) {
  const API = API_BASE;

  // Deletar instâncias
  for (const id of resourceIds.instances || []) {
    try {
      await fetch(`${API}/api/v1/instances/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
    } catch (e) {
      console.log(`Cleanup: failed to delete instance ${id}`);
    }
  }

  // Deletar snapshots
  for (const id of resourceIds.snapshots || []) {
    try {
      await fetch(`${API}/api/v1/snapshots/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
    } catch (e) {
      console.log(`Cleanup: failed to delete snapshot ${id}`);
    }
  }

  // Deletar associações standby
  for (const id of resourceIds.associations || []) {
    try {
      await fetch(`${API}/api/v1/standby/associations/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
    } catch (e) {
      console.log(`Cleanup: failed to delete association ${id}`);
    }
  }
}
