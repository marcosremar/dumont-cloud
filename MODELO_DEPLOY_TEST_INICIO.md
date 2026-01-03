# Teste Real de Deploy de 10 LLMs - Dumont Cloud + VAST.ai

## Informações do Teste

- **Data/Hora Início**: 2026-01-03 02:10:00 UTC
- **Objetivo**: Deploy REAL de 10 modelos LLM leves em GPUs VAST.ai
- **Script**: `/Users/marcos/CascadeProjects/dumontcloud/scripts/test_10_models_real.py`
- **API Backend**: http://localhost:8000
- **Usuário**: test@test.com

## Modelos a Testar (10 total)

### LLMs (4 modelos - vLLM runtime)
1. **Llama 3.2 1B** - `meta-llama/Llama-3.2-1B-Instruct`
2. **Qwen 0.5B** - `Qwen/Qwen2.5-0.5B-Instruct`
3. **Phi-2** - `microsoft/phi-2`
4. **TinyLlama 1.1B** - `TinyLlama/TinyLlama-1.1B-Chat-v1.0`

### Speech (2 modelos - faster-whisper runtime)
5. **Whisper Tiny** - `openai/whisper-tiny`
6. **Whisper Base** - `openai/whisper-base`

### Image (2 modelos - diffusers runtime)
7. **SD Turbo** - `stabilityai/sd-turbo`
8. **SSD-1B** - `segmind/SSD-1B`

### Embeddings (2 modelos - sentence-transformers runtime)
9. **MiniLM-L6** - `sentence-transformers/all-MiniLM-L6-v2`
10. **BGE Small** - `BAAI/bge-small-en-v1.5`

## Configuração

- **GPU Target**: RTX 3060 (12GB VRAM)
- **Max Price**: $0.10 - $0.20/hora
- **Timeout por Modelo**: 20 minutos
- **Total Estimado**: ~3-4 horas

## Processo de Teste

Para cada modelo:
1. Criar deployment via API `/api/v1/models/deploy`
2. Aguardar status "running" (polling a cada 10s)
3. Registrar métricas (tempo, custo, instance ID)
4. Deletar deployment (economizar créditos)
5. Aguardar 5s antes do próximo

## Métricas Coletadas

- Deployment ID
- Instance ID (VAST.ai)
- Tempo para criar deployment
- Tempo para ficar running
- Status final
- Preço por hora
- Custo estimado
- Erros (se houver)

## Rate Limiting

- VAST.ai implementa rate limiting
- Backoff exponencial em caso de 429
- Delay de 5s entre cada deploy

## IMPORTANTE

- Este teste USA CRÉDITOS REAIS da VAST.ai
- Cada deployment é deletado após teste
- Custo estimado: $2-5 total (dependendo dos tempos)
- Todos os deployments são limpos automaticamente

## Resultado

Ver arquivo: `/Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_REAL_TEST.json`
