#!/bin/bash

# 🚀 Dumont Cloud - Script de Desenvolvimento Otimizado
# Detecta porta livre automaticamente e inicia o projeto

set -e

PROJECT_NAME="dumont-cloud"
DEFAULT_FRONTEND_PORT=3200
PORT_RANGE_START=3200
PORT_RANGE_END=3300
BACKEND_PORT=8767

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🚀 Dumont Cloud - Dev Environment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Função para verificar se porta está em uso
is_port_in_use() {
    lsof -i ":$1" >/dev/null 2>&1
}

# Função para encontrar porta livre
find_free_port() {
    local port=$DEFAULT_FRONTEND_PORT

    # Tenta a porta padrão primeiro
    if ! is_port_in_use $port; then
        echo $port
        return 0
    fi

    echo -e "${YELLOW}⚠️  Porta $DEFAULT_FRONTEND_PORT em uso, procurando porta livre...${NC}" >&2

    # Procura porta livre no range
    for ((port=$PORT_RANGE_START; port<=$PORT_RANGE_END; port++)); do
        if ! is_port_in_use $port; then
            echo $port
            return 0
        fi
    done

    echo -e "${RED}❌ Nenhuma porta livre encontrada no range $PORT_RANGE_START-$PORT_RANGE_END${NC}" >&2
    return 1
}

# Função para verificar se PostgreSQL está rodando (localhost OU Docker)
check_postgres() {
    # Primeiro verifica se tem PostgreSQL no localhost:5432
    if nc -z localhost 5432 2>/dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL rodando (localhost:5432)"
        return 0
    fi

    # Se não, verifica se tem container Docker
    if docker ps --format '{{.Names}}' | grep -q "dumont-cloud-db"; then
        echo -e "${GREEN}✓${NC} PostgreSQL rodando (Docker)"
        return 0
    fi

    echo -e "${YELLOW}⚠️  PostgreSQL não encontrado${NC}"
    return 1
}

# Função para verificar dependências
check_dependencies() {
    echo -e "${BLUE}📦 Verificando dependências...${NC}"

    # Verifica Bun
    if ! command -v bun &> /dev/null; then
        echo -e "${RED}❌ Bun não encontrado. Instale com: ./install-bun.sh${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Bun instalado: $(bun --version)"

    # Verifica Python venv
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}🐍 Criando virtualenv Python...${NC}"
        python3 -m venv venv
    fi
    echo -e "${GREEN}✓${NC} Python venv pronto"

    # Verifica dependências Python
    if ! ./venv/bin/pip show fastapi &> /dev/null; then
        echo -e "${YELLOW}📥 Instalando dependências Python...${NC}"
        ./venv/bin/pip install --upgrade pip -q
        ./venv/bin/pip install -r requirements.txt -q
    else
        echo -e "${GREEN}✓${NC} Dependências Python instaladas"
    fi

    # Verifica node_modules no frontend
    if [ ! -d "web/node_modules" ]; then
        echo -e "${YELLOW}📥 Instalando dependências do frontend...${NC}"
        cd web && bun install && cd ..
    else
        echo -e "${GREEN}✓${NC} Dependências do frontend instaladas"
    fi
}

# Função para verificar .env
check_env() {
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ Arquivo .env não encontrado!${NC}"
        echo -e "${YELLOW}   Copie o .env de /Users/marcos/Documents/projects/dumont-cloud/.env${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Arquivo .env presente"
}

# Função para verificar conexão com database
check_database_connection() {
    echo -e "${BLUE}🔄 Verificando conexão com database...${NC}"

    # Extrai configurações do .env
    DB_USER=$(grep "^DB_USER=" .env | cut -d '=' -f2)
    DB_PASSWORD=$(grep "^DB_PASSWORD=" .env | cut -d '=' -f2)
    DB_NAME=$(grep "^DB_NAME=" .env | cut -d '=' -f2)
    DB_HOST=$(grep "^DB_HOST=" .env | cut -d '=' -f2)
    DB_PORT=$(grep "^DB_PORT=" .env | cut -d '=' -f2)

    # Aguarda PostgreSQL estar pronto
    for i in {1..5}; do
        if ./venv/bin/python -c "import psycopg2; psycopg2.connect('postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME')" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Database conectado: ${BLUE}$DB_NAME${NC} em ${BLUE}$DB_HOST:$DB_PORT${NC}"
            return 0
        fi
        if [ $i -lt 5 ]; then
            echo -e "${YELLOW}⏳ Aguardando database ($i/5)...${NC}"
            sleep 1
        fi
    done

    echo -e "${RED}❌ Falha ao conectar ao database${NC}"
    echo -e "${YELLOW}   Verifique se o PostgreSQL está rodando em $DB_HOST:$DB_PORT${NC}"
    echo -e "${YELLOW}   Database esperado: $DB_NAME${NC}"
    exit 1
}

# Função para matar processos antigos
kill_old_processes() {
    echo -e "${BLUE}🧹 Limpando processos antigos...${NC}"

    # Mata processos na porta do backend
    if is_port_in_use $BACKEND_PORT; then
        echo -e "${YELLOW}⚠️  Matando processo na porta $BACKEND_PORT${NC}"
        lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
        sleep 1
    fi

    # Mata processos antigos do frontend no range
    for ((port=$PORT_RANGE_START; port<=$PORT_RANGE_END; port++)); do
        if is_port_in_use $port; then
            if lsof -i:$port | grep -q "node\|bun\|vite"; then
                echo -e "${YELLOW}⚠️  Matando processo Vite na porta $port${NC}"
                lsof -ti:$port | xargs kill -9 2>/dev/null || true
            fi
        fi
    done

    echo -e "${GREEN}✓${NC} Processos antigos limpos"
}

# Função principal
main() {
    # Verifica dependências
    check_dependencies

    # Verifica .env
    check_env

    # Verifica PostgreSQL
    if ! check_postgres; then
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}  ❌ PostgreSQL não está rodando${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${YELLOW}Este projeto usa um PostgreSQL EXISTENTE com dados.${NC}"
        echo ""
        echo -e "Você pode:"
        echo -e "  1. ${BLUE}Usar o PostgreSQL da VM/OrbStack${NC}"
        echo -e "     (recomendado - mantém seus dados)"
        echo ""
        echo -e "  2. ${BLUE}Criar um container Docker local${NC}"
        echo -e "     ${YELLOW}(banco vazio - para desenvolvimento local)${NC}"
        echo ""
        read -p "Qual opção? (1/2): " -n 1 -r
        echo ""

        if [[ $REPLY == "2" ]]; then
            echo -e "${BLUE}🐘 Criando PostgreSQL no Docker...${NC}"
            docker run -d \
                --name dumont-cloud-db \
                -e POSTGRES_USER=dumont \
                -e POSTGRES_PASSWORD=dumont123 \
                -e POSTGRES_DB=dumont_cloud \
                -p 5432:5432 \
                -v dumont-cloud-postgres-data:/var/lib/postgresql/data \
                --restart unless-stopped \
                postgres:16-alpine

            echo -e "${GREEN}✓${NC} PostgreSQL criado"
            echo -e "${YELLOW}⏳ Aguardando PostgreSQL ficar pronto...${NC}"
            sleep 3
        else
            echo -e "${YELLOW}⚠️  Certifique-se que o PostgreSQL está rodando.${NC}"
            exit 1
        fi
    fi

    # Verifica conexão com database
    check_database_connection

    # Limpa processos antigos
    kill_old_processes

    # Encontra porta livre para o frontend
    FRONTEND_PORT=$(find_free_port)
    if [ $? -ne 0 ]; then
        exit 1
    fi

    echo -e "${GREEN}✓${NC} Porta frontend disponível: ${GREEN}$FRONTEND_PORT${NC}"

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✨ Ambiente pronto!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  🌐 Frontend: ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "  🔧 Backend:  ${BLUE}http://localhost:$BACKEND_PORT${NC}"
    echo -e "  📚 API Docs: ${BLUE}http://localhost:$BACKEND_PORT/docs${NC}"
    echo -e "  🐘 Database: ${BLUE}$DB_NAME${NC} @ ${BLUE}$DB_HOST:$DB_PORT${NC}"
    echo ""
    echo -e "${YELLOW}🚀 Iniciando servidores...${NC}"
    echo ""

    # Inicia o backend em background
    echo -e "${BLUE}🔧 Iniciando backend (FastAPI)...${NC}"
    ./venv/bin/uvicorn src.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > /tmp/dumont-backend.log 2>&1 &
    BACKEND_PID=$!

    # Aguarda backend iniciar
    sleep 2

    if ps -p $BACKEND_PID > /dev/null; then
        echo -e "${GREEN}✓${NC} Backend rodando (PID: $BACKEND_PID)"
        echo -e "${YELLOW}   Logs: tail -f /tmp/dumont-backend.log${NC}"
    else
        echo -e "${RED}❌ Falha ao iniciar backend. Veja o log: tail -f /tmp/dumont-backend.log${NC}"
        exit 1
    fi

    # Inicia o frontend com Bun
    echo -e "${BLUE}🌐 Iniciando frontend (Vite + Bun)...${NC}"
    echo ""

    cd web
    PORT=$FRONTEND_PORT bun --bun run dev --port $FRONTEND_PORT --host
}

# Trap para limpar ao sair
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Encerrando servidores...${NC}"

    # Mata o backend
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi

    echo -e "${GREEN}✓${NC} Servidores encerrados"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Executa
main
