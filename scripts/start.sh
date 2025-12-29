#!/bin/bash
# Dumont Cloud - Start Script
# Inicia code-server e backend simultaneamente

# Iniciar code-server em background
echo "Starting VS Code Server on port 8080..."
code-server /app --bind-addr 0.0.0.0:8080 &

# Aguardar um pouco para code-server inicializar
sleep 2

# Iniciar backend (foreground)
echo "Starting Dumont Cloud API on port 8000..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
