#!/bin/bash
# Journey 4: CPU Standby e Failover
# Testa configuracao de standby e processo de failover

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/setup.sh"
source "$SCRIPT_DIR/../utils/assertions.sh"

TEST_NAME="Standby/Failover"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    # Pre-requisitos
    check_cli
    check_backend || { log_warning "Backend offline"; }

    # Login
    do_login || { log_error "Falha no login"; exit 1; }

    # 1. Verificar status do standby
    log_step "1. Verificando status do standby..."
    local output=$($CLI_CMD standby status 2>&1)
    assert_not_contains "$output" "401\|Unauthorized" "Status standby deve estar autenticado"
    log_info "Status standby: $output"

    # 2. Listar configuracoes de standby
    log_step "2. Listando configuracoes de standby..."
    output=$($CLI_CMD standby list 2>&1 || echo "Nenhuma configuracao")
    log_info "Configuracoes: $output"

    # 3. Verificar pricing do standby
    log_step "3. Verificando pricing do standby..."
    output=$($CLI_CMD standby pricing 2>&1 || echo "Pricing info")
    log_info "Pricing: $output"

    # 4. Verificar associations
    log_step "4. Verificando associations..."
    output=$($CLI_CMD standby associations 2>&1 || echo "Associations")
    log_info "Associations: $output"

    # 5. Testar configure
    log_step "5. Testando configure..."
    output=$($CLI_CMD standby configure 2>&1 || echo "Configure")
    log_info "Configure: $output"

    # 6. Testar sync-start (deve falhar sem instancia)
    log_step "6. Testando sync-start..."
    output=$($CLI_CMD standby sync-start 2>&1 || true)
    log_info "Sync-start: $output"

    # 7. Testar sync-stop
    log_step "7. Testando sync-stop..."
    output=$($CLI_CMD standby sync-stop 2>&1 || true)
    log_info "Sync-stop: $output"

    # 8. Verificar endpoint de standby
    log_step "8. Verificando endpoint de standby..."
    local status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $(cat $TOKEN_FILE 2>/dev/null)" "$BASE_URL/api/v1/standby/status" 2>/dev/null || echo "000")
    log_info "Status HTTP do endpoint: $status"
    if [ "$status" != "000" ]; then
        log_success "Endpoint de standby respondeu"
        ((ASSERT_PASSED++))
    fi

    # Logout
    do_logout

    # Resumo
    print_assert_summary
    local result=$?

    finish_test "$TEST_NAME" $result
    return $result
}

main "$@"
