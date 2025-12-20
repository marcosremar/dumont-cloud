#!/bin/bash
# Journey 1: Auth - Ciclo completo de autenticacao
# Testa login, status, e logout

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/setup.sh"
source "$SCRIPT_DIR/../utils/assertions.sh"

TEST_NAME="Auth Journey"

main() {
    init_test "$TEST_NAME"
    reset_asserts

    # Pre-requisitos
    check_cli
    check_backend || { log_warning "Backend offline - alguns testes podem falhar"; }

    # 1. Logout inicial (limpar estado)
    log_step "1. Limpando estado anterior..."
    $CLI_CMD auth logout 2>/dev/null || true
    assert_file_not_exists "$TOKEN_FILE" "Token deve ser removido apos logout"

    # 2. Tentar comando sem auth (deve falhar ou pedir login)
    log_step "2. Testando acesso sem autenticacao..."
    local output=$($CLI_CMD instance list 2>&1 || true)
    # Sem token, deve dar erro ou lista vazia/erro de auth
    log_info "Response sem auth: $output"

    # 3. Login com credenciais validas
    log_step "3. Fazendo login com credenciais validas..."
    output=$($CLI_CMD auth login "$TEST_EMAIL" "$TEST_PASSWORD" 2>&1)
    assert_contains "$output" "sucesso\|Login\|token\|Autenticado" "Login deve retornar sucesso"
    assert_file_exists "$TOKEN_FILE" "Token deve ser salvo apos login"

    # 4. Verificar status de autenticacao (usando 'me' em vez de 'status')
    log_step "4. Verificando status de autenticacao..."
    output=$($CLI_CMD auth me 2>&1)
    assert_contains "$output" "$TEST_EMAIL\|email\|user\|id" "Status deve mostrar usuario logado"

    # 5. Comando autenticado deve funcionar
    log_step "5. Testando comando autenticado..."
    output=$($CLI_CMD instance list 2>&1)
    # Deve retornar lista (vazia ou com instancias) sem erro de auth
    assert_not_contains "$output" "401\|Unauthorized\|nao autenticado" "Comando deve funcionar com auth"

    # 6. Login com credenciais invalidas
    log_step "6. Testando login com credenciais invalidas..."
    output=$($CLI_CMD auth login "invalido@test.com" "senhaerrada" 2>&1 || true)
    assert_contains "$output" "erro\|Erro\|falha\|Falha\|401\|Invalid\|incorreta\|Unauthorized" "Login invalido deve falhar"

    # 7. Logout
    log_step "7. Fazendo logout..."
    output=$($CLI_CMD auth logout 2>&1)
    assert_contains "$output" "sucesso\|Logout\|desconectado\|removido\|success\|out" "Logout deve confirmar sucesso"
    assert_file_not_exists "$TOKEN_FILE" "Token deve ser removido apos logout"

    # 8. Verificar que nao esta mais autenticado
    log_step "8. Verificando que esta deslogado..."
    output=$($CLI_CMD auth me 2>&1 || true)
    assert_contains "$output" "Unauthorized\|login\|401\|error\|Token" "Status deve indicar nao logado"

    # Resumo
    print_assert_summary
    local result=$?

    finish_test "$TEST_NAME" $result
    return $result
}

main "$@"
