#!/bin/bash
# Dumont Cloud - Script de inicialização
# Inicia backend (FastAPI) e frontend (Vite)

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}           🚀 Dumont Cloud - Iniciando...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Carregar variáveis de ambiente
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${GREEN}✓${NC} Variáveis de ambiente carregadas"
fi

# Matar processos anteriores
echo -e "${YELLOW}⏳${NC} Encerrando processos anteriores..."
pkill -f "uvicorn src.main:app" 2>/dev/null || true
pkill -f "vite.*4892" 2>/dev/null || true
sleep 1

# Iniciar Backend
echo -e "${YELLOW}⏳${NC} Iniciando backend (FastAPI)..."
nohup python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/dumont-backend.log 2>&1 &
BACKEND_PID=$!

# Aguardar backend iniciar
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Backend rodando (PID: $BACKEND_PID)"
        break
    fi
    sleep 1
done

# Iniciar Frontend
echo -e "${YELLOW}⏳${NC} Iniciando frontend (Vite)..."
cd "$PROJECT_DIR/web"
nohup npm run dev > /tmp/dumont-frontend.log 2>&1 &
FRONTEND_PID=$!
cd "$PROJECT_DIR"

# Aguardar frontend iniciar
for i in {1..10}; do
    if curl -s http://localhost:4892 > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Frontend rodando (PID: $FRONTEND_PID)"
        break
    fi
    sleep 1
done

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Dumont Cloud iniciado com sucesso!${NC}"
echo ""
echo -e "   ${BLUE}Frontend:${NC} http://localhost:4892"
echo -e "   ${BLUE}Backend:${NC}  http://localhost:8000"
echo -e "   ${BLUE}API Docs:${NC} http://localhost:8000/docs"
echo ""
echo -e "   ${YELLOW}Logs:${NC}"
echo -e "   - Backend:  tail -f /tmp/dumont-backend.log"
echo -e "   - Frontend: tail -f /tmp/dumont-frontend.log"
echo ""
echo -e "   ${YELLOW}Para parar:${NC} ./stop.sh ou pkill -f 'uvicorn|vite'"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Abrir navegador (opcional)
if [[ "$1" != "--no-browser" ]]; then
    sleep 1
    open http://localhost:4892 2>/dev/null || xdg-open http://localhost:4892 2>/dev/null || true
fi
