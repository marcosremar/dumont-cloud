# Checklist de Testes - Fluxos de Usuário Dumont Cloud

> **Data**: ____/____/______
> **Testador**: _________________
> **Ambiente**: [ ] Local [ ] Staging [ ] Produção

---

## Pré-requisitos

- [ ] Servidor rodando (`python -m uvicorn src.main:app --port 8000`)
- [ ] PostgreSQL rodando
- [ ] Redis rodando
- [ ] Variáveis de ambiente configuradas (.env)
- [ ] Saldo disponível no Vast.ai (verificar em /api/balance)
- [ ] Credenciais GCP configuradas (para CPU Standby)

---

## Fluxo 1: Deploy Rápido de Modelo

### 1.1 Deploy de LLM (vLLM)

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Listar modelos disponíveis | `GET /api/models` | Lista de tipos de modelo | [ ] OK [ ] FALHA |
| 2 | Buscar ofertas de GPU | `GET /api/instances/offers?gpu_name=RTX 4090` | Lista de ofertas com preço | [ ] OK [ ] FALHA |
| 3 | Deploy do modelo | `POST /api/models/deploy` com body abaixo | Retorna instance_id e status | [ ] OK [ ] FALHA |
| 4 | Verificar status do deploy | `GET /api/models/{deploy_id}/status` | Status: deploying → ready | [ ] OK [ ] FALHA |
| 5 | Testar endpoint do modelo | `curl {endpoint}/v1/models` | Lista modelo carregado | [ ] OK [ ] FALHA |
| 6 | Fazer inferência | `POST {endpoint}/v1/chat/completions` | Resposta do modelo | [ ] OK [ ] FALHA |

**Body para teste 3:**
```json
{
  "model_type": "llm",
  "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
  "gpu_type": "RTX 4090",
  "max_price": 0.50
}
```

**Observações:**
```
_________________________________________________________________
_________________________________________________________________
```

---

### 1.2 Deploy de Whisper (Speech-to-Text)

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Deploy Whisper | `POST /api/models/deploy` | Retorna instance_id | [ ] OK [ ] FALHA |
| 2 | Aguardar ready | `GET /api/models/{id}/status` | Status: ready | [ ] OK [ ] FALHA |
| 3 | Testar health | `GET {endpoint}/health` | {"status": "healthy"} | [ ] OK [ ] FALHA |
| 4 | Transcrever áudio | `POST {endpoint}/transcribe` com arquivo | Texto transcrito | [ ] OK [ ] FALHA |

**Body para teste 1:**
```json
{
  "model_type": "speech",
  "model_id": "openai/whisper-large-v3",
  "gpu_type": "RTX 3090"
}
```

**Observações:**
```
_________________________________________________________________
_________________________________________________________________
```

---

### 1.3 Deploy de Embeddings

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Deploy modelo embeddings | `POST /api/models/deploy` | Retorna instance_id | [ ] OK [ ] FALHA |
| 2 | Aguardar ready | Polling status | Status: ready | [ ] OK [ ] FALHA |
| 3 | Gerar embeddings | `POST {endpoint}/embeddings` | Array de floats | [ ] OK [ ] FALHA |

**Body para teste 1:**
```json
{
  "model_type": "embeddings",
  "model_id": "BAAI/bge-large-en-v1.5",
  "gpu_type": "RTX 3080"
}
```

---

## Fluxo 2: Job GPU (Execute & Destroy)

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Criar job | `POST /api/jobs` | Retorna job_id | [ ] OK [ ] FALHA |
| 2 | Verificar status | `GET /api/jobs/{job_id}` | Status: queued → running | [ ] OK [ ] FALHA |
| 3 | Aguardar conclusão | Polling status | Status: completed | [ ] OK [ ] FALHA |
| 4 | Verificar output | `GET /api/jobs/{job_id}/output` | Logs e arquivos de saída | [ ] OK [ ] FALHA |
| 5 | Verificar GPU destruída | `GET /api/instances` | Instância não aparece | [ ] OK [ ] FALHA |
| 6 | Download de artefatos | `GET /api/jobs/{job_id}/artifacts` | Arquivos gerados | [ ] OK [ ] FALHA |

**Body para teste 1:**
```json
{
  "name": "test-job",
  "script": "nvidia-smi && python -c 'import torch; print(torch.cuda.is_available())'",
  "gpu_type": "RTX 4090",
  "disk_size": 20,
  "timeout_minutes": 10
}
```

**Tempo de execução**: _______ minutos

**Observações:**
```
_________________________________________________________________
_________________________________________________________________
```

---

## Fluxo 3: Desenvolvimento Interativo

### 3.1 Criar Instância

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Buscar ofertas | `GET /api/instances/offers` | Lista de GPUs disponíveis | [ ] OK [ ] FALHA |
| 2 | Criar instância | `POST /api/instances` | Retorna instance_id, ssh_host, ssh_port | [ ] OK [ ] FALHA |
| 3 | Aguardar SSH ready | Polling até ssh disponível | SSH conectável | [ ] OK [ ] FALHA |
| 4 | Conectar via SSH | `ssh -p {port} root@{host}` | Login bem-sucedido | [ ] OK [ ] FALHA |
| 5 | Verificar GPU | `nvidia-smi` no SSH | GPU listada corretamente | [ ] OK [ ] FALHA |

**Body para teste 2:**
```json
{
  "gpu_type": "RTX 3090",
  "image": "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
  "disk_size": 30
}
```

### 3.2 Serverless (Auto-Pause/Resume)

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Deixar GPU ociosa | Não usar por 3 minutos | - | [ ] OK [ ] FALHA |
| 2 | Verificar pause automático | `GET /api/instances/{id}` | Status: paused | [ ] OK [ ] FALHA |
| 3 | Fazer request à GPU | Qualquer comando SSH ou API | GPU acorda automaticamente | [ ] OK [ ] FALHA |
| 4 | Verificar resume | `GET /api/instances/{id}` | Status: running | [ ] OK [ ] FALHA |
| 5 | Medir tempo de resume | Cronometrar | Tempo: _______ segundos | [ ] OK [ ] FALHA |

### 3.3 Auto-Hibernation

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Deixar GPU pausada | Não usar por 30 minutos | - | [ ] OK [ ] FALHA |
| 2 | Verificar snapshot criado | `GET /api/snapshots` | Snapshot da instância | [ ] OK [ ] FALHA |
| 3 | Verificar instância destruída | `GET /api/instances` | Instância não listada | [ ] OK [ ] FALHA |
| 4 | Restaurar snapshot | `POST /api/snapshots/{id}/restore` | Nova instância criada | [ ] OK [ ] FALHA |
| 5 | Verificar dados restaurados | SSH e verificar /workspace | Dados intactos | [ ] OK [ ] FALHA |

**Observações:**
```
_________________________________________________________________
_________________________________________________________________
```

---

## Fluxo 4: API de Inferência Serverless

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Deploy modelo serverless | `POST /api/serverless/deploy` | Endpoint da API | [ ] OK [ ] FALHA |
| 2 | Primeira request (cold) | `POST {endpoint}/inference` | Resposta + tempo cold start | [ ] OK [ ] FALHA |
| 3 | Segunda request (warm) | `POST {endpoint}/inference` | Resposta rápida | [ ] OK [ ] FALHA |
| 4 | Aguardar idle (3 min) | Esperar sem requests | - | [ ] OK [ ] FALHA |
| 5 | Verificar GPU pausada | `GET /api/serverless/{id}/status` | Status: paused | [ ] OK [ ] FALHA |
| 6 | Request após pause | `POST {endpoint}/inference` | GPU acorda, responde | [ ] OK [ ] FALHA |
| 7 | Medir cold start | Cronometrar teste 6 | Tempo: _______ segundos | [ ] OK [ ] FALHA |

**Tempos medidos:**
- Cold start inicial: _______ segundos
- Request warm: _______ ms
- Cold start após pause: _______ segundos

---

## Fluxo 5: Alta Disponibilidade (CPU Standby + Failover)

### 5.1 Configurar CPU Standby

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Verificar credenciais GCP | `GET /api/standby/status` | configured: true | [ ] OK [ ] FALHA |
| 2 | Configurar auto-standby | `POST /api/standby/configure` | Success | [ ] OK [ ] FALHA |
| 3 | Criar GPU com standby | `POST /api/instances` | GPU + CPU criados | [ ] OK [ ] FALHA |
| 4 | Verificar CPU standby | `GET /api/standby/associations` | Associação GPU→CPU | [ ] OK [ ] FALHA |
| 5 | Verificar sync ativo | `GET /api/standby/associations/{gpu_id}` | sync_enabled: true | [ ] OK [ ] FALHA |

**Body para teste 2:**
```json
{
  "enabled": true,
  "gcp_zone": "europe-west1-b",
  "gcp_machine_type": "e2-medium",
  "gcp_spot": true,
  "auto_failover": true
}
```

### 5.2 Testar Failover Simulado

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Criar mock association | `POST /api/standby/test/create-mock-association` | Association criada | [ ] OK [ ] FALHA |
| 2 | Simular failover | `POST /api/standby/failover/simulate/{gpu_id}` | Failover iniciado | [ ] OK [ ] FALHA |
| 3 | Monitorar fases | `GET /api/standby/failover/status/{id}` | Fases progressivas | [ ] OK [ ] FALHA |
| 4 | Verificar conclusão | Polling status | Phase: complete | [ ] OK [ ] FALHA |
| 5 | Verificar relatório | `GET /api/standby/failover/report` | Métricas do failover | [ ] OK [ ] FALHA |

### 5.3 Testar Failover Real (CUIDADO: CUSTA $$$)

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Criar GPU real | `POST /api/instances` | GPU running | [ ] OK [ ] FALHA |
| 2 | Provisionar standby | `POST /api/standby/provision/{gpu_id}` | CPU standby criado | [ ] OK [ ] FALHA |
| 3 | Criar dados de teste | SSH: `echo "test" > /workspace/test.txt` | Arquivo criado | [ ] OK [ ] FALHA |
| 4 | Executar failover real | `POST /api/standby/failover/fast/{gpu_id}` | Failover completo | [ ] OK [ ] FALHA |
| 5 | Verificar dados restaurados | SSH na nova GPU | Arquivo test.txt presente | [ ] OK [ ] FALHA |
| 6 | Verificar tempo total | Response do failover | Tempo: _______ segundos | [ ] OK [ ] FALHA |

**Observações:**
```
_________________________________________________________________
_________________________________________________________________
```

---

## Fluxo 6: Warm Pool

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Verificar status pool | `GET /api/warmpool/status` | Status do pool | [ ] OK [ ] FALHA |
| 2 | Configurar pool | `POST /api/warmpool/configure` | Pool configurado | [ ] OK [ ] FALHA |
| 3 | Adicionar GPU ao pool | `POST /api/warmpool/add` | GPU adicionada | [ ] OK [ ] FALHA |
| 4 | Verificar GPU ready | `GET /api/warmpool/status` | GPU no pool | [ ] OK [ ] FALHA |
| 5 | Adquirir do pool | `POST /api/warmpool/acquire` | GPU atribuída rapidamente | [ ] OK [ ] FALHA |
| 6 | Medir tempo aquisição | Cronometrar teste 5 | Tempo: _______ segundos | [ ] OK [ ] FALHA |
| 7 | Liberar para pool | `POST /api/warmpool/release/{id}` | GPU volta ao pool | [ ] OK [ ] FALHA |

**Body para teste 2:**
```json
{
  "gpu_types": ["RTX 4090", "RTX 3090"],
  "min_ready": 1,
  "max_ready": 2
}
```

---

## Fluxo 7: Monitoramento e Métricas

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Health check | `GET /health` | {"status": "healthy"} | [ ] OK [ ] FALHA |
| 2 | Estatísticas hibernação | `GET /api/hibernation/stats` | Contadores por status | [ ] OK [ ] FALHA |
| 3 | Dashboard economia | `GET /api/savings` | Economia calculada | [ ] OK [ ] FALHA |
| 4 | Métricas de mercado | `GET /api/metrics/market` | Preços atuais | [ ] OK [ ] FALHA |
| 5 | Histórico de máquinas | `GET /api/machines/history` | Histórico de uso | [ ] OK [ ] FALHA |
| 6 | Instâncias do agente | `GET /api/agent/instances` | Lista de heartbeats | [ ] OK [ ] FALHA |

---

## Fluxo 8: Autenticação e Configurações

| # | Teste | Comando/Ação | Esperado | Status |
|---|-------|--------------|----------|--------|
| 1 | Registrar usuário | `POST /api/auth/register` | Token JWT | [ ] OK [ ] FALHA |
| 2 | Login | `POST /api/auth/login` | Token JWT | [ ] OK [ ] FALHA |
| 3 | Obter settings | `GET /api/settings` | Configurações do usuário | [ ] OK [ ] FALHA |
| 4 | Atualizar API key | `PUT /api/settings` | Success | [ ] OK [ ] FALHA |
| 5 | Verificar saldo | `GET /api/balance` | Saldo Vast.ai | [ ] OK [ ] FALHA |
| 6 | Testar AI Advisor | `POST /api/advisor/recommend` | Recomendação de GPU | [ ] OK [ ] FALHA |

**Body para teste 1:**
```json
{
  "email": "teste@example.com",
  "password": "senha123"
}
```

**Body para teste 4:**
```json
{
  "vast_api_key": "sua_api_key_aqui"
}
```

---

## Resumo Final

### Contagem de Testes

| Fluxo | Total | OK | Falha | % |
|-------|-------|-----|-------|---|
| 1. Deploy Modelo | 14 | | | |
| 2. Job GPU | 6 | | | |
| 3. Dev Interativo | 14 | | | |
| 4. API Serverless | 7 | | | |
| 5. Alta Disponibilidade | 16 | | | |
| 6. Warm Pool | 7 | | | |
| 7. Monitoramento | 6 | | | |
| 8. Auth/Settings | 6 | | | |
| **TOTAL** | **76** | | | |

### Problemas Encontrados

| # | Fluxo | Teste | Descrição do Problema | Severidade |
|---|-------|-------|----------------------|------------|
| 1 | | | | [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo |
| 2 | | | | [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo |
| 3 | | | | [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo |
| 4 | | | | [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo |
| 5 | | | | [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo |

### Tempos Medidos

| Operação | Tempo |
|----------|-------|
| Cold start LLM | _______ seg |
| Cold start Whisper | _______ seg |
| Resume de GPU pausada | _______ seg |
| Failover completo | _______ seg |
| Aquisição do warm pool | _______ seg |
| Restauração de snapshot | _______ seg |

### Assinaturas

**Testador**: _________________________ Data: ____/____/______

**Revisor**: _________________________ Data: ____/____/______

---

## Comandos Úteis para Testes

```bash
# Autenticação (obter token)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}' | jq -r '.token')

# Header de autenticação
AUTH="Authorization: Bearer $TOKEN"

# Listar instâncias
curl -s -H "$AUTH" http://localhost:8000/api/instances | jq

# Criar instância
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  http://localhost:8000/api/instances \
  -d '{"gpu_type":"RTX 3090","disk_size":20}' | jq

# Verificar status
curl -s -H "$AUTH" http://localhost:8000/api/instances/{ID} | jq

# Health check
curl -s http://localhost:8000/health | jq
```
