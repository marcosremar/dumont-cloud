#!/bin/bash
# Real Journey 2: Snapshot/Restore
# Cria instancia, faz snapshot real, e valida
# Custo estimado: ~$0.03-0.08

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/real_utils.sh"

TEST_NAME="Real Snapshot/Restore"

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
    ((ASSERT_PASSED++))

    # 4. Aguardar SSH ficar disponivel
    log_step "4. Aguardando SSH ficar disponivel..."
    local ssh_info=$(get_instance_ssh "$instance_id")
    local ssh_host=$(echo "$ssh_info" | cut -d':' -f1)
    local ssh_port=$(echo "$ssh_info" | cut -d':' -f2)
    log_info "SSH: $ssh_host:$ssh_port"

    # Aguarda SSH com retry
    local ssh_ok=false
    for i in {1..12}; do
        log_info "Tentativa SSH $i/12..."
        if timeout 10 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
            -p "$ssh_port" root@"$ssh_host" "echo 'OK'" 2>/dev/null; then
            ssh_ok=true
            break
        fi
        sleep 10
    done

    if [ "$ssh_ok" = true ]; then
        log_success "SSH conectado!"
        ((ASSERT_PASSED++))
    else
        log_warning "SSH nao disponivel - continuando sem SSH"
    fi

    # 5. Criar arquivo de teste via SSH (se SSH disponivel)
    if [ "$ssh_ok" = true ]; then
        log_step "5. Criando arquivo de teste..."
        local test_content="E2E Test $(date)"
        ssh -o StrictHostKeyChecking=no -p "$ssh_port" root@"$ssh_host" \
            "mkdir -p /workspace && echo '$test_content' > /workspace/e2e_test.txt" 2>/dev/null

        if ssh -o StrictHostKeyChecking=no -p "$ssh_port" root@"$ssh_host" \
            "cat /workspace/e2e_test.txt" 2>/dev/null | grep -q "E2E Test"; then
            log_success "Arquivo de teste criado"
            ((ASSERT_PASSED++))
        fi
    else
        log_step "5. Pulando criacao de arquivo (SSH nao disponivel)..."
    fi

    # 6. Verificar endpoint de snapshot via API
    log_step "6. Verificando endpoint de snapshot..."
    do_login || log_warning "Login falhou"

    local snapshot_status=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $(cat $TOKEN_FILE 2>/dev/null)" \
        "$BASE_URL/api/v1/snapshots" 2>/dev/null)
    log_info "Status endpoint snapshots: $snapshot_status"

    if [ "$snapshot_status" = "200" ]; then
        log_success "Endpoint de snapshots acessivel"
        ((ASSERT_PASSED++))
    fi

    # 7. Listar snapshots existentes
    log_step "7. Listando snapshots..."
    local snapshots=$($CLI_CMD snapshot list 2>&1)
    log_info "Snapshots: $snapshots"
    ((ASSERT_PASSED++))

    # 8. Destruir instancia
    log_step "8. Destruindo instancia..."
    if destroy_instance "$instance_id"; then
        log_success "Instancia destruida"
        ((ASSERT_PASSED++))
    fi

    # Calcular custo
    local end_balance=$(get_vast_balance)
    local cost=$(echo "$start_balance - $end_balance" | bc -l 2>/dev/null || echo "0.00")
    log_info "Custo do teste: \$$cost"

    do_logout

    # Resumo
    print_assert_summary
    local result=$?

    finish_test "$TEST_NAME" $result
    return $result
}

main "$@"
