#!/bin/bash
#
# Script para executar testes de failover REAIS no Dumont Cloud
#
# ATENÇÃO: Este script USA CRÉDITOS REAIS da VAST.ai e Backblaze B2!
#
# Uso:
#   ./run_failover_tests.sh             # Executa todos os testes
#   ./run_failover_tests.sh --quick     # Apenas testes rápidos (sem GPUs)
#   ./run_failover_tests.sh --dry-run   # Mostra o que seria executado
#

set -e  # Exit on error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

# Parse argumentos
DRY_RUN=false
QUICK_MODE=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --quick)
            QUICK_MODE=true
            ;;
        --help|-h)
            echo "Uso: $0 [OPTIONS]"
            echo ""
            echo "Opções:"
            echo "  --quick     Executa apenas testes rápidos (sem criar GPUs)"
            echo "  --dry-run   Mostra comandos sem executar"
            echo "  --help      Mostra esta mensagem"
            echo ""
            echo "Variáveis de ambiente necessárias:"
            echo "  VAST_API_KEY         - API key da VAST.ai"
            echo "  B2_ENDPOINT          - Endpoint do Backblaze B2"
            echo "  B2_BUCKET            - Bucket do B2"
            echo "  DUMONT_API_URL       - URL do backend (default: http://localhost:8766)"
            exit 0
            ;;
    esac
done

# Banner
echo ""
echo "======================================================================="
echo "  DUMONT CLOUD - BATERIA DE TESTES DE FAILOVER REAIS"
echo "======================================================================="
echo ""

# Verificar variáveis de ambiente
echo -e "${YELLOW}[1/7] Verificando pré-requisitos...${NC}"

if [ -z "$VAST_API_KEY" ]; then
    echo -e "${RED}✗ VAST_API_KEY não configurado${NC}"
    echo "  Configure: export VAST_API_KEY='your_key'"
    exit 1
fi

if [ -z "$B2_ENDPOINT" ]; then
    echo -e "${YELLOW}⚠ B2_ENDPOINT não configurado, usando default${NC}"
    export B2_ENDPOINT="https://s3.us-west-004.backblazeb2.com"
fi

if [ -z "$B2_BUCKET" ]; then
    echo -e "${YELLOW}⚠ B2_BUCKET não configurado, usando default${NC}"
    export B2_BUCKET="dumoncloud-snapshot"
fi

if [ -z "$DUMONT_API_URL" ]; then
    echo -e "${YELLOW}⚠ DUMONT_API_URL não configurado, usando default${NC}"
    export DUMONT_API_URL="http://localhost:8766"
fi

echo -e "${GREEN}✓ Variáveis de ambiente OK${NC}"
echo "  VAST_API_KEY: ${VAST_API_KEY:0:10}..."
echo "  B2_ENDPOINT: $B2_ENDPOINT"
echo "  B2_BUCKET: $B2_BUCKET"
echo "  DUMONT_API_URL: $DUMONT_API_URL"

# Verificar backend
echo ""
echo -e "${YELLOW}[2/7] Verificando backend...${NC}"

if $DRY_RUN; then
    echo "[DRY RUN] curl -s $DUMONT_API_URL/health"
else
    if curl -s "$DUMONT_API_URL/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend acessível${NC}"
    else
        echo -e "${RED}✗ Backend não está rodando em $DUMONT_API_URL${NC}"
        echo ""
        echo "Inicie o backend:"
        echo "  cd $PROJECT_DIR"
        echo "  source venv/bin/activate"
        echo "  uvicorn src.main:app --host 0.0.0.0 --port 8766"
        exit 1
    fi
fi

# Ativar ambiente virtual
echo ""
echo -e "${YELLOW}[3/7] Ativando ambiente virtual...${NC}"

if [ ! -d "venv" ]; then
    echo -e "${RED}✗ Ambiente virtual não encontrado${NC}"
    echo "  Crie: python3 -m venv venv"
    exit 1
fi

if $DRY_RUN; then
    echo "[DRY RUN] source venv/bin/activate"
else
    source venv/bin/activate
    echo -e "${GREEN}✓ Ambiente virtual ativado${NC}"
fi

# Instalar dependências
echo ""
echo -e "${YELLOW}[4/7] Verificando dependências...${NC}"

if $DRY_RUN; then
    echo "[DRY RUN] pip install -q pytest requests"
else
    pip install -q pytest requests > /dev/null 2>&1
    echo -e "${GREEN}✓ Dependências instaladas${NC}"
fi

# Verificar saldo VAST.ai
echo ""
echo -e "${YELLOW}[5/7] Verificando saldo VAST.ai...${NC}"

if $DRY_RUN; then
    echo "[DRY RUN] curl -H 'Authorization: Bearer \$VAST_API_KEY' https://cloud.vast.ai/api/v0/users/current/"
else
    BALANCE=$(curl -s -H "Authorization: Bearer $VAST_API_KEY" \
        https://cloud.vast.ai/api/v0/users/current/ | \
        python3 -c "import sys, json; print(json.load(sys.stdin).get('balance', 'N/A'))" 2>/dev/null || echo "N/A")

    if [ "$BALANCE" != "N/A" ]; then
        echo -e "${GREEN}✓ Saldo disponível: \$$BALANCE${NC}"

        # Avisar se saldo baixo
        if (( $(echo "$BALANCE < 1.0" | bc -l) )); then
            echo -e "${YELLOW}⚠ Saldo baixo! Testes podem falhar por falta de créditos.${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Não foi possível verificar saldo${NC}"
    fi
fi

# Executar testes
echo ""
echo -e "${YELLOW}[6/7] Executando testes de failover...${NC}"
echo ""

if $QUICK_MODE; then
    echo -e "${YELLOW}Modo RÁPIDO: Apenas testes sem criar GPUs${NC}"
    TEST_MARKERS="-m 'not slow'"
else
    echo -e "${RED}ATENÇÃO: Testes COMPLETOS - VAI CRIAR GPUS REAIS!${NC}"
    echo ""
    echo "Estimativa de custo: ~\$0.10 - \$0.50"
    echo "Tempo estimado: 15-30 minutos"
    echo ""
    read -p "Continuar? (yes/no): " -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Cancelado pelo usuário."
        exit 0
    fi

    TEST_MARKERS=""
fi

# Comandos de teste
TEST_CMD="pytest cli/tests/test_real_failover_complete.py -v -s --tb=short $TEST_MARKERS"

if $DRY_RUN; then
    echo "[DRY RUN] $TEST_CMD"
else
    echo "Executando: $TEST_CMD"
    echo ""

    # Executar com timestamp
    START_TIME=$(date +%s)

    if $TEST_CMD; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))

        echo ""
        echo -e "${GREEN}✓ Testes concluídos com sucesso!${NC}"
        echo "  Tempo total: ${DURATION}s"
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))

        echo ""
        echo -e "${RED}✗ Alguns testes falharam${NC}"
        echo "  Tempo total: ${DURATION}s"
        echo ""
        echo "Verifique logs para detalhes."
        exit 1
    fi
fi

# Relatório final
echo ""
echo -e "${YELLOW}[7/7] Gerando relatório...${NC}"

if $DRY_RUN; then
    echo "[DRY RUN] Relatório seria gerado aqui"
else
    # Verificar se há arquivo de métricas
    if [ -f "cli/tests/failover_test_metrics.json" ]; then
        echo -e "${GREEN}✓ Métricas salvas em: cli/tests/failover_test_metrics.json${NC}"

        # Mostrar resumo
        echo ""
        echo "Resumo das métricas:"
        python3 -c "
import json
try:
    with open('cli/tests/failover_test_metrics.json') as f:
        metrics = json.load(f)
    if isinstance(metrics, list) and metrics:
        latest = metrics[-1]
        print(f\"  Teste: {latest.get('test_name', 'N/A')}\")
        print(f\"  Sucesso: {latest.get('success', False)}\")
        print(f\"  Arquivos validados: {latest.get('files_validated', 0)}/{len(latest.get('test_files', []))}\")
        print(f\"  Tempo total: {latest.get('time_total', 0):.1f}s\")
        print(f\"  Custo estimado: \${latest.get('estimated_cost_usd', 0):.4f}\")
except Exception as e:
    print(f'  Erro ao ler métricas: {e}')
" 2>/dev/null || echo "  Métricas não disponíveis"
    fi
fi

echo ""
echo "======================================================================="
echo "  TESTES CONCLUÍDOS"
echo "======================================================================="
echo ""

if ! $QUICK_MODE && ! $DRY_RUN; then
    echo "Recursos criados durante os testes foram deletados automaticamente."
    echo "Snapshots permanecem em B2 para auditoria."
    echo ""
    echo "Para deletar snapshots:"
    echo "  dumont snapshot list"
    echo "  dumont snapshot delete --snapshot-id <ID>"
fi

echo ""
echo "Para mais informações, consulte:"
echo "  FAILOVER_TESTING_GUIDE.md"
echo ""
