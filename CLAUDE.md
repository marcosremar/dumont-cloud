# CLAUDE.md - Diretrizes para Claude Code

## Filosofia do Projeto

**Vibe Coding** - Foco em resultados, não em perguntas desnecessárias.

---

## Plano de Refatoração - Modularização

### Objetivo
Transformar o sistema monolítico em módulos auto-contidos e reutilizáveis.
Reduzir arquivos gigantes (17K+ linhas) em módulos menores (~800 linhas cada).

### Módulos Existentes ✅

- [x] **serverless/** - GPU Serverless (pause/resume, checkpoint) - 3,438 linhas
- [x] **jobs/** - Job Execution System (fine-tuning, training) - ~2,000 linhas
- [x] **storage/** - Cloud Storage (B2/R2/S3/Wasabi) - ~1,200 linhas
- [x] **models/** - Model Registry & Auto-Deploy (HuggingFace) - ~1,000 linhas

### Novos Módulos a Criar

#### Prioridade 1 - Alto Impacto

- [x] **failover/** - Orquestração de Failover
  - **Objetivo**: Extrair 17,257 linhas do `failover_orchestrator.py`
  - **Componentes**:
    - `orchestrator.py` - Lógica central de failover
    - `strategies/regional.py` - Failover entre regiões
    - `strategies/snapshot.py` - Failover via snapshot
    - `strategies/warmpool.py` - Failover via warm pool
    - `strategies/coldstart.py` - Recovery cold start
    - `recovery.py` - Auto-recovery
    - `models.py` - FailoverEvent, FailoverConfig
  - **Consolida**: `failover_orchestrator.py`, `failover_settings.py`, `services/standby/failover.py`

- [x] **market/** - Market Intelligence
  - **Objetivo**: Unificar análise de mercado e preços
  - **Componentes**:
    - `service.py` - Market service com recomendações
    - `predictor.py` - ML price forecasting
    - `monitor.py` - Real-time price monitoring
    - `savings.py` - Cost optimization
    - `models.py` - PricePoint, PriceForecast, MarketSnapshot
  - **Consolida**: `price_prediction_service.py`, `price_monitor_agent.py`, `market_monitor_agent.py`, `savings_calculator.py`, `gpu/advisor.py`

- [x] **observability/** - Monitoramento e Alertas
  - **Objetivo**: Sistema unificado de observabilidade
  - **Componentes**:
    - `telemetry.py` - Métricas Prometheus
    - `alerting.py` - Sistema de alertas com cooldown
    - `health.py` - Health checks extensível
    - `models.py` - HealthStatus, Alert, ComponentHealth
  - **Consolida**: `telemetry_service.py`, `alert_manager.py`, endpoints de `metrics.py`

#### Prioridade 2 - Médio Impacto

- [x] **sync/** - Sync Engine
  - **Objetivo**: Sincronização de dados unificada
  - **Componentes**:
    - `service.py` - Serviço principal de sync
    - `checkpoint.py` - Checkpoint management (full/incremental)
    - `realtime.py` - lsyncd/rsync real-time
    - `models.py` - Checkpoint, SyncProgress, RestoreResult
  - **Consolida**: `sync_machine_service.py`, `gpu/snapshot.py`

- [x] **machines/** - Machine Management
  - **Objetivo**: Gestão completa de máquinas GPU
  - **Componentes**:
    - `service.py` - MachineManager principal
    - `history.py` - Event tracking
    - `models.py` - MachineInfo, MachineStats, HostBlacklist
  - **Consolida**: `machine_history_service.py`, `host_finder.py`

- [x] **warmpool/** - GPU Warm Pool
  - **Objetivo**: Pool de GPUs pré-aquecidas
  - **Componentes**:
    - `manager.py` - WarmPoolManager
    - `models.py` - WarmPoolState, WarmPoolStatus, WarmPoolConfig
  - **Consolida**: `services/warmpool/` inteiro

- [x] **hibernation/** - Auto-Hibernation
  - **Objetivo**: Auto-pause e hibernação inteligente
  - **Componentes**:
    - `manager.py` - HibernationManager
    - `detector.py` - IdleDetector
    - `models.py` - HibernationState, HibernationEvent
  - **Consolida**: `auto_hibernation_manager.py`, `hibernation.py`

#### Prioridade 3 - Organização

- [x] **providers/** - Unified Providers
  - **Objetivo**: Interface unificada de providers GPU
  - **Componentes**:
    - `base.py` - GPUProvider abstract class
    - `factory.py` - ProviderFactory (Vast, TensorDock, GCP)
  - **Consolida**: `infrastructure/providers/`, `services/gpu/vast.py`, `services/gpu/tensordock.py`

### Métricas de Sucesso ✅

| Métrica | Antes | Objetivo | Atual |
|---------|-------|----------|-------|
| Maior arquivo | 17,257 linhas | < 1,000 linhas | ~350 linhas |
| Módulos auto-contidos | 4 | 12 | **12** ✅ |
| Testabilidade | Média | Alta | Alta |
| Código duplicado | Alto | Mínimo | Mínimo |

### Padrão de Módulo

Cada módulo deve seguir esta estrutura:
```
src/modules/{nome}/
├── __init__.py      # Exports públicos
├── service.py       # Serviço principal
├── repository.py    # Persistência (se necessário)
├── models.py        # ORM models (se necessário)
├── config.py        # Configuração
├── strategies/      # Estratégias (se aplicável)
└── migrations/      # Migrations DB (se necessário)
```

---

## Regras de Teste

### SEMPRE fazer testes reais
- **Prioridade máxima**: Testes com GPU real, não mocks
- Economizar onde possível, mas NUNCA pular testes reais
- Não perguntar se deve fazer teste real - FAZER
- Usar GPUs mais baratas quando possível (RTX 4090 < $0.50/hr)

### Testes E2E
- Deploy de modelos reais (Whisper, Stable Diffusion, LLM)
- Testar serverless pause/wake com GPU real
- Medir cold start times reais

## Regras de Desenvolvimento

### Vibe Coding
- Não perder tempo com detalhes pequenos
- Ir direto ao ponto
- Executar e iterar rápido
- Perguntar só quando realmente necessário

### Código
- Preferir editar arquivos existentes a criar novos
- Manter backwards compatibility
- Testes passando antes de commitar

## Estrutura do Projeto

```
src/
├── modules/          # Módulos auto-contidos
│   └── serverless/   # Serverless GPU (pause/resume, checkpoint)
├── services/         # Serviços de domínio
├── api/              # Endpoints REST
└── infrastructure/   # Providers (VAST, GCP, TensorDock)

tests/
├── backend/
│   ├── e2e/          # Testes end-to-end (GPU real)
│   └── api/          # Testes de API
```

## Provedores GPU

- **VAST.ai**: Principal (pause/resume nativo)
- **TensorDock**: Bare metal (checkpoint CRIU)
- **GCP**: CPU Standby

## Comandos Úteis

```bash
# Rodar testes reais
pytest tests/backend/e2e/test_serverless_deploy_real.py -v -s --timeout=600

# Rodar apenas testes unitários
pytest tests/backend/e2e/test_serverless_module.py::TestServerlessModuleImports -v -c /dev/null

# Iniciar servidor
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```
