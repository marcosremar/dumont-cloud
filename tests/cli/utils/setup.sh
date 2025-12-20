#!/bin/bash
# Test Setup Utilities
# Configuracao comum para todos os testes E2E do CLI

# Nao usar set -e para permitir assertions que falham

# Cores para output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export NC='\033[0m' # No Color

# Configuracoes
export CLI_CMD="dumont"
export BASE_URL="${DUMONT_API_URL:-http://localhost:8767}"
export TEST_EMAIL="${DUMONT_TEST_EMAIL:-marcosremar@gmail.com}"
export TEST_PASSWORD="${DUMONT_TEST_PASSWORD:-123456}"
export RESULTS_DIR="$(dirname "$0")/../results"
export TOKEN_FILE="$HOME/.dumont_token"

# Criar diretorio de resultados
mkdir -p "$RESULTS_DIR"

# Funcao para log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_step() {
    echo -e "${YELLOW}[STEP]${NC} $1"
}

# Verificar se CLI esta instalado
check_cli() {
    if ! command -v $CLI_CMD &> /dev/null; then
        log_error "CLI '$CLI_CMD' nao encontrado. Instale com: pip install -e ."
        exit 1
    fi
    log_success "CLI encontrado: $(which $CLI_CMD)"
}

# Verificar se backend esta rodando
check_backend() {
    if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
        log_warning "Backend nao acessivel em $BASE_URL"
        return 1
    fi
    log_success "Backend acessivel em $BASE_URL"
    return 0
}

# Login para testes
do_login() {
    log_step "Fazendo login com $TEST_EMAIL..."
    local result=$($CLI_CMD auth login "$TEST_EMAIL" "$TEST_PASSWORD" 2>&1)
    if echo "$result" | grep -q "sucesso\|Login\|token"; then
        log_success "Login realizado"
        return 0
    else
        log_error "Falha no login: $result"
        return 1
    fi
}

# Logout
do_logout() {
    log_step "Fazendo logout..."
    $CLI_CMD auth logout 2>&1 || true
    log_success "Logout realizado"
}

# Verificar se esta autenticado
check_auth() {
    if [ -f "$TOKEN_FILE" ]; then
        log_success "Token encontrado"
        return 0
    else
        log_warning "Token nao encontrado"
        return 1
    fi
}

# Inicializar teste
init_test() {
    local test_name="$1"
    echo ""
    echo "=============================================="
    echo -e "${BLUE}Teste: $test_name${NC}"
    echo "=============================================="
    echo "Inicio: $(date)"
    echo ""
}

# Finalizar teste
finish_test() {
    local test_name="$1"
    local status="$2"
    echo ""
    if [ "$status" = "0" ]; then
        log_success "Teste '$test_name' completado com sucesso!"
    else
        log_error "Teste '$test_name' falhou!"
    fi
    echo "Fim: $(date)"
    echo "=============================================="
}
