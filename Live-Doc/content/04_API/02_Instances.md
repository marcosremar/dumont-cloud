# API de Instancias

## Listar Instancias

```http
GET /api/v1/instances
```

### Query Parameters

| Param | Tipo | Descricao |
|-------|------|-----------|
| status | string | Filtrar por status |
| gpu_type | string | Filtrar por GPU |
| page | int | Pagina (default: 1) |
| per_page | int | Items por pagina |

### Response

```json
{
  "data": [
    {
      "id": "inst_abc123",
      "gpu_type": "RTX_4090",
      "status": "running",
      "ip_address": "203.0.113.50",
      "ssh_port": 22,
      "created_at": "2024-01-15T10:00:00Z",
      "cost_per_hour": 0.40,
      "region": "us-west"
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 5
  }
}
```

---

## Criar Instancia

```http
POST /api/v1/instances
```

### Request Body

```json
{
  "gpu_type": "RTX_4090",
  "region": "us-west",
  "image": "pytorch/pytorch:2.0-cuda12.1",
  "disk_gb": 100,
  "failover_enabled": true,
  "failover_strategy": "warmpool",
  "ssh_key": "ssh-rsa AAAA..."
}
```

### Response

```json
{
  "id": "inst_abc123",
  "status": "starting",
  "estimated_ready_seconds": 60
}
```

---

## Obter Instancia

```http
GET /api/v1/instances/{id}
```

### Response

```json
{
  "id": "inst_abc123",
  "gpu_type": "RTX_4090",
  "gpu_name": "NVIDIA GeForce RTX 4090",
  "gpu_memory_gb": 24,
  "status": "running",
  "ip_address": "203.0.113.50",
  "ssh_port": 22,
  "ssh_command": "ssh -p 22 root@203.0.113.50",
  "jupyter_url": "https://inst_abc123.dumontcloud.com:8888",
  "created_at": "2024-01-15T10:00:00Z",
  "uptime_seconds": 3600,
  "cost_per_hour": 0.40,
  "cost_accumulated": 0.40,
  "region": "us-west",
  "host_reliability_score": 4.5,
  "failover": {
    "enabled": true,
    "strategy": "warmpool",
    "last_failover": null
  },
  "serverless": {
    "enabled": true,
    "idle_timeout_minutes": 15,
    "state": "active"
  },
  "metrics": {
    "gpu_utilization": 45,
    "gpu_memory_used_gb": 12,
    "gpu_temperature": 65
  }
}
```

---

## Acoes

### Iniciar

```http
POST /api/v1/instances/{id}/start
```

### Parar

```http
POST /api/v1/instances/{id}/stop
```

### Reiniciar

```http
POST /api/v1/instances/{id}/reboot
```

### Destruir

```http
DELETE /api/v1/instances/{id}
```

---

## Metricas

```http
GET /api/v1/instances/{id}/metrics
```

### Query Parameters

| Param | Tipo | Descricao |
|-------|------|-----------|
| period | string | 1h, 24h, 7d, 30d |
| metrics | string | gpu_util,gpu_mem,cpu,ram |

### Response

```json
{
  "instance_id": "inst_abc123",
  "period": "24h",
  "data": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "gpu_utilization": 45,
      "gpu_memory_used_gb": 12,
      "cpu_utilization": 20,
      "ram_used_gb": 8
    }
  ]
}
```

---

## SSH Keys

### Adicionar SSH Key

```http
POST /api/v1/instances/{id}/ssh-keys
```

```json
{
  "name": "my-laptop",
  "public_key": "ssh-rsa AAAA..."
}
```

### Listar SSH Keys

```http
GET /api/v1/instances/{id}/ssh-keys
```

### Remover SSH Key

```http
DELETE /api/v1/instances/{id}/ssh-keys/{key_id}
```

---

## Logs

```http
GET /api/v1/instances/{id}/logs
```

### Query Parameters

| Param | Tipo | Descricao |
|-------|------|-----------|
| lines | int | Ultimas N linhas |
| since | datetime | Desde timestamp |

---

## Eventos

```http
GET /api/v1/instances/{id}/events
```

### Response

```json
{
  "events": [
    {
      "type": "instance.created",
      "timestamp": "2024-01-15T10:00:00Z",
      "details": {}
    },
    {
      "type": "instance.started",
      "timestamp": "2024-01-15T10:01:00Z",
      "details": {}
    }
  ]
}
```
