# Specification: Verificar e Corrigir Migração GPU-para-CPU na Criação de Máquinas

## Overview

Esta tarefa visa verificar e, se necessário, corrigir a funcionalidade de migração de GPU para CPU durante a criação de máquinas. Esta é uma feature de otimização de custos que permite migrar workloads de instâncias GPU (mais caras) para instâncias CPU (mais baratas) quando a GPU não está sendo utilizada. A verificação será feita através de testes de interface (Playwright) já existentes no projeto, identificando se a funcionalidade está operacional e corrigindo eventuais problemas.

## Workflow Type

**Type**: investigation

**Rationale**: Esta é uma tarefa de investigação e verificação de funcionalidade existente. O objetivo primário é verificar se a migração GPU→CPU funciona corretamente, executar os testes existentes e, apenas se necessário, corrigir problemas identificados. Não é desenvolvimento de nova feature, mas sim validação de feature existente.

## Task Scope

### Services Involved
- **tests** (primary) - Contém a infraestrutura Playwright e testes E2E de failover/migração
- **web** (integration) - Frontend React onde a UI de máquinas e migração é apresentada
- **src/domain/services** (reference) - Contém a lógica de migração (`migration_service.py`)
- **cli** (reference) - Backend Python com API endpoints

### This Task Will:
- [x] Verificar se Playwright está instalado e configurado corretamente
- [x] Executar testes E2E existentes relacionados a CPU Standby e Failover
- [x] Identificar testes que validam migração GPU→CPU
- [x] Analisar resultados dos testes e identificar falhas
- [ ] Corrigir testes ou funcionalidade se estiverem quebrados
- [ ] Garantir que a migração GPU→CPU funciona no fluxo de criação de máquina

### Out of Scope:
- Criação de nova funcionalidade de migração
- Mudanças na arquitetura do sistema
- Testes de performance ou carga
- Modificações no backend de migração (apenas se absolutamente necessário)
- Testes de outros frameworks além de Playwright

## Service Context

### Tests Service

**Tech Stack:**
- Language: JavaScript
- Framework: Playwright Test
- Package Manager: npm

**Entry Point:** `tests/playwright.config.js`

**How to Run:**
```bash
cd tests && npm test
# ou
cd tests && npx playwright test
```

**Key Directories:**
- `tests/e2e-journeys/` - Testes de jornadas E2E
- `tests/helpers/` - Funções auxiliares
- `tests/.auth/` - Estado de autenticação salvo

**Port:** N/A (testes de UI acessam frontend em localhost:5173)

### Web Service

**Tech Stack:**
- Language: JavaScript/JSX
- Framework: React + Vite
- Build Tool: Vite
- Styling: Tailwind CSS
- State Management: Redux

**Entry Point:** `web/src/App.jsx`

**How to Run:**
```bash
cd web && npm run dev
```

**Port:** 5173 (dev), 8000 (production)

### Backend (CLI/API)

**Tech Stack:**
- Language: Python
- Framework: FastAPI

**Entry Point:** `cli/__main__.py`

**Port:** 8000 (APP_PORT)

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `tests/e2e-journeys/cpu-standby-failover.spec.js` | tests | Verificar/corrigir testes de CPU Standby e Failover |
| `tests/e2e-journeys/failover-complete-journeys.spec.js` | tests | Verificar/corrigir testes completos de failover |
| `tests/e2e-journeys/failover-strategy-selection.spec.js` | tests | Verificar testes de seleção de estratégia de failover |
| `tests/playwright.config.js` | tests | Ajustar configuração se necessário |
| `tests/auth.setup.js` | tests | Verificar setup de autenticação |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `src/domain/services/migration_service.py` | Lógica de migração GPU↔CPU com snapshots |
| `src/services/machine_setup_service.py` | Setup completo de máquinas GPU |
| `tests/e2e-journeys/machine-details-actions.spec.js` | Padrão de testes de ações em máquinas |
| `tests/auth.setup.js` | Padrão de autenticação para testes |
| `web/src/pages/Machines.jsx` | Componente de listagem de máquinas |

## Patterns to Follow

### Playwright Test Pattern

From `tests/e2e-journeys/cpu-standby-failover.spec.js`:

```javascript
const { test, expect } = require('@playwright/test');

test.describe('Description', () => {
  test('Test case name', async ({ page }) => {
    // Navigate
    await page.goto('/app/machines');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Find elements with flexible matching
    const element = await page.getByText(/pattern/i).first().isVisible({ timeout: 5000 }).catch(() => false);

    // Assert
    expect(element).toBeTruthy();
  });
});
```

**Key Points:**
- Usar `page.getByText()` e `page.getByRole()` com `.first()` para evitar múltiplos matches
- Sempre usar `.catch(() => false)` para elementos opcionais
- Usar timeouts generosos (5000ms+) para elementos assíncronos
- Usar `{ force: true }` em clicks quando necessário

### Migration Service Flow

From `src/domain/services/migration_service.py`:

```python
# Migration flow steps:
# 1. Validate source instance
# 2. Create snapshot of source instance
# 3. Search for target offers (GPU or CPU)
# 4. Create new instance
# 5. Wait for SSH ready
# 6. Restore snapshot to new instance
# 7. Destroy source (if auto_destroy_source=True)
```

**Key Points:**
- Migração preserva dados via snapshot/restore
- Suporta GPU→CPU e CPU→GPU
- Usa vast.ai API para buscar ofertas

## Requirements

### Functional Requirements

1. **Verificar Infraestrutura de Testes**
   - Description: Confirmar que Playwright está instalado e configurável
   - Acceptance: `npx playwright test --version` retorna versão válida

2. **Executar Testes de Failover/Migração**
   - Description: Rodar testes E2E que validam migração GPU↔CPU
   - Acceptance: Testes em `e2e-journeys/*failover*.spec.js` executam sem erros críticos

3. **Validar Funcionalidade de Migração na UI**
   - Description: Verificar que UI permite configurar e simular failover
   - Acceptance: Página de máquinas mostra opções de backup/failover

4. **Corrigir Problemas Identificados**
   - Description: Se testes falharem, identificar e corrigir a causa
   - Acceptance: Testes passam após correções

### Edge Cases

1. **Sem máquinas disponíveis** - Testes devem funcionar com dados mockados (demo mode)
2. **Timeout de autenticação** - Auth setup deve lidar com modais de boas-vindas
3. **Múltiplos elementos matching** - Usar `.first()` para evitar erros de seleção
4. **Elementos não visíveis** - Usar `catch(() => false)` para falhas graceful

## Implementation Notes

### DO
- Execute `npm install` em `tests/` antes de rodar testes
- Use `USE_DEMO_MODE=true` para testes com dados mockados
- Verifique se o frontend está rodando em localhost:5173 antes de testes
- Siga o padrão de autenticação em `auth.setup.js`
- Use console.log para debugging de fluxos
- Mantenha testes resilientes com fallbacks

### DON'T
- Não modifique lógica de migração no backend sem necessidade
- Não crie novos frameworks de teste
- Não quebre testes existentes que passam
- Não use seletores frágeis (IDs dinâmicos, classes minificadas)
- Não assuma que elementos estarão sempre visíveis

## Development Environment

### Start Services

```bash
# Terminal 1: Frontend
cd web && npm run dev

# Terminal 2: Backend (se necessário)
cd cli && python -m uvicorn main:app --reload --port 8000

# Terminal 3: Testes
cd tests && npm test
```

### Service URLs
- Frontend (Dev): http://localhost:5173
- Frontend (App): http://localhost:5173/app
- Backend API: http://localhost:8000
- Login: http://localhost:5173/login

### Required Environment Variables
- `BASE_URL`: http://localhost:5173 (default no playwright.config.js)
- `TEST_USER_EMAIL`: marcosremar@gmail.com (default)
- `TEST_USER_PASSWORD`: dumont123 (default)
- `USE_DEMO_MODE`: true/false para dados mockados

## Success Criteria

The task is complete when:

1. [x] Playwright instalado e funcional no diretório `tests/`
2. [ ] Testes de CPU Standby/Failover executam sem erros
3. [ ] Migração GPU→CPU é validada pela UI (botões/badges visíveis)
4. [ ] Nenhum teste existente regrediu
5. [ ] Documentado status atual dos testes e correções feitas

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| N/A | - | Esta tarefa foca em testes E2E, não unitários |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| CPU Standby Config | web ↔ backend | Configuração de CPU Standby persiste |
| Failover Simulation | web ↔ backend | Simulação de failover inicia corretamente |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Verificar CPU Standby | 1. Login 2. Ir para /app/machines 3. Verificar badge Backup | Badge de backup visível em máquinas com standby |
| Simular Failover | 1. Login 2. Ir para /app/machines 3. Clicar Simular Failover | Painel de progresso aparece |
| Configurar Failover | 1. Login 2. Ir para /app/settings 3. Acessar aba CPU Failover | Configurações de failover visíveis |
| Relatório Failover | 1. Login 2. Ir para /app/failover-report | Página de relatório carrega |

### Browser Verification (if frontend)
| Page/Component | URL | Checks |
|----------------|-----|--------|
| Machines List | `http://localhost:5173/app/machines` | Cards de máquinas com badge Backup/Standby |
| Settings | `http://localhost:5173/app/settings` | Aba CPU Failover presente |
| Failover Report | `http://localhost:5173/app/failover-report` | Métricas e histórico de failover |
| Dashboard | `http://localhost:5173/app` | Métricas de economia/savings |

### Database Verification (if applicable)
| Check | Query/Command | Expected |
|-------|---------------|----------|
| N/A | - | Esta tarefa não modifica banco de dados |

### QA Sign-off Requirements
- [ ] Todos os testes E2E de failover passam
- [ ] Testes de CPU Standby executam sem erro
- [ ] Navegação entre páginas funciona
- [ ] Verificação visual das páginas de máquinas completada
- [ ] Sem regressões em funcionalidade existente
- [ ] Código segue padrões estabelecidos de Playwright
- [ ] Nenhuma vulnerabilidade de segurança introduzida

## Test Commands Reference

```bash
# Instalar dependências
cd tests && npm install

# Rodar todos os testes
npx playwright test

# Rodar apenas testes de failover
npx playwright test e2e-journeys/cpu-standby-failover.spec.js
npx playwright test e2e-journeys/failover-complete-journeys.spec.js

# Rodar em modo headed (ver browser)
npx playwright test --headed

# Rodar com UI interativo
npx playwright test --ui

# Rodar em debug mode
npx playwright test --debug

# Ver relatório HTML
npx playwright show-report
```

## Existing Test Files Summary

1. **cpu-standby-failover.spec.js** - 7 testes de CPU Standby e Failover
2. **failover-complete-journeys.spec.js** - 15+ testes de jornadas completas
3. **failover-strategy-selection.spec.js** - Testes de seleção de estratégia
4. **machine-details-actions.spec.js** - Ações em detalhes de máquina
