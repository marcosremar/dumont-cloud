import { defineConfig, devices } from '@playwright/test';

/**
 * Dumont Cloud - E2E Test Configuration
 *
 * Testes reais contra APIs de staging/produção.
 * NÃO usa mocks - cria recursos reais.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false, // Sequencial para evitar conflitos de recursos
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Um worker para testes que criam recursos reais
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list']
  ],

  use: {
    baseURL: process.env.TEST_BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Timeouts maiores para operações reais
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },

  timeout: 120000, // 2 minutos por teste (operações reais demoram)

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Servidor de desenvolvimento
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
