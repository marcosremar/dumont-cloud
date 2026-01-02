#!/bin/bash
# Journey 10: Health Check
# Testa monitoramento e health checks

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/setup.sh"
source "$SCRIPT_DIR/../utils/assertions.sh"

TEST_NAME="Health Check"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    # Pre-requisitos
    check_cli

    # 1. Verificar health do backend (sem auth)
    log_step "1. Verificando health do backend..."
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
    if [ "$status" = "200" ]; then
        log_success "Backend health: OK (200)"
        ((ASSERT_PASSED++))
    else
        log_warning "Backend health status: $status"
    fi

    # 2. Verificar versao da API
    log_step "2. Verificando versao da API..."
    local output=$(curl -s "$BASE_URL/api/v1/version" 2>/dev/null || echo "{}")
    log_info "Version: $output"

    # 3. Verificar CLI version
    log_step "3. Verificando versao do CLI..."
    output=$($CLI_CMD --version 2>&1 || $CLI_CMD version 2>&1 || echo "Version")
    log_info "CLI Version: $output"

    # 4. Verificar conectividade com providers
    log_step "4. Verificando conectividade com providers..."
    output=$($CLI_CMD health providers 2>&1 || echo "Providers check")
    log_info "Providers: $output"

    # Login para testes autenticados
    do_login || { log_warning "Login falhou, continuando testes publicos"; }

    # 5. Verificar metricas do sistema
    log_step "5. Verificando metricas do sistema..."
    output=$($CLI_CMD metrics system 2>&1 || $CLI_CMD health metrics 2>&1 || echo "Metricas")
    log_info "Metrics: $output"

    # 6. Verificar status dos agentes
    log_step "6. Verificando status dos agentes..."
    output=$($CLI_CMD agent status 2>&1 || echo "Agent status")
    log_info "Agents: $output"

    # 7. Verificar alertas ativos
    log_step "7. Verificando alertas ativos..."
    output=$($CLI_CMD alerts list 2>&1 || $CLI_CMD health alerts 2>&1 || echo "Alertas")
    log_info "Alerts: $output"

    # 8. Verificar latencia da API
    log_step "8. Verificando latencia da API..."
    local start_time=$(date +%s%N)
    curl -s "$BASE_URL/health" > /dev/null 2>&1
    local end_time=$(date +%s%N)
    local latency=$(( (end_time - start_time) / 1000000 ))
    log_info "Latencia: ${latency}ms"
    if [ "$latency" -lt 1000 ]; then
        log_success "Latencia aceitavel (<1s)"
        ((ASSERT_PASSED++))
    else
        log_warning "Latencia alta: ${latency}ms"
    fi

    # 9. Verificar endpoints principais
    log_step "9. Verificando endpoints principais..."
    local endpoints=("/api/v1/instances" "/api/v1/gpu/offers" "/api/v1/snapshots")
    local ok_count=0
    for endpoint in "${endpoints[@]}"; do
        status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $(cat $TOKEN_FILE 2>/dev/null)" "$BASE_URL$endpoint" 2>/dev/null || echo "000")
        if [ "$status" = "200" ] || [ "$status" = "401" ]; then
            ((ok_count++))
        fi
        log_info "  $endpoint: $status"
    done
    log_info "Endpoints OK: $ok_count/${#endpoints[@]}"

    # 10. Verificar disco e recursos
    log_step "10. Verificando recursos do sistema..."
    output=$($CLI_CMD health resources 2>&1 || echo "Resources check")
    log_info "Resources: $output"

    # Logout
    do_logout

    # Resumo
    print_assert_summary
    local result=$?

    finish_test "$TEST_NAME" $result
    return $result
}

main "$@"
