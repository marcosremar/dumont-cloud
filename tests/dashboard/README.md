# Test Dashboard

Dashboard web para executar e visualizar testes do Dumont Cloud.

## Funcionalidades

- **Run Tests** - Executar testes backend (pytest) e frontend (Playwright)
- **Real-time Output** - Ver saida dos testes em tempo real via WebSocket
- **History** - Historico de execucoes com estatisticas
- **Allure Reports** - Integracao com Allure para relatorios detalhados
- **Cancel** - Cancelar testes em execucao

## Instalacao

```bash
cd tests/dashboard
pip install -r requirements.txt
```

## Uso

```bash
# Iniciar o servidor
./start.sh

# Ou diretamente
python server.py

# Acessar no navegador
open http://localhost:8082
```

## API Endpoints

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/` | GET | Dashboard HTML |
| `/api/run` | POST | Iniciar execucao de testes |
| `/api/cancel/{id}` | POST | Cancelar execucao |
| `/api/runs` | GET | Listar execucoes (atuais + historico) |
| `/api/run/{id}` | GET | Detalhes de uma execucao |
| `/api/stats` | GET | Estatisticas gerais |
| `/api/tests` | GET | Listar testes disponiveis |
| `/api/allure/generate` | POST | Gerar relatorio Allure |
| `/ws` | WebSocket | Streaming de output em tempo real |

## Estrutura

```
tests/
├── dashboard/
│   ├── server.py          # Servidor FastAPI
│   ├── requirements.txt   # Dependencias Python
│   ├── start.sh          # Script de inicializacao
│   ├── reports/          # Historico de execucoes
│   └── README.md
├── backend/              # Testes pytest
│   ├── auth/
│   ├── instances/
│   ├── metrics/
│   └── ...
├── e2e-journeys/         # Testes Playwright
└── *.spec.js             # Testes Playwright
```

## Integracao com Allure

Para relatorios Allure detalhados:

```bash
# Instalar Allure CLI
pip install allure-commandline

# Os resultados sao salvos em tests/allure-results/
# Gerar relatorio HTML:
allure generate tests/allure-results -o tests/allure-report --clean
allure open tests/allure-report
```

## Solucoes Alternativas

Se precisar de mais recursos, considere:

1. **[Allure Report](https://allurereport.org/)** - Open source, suporta pytest/playwright
2. **[ReportPortal](https://reportportal.io/)** - Dashboard com ML para analise de falhas
3. **[Playwright UI Mode](https://playwright.dev/docs/test-ui-mode)** - `npx playwright test --ui`
4. **[Currents](https://currents.dev/playwright)** - Dashboard cloud para Playwright

## Screenshots

```
+--------------------------------------------------+
|  Test Dashboard                    [Run Backend] |
+--------------------------------------------------+
|  Stats: 45 runs | 89% pass | 12.3s avg          |
+--------------------------------------------------+
| Tests          |  Terminal Output               |
| - backend (15) |  > pytest backend/ -v          |
| - frontend (8) |  PASSED test_login.py::test... |
|                |  PASSED test_auth.py::test...  |
| History        |  ...                           |
| - backend pass |  5 passed, 0 failed in 8.2s   |
| - frontend fail|                                |
+--------------------------------------------------+
```
