# CPU Standby (Failover de Fallback)

> **STATUS**: Estrategia de fallback | Usado quando GPU Warm Pool nao disponivel

## O que e CPU Standby?

CPU Standby e a **estrategia de fallback** do Dumont Cloud. E uma maquina de baixo custo (GCP) que assume quando sua GPU Spot e interrompida, garantindo que voce nunca perca dados.

### Quando e Usado?

| Cenario | Estrategia Usada |
|---------|------------------|
| Host tem 2+ GPUs | **GPU Warm Pool** (principal) |
| Host tem 1 GPU | **CPU Standby** (fallback) |
| Host inteiro falha | **CPU Standby** + Snapshot B2/R2 |
| Usuario desativou Warm Pool | **CPU Standby** |

> **Nota**: Prefira hosts com 2+ GPUs para usar o [GPU Warm Pool](05_GPU_Warm_Pool.md) - failover em 30-60s vs 10-20min.

---

## Como Funciona

```mermaid
sequenceDiagram
    participant GPU as GPU Spot
    participant Agent as Dumont Agent
    participant CPU as CPU Standby
    participant R2 as Backup R2

    Note over GPU: Rodando normalmente
    GPU->>R2: Sync a cada 30s

    Note over GPU: Interrupcao detectada!
    Agent->>CPU: Ativar standby
    CPU->>R2: Baixar ultimo backup
    CPU->>CPU: Continuar trabalho

    Note over GPU: GPU disponivel novamente
    CPU->>R2: Sync final
    Agent->>GPU: Restaurar para GPU
    Agent->>CPU: Desativar standby
```

### Fluxo
1. **Normal**: GPU roda, sincroniza dados a cada 30s
2. **Interrupcao**: GPU cai, sistema detecta em ~5s
3. **Failover**: CPU Standby assume, restaura ultimo backup
4. **Continuidade**: Voce pode continuar trabalhando na CPU
5. **Restauracao**: Quando GPU volta, migra de volta automaticamente

---

## Tipos de CPU Standby

| Tipo | vCPUs | RAM | Preco | Uso |
|------|-------|-----|-------|-----|
| **e2-medium** | 2 | 4GB | $0.03/h | Basico |
| **e2-standard-4** | 4 | 16GB | $0.15/h | Recomendado |
| **n2-standard-8** | 8 | 32GB | $0.40/h | Intensivo |
| **c2-standard-16** | 16 | 64GB | $0.80/h | HPC |

---

## Configurar CPU Standby

### Ativar
1. Va em **Settings** > **Failover**
2. Ative **"CPU Standby Automatico"**
3. Escolha o tipo de CPU
4. Salve

### Por Maquina
1. Selecione a maquina em **Machines**
2. Clique em **"Configuracoes"**
3. Ative **"Failover para CPU"**
4. Escolha comportamento:
   - **Automatico**: Failover + restore automatico
   - **Manual**: Failover automatico, restore manual
   - **Desativado**: Sem failover

---

## O que Acontece Durante Failover

### Dados Preservados
- Arquivos sincronizados (ultimo backup)
- Variaveis de ambiente
- Configuracoes do sistema

### Dados Perdidos
- Processos em memoria (nao salvos)
- Conexoes de rede ativas
- Arquivos nao sincronizados

### Notificacoes
Voce recebe notificacao quando:
- Failover iniciado
- CPU Standby ativo
- GPU restaurada
- Failback completo

---

## Durante o Standby

### O que voce pode fazer
- Acessar arquivos
- Rodar scripts leves
- Preparar dados
- Fazer debugging

### O que nao e recomendado
- Treinar modelos grandes
- Inferencia pesada
- Compilacao intensiva

### Custo
Voce paga apenas pela CPU Standby enquanto ativa:
- GPU: $0.00 (pausada)
- CPU: $0.15/h (ativa)

---

## Tempo de Failover

| Etapa | Tempo |
|-------|-------|
| Deteccao de interrupcao | ~5s |
| Ativacao do standby | ~10s |
| Download do backup | ~30s-5min* |
| Sistema pronto | ~1min |

*Depende do tamanho dos dados

### Otimizar Tempo
- Mantenha backups pequenos (exclua arquivos grandes)
- Use SSD no standby
- Escolha regiao proxima

---

## Monitoramento

### Ver Status
No dashboard, veja:
- Estado atual (GPU/CPU Standby)
- Tempo em standby
- Custo acumulado
- Ultimas interrupcoes

### Historico
1. Va em **Machines** > **Historico de Failover**
2. Veja todas as interrupcoes
3. Analise padroes (horarios, duracoes)

---

## Precos

### CPU Standby
Voce paga apenas quando a CPU esta ativa:

| Evento | Custo |
|--------|-------|
| GPU rodando | $0.40/h (GPU) |
| Interrupcao (failover) | $0.15/h (CPU) |
| GPU volta (failback) | $0.40/h (GPU) |

### Exemplo
```
GPU rodando: 10 horas × $0.40 = $4.00
Interrupcoes: 30 min em CPU × $0.15 = $0.075
Total: $4.075
```

---

## Best Practices

### Checkpoints Frequentes
Salve checkpoints a cada 15-30 minutos para minimizar perda:
```python
# PyTorch
torch.save(model.state_dict(), f'checkpoint_{epoch}.pt')

# TensorFlow
model.save_weights(f'checkpoint_{epoch}')
```

### Scripts de Resume
Crie scripts que detectam e retomam do ultimo checkpoint:
```python
import glob

checkpoints = glob.glob('checkpoint_*.pt')
if checkpoints:
    latest = max(checkpoints)
    model.load_state_dict(torch.load(latest))
    print(f"Resuming from {latest}")
```

### Graceful Shutdown
Trate sinais de interrupcao:
```python
import signal

def handle_interrupt(signum, frame):
    print("Salvando checkpoint final...")
    torch.save(model.state_dict(), 'checkpoint_final.pt')
    exit(0)

signal.signal(signal.SIGTERM, handle_interrupt)
```

---

## Comparacao: CPU Standby vs GPU Warm Pool

| Aspecto | GPU Warm Pool | CPU Standby |
|---------|---------------|-------------|
| **Recovery Time** | 30-60 segundos | 10-20 minutos |
| **Custo Mensal** | ~$5-10 | ~$11-28 |
| **Performance** | 100% GPU | Limitado (CPU) |
| **Transferencia** | Zero (mesmo disco) | rsync (lento) |
| **Disponibilidade** | Host com 2+ GPUs | Sempre |
| **Recomendacao** | **PRINCIPAL** | Fallback |

### Quando Preferir CPU Standby?

- Host disponivel so tem 1 GPU
- Precisa de resiliencia multi-datacenter
- Custo nao e prioridade (CPU on-demand)

### Quando Preferir GPU Warm Pool?

- Recovery time < 1 minuto e critico
- Quer manter 100% performance GPU
- Host tem 2+ GPUs disponiveis

---

## API Reference

### Endpoints de Standby

```bash
# Status do standby
curl https://api.dumontcloud.com/api/v1/standby/status \
  -H "Authorization: Bearer $API_KEY"

# Configurar standby
curl -X POST https://api.dumontcloud.com/api/v1/standby/configure \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "gcp_zone": "europe-west1-b",
    "gcp_machine_type": "e2-standard-4"
  }'

# Listar associacoes GPU-CPU
curl https://api.dumontcloud.com/api/v1/standby/associations \
  -H "Authorization: Bearer $API_KEY"

# Iniciar sync manualmente
curl -X POST https://api.dumontcloud.com/api/v1/standby/associations/456789/start-sync \
  -H "Authorization: Bearer $API_KEY"

# Estimar custos
curl https://api.dumontcloud.com/api/v1/standby/pricing \
  -H "Authorization: Bearer $API_KEY"
```

### Endpoints de Failover Testing

```bash
# Simular failover
curl -X POST https://api.dumontcloud.com/api/v1/standby/failover/simulate/456789 \
  -H "Authorization: Bearer $API_KEY"

# Relatório de failovers
curl https://api.dumontcloud.com/api/v1/standby/failover/report \
  -H "Authorization: Bearer $API_KEY"
```

> Veja documentacao completa em [Failover Orchestrator API](/admin/doc/live#04_API/03_Failover_Orchestrator.md)

---

## Ver Tambem

- [GPU Warm Pool](05_GPU_Warm_Pool.md) - Estrategia principal de failover
- [Failover Settings API](/admin/doc/live#04_API/04_Failover_Settings.md) - Configurar estrategias
