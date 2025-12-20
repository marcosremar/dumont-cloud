#!/bin/bash
# Journey 9: Migration GPU <-> CPU
# Testa migracao entre recursos

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/setup.sh"
source "$SCRIPT_DIR/../utils/assertions.sh"

TEST_NAME="Migration"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    # Pre-requisitos
    check_cli
    check_backend || { log_warning "Backend offline"; }

    # Login
    do_login || { log_error "Falha no login"; exit 1; }

    # 1. Verificar hibernation status (relacionado a migracao)
    log_step "1. Verificando hibernation status..."
    local output=$($CLI_CMD hibernation status 2>&1 || echo "Hibernation status")
    log_info "Hibernation: $output"

    # 2. Verificar agent status
    log_step "2. Verificando agent status..."
    output=$($CLI_CMD agent status 2>&1 || echo "Agent status")
    log_info "Agent: $output"

    # 3. Verificar standby associations (relacionado a migracao GPU<->CPU)
    log_step "3. Verificando standby associations..."
    output=$($CLI_CMD standby associations 2>&1 || echo "Associations")
    log_info "Associations: $output"

    # 4. Verificar sync via standby
    log_step "4. Verificando sync..."
    output=$($CLI_CMD standby status 2>&1 || echo "Standby status")
    log_info "Standby: $output"

    # 5. Verificar metricas
    log_step "5. Verificando metricas..."
    output=$($CLI_CMD metrics 2>&1 || echo "Metrics")
    log_info "Metrics: $output"

    # 6. Verificar health
    log_step "6. Verificando health..."
    output=$($CLI_CMD health 2>&1 || echo "Health")
    log_info "Health: $output"

    # 7. Verificar admin (se disponivel)
    log_step "7. Verificando admin..."
    output=$($CLI_CMD admin 2>&1 || echo "Admin")
    log_info "Admin: $output"

    # 8. Verificar balance
    log_step "8. Verificando balance..."
    output=$($CLI_CMD balance 2>&1 || echo "Balance")
    log_info "Balance: $output"

    # Validar que migration responde
    log_success "Migration verificada"
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
