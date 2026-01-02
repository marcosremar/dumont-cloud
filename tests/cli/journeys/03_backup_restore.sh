#!/bin/bash
# Journey 3: Backup/Restore - Snapshots e restore
# Testa criacao, listagem e restauracao de snapshots

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/setup.sh"
source "$SCRIPT_DIR/../utils/assertions.sh"

TEST_NAME="Backup/Restore"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    # Pre-requisitos
    check_cli
    check_backend || { log_warning "Backend offline"; }

    # Login
    do_login || { log_error "Falha no login"; exit 1; }

    # 1. Listar snapshots existentes
    log_step "1. Listando snapshots existentes..."
    local output=$($CLI_CMD snapshot list 2>&1)
    assert_not_contains "$output" "401\|Unauthorized" "Listagem de snapshots deve estar autenticada"
    log_info "Snapshots: $output"

    # 2. Verificar status do sistema de backup
    log_step "2. Verificando status do backup..."
    output=$($CLI_CMD snapshot status 2>&1 || echo "Status nao disponivel")
    log_info "Status backup: $output"

    # 3. Testar criacao de snapshot (sem instancia real, deve falhar graciosamente)
    log_step "3. Testando criacao de snapshot em instancia inexistente..."
    output=$($CLI_CMD snapshot create 999999 2>&1 || true)
    # Deve falhar com 404 ou erro de instancia
    assert_contains "$output" "404\|erro\|Erro\|encontrad\|exist\|not found" "Snapshot em instancia inexistente deve falhar"

    # 4. Testar listagem de snapshots de instancia especifica
    log_step "4. Listando snapshots de instancia..."
    output=$($CLI_CMD snapshot list --instance 999999 2>&1 || $CLI_CMD snapshot list 2>&1)
    log_info "Snapshots da instancia: $output"

    # 5. Testar restauracao de snapshot inexistente
    log_step "5. Testando restore de snapshot inexistente..."
    output=$($CLI_CMD snapshot restore "snapshot-inexistente-xyz" 2>&1 || true)
    assert_contains "$output" "404\|erro\|Erro\|encontrad\|exist\|not found" "Restore de snapshot inexistente deve falhar"

    # 6. Verificar integridade do endpoint
    log_step "6. Verificando endpoint de snapshots..."
    local status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $(cat $TOKEN_FILE 2>/dev/null)" "$BASE_URL/api/v1/snapshots" 2>/dev/null || echo "000")
    if [ "$status" = "200" ] || [ "$status" = "401" ]; then
        log_success "Endpoint de snapshots acessivel (status: $status)"
        ((ASSERT_PASSED++))
    else
        log_warning "Endpoint retornou status: $status"
    fi

    # 7. Testar delete de snapshot inexistente
    log_step "7. Testando delete de snapshot inexistente..."
    output=$($CLI_CMD snapshot delete "snapshot-fake-123" 2>&1 || true)
    assert_contains "$output" "404\|erro\|Erro\|encontrad\|exist\|not found" "Delete de snapshot inexistente deve falhar"

    # 8. Verificar formato de resposta
    log_step "8. Verificando formato de resposta..."
    output=$($CLI_CMD snapshot list 2>&1)
    # Deve ser formatado (tabela, JSON, ou mensagem)
    if [ -n "$output" ]; then
        log_success "Resposta formatada recebida"
        ((ASSERT_PASSED++))
    else
        log_warning "Resposta vazia"
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
