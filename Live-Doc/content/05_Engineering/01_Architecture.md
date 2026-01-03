# Arquitetura do Sistema

## Visao Geral

O Dumont Cloud e construido com arquitetura Clean/DDD, focada em resiliencia, escalabilidade e baixo custo.

---

## Diagrama de Alto Nivel

```mermaid
graph TB
    subgraph Frontend
        A[React Dashboard]
        B[Deploy Wizard]
    end

    subgraph Backend
        C[FastAPI]
        D[Domain Services]
        E[Background Jobs]
    end

    subgraph Modules
        F[Failover]
        G[Hibernation]
        H[Serverless]
        I[Market]
    end

    subgraph Providers
        J[VAST.ai]
        K[TensorDock]
        L[GCP]
    end

    subgraph Storage
        M[PostgreSQL]
        N[Cloudflare R2]
    end

    A --> C
    B --> C
    C --> D
    D --> F
    D --> G
    D --> H
    D --> I
    F --> J
    F --> K
    F --> L
    D --> M
    D --> N
```

---

## Estrutura do Projeto

```
dumontcloud/
├── src/                    # Backend FastAPI
│   ├── main.py             # App factory
│   ├── api/v1/             # 38 endpoints
│   ├── core/               # Config, security
│   ├── domain/             # DDD layer
│   ├── models/             # 29 SQLAlchemy models
│   ├── services/           # 58+ services
│   ├── modules/            # 14 feature modules
│   └── infrastructure/     # Providers
│
├── web/                    # Frontend React
│   ├── src/pages/          # 29+ pages
│   ├── src/components/     # 118+ components
│   └── src/api/            # API client
│
├── tests/                  # 73+ test files
├── migrations/             # Alembic
└── Live-Doc/               # Esta documentacao
```

---

## Backend Stack

| Componente | Tecnologia |
|------------|------------|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| Validation | Pydantic 2 |
| Auth | JWT + OIDC + SAML |
| Scheduler | APScheduler |
| Storage | Cloudflare R2 |
| Backup | Restic |

---

## Frontend Stack

| Componente | Tecnologia |
|------------|------------|
| Framework | React 18 |
| Build | Vite 5 |
| Styling | Tailwind CSS |
| State | Redux Toolkit |
| Charts | ApexCharts |
| Testing | Playwright |

---

## Modulos Principais

### 1. Failover
Orquestracao de failover GPU -> Warm Pool -> CPU

### 2. Hibernation
Auto-pause de instancias ociosas

### 3. Serverless
Resume sob demanda

### 4. Market
Monitoramento e predicao de precos

### 5. Warmpool
Pool de GPUs pre-alocadas

---

## Fluxo de Failover

```mermaid
sequenceDiagram
    Agent->>Monitor: Heartbeat
    Note over Agent: GPU Falha
    Agent--xMonitor: Heartbeat falhou
    Monitor->>WarmPool: Busca GPU
    alt GPU disponivel
        WarmPool->>R2: Restaura snapshot
        WarmPool->>User: GPU pronta (30s)
    else Pool vazio
        Monitor->>GCP: Ativa CPU
        GCP->>R2: Restaura dados
        GCP->>User: CPU pronta (3min)
    end
```

---

## Banco de Dados

### Principais Tabelas

- `users` - Contas
- `teams` / `roles` / `permissions` - RBAC
- `instances` / `instance_status` - Maquinas
- `snapshots` - Backups
- `machine_history` - Reliability
- `price_history` - Precos

---

## Seguranca

- JWT com rotacao
- OIDC / SAML SSO
- API Keys com scopes
- Criptografia AES-256
- Audit logging
