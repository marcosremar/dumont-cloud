# Failover Tests - Phases 3 & 4

Testes de integração REAIS para hibernação e stress testing do Dumont Cloud.

**IMPORTANTE:** Estes testes usam créditos REAIS da VAST.ai e Backblaze B2.

## Estrutura dos Testes

### Phase 3: Hibernation & Cost Optimization

#### Test 3.1: Auto-Hibernation
**Arquivo:** `test_auto_hibernation.py`

**O que testa:**
- Provisionamento de GPU real
- Criação de arquivos de teste
- Simulação de período idle (60s)
- Trigger de auto-hibernation:
  - Criação de snapshot
  - Upload para B2
  - Destruição da GPU
- Verificação de snapshot no B2

**Custo estimado:** ~$0.15-0.30 por execução

**Como executar:**
```bash
cd /Users/marcos/CascadeProjects/dumontcloud
source venv/bin/activate
pytest cli/tests/test_auto_hibernation.py -v -s --tb=short
```

**Métricas coletadas:**
- Tempo de provisionamento
- Tempo de criação de arquivos
- Tempo de idle wait
- Tempo de snapshot
- Tempo de destruição
- Custo total estimado
- Validação de snapshot no B2

---

#### Test 3.2: Wake from Hibernation
**Arquivo:** `test_wake_hibernation.py`

**O que testa:**
- Busca de snapshot hibernado mais recente
- Provisionamento de nova GPU
- Download e restore do snapshot
- Validação de arquivos restaurados (MD5)
- Medição de tempo de "wake up"

**Pré-requisito:** Execute `test_auto_hibernation.py` primeiro para criar snapshot

**Custo estimado:** ~$0.15-0.30 por execução

**Como executar:**
```bash
pytest cli/tests/test_wake_hibernation.py -v -s --tb=short
```

**Métricas coletadas:**
- Tempo para encontrar snapshot
- Tempo de provisionamento
- Tempo de restore
- Tempo de validação
- **WAKE UP TIME total** (provision + restore)
- Taxa de sucesso de validação de arquivos

---

### Phase 4: Stress Testing

#### Test 4.1: Large Model Snapshot
**Arquivo:** `test_large_snapshot.py`

**O que testa:**
- Criação de arquivo grande (1GB - simula modelo LLM)
- Cálculo de MD5 do arquivo original
- Snapshot comprimido
- Upload para B2 com medição de velocidade
- Provisionamento de nova GPU
- Download do snapshot com medição de velocidade
- Validação de MD5 do arquivo restaurado

**Custo estimado:** ~$0.50-1.00 por execução (2 GPUs + tempo de transfer)

**Como executar (APENAS com flag --real):**
```bash
pytest cli/tests/test_large_snapshot.py -v -s --real
```

**Métricas coletadas:**
- Tempo de criação do arquivo grande
- Tempo de snapshot
- **Upload speed (Mbps)**
- **Download speed (Mbps)**
- Compression ratio
- Validação de MD5 (integridade)
- Custo total (2 GPUs)

---

#### Test 4.2: Multiple Failovers (5x)
**Arquivo:** `test_multiple_failovers.py`

**O que testa:**
- Criação de arquivos iniciais
- Loop de 5 ciclos de failover:
  - Snapshot
  - Destruição de GPU
  - Provisionamento de nova GPU
  - Restore
  - Validação de arquivos
- Cálculo de estatísticas agregadas

**Custo estimado:** ~$1.50-3.00 por execução (6 GPUs total)

**Como executar (APENAS com flag --real):**
```bash
pytest cli/tests/test_multiple_failovers.py -v -s --real
```

**Métricas coletadas:**
- Taxa de sucesso (deve ser 100%)
- Tempo médio por failover
- Tempo mínimo/máximo
- Desvio padrão
- Custo total acumulado
- Validação de integridade em cada ciclo

---

## Configuração

### Variáveis de Ambiente

Todas as credenciais estão em `/Users/marcos/CascadeProjects/dumontcloud/.env`:

```bash
# VAST.ai
VAST_API_KEY=a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd

# Backblaze B2
B2_KEY_ID=a1ef6268a3f3
B2_APPLICATION_KEY=003b33c7f73d94db9f5ab15ca33afb747ebc3c6dc3
B2_BUCKET=dumontcloud-snapshots
B2_ENDPOINT=s3.us-west-000.backblazeb2.com

# Dumont API
DUMONT_API_URL=http://localhost:8766
```

### Autenticação

Todos os testes usam credenciais demo:
- Email: `test@test.com`
- Password: `test123`

---

## Ordem de Execução Recomendada

### 1. Testes Rápidos (Phase 3)

Executar primeiro para validar funcionamento básico:

```bash
# Test 3.1: Auto-Hibernation (rápido, ~5-10 min)
pytest cli/tests/test_auto_hibernation.py -v -s --tb=short

# Test 3.2: Wake from Hibernation (rápido, ~5-10 min)
pytest cli/tests/test_wake_hibernation.py -v -s --tb=short
```

**Custo total Phase 3:** ~$0.30-0.60

---

### 2. Testes de Stress (Phase 4)

Executar apenas se Phase 3 passou com sucesso:

```bash
# Test 4.1: Large Model Snapshot (médio, ~15-30 min)
pytest cli/tests/test_large_snapshot.py -v -s --real

# Test 4.2: Multiple Failovers (longo, ~30-60 min)
pytest cli/tests/test_multiple_failovers.py -v -s --real
```

**Custo total Phase 4:** ~$2.00-4.00

---

## Timeouts Configurados

| Operação | Timeout | Comentário |
|----------|---------|------------|
| Instance Create | 300s (5 min) | Criar instância na VAST.ai |
| Instance Ready | 600s (10 min) | Aguardar running + SSH |
| Snapshot Create | 300s (5 min) | Snapshot pequeno |
| Snapshot Create (1GB) | 1200s (20 min) | Snapshot grande |
| Restore | 600s (10 min) | Restore padrão |
| Restore (1GB) | 1200s (20 min) | Restore grande |
| Idle Wait | 60s | Simulação de idle (produção: 180s) |

---

## Rate Limiting VAST.ai

Todos os testes implementam retry com backoff exponencial:

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        response = requests.post(...)
        if response.status_code == 429:
            wait_time = 2 ** attempt  # 2s, 4s, 8s
            time.sleep(wait_time)
            continue
        return response
    except:
        time.sleep(2 ** attempt)
```

---

## Relatórios Gerados

Cada teste gera:

### 1. Saída no console (tempo real)
```
======================================================================
TESTE 3.1: AUTO-HIBERNATION
======================================================================

[1/5] Provisionando GPU...
   GPU: RTX A4000
   Preço: $0.3200/hr
   Instance ID: 29070710
   SSH: 123.45.67.89:22
   Tempo: 145.3s
   ✓ GPU provisionada com sucesso

[2/5] Criando arquivos de teste...
   Created: /workspace/auto-hibernation-test-1.txt (245 bytes, MD5: a3f5c8d2...)
   ...

======================================================================
RELATÓRIO: AUTO-HIBERNATION TEST
======================================================================
...
```

### 2. Arquivo JSON
```
/tmp/auto_hibernation_report_1735840123.json
/tmp/wake_hibernation_report_1735840456.json
/tmp/large_snapshot_report_1735840789.json
/tmp/multiple_failovers_report_1735841012.json
```

Estrutura do JSON:
```json
{
  "test_name": "auto_hibernation",
  "timestamp": "2025-01-02T15:30:45",
  "resources": {
    "instance_id": "29070710",
    "snapshot_id": "abc123",
    "test_files_count": 5
  },
  "timings": {
    "provision_sec": 145.3,
    "create_files_sec": 12.5,
    "idle_wait_sec": 60.0,
    "snapshot_sec": 78.2,
    "destroy_sec": 5.1,
    "total_sec": 301.1,
    "total_min": 5.02
  },
  "cost": {
    "gpu_hourly_usd": 0.32,
    "estimated_total_usd": 0.027
  },
  "validation": {
    "success": true,
    "snapshot_exists_in_b2": true,
    "error": null
  }
}
```

---

## Cleanup Automático

Todos os testes garantem cleanup de recursos:

```python
def test_99_cleanup(self, auth_token, metrics):
    """Cleanup: deleta GPUs criadas"""
    if metrics.instance_id:
        call_api("DELETE", f"/api/v1/instances/{metrics.instance_id}", token=auth_token)
```

Mesmo se teste falhar, pytest fixtures garantem cleanup no teardown.

---

## Troubleshooting

### Erro: "No GPU offers available"
**Solução:** VAST.ai sem GPUs disponíveis no momento. Aguarde alguns minutos.

### Erro: "Instance not ready after 600s"
**Solução:** GPU demorou muito para iniciar. Pode ser problema da VAST.ai. Tente novamente.

### Erro: "Snapshot failed"
**Solução:** Verificar credenciais B2 no `.env` e conectividade com Backblaze.

### Erro: "SSH connection refused"
**Solução:** Porta SSH bloqueada ou GPU ainda inicializando. Testes aguardam até 10 min.

### Erro: "Rate limit (429)"
**Solução:** VAST.ai rate limiting. Testes automaticamente aguardam com backoff.

---

## Checklist de Validação

Antes de considerar os testes prontos:

- [x] Test 3.1: Auto-hibernation implementado
- [x] Test 3.2: Wake from hibernation implementado
- [x] Test 4.1: Large snapshot implementado
- [x] Test 4.2: Multiple failovers implementado
- [x] Rate limiting com backoff exponencial
- [x] Todos os testes deletam instâncias ao final
- [x] Métricas de tempo coletadas
- [x] Custo total calculado
- [x] Relatórios JSON gerados
- [x] Documentação completa

---

## Custos Projetados

| Teste | GPUs | Tempo Estimado | Custo Estimado |
|-------|------|----------------|----------------|
| 3.1 Auto-Hibernation | 1 | 5-10 min | $0.15-0.30 |
| 3.2 Wake Hibernation | 1 | 5-10 min | $0.15-0.30 |
| 4.1 Large Snapshot | 2 | 15-30 min | $0.50-1.00 |
| 4.2 Multiple Failovers | 6 | 30-60 min | $1.50-3.00 |
| **TOTAL** | **10** | **55-110 min** | **$2.30-4.60** |

**Nota:** Preços baseados em GPUs ~$0.30/hr (RTX A4000/3060). GPUs mais caras aumentam custo.

---

## Próximos Passos

1. **Executar Test 3.1 e 3.2** para validar hibernação básica
2. **Analisar relatórios JSON** gerados
3. **Se tudo OK**, executar Test 4.1 (large snapshot)
4. **Se Test 4.1 OK**, executar Test 4.2 (multiple failovers)
5. **Consolidar métricas** de todos os testes
6. **Ajustar timeouts** se necessário baseado em resultados reais

---

## Comandos Rápidos

```bash
# Ativar ambiente
cd /Users/marcos/CascadeProjects/dumontcloud
source venv/bin/activate

# Executar Phase 3 completa
pytest cli/tests/test_auto_hibernation.py cli/tests/test_wake_hibernation.py -v -s

# Executar Phase 4 completa (CUIDADO: CARO!)
pytest cli/tests/test_large_snapshot.py cli/tests/test_multiple_failovers.py -v -s --real

# Ver relatórios gerados
ls -lah /tmp/*_report_*.json | tail -10
cat /tmp/auto_hibernation_report_*.json | jq .
```

---

## Contato

Para dúvidas sobre estes testes, consultar:
- Código: `/Users/marcos/CascadeProjects/dumontcloud/cli/tests/`
- Documentação: Este arquivo
- CLAUDE.md: Instruções gerais do projeto
