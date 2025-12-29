#!/bin/bash
# Dumont Cloud - Start Script
# Inicia code-server e backend simultaneamente

set -e

echo "============================================"
echo "Dumont Cloud - Starting services..."
echo "============================================"

# Verificar se code-server está instalado
if ! command -v code-server &> /dev/null; then
    echo "ERROR: code-server not found!"
    exit 1
fi

# Criar diretório de config se não existir
mkdir -p /root/.config/code-server

# Criar config do code-server se não existir
if [ ! -f /root/.config/code-server/config.yaml ]; then
    echo "Creating code-server config..."
    cat > /root/.config/code-server/config.yaml << 'EOF'
bind-addr: 0.0.0.0:8080
auth: password
password: Marcos+123
cert: false
EOF
fi

echo "Starting VS Code Server on port 8080..."
code-server /app --bind-addr 0.0.0.0:8080 2>&1 | sed 's/^/[code-server] /' &
CODE_SERVER_PID=$!

# Aguardar um pouco para code-server inicializar
sleep 3

# Verificar se code-server está rodando
if ! kill -0 $CODE_SERVER_PID 2>/dev/null; then
    echo "WARNING: code-server may have failed to start"
fi

echo "Starting Dumont Cloud API on port 8000..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
