#!/bin/bash
#
# Script de teste: Compressão em chunks com download paralelo + descompressão GPU
# Para rodar em uma máquina Vast.ai com GPU (RTX 5090, 4090, etc)
#
# Uso: ./test_chunked_compression.sh
#

set -e

echo "=============================================="
echo "  Teste de Compressão em Chunks + GPU"
echo "=============================================="
echo ""

# Verificar GPU
echo "[1/8] Verificando GPU..."
nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv
echo ""

# Instalar dependências
echo "[2/8] Instalando dependências..."
apt-get update -qq
apt-get install -y -qq cmake build-essential git pv aria2 zstd pigz

# Verificar CUDA
echo "[3/8] Verificando CUDA..."
nvcc --version 2>/dev/null || echo "CUDA não instalado - LibBSC vai usar CPU"
echo ""

# Clonar e compilar LibBSC com CUDA
echo "[4/8] Compilando LibBSC com suporte CUDA..."
cd /tmp
rm -rf libbsc
git clone https://github.com/IlyaGrebnov/libbsc.git
cd libbsc
mkdir -p build && cd build
cmake .. -DBSC_ENABLE_CUDA=ON 2>&1 | tail -5
make -j$(nproc) 2>&1 | tail -3
echo "LibBSC compilado!"
echo ""

# Criar dados de teste (simula /workspace com ~1GB)
echo "[5/8] Criando dados de teste (~1GB)..."
cd /tmp
rm -rf test_workspace
mkdir -p test_workspace

# Mix de arquivos realistas
dd if=/dev/urandom of=test_workspace/model_weights.bin bs=1M count=300 2>/dev/null
dd if=/dev/urandom of=test_workspace/embeddings.bin bs=1M count=200 2>/dev/null
yes "import torch; model = torch.load('model.pt'); print(model)" | head -c 100M > test_workspace/code.py
yes '{"key": "value", "data": [1,2,3,4,5]}' | head -c 200M > test_workspace/data.json
cp -r /usr test_workspace/system_files 2>/dev/null || true

ORIGINAL_SIZE=$(du -sb test_workspace | cut -f1)
echo "Tamanho original: $(du -sh test_workspace | cut -f1) ($ORIGINAL_SIZE bytes)"
echo ""

# Criar arquivo tar
echo "[6/8] Criando arquivo tar..."
tar -cf test_data.tar test_workspace
TAR_SIZE=$(stat -c%s test_data.tar)
echo "Tamanho tar: $(ls -lh test_data.tar | awk '{print $5}')"
echo ""

# ============================================
# TESTE 1: LibBSC (melhor ratio)
# ============================================
echo "=============================================="
echo "  TESTE 1: LibBSC (GPU se disponível)"
echo "=============================================="

echo "Comprimindo com LibBSC..."
time /tmp/libbsc/build/bsc e test_data.tar test_data.bsc -b64 -G 2>&1 || \
time /tmp/libbsc/build/bsc e test_data.tar test_data.bsc -b64 2>&1

BSC_SIZE=$(stat -c%s test_data.bsc)
BSC_RATIO=$(echo "scale=2; $TAR_SIZE / $BSC_SIZE" | bc)
echo "Tamanho BSC: $(ls -lh test_data.bsc | awk '{print $5}') (ratio: ${BSC_RATIO}:1)"
echo ""

echo "Descomprimindo com LibBSC..."
rm -rf test_workspace_restored
time /tmp/libbsc/build/bsc d test_data.bsc test_data_restored.tar -G 2>&1 || \
time /tmp/libbsc/build/bsc d test_data.bsc test_data_restored.tar 2>&1
echo ""

# ============================================
# TESTE 2: Zstd -22 (para comparar)
# ============================================
echo "=============================================="
echo "  TESTE 2: Zstd nível 22"
echo "=============================================="

echo "Comprimindo com Zstd -22..."
time zstd -22 --ultra -T0 test_data.tar -o test_data.tar.zst 2>&1

ZSTD_SIZE=$(stat -c%s test_data.tar.zst)
ZSTD_RATIO=$(echo "scale=2; $TAR_SIZE / $ZSTD_SIZE" | bc)
echo "Tamanho Zstd: $(ls -lh test_data.tar.zst | awk '{print $5}') (ratio: ${ZSTD_RATIO}:1)"
echo ""

echo "Descomprimindo com Zstd..."
time zstd -d -T0 test_data.tar.zst -o test_data_zstd.tar 2>&1
echo ""

# ============================================
# TESTE 3: Chunks paralelos (simulação)
# ============================================
echo "=============================================="
echo "  TESTE 3: Chunks Paralelos (simulação)"
echo "=============================================="

CHUNK_SIZE=100M
echo "Dividindo em chunks de $CHUNK_SIZE..."
split -b $CHUNK_SIZE test_data.tar test_chunk_

CHUNK_COUNT=$(ls test_chunk_* | wc -l)
echo "Criados $CHUNK_COUNT chunks"
echo ""

echo "Comprimindo chunks em paralelo..."
time (
  for chunk in test_chunk_*; do
    zstd -19 -T2 "$chunk" -o "${chunk}.zst" &
  done
  wait
)
echo ""

TOTAL_COMPRESSED=0
for f in test_chunk_*.zst; do
  SIZE=$(stat -c%s "$f")
  TOTAL_COMPRESSED=$((TOTAL_COMPRESSED + SIZE))
done
CHUNK_RATIO=$(echo "scale=2; $TAR_SIZE / $TOTAL_COMPRESSED" | bc)
echo "Tamanho total chunks: $(echo $TOTAL_COMPRESSED | numfmt --to=iec) (ratio: ${CHUNK_RATIO}:1)"
echo ""

echo "Simulando download + decompress paralelo..."
echo "(Em produção: enquanto baixa chunk N+1, descomprime chunk N)"
time (
  for chunk in test_chunk_*.zst; do
    zstd -d -T0 "$chunk" -o "${chunk%.zst}.restored" &
  done
  wait
)
echo ""

# ============================================
# RESUMO
# ============================================
echo "=============================================="
echo "  RESUMO DOS TESTES"
echo "=============================================="
echo ""
echo "Tamanho original: $(echo $TAR_SIZE | numfmt --to=iec)"
echo ""
echo "| Método      | Comprimido    | Ratio  |"
echo "|-------------|---------------|--------|"
echo "| LibBSC      | $(echo $BSC_SIZE | numfmt --to=iec --padding=13) | ${BSC_RATIO}:1  |"
echo "| Zstd -22    | $(echo $ZSTD_SIZE | numfmt --to=iec --padding=13) | ${ZSTD_RATIO}:1  |"
echo "| Chunks Zstd | $(echo $TOTAL_COMPRESSED | numfmt --to=iec --padding=13) | ${CHUNK_RATIO}:1  |"
echo ""
echo "=============================================="
echo "  CONCLUSÃO"
echo "=============================================="
echo ""
echo "Para 68GB de dados reais:"
echo ""
echo "LibBSC (ratio ~${BSC_RATIO}x):"
echo "  - Arquivo: ~$(echo "68 / $BSC_RATIO" | bc)GB"
echo "  - Download 100Mbps: ~$(echo "68 * 8 / $BSC_RATIO / 100 / 60" | bc) min"
echo ""
echo "Zstd -22 (ratio ~${ZSTD_RATIO}x):"
echo "  - Arquivo: ~$(echo "68 / $ZSTD_RATIO" | bc)GB"
echo "  - Download 100Mbps: ~$(echo "68 * 8 / $ZSTD_RATIO / 100 / 60" | bc) min"
echo ""
echo "Com chunks paralelos: tempo de descompressão fica ~grátis!"
echo ""

# Cleanup
rm -rf test_workspace test_workspace_restored test_data* test_chunk_*
echo "Teste concluído! Arquivos temporários removidos."
