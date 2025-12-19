# Vibe Tests - Quick Start Guide

Guia rápido para executar os Vibe Tests do Dumont Cloud.

## Execução Rápida

### Opção 1: Usar o Script Helper (Recomendado)

```bash
# Executar TODOS os vibe tests
./run-vibe-tests.sh

# Executar apenas o teste de Failover
./run-vibe-tests.sh --failover

# Executar com UI (debugger visual)
./run-vibe-tests.sh --failover --ui

# Executar com browser visível
./run-vibe-tests.sh --failover --headed

# Gerar relatório HTML
./run-vibe-tests.sh --failover --html
```

### Opção 2: Usar Comandos Playwright Diretos

```bash
# Executar vibe test de failover
npx playwright test tests/vibe/failover-journey-vibe.spec.js --project=chromium

# Executar todos os vibe tests
npx playwright test tests/vibe/ --project=chromium

# Modo UI (visual debugger)
npx playwright test tests/vibe/failover-journey-vibe.spec.js --ui

# Browser visível (headed)
npx playwright test tests/vibe/failover-journey-vibe.spec.js --headed

# Gerar relatório HTML
npx playwright test tests/vibe/ --reporter=html
npx playwright show-report
```

## Pré-requisitos

1. **Servidor de desenvolvimento rodando**:
```bash
cd web
npm run dev
# Deve estar disponível em http://localhost:5173
```

2. **Playwright instalado**:
```bash
npm install
npx playwright install chromium
```

3. **Autenticação configurada**:
```bash
# Executar setup de autenticação (automático se usar script)
npx playwright test tests/e2e-journeys/auth.setup.js --project=setup
```

## Modo Debug

### Debug com Playwright Inspector

```bash
# Abre o Playwright Inspector
npx playwright test tests/vibe/failover-journey-vibe.spec.js --debug
```

### Ver Traces de Falhas

```bash
# Executar com trace
npx playwright test tests/vibe/ --trace on

# Ver o trace
npx playwright show-trace test-results/[test-name]/trace.zip
```

### Ver Screenshots e Vídeos

Screenshots e vídeos são salvos automaticamente em falhas:

```bash
# Ver screenshots
ls test-results/*/test-failed-*.png

# Ver vídeos
ls test-results/*/video.webm
```

## Executar Contra Staging Real

### 1. Editar playwright.config.js

```javascript
use: {
  baseURL: 'https://dumontcloud.com',  // Mudar de localhost
  // ...
}
```

### 2. Executar o teste

```bash
npx playwright test tests/vibe/failover-journey-vibe.spec.js --project=chromium
```

### 3. Reverter para localhost

```javascript
use: {
  baseURL: 'http://localhost:5173',  // Voltar para dev
  // ...
}
```

## Resultado Esperado

### Sucesso Total

```
========================================
VIBE TEST: CPU Standby & Failover Journey
Environment: REAL (no mocks)
========================================

STEP 1: Login
Time: 2448ms
Status: Authenticated and navigated to Machines
Validated: URL contains /app/machines

STEP 2: Find machine with CPU Standby
Time: 2000ms
Status: Found machine with backup
Validated: Badge "Backup" is visible

... (16 steps total)

========================================
VIBE TEST COMPLETE!
========================================
Total journey time: 35240ms (35.24s)

Phase Breakdown:
  Phase 1 (GPU Lost):        1500ms
  Phase 2 (CPU Failover):    2500ms
  Phase 3 (GPU Search):      3000ms
  Phase 4 (Provisioning):    3500ms
  Phase 5 (Restoration):     3000ms
  Phase 6 (Complete):        4000ms

All validations passed:
  - Real environment (no mocks)
  - All 6 phases completed
  - Visual feedback validated
  - Metrics captured
  - Report verified
  - History updated
========================================

1 passed (35.2s)
```

### Graceful Skip (Normal em Dev)

```
STEP 1: Login
Time: 2448ms
Status: Authenticated and navigated to Machines
Validated: URL contains /app/machines

STEP 2: Find machine with CPU Standby
Status: No machines with CPU Standby found
Note: This is a graceful skip - environment may not have standby machines

1 skipped, 1 passed (13.1s)
```

Este é o comportamento **esperado** em ambiente de desenvolvimento sem máquinas reais. O teste faz um skip gracioso.

## Troubleshooting

### Problema: "No dev server running"

**Solução**:
```bash
cd web
npm run dev
```

### Problema: "Auth file not found"

**Solução**:
```bash
npx playwright test tests/e2e-journeys/auth.setup.js --project=setup
```

### Problema: "Browser not found"

**Solução**:
```bash
npx playwright install chromium
```

### Problema: "Timeout waiting for element"

**Possíveis causas**:
- Servidor muito lento
- Elemento mudou de estrutura
- Demo mode habilitado (bug)

**Debug**:
```bash
# Executar com headed para ver o que está acontecendo
npx playwright test tests/vibe/failover-journey-vibe.spec.js --headed

# Ou usar UI mode
npx playwright test tests/vibe/failover-journey-vibe.spec.js --ui
```

## Próximos Passos

Depois de executar os vibe tests com sucesso:

1. Revisar os logs de saída
2. Verificar métricas de performance
3. Se houver falhas, analisar screenshots/vídeos
4. Validar que o ambiente está configurado corretamente
5. Executar contra staging para testes finais

## Comandos Úteis

```bash
# Listar todos os testes disponíveis
npx playwright test --list

# Executar apenas um teste específico por nome
npx playwright test -g "should complete full failover"

# Executar com workers paralelos (mais rápido)
npx playwright test tests/vibe/ --workers=2

# Executar com retry em falhas
npx playwright test tests/vibe/ --retries=2

# Executar apenas testes que falharam
npx playwright test --last-failed
```

## Integração CI/CD

Para rodar em CI/CD (GitHub Actions, etc):

```yaml
- name: Run Vibe Tests
  run: |
    npx playwright test tests/vibe/ --project=chromium
  env:
    CI: true
```

## Referências

- [README completo](./README.md) - Documentação detalhada
- [Failover Vibe Test](./failover-journey-vibe.spec.js) - Código do teste
- [Playwright Docs](https://playwright.dev/) - Documentação oficial

---

**Última atualização**: 2025-12-19
