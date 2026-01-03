# AI Wizard

## O que e o AI Wizard?

O AI Wizard e um assistente de IA que recomenda a melhor GPU para seu caso de uso. Descreva seu projeto em linguagem natural e receba recomendacoes otimizadas.

---

## Como Usar

### 1. Acesse o Wizard

- Clique em **"AI Wizard"** no menu
- Ou use o atalho `W`

### 2. Descreva seu Projeto

Exemplos de prompts:

> "Quero treinar um modelo de linguagem com 7B parametros usando LoRA"

> "Preciso rodar inferencia de Stable Diffusion para gerar 1000 imagens por dia"

> "Vou fazer fine-tuning do Whisper para transcricao em portugues"

### 3. Receba Recomendacao

O wizard analisa:
- Requisitos de VRAM
- Custo estimado
- Tempo de execucao
- Disponibilidade

### 4. Lance com 1 Clique

Aceite a recomendacao e a maquina e criada automaticamente.

---

## Exemplos de Recomendacoes

### Treinamento LLM 7B

```
Prompt: "Treinar LLM 7B com LoRA"

Recomendacao:
- GPU: RTX 4090 (24GB VRAM)
- Custo: ~$0.40/hora
- Estimativa: 8-12 horas
- Total: ~$4-5

Alternativa mais barata:
- GPU: RTX 3090 (24GB VRAM)
- Custo: ~$0.30/hora
- Estimativa: 12-16 horas
- Total: ~$4-5
```

### Inferencia Stable Diffusion

```
Prompt: "Gerar 1000 imagens SD XL por dia"

Recomendacao:
- GPU: RTX 4090
- Tempo/imagem: ~3s
- Total/dia: ~50 min
- Custo/dia: ~$0.35

Opcao Serverless:
- Auto-pause quando idle
- Custo estimado: ~$0.20/dia
```

### Fine-tuning Whisper

```
Prompt: "Fine-tune Whisper para PT-BR, 100h de audio"

Recomendacao:
- GPU: A100 40GB
- Tempo estimado: 4-6 horas
- Custo: ~$5-7

Configuracao sugerida:
- Batch size: 16
- Learning rate: 1e-5
- Epochs: 3
```

---

## Fatores Considerados

### Requisitos Tecnicos
- VRAM necessaria
- Compute capability
- Bandwidth de memoria

### Custo-Beneficio
- Preco atual da GPU
- Tempo estimado de execucao
- Custo total do projeto

### Disponibilidade
- GPUs disponiveis agora
- Probabilidade de interrupcao
- Regioes alternativas

### Otimizacoes
- Batch size otimo
- Precisao (FP16, BF16, FP32)
- Gradient checkpointing

---

## API

### Consultar Recomendacao

```bash
curl -X POST /api/v1/ai-wizard/recommend \
  -d '{
    "prompt": "Treinar modelo de visao com 1M de imagens",
    "budget_max": 50,
    "priority": "cost"  # ou "speed"
  }'
```

### Resposta

```json
{
  "recommendation": {
    "gpu_type": "RTX_4090",
    "quantity": 1,
    "estimated_hours": 12,
    "estimated_cost": 4.80,
    "confidence": 0.92
  },
  "alternatives": [...],
  "reasoning": "RTX 4090 oferece melhor custo-beneficio para treinamento de visao..."
}
```

---

## Melhores Praticas

1. **Seja especifico** - Mencione tamanho do modelo, dataset, etc
2. **Informe orcamento** - Ajuda a filtrar opcoes
3. **Compare alternativas** - O wizard mostra varias opcoes
4. **Use estimativas** - Sao aproximacoes, monitore o uso real
