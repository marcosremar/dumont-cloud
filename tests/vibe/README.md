# Vibe Tests - Dumont Cloud

Vibe Tests são testes end-to-end que simulam comportamento REAL de usuários em ambientes de staging/production. Eles **NUNCA** usam mocks ou dados falsos - sempre testam contra sistemas reais.

## Filosofia dos Vibe Tests

1. **REAL Environment Only** - Sem mocks, sem demo mode, sem dados falsos
2. **User Behavior Simulation** - Clicks, waits, navegação natural
3. **Performance Metrics** - Captura tempo de cada ação
4. **Visual Feedback Validation** - Verifica toasts, spinners, loading states
5. **Complete Journeys** - Testa fluxos completos, não ações isoladas

## Estrutura de Diretórios

```
tests/
├── vibe/                           # Vibe tests (comportamento real)
│   ├── failover-journey-vibe.spec.js
│   ├── finetune-journey-vibe.spec.js
│   └── README.md (este arquivo)
├── e2e-journeys/                   # E2E tests funcionais
│   ├── auth.setup.js               # Setup de autenticação
│   └── cpu-standby-failover.spec.js
└── .auth/
    └── user.json                   # Estado de autenticação salvo
```

## Testes Disponíveis

### 1. Failover Journey Vibe Test
**Arquivo**: `tests/vibe/failover-journey-vibe.spec.js`

**Jornada completa testada**:
1. Login com credenciais reais
2. Navegar para /app/machines
3. Encontrar máquina com CPU Standby (badge "Backup")
4. Clicar em "Simular Failover"
5. Observar 6 fases do failover em tempo real:
   - GPU Interrompida
   - Failover para CPU Standby
   - Buscando Nova GPU
   - Provisionando
   - Restaurando Dados
   - Recuperação Completa
6. Validar métricas de latência
7. Navegar para /app/settings?tab=failover
8. Verificar relatório de failover
9. Validar histórico de eventos

**Tempo esperado**: ~30-45 segundos (ambiente real)

**Métricas capturadas**:
- Tempo total da jornada
- Tempo de cada fase do failover
- Tempo de navegação
- Tempo de carregamento de relatórios

---

### 2. Fine-Tuning Journey Vibe Test
**Arquivo**: `tests/vibe/finetune-journey-vibe.spec.js`

**Jornada completa testada**:
1. Login com credenciais reais
2. Navegar para /app/finetune
3. Verificar dashboard com stats (Total Jobs, Running, Completed, Failed)
4. Clicar em "New Fine-Tune Job"
5. **Step 1**: Selecionar modelo Phi-3 Mini (3.8B params, 8GB VRAM)
6. **Step 2**: Configurar dataset via URL (HuggingFace Alpaca dataset)
7. **Step 3**: Configurar job (nome, GPU A100, parâmetros avançados)
8. **Step 4**: Review e Launch
9. Validar job criado aparece na lista
10. Verificar status (pending/queued)
11. Testar action buttons (Refresh, Logs)

**Tempo esperado**: ~20-30 segundos (criação do job apenas)

**Métricas capturadas**:
- Tempo total da jornada
- Tempo de cada step do wizard
- Tempo de resposta da API
- Tempo de atualização do dashboard

**Nota**: Este teste cria um job REAL no ambiente. O job será provisionado via SkyPilot no GCP.

## Como Executar

### Pré-requisitos

1. Backend rodando (Flask API)
2. Frontend rodando (Vite dev server ou build)
3. Credenciais válidas configuradas

### Setup Inicial

```bash
# 1. Instalar dependências do Playwright
npm install

# 2. Instalar browsers do Playwright
npx playwright install chromium

# 3. Iniciar o servidor de desenvolvimento
cd web && npm run dev
```

### Executar Testes

```bash
# Executar TODOS os vibe tests
npx playwright test tests/vibe/ --project=chromium

# Executar teste específico (Failover)
npx playwright test tests/vibe/failover-journey-vibe.spec.js --project=chromium

# Executar teste específico (Fine-Tuning)
npx playwright test tests/vibe/finetune-journey-vibe.spec.js --project=chromium

# Executar com UI (modo debug)
npx playwright test tests/vibe/finetune-journey-vibe.spec.js --ui

# Executar com headed browser (ver o navegador)
npx playwright test tests/vibe/finetune-journey-vibe.spec.js --headed

# Gerar relatório HTML
npx playwright test tests/vibe/ --project=chromium --reporter=html
npx playwright show-report
```

### Executar contra Staging Real

Para executar contra o ambiente de staging (https://dumontcloud.com):

1. Editar `playwright.config.js`:
```javascript
use: {
  baseURL: 'https://dumontcloud.com', // Mudar de localhost para staging
  // ...
}
```

2. Executar o teste:
```bash
npx playwright test tests/vibe/failover-journey-vibe.spec.js --project=chromium
```

## Estrutura de um Vibe Test

```javascript
// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Journey Name - Vibe Test', () => {

  test.beforeEach(async ({ page }) => {
    // CRITICAL: Sempre desabilitar demo mode
    await page.addInitScript(() => {
      localStorage.removeItem('demo_mode');
      localStorage.setItem('demo_mode', 'false');
    });
  });

  test('should complete [journey name] with real environment', async ({ page }) => {
    const startTime = Date.now();

    // STEP 1: [Description]
    console.log('STEP 1: [Description]');
    const step1Start = Date.now();

    await page.goto('/some-page');
    await page.waitForLoadState('networkidle');

    const step1Duration = Date.now() - step1Start;
    console.log(`Time: ${step1Duration}ms`);
    console.log('Status: [What happened]');
    console.log('Validated: [What was verified]');

    // STEP 2, 3, 4...
    // ...

    // FINAL SUMMARY
    const totalDuration = Date.now() - startTime;
    console.log('\n========================================');
    console.log('VIBE TEST COMPLETE!');
    console.log('========================================');
    console.log(`Total journey time: ${totalDuration}ms`);
    console.log('All validations passed');
    console.log('========================================\n');

    expect(true).toBeTruthy();
  });
});
```

## Padrões e Boas Práticas

### 1. Sempre Esperar por Loading States
```javascript
// BOA PRÁTICA
await page.goto('/app/machines');
await page.waitForLoadState('networkidle');
await page.waitForTimeout(1000); // Buffer para animações

// MÁ PRÁTICA
await page.goto('/app/machines');
// Não espera nada - pode falhar
```

### 2. Usar data-testid Quando Possível
```javascript
// BOA PRÁTICA
const panel = page.locator('[data-testid="failover-progress-panel"]');

// ALTERNATIVA (quando data-testid não existe)
const panel = page.locator('[class*="rounded-lg"]').filter({
  has: page.locator('text="Backup"')
});
```

### 3. Graceful Skips
```javascript
// Se algo não está disponível, skip graciosamente
const hasMachine = await machineLocator.isVisible().catch(() => false);
if (!hasMachine) {
  console.log('⚠️ No machine found - skipping gracefully');
  test.skip();
  return;
}
```

### 4. Capturar Métricas
```javascript
const stepStart = Date.now();

// ... ação

const stepDuration = Date.now() - stepStart;
console.log(`⏱️ Action took ${stepDuration}ms`);
```

### 5. Logs Estruturados
```javascript
console.log('\nSTEP 5: Phase 1 - GPU Interrompida');
console.log(`⏱️ Time: ${duration}ms`);
console.log('✅ Status: Phase completed');
console.log('📊 Validated: Step panel visible');
```

## Debug e Troubleshooting

### Ver Screenshots de Falhas
```bash
# Playwright salva screenshots automaticamente em falhas
ls test-results/
```

### Ver Vídeos de Execução
```bash
# Playwright grava vídeo em falhas
ls test-results/*/video.webm
```

### Executar com Trace
```bash
# Gerar trace completo (útil para debug)
npx playwright test tests/vibe/ --trace on

# Ver o trace
npx playwright show-trace test-results/[test-name]/trace.zip
```

### Inspecionar Estado da Página
```bash
# Modo debug com Playwright Inspector
npx playwright test tests/vibe/ --debug
```

## Validações Críticas

Cada vibe test DEVE validar:

1. **URL Correta** - Após navegações
2. **Loading States** - Esperar networkidle
3. **Visual Feedback** - Toasts, spinners, progress bars
4. **Data Visibility** - Elementos com dados reais aparecem
5. **User Actions** - Clicks, fills funcionam
6. **Timeouts** - Nenhuma ação demora mais que o esperado
7. **Error States** - Erros são tratados graciosamente

## Métricas de Sucesso

Um vibe test é bem-sucedido quando:

- ✅ Executa contra ambiente REAL (sem mocks)
- ✅ Completa toda a jornada
- ✅ Captura métricas de performance
- ✅ Valida feedback visual
- ✅ Passa consistentemente (>95% success rate)
- ✅ Detecta problemas reais de UX
- ✅ Tempo de execução razoável (<2 min)

## Próximos Vibe Tests a Criar

1. **New User Journey** - Do signup até primeira máquina criada
2. **Metrics Hub Journey** - Navegação e validação de métricas
3. **Settings Journey** - Modificação de configurações
4. **Destroy Machine Journey** - Destruição de máquina e cleanup
5. **Search & Filter Journey** - Busca e filtros em máquinas
6. **Fine-Tuning Job Monitoring** - Acompanhar job durante execução (logs em tempo real)
7. **Fine-Tuning Job Completion** - Validar job completo e download do modelo

## Referências

- [Playwright Documentation](https://playwright.dev/)
- [Vibe Testing Philosophy](https://github.com/dumont-cloud/docs/vibe-testing.md)
- [E2E Testing Best Practices](https://playwright.dev/docs/best-practices)

---

**Última atualização**: 2025-12-19
**Mantido por**: Equipe Dumont Cloud
