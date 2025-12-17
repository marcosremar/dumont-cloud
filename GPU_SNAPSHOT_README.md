# GPU Snapshot System - Hibernação/Restore de Máquinas GPU

Sistema de snapshot otimizado usando **ANS (GPU compression) + Cloudflare R2** com upload/download paralelo em 32 partes.

## 🎯 Performance

- **Compressão**: 41 GB/s (GPU com ANS)
- **Descompressão**: 107 GB/s (GPU com ANS)
- **Upload R2**: 950 MB/s (32 partes paralelas)
- **Download R2**: 950 MB/s (32 partes paralelas)
- **Restore total (70GB workspace)**: ~5 minutos

## 🚀 Arquitetura

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  GPU Machine│         │ Cloudflare R2│         │  GPU Machine│
│  (Origin)   │         │   Storage    │         │  (Target)   │
└─────────────┘         └──────────────┘         └─────────────┘
      │                        │                        │
      │ 1. Compress with ANS   │                        │
      │    (41 GB/s on GPU)    │                        │
      │ Split into 32 parts    │                        │
      ├───────────────────────>│                        │
      │ 2. Upload 32 parts     │                        │
      │    (950 MB/s parallel) │                        │
      │                        │<───────────────────────┤
      │                        │ 3. Download 32 parts   │
      │                        │    (950 MB/s parallel) │
      │                        │                        │
      │                        │ 4. Decompress with ANS │
      │                        │    (107 GB/s on GPU)   │
```

## 📦 Componentes

### 1. Serviço Principal
**Arquivo**: `src/services/gpu_snapshot_service.py`

```python
from src.services.gpu_snapshot_service import GPUSnapshotService

# Inicializar
service = GPUSnapshotService(
    r2_endpoint="https://....r2.cloudflarestorage.com",
    r2_bucket="bucket-name"
)

# Criar snapshot (hibernar)
snapshot_info = service.create_snapshot(
    instance_id="12345",
    ssh_host="1.2.3.4",
    ssh_port=22,
    workspace_path="/workspace",
    snapshot_name="my-snapshot"
)

# Restaurar snapshot
restore_info = service.restore_snapshot(
    snapshot_id="my-snapshot",
    ssh_host="5.6.7.8",
    ssh_port=22,
    workspace_path="/workspace"
)
```

### 2. API Endpoints
**Arquivo**: `src/api/snapshots_ans.py`

#### Listar snapshots
```bash
GET /api/gpu-snapshots?instance_id=12345
```

#### Criar snapshot (hibernar)
```bash
POST /api/gpu-snapshots/create
{
  "instance_id": "12345",
  "ssh_host": "1.2.3.4",
  "ssh_port": 22,
  "workspace_path": "/workspace",
  "snapshot_name": "optional-name"
}
```

#### Restaurar snapshot
```bash
POST /api/gpu-snapshots/<snapshot_id>/restore
{
  "ssh_host": "5.6.7.8",
  "ssh_port": 22,
  "workspace_path": "/workspace"
}
```

#### Hibernar instância (snapshot + destroy)
```bash
POST /api/instances/<instance_id>/hibernate
{
  "ssh_host": "1.2.3.4",
  "ssh_port": 22,
  "workspace_path": "/workspace",
  "destroy_after": true
}
```

#### Acordar instância (create + restore)
```bash
POST /api/instances/<instance_id>/wake
{
  "snapshot_id": "optional-snapshot-id",
  "gpu_type": "RTX 5090",
  "region": "eu"
}
```

#### Deletar snapshot
```bash
DELETE /api/gpu-snapshots/<snapshot_id>
```

## 🔧 Dependências

### Na máquina de controle (VPS):
```bash
# s5cmd (R2 transfers)
wget https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz
tar -xzf s5cmd_2.2.2_Linux-64bit.tar.gz
sudo mv s5cmd /usr/local/bin/

# Variáveis de ambiente (.env)
R2_ENDPOINT=https://....r2.cloudflarestorage.com
R2_BUCKET=bucket-name
R2_ACCESS_KEY=your-access-key
R2_SECRET_KEY=your-secret-key
```

### Nas máquinas GPU (vast.ai):
```bash
# Instalado automaticamente via SSH nos scripts
pip install nvidia-nvcomp-cu13 cupy-cuda12x
```

## 📊 Benchmark Results

Veja `REPLICATION_BENCHMARK_FINAL.md` para resultados completos.

### Para workspace de 70GB:
| Operação | Tempo |
|----------|-------|
| Compressão ANS (GPU) | ~2s |
| Upload R2 (32 partes) | ~5-6 min |
| Download R2 (32 partes) | ~5 min |
| Descompressão ANS (GPU) | ~0.5s |
| **Total** | **~5 minutos** |

### Comparação com outros métodos:
| Método | Tempo 1→3 (70GB) | Custo | Complexidade |
|--------|------------------|-------|--------------|
| **ANS + R2** | **~5 min** | $0.83/mês | Baixa ⭐ |
| Sync Machines (GCP) | ~8-10 min | $25/mês | Alta |
| Direct Copy (SCP) | ~20-30 min | $0 | Média |
| Docker Registry | ~15-20 min | Variável | Média |

## 🧪 Testes

### Teste manual com curl:
```bash
# 1. Criar snapshot
curl -X POST http://localhost:5000/api/gpu-snapshots/create \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "12345",
    "ssh_host": "1.2.3.4",
    "ssh_port": 22,
    "workspace_path": "/workspace"
  }'

# 2. Listar snapshots
curl http://localhost:5000/api/gpu-snapshots

# 3. Restaurar snapshot
curl -X POST http://localhost:5000/api/gpu-snapshots/<snapshot-id>/restore \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_host": "5.6.7.8",
    "ssh_port": 22,
    "workspace_path": "/workspace"
  }'
```

### Teste completo (RTX 5090 + Qwen 2.5-0.5B):
```bash
# Ver script de teste em /tmp/test_replication_simple.sh
bash /tmp/test_replication_simple.sh
```

## 🔍 Como Funciona

### Criação de Snapshot (Hibernar):
1. **Compressão**:
   - Cria tar do workspace
   - Divide em 32 partes
   - Comprime cada parte com ANS na GPU (nvCOMP)
   - Velocidade: 41 GB/s

2. **Upload**:
   - Upload paralelo de 32 partes para R2
   - s5cmd com --numworkers 32
   - Velocidade: 950 MB/s

3. **Metadados**:
   - Salva JSON com info do snapshot
   - Inclui tamanho original, comprimido, ratio, etc.

### Restauração de Snapshot:
1. **Download**:
   - Download paralelo de 32 partes do R2
   - s5cmd com --numworkers 32
   - Velocidade: 950 MB/s

2. **Descompressão**:
   - Descomprime cada parte com ANS na GPU
   - Junta as partes
   - Extrai tar para workspace
   - Velocidade: 107 GB/s

## 🎯 Casos de Uso

### 1. Hibernar máquina GPU cara
```bash
# Salvar estado e destruir instância
POST /api/instances/12345/hibernate
{
  "ssh_host": "1.2.3.4",
  "ssh_port": 22,
  "destroy_after": true
}

# Economizar 100% do custo de GPU enquanto não está em uso
```

### 2. Replicar workspace para múltiplas GPUs
```bash
# Criar snapshot uma vez
POST /api/gpu-snapshots/create

# Restaurar em 3 máquinas diferentes (paralelo)
# Tempo total: ~5 minutos (não 15 minutos!)
```

### 3. Backup contínuo
```bash
# Criar snapshot diário automaticamente
# Manter últimos 7 snapshots
# Custo: ~$6/mês para 70GB x 7 dias
```

## 💡 Otimizações

### 1. Escolher região próxima do R2
- R2 está em EU
- Escolher GPUs vast.ai na região EU
- Ganho: 30-50% mais rápido

### 2. Sync incremental (rclone)
- Primeira vez: 5 minutos (snapshot completo)
- Próximas vezes: ~30s (só arquivos modificados)
- Ideal para development contínuo

### 3. Compressão adicional (zstd pré-processamento)
- Comprimir com zstd nível 19 antes de ANS
- Ganho: 20-30% arquivo menor
- Trade-off: +10s no processo

## 🔐 Segurança

- Credenciais R2 em variáveis de ambiente
- SSH sem verificação de host (apenas para vast.ai)
- Sem autenticação adicional (assumindo VPN/firewall)

## 📝 Logs

Os logs estão disponíveis via Python logging:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 🐛 Troubleshooting

### Erro: "CUDA Runtime API failure"
- **Causa**: GPU ocupada com outro processo
- **Solução**: `pkill -9 python && sleep 2` na máquina GPU

### Erro: "s5cmd not found"
- **Causa**: s5cmd não instalado na máquina GPU
- **Solução**: Script instala automaticamente via SSH

### Erro: "nvcomp import error"
- **Causa**: nvcomp não instalado ou versão CUDA incorreta
- **Solução**: `pip install nvidia-nvcomp-cu13 cupy-cuda12x`

### Timeout no SSH
- **Causa**: Máquina GPU não está pronta
- **Solução**: Aguardar 1-2 minutos após criação da instância

## 📚 Referências

- [nvCOMP Documentation](https://github.com/NVIDIA/nvcomp)
- [s5cmd Documentation](https://github.com/peak/s5cmd)
- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [Benchmark Results](./REPLICATION_BENCHMARK_FINAL.md)
