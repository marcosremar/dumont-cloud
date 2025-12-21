# Spot Market Analysis API

Endpoints para análise do mercado spot de GPUs, incluindo disponibilidade, eficiência para LLM e custos de treinamento.

## Visão Geral

Estes endpoints fornecem dados em tempo real sobre o mercado de GPUs:
- Disponibilidade instantânea por região
- Melhores GPUs para inferência LLM ($/token)
- Custos estimados de treinamento

---

## Endpoints

### GET /metrics/availability

Retorna disponibilidade instantânea de GPUs Spot com distribuição por região.

**Parâmetros:**
| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| gpu_name | string? | null | Filtrar por GPU específica |
| max_price | float? | null | Preço máximo por hora |

**Response:**
```json
{
  "timestamp": "2024-12-20T15:30:00Z",
  "gpus": [
    {
      "gpu_name": "RTX_4090",
      "available_count": 45,
      "avg_price": 0.42,
      "min_price": 0.35,
      "max_price": 0.55,
      "regions": {
        "US": 20,
        "DE": 15,
        "PL": 10
      }
    },
    {
      "gpu_name": "A100",
      "available_count": 12,
      "avg_price": 1.20,
      "min_price": 0.95,
      "max_price": 1.50,
      "regions": {
        "US": 8,
        "DE": 4
      }
    }
  ],
  "total_available": 57
}
```

**Exemplo curl:**
```bash
curl "https://api.dumontcloud.com/api/v1/metrics/availability?gpu_name=RTX_4090" \
  -H "Authorization: Bearer $API_KEY"
```

---

### GET /metrics/llm-gpus

Retorna ranking das melhores GPUs para LLM ordenadas por $/token (eficiência de inferência).

**Response:**
```json
{
  "timestamp": "2024-12-20T15:30:00Z",
  "ranking": [
    {
      "rank": 1,
      "gpu_name": "RTX_4090",
      "vram_gb": 24,
      "avg_price_hour": 0.42,
      "tokens_per_second": 85,
      "cost_per_million_tokens": 1.37,
      "recommended_models": ["Llama-3-8B", "Mistral-7B", "Qwen-7B"],
      "max_context_length": 32768,
      "available_count": 45
    },
    {
      "rank": 2,
      "gpu_name": "A100_40GB",
      "vram_gb": 40,
      "avg_price_hour": 1.20,
      "tokens_per_second": 120,
      "cost_per_million_tokens": 2.78,
      "recommended_models": ["Llama-3-70B", "Mixtral-8x7B"],
      "max_context_length": 65536,
      "available_count": 12
    },
    {
      "rank": 3,
      "gpu_name": "H100",
      "vram_gb": 80,
      "avg_price_hour": 2.50,
      "tokens_per_second": 250,
      "cost_per_million_tokens": 2.78,
      "recommended_models": ["Llama-3-70B", "GPT-4 equivalent"],
      "max_context_length": 131072,
      "available_count": 5
    }
  ],
  "notes": "Tokens/second based on Llama-3-8B Q4 quantization"
}
```

**Exemplo curl:**
```bash
curl https://api.dumontcloud.com/api/v1/metrics/llm-gpus \
  -H "Authorization: Bearer $API_KEY"
```

---

### GET /metrics/training-cost

Retorna custo estimado por hora de treinamento, eficiência e batch size recomendado.

**Parâmetros:**
| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| model_size | string | 7B | Tamanho do modelo (7B, 13B, 70B) |
| precision | string | fp16 | Precisão (fp32, fp16, bf16, int8) |

**Response:**
```json
{
  "timestamp": "2024-12-20T15:30:00Z",
  "model_size": "7B",
  "precision": "fp16",
  "gpus": [
    {
      "gpu_name": "RTX_4090",
      "vram_gb": 24,
      "avg_price_hour": 0.42,
      "can_train": true,
      "recommended_batch_size": 4,
      "estimated_tokens_per_second": 1500,
      "estimated_cost_per_epoch": 2.50,
      "notes": "Uses gradient checkpointing"
    },
    {
      "gpu_name": "A100_40GB",
      "vram_gb": 40,
      "avg_price_hour": 1.20,
      "can_train": true,
      "recommended_batch_size": 16,
      "estimated_tokens_per_second": 4000,
      "estimated_cost_per_epoch": 1.80,
      "notes": "Full fine-tuning supported"
    },
    {
      "gpu_name": "RTX_3090",
      "vram_gb": 24,
      "avg_price_hour": 0.30,
      "can_train": true,
      "recommended_batch_size": 2,
      "estimated_tokens_per_second": 800,
      "estimated_cost_per_epoch": 3.20,
      "notes": "LoRA recommended for efficiency"
    }
  ],
  "recommendations": {
    "best_value": "A100_40GB",
    "best_budget": "RTX_3090",
    "fastest": "H100"
  }
}
```

**Exemplo curl:**
```bash
curl "https://api.dumontcloud.com/api/v1/metrics/training-cost?model_size=7B&precision=fp16" \
  -H "Authorization: Bearer $API_KEY"
```

---

## Uso Recomendado

### Para Inferência LLM
1. Use `/metrics/llm-gpus` para encontrar a GPU mais eficiente
2. Priorize $/million tokens para workloads de produção
3. Considere VRAM para modelos maiores

### Para Treinamento/Fine-tuning
1. Use `/metrics/training-cost` com tamanho do modelo
2. Compare custo por época vs velocidade
3. Considere GPUs com mais VRAM para batches maiores

### Para Disponibilidade
1. Use `/metrics/availability` para monitorar mercado
2. Configure alertas quando GPUs preferidas ficarem disponíveis
3. Distribua workloads por região para resiliência

---

## Notas Técnicas

### Cálculo de $/Token
```
cost_per_million_tokens = (price_per_hour / tokens_per_second) * 1000000 / 3600
```

### Tokens por Segundo (Benchmarks)
Baseado em Llama-3-8B com quantização Q4:
- RTX 4090: ~85 tok/s
- A100 40GB: ~120 tok/s
- H100: ~250 tok/s

### VRAM Necessário
| Modelo | FP16 | INT8 | INT4 |
|--------|------|------|------|
| 7B | 14GB | 7GB | 4GB |
| 13B | 26GB | 13GB | 7GB |
| 70B | 140GB | 70GB | 35GB |
