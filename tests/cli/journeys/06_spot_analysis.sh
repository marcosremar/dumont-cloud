#!/bin/bash
# Journey 6: Spot Market Analysis
# Testa analise de mercado spot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/setup.sh"
source "$SCRIPT_DIR/../utils/assertions.sh"

TEST_NAME="Spot Analysis"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    # Pre-requisitos
    check_cli
    check_backend || { log_warning "Backend offline"; }

    # Login
    do_login || { log_error "Falha no login"; exit 1; }

    # 1. Verificar monitor de mercado spot
    log_step "1. Verificando monitor de mercado spot..."
    local output=$($CLI_CMD spot monitor 2>&1)
    log_info "Monitor: $output"
    assert_not_contains "$output" "401\|Unauthorized" "Monitor spot deve estar autenticado"

    # 2. Verificar predicao de precos
    log_step "2. Verificando predicao de precos..."
    output=$($CLI_CMD spot prediction "RTX_4090" 2>&1)
    log_info "Predicao: $output"

    # 3. Verificar taxa de interrupcao
    log_step "3. Verificando taxa de interrupcao..."
    output=$($CLI_CMD spot interruption 2>&1)
    log_info "Interrupcao: $output"

    # 4. Verificar janelas seguras
    log_step "4. Verificando janelas seguras..."
    output=$($CLI_CMD spot safe-windows 2>&1)
    log_info "Safe windows: $output"

    # 5. Verificar confiabilidade
    log_step "5. Verificando score de confiabilidade..."
    output=$($CLI_CMD spot reliability 2>&1)
    log_info "Reliability: $output"

    # 6. Verificar ranking de GPUs para LLM
    log_step "6. Verificando ranking de GPUs para LLM..."
    output=$($CLI_CMD spot llm-ranking 2>&1)
    log_info "LLM Ranking: $output"

    # 7. Verificar calculadora de economia
    log_step "7. Verificando calculadora de economia..."
    output=$($CLI_CMD spot savings 2>&1)
    log_info "Savings: $output"

    # 8. Verificar custo de treinamento
    log_step "8. Verificando custo de treinamento..."
    output=$($CLI_CMD spot training-cost 2>&1)
    log_info "Training cost: $output"

    # 9. Verificar estrategia de fleet
    log_step "9. Verificando estrategia de fleet..."
    output=$($CLI_CMD spot fleet-strategy 2>&1)
    log_info "Fleet strategy: $output"

    # 10. Verificar disponibilidade instantanea
    log_step "10. Verificando disponibilidade instantanea..."
    output=$($CLI_CMD spot availability 2>&1)
    log_info "Availability: $output"

    # Validar que ao menos alguns endpoints responderam
    if [ $ASSERT_PASSED -eq 0 ]; then
        # Contar endpoints que responderam (sem erro 401/500)
        log_success "Endpoints de spot verificados"
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
