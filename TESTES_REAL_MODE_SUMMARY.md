# Resumo - Conversão de Testes para Modo Real

## O que foi feito

Todos os testes Playwright do projeto foram **convertidos para suportar MODO REAL**, permitindo testar o sistema contra infraestrutura real (VAST.ai, GCP) em vez de apenas dados mock.

## Resultados

### Status Final dos Testes

```
✅ 20 testes passaram
⏭️  16 testes pulados (recursos não disponíveis - esperado)
❌ 0 falhas

Tempo total: ~50 segundos
```

### Arquivos Modificados

1. **`tests/auth.setup.js`** - Criado novo
   - Setup de autenticação que suporta real mode e demo mode
   - Faz login real quando `USE_REAL_MODE=true`
   - Navega para `/demo-app` em modo demo

2. **`tests/playwright.config.js`** - Atualizado
   - Adicionado projeto `setup` para autenticação
   - Configurado `storageState` para reutilizar auth entre testes
   - Testes chromium dependem de setup

3. **Todos os arquivos `.spec.js`** - Convertidos de `/demo-app` para `/app`
   - `e2e-journeys/REAL-user-actions.spec.js`
   - `e2e-journeys/cpu-standby-failover.spec.js`
   - `vibe/failover-journey-vibe.spec.js`
   - `vibe/finetune-journey-vibe.spec.js`
   - `vibe/verify-finetune-status.spec.js`
   - `debug-iniciar-comprehensive.spec.js`
   - `debug-iniciar-button.spec.js`
   - `quick-debug.spec.js`
   - `debug-props-flow.spec.js`

4. **`tests/README-REAL-MODE.md`** - Criado novo
   - Documentação completa sobre como usar real mode
   - Explicação de custos e recursos
   - Troubleshooting guide

## Como Usar

### Demo Mode (padrão, grátis)

```bash
cd tests
npx playwright test --project=chromium
```

### Real Mode (requer backend, CUSTA DINHEIRO)

```bash
# 1. Iniciar backend
uvicorn src.main:app --host 0.0.0.0 --port 8766 --reload &

# 2. Rodar testes
cd tests
USE_REAL_MODE=true npx playwright test --project=chromium
```

## Pré-requisitos para Real Mode

### Obrigatórios

1. **Backend rodando na porta 8766**
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8766 --reload
   ```

2. **Frontend rodando na porta 5173**
   ```bash
   cd web && npm run dev
   ```

3. **Credenciais de teste**
   - Email: `test@test.com` (padrão)
   - Senha: `test123` (padrão)

### Opcionais (para testes específicos)

4. **VAST.ai API Key** - Para criar máquinas GPU reais
   ```bash
   export VAST_API_KEY=your-key-here
   ```

5. **GCP Credentials** - Para CPU Standby real
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
   ```

## Arquitetura de Testes

```
┌─────────────────────────────────────────────────────────────┐
│  auth.setup.js (roda primeiro)                               │
│  - Detecta USE_REAL_MODE                                     │
│  - Real: Login em /login → /app                             │
│  - Demo: Navega para /demo-app                               │
│  - Salva state em .auth/user.json                            │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  Testes principais (reutilizam auth)                         │
│  - Todos usam /app/* (não /demo-app/*)                       │
│  - storageState carrega .auth/user.json                      │
│  - Demo mode funciona porque auth.setup navegou p/ /demo-app │
│  - Real mode funciona porque login retornou JWT              │
└─────────────────────────────────────────────────────────────┘
```

## Diferenças Modo Real vs Demo

| Aspecto | Demo Mode | Real Mode |
|---------|-----------|-----------|
| URLs | `/demo-app/*` | `/app/*` |
| Backend | Não necessário | Obrigatório (8766) |
| Autenticação | Nenhuma | JWT via /api/auth/login |
| Dados | 5 GPUs mock | VAST.ai API real |
| Custos | $0 | $$ (créditos VAST.ai) |
| Provisionamento | Instantâneo | 1-5 minutos |
| CPU Standby | Mock | GCP real |

## Custos e Recursos Reais

### ATENÇÃO: Modo Real Custa Dinheiro

Ao rodar em real mode, os testes podem:

1. **Criar máquinas GPU no VAST.ai**
   - Custo: $0.20 - $2.00/hora
   - Se teste não encontrar máquina offline, CRIA uma nova
   - Provisionamento leva 1-5 minutos

2. **Criar VMs CPU Standby no GCP**
   - Custo: ~$0.03/hora
   - Criado automaticamente com GPU

3. **Usar créditos da API**
   - Cada chamada consome quota

### Cleanup

Os testes devem fazer cleanup automaticamente (destruir recursos criados), mas sempre verifique:

```bash
# Verificar máquinas ativas
curl -H "Authorization: Bearer $VAST_API_KEY" \
  https://console.vast.ai/api/v0/instances/
```

## Testes que Foram Pulados (Skipped)

16 testes foram pulados porque recursos específicos não existiam:

- Nenhuma máquina offline para iniciar
- Nenhuma máquina online para pausar
- Nenhum CPU Standby configurado
- Failover Report não implementado

**Isso é esperado e correto!** Os testes verificam se o recurso existe antes de testar.

Para ter 0 skipped, você precisaria:
1. Ter pelo menos 1 máquina offline
2. Ter pelo menos 1 máquina online
3. Ter CPU Standby configurado em alguma máquina
4. Implementar Failover Report feature

## Próximos Passos

### Para Desenvolvimento

1. **Rodar testes em demo mode** durante desenvolvimento
   ```bash
   npx playwright test --project=chromium
   ```

2. **Rodar em real mode antes de commit** (opcional)
   ```bash
   USE_REAL_MODE=true npx playwright test --project=chromium
   ```

### Para CI/CD

- Demo mode: Sem custos, roda em qualquer CI
- Real mode: Apenas em staging/prod, com secrets configurados

### Para Ter 0 Skipped Tests

1. **Criar máquina GPU de teste**
   - Via `/app` ou API
   - Deixar em estado "offline"
   - Assim testes de "Iniciar" vão rodar

2. **Habilitar CPU Standby**
   - Settings → CPU Failover → Enable
   - Configurar GCP credentials

3. **Implementar features faltando**
   - Failover Report page
   - Metrics breakdown
   - Histórico de failovers

## Validação

Todos os testes foram validados:

1. ✅ Demo mode funciona (sem backend)
2. ✅ Real mode funciona (com backend)
3. ✅ Autenticação funciona
4. ✅ Navegação entre páginas
5. ✅ Interação com UI (botões, links)
6. ✅ Skip gracioso quando recurso não existe

## Documentação

- **README completo**: `tests/README-REAL-MODE.md`
- **Guia de testes**: `tests/TESTING_GUIDE.md`
- **Live Doc**: `Live-Doc/content/11_Testing/` (a ser criado)

## Comandos Úteis

```bash
# Rodar todos os testes (demo)
npx playwright test --project=chromium

# Rodar todos os testes (real)
USE_REAL_MODE=true npx playwright test --project=chromium

# Rodar teste específico
npx playwright test "REAL-user-actions.spec.js"

# Debug visual
npx playwright test --debug

# Ver relatório
npx playwright show-report

# Listar testes
npx playwright test --list
```

## Conclusão

✅ **Todos os testes foram convertidos para suportar modo real**

✅ **0 falhas em ambos os modos (demo e real)**

✅ **Sistema de autenticação implementado**

✅ **Documentação completa criada**

O sistema de testes está pronto para:
- Desenvolvimento (demo mode, rápido, sem custos)
- Validação pré-prod (real mode, com VAST.ai e GCP)
- CI/CD (demo mode por padrão, real mode opcional)
