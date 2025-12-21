# GPU Warm Pool (Failover Rapido)

> **STATUS**: Habilitado por padrao | Feature principal de failover

## O que e GPU Warm Pool?

GPU Warm Pool e a estrategia principal de failover do Dumont Cloud. Utiliza **multiplas GPUs do mesmo host fisico** no VAST.ai, compartilhando um **Volume persistente**. Isso permite failover em **30-60 segundos** ao inves de 10-20 minutos.

---

## Por que e a Opcao Principal?

| Aspecto | GPU Warm Pool | CPU Standby |
|---------|---------------|-------------|
| **Tempo de Recovery** | 30-60 segundos | 10-20 minutos |
| **Transferencia de dados** | Zero (mesmo disco) | rsync 5-30 min |
| **Custo mensal** | ~$5-10 (so volume) | ~$11 (VM + disco) |
| **Performance apos failover** | 100% GPU | CPU limitada |
| **Complexidade** | Baixa | Media |

---

## Como Funciona

```
+---------------------------------------------------------------------+
|                    HOST COM MULTIPLAS GPUs                           |
|                    (mesmo machine_id)                                |
|                                                                      |
|   +--------------+    +--------------+    +--------------+          |
|   |   GPU #1     |    |   GPU #2     |    |   GPU #3     |          |
|   |  RUNNING     |    |  STOPPED     |    | (disponivel) |          |
|   |  (em uso)    |    |  (standby)   |    |              |          |
|   +------+-------+    +------+-------+    +--------------+          |
|          |                   |                                       |
|          |    +--------------+--------------+                        |
|          +----+      VOLUME COMPARTILHADO   |                        |
|               |      /data                  |                        |
|               |      - Models               |                        |
|               |      - Datasets             |                        |
|               |      - Configs              |                        |
|               |      - Checkpoints          |                        |
|               +-----------------------------+                        |
|                                                                      |
|   MESMA REDE LOCAL (latencia <1ms)                                  |
|   MESMO DISCO FISICO (sem transferencia)                            |
+---------------------------------------------------------------------+
```

### Fluxo de Failover

```
T=0.0s     GPU #1 falha (Spot interruption ou erro)
T=0.1s     Health check detecta falha
T=0.5s     Sistema dispara START na GPU #2
T=30-60s   GPU #2 esta RUNNING
T=60-90s   SSH ready, aplicacao pode continuar

TOTAL: ~60-90 segundos
```

---

## Ativar GPU Warm Pool

### Automatico (Padrao)
O Warm Pool e ativado automaticamente quando:
1. Voce cria uma nova maquina
2. Sistema busca hosts com 2+ GPUs
3. Volume e criado automaticamente
4. GPU standby fica em modo STOPPED

### Manual
1. Va em **Settings** > **Failover**
2. Verifique se **"GPU Warm Pool"** esta ativo
3. Escolha preferencias de GPU (RTX 4090, A100, etc)
4. Defina tamanho do volume (padrao: 100GB)

---

## Configurar por Maquina

1. Selecione a maquina em **Machines**
2. Clique em **"Failover Settings"**
3. Escolha estrategia:
   - **GPU Warm Pool** (Recomendado): Failover em 30-60s
   - **CPU Standby**: Failover em 10-20min (se host nao tem 2+ GPUs)
   - **Desativado**: Sem failover automatico

---

## Custos

### GPU Warm Pool

```
GPU Principal (RTX 4090):       $0.30-0.50/hora (em uso)
GPU Standby (STOPPED):          $0.00/hora (nao cobra GPU parada)
Volume 100GB:                   ~$5-10/mes

CUSTO MENSAL TOTAL: ~$5-10
```

### Comparacao

| Estrategia | Custo Mensal | Recovery Time |
|------------|--------------|---------------|
| GPU Warm Pool | $5-10 | 30-60 seg |
| CPU Standby | $11-28 | 10-20 min |
| Sem failover | $0 | Manual |

---

## O que Acontece Durante Failover

### Preservado (100%)
- Todos os arquivos no Volume (/data)
- Models e checkpoints
- Datasets
- Configuracoes
- Variaveis de ambiente

### Perdido
- Processos em memoria (RAM)
- Conexoes de rede ativas
- Cache temporario

### Notificacoes
Voce recebe notificacao quando:
- GPU #1 falha detectada
- GPU #2 iniciando
- Failover completo
- Nova GPU standby provisionada

---

## Fluxo de Decisao Automatico

```
                    +---------------------+
                    |  PROVISIONAR GPU    |
                    +----------+----------+
                               |
                    +----------v----------+
                    | Host tem >=2 GPUs?  |
                    +----------+----------+
                               |
              +----------------+----------------+
              | SIM                             | NAO
              v                                 v
    +---------------------+           +---------------------+
    | GPU WARM POOL       |           | CPU STANDBY (GCP)   |
    | (Estrategia         |           | (Fallback)          |
    |  Principal)         |           |                     |
    +---------------------+           +---------------------+
              |                                 |
              v                                 v
    +---------------------+           +---------------------+
    | - Cria Volume       |           | - Provisiona CPU    |
    | - GPU #1 principal  |           | - rsync continuo    |
    | - GPU #2 stopped    |           | - Snapshot B2/R2    |
    | - Failover: 60s     |           | - Failover: 10-20m  |
    +---------------------+           +---------------------+
```

---

## Monitoramento

### Ver Status
No dashboard, veja:
- Estado do Warm Pool (Active/Degraded)
- GPU Principal (ID, status)
- GPU Standby (ID, status)
- Volume (ID, tamanho, uso)
- Contagem de failovers

### API

```bash
# Status do warm pool
curl https://api.dumontcloud.com/api/v1/warmpool/status/123 \
  -H "Authorization: Bearer $API_KEY"

# Listar hosts com multiplas GPUs
curl "https://api.dumontcloud.com/api/v1/warmpool/hosts?gpu_name=RTX_4090&min_gpus=2" \
  -H "Authorization: Bearer $API_KEY"

# Provisionar warm pool
curl -X POST https://api.dumontcloud.com/api/v1/warmpool/provision \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"machine_id": 123, "host_machine_id": 88888}'

# Habilitar warm pool
curl -X POST https://api.dumontcloud.com/api/v1/warmpool/enable/123 \
  -H "Authorization: Bearer $API_KEY"

# Testar failover
curl -X POST https://api.dumontcloud.com/api/v1/warmpool/failover/test/123 \
  -H "Authorization: Bearer $API_KEY"
```

> Veja documentacao completa em [GPU Warm Pool API](/admin/doc/live#04_API/05_GPU_Warm_Pool_API.md)

---

## Limitacoes

| Limitacao | Mitigacao |
|-----------|-----------|
| Host pode nao ter GPU extra | Sistema busca hosts com 2+ GPUs |
| Volume nao migra entre hosts | Backup automatico para B2/R2 |
| Se host inteiro cair | Fallback para CPU Standby |

---

## Fallback Automatico

Se o Warm Pool nao estiver disponivel, o sistema automaticamente:

1. Detecta que host nao tem 2+ GPUs
2. Ativa **CPU Standby** como fallback
3. Sincroniza dados via rsync
4. Failover leva 10-20 minutos (mais lento, mas funciona)

Voce nao precisa configurar nada - e automatico.

---

## Best Practices

### Usar o Volume para Tudo
Salve todos os dados importantes em `/data`:
```python
# Salvar checkpoints no volume
MODEL_PATH = "/data/models"
torch.save(model.state_dict(), f'{MODEL_PATH}/checkpoint_{epoch}.pt')
```

### Checkpoints Frequentes
```python
# A cada 15-30 minutos
if step % 1000 == 0:
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'loss': loss,
    }, f'/data/checkpoints/step_{step}.pt')
```

### Nao Depender de /workspace
O volume `/data` persiste; `/workspace` pode ser efemero:
```bash
# Bom: usar /data
cd /data/meu-projeto

# Evitar: usar /workspace para dados importantes
cd /workspace/meu-projeto  # Pode perder em failover sem volume
```

---

## Comparacao Final

| Cenario | Estrategia | Recovery Time | Custo |
|---------|------------|---------------|-------|
| GPU falha (host multi-GPU) | Warm Pool | 30-60 seg | $5-10/mes |
| GPU falha (host single-GPU) | CPU Standby | 10-20 min | $11-28/mes |
| Host inteiro falha | CPU + Snapshot | 15-30 min | $11-28/mes |

**Perda de dados:** ZERO em todos os cenarios (com volume/backup)

---

## Proximos Passos

1. Crie uma maquina - Warm Pool e ativado automaticamente
2. Verifique o status em **Machines** > **Failover**
3. Seus dados estarao protegidos com recovery em 30-60 segundos
