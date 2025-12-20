#!/bin/bash
# Run All CLI E2E Journey Tests
# Executa todos os testes de jornada e gera relatorio

# Nao usar set -e para continuar mesmo se testes falharem

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"
REPORT_FILE="$RESULTS_DIR/report_$(date +%Y%m%d_%H%M%S).txt"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Contadores
TOTAL=0
PASSED=0
FAILED=0

# Criar diretorio de resultados
mkdir -p "$RESULTS_DIR"

# Header
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         DUMONT CLI - E2E Journey Tests                   ║${NC}"
echo -e "${CYAN}║         $(date)                        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Iniciar relatorio
{
    echo "DUMONT CLI - E2E Journey Tests Report"
    echo "======================================"
    echo "Data: $(date)"
    echo "Host: $(hostname)"
    echo ""
} > "$REPORT_FILE"

# Funcao para executar um teste
run_test() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .sh)

    ((TOTAL++))

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}[$TOTAL] Executando: $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    local start_time=$(date +%s)
    local output_file="$RESULTS_DIR/${test_name}_output.txt"

    # Executar teste e capturar output
    if bash "$test_file" > "$output_file" 2>&1; then
        local status="PASS"
        ((PASSED++))
        echo -e "${GREEN}✓ $test_name: PASSED${NC}"
    else
        local status="FAIL"
        ((FAILED++))
        echo -e "${RED}✗ $test_name: FAILED${NC}"
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Adicionar ao relatorio
    {
        echo "Test: $test_name"
        echo "Status: $status"
        echo "Duration: ${duration}s"
        echo "Output: $output_file"
        echo "---"
    } >> "$REPORT_FILE"

    echo ""
}

# Verificar pre-requisitos
echo -e "${YELLOW}Verificando pre-requisitos...${NC}"

# Verificar CLI
if ! command -v dumont &> /dev/null; then
    echo -e "${RED}ERRO: CLI 'dumont' nao encontrado${NC}"
    echo "Instale com: pip install -e ."
    exit 1
fi
echo -e "${GREEN}✓ CLI encontrado${NC}"

# Verificar backend
if curl -s "http://localhost:8767/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend acessivel${NC}"
else
    echo -e "${YELLOW}⚠ Backend pode nao estar acessivel${NC}"
fi

echo ""

# Executar todos os testes em ordem
JOURNEY_DIR="$SCRIPT_DIR/journeys"

for test_file in "$JOURNEY_DIR"/*.sh; do
    if [ -f "$test_file" ]; then
        run_test "$test_file"
    fi
done

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

# Calcular porcentagem
if [ $TOTAL -gt 0 ]; then
    PERCENT=$((PASSED * 100 / TOTAL))
    echo -e "  Taxa de sucesso: ${CYAN}${PERCENT}%${NC}"
fi

echo ""
echo -e "  Relatorio salvo em: ${YELLOW}$REPORT_FILE${NC}"
echo ""

# Adicionar resumo ao relatorio
{
    echo ""
    echo "======================================"
    echo "RESUMO"
    echo "======================================"
    echo "Total: $TOTAL"
    echo "Passed: $PASSED"
    echo "Failed: $FAILED"
    echo "Success Rate: ${PERCENT}%"
} >> "$REPORT_FILE"

# Exit code baseado nos resultados
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Alguns testes falharam!${NC}"
    exit 1
else
    echo -e "${GREEN}Todos os testes passaram!${NC}"
    exit 0
fi
