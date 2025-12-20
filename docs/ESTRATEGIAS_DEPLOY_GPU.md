# Estrategias de Deploy GPU - Analise Comparativa

> Documento tecnico comparando todas as estrategias de deploy de containers GPU no DumontCloud.
> Ultima atualizacao: 2024-12-20

## Indice

1. [Visao Geral](#1-visao-geral)
2. [Estrategias Identificadas](#2-estrategias-identificadas)
3. [Tabela Comparativa Principal](#3-tabela-comparativa-principal)
4. [Imagens Docker Disponiveis](#4-imagens-docker-disponiveis)
5. [Detalhamento por Stack](#5-detalhamento-por-stack)
6. [Analise de Trade-offs](#6-analise-de-trade-offs)
7. [Fluxo de Cache (Estrategia D)](#7-fluxo-de-cache-estrategia-d)
8. [Recomendacoes por Caso de Uso](#8-recomendacoes-por-caso-de-uso)
9. [Implementacao Atual](#9-implementacao-atual)
10. [Proximos Passos](#10-proximos-passos)

---

## 1. Visao Geral

O tempo de startup de um container GPU e critico para a experiencia do usuario. Este documento analisa todas as estrategias possiveis para minimizar esse tempo, considerando trade-offs entre velocidade, complexidade e custo.

### Problema Principal

- Imagens pesadas como `vastai/base-image` (~8GB) demoram 2+ minutos para carregar
- Instalar dependencias (PyTorch, vLLM, Ollama) via script adiciona tempo extra
- Usuarios esperam respostas em segundos, nao minutos

### Objetivo

Reduzir o tempo de startup para **< 60 segundos** na primeira execucao e **< 30 segundos** em restarts.

---

## 2. Estrategias Identificadas

| # | Estrategia | Descricao | Exemplo |
|---|------------|-----------|---------|
| **A** | Docker Oficial Pronto | Usar imagem pronta do Docker Hub | `ollama/ollama`, `pytorch/pytorch` |
| **B** | Docker Oficial + Script | Imagem oficial + instalar extras via onstart | `ollama/ollama` + SSH install |
| **C** | Docker Custom Publicado | Criar imagem propria no Docker Hub | `dumontcloud/gpu-base:pytorch` |
| **D** | Base + Cache Backblaze | Imagem minima + baixar binarios de cache externo | `cuda-base` + download B2 |
| **E** | Base + Vast Snapshot | Imagem minima + restaurar snapshot Vast.ai | Snapshot com ambiente pronto |
| **F** | Docker Custom + Snapshot | Imagem propria + snapshot para dados/modelos | Custom + modelos em snapshot |

---

## 3. Tabela Comparativa Principal

| Criterio | A: Oficial | B: +Script | C: Custom | D: Cache B2 | E: Snapshot | F: Custom+Snap |
|----------|------------|------------|-----------|-------------|-------------|----------------|
| **Tempo 1o Start** | 30-120s | 60-180s | 30-60s | 40-90s | 20-40s | 15-30s |
| **Tempo Restart** | 30-120s | 60-180s | 30-60s | 20-40s | 10-20s | 10-20s |
| **Complexidade** | Baixa | Media | Alta | Alta | Media | Muito Alta |
| **Manutencao** | Nenhuma | Baixa | Alta | Alta | Media | Alta |
| **Custo Storage** | $0 | $0 | $0 | ~$5/mes | ~$10/mes | ~$15/mes |
| **Flexibilidade** | Baixa | Alta | Total | Total | Media | Total |
| **Portabilidade** | Alta | Alta | Alta | Media | Baixa | Baixa |
| **Confiabilidade** | Alta | Media | Alta | Media | Alta | Alta |

### Legenda de Cores (para visualizacao)

- **Verde**: Melhor opcao nesse criterio
- **Amarelo**: Opcao intermediaria
- **Vermelho**: Pior opcao nesse criterio

---

## 4. Imagens Docker Disponiveis

### Ordenadas por Velocidade de Carregamento

| Chave | Imagem | Tamanho | Tempo Start | Contem |
|-------|--------|---------|-------------|--------|
| `cuda-base` | `nvidia/cuda:12.1.0-base-ubuntu22.04` | ~200MB | <30s | CUDA base |
| `cuda-runtime` | `nvidia/cuda:12.1.0-runtime-ubuntu22.04` | ~1.5GB | <30s | CUDA runtime |
| `ollama` | `ollama/ollama` | ~2GB | 30-60s | Ollama pronto |
| `pytorch` | `pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime` | ~3GB | 30-60s | PyTorch |
| `vastai-pytorch` | `vastai/pytorch` | ~4-5GB | 60-120s | PyTorch + SSH |
| `vastai` | `vastai/base-image` | ~8GB | >120s | SSH + extras |

### Descoberta Importante

> **PyTorch inclui seus proprios binarios CUDA!**
> 
> Isso significa que nao precisa de imagem `runtime` ou `devel` da NVIDIA.
> Usar `nvidia/cuda:base` + PyTorch via pip = **60% menor** que usar `runtime`.

Fonte: [Optimizing PyTorch Docker images: how to cut size by 60%](https://mveg.es/posts/optimizing-pytorch-docker-images-cut-size-by-60percent/)

---

## 5. Detalhamento por Stack

### 5.1 Para OLLAMA (LLM Local)

| Opcao | Imagem | Setup | 1o Start | Restart | Notas |
|-------|--------|-------|----------|---------|-------|
| A1 | `ollama/ollama` | SSH script | ~60s | ~60s | Simples, Ollama pronto |
| B1 | `cuda-base` + ollama install | Script completo | ~90s | ~90s | Mais controle |
| D1 | `cuda-base` + B2 cache | Baixa ollama de B2 | ~50s | ~30s | Rapido no restart |
| E1 | Snapshot com Ollama | Restore | ~30s | ~20s | Mais rapido, custo storage |

**Recomendacao:** Usar `ollama/ollama` + SSH script (estrategia B) para simplicidade.

### 5.2 Para PYTORCH

| Opcao | Imagem | Setup | 1o Start | Restart | Notas |
|-------|--------|-------|----------|---------|-------|
| A2 | `pytorch/pytorch:runtime` | SSH script | ~50s | ~50s | Simples |
| B2 | `cuda-base` + pip install | Script | ~120s | ~120s | Flexivel mas lento |
| C2 | Custom com PyTorch | Nenhum | ~40s | ~40s | Pre-built |
| D2 | `cuda-base` + B2 cache | Extrai .tar.gz | ~45s | ~25s | Cache de wheels |

**Recomendacao:** Usar `pytorch/pytorch:runtime` + SSH script para balance.

### 5.3 Para VLLM

| Opcao | Imagem | Setup | 1o Start | Restart | Notas |
|-------|--------|-------|----------|---------|-------|
| A3 | `vllm/vllm-openai` | SSH script | ~90s | ~90s | Oficial, pesado |
| C3 | Custom VLLM slim | Nenhum | ~60s | ~60s | Otimizado |
| D3 | `cuda-base` + B2 vllm | Download | ~70s | ~40s | Cache ajuda |
| F3 | Custom + Snap modelos | Restore | ~40s | ~25s | Modelos em snapshot |

**Recomendacao:** Para producao, usar Custom + Snapshot (F) devido aos modelos grandes.

---

## 6. Analise de Trade-offs

### 6.1 Velocidade vs Complexidade

```
MAIS RAPIDO ──────────────────────────────────────> MAIS LENTO
   F          E          D          C          A          B
(Custom+Snap) (Snapshot)  (Cache)   (Custom)  (Oficial)  (Script)
   ▲                                                        ▲
   │                                                        │
COMPLEXO ◄───────────────────────────────────────────► SIMPLES
```

### 6.2 Custo vs Velocidade

```
                    ┌─────────────────────────────────┐
                    │     F: Custom + Snapshot        │ ← Mais rapido
                    │     (custo: ~$15/mes)           │   no restart
                    ├─────────────────────────────────┤
                    │     E: Vast Snapshot            │
                    │     (custo: ~$10/mes)           │
                    ├─────────────────────────────────┤
                    │     D: Cache Backblaze          │
                    │     (custo: ~$5/mes)            │
                    ├─────────────────────────────────┤
                    │     C: Custom Docker            │
                    │     (custo: $0)                 │
                    ├─────────────────────────────────┤
                    │     A/B: Oficial                │ ← Mais lento
                    │     (custo: $0)                 │   mas simples
                    └─────────────────────────────────┘
```

---

## 7. Fluxo de Cache (Estrategia D)

### 7.1 Primeira Execucao

```
┌─────────────────────────────────────────────────────────────┐
│                    PRIMEIRA EXECUCAO                         │
├─────────────────────────────────────────────────────────────┤
│  1. Start container (cuda-base) ────────────────► ~10s      │
│  2. apt-get install python, ssh ────────────────► ~20s      │
│  3. pip install pytorch/vllm/ollama ────────────► ~60s      │
│  4. UPLOAD para Backblaze (tar.gz) ─────────────► ~30s      │
│                                         TOTAL: ~120s        │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Execucoes Seguintes

```
┌─────────────────────────────────────────────────────────────┐
│                    EXECUCOES SEGUINTES                       │
├─────────────────────────────────────────────────────────────┤
│  1. Start container (cuda-base) ────────────────► ~10s      │
│  2. Download de Backblaze ──────────────────────► ~15s      │
│  3. Extrai tar.gz ──────────────────────────────► ~5s       │
│  4. Ready! ─────────────────────────────────────► ~0s       │
│                                         TOTAL: ~30s         │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 Estrutura do Cache

```
backblaze-bucket/
├── cache/
│   ├── pytorch-2.1.0-cuda12.1.tar.gz      (~2.5GB)
│   ├── vllm-0.4.0-cuda12.1.tar.gz         (~3GB)
│   ├── ollama-linux-amd64.tar.gz          (~1GB)
│   └── ssh-config.tar.gz                  (~1MB)
└── models/
    ├── qwen3-0.6b.tar.gz                  (~400MB)
    └── llama3.1-8b.tar.gz                 (~4.5GB)
```

---

## 8. Recomendacoes por Caso de Uso

| Caso de Uso | Estrategia | Imagem | Por que? |
|-------------|------------|--------|----------|
| **Dev/Teste rapido** | A/B | `ollama/ollama` + SSH | Simples, funciona |
| **Producao Ollama** | D | Cache B2 | Restart rapido, custo baixo |
| **Producao PyTorch** | C | Custom Docker | Controle total, sem overhead |
| **Producao VLLM** | F | Custom + Snapshot | Modelos grandes = snapshot |
| **Multi-tenant** | C | Custom Docker | Consistencia entre deploys |
| **Custo minimo** | A/B | Oficial | Zero storage extra |
| **Velocidade maxima** | F | Custom + Snapshot | ~15s restart |

---

## 9. Implementacao Atual

### 9.1 Codigo em `deploy_wizard.py`

```python
# Imagens Docker disponiveis (ordenadas por velocidade de carregamento)
DOCKER_IMAGES = {
    # ULTRA RAPIDAS (< 30s) - Sem PyTorch
    "cuda-base": "nvidia/cuda:12.1.0-base-ubuntu22.04",
    "cuda-runtime": "nvidia/cuda:12.1.0-runtime-ubuntu22.04",
    "ollama": "ollama/ollama",
    
    # RAPIDAS (30-60s) - Com PyTorch otimizado
    "pytorch": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
    
    # MEDIAS (60-120s) - PyTorch + SSH pronto
    "vastai-pytorch": "vastai/pytorch",
    
    # LENTAS (>120s) - Pesadas mas completas
    "vastai": "vastai/base-image",
}
```

### 9.2 Script SSH Atual

```bash
apt-get update && apt-get install -y --no-install-recommends openssh-server && \
mkdir -p /var/run/sshd /root/.ssh && \
echo "SSH_PUBLIC_KEY" > /root/.ssh/authorized_keys && \
chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys && \
echo "PermitRootLogin yes" >> /etc/ssh/sshd_config && \
echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config && \
/usr/sbin/sshd
```

---

## 10. Proximos Passos

### 10.1 Curto Prazo (Funciona Hoje)
- [x] Usar `ollama/ollama` + SSH script
- [x] Tempo atual: ~60-78s para SSH ready
- [ ] Testar `pytorch/pytorch` para workloads PyTorch

### 10.2 Medio Prazo (Cache Backblaze)
- [ ] Implementar sistema de cache no Backblaze B2
- [ ] Criar scripts de upload/download automatico
- [ ] Primeira execucao faz upload, seguintes fazem download
- [ ] Meta: ~30s restart

### 10.3 Longo Prazo (Otimizacao Maxima)
- [ ] Criar imagens Docker customizadas para cada stack
- [ ] Publicar no Docker Hub: `dumontcloud/gpu-ollama`, `dumontcloud/gpu-pytorch`
- [ ] Usar Vast snapshots para dados/modelos grandes
- [ ] Meta: ~15s restart

---

## Apendice: Referencias

1. [Optimizing PyTorch Docker images](https://mveg.es/posts/optimizing-pytorch-docker-images-cut-size-by-60percent/)
2. [NVIDIA CUDA Docker Hub](https://hub.docker.com/r/nvidia/cuda)
3. [Vast.ai Documentation - Templates](https://docs.vast.ai/documentation/templates/introduction)
4. [AI-Dock PyTorch Images](https://github.com/ai-dock/pytorch)
5. [Backblaze B2 Documentation](https://www.backblaze.com/docs/cloud-storage)

---

*Documento gerado automaticamente. Para atualizacoes, editar `docs/ESTRATEGIAS_DEPLOY_GPU.md`*
