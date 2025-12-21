# GPU Warm Pool - Arquitetura Tecnica

Documentacao tecnica da estrategia principal de failover do Dumont Cloud.

## Visao Geral

O GPU Warm Pool utiliza **multiplas GPUs do mesmo host fisico** no VAST.ai para failover ultra-rapido (30-60 segundos).

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
|               +-----------------------------+                        |
|                                                                      |
|   MESMA REDE LOCAL (latencia <1ms)                                  |
|   MESMO DISCO FISICO (sem transferencia)                            |
+---------------------------------------------------------------------+
```

---

## Componentes

### 1. WarmPoolManager

Coordenador central do warm pool.

```python
# src/services/warmpool/manager.py

class WarmPoolState(Enum):
    DISABLED = "disabled"
    SEARCHING = "searching"       # Buscando host com multi-GPU
    PROVISIONING = "provisioning" # Criando volume e instancias
    ACTIVE = "active"             # GPU #1 running, GPU #2 stopped
    FAILOVER = "failover"         # GPU #2 iniciando
    DEGRADED = "degraded"         # Sem warm pool, usando CPU standby

class WarmPoolManager:
    async def find_multi_gpu_hosts(gpu_name: str) -> List[dict]
    async def provision_warm_pool(machine_id: int) -> bool
    async def trigger_failover() -> bool
    async def health_check() -> WarmPoolStatus
```

### 2. Volume Service

Gerencia volumes VAST.ai.

```python
# src/services/warmpool/volume_service.py

class VolumeService:
    async def create_volume(machine_id: int, size_gb: int) -> Volume
    async def attach_volume(instance_id: int, volume_id: int) -> bool
    async def detach_volume(instance_id: int, volume_id: int) -> bool
    async def get_volume_status(volume_id: int) -> VolumeStatus
```

### 3. Host Finder

Busca hosts com multiplas GPUs.

```python
# src/services/warmpool/host_finder.py

class HostFinder:
    async def search_multi_gpu_hosts(
        gpu_name: str = "RTX_4090",
        min_gpus: int = 2,
        verified: bool = True
    ) -> List[MultiGPUHost]
```

---

## Fluxo de Provisioning

```
1. BUSCAR HOST
   +------------------+
   | search_offers    |
   | num_gpus >= 2    |
   | gpu_name = 4090  |
   +--------+---------+
            |
            v
   +------------------+
   | Agrupar por      |
   | machine_id       |
   +--------+---------+
            |
            v
2. CRIAR VOLUME
   +------------------+
   | create_volume    |
   | machine_id = X   |
   | size = 100GB     |
   +--------+---------+
            |
            v
3. GPU PRINCIPAL
   +------------------+
   | create_instance  |
   | offer_id = A     |
   | volume_id = V    |
   +--------+---------+
            |
            v
4. GPU STANDBY
   +------------------+
   | create_instance  |
   | offer_id = B     |
   | volume_id = V    |
   +--------+---------+
            |
            v
   +------------------+
   | stop_instance    |
   | instance_id = B  |
   +--------+---------+
            |
            v
5. WARM POOL ATIVO
   GPU #1: RUNNING
   GPU #2: STOPPED
   Volume: ATTACHED
```

---

## Fluxo de Failover

```
T=0.0s     GPU #1 FALHA
           +------------------+
           | Health check     |
           | detecta falha    |
           +--------+---------+
                    |
T=0.5s              v
           +------------------+
           | start_instance   |
           | GPU #2           |
           +--------+---------+
                    |
T=30-60s            v
           +------------------+
           | GPU #2 RUNNING   |
           | Volume montado   |
           +--------+---------+
                    |
T=60-90s            v
           +------------------+
           | SSH ready        |
           | App continua     |
           +------------------+

           BACKGROUND:
           +------------------+
           | cleanup GPU #1   |
           | provision nova   |
           | GPU standby      |
           +------------------+
```

---

## API VAST.ai Utilizada

### Search Offers

```bash
POST https://console.vast.ai/api/v0/bundles/
{
    "num_gpus": {"gte": 2},
    "gpu_name": "RTX_4090",
    "verified": true,
    "rentable": true
}
```

### Create Volume

```bash
POST https://console.vast.ai/api/v0/volumes/
{
    "size": 100,
    "machine_id": 88888
}
```

### Create Instance

```bash
POST https://console.vast.ai/api/v0/asks/<offer_id>/
{
    "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
    "volume_id": 12345,
    "onstart": "..."
}
```

### Stop/Start Instance

```bash
PUT https://console.vast.ai/api/v0/instances/<id>/
{
    "state": "stopped"  # ou "running"
}
```

---

## Configuracao

```python
# src/config/warmpool_settings.py

class WarmPoolSettings(BaseSettings):
    # Habilitado por padrao
    WARM_POOL_ENABLED: bool = True

    # Requisitos do host
    WARM_POOL_MIN_GPUS: int = 2
    WARM_POOL_PREFERRED_GPUS: str = "RTX_4090,A100,RTX_3090"

    # Volume
    WARM_POOL_VOLUME_SIZE_GB: int = 100

    # Comportamento
    WARM_POOL_AUTO_PROVISION: bool = True
    WARM_POOL_FALLBACK_TO_CPU: bool = True
    WARM_POOL_HEALTH_CHECK_INTERVAL: int = 10  # segundos

    class Config:
        env_file = ".env"
```

---

## Endpoints REST

### Warm Pool

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/v1/warmpool/status/{machine_id}` | GET | Status do warm pool |
| `/api/v1/warmpool/hosts` | GET | Listar hosts multi-GPU |
| `/api/v1/warmpool/provision` | POST | Provisionar warm pool |
| `/api/v1/warmpool/enable/{machine_id}` | POST | Habilitar warm pool |
| `/api/v1/warmpool/disable/{machine_id}` | POST | Desabilitar (usa CPU) |
| `/api/v1/warmpool/failover/test/{machine_id}` | POST | Testar failover |
| `/api/v1/warmpool/cleanup/{machine_id}` | DELETE | Limpar recursos |

### Failover Orchestrator

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/v1/failover/execute` | POST | Executar failover |
| `/api/v1/failover/readiness/{machine_id}` | GET | Verificar prontidao |
| `/api/v1/failover/status/{machine_id}` | GET | Status detalhado |
| `/api/v1/failover/strategies` | GET | Listar estrategias |

### Failover Settings

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/v1/failover/settings/global` | GET/PUT | Config global |
| `/api/v1/failover/settings/machines/{id}` | GET/PUT | Config por maquina |
| `/api/v1/failover/settings/machines/{id}/enable-warm-pool` | POST | Habilitar warm pool |
| `/api/v1/failover/settings/machines/{id}/enable-both` | POST | Habilitar ambas estrategias |

> Documentacao completa: [GPU Warm Pool API](/admin/doc/live#04_API/05_GPU_Warm_Pool_API.md)

---

## Estados do Sistema

```
                    +------------+
                    |  DISABLED  |
                    +-----+------+
                          |
                          | enable()
                          v
                    +------------+
                    | SEARCHING  |
                    +-----+------+
                          |
                          | host found
                          v
                    +-------------+
                    |PROVISIONING |
                    +-----+-------+
                          |
                          | success
                          v
                    +------------+
            +------>|   ACTIVE   |<------+
            |       +-----+------+       |
            |             |              |
            |             | GPU #1 fail  |
            |             v              |
            |       +------------+       |
            |       |  FAILOVER  |-------+
            |       +-----+------+ success
            |             |
            |             | fail
            |             v
            |       +------------+
            +-------|  DEGRADED  |
         recovery   +------------+
                          |
                          | CPU standby
                          v
                    +------------+
                    | CPU_ACTIVE |
                    +------------+
```

---

## Custos

### Warm Pool Ativo

| Componente | Custo |
|------------|-------|
| GPU Principal (RTX 4090) | $0.30-0.50/hora |
| GPU Standby (STOPPED) | $0.00/hora |
| Volume 100GB | ~$5-10/mes |
| **Total mensal** | **$5-10** |

### Comparacao

| Estrategia | Custo Mensal | Recovery |
|------------|--------------|----------|
| GPU Warm Pool | $5-10 | 30-60s |
| CPU Standby (Spot) | $11 | 10-20min |
| CPU Standby (On-demand) | $28 | 10-20min |

---

## Limitacoes

### Volume VAST.ai

| Limitacao | Impacto |
|-----------|---------|
| Volume preso ao host | Nao migra entre hosts |
| Uma instancia por vez | Nao pode compartilhar simultaneamente |
| Destroy para mover | Precisa destruir instancia para reanexar |

### Disponibilidade

| Limitacao | Mitigacao |
|-----------|-----------|
| Host pode nao ter 2+ GPUs | Buscar hosts qualificados |
| Host inteiro pode falhar | Fallback para CPU Standby |
| GPU standby pode ser alugada | Monitorar disponibilidade |

---

## Fallback Automatico

Se Warm Pool nao disponivel:

```
WARM_POOL_FALLBACK_TO_CPU=true

1. Host nao tem 2+ GPUs
   -> Ativar CPU Standby automaticamente

2. Host inteiro falha
   -> CPU assume
   -> Restaura de snapshot B2/R2

3. GPU standby indisponivel
   -> Tentar provisionar nova
   -> Se falhar, CPU Standby
```

---

## Monitoramento

### Metricas Prometheus

```python
# Metricas exportadas
warm_pool_state              # Estado atual (0-5)
warm_pool_failover_count     # Total de failovers
warm_pool_failover_duration  # Duracao do ultimo failover
warm_pool_gpu_primary_status # Status GPU principal
warm_pool_gpu_standby_status # Status GPU standby
warm_pool_volume_usage_gb    # Uso do volume
```

### Alertas

```yaml
# alerts.yml
- alert: WarmPoolDegraded
  expr: warm_pool_state == 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Warm Pool em modo degradado"

- alert: WarmPoolFailoverSlow
  expr: warm_pool_failover_duration > 120
  labels:
    severity: warning
  annotations:
    summary: "Failover demorou mais de 2 minutos"
```

---

## Arquivos do Projeto

```
src/services/warmpool/
├── __init__.py
├── manager.py              # WarmPoolManager
├── host_finder.py          # HostFinder
├── volume_service.py       # VolumeService
├── failover_handler.py     # FailoverHandler
└── health_checker.py       # HealthChecker

src/api/v1/endpoints/
└── warmpool.py             # REST endpoints

src/config/
└── warmpool_settings.py    # Configuracoes

tests/
└── test_warmpool/
    ├── test_manager.py
    ├── test_failover.py
    └── test_volume.py
```

---

## Ver Tambem

- [GPU Warm Pool (Feature)](../03_Features/05_GPU_Warm_Pool.md)
- [CPU Standby (Fallback)](../03_Features/04_CPU_Standby.md)
- [Estrategias Deploy GPU](01_Estrategias_Deploy_GPU.md)
