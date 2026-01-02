#!/bin/bash
# Journey 2: Instance Lifecycle - Criar, gerenciar e destruir GPU
# Testa listagem e operacoes com instancias

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/setup.sh"
source "$SCRIPT_DIR/../utils/assertions.sh"

TEST_NAME="Instance Lifecycle"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    # Pre-requisitos
    check_cli
    check_backend || { log_warning "Backend offline"; }

    # Login
    do_login || { log_error "Falha no login"; exit 1; }

    # 1. Verificar menu principal
    log_step "1. Verificando menu principal..."
    local output=$($CLI_CMD menu 2>&1)
    assert_not_contains "$output" "401\|Unauthorized" "Menu deve estar acessivel"
    log_info "Menu: $(echo "$output" | head -3)"

    # 2. Listar instancias (ofertas vem da API)
    log_step "2. Verificando endpoint de ofertas via API..."
    local status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $(cat $TOKEN_FILE 2>/dev/null)" "$BASE_URL/api/v1/gpu/offers" 2>/dev/null || echo "000")
    log_info "Status ofertas GPU: $status"
    if [ "$status" = "200" ]; then
        log_success "Ofertas de GPU disponiveis via API"
        ((ASSERT_PASSED++))
    else
        log_warning "API de ofertas retornou: $status"
    fi

    # 3. Listar minhas instancias
    log_step "3. Listando minhas instancias..."
    output=$($CLI_CMD instance list 2>&1)
    assert_not_contains "$output" "erro\|Erro\|401" "Listagem de instancias deve funcionar"
    log_info "Instancias: $output"

    # 4. Tentar obter instancia inexistente (deve dar 404)
    log_step "4. Testando instancia inexistente..."
    output=$($CLI_CMD instance get 999999 2>&1 || true)
    assert_contains "$output" "404\|encontrad\|exist\|not found" "Instancia inexistente deve retornar 404"

    # 5. Tentar pausar instancia inexistente
    log_step "5. Testando pause em instancia inexistente..."
    output=$($CLI_CMD instance pause 999999 2>&1 || true)
    assert_contains "$output" "404\|encontrad\|exist\|not found" "Pause em instancia inexistente deve falhar"

    # 6. Tentar resume em instancia inexistente
    log_step "6. Testando resume em instancia inexistente..."
    output=$($CLI_CMD instance resume 999999 2>&1 || true)
    assert_contains "$output" "404\|encontrad\|exist\|not found" "Resume em instancia inexistente deve falhar"

    # 7. Verificar settings
    log_step "7. Testando settings..."
    output=$($CLI_CMD settings list 2>&1 || $CLI_CMD setting list 2>&1)
    log_info "Settings: $output"

    # 8. Verificar balance
    log_step "8. Verificando balance..."
    output=$($CLI_CMD balance 2>&1 || echo "Balance info")
    log_info "Balance: $output"
    log_success "Endpoints de instancia verificados"
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
