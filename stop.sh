#!/bin/bash
# Dumont Cloud - Script para parar servidores

echo "🛑 Parando Dumont Cloud..."

pkill -f "uvicorn src.main:app" 2>/dev/null && echo "✓ Backend parado" || echo "- Backend não estava rodando"
pkill -f "vite.*4892" 2>/dev/null && echo "✓ Frontend parado" || echo "- Frontend não estava rodando"

echo "✅ Servidores encerrados"
