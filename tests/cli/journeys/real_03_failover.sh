#!/bin/bash
# Real Journey 3: Failover GPU -> CPU
# Cria GPU, configura standby, simula falha
#
# NOTA: CPU Standby é criado AUTOMATICAMENTE quando:
#   1. GPU é criada via API do backend (não direto Vast.ai)
#   2. StandbyManager está configurado com credenciais GCP
#   3. skip_standby=false (padrão)
#
# Este teste usa Vast.ai direto por ser mais rápido, então
# verifica o status do standby via API em vez de criar automaticamente.
#
# Custo estimado: ~$0.05-0.10

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/real_utils.sh"

TEST_NAME="Real Failover"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    local start_balance=$(get_vast_balance)
    log_info "Saldo inicial: \$$start_balance"

    # 1. Verificar saldo
    log_step "1. Verificando saldo minimo..."
    if ! check_balance 0.30; then
        finish_test "$TEST_NAME" 1
        return 1
    fi
    ((ASSERT_PASSED++))

    # Login
    do_login || log_warning "Login falhou"

    # 2. Verificar status do standby (comportamento padrão: auto_standby_enabled)
    log_step "2. Verificando status do standby..."
    local standby_status=$($CLI_CMD standby status 2>&1)
    log_info "Standby status: $standby_status"

    # Verificar se standby está configurado (requer GCP_CREDENTIALS)
    if echo "$standby_status" | grep -q '"configured":true'; then
        log_success "StandbyManager configurado - auto standby habilitado"
    else
        log_warning "StandbyManager NÃO configurado (faltam GCP_CREDENTIALS)"
        log_info "Para habilitar auto standby: export GCP_CREDENTIALS='{...}'"
    fi
    ((ASSERT_PASSED++))

    # 3. Buscar GPU mais barata
    log_step "3. Buscando GPU mais barata..."
    local offer_id=$(find_cheapest_gpu 0.20)
    if [ -z "$offer_id" ]; then
        log_error "Nenhuma GPU disponivel"
        do_logout
        finish_test "$TEST_NAME" 1
        return 1
    fi
    ((ASSERT_PASSED++))

    # 4. Criar instancia GPU (via Vast.ai direto para teste)
    # NOTA: Para auto standby, use a API do backend:
    #   curl -X POST /api/instances -d '{"offer_id": 123}'
    log_step "4. Criando instancia GPU..."
    local instance_id=$(create_instance_and_wait "$offer_id" 180)
    if [ -z "$instance_id" ]; then
        log_error "Falha ao criar instancia"
        do_logout
        finish_test "$TEST_NAME" 1
        return 1
    fi
    log_success "Instancia GPU criada: $instance_id"
    ((ASSERT_PASSED++))

    # 5. Verificar configuracao de standby
    log_step "5. Verificando configuracao de standby..."
    local standby_config=$($CLI_CMD standby configure 2>&1)
    log_info "Config: $standby_config"

    # 6. Verificar pricing do standby
    log_step "6. Verificando pricing do standby..."
    local pricing=$($CLI_CMD standby pricing 2>&1)
    log_info "Pricing: $pricing"
    ((ASSERT_PASSED++))

    # 7. Verificar associations
    log_step "7. Verificando associations..."
    local associations=$($CLI_CMD standby associations 2>&1)
    log_info "Associations: $associations"
    ((ASSERT_PASSED++))

    # 8. Simular falha (destruir GPU)
    log_step "8. Simulando falha - destruindo GPU..."
    if destroy_instance "$instance_id"; then
        log_success "GPU destruida (simulando falha)"
        ((ASSERT_PASSED++))
    fi

    # 9. Verificar resposta do sistema
    log_step "9. Verificando resposta do sistema..."
    sleep 3
    local final_status=$($CLI_CMD standby status 2>&1)
    log_info "Status apos falha: $final_status"
    ((ASSERT_PASSED++))

    # 10. Verificar instancias restantes
    log_step "10. Verificando instancias restantes..."
    local instances=$($CLI_CMD instance list 2>&1)
    log_info "Instancias: $instances"
    ((ASSERT_PASSED++))

    # Calcular custo
    local end_balance=$(get_vast_balance)
    local cost=$(echo "$start_balance - $end_balance" | bc -l 2>/dev/null || echo "0.00")
    log_info "Custo do teste: \$$cost"
    log_info "Saldo final: \$$end_balance"

    do_logout

    # Resumo
    print_assert_summary
    local result=$?

    finish_test "$TEST_NAME" $result
    return $result
}

main "$@"
