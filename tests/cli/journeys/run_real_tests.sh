#!/bin/bash
# Run Real E2E Tests
# Executa testes que criam recursos REAIS na Vast.ai
# ATENCAO: Estes testes CUSTAM DINHEIRO!

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Vast.ai config
VAST_API_KEY="${VAST_API_KEY:-a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd}"
VAST_API_URL="https://console.vast.ai/api/v0"
MIN_BALANCE="0.50"

# Contadores
TOTAL=0
PASSED=0
FAILED=0
TOTAL_COST=0

echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║     ATENCAO: TESTES REAIS - CUSTAM DINHEIRO REAL!        ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar saldo
echo -e "${YELLOW}Verificando saldo Vast.ai...${NC}"
BALANCE=$(curl -s "${VAST_API_URL}/users/current/?api_key=${VAST_API_KEY}" 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d.get(\"credit\", 0):.2f}')" 2>/dev/null)

if [ -z "$BALANCE" ]; then
    echo -e "${RED}ERRO: Nao foi possivel verificar saldo${NC}"
    exit 1
fi

echo -e "${GREEN}Saldo atual: \$$BALANCE${NC}"

# Verificar saldo minimo
if (( $(echo "$BALANCE < $MIN_BALANCE" | bc -l) )); then
    echo -e "${RED}ERRO: Saldo insuficiente. Minimo: \$$MIN_BALANCE${NC}"
    exit 1
fi

# Confirmar execucao
echo ""
echo -e "${YELLOW}Voce esta prestes a executar testes que:${NC}"
echo "  - Criam instancias GPU reais na Vast.ai"
echo "  - Podem custar ate ~\$0.15"
echo "  - Levam ~10-15 minutos para completar"
echo ""
read -p "Continuar? (s/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${YELLOW}Testes cancelados.${NC}"
    exit 0
fi

START_BALANCE="$BALANCE"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         REAL E2E Tests - Vast.ai                         ║${NC}"
echo -e "${CYAN}║         $(date)                        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Funcao para executar teste
run_test() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .sh)

    ((TOTAL++))

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}[$TOTAL] Executando: $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    local start_time=$(date +%s)

    # Executar teste
    if bash "$test_file"; then
        ((PASSED++))
        echo -e "${GREEN}✓ $test_name: PASSED${NC}"
    else
        ((FAILED++))
        echo -e "${RED}✗ $test_name: FAILED${NC}"
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    echo -e "${BLUE}Duracao: ${duration}s${NC}"
}

# Executar testes reais
run_test "$SCRIPT_DIR/real_01_instance_lifecycle.sh"
run_test "$SCRIPT_DIR/real_02_snapshot_restore.sh"
run_test "$SCRIPT_DIR/real_03_failover.sh"

# Teste E2E COMPLETO de failover (o mais importante!)
echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}  🚀 TESTE PRINCIPAL: Complete E2E Failover              ${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
run_test "$SCRIPT_DIR/real_05_complete_failover_e2e.sh"

# Calcular custo total
END_BALANCE=$(curl -s "${VAST_API_URL}/users/current/?api_key=${VAST_API_KEY}" 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d.get(\"credit\", 0):.2f}')" 2>/dev/null)

TOTAL_COST=$(echo "$START_BALANCE - $END_BALANCE" | bc -l 2>/dev/null || echo "0.00")

# Resumo final
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    RESUMO FINAL                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Total de testes: ${BLUE}$TOTAL${NC}"
echo -e "  Passou:          ${GREEN}$PASSED${NC}"
echo -e "  Falhou:          ${RED}$FAILED${NC}"
echo ""
echo -e "  ${YELLOW}CUSTO TOTAL: \$$TOTAL_COST${NC}"
echo -e "  Saldo inicial: \$$START_BALANCE"
echo -e "  Saldo final:   \$$END_BALANCE"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Alguns testes falharam!${NC}"
    exit 1
else
    echo -e "${GREEN}Todos os testes passaram!${NC}"
    exit 0
fi
