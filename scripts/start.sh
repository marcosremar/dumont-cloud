#!/bin/bash
# Dumont Cloud - Start Script
# Inicia code-server e backend simultaneamente

echo "============================================"
echo "Dumont Cloud - Starting services..."
echo "============================================"

# Verificar se code-server está instalado
if ! command -v code-server &> /dev/null; then
    echo "ERROR: code-server not found!"
    # Continue anyway - don't fail the whole container
fi

# Criar diretório de config se não existir
mkdir -p /root/.config/code-server

# Criar config do code-server
cat > /root/.config/code-server/config.yaml << 'EOF'
bind-addr: 0.0.0.0:8080
auth: password
password: Marcos+123
cert: false
EOF

echo "Config file created:"
cat /root/.config/code-server/config.yaml

echo ""
echo "Starting VS Code Server on port 8080..."
# Run code-server in background, output goes to container logs
nohup code-server /app --bind-addr 0.0.0.0:8080 > /proc/1/fd/1 2>&1 &

# Give code-server time to start
sleep 5

# Check if it started
if pgrep -f "code-server" > /dev/null; then
    echo "code-server started successfully (PID: $(pgrep -f 'code-server' | head -1))"
else
    echo "WARNING: code-server may not have started"
fi

echo ""
echo "Starting Dumont Cloud API on port 8000..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
