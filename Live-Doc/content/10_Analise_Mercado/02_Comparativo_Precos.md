# Comparativo de Precos GPU Cloud 2025

## Tabela de Precos por GPU (Dezembro 2025)

### NVIDIA H100 80GB

| Provider | Preco/hora | Tipo | Notas |
|----------|------------|------|-------|
| **Vast.ai** | $1.87 | Marketplace | Mais baixo, variavel |
| **RunPod** | $1.99 | Community | Secure Cloud: $2.39 |
| **Thunder Compute** | $1.47 | On-demand | Budget option |
| **Lambda Labs** | $2.99 | On-demand | Managed |
| **CoreWeave** | $4.25 | Enterprise | SLA incluido |
| **AWS** | $4.10+ | On-demand | p5.48xlarge |
| **GCP** | $4.00+ | On-demand | a3-highgpu |
| **Azure** | $4.50+ | On-demand | NC-series |

**Insight**: Neoclouds oferecem H100 ate **85% mais barato** que hyperscalers.

### NVIDIA A100 80GB

| Provider | Preco/hora | Tipo | Notas |
|----------|------------|------|-------|
| **Vast.ai** | $0.22-0.87 | Marketplace | SXM vs PCIe |
| **Thunder Compute** | $0.78 | On-demand | Budget |
| **RunPod** | $1.19-1.39 | On-demand | PCIe vs SXM |
| **Lambda Labs** | $1.10 | On-demand | 40GB |
| **CoreWeave** | $2.06-2.21 | Enterprise | 40GB vs 80GB |
| **AWS** | $4.00+ | On-demand | p4d instances |

### NVIDIA A100 40GB

| Provider | Preco/hora | Notas |
|----------|------------|-------|
| **Lambda Labs** | $1.10 | Mais popular |
| **Thunder Compute** | $0.66 | Budget |
| **CoreWeave** | $2.06 | Enterprise |
| **AWS** | $3.00+ | p4d.24xlarge |

### RTX 4090 24GB

| Provider | Preco/hora | Notas |
|----------|------------|-------|
| **Vast.ai** | $0.30-0.50 | Marketplace |
| **RunPod** | $0.44 | Community |
| Dumont (target) | $0.40 | Competitivo |

---

## Analise de Margens

### Custo vs Preco de Venda

| GPU | Custo All-in/h* | Preco Mercado | Margem Bruta |
|-----|-----------------|---------------|--------------|
| H100 | ~$1.50 | $2.00-4.00 | 25-63% |
| A100 80GB | ~$0.80 | $1.20-2.20 | 33-64% |
| A100 40GB | ~$0.60 | $1.10-2.00 | 45-70% |
| RTX 4090 | ~$0.15 | $0.40-0.50 | 63-70% |

*Custo inclui: depreciacao GPU, energia, hosting, rede, overhead

### Benchmark de Margens da Industria

| Metrica | Valor | Fonte |
|---------|-------|-------|
| Margem Bruta Target | 60% | Industry Standard |
| EBITDA Margin (Neo-cloud madura) | 30-35% | McKinsey |
| ROI por $1 em GPU | $5-7 em 4 anos | Nvidia/Tom Tunguz |
| Oracle AI Cloud Margin | 16% | Internal docs leak |

---

## Estrategia de Pricing Dumont

### Tabela Proposta

| GPU | Preco Dumont | vs Vast.ai | vs RunPod | vs Lambda |
|-----|--------------|------------|-----------|-----------|
| H100 80GB | $2.50 | +34% | +26% | -16% |
| A100 80GB | $1.20 | +37% | -14% | +9% |
| A100 40GB | $0.90 | - | - | -18% |
| RTX 4090 | $0.40 | +0% | -9% | - |
| RTX 3090 | $0.30 | +0% | -14% | - |

**Posicionamento**: Entre Vast.ai (budget) e Lambda (premium)

### Diferenciais de Valor (nao so preco)

| Feature | Valor Agregado |
|---------|----------------|
| CPU Standby | Economia 80-90% em idle |
| Suporte BR | Reducao de churn |
| PIX instantaneo | Conversao +20% |
| Templates one-click | Time-to-value -80% |
| Storage persistente | Sem perda de dados |

---

## Custos Adicionais no Mercado

### Storage

| Provider | Preco/GB/mes | Notas |
|----------|--------------|-------|
| Vast.ai | $0.02 | Network storage |
| RunPod | $0.04 | Pod storage |
| Lambda | Incluido | Ate 512GB |
| Dumont (target) | $0.01 | 0-50GB gratis |

### Network Egress

| Provider | Preco/GB |
|----------|----------|
| AWS | $0.09 |
| GCP | $0.12 |
| Neoclouds | $0.00-0.05 |
| Dumont (target) | $0.05 (1TB gratis) |

---

## Modelos de Cobranca

### Pay-as-you-go (Predominante)
- Cobranca por segundo/minuto/hora
- Sem compromisso
- Preco mais alto

### Reserved/Committed
- Desconto 20-40% vs on-demand
- Compromisso 1-3 anos
- CoreWeave, Lambda oferecem

### Spot/Interruptible
- Desconto 50-80%
- Pode ser interrompido
- Vast.ai especialista

### Subscription (Oportunidade)
- Plano mensal com creditos inclusos
- Previsibilidade para usuario
- **Dumont Pro: $29/mes = $79 em creditos**

---

## Calculadora de Economia

### Caso 1: ML Researcher (160h/mes em RTX 4090)

| Provider | Custo Mensal |
|----------|--------------|
| AWS (equivalente) | $490 |
| Lambda | $120 |
| RunPod | $70 |
| Dumont | $64 |
| **Economia vs AWS** | **87%** |

### Caso 2: Startup AI (3x A100, 24/7)

| Provider | Custo Mensal |
|----------|--------------|
| GCP | $8,640 |
| CoreWeave | $4,766 |
| Lambda | $4,298 |
| Dumont | $2,592 |
| **Economia vs GCP** | **70%** |

### Caso 3: AI Artist (4h/semana ComfyUI)

| Provider | Custo Mensal |
|----------|--------------|
| RunPod | $7 |
| Vast.ai | $5 |
| Dumont | $6.40 |
| **Competitivo** | Sim |
