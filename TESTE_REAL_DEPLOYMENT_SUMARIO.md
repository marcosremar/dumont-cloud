# Teste REAL de Deploy de 10 LLMs - Dumont Cloud + VAST.ai

## Status: EM EXECUCAO

Data/Hora Início: 2026-01-03 02:12:00 UTC

---

## Objetivo

Executar testes REAIS de deploy de 10 modelos LLM leves no Dumont Cloud usando GPUs da VAST.ai, validando:
- API de deployment `/api/v1/models/deploy`
- Provisionamento de GPUs via VAST.ai
- Instalação de diferentes runtimes (vLLM, faster-whisper, diffusers, sentence-transformers)
- Tempo de deploy end-to-end
- Custos reais de operação
- Cleanup automático de recursos

---

## Modelos Testados (10 total)

### LLMs - vLLM Runtime (4 modelos)
1. **Llama 3.2 1B** - `meta-llama/Llama-3.2-1B-Instruct` - 1B params
2. **Qwen 0.5B** - `Qwen/Qwen2.5-0.5B-Instruct` - 500M params
3. **Phi-2** - `microsoft/phi-2` - 2.7B params
4. **TinyLlama 1.1B** - `TinyLlama/TinyLlama-1.1B-Chat-v1.0` - 1.1B params

### Speech - faster-whisper Runtime (2 modelos)
5. **Whisper Tiny** - `openai/whisper-tiny` - 39M params
6. **Whisper Base** - `openai/whisper-base` - 74M params

### Image - diffusers Runtime (2 modelos)
7. **SD Turbo** - `stabilityai/sd-turbo` - 1.1B params
8. **SSD-1B** - `segmind/SSD-1B` - 1.1B params (distilled)

### Embeddings - sentence-transformers Runtime (2 modelos)
9. **MiniLM-L6** - `sentence-transformers/all-MiniLM-L6-v2` - 22M params
10. **BGE Small** - `BAAI/bge-small-en-v1.5` - 33M params

---

## Infraestrutura

### Backend API
- **URL**: http://localhost:8000
- **Versão**: Dumont Cloud v3.0.0
- **Framework**: FastAPI + SQLAlchemy
- **Database**: PostgreSQL (OrbStack)

### Provider GPU
- **Provider**: VAST.ai
- **API Key**: Configurado via `.env`
- **GPU Target**: RTX 3060 (12GB VRAM)
- **Max Price**: $0.10 - $0.20/hora
- **Região**: Qualquer disponível

### Usuário de Teste
- **Email**: test@test.com
- **Password**: test123
- **Trial GPU**: 7200 segundos (2h)
- **Criado**: 2026-01-03 via script `create_test_user.py`

---

## Configuração do Teste

### Timeouts
- **Deployment Create**: 60s
- **Wait for Running**: 1200s (20 min)
- **Total per Model**: ~20 min
- **Total Estimated**: ~3-4 horas para 10 modelos

### Rate Limiting
- **VAST.ai**: Implementa rate limiting (429)
- **Estratégia**: Backoff exponencial (2s inicial, 1.5x multiplicador)
- **Max Retries**: 5 tentativas
- **Delay entre Modelos**: 5 segundos

### Cleanup
- **Automático**: Sim, após cada teste
- **On Error**: Sim, tentativa de cleanup mesmo em falha
- **Verificação**: Status 204 no DELETE

---

## Processo de Teste

Para cada modelo:

1. **Deploy** (60s timeout)
   - POST `/api/v1/models/deploy`
   - Payload: model_id, model_type, gpu_type, max_price
   - Retorna: deployment_id

2. **Wait for Running** (20 min timeout)
   - GET `/api/v1/models/{deployment_id}` a cada 10s
   - Monitora: status, progress, status_message
   - Finaliza quando: status == "running" | "error" | "failed"

3. **Cleanup** (sempre executado)
   - DELETE `/api/v1/models/{deployment_id}`
   - Confirma: status code 204

4. **Delay** (5s entre modelos)
   - Evita rate limiting
   - Permite estabilização da VAST.ai API

---

## Métricas Coletadas

Para cada deployment:

### Tempos
- `time_to_deploy`: Tempo para criar deployment (API call)
- `time_to_running`: Tempo total até status "running"
- Incluindo:
  - Provisioning GPU na VAST.ai
  - SSH setup
  - Runtime installation (vLLM, etc)
  - Model download do HuggingFace
  - Model loading em GPU
  - Health check

### Custos
- `price_per_hour`: Preço da GPU por hora
- `estimated_cost`: (time_to_running / 3600) * price_per_hour

### IDs e Status
- `deployment_id`: UUID do deployment
- `instance_id`: ID da instância VAST.ai
- `final_status`: running | error | failed
- `error`: Mensagem de erro (se houver)

---

## Arquivos Gerados

### Log de Execução
- **Path**: `/tmp/model_deploy_10_test.log`
- **Formato**: Texto plano com timestamps
- **Conteúdo**: Output completo do teste
- **Atualização**: Tempo real

### Relatório JSON
- **Path**: `/Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_REAL_TEST.json`
- **Formato**: JSON estruturado
- **Conteúdo**:
  ```json
  {
    "timestamp": "2026-01-03T02:12:00Z",
    "total_models": 10,
    "successful": 0,
    "failed": 0,
    "results": [
      {
        "model_name": "Llama 3.2 1B",
        "model_id": "meta-llama/Llama-3.2-1B-Instruct",
        "deployment_id": "a76cd4f2-0c3b-44cd-81e2-af8e0d2c8142",
        "success": true,
        "time_to_deploy": 0.05,
        "time_to_running": 180.5,
        "final_status": "running",
        "error": null,
        "price_per_hour": 0.12,
        "instance_id": "29087654"
      },
      ...
    ]
  }
  ```

---

## Scripts Criados

1. **test_10_models_real.py**
   - **Path**: `/Users/marcos/CascadeProjects/dumontcloud/scripts/test_10_models_real.py`
   - **Função**: Executa teste completo dos 10 modelos
   - **Features**:
     - Login automático
     - Deploy sequencial
     - Rate limiting handling
     - Cleanup automático
     - Relatório JSON
     - Progress em tempo real

2. **test_3_models_quick.py**
   - **Path**: `/Users/marcos/CascadeProjects/dumontcloud/scripts/test_3_models_quick.py`
   - **Função**: Teste rápido com 3 modelos (Qwen, TinyLlama, MiniLM)
   - **Timeout**: 10 min por modelo
   - **Uso**: Validação rápida

3. **create_test_user.py**
   - **Path**: `/Users/marcos/CascadeProjects/dumontcloud/scripts/create_test_user.py`
   - **Função**: Cria usuário test@test.com no banco
   - **Executado**: Uma vez no início

4. **monitor_test_progress.sh**
   - **Path**: `/Users/marcos/CascadeProjects/dumontcloud/scripts/monitor_test_progress.sh`
   - **Função**: Monitor em tempo real do teste
   - **Uso**: `./scripts/monitor_test_progress.sh`

---

## Comandos para Acompanhar

### Ver log em tempo real
```bash
tail -f /tmp/model_deploy_10_test.log
```

### Ver progresso resumido
```bash
./scripts/monitor_test_progress.sh
```

### Verificar processo rodando
```bash
ps aux | grep test_10_models_real
```

### Ver últimas 50 linhas
```bash
tail -50 /tmp/model_deploy_10_test.log
```

### Contar sucessos/erros
```bash
grep -c "SUCCESS:" /tmp/model_deploy_10_test.log
grep -c "ERROR:" /tmp/model_deploy_10_test.log
```

---

## Pontos de Atenção

### VAST.ai Rate Limiting
- A API retorna 429 quando muitas requests
- Script implementa backoff exponencial automático
- Delay de 5s entre modelos ajuda a evitar

### Timeouts
- 20 min por modelo pode não ser suficiente para modelos grandes
- Download de 7B+ pode demorar mais
- Modelos escolhidos são leves (< 3B) para minimizar tempo

### Custos
- Cada modelo roda por ~3-10 minutos
- Custo estimado: $0.20 - $0.50 por modelo
- Total estimado: $2 - $5 para os 10 modelos
- Todos são deletados após teste

### Cleanup
- CRÍTICO: Sempre deletar deployments
- Script tenta cleanup mesmo em erro
- Verificar manualmente se houver falhas:
  ```bash
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/api/v1/models/
  ```

---

## Próximos Passos

Após o teste completar:

1. **Analisar Resultados**
   - Ler `/Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_REAL_TEST.json`
   - Verificar taxa de sucesso
   - Analisar tempos médios
   - Calcular custos totais

2. **Validar Limpeza**
   - Verificar se todos deployments foram deletados
   - Checar instâncias VAST.ai (não devem ter vazamentos)

3. **Documentar Aprendizados**
   - Tempos típicos por tipo de modelo
   - Problemas encontrados
   - Rate limiting observado
   - Otimizações possíveis

4. **Melhorias**
   - Implementar deploy paralelo (com cuidado com rate limit)
   - Cache de modelos em volume persistente
   - Reutilizar instâncias para modelos do mesmo tipo

---

## Observações Finais

- Este é um teste de INTEGRAÇÃO REAL, não um mock
- USA CRÉDITOS REAIS da VAST.ai
- Todos os componentes são testados end-to-end:
  - API Backend (FastAPI)
  - Database (PostgreSQL)
  - VAST.ai provisioning
  - SSH connection
  - Runtime installation
  - Model download
  - GPU inference
- Resultados refletem performance REAL do sistema

---

**Status Atual**: Teste em execução
**PID**: 11222
**Log**: `/tmp/model_deploy_10_test.log`
**Início**: 2026-01-03 02:12:00 UTC
**Estimativa de Conclusão**: 2026-01-03 05:00:00 UTC (~3h)
