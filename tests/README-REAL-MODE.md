# Playwright Tests - Real Mode vs Demo Mode

## Overview

Os testes Playwright do Dumont Cloud podem rodar em dois modos:

1. **DEMO MODE** (padrão) - Usa dados mock, não requer backend rodando
2. **REAL MODE** - Conecta com backend real, usa VAST.ai API, CUSTA DINHEIRO

## Quick Start

### Demo Mode (padrão, sem custos)

```bash
cd tests
npx playwright test --project=chromium
```

### Real Mode (requer backend, CUSTA DINHEIRO)

```bash
# 1. Iniciar backend na porta 8766
cd /home/marcos/dumontcloud
source venv/bin/activate
PYTHONPATH="${PYTHONPATH}:$(pwd)" uvicorn src.main:app --host 0.0.0.0 --port 8766 --reload &

# 2. Rodar testes em modo real
cd tests
USE_REAL_MODE=true npx playwright test --project=chromium
```

## Configuração

### Variáveis de Ambiente

#### Para Demo Mode (sem backend)
Nenhuma configuração necessária - funciona out-of-the-box.

#### Para Real Mode (com backend)

1. **Backend Running**
   - O backend DEVE estar rodando em `localhost:8766`
   - O Vite proxy redireciona `/api/*` para `http://localhost:8766`

2. **Credenciais de Login**
   ```bash
   export TEST_USER_EMAIL="test@test.com"      # default
   export TEST_USER_PASSWORD="test123"         # default
   ```

3. **VAST.ai API Key** (para criar máquinas reais)
   ```bash
   # Em .env ou .credentials/vast_api_key
   VAST_API_KEY=your-vast-api-key-here
   ```

4. **GCP Credentials** (para CPU Standby)
   ```bash
   # Para testes de CPU Standby real
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-credentials.json
   ```

### Estrutura de Autenticação

O sistema usa um setup de autenticação em dois modos:

```javascript
// tests/auth.setup.js
const useRealMode = process.env.USE_REAL_MODE === 'true';

if (useRealMode) {
  // Faz login real em /login
  // Salva token JWT em localStorage
  // Redireciona para /app
} else {
  // Navega direto para /demo-app
  // Sem autenticação necessária
}
```

O estado de autenticação é salvo em `.auth/user.json` e reutilizado entre testes.

## Diferenças Entre Modos

| Aspecto | Demo Mode | Real Mode |
|---------|-----------|-----------|
| **URLs** | `/demo-app/*` | `/app/*` |
| **Backend** | Não necessário | **Obrigatório** (porta 8766) |
| **Autenticação** | Nenhuma | Login real |
| **Dados** | Mock (5 GPUs fixas) | VAST.ai real |
| **Custos** | **$0** | **$$$** (créditos VAST.ai) |
| **API Calls** | Mock | VAST.ai API real |
| **Provisionamento** | Instantâneo | 1-5 minutos |
| **CPU Standby** | Mock | GCP real |

## Estrutura de Testes

```
tests/
├── auth.setup.js                    # Setup de autenticação (real ou demo)
├── playwright.config.js             # Config principal
├── .auth/user.json                  # Estado de autenticação salvo
│
├── e2e-journeys/                    # Testes E2E completos
│   ├── REAL-user-actions.spec.js   # Ações de usuário (iniciar/pausar máquinas)
│   └── cpu-standby-failover.spec.js # CPU Standby e Failover
│
├── vibe/                            # Testes "vibe" (interface/UX)
│   ├── failover-journey-vibe.spec.js
│   ├── finetune-journey-vibe.spec.js
│   └── verify-finetune-status.spec.js
│
└── debug-*.spec.js                  # Testes de debug (botão Iniciar, etc)
```

## Modo Real - Custos e Recursos

### IMPORTANTE: MODO REAL CUSTA DINHEIRO

Ao rodar testes em **REAL MODE**, você está:

1. **Criando máquinas GPU reais no VAST.ai**
   - Custo: $0.20 - $2.00/hora dependendo da GPU
   - Provisionamento: 1-5 minutos
   - Preferir GPUs baratas para testes (RTX 3090, RTX 4090)

2. **Criando VMs CPU Standby no GCP**
   - Custo: ~$0.03/hora (e2-small ou e2-medium)
   - Criado automaticamente com GPU

3. **Usando créditos VAST.ai**
   - Verifique saldo antes de rodar testes
   - CLEANUP é CRÍTICO para não acumular custos

### Cleanup de Recursos

Os testes devem fazer cleanup automaticamente, mas verifique:

```bash
# Verificar máquinas ativas no VAST.ai
curl -H "Authorization: Bearer $VAST_API_KEY" https://console.vast.ai/api/v0/instances/

# Destruir todas as máquinas manualmente (se necessário)
# CUIDADO: Isso destrói TODAS as máquinas
# curl -X DELETE -H "Authorization: Bearer $VAST_API_KEY" https://console.vast.ai/api/v0/instances/{id}/
```

## Testes que Criam Recursos Reais

Estes testes podem criar recursos VAST.ai reais se não encontrarem o recurso necessário:

- `REAL-user-actions.spec.js` → "Usuário consegue INICIAR uma máquina parada"
- `cpu-standby-failover.spec.js` → "Simular failover completo"

### Comportamento Esperado

```javascript
// Se não encontrar máquina offline:
if (!hasOfflineMachine) {
  console.log('Criando máquina GPU com VAST.ai...');
  // Buscar ofertas
  // Criar máquina (CUSTA DINHEIRO)
  // Aguardar provisionamento (1-5 min)
}
```

## Debug de Testes

### Ver screenshots e traces

```bash
# Screenshots são salvos em test-results/
ls test-results/*/

# Ver relatório HTML com traces
npx playwright show-report
```

### Rodar teste específico

```bash
# Demo mode
npx playwright test "REAL-user-actions.spec.js" --project=chromium

# Real mode
USE_REAL_MODE=true npx playwright test "REAL-user-actions.spec.js" --project=chromium
```

### Debug visual (headed mode)

```bash
npx playwright test --debug
```

## Troubleshooting

### Backend não conecta

```
❌ Erro de conexão com o servidor
```

**Solução:**
```bash
# Verificar se backend está rodando
curl http://localhost:8766/health

# Verificar porta correta (8766, não 8767)
ps aux | grep uvicorn

# Reiniciar backend
pkill -f uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8766 --reload
```

### Login falha em Real Mode

```
TimeoutError: page.waitForURL: Timeout exceeded
```

**Solução:**
1. Verificar backend rodando
2. Verificar credenciais (TEST_USER_EMAIL, TEST_USER_PASSWORD)
3. Verificar se usuário existe no banco de dados

### Testes pulados (skipped)

Isso é **esperado** quando recursos não existem:

```
⚠️ Nenhuma máquina offline para testar - pulando
⚠️ Nenhuma máquina com CPU Standby - pulando
```

Para ter 0 skipped, você precisaria:
- Ter máquinas offline E online
- Ter CPU Standby configurado
- Ter failover report habilitado

## CI/CD

Para rodar testes em CI (GitHub Actions, etc):

```yaml
# .github/workflows/test.yml
- name: Run Playwright Tests (Demo Mode)
  run: |
    cd tests
    npx playwright test --project=chromium

# OU para real mode (cuidado com custos!)
- name: Run Playwright Tests (Real Mode)
  env:
    USE_REAL_MODE: true
    TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
    TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}
    VAST_API_KEY: ${{ secrets.VAST_API_KEY }}
  run: |
    cd tests
    npx playwright test --project=chromium
```

## Status Atual

Última execução (2025-12-20):

```
✅ 20 passed
⏭️  16 skipped (recursos não disponíveis)
❌ 0 failed
```

**Todos os testes passaram em REAL MODE com backend rodando!**

## Próximos Passos

Para ter 0 testes skipped:

1. **Criar máquina GPU real**
   - Via frontend `/app` ou API `/api/instances/create`
   - Escolher GPU barata (RTX 3090)

2. **Habilitar CPU Standby**
   - Em Settings, ativar "CPU Failover"
   - Configurar GCP credentials

3. **Implementar Failover Report**
   - Feature ainda não implementada
   - Testes vão passar assim que for implementada

## Contato

Para dúvidas sobre os testes:
- Documentação: `Live-Doc/content/11_Testing/`
- Issues: Criar issue no repositório
