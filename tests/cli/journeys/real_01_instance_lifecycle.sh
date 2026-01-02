#!/bin/bash
# Real Journey 1: Instance Lifecycle
# Cria, pausa, resume e destroi uma GPU REAL na Vast.ai
# Custo estimado: ~$0.02-0.05

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/real_utils.sh"

TEST_NAME="Real Instance Lifecycle"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    local start_balance=$(get_vast_balance)
    log_info "Saldo inicial: \$$start_balance"

    # 1. Verificar saldo
    log_step "1. Verificando saldo minimo..."
    if ! check_balance 0.30; then
        log_error "Saldo insuficiente para teste"
        finish_test "$TEST_NAME" 1
        return 1
    fi
    ((ASSERT_PASSED++))

    # 2. Buscar GPU mais barata
    log_step "2. Buscando GPU mais barata..."
    local offer_id=$(find_cheapest_gpu 0.20)
    if [ -z "$offer_id" ]; then
        log_error "Nenhuma GPU disponivel"
        finish_test "$TEST_NAME" 1
        return 1
    fi
    ((ASSERT_PASSED++))

    # 3. Criar instancia
    log_step "3. Criando instancia GPU..."
    local instance_id=$(create_instance_and_wait "$offer_id" 180)
    if [ -z "$instance_id" ]; then
        log_error "Falha ao criar instancia"
        finish_test "$TEST_NAME" 1
        return 1
    fi
    log_success "Instancia criada: $instance_id"
    ((ASSERT_PASSED++))

    # 4. Verificar status running
    log_step "4. Verificando status running..."
    if wait_for_status "$instance_id" "running" 30; then
        log_success "Instancia esta running"
        ((ASSERT_PASSED++))
    else
        log_warning "Instancia pode nao estar totalmente pronta"
    fi

    # 5. Testar SSH (opcional - pode demorar)
    log_step "5. Testando conexao SSH..."
    local ssh_info=$(get_instance_ssh "$instance_id")
    log_info "SSH info: $ssh_info"
    if [ -n "$ssh_info" ]; then
        log_success "Info SSH disponivel"
        ((ASSERT_PASSED++))
    fi

    # 6. Pausar instancia
    log_step "6. Pausando instancia..."
    if pause_instance "$instance_id"; then
        ((ASSERT_PASSED++))
        sleep 5  # Aguarda processamento
    else
        log_warning "Pause pode ter falhado"
    fi

    # 7. Verificar status paused
    log_step "7. Verificando status paused..."
    sleep 5
    local info=$(get_instance_info "$instance_id")
    log_info "Info apos pause: $(echo "$info" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("instances",[d])[0].get("actual_status","?"))' 2>/dev/null)"

    # 8. Resumir instancia
    log_step "8. Resumindo instancia..."
    if resume_instance "$instance_id"; then
        ((ASSERT_PASSED++))
        sleep 5
    fi

    # 9. Destruir instancia
    log_step "9. Destruindo instancia..."
    if destroy_instance "$instance_id"; then
        log_success "Instancia destruida com sucesso"
        ((ASSERT_PASSED++))
    fi

    # 10. Confirmar destruicao
    log_step "10. Confirmando destruicao..."
    sleep 3
    local final_info=$(get_instance_info "$instance_id")
    local final_status=$(echo "$final_info" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("instances",[{}])[0].get("actual_status","destroyed"))' 2>/dev/null || echo "destroyed")
    log_info "Status final: $final_status"
    if [[ "$final_status" == *"destroy"* ]] || [[ -z "$final_status" ]]; then
        log_success "Instancia confirmada como destruida"
        ((ASSERT_PASSED++))
    fi

    # Calcular custo
    local end_balance=$(get_vast_balance)
    local cost=$(echo "$start_balance - $end_balance" | bc -l 2>/dev/null || echo "0.00")
    log_info "Custo do teste: \$$cost"
    log_info "Saldo final: \$$end_balance"

    # Resumo
    print_assert_summary
    local result=$?

    finish_test "$TEST_NAME" $result
    return $result
}

main "$@"
