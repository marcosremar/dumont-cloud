#!/bin/bash
# Script para rodar testes de fluxo do Dumont Cloud

set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuração
export DUMONT_API_URL="${DUMONT_API_URL:-http://localhost:8000}"
export TEST_EMAIL="${TEST_EMAIL:-test@test.com}"
export TEST_PASSWORD="${TEST_PASSWORD:-test123}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Testes de Fluxo - Dumont Cloud${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "API URL: ${YELLOW}$DUMONT_API_URL${NC}"
echo ""

# Verificar se servidor está rodando
if ! curl -s "$DUMONT_API_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}ERRO: Servidor não está rodando em $DUMONT_API_URL${NC}"
    echo "Inicie o servidor com: cd $PROJECT_DIR && python -m uvicorn src.main:app --port 8000"
    exit 1
fi

echo -e "${GREEN}Servidor OK${NC}"
echo ""

# Função para rodar testes
run_tests() {
    local marker=$1
    local description=$2

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}  $description${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    cd "$PROJECT_DIR"

    if [ -n "$marker" ]; then
        pytest tests/flows/ -v -m "$marker" --tb=short || true
    else
        pytest tests/flows/ -v --tb=short || true
    fi

    echo ""
}

# Menu
case "${1:-menu}" in
    all)
        echo -e "${RED}ATENÇÃO: Rodando TODOS os testes (incluindo GPU real - CUSTA \$\$\$)${NC}"
        read -p "Continuar? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_tests "" "Todos os testes"
        fi
        ;;

    safe)
        run_tests "not real_gpu" "Testes seguros (sem GPU real)"
        ;;

    fast)
        run_tests "not real_gpu and not slow" "Testes rápidos"
        ;;

    flow1)
        run_tests "flow1 and not real_gpu" "Fluxo 1: Deploy de Modelos (API only)"
        ;;

    flow2)
        run_tests "flow2 and not real_gpu" "Fluxo 2: Job GPU (API only)"
        ;;

    flow3)
        run_tests "flow3 and not real_gpu" "Fluxo 3: Dev Interativo (API only)"
        ;;

    flow4)
        run_tests "flow4 and not real_gpu" "Fluxo 4: API Serverless (API only)"
        ;;

    flow5)
        run_tests "flow5 and not real_gpu" "Fluxo 5: Alta Disponibilidade"
        ;;

    flow6)
        run_tests "flow6 and not real_gpu" "Fluxo 6: Warm Pool"
        ;;

    flow7)
        run_tests "flow7" "Fluxo 7: Monitoramento"
        ;;

    flow8)
        run_tests "flow8" "Fluxo 8: Auth e Settings"
        ;;

    gpu)
        echo -e "${RED}ATENÇÃO: Rodando testes com GPU real (CUSTA \$\$\$)${NC}"
        read -p "Continuar? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_tests "real_gpu" "Testes com GPU real"
        fi
        ;;

    menu|*)
        echo "Uso: $0 <comando>"
        echo ""
        echo "Comandos disponíveis:"
        echo ""
        echo -e "  ${GREEN}safe${NC}    - Testes seguros (sem GPU real) - RECOMENDADO"
        echo -e "  ${GREEN}fast${NC}    - Testes rápidos (sem GPU, sem slow)"
        echo ""
        echo "  flow1   - Deploy de Modelos"
        echo "  flow2   - Job GPU"
        echo "  flow3   - Dev Interativo + Serverless"
        echo "  flow4   - API Inferência Serverless"
        echo "  flow5   - Alta Disponibilidade"
        echo "  flow6   - Warm Pool"
        echo "  flow7   - Monitoramento"
        echo "  flow8   - Auth e Settings"
        echo ""
        echo -e "  ${YELLOW}gpu${NC}     - Testes com GPU real (CUSTA \$\$\$)"
        echo -e "  ${RED}all${NC}     - TODOS os testes (CUSTA \$\$\$)"
        echo ""
        echo "Exemplos:"
        echo "  $0 safe         # Rodar testes seguros"
        echo "  $0 flow7        # Rodar só fluxo 7"
        echo "  $0 flow8        # Rodar só fluxo 8 (auth)"
        ;;
esac

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Testes finalizados${NC}"
echo -e "${GREEN}========================================${NC}"
