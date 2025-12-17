const { test, expect } = require('@playwright/test');

test.describe('Metrics API Tests', () => {
  const BASE_URL = 'https://dumontcloud.com';
  let authToken = null;

  test.beforeAll(async ({ request }) => {
    // Fazer login para obter token
    console.log('Fazendo login...');
    const loginResponse = await request.post(`${BASE_URL}/api/v1/auth/login`, {
      data: {
        email: 'marcosremar@gmail.com',
        password: 'marcos123'
      }
    });

    if (loginResponse.ok()) {
      const data = await loginResponse.json();
      authToken = data.access_token;
      console.log('Login OK, token obtido');
    } else {
      console.log('Login falhou, status:', loginResponse.status());
    }
  });

  test('GET /api/v1/metrics/types - Lista tipos de máquinas', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/metrics/types`, {
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    console.log('Status /metrics/types:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('Tipos de máquinas:', data);
      expect(data).toContain('on-demand');
      expect(data).toContain('interruptible');
      expect(data).toContain('bid');
    } else {
      const text = await response.text();
      console.log('Resposta:', text.substring(0, 500));
    }
  });

  test('GET /api/v1/metrics/gpus - Lista GPUs disponíveis', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/metrics/gpus`, {
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    console.log('Status /metrics/gpus:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('GPUs disponíveis:', data.length > 0 ? data.slice(0, 5) : 'Nenhuma');
    } else {
      const text = await response.text();
      console.log('Resposta:', text.substring(0, 500));
    }
  });

  test('GET /api/v1/metrics/market - Histórico de mercado', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/metrics/market?hours=24&limit=10`, {
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    console.log('Status /metrics/market:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('Snapshots de mercado:', data.length || 0);
      if (data.length > 0) {
        console.log('Exemplo:', JSON.stringify(data[0], null, 2));
      }
    } else {
      const text = await response.text();
      console.log('Resposta:', text.substring(0, 500));
    }
  });

  test('GET /api/v1/metrics/providers - Ranking de provedores', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/metrics/providers?limit=10`, {
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    console.log('Status /metrics/providers:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('Provedores rankeados:', data.length || 0);
      if (data.length > 0) {
        console.log('Top provedor:', JSON.stringify(data[0], null, 2));
      }
    } else {
      const text = await response.text();
      console.log('Resposta:', text.substring(0, 500));
    }
  });

  test('GET /api/v1/metrics/efficiency - Ranking custo-benefício', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/metrics/efficiency?limit=10`, {
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    console.log('Status /metrics/efficiency:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('Rankings de eficiência:', data.length || 0);
      if (data.length > 0) {
        console.log('Top eficiência:', JSON.stringify(data[0], null, 2));
      }
    } else {
      const text = await response.text();
      console.log('Resposta:', text.substring(0, 500));
    }
  });

  test('GET /api/v1/metrics/compare - Comparar GPUs', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/metrics/compare?gpus=RTX%204090,RTX%204080,RTX%203090`, {
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    console.log('Status /metrics/compare:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('Comparação de GPUs:', JSON.stringify(data, null, 2));
    } else {
      const text = await response.text();
      console.log('Resposta:', text.substring(0, 500));
    }
  });

  test('GET /api/v1/metrics/market/summary - Resumo de mercado', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/metrics/market/summary?gpu_name=RTX%204090`, {
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    console.log('Status /metrics/market/summary:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('Resumo de mercado RTX 4090:', JSON.stringify(data, null, 2));
    } else {
      const text = await response.text();
      console.log('Resposta:', text.substring(0, 500));
    }
  });
});

test.describe('UI Page Tests', () => {
  test('Acessar página de métricas', async ({ page }) => {
    test.setTimeout(90000);

    // Capturar erros do console
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('CONSOLE ERROR:', msg.text());
      }
    });

    // 1. Login
    console.log('1. Acessando página de login...');
    await page.goto('https://dumontcloud.com');
    await page.waitForTimeout(2000);

    // Fazer login
    console.log('2. Fazendo login...');
    await page.locator('input[placeholder="Usuario"]').fill('marcosremar@gmail.com');
    await page.locator('input[placeholder="Senha"]').fill('marcos123');
    await page.locator('button[type="submit"]').click();
    await page.waitForTimeout(3000);

    await page.screenshot({ path: '/tmp/metrics_01_after_login.png', fullPage: true });
    console.log('Screenshot 1: Após login');

    // 2. Navegar para métricas
    console.log('3. Navegando para /metrics...');
    await page.goto('https://dumontcloud.com/metrics');
    await page.waitForTimeout(3000);

    await page.screenshot({ path: '/tmp/metrics_02_metrics_page.png', fullPage: true });
    console.log('Screenshot 2: Página de métricas');

    // 3. Verificar elementos da página
    const pageContent = await page.content();
    console.log('Página contém "metrics":', pageContent.toLowerCase().includes('metrics'));
    console.log('Página contém "price":', pageContent.toLowerCase().includes('price'));

    console.log('Teste de UI concluído!');
  });
});
