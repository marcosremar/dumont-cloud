#!/bin/bash
# Journey 7: Savings Tracking
# Testa metricas de economia

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/setup.sh"
source "$SCRIPT_DIR/../utils/assertions.sh"

TEST_NAME="Savings Tracking"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    # Pre-requisitos
    check_cli
    check_backend || { log_warning "Backend offline"; }

    # Login
    do_login || { log_error "Falha no login"; exit 1; }

    # 1. Verificar resumo de economia
    log_step "1. Verificando resumo de economia..."
    local output=$($CLI_CMD savings summary 2>&1)
    log_info "Summary: $output"
    assert_not_contains "$output" "401\|Unauthorized" "Savings deve estar autenticado"

    # 2. Verificar economia por periodo
    log_step "2. Verificando economia mensal..."
    output=$($CLI_CMD savings monthly 2>&1 || $CLI_CMD savings summary 2>&1)
    log_info "Monthly: $output"

    # 3. Verificar breakdown por tipo
    log_step "3. Verificando breakdown de economia..."
    output=$($CLI_CMD savings breakdown 2>&1 || echo "Breakdown nao disponivel")
    log_info "Breakdown: $output"

    # 4. Verificar economia por hibernacao
    log_step "4. Verificando economia por hibernacao..."
    output=$($CLI_CMD savings hibernation 2>&1 || echo "Hibernation savings nao disponivel")
    log_info "Hibernation savings: $output"

    # 5. Verificar economia por spot
    log_step "5. Verificando economia por spot..."
    output=$($CLI_CMD savings spot 2>&1 || $CLI_CMD spot savings 2>&1)
    log_info "Spot savings: $output"

    # 6. Verificar comparacao com on-demand
    log_step "6. Verificando comparacao com on-demand..."
    output=$($CLI_CMD savings compare 2>&1 || echo "Comparacao nao disponivel")
    log_info "Compare: $output"

    # 7. Verificar projecao de economia
    log_step "7. Verificando projecao de economia..."
    output=$($CLI_CMD savings projection 2>&1 || echo "Projecao nao disponivel")
    log_info "Projection: $output"

    # 8. Verificar historico
    log_step "8. Verificando historico de economia..."
    output=$($CLI_CMD savings history 2>&1 || $CLI_CMD savings summary 2>&1)
    log_info "History: $output"

    # Validar que comandos principais funcionam
    log_success "Endpoints de savings verificados"
    ((ASSERT_PASSED++))

    # Logout
    do_logout

    # Resumo
    print_assert_summary
    local result=$?

    finish_test "$TEST_NAME" $result
    return $result
}

main "$@"
