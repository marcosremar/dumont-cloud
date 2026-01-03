# API Overview

## Introducao

A API do Dumont Cloud e RESTful e usa JSON para requests e responses. Autenticacao via JWT Bearer token ou API Key.

**Base URL**: `https://api.dumontcloud.com/api/v1`

---

## Autenticacao

### JWT Token

```bash
# Login
curl -X POST /api/v1/auth/login \
  -d '{"email": "user@example.com", "password": "xxx"}'

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}

# Usar token
curl -H "Authorization: Bearer eyJ..." /api/v1/instances
```

### API Key

```bash
curl -H "X-API-Key: your_api_key" /api/v1/instances
```

---

## Endpoints Principais

### Instancias

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/instances` | Listar instancias |
| POST | `/instances` | Criar instancia |
| GET | `/instances/{id}` | Detalhes |
| DELETE | `/instances/{id}` | Destruir |
| POST | `/instances/{id}/start` | Iniciar |
| POST | `/instances/{id}/stop` | Parar |
| POST | `/instances/{id}/reboot` | Reiniciar |

### Snapshots

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/snapshots` | Listar snapshots |
| POST | `/snapshots` | Criar snapshot |
| GET | `/snapshots/{id}` | Detalhes |
| DELETE | `/snapshots/{id}` | Deletar |
| POST | `/snapshots/{id}/restore` | Restaurar |

### Failover

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/failover/status/{id}` | Status failover |
| POST | `/failover/configure` | Configurar |
| POST | `/failover/trigger/{id}` | Forcar failover |

### Serverless

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/serverless/enable` | Habilitar |
| POST | `/serverless/disable` | Desabilitar |
| GET | `/serverless/status/{id}` | Status |
| POST | `/serverless/pause/{id}` | Pausar |
| POST | `/serverless/resume/{id}` | Resumir |

### Market

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/market/prices` | Precos atuais |
| GET | `/market/history` | Historico |
| GET | `/market/predictions` | Predicoes |

### Teams & RBAC

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/teams` | Listar teams |
| POST | `/teams` | Criar team |
| POST | `/teams/{id}/members` | Adicionar membro |
| GET | `/roles` | Listar roles |
| POST | `/roles` | Criar role |

---

## Formato de Resposta

### Sucesso

```json
{
  "data": {...},
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 100
  }
}
```

### Erro

```json
{
  "error": {
    "code": "INSTANCE_NOT_FOUND",
    "message": "Instance not found",
    "details": {...}
  }
}
```

---

## Codigos de Status

| Codigo | Significado |
|--------|-------------|
| 200 | OK |
| 201 | Criado |
| 400 | Bad Request |
| 401 | Nao autenticado |
| 403 | Sem permissao |
| 404 | Nao encontrado |
| 429 | Rate limit |
| 500 | Erro interno |

---

## Rate Limits

| Plano | Requests/min |
|-------|--------------|
| Free | 60 |
| Pro | 300 |
| Enterprise | 1000 |

Header de resposta:
```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 299
X-RateLimit-Reset: 1640000000
```

---

## Paginacao

```bash
curl /api/v1/instances?page=2&per_page=50
```

---

## SDKs

### Python

```python
from dumont import DumontClient

client = DumontClient(api_key="your_key")
instances = client.instances.list()
```

### JavaScript

```javascript
import { Dumont } from 'dumont-sdk';

const client = new Dumont({ apiKey: 'your_key' });
const instances = await client.instances.list();
```

---

## Webhooks

Configure webhooks para receber eventos:

```bash
curl -X POST /api/v1/webhooks \
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["instance.created", "failover.completed"]
  }'
```
