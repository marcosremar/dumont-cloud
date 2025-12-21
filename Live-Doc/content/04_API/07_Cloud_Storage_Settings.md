# Cloud Storage Settings API

Endpoints para configurar cloud storage para snapshots e failover.

## Visão Geral

O Dumont Cloud suporta múltiplos provedores de cloud storage para armazenar snapshots:

| Provider | Descrição | Custo Estimado |
|----------|-----------|----------------|
| Backblaze B2 | Mais barato, boa performance | $0.005/GB/mês |
| AWS S3 | Maior disponibilidade | $0.023/GB/mês |
| Google GCS | Integração com GCP | $0.020/GB/mês |
| Cloudflare R2 | Sem egress fees | $0.015/GB/mês |

---

## Endpoints

### GET /settings/cloud-storage

Retorna configurações de cloud storage para failover.

**Response:**
```json
{
  "provider": "backblaze_b2",
  "bucket_name": "dumont-snapshots",
  "region": "us-west-004",
  "endpoint": "s3.us-west-004.backblazeb2.com",
  "configured": true,
  "last_test": "2024-12-20T15:30:00Z",
  "last_test_success": true,
  "stats": {
    "total_snapshots": 45,
    "total_size_gb": 120.5,
    "last_snapshot": "2024-12-20T15:00:00Z"
  }
}
```

**Exemplo curl:**
```bash
curl https://api.dumontcloud.com/api/v1/settings/cloud-storage \
  -H "Authorization: Bearer $API_KEY"
```

---

### PUT /settings/cloud-storage

Atualiza configurações de cloud storage.

**Request (Backblaze B2):**
```json
{
  "provider": "backblaze_b2",
  "bucket_name": "my-dumont-snapshots",
  "key_id": "004xxxxxxxxxxxx",
  "application_key": "K004xxxxxxxxxxxxxxxxxxxxxxxxx",
  "region": "us-west-004"
}
```

**Request (AWS S3):**
```json
{
  "provider": "aws_s3",
  "bucket_name": "my-dumont-snapshots",
  "access_key_id": "AKIAXXXXXXXXXXXXXXXX",
  "secret_access_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "region": "us-west-2"
}
```

**Request (Google GCS):**
```json
{
  "provider": "google_gcs",
  "bucket_name": "my-dumont-snapshots",
  "service_account_json": "{...}",
  "region": "us-central1"
}
```

**Request (Cloudflare R2):**
```json
{
  "provider": "cloudflare_r2",
  "bucket_name": "my-dumont-snapshots",
  "account_id": "xxxxxxxxxxxxxxxxxxxx",
  "access_key_id": "xxxxxxxxxxxxxxxxxxxx",
  "secret_access_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Cloud storage configured successfully",
  "provider": "backblaze_b2",
  "bucket_name": "my-dumont-snapshots"
}
```

**Exemplo curl:**
```bash
curl -X PUT https://api.dumontcloud.com/api/v1/settings/cloud-storage \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "backblaze_b2",
    "bucket_name": "my-dumont-snapshots",
    "key_id": "004xxxxxxxxxxxx",
    "application_key": "K004xxxxxxxxxxxxxxxxxxxxxxxxx"
  }'
```

---

### POST /settings/cloud-storage/test

Testa conexão com cloud storage.

**Response (sucesso):**
```json
{
  "success": true,
  "message": "Connection successful",
  "latency_ms": 45,
  "bucket_accessible": true,
  "write_permission": true,
  "read_permission": true,
  "delete_permission": true
}
```

**Response (falha):**
```json
{
  "success": false,
  "message": "Connection failed",
  "error": "Invalid credentials",
  "details": "The provided key_id is not valid"
}
```

**Exemplo curl:**
```bash
curl -X POST https://api.dumontcloud.com/api/v1/settings/cloud-storage/test \
  -H "Authorization: Bearer $API_KEY"
```

---

## Configuração por Provider

### Backblaze B2 (Recomendado)

1. Crie uma conta em [backblaze.com](https://www.backblaze.com)
2. Crie um bucket B2
3. Gere Application Key com permissões de leitura/escrita
4. Configure no Dumont Cloud

```json
{
  "provider": "backblaze_b2",
  "bucket_name": "seu-bucket",
  "key_id": "004xxxxxxxxxx",
  "application_key": "K004xxxxxxxxxxxxxx",
  "region": "us-west-004"
}
```

### AWS S3

1. Crie um bucket S3
2. Crie um IAM user com política:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
    "Resource": ["arn:aws:s3:::seu-bucket", "arn:aws:s3:::seu-bucket/*"]
  }]
}
```

### Google GCS

1. Crie um bucket GCS
2. Crie uma Service Account com role `Storage Object Admin`
3. Gere uma chave JSON

### Cloudflare R2

1. Crie um bucket R2 no dashboard Cloudflare
2. Gere API tokens com permissões R2

---

## Integração com Failover

O cloud storage é usado automaticamente para:

1. **Snapshots automáticos** - A cada 30 segundos (configurável)
2. **Failover CPU Standby** - Download do snapshot para nova GPU
3. **Disaster Recovery** - Restauração após falha total

```mermaid
graph LR
    GPU[GPU Principal] -->|Sync| CS[Cloud Storage]
    CS -->|Restore| CPU[CPU Standby]
    CPU -->|Deploy| GPU2[Nova GPU]
```

---

## Troubleshooting

### "Invalid credentials"
- Verifique key_id e application_key
- Confirme que a key tem permissões de escrita

### "Bucket not found"
- Verifique o nome do bucket
- Confirme a região correta

### Upload lento
- Considere usar região mais próxima das GPUs
- Cloudflare R2 tem boa performance global
