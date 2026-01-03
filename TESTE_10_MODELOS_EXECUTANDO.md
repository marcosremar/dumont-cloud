# Teste REAL de 10 LLMs - EM EXECUCAO

## Status Atual

**Teste REAL de deployment de 10 modelos LLM está RODANDO**

- **Início**: 2026-01-03 02:12:00 UTC
- **PID**: 11222
- **Log**: `/tmp/model_deploy_10_test.log`
- **Relatório Final**: `/Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_REAL_TEST.json`

---

## Progresso Observado (primeiros 2 minutos)

### Modelo 1/10: Llama 3.2 1B
- **Status**: downloading (60%)
- **Deployment ID**: a76cd4f2-0c3b-44cd-81e2-af8e0d2c8142
- **Tempo decorrido**: ~2 minutos
- **Etapa atual**: "Deploying model to instance..."

**Timeline observada**:
- 0-25s: Provisioning (criando 5 máquinas VAST.ai, aguardando SSH)
- 30s+: Downloading (baixando modelo do HuggingFace)
- Status atual: ainda baixando

---

## Modelos na Fila (9 restantes)

2. Qwen 0.5B - Qwen/Qwen2.5-0.5B-Instruct
3. Phi-2 - microsoft/phi-2
4. TinyLlama 1.1B - TinyLlama/TinyLlama-1.1B-Chat-v1.0
5. Whisper Tiny - openai/whisper-tiny
6. Whisper Base - openai/whisper-base
7. SD Turbo - stabilityai/sd-turbo
8. SSD-1B - segmind/SSD-1B
9. MiniLM-L6 - sentence-transformers/all-MiniLM-L6-v2
10. BGE Small - BAAI/bge-small-en-v1.5

---

## Como Acompanhar

### Ver log em tempo real
```bash
tail -f /tmp/model_deploy_10_test.log
```

### Ver últimas 50 linhas
```bash
tail -50 /tmp/model_deploy_10_test.log
```

### Verificar se processo está rodando
```bash
ps aux | grep 11222
# ou
ps aux | grep test_10_models_real
```

### Contar sucessos até agora
```bash
grep -c "SUCCESS:" /tmp/model_deploy_10_test.log
```

### Contar erros
```bash
grep -c "ERROR:" /tmp/model_deploy_10_test.log
```

### Ver apenas status de deployments
```bash
grep -E "(Creating deployment|STATUS: RUNNING|ERROR:)" /tmp/model_deploy_10_test.log
```

---

## Tempo Estimado

Baseado no primeiro modelo:
- **Por modelo**: 5-15 minutos (download + deploy + running)
- **Total para 10**: ~2-4 horas
- **Estimativa de conclusão**: 2026-01-03 04:00-06:00 UTC

---

## O Que Está Acontecendo

### Para cada modelo, o sistema:

1. **Cria Deployment** (~0.1s)
   - POST /api/v1/models/deploy
   - Backend cria registro no banco
   - Retorna deployment_id

2. **Provisiona GPU** (~20-60s)
   - Backend busca GPUs disponíveis na VAST.ai
   - Cria instância (5 tentativas paralelas)
   - Aguarda SSH estar acessível

3. **Instala Runtime** (~30-120s)
   - Conecta via SSH na instância
   - Instala vLLM/faster-whisper/diffusers/sentence-transformers
   - Configura dependências

4. **Baixa Modelo** (~60-600s) <- ETAPA ATUAL
   - Download do HuggingFace
   - Modelos pequenos: 0.5-3GB
   - Velocidade depende da GPU/região

5. **Carrega em GPU** (~30-60s)
   - Load do modelo na VRAM
   - Inicializa servidor
   - Health check

6. **Status: Running** (sucesso!)
   - Registra métricas
   - Deleta deployment
   - Vai para próximo modelo

---

## Métricas Sendo Coletadas

Para cada modelo:
- Deployment ID
- Instance ID (VAST.ai)
- Tempo para criar
- Tempo até running
- Status final
- Preço por hora da GPU
- Custo estimado
- Erros (se houver)

---

## Arquivos e Scripts

### Script Principal
- `/Users/marcos/CascadeProjects/dumontcloud/scripts/test_10_models_real.py`
- Roda em background com nohup
- Output em `/tmp/model_deploy_10_test.log`

### Relatório JSON (gerado ao final)
- `/Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_REAL_TEST.json`
- Formato estruturado com todas as métricas
- Gerado automaticamente ao finalizar

### Documentação
- `/Users/marcos/CascadeProjects/dumontcloud/TESTE_REAL_DEPLOYMENT_SUMARIO.md`
- Documentação completa do teste

---

## IMPORTANTE: Custos

Este teste USA CRÉDITOS REAIS da VAST.ai

- **Por modelo**: ~$0.20 - $0.50 (5-15 min em RTX 3060)
- **Total estimado**: $2 - $5 para os 10 modelos
- **Cleanup automático**: Sim, cada modelo é deletado após teste
- **Vazamento**: Improvável (script tenta cleanup mesmo em erro)

### Verificar vazamentos (opcional)
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}' | jq -r '.token')

# Listar deployments ativos
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/models/ | jq
```

---

## Próximos Passos

### Quando o teste completar:

1. **Verificar relatório**
   ```bash
   cat /Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_REAL_TEST.json | jq
   ```

2. **Analisar sucessos/falhas**
   ```bash
   grep "SUCCESS:" /tmp/model_deploy_10_test.log | wc -l
   grep "ERROR:" /tmp/model_deploy_10_test.log | wc -l
   ```

3. **Ver tempos médios**
   ```bash
   cat /Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_REAL_TEST.json | \
     jq '.results[] | select(.success==true) | .time_to_running' | \
     awk '{sum+=$1; count++} END {print "Média:", sum/count, "segundos"}'
   ```

4. **Calcular custo total**
   ```bash
   cat /Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_REAL_TEST.json | \
     jq '[.results[] | select(.price_per_hour > 0) |
          (.time_to_running / 3600 * .price_per_hour)] | add'
   ```

---

## Troubleshooting

### Se o teste travar
```bash
# Verificar processo
ps aux | grep 11222

# Ver log
tail -100 /tmp/model_deploy_10_test.log

# Matar processo (se necessário)
kill 11222

# Limpar deployments pendentes
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}' | jq -r '.token')

curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/models/ | jq -r '.models[].id' | \
  while read id; do
    curl -X DELETE -H "Authorization: Bearer $TOKEN" \
      "http://localhost:8000/api/v1/models/$id"
    echo "Deleted: $id"
  done
```

### Se houver rate limiting (429)
O script já lida com isso automaticamente via backoff exponencial.
Se persistir, aumentar delay entre modelos no script.

---

## Contato/Suporte

Este é um teste automatizado. Resultados em:
- Log: `/tmp/model_deploy_10_test.log`
- JSON: `/Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_REAL_TEST.json`

---

**Última atualização**: 2026-01-03 02:14:00 UTC
**Status**: Rodando - Modelo 1/10 baixando
