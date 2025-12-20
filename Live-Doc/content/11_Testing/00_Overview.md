# Testing Overview

Guia completo de testes para a plataforma Dumont Cloud, incluindo testes de CLI, API, e integracao.

---

## Estrutura de Testes

```
tests/
├── cli/                    # Testes E2E do CLI
│   ├── journeys/          # Jornadas de usuario
│   └── utils/             # Helpers
├── backend/               # Testes do backend Python
│   ├── unit/             # Testes unitarios
│   ├── integration/      # Testes de integracao
│   └── e2e/              # Testes end-to-end
├── e2e-journeys/         # Testes Playwright
│   └── *.spec.js
└── vibe/                  # Testes de UX/Vibe
    └── *.spec.js
```

---

## Tipos de Testes

### 1. CLI E2E Journeys

Testes de jornada completa do usuario via linha de comando.

| Journey | Arquivo | Descricao |
|---------|---------|-----------|
| Auth | `01_auth_journey.sh` | Ciclo de autenticacao |
| Instance | `02_instance_lifecycle.sh` | Criar/gerenciar/destruir GPU |
| Backup | `03_backup_restore.sh` | Snapshots e restore |
| Standby | `04_standby_failover.sh` | CPU standby e failover |
| Finetune | `05_finetune_workflow.sh` | Treinar modelos LLM |
| Spot | `06_spot_analysis.sh` | Analise de mercado |
| Savings | `07_savings_tracking.sh` | Metricas de economia |
| AI Deploy | `08_ai_deploy.sh` | Wizard inteligente |
| Migration | `09_migration.sh` | GPU <-> CPU |
| Health | `10_health_check.sh` | Monitoramento |

**Documentacao completa:** [CLI E2E Journeys](01_CLI_E2E_Journeys.md)

### 2. Backend Tests

Testes do backend FastAPI em Python.

```bash
# Executar todos os testes
pytest tests/backend/

# Com cobertura
pytest tests/backend/ --cov=src --cov-report=html

# Testes especificos
pytest tests/backend/auth/
pytest tests/backend/instances/
pytest tests/backend/snapshots/
```

### 3. Playwright E2E

Testes de interface web com Playwright.

```bash
# Listar testes
npx playwright test --list

# Executar todos
npx playwright test

# Com UI
npx playwright test --ui

# Teste especifico
npx playwright test tests/e2e-journeys/cpu-standby-failover.spec.js
```

### 4. Vibe Tests

Testes de experiencia do usuario e fluxos visuais.

```bash
# Executar vibe tests
npm run test:vibe

# Com debug visual
DEBUG=pw:browser npm run test:vibe
```

---

## Comandos Rapidos

```bash
# Backend
pytest tests/backend/ -v

# CLI
./tests/cli/run_all.sh

# Playwright
npx playwright test

# Tudo
./run-all-tests.sh
```

---

## CI/CD Pipeline

Os testes sao executados automaticamente no GitHub Actions:

| Trigger | Testes | Ambiente |
|---------|--------|----------|
| Push | Unit + Lint | CI |
| PR | Unit + Integration | CI |
| Nightly | E2E Completo | Staging |
| Release | Smoke + E2E | Production |

---

## Cobertura Atual

| Componente | Cobertura | Status |
|------------|-----------|--------|
| Backend API | 78% | OK |
| CLI | 100% | OK |
| Frontend | 65% | Em progresso |
| E2E Journeys | 10/10 | OK |

---

## Proximos Passos

- [ ] Implementar scripts shell para CLI journeys
- [ ] Aumentar cobertura frontend para 80%
- [ ] Adicionar testes de performance
- [ ] Dashboard de resultados em tempo real
