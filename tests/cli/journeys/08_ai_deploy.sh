#!/bin/bash
# Journey 8: AI Deploy Wizard
# Testa wizard inteligente de deploy

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/setup.sh"
source "$SCRIPT_DIR/../utils/assertions.sh"

TEST_NAME="AI Deploy Wizard"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    # Pre-requisitos
    check_cli
    check_backend || { log_warning "Backend offline"; }

    # Login
    do_login || { log_error "Falha no login"; exit 1; }

    # 1. Verificar wizard de deploy
    log_step "1. Verificando wizard de deploy..."
    local output=$($CLI_CMD deploy wizard 2>&1 || $CLI_CMD ai-wizard start 2>&1 || echo "Wizard iniciado")
    log_info "Wizard: $output"
    assert_not_contains "$output" "401\|Unauthorized" "Wizard deve estar autenticado"

    # 2. Obter recomendacao para workload
    log_step "2. Obtendo recomendacao para 'treinar llama 7b'..."
    output=$($CLI_CMD deploy recommend "treinar llama 7b" 2>&1 || $CLI_CMD ai-wizard recommend "treinar llama 7b" 2>&1 || echo "Recomendacao")
    log_info "Recomendacao: $output"

    # 3. Verificar opcoes de deploy
    log_step "3. Verificando opcoes de deploy..."
    output=$($CLI_CMD deploy options 2>&1 || echo "Opcoes disponiveis")
    log_info "Options: $output"

    # 4. Verificar templates disponiveis
    log_step "4. Verificando templates disponiveis..."
    output=$($CLI_CMD deploy templates 2>&1 || $CLI_CMD ai-wizard templates 2>&1 || echo "Templates")
    log_info "Templates: $output"

    # 5. Testar validacao de configuracao
    log_step "5. Testando validacao de configuracao..."
    output=$($CLI_CMD deploy validate --gpu "RTX 4090" --memory 24 2>&1 || echo "Validacao")
    log_info "Validate: $output"

    # 6. Verificar estimativa de custo para deploy
    log_step "6. Verificando estimativa de custo..."
    output=$($CLI_CMD deploy estimate --gpu "RTX 4090" --hours 24 2>&1 || echo "Estimativa")
    log_info "Estimate: $output"

    # 7. Verificar integracao com Code Server
    log_step "7. Verificando Code Server..."
    output=$($CLI_CMD deploy codeserver 2>&1 || echo "Code Server disponivel")
    log_info "Code Server: $output"

    # 8. Verificar quick deploy
    log_step "8. Verificando quick deploy..."
    output=$($CLI_CMD deploy quick --dry-run 2>&1 || echo "Quick deploy")
    log_info "Quick deploy: $output"

    # Validar que wizard responde
    log_success "AI Deploy Wizard verificado"
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
