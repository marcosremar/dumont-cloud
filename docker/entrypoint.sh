#!/bin/bash
# =============================================================================
# DUMONTCLOUD WORKER ENTRYPOINT
# =============================================================================
# Inicializa SSH e Ollama na inicialização do container
# =============================================================================

set -e

echo "============================================"
echo "  DumontCloud GPU Worker v1.0"
echo "============================================"
echo ""

# 1. Iniciar SSH Server
echo "[1/3] Iniciando SSH Server..."
/usr/sbin/sshd

# 2. Iniciar Ollama em background
echo "[2/3] Iniciando Ollama Server..."
export OLLAMA_MODELS=/workspace/ollama_models
ollama serve &

# Aguardar Ollama iniciar
sleep 2

# 3. Verificar GPU
echo "[3/3] Verificando GPU..."
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo "N/A")
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null || echo "N/A")
    echo "  GPU: $GPU_NAME"
    echo "  VRAM: $GPU_MEM"
else
    echo "  [WARN] nvidia-smi não disponível"
fi

echo ""
echo "============================================"
echo "  Worker pronto!"
echo "  - SSH: Porta 22"
echo "  - Ollama API: Porta 11434"
echo "============================================"
echo ""

# Manter container rodando
exec tail -f /dev/null
