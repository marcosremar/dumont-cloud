#!/bin/bash
#
# DumontCloud - Background Screenshot Capture
#
# Este script inicia a captura de screenshots em background
# com suporte a recuperação e monitoramento.
#
# Uso:
#   ./run-in-background.sh          # Inicia captura em background
#   ./run-in-background.sh --status # Verifica status
#   ./run-in-background.sh --stop   # Para a captura
#   ./run-in-background.sh --resume # Retoma captura interrompida
#   ./run-in-background.sh --logs   # Mostra logs em tempo real
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_FILE="$PROJECT_DIR/artifacts/screenshots/capture.log"
PID_FILE="$SCRIPT_DIR/.capture.pid"
STATE_FILE="$SCRIPT_DIR/screenshot-state.json"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   DumontCloud Screenshot Capture Tool${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_dependencies() {
    echo -e "\n${YELLOW}🔍 Verificando dependências...${NC}"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js não encontrado${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Node.js: $(node --version)${NC}"
    
    # Check Playwright
    cd "$PROJECT_DIR/scripts/screenshots"
    if ! node -e "require('playwright')" 2>/dev/null; then
        echo -e "${YELLOW}📦 Instalando Playwright...${NC}"
        npm install playwright 2>&1
        npx playwright install chromium 2>&1
    else
        echo -e "${GREEN}✓ Playwright instalado${NC}"
    fi
}

check_dev_server() {
    echo -e "\n${YELLOW}🌐 Verificando servidor de desenvolvimento...${NC}"
    
    if lsof -i :5173 &> /dev/null; then
        echo -e "${GREEN}✓ Servidor Vite rodando na porta 5173${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Servidor não detectado na porta 5173${NC}"
        echo -e "${YELLOW}   Iniciando servidor de desenvolvimento...${NC}"
        
        cd "$PROJECT_DIR/web"
        nohup npm run dev > "$PROJECT_DIR/artifacts/screenshots/vite.log" 2>&1 &
        VITE_PID=$!
        echo "$VITE_PID" > "$SCRIPT_DIR/.vite.pid"
        
        # Wait for server to start
        echo -n "   Aguardando servidor iniciar"
        for i in {1..30}; do
            if curl -s http://localhost:5173 > /dev/null 2>&1; then
                echo -e "\n${GREEN}✓ Servidor iniciado (PID: $VITE_PID)${NC}"
                return 0
            fi
            echo -n "."
            sleep 1
        done
        
        echo -e "\n${RED}❌ Timeout aguardando servidor${NC}"
        return 1
    fi
}

start_capture() {
    print_header
    check_dependencies
    
    if ! check_dev_server; then
        echo -e "${RED}Não foi possível iniciar o servidor. Abortando.${NC}"
        exit 1
    fi
    
    # Ensure output directory exists
    mkdir -p "$PROJECT_DIR/artifacts/screenshots"
    
    echo -e "\n${GREEN}🚀 Iniciando captura em background...${NC}"
    
    cd "$SCRIPT_DIR"
    
    RESUME_FLAG=""
    if [ "$1" == "--resume" ]; then
        RESUME_FLAG="--resume"
        echo -e "${YELLOW}   Modo: Retomar sessão anterior${NC}"
    fi
    
    nohup node capture-all-screens.js $RESUME_FLAG > "$LOG_FILE" 2>&1 &
    CAPTURE_PID=$!
    echo "$CAPTURE_PID" > "$PID_FILE"
    
    echo -e "${GREEN}✓ Captura iniciada em background${NC}"
    echo -e "   PID: $CAPTURE_PID"
    echo -e "   Log: $LOG_FILE"
    echo -e "\n${BLUE}Comandos úteis:${NC}"
    echo -e "   $0 --status   # Ver progresso"
    echo -e "   $0 --logs     # Ver logs em tempo real"
    echo -e "   $0 --stop     # Parar captura"
}

show_status() {
    print_header
    echo -e "\n${BLUE}📊 Status da Captura${NC}\n"
    
    # Check if running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${GREEN}🟢 Captura em execução (PID: $PID)${NC}"
        else
            echo -e "${YELLOW}🟡 Processo não está rodando (PID antigo: $PID)${NC}"
        fi
    else
        echo -e "${YELLOW}⚪ Nenhuma captura em andamento${NC}"
    fi
    
    # Show state file info
    if [ -f "$STATE_FILE" ]; then
        echo -e "\n${BLUE}📋 Estado salvo:${NC}"
        COMPLETED=$(cat "$STATE_FILE" | grep -o '"completed":' -A 1000 | grep -o '\[.*\]' | head -1 | tr ',' '\n' | wc -l)
        FAILED=$(cat "$STATE_FILE" | grep -o '"failed":' -A 1000 | grep -o '\[.*\]' | head -1 | tr ',' '\n' | wc -l)
        TOTAL=$(cat "$STATE_FILE" | grep '"totalRoutes"' | grep -o '[0-9]*')
        
        echo -e "   Completadas: $COMPLETED/$TOTAL"
        echo -e "   Falhas: $FAILED"
        
        IN_PROGRESS=$(cat "$STATE_FILE" | grep '"inProgress"' | sed 's/.*: "\([^"]*\)".*/\1/')
        if [ ! -z "$IN_PROGRESS" ] && [ "$IN_PROGRESS" != "null" ]; then
            echo -e "   Em andamento: $IN_PROGRESS"
        fi
    fi
    
    # Count screenshots
    if [ -d "$PROJECT_DIR/artifacts/screenshots" ]; then
        COUNT=$(ls "$PROJECT_DIR/artifacts/screenshots"/*.png 2>/dev/null | wc -l)
        echo -e "\n${BLUE}📸 Screenshots capturados: $COUNT${NC}"
    fi
    
    # Show last log lines
    if [ -f "$LOG_FILE" ]; then
        echo -e "\n${BLUE}📝 Últimas linhas do log:${NC}"
        tail -5 "$LOG_FILE"
    fi
}

stop_capture() {
    print_header
    echo -e "\n${YELLOW}⏹️  Parando captura...${NC}"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            echo -e "${GREEN}✓ Processo $PID terminado${NC}"
            echo -e "${BLUE}   Estado salvo para recuperação posterior${NC}"
        else
            echo -e "${YELLOW}Processo já não está rodando${NC}"
        fi
        rm -f "$PID_FILE"
    else
        echo -e "${YELLOW}Nenhum PID encontrado${NC}"
    fi
}

show_logs() {
    print_header
    echo -e "\n${BLUE}📝 Logs em tempo real (Ctrl+C para sair)${NC}\n"
    
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}Nenhum log encontrado${NC}"
    fi
}

# Main
case "$1" in
    --status)
        show_status
        ;;
    --stop)
        stop_capture
        ;;
    --logs)
        show_logs
        ;;
    --resume)
        start_capture --resume
        ;;
    *)
        start_capture
        ;;
esac
