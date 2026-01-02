#!/bin/bash
# Test Assertion Utilities
# Funcoes de assert para validar resultados

# Contador de asserts
ASSERT_PASSED=0
ASSERT_FAILED=0

# Assert que comando retorna sucesso (exit code 0)
assert_success() {
    local cmd="$1"
    local msg="${2:-Command should succeed}"

    if eval "$cmd" > /dev/null 2>&1; then
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    else
        log_error "$msg"
        ((ASSERT_FAILED++))
        return 1
    fi
}

# Assert que comando falha (exit code != 0)
assert_failure() {
    local cmd="$1"
    local msg="${2:-Command should fail}"

    if eval "$cmd" > /dev/null 2>&1; then
        log_error "$msg (esperava falha, mas teve sucesso)"
        ((ASSERT_FAILED++))
        return 1
    else
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    fi
}

# Assert que output contem string (case insensitive)
assert_contains() {
    local output="$1"
    local expected="$2"
    local msg="${3:-Output should contain '$expected'}"

    if echo "$output" | grep -qi "$expected"; then
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    else
        log_error "$msg"
        log_error "Output: $output"
        ((ASSERT_FAILED++))
        return 1
    fi
}

# Assert que output NAO contem string (case insensitive)
assert_not_contains() {
    local output="$1"
    local unexpected="$2"
    local msg="${3:-Output should not contain '$unexpected'}"

    if echo "$output" | grep -qi "$unexpected"; then
        log_error "$msg"
        ((ASSERT_FAILED++))
        return 1
    else
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    fi
}

# Assert que output e JSON valido
assert_json() {
    local output="$1"
    local msg="${2:-Output should be valid JSON}"

    if echo "$output" | python3 -m json.tool > /dev/null 2>&1; then
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    else
        log_error "$msg"
        ((ASSERT_FAILED++))
        return 1
    fi
}

# Assert que campo JSON existe e tem valor
assert_json_field() {
    local output="$1"
    local field="$2"
    local expected="$3"
    local msg="${4:-JSON field '$field' should be '$expected'}"

    local actual=$(echo "$output" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('$field', ''))" 2>/dev/null)

    if [ "$actual" = "$expected" ]; then
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    else
        log_error "$msg (atual: '$actual')"
        ((ASSERT_FAILED++))
        return 1
    fi
}

# Assert que HTTP status code e esperado
assert_http_status() {
    local url="$1"
    local expected="$2"
    local msg="${3:-HTTP status should be $expected}"

    local actual=$(curl -s -o /dev/null -w "%{http_code}" "$url")

    if [ "$actual" = "$expected" ]; then
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    else
        log_error "$msg (atual: $actual)"
        ((ASSERT_FAILED++))
        return 1
    fi
}

# Assert que arquivo existe
assert_file_exists() {
    local file="$1"
    local msg="${2:-File '$file' should exist}"

    if [ -f "$file" ]; then
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    else
        log_error "$msg"
        ((ASSERT_FAILED++))
        return 1
    fi
}

# Assert que arquivo NAO existe
assert_file_not_exists() {
    local file="$1"
    local msg="${2:-File '$file' should not exist}"

    if [ ! -f "$file" ]; then
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    else
        log_error "$msg"
        ((ASSERT_FAILED++))
        return 1
    fi
}

# Assert que valor e numero
assert_number() {
    local value="$1"
    local msg="${2:-Value should be a number}"

    if [[ "$value" =~ ^[0-9]+\.?[0-9]*$ ]]; then
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    else
        log_error "$msg (valor: '$value')"
        ((ASSERT_FAILED++))
        return 1
    fi
}

# Assert que valor e maior que
assert_greater_than() {
    local value="$1"
    local min="$2"
    local msg="${3:-Value should be greater than $min}"

    if (( $(echo "$value > $min" | bc -l) )); then
        log_success "$msg"
        ((ASSERT_PASSED++))
        return 0
    else
        log_error "$msg (valor: $value)"
        ((ASSERT_FAILED++))
        return 1
    fi
}

# Resumo dos asserts
print_assert_summary() {
    echo ""
    echo "----------------------------------------------"
    echo "Resumo dos Asserts:"
    echo -e "  ${GREEN}Passed: $ASSERT_PASSED${NC}"
    echo -e "  ${RED}Failed: $ASSERT_FAILED${NC}"
    echo "----------------------------------------------"

    if [ $ASSERT_FAILED -gt 0 ]; then
        return 1
    fi
    return 0
}

# Reset contadores
reset_asserts() {
    ASSERT_PASSED=0
    ASSERT_FAILED=0
}
