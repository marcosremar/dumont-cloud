# Guia Completo de Testes de Failover REAIS - Dumont Cloud

Este guia documenta como executar testes de failover **REAIS** que:
- Provisionam GPUs reais na VAST.ai
- Criam arquivos únicos para validação
- Fazem snapshots reais em Backblaze B2
- Testam failover com transferência de dados
- Validam integridade via checksums MD5

**ATENÇÃO:** Estes testes **CUSTAM DINHEIRO REAL**!
- VAST.ai: ~$0.30-0.50 por teste completo
- Backblaze B2: ~$0.01 por snapshot
- GCP (opcional): ~$0.05/hora para CPU Standby

## Arquivos de Teste

### 1. Suite de Testes Principal
**Arquivo:** `/Users/marcos/CascadeProjects/dumontcloud/cli/tests/test_real_failover_complete.py`

Esta suite executa a jornada completa:
1. Provisiona GPU real
2. Cria arquivos de teste com conteúdo único
3. Cria snapshot em B2
4. Provisiona NOVA GPU (failover)
5. Restaura snapshot
6. Valida integridade (MD5)

### 2. Script Helper SSH
**Arquivo:** `/Users/marcos/CascadeProjects/dumontcloud/scripts/dumont_ssh_failover_test.py`

Utilitário para criar/validar arquivos via SSH direto.

## Execução dos Testes

### Pré-requisitos

1. **Variáveis de ambiente:**
```bash
export VAST_API_KEY="your_vast_api_key"
export B2_ENDPOINT="https://s3.us-west-004.backblazeb2.com"
export B2_BUCKET="dumoncloud-snapshot"
export DUMONT_API_URL="http://localhost:8766"
```

2. **Backend rodando:**
```bash
cd /Users/marcos/CascadeProjects/dumontcloud
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8766
```

### Teste 1: Sincronização em Tempo Real (Completo)

**Objetivo:** Validar transferência de dados via snapshot entre GPUs.

```bash
cd /Users/marcos/CascadeProjects/dumontcloud/cli

# Executar teste completo (demora ~15-20 min)
pytest tests/test_real_failover_complete.py::TestRealTimeSyncFailover -v -s --tb=short
```

**O que este teste faz:**

1. **[1/6] Busca oferta GPU**
   - Consulta VAST.ai
   - Escolhe GPU mais barata
   - Exibe preço/hr

2. **[2/6] Cria instância GPU**
   - Provisiona GPU real
   - Aguarda até 10 min para ficar ready
   - Verifica SSH acessível

3. **[3/6] Cria arquivos de teste**
   - 3 arquivos em `/workspace`
   - Cada arquivo tem timestamp único
   - Calcula MD5 de cada arquivo
   - Armazena metadados

4. **[4/6] Cria snapshot**
   - Snapshot completo do `/workspace`
   - Upload para Backblaze B2
   - Compressão LZ4
   - Mede tempo de upload

5. **[5/6] Failover para nova GPU**
   - Provisiona NOVA GPU
   - Aguarda ficar ready
   - Restaura snapshot
   - Mede tempo de restore

6. **[6/6] Valida integridade**
   - Verifica cada arquivo existe
   - Compara MD5 original vs restaurado
   - Conta arquivos válidos
   - Gera relatório final

**Saída esperada:**

```
======================================================================
RELATÓRIO DO TESTE
======================================================================

Jornada completa:
  1. Criar arquivos:       3.2s
  2. Criar snapshot:      45.8s
  3. Failover + Restore: 125.3s
  4. Validar:              2.1s
  TOTAL:                 176.4s (2.9 min)

Recursos:
  GPU Original:    29012345
  Snapshot:        test-snapshot-1704108234
  Failover GPU:    29012456

Custo estimado:
  GPU hourly:      $0.3200/hr
  Tempo total:     0.0490 hrs
  Total (2 GPUs):  $0.0314

Validação:
  Arquivos OK:     3/3
  Sucesso:         ✓ SIM

======================================================================
```

### Teste 2: Failover Manual via SSH

**Objetivo:** Testar transferência de dados manualmente, sem destruir GPUs.

#### 2.1. Criar GPU e arquivos de teste

```bash
# 1. Provisionar GPU via Dumont
dumont instance create --gpu RTX_4090 --name "test-failover-1"

# Anote o instance_id retornado (ex: 29012345)

# 2. Criar arquivos de teste via SSH helper
python scripts/dumont_ssh_failover_test.py \
  --instance-id 29012345 \
  --create-files \
  --file-count 5

# Isso cria:
# - 5 arquivos em /workspace/test-file-*.txt
# - Salva metadados em failover_files_29012345.json
```

#### 2.2. Criar snapshot

```bash
# Via API ou CLI
dumont snapshot create --instance-id 29012345 --name "manual-test-1"

# Anote o snapshot_id retornado
```

#### 2.3. Criar segunda GPU e restaurar

```bash
# 1. Provisionar segunda GPU
dumont instance create --gpu RTX_4090 --name "test-failover-2"

# Anote o novo instance_id (ex: 29012456)

# 2. Restaurar snapshot
dumont snapshot restore --snapshot-id "manual-test-1" --instance-id 29012456

# 3. Validar arquivos
python scripts/dumont_ssh_failover_test.py \
  --instance-id 29012456 \
  --validate-files failover_files_29012345.json
```

**Saída esperada:**

```
============================================================
VALIDATION RESULT
============================================================
  Files validated: 5/5
  Success rate:    100.0%
============================================================
```

### Teste 3: Failover com CPU Standby (GCP)

**Objetivo:** Testar failover GPU → CPU → GPU nova.

**Pré-requisito:** Credenciais GCP configuradas.

```bash
# 1. Configurar CPU Standby
dumont standby configure --enabled=true --gcp-zone=us-central1-a

# 2. Criar GPU com Standby automático
dumont instance create --gpu RTX_4090 --cpu-standby=true

# 3. Criar arquivos de teste (via SSH helper)
python scripts/dumont_ssh_failover_test.py \
  --instance-id <GPU_ID> \
  --create-files

# 4. Simular falha da GPU (destroi instância)
dumont instance destroy <GPU_ID>

# 5. Verificar que CPU Standby assumiu
dumont standby associations

# 6. Provisionar nova GPU e restaurar
dumont failover restore --from-cpu-standby --gpu-id <GPU_ID>

# 7. Validar arquivos
python scripts/dumont_ssh_failover_test.py \
  --instance-id <NEW_GPU_ID> \
  --validate-files failover_files_<GPU_ID>.json
```

## Métricas Coletadas

Cada teste coleta:

### Timing
- `time_create_files`: Tempo para criar arquivos de teste
- `time_create_snapshot`: Tempo para snapshot completo
- `time_failover`: Tempo para provisionar nova GPU + restore
- `time_validate`: Tempo para validar integridade
- `time_total`: Tempo total do teste

### Validação
- `files_validated`: Número de arquivos validados com MD5 correto
- `test_files`: Lista de arquivos com path, MD5, size
- `success`: Boolean - teste passou ou falhou

### Custos
- `gpu_cost_per_hour`: Custo/hora da GPU
- `estimated_cost_usd`: Custo total estimado do teste

### Recursos
- `gpu_instance_id`: ID da GPU original
- `snapshot_id`: ID do snapshot criado
- `failover_gpu_id`: ID da GPU de failover

## Análise de Falhas

### Teste falhou na criação de arquivos

**Sintoma:**
```
✗ Failed to create /workspace/test-file-1.txt: Permission denied
```

**Solução:**
- Verificar que SSH está acessível
- Tentar criar diretório manualmente: `ssh root@<host> -p <port> mkdir -p /workspace`
- Verificar permissões da instância

### Teste falhou no snapshot

**Sintoma:**
```
Snapshot failed: No such file or directory
```

**Solução:**
- Verificar que `/workspace` existe
- Verificar credenciais B2
- Verificar que `s5cmd` está instalado na GPU

### Validação de MD5 falhou

**Sintoma:**
```
✗ MD5 mismatch: /workspace/test-file-1.txt
   Expected: abc123...
   Got:      def456...
```

**Causa possível:**
- Arquivo foi modificado após snapshot
- Snapshot corrupto
- Restore incompleto

**Solução:**
- Re-executar teste do zero
- Verificar logs do restore
- Tentar snapshot manual

## Custos Estimados

### Teste Completo (15-20 min)

| Item | Custo |
|------|-------|
| GPU Original (RTX 4090, 0.05h) | $0.016 |
| GPU Failover (RTX 4090, 0.05h) | $0.016 |
| Snapshot B2 (100MB) | $0.001 |
| Transfer B2 (100MB download) | $0.000 |
| **TOTAL** | **~$0.035** |

### Teste com CPU Standby (30 min)

| Item | Custo |
|------|-------|
| GPU Original (RTX 4090, 0.1h) | $0.032 |
| CPU Standby (e2-medium, 0.5h) | $0.017 |
| GPU Failover (RTX 4090, 0.1h) | $0.032 |
| Snapshot B2 (100MB) | $0.001 |
| **TOTAL** | **~$0.082** |

## Cleanup Automático

Os testes **sempre** limpam recursos ao final:

```python
def test_99_cleanup(self, auth_token, test_metrics):
    """Cleanup: deleta GPUs criadas"""
    # Deleta GPU original
    # Deleta GPU de failover
    # Snapshot permanece em B2 (para auditoria)
```

Para limpar snapshots manualmente:

```bash
# Listar snapshots
dumont snapshot list

# Deletar snapshot específico
dumont snapshot delete --snapshot-id <ID>

# Deletar todos snapshots de teste
dumont snapshot delete --pattern "test-snapshot-*"
```

## Troubleshooting

### Teste trava em "Aguardando instância ficar ready"

**Timeout:** 10 minutos

**Possíveis causas:**
1. GPU não está ficando running
2. SSH não está acessível
3. Host VAST.ai com problemas

**Solução:**
- Verificar status da instância: `dumont instance status <ID>`
- Verificar logs VAST.ai
- Cancelar teste: Ctrl+C
- Deletar instância: `dumont instance destroy <ID>`

### ImportError: No module named 'requests'

**Solução:**
```bash
source venv/bin/activate
pip install requests
```

### Authentication failed

**Solução:**
```bash
# Verificar credenciais demo
dumont auth login --email test@test.com --password test123

# Verificar token
dumont auth whoami
```

## Comandos Úteis

```bash
# Ver métricas dos testes
cat cli/tests/failover_test_metrics.json | jq

# Ver logs do backend
tail -f logs/dumont.log | grep -i failover

# Monitorar uso de créditos VAST.ai
curl -H "Authorization: Bearer $VAST_API_KEY" \
  https://cloud.vast.ai/api/v0/users/current/ | jq '.balance'

# Listar todas instâncias ativas
dumont instance list --status running

# Forçar cleanup de todas instâncias de teste
dumont instance destroy --pattern "test-failover-*"
```

## Referências

- **Documentação Failover**: `/Users/marcos/CascadeProjects/dumontcloud/docs/FAILOVER_SYSTEM.md`
- **Testes unitários**: `/Users/marcos/CascadeProjects/dumontcloud/cli/tests/test_failover_real.py`
- **API Endpoints**: `/Users/marcos/CascadeProjects/dumontcloud/src/api/v1/endpoints/standby.py`
- **Snapshot Service**: `/Users/marcos/CascadeProjects/dumontcloud/src/services/gpu/snapshot.py`

## Suporte

Para problemas ou dúvidas:

1. Verificar logs: `tail -f logs/dumont.log`
2. Verificar status do backend: `curl http://localhost:8766/health`
3. Consultar documentação: `docs/FAILOVER_SYSTEM.md`
4. Reportar issue: GitHub Issues

---

**Última atualização:** 2026-01-02
**Versão:** 1.0
**Autor:** Dumont Cloud Team
