# Plano: Sistema de Auto-Hibernação Inteligente de GPUs

## 📋 Resumo Executivo

Implementar sistema de auto-hibernação que monitora uso da GPU e automaticamente:
- **3 min ociosa**: Cria snapshot ANS + Destroi instância vast.ai (economiza 100%)
- **30 min destruída**: Mantém snapshot no R2 (custo: $0.01/mês)
- **Reativação**: 3 opções (Manual, Automática, Agendada)
- **Monitoramento**: nvidia-smi utilização < 5%
- **Notificações**: Log apenas (sem alertas)

## 🎯 Requisitos Funcionais

### RF1: Monitoramento Automático de GPU
- Agente roda **dentro da instância GPU** (via DumontAgent)
- Verifica a cada **30 segundos**: `nvidia-smi --query-gpu=utilization.gpu`
- Considera ociosa se: **utilização < 5%** por **3 minutos consecutivos**
- Log: timestamp, utilização, status

### RF2: Auto-Pausar (3 min ociosa)
```
GPU ociosa por 3 min →
  1. Criar snapshot ANS (via GPUSnapshotService)
  2. Destruir instância vast.ai (via VastService)
  3. Registrar evento no DB
  4. Status da instância: "hibernated"
```

### RF3: Auto-Deletar Instância (30 min destruída)
```
Instância destruída há 30 min →
  1. Verificar se snapshot existe no R2
  2. Se existe: manter snapshot
  3. Se não: criar snapshot final antes de deletar
  4. Status: "deleted" (snapshot permanece)
```

### RF4: Reativação da GPU
**Opção 1: Manual (UI)**
- Botão "Wake Up" na dashboard
- Mostra tempo estimado: "~2 min para criar instância + ~5 min restore"
- Seleciona GPU type/região

**Opção 2: Automática (API)**
- Middleware detecta requisição para instância hibernada
- Acorda automaticamente em background
- Retorna 503 "Waking up... try again in 2 min"

**Opção 3: Agendada (Cron)**
- UI permite configurar horários: "Acordar todo dia 9h, pausar 18h"
- Cron job no servidor

### RF5: Configuração por Usuário
```json
{
  "auto_hibernation": {
    "enabled": true,              // Padrão: true
    "pause_after_idle_minutes": 3,
    "delete_after_pause_minutes": 30,
    "gpu_usage_threshold": 5,     // %
    "check_interval_seconds": 30,
    "wake_method": "manual",      // "manual", "auto", "scheduled"
    "schedule": {
      "wake_time": "09:00",
      "sleep_time": "18:00",
      "timezone": "America/Sao_Paulo"
    }
  }
}
```

## 🏗️ Arquitetura

### Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                     Control Plane (VPS)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐      ┌──────────────────┐               │
│  │ AutoHibernation  │      │   Flask API      │               │
│  │     Manager      │◄─────│  /api/instances  │               │
│  └──────────────────┘      │  /wake           │               │
│           │                 └──────────────────┘               │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────┐      ┌──────────────────┐               │
│  │ GPUSnapshot      │      │   VastService    │               │
│  │   Service        │      │  (create/destroy)│               │
│  └──────────────────┘      └──────────────────┘               │
│           │                          │                          │
│           ▼                          ▼                          │
│  ┌─────────────────────────────────────────┐                  │
│  │         Cloudflare R2 Storage           │                  │
│  └─────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ Status updates via /api/agent/status
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Plane (GPU Instance)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐                                          │
│  │   DumontAgent    │  (roda na GPU)                           │
│  │  (GPU Monitor)   │                                          │
│  └──────────────────┘                                          │
│           │                                                     │
│           ├─► nvidia-smi (a cada 30s)                          │
│           ├─► Envia status: {gpu_util: 2%, status: "idle"}    │
│           └─► Aguarda comando de hibernação                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

**1. Monitoramento (loop contínuo)**
```
GPU Instance → nvidia-smi → DumontAgent → POST /api/agent/status
                                              ↓
                              AutoHibernationManager (verifica)
                                              ↓
                              Se ociosa > 3min: trigger hibernação
```

**2. Hibernação**
```
AutoHibernationManager
  ├─► GPUSnapshotService.create_snapshot()
  │     ├─► SSH para GPU
  │     ├─► Comprimir com ANS (32 partes)
  │     └─► Upload para R2
  │
  ├─► VastService.destroy_instance()
  │
  └─► DB: instance_status = "hibernated"
          hibernated_at = timestamp
          snapshot_id = "..."
```

**3. Reativação Manual**
```
User → Clica "Wake" na UI
  ↓
POST /api/instances/{id}/wake
  ↓
AutoHibernationManager.wake_instance()
  ├─► VastService.create_instance() (nova GPU)
  │     └─► Aguarda ficar ready (1-2 min)
  │
  ├─► GPUSnapshotService.restore_snapshot()
  │     ├─► Download 32 partes do R2
  │     └─► Descomprimir com ANS
  │
  └─► DB: instance_status = "running"
```

## 📦 Implementação

### Novos Arquivos

#### 1. `src/services/auto_hibernation_manager.py`
```python
class AutoHibernationManager(Agent):
    """
    Gerencia auto-hibernação de instâncias GPU.
    Roda como agente em background no VPS.
    """

    def __init__(self, vast_api_key, snapshot_service, config):
        # Inicialização

    def run(self):
        # Loop principal: verifica status de todas as instâncias
        while self.running:
            self._check_all_instances()
            self.sleep(30)  # Verifica a cada 30s

    def _check_all_instances(self):
        # Para cada instância ativa:
        # 1. Obter último status do DumontAgent
        # 2. Verificar se está ociosa
        # 3. Se ociosa > 3min: hibernar
        # 4. Se hibernada > 30min: deletar

    def hibernate_instance(self, instance_id):
        # 1. Criar snapshot
        # 2. Destruir instância vast.ai
        # 3. Atualizar DB

    def wake_instance(self, instance_id, gpu_type, region):
        # 1. Criar nova instância
        # 2. Aguardar ficar ready
        # 3. Restaurar snapshot
        # 4. Atualizar DB

    def check_scheduled_wake(self):
        # Verifica se há instâncias agendadas para acordar
```

#### 2. `src/services/gpu_monitor_agent.py` (roda NA GPU)
```python
class GPUMonitorAgent:
    """
    Agente que roda DENTRO da instância GPU.
    Monitora uso e envia status para o VPS.
    """

    def __init__(self, instance_id, control_plane_url):
        # Inicialização

    def run(self):
        # Loop principal
        while True:
            gpu_util = self.get_gpu_utilization()
            self.send_status(gpu_util)
            time.sleep(30)

    def get_gpu_utilization(self):
        # nvidia-smi --query-gpu=utilization.gpu
        # Retorna % de uso

    def send_status(self, gpu_util):
        # POST para /api/agent/status
        # {instance_id, gpu_util, timestamp}
```

#### 3. `src/models/instance_status.py` (novo modelo DB)
```python
class InstanceStatus(Base):
    """Armazena status e histórico de instâncias"""

    __tablename__ = "instance_status"

    id = Column(Integer, primary_key=True)
    instance_id = Column(String(100), unique=True, index=True)
    user_id = Column(String(100), index=True)

    # Status atual
    status = Column(String(50))  # "running", "idle", "hibernated", "deleted"
    gpu_utilization = Column(Float)  # %
    last_activity = Column(DateTime)

    # Hibernação
    idle_since = Column(DateTime, nullable=True)
    hibernated_at = Column(DateTime, nullable=True)
    snapshot_id = Column(String(200), nullable=True)

    # Auto-hibernation config
    auto_hibernation_enabled = Column(Boolean, default=True)
    pause_after_minutes = Column(Integer, default=3)
    delete_after_minutes = Column(Integer, default=30)

    # Vast.ai info
    vast_instance_id = Column(Integer, nullable=True)
    gpu_type = Column(String(100))
    region = Column(String(100))
```

#### 4. `src/api/hibernation.py` (novos endpoints)
```python
@hibernation_bp.route('/api/instances/<instance_id>/wake', methods=['POST'])
def wake_instance(instance_id):
    """Acorda instância hibernada"""
    # Chama AutoHibernationManager.wake_instance()

@hibernation_bp.route('/api/instances/<instance_id>/config', methods=['PUT'])
def update_hibernation_config(instance_id):
    """Atualiza config de auto-hibernação"""
    # pause_after_minutes, delete_after_minutes, enabled

@hibernation_bp.route('/api/instances/<instance_id>/schedule', methods=['PUT'])
def set_wake_schedule(instance_id):
    """Define agendamento wake/sleep"""
    # wake_time, sleep_time, timezone
```

### Modificações em Arquivos Existentes

#### `app.py`
- Registrar `hibernation_bp`
- Inicializar `AutoHibernationManager` no startup
- Registrar agente no `agent_manager`

#### `src/api/instances.py`
- Adicionar campo `auto_hibernation_config` na resposta
- Adicionar indicador visual se está hibernada

#### `web/src/pages/Machines.jsx`
- Botão "Wake Up" para instâncias hibernadas
- Indicador de status: "Running", "Idle", "Hibernated", "Deleted"
- Progress bar durante wake/restore
- Config de auto-hibernação (modal)

## 🗄️ Banco de Dados

### Nova Tabela: `instance_status`
```sql
CREATE TABLE instance_status (
    id INTEGER PRIMARY KEY,
    instance_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,

    -- Status
    status VARCHAR(50) NOT NULL,
    gpu_utilization FLOAT,
    last_activity DATETIME,

    -- Hibernation
    idle_since DATETIME,
    hibernated_at DATETIME,
    snapshot_id VARCHAR(200),

    -- Config
    auto_hibernation_enabled BOOLEAN DEFAULT TRUE,
    pause_after_minutes INTEGER DEFAULT 3,
    delete_after_minutes INTEGER DEFAULT 30,

    -- Vast info
    vast_instance_id INTEGER,
    gpu_type VARCHAR(100),
    region VARCHAR(100),

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_instance_status ON instance_status(instance_id);
CREATE INDEX idx_user_status ON instance_status(user_id, status);
```

### Nova Tabela: `hibernation_events`
```sql
CREATE TABLE hibernation_events (
    id INTEGER PRIMARY KEY,
    instance_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- "idle_detected", "hibernated", "woke_up", "deleted"
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Metadata
    gpu_utilization FLOAT,
    snapshot_id VARCHAR(200),
    reason VARCHAR(500),

    FOREIGN KEY (instance_id) REFERENCES instance_status(instance_id)
);

CREATE INDEX idx_hibernation_events ON hibernation_events(instance_id, timestamp);
```

## 🔄 Fluxo Completo

### Cenário 1: GPU para de ser usada

```
T=0:00  │ GPU em uso (95% utilização)
        │ Status: "running"
        │
T=0:30  │ GPU ociosa (2% utilização)
        │ DumontAgent → POST /api/agent/status {gpu_util: 2%}
        │ AutoHibernationManager: marca idle_since = T=0:30
        │ Status: "idle"
        │
T=1:00  │ Ainda ociosa (1% utilização)
        │ AutoHibernationManager: verifica... ainda < 3 min
        │
T=3:30  │ Ainda ociosa (0% utilização)
        │ AutoHibernationManager: ociosa > 3 min → HIBERNAR!
        │ ├─► Criar snapshot ANS (~20s para 6GB)
        │ ├─► Destruir instância vast.ai
        │ └─► DB: status = "hibernated", snapshot_id = "..."
        │ Status: "hibernated"
        │
T=33:30 │ Hibernada há 30 min
        │ AutoHibernationManager: verifica snapshot existe no R2
        │ ├─► Snapshot confirmado
        │ └─► DB: status = "deleted"
        │ Status: "deleted" (snapshot permanece no R2)
```

### Cenário 2: Usuário acorda GPU

```
T=0:00  │ Status: "hibernated"
        │ Snapshot: "qwen_snapshot_123" no R2
        │
        │ User clica "Wake Up" na UI
        │ └─► POST /api/instances/12345/wake
        │       {gpu_type: "RTX 3090", region: "EU"}
        │
T=0:01  │ AutoHibernationManager.wake_instance()
        │ ├─► VastService.create_instance()
        │ │     └─► Buscar ofertas RTX 3090 EU
        │ │     └─► Criar instância
        │ └─► Status: "waking"
        │
T=1:30  │ Instância vast.ai pronta (SSH ativo)
        │ AutoHibernationManager
        │ └─► GPUSnapshotService.restore_snapshot()
        │       ├─► Download 32 partes R2 (~10s)
        │       └─► Descomprimir ANS (~0.1s)
        │       └─► Extrair para /workspace
        │
T=1:45  │ Restore completo!
        │ ├─► Iniciar DumontAgent na nova instância
        │ └─► DB: status = "running"
        │ Status: "running"
```

## 📊 Economia Estimada

### Workspace 70GB, RTX 5090 @ $1.50/h

**Sem auto-hibernação:**
- 24h/dia = $36/dia = $1,080/mês
- Uso real: 6h/dia
- Desperdício: 18h/dia ociosa = $27/dia = $810/mês

**Com auto-hibernação:**
- Uso ativo: 6h/dia = $9/dia
- Snapshot storage: $0.01/mês
- **Total: ~$270/mês**
- **Economia: $810/mês (75%)**

### Workspace 6GB, RTX 3090 @ $0.30/h

**Sem auto-hibernação:**
- 24h/dia = $7.20/dia = $216/mês

**Com auto-hibernação:**
- Uso ativo: 4h/dia = $1.20/dia
- Snapshot: $0.001/mês
- **Total: ~$36/mês**
- **Economia: $180/mês (83%)**

## 🧪 Testes

### Teste 1: Monitoramento
- Criar instância GPU
- Instalar DumontAgent
- Verificar que envia status a cada 30s
- Simular carga GPU (torch.cuda random ops)
- Verificar que detecta uso > 5%

### Teste 2: Auto-Hibernação
- GPU ociosa por 3 min
- Verificar que cria snapshot
- Verificar que destroi instância
- Verificar snapshot no R2

### Teste 3: Wake Manual
- Instância hibernada
- Clicar "Wake"
- Verificar criação nova instância
- Verificar restore do snapshot
- Verificar workspace intacto

### Teste 4: Agendamento
- Configurar wake 09:00, sleep 18:00
- Simular timezone America/Sao_Paulo
- Verificar que acorda no horário
- Verificar que hiberna no horário

## ⚠️ Considerações

### Limitações
1. **Tempo de wake**: 1-2 min criar instância + 5 min restore (70GB)
2. **Custo R2**: ~$0.01/mês por snapshot 70GB
3. **Disponibilidade GPU**: Pode não haver GPUs disponíveis ao acordar

### Mitigações
1. **Cache local**: Manter snapshot na sync machine para restore rápido
2. **Multi-região**: Tentar regiões alternativas se não houver GPU
3. **Notificação**: Avisar se wake falhar por falta de GPUs

### Segurança
1. **DumontAgent authentication**: Token JWT para enviar status
2. **Rate limiting**: Max 1 wake request por minuto
3. **Validação**: Verificar ownership antes de wake/hibernate

## 📅 Cronograma de Implementação

### Fase 1: Core (2-3 horas)
- [ ] Criar `AutoHibernationManager`
- [ ] Criar `GPUMonitorAgent`
- [ ] Criar modelos DB
- [ ] Endpoints API básicos

### Fase 2: Integração (1-2 horas)
- [ ] Integrar com GPUSnapshotService
- [ ] Integrar com VastService
- [ ] Registrar agente no agent_manager
- [ ] Testes unitários

### Fase 3: UI (1 hora)
- [ ] Botão "Wake" na dashboard
- [ ] Indicadores de status
- [ ] Modal de configuração
- [ ] Progress bar de wake/restore

### Fase 4: Features Avançadas (1-2 horas)
- [ ] Agendamento (cron)
- [ ] Wake automático via API
- [ ] Múltiplas políticas (por GPU type)
- [ ] Dashboard de economia

**Total estimado: 5-8 horas**

## ✅ Critérios de Sucesso

1. ✅ GPU ociosa por 3 min → hibernada automaticamente
2. ✅ Snapshot criado e salvo no R2
3. ✅ Instância destruída (custo = $0)
4. ✅ Wake manual funciona em < 7 min
5. ✅ Workspace restaurado 100% intacto
6. ✅ Economia > 70% em testes reais
7. ✅ Zero intervenção manual necessária

---

**Status**: ✅ Plano Completo - Pronto para Aprovação
**Próximo Passo**: Aguardar aprovação do usuário para iniciar implementação
