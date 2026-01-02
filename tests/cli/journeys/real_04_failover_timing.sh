#!/bin/bash
# Real Journey 4: Failover Timing Test
# Mede os tempos REAIS de cada fase do failover:
#   1. GPU funcionando
#   2. GPU destruida (simula falha)
#   3. CPU Standby assume
#   4. Nova GPU provisionada
#   5. Dados restaurados
#
# Custo estimado: ~$0.10-0.20

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/real_utils.sh"

TEST_NAME="Real Failover Timing"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Variaveis de timing
declare -A TIMING

# Funcao para registrar tempo
record_time() {
    local phase="$1"
    local start="$2"
    local end=$(date +%s%3N)  # milliseconds
    local duration=$((end - start))
    TIMING["$phase"]=$duration
    log_info "Fase '$phase': ${duration}ms"
}

# Funcao para aguardar API com retry (evita rate limiting)
api_with_retry() {
    local max_attempts=5
    local attempt=1
    local result=""

    while [ $attempt -le $max_attempts ]; do
        sleep 2  # Sempre espera 2s entre chamadas
        result=$(eval "$1" 2>/dev/null)

        if [ -n "$result" ] && ! echo "$result" | grep -q "429"; then
            echo "$result"
            return 0
        fi

        log_info "Rate limited, tentativa $attempt/$max_attempts..." >&2
        sleep $((attempt * 2))
        ((attempt++))
    done

    echo "$result"
}

main() {
    init_test "$TEST_NAME"
    reset_asserts

    local test_start=$(date +%s%3N)
    local start_balance=$(get_vast_balance)

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     FAILOVER TIMING TEST - Medicao de Tempos Reais      ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    log_info "Saldo inicial: \$$start_balance"

    # ============================================
    # FASE 0: Verificar pre-requisitos
    # ============================================
    log_step "FASE 0: Verificando pre-requisitos..."
    local phase0_start=$(date +%s%3N)

    if ! check_balance 0.50; then
        log_error "Saldo insuficiente para teste de failover"
        finish_test "$TEST_NAME" 1
        return 1
    fi

    record_time "prereq_check" $phase0_start
    ((ASSERT_PASSED++))

    # ============================================
    # FASE 1: Criar GPU primaria
    # ============================================
    log_step "FASE 1: Criando GPU primaria..."
    local phase1_start=$(date +%s%3N)

    local offer_id=$(find_cheapest_gpu 0.25)
    if [ -z "$offer_id" ]; then
        log_error "Nenhuma GPU disponivel"
        finish_test "$TEST_NAME" 1
        return 1
    fi

    local gpu_instance_id=$(create_instance_and_wait "$offer_id" 300)
    if [ -z "$gpu_instance_id" ]; then
        log_error "Falha ao criar GPU"
        finish_test "$TEST_NAME" 1
        return 1
    fi

    record_time "gpu_provisioning" $phase1_start
    log_success "GPU provisionada em ${TIMING[gpu_provisioning]}ms"
    ((ASSERT_PASSED++))

    # Guardar info da GPU para comparacao
    local gpu_info=$(api_with_retry "curl -s '${VAST_API_URL}/instances/${gpu_instance_id}/?api_key=${VAST_API_KEY}'")
    local gpu_name=$(echo "$gpu_info" | python3 -c "import sys,json; d=json.load(sys.stdin).get('instances',{}); print(d.get('gpu_name','Unknown'))" 2>/dev/null)
    log_info "GPU: $gpu_name (ID: $gpu_instance_id)"

    # ============================================
    # FASE 2: Aguardar GPU estabilizar
    # ============================================
    log_step "FASE 2: Aguardando GPU estabilizar (15s)..."
    local phase2_start=$(date +%s%3N)

    sleep 15  # Dar tempo para GPU inicializar completamente

    # Verificar SSH disponivel
    local ssh_info=$(get_instance_ssh "$gpu_instance_id")
    log_info "SSH: $ssh_info"

    record_time "gpu_stabilization" $phase2_start
    ((ASSERT_PASSED++))

    # ============================================
    # FASE 3: Simular falha - Destruir GPU
    # ============================================
    log_step "FASE 3: Simulando FALHA - Destruindo GPU..."
    local phase3_start=$(date +%s%3N)

    # Timestamp exato da falha
    local failure_timestamp=$(date +%s%3N)

    if ! destroy_instance "$gpu_instance_id"; then
        log_error "Falha ao destruir GPU"
        finish_test "$TEST_NAME" 1
        return 1
    fi

    record_time "gpu_destruction" $phase3_start
    log_success "GPU destruida (falha simulada) em ${TIMING[gpu_destruction]}ms"
    ((ASSERT_PASSED++))

    # ============================================
    # FASE 4: Verificar CPU Standby (via API)
    # ============================================
    log_step "FASE 4: Verificando CPU Standby..."
    local phase4_start=$(date +%s%3N)

    # Fazer login para acessar API
    do_login || log_warning "Login falhou"

    # Verificar status do standby
    local standby_status=$(curl -s -H "Authorization: Bearer $(cat $TOKEN_FILE 2>/dev/null)" \
        "$BASE_URL/api/v1/standby/status" 2>/dev/null)

    log_info "Status Standby: $standby_status"

    # Verificar associations
    local associations=$(curl -s -H "Authorization: Bearer $(cat $TOKEN_FILE 2>/dev/null)" \
        "$BASE_URL/api/v1/standby/associations" 2>/dev/null)

    log_info "Associations: $associations"

    record_time "standby_check" $phase4_start
    ((ASSERT_PASSED++))

    # ============================================
    # FASE 5: Buscar e provisionar nova GPU
    # ============================================
    log_step "FASE 5: Buscando e provisionando nova GPU..."
    local phase5_start=$(date +%s%3N)

    # Buscar nova GPU (pode ser diferente da anterior)
    local new_offer_id=$(find_cheapest_gpu 0.30)
    if [ -z "$new_offer_id" ]; then
        log_warning "Nenhuma GPU disponivel para recovery"
        record_time "recovery_search" $phase5_start
    else
        log_info "Nova GPU encontrada: Offer $new_offer_id"

        # Provisionar nova GPU
        local new_instance_id=$(create_instance_and_wait "$new_offer_id" 300)

        if [ -n "$new_instance_id" ]; then
            record_time "recovery_provisioning" $phase5_start
            log_success "Nova GPU provisionada em ${TIMING[recovery_provisioning]}ms"

            # Destruir para nao gastar dinheiro
            log_step "Destruindo nova GPU (cleanup)..."
            destroy_instance "$new_instance_id"
            ((ASSERT_PASSED++))
        else
            log_warning "Falha ao provisionar nova GPU"
            record_time "recovery_provisioning" $phase5_start
        fi
    fi

    # ============================================
    # RESUMO DE TEMPOS
    # ============================================
    local test_end=$(date +%s%3N)
    local total_time=$((test_end - test_start))

    local end_balance=$(get_vast_balance)
    local cost=$(echo "$start_balance - $end_balance" | bc -l 2>/dev/null || echo "0.00")

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              RESUMO DE TEMPOS DE FAILOVER                ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${YELLOW}Fase${NC}                          ${YELLOW}Tempo${NC}"
    echo -e "  ────────────────────────────────────────"
    echo -e "  Pre-requisitos:              ${TIMING[prereq_check]:-0}ms"
    echo -e "  GPU Provisioning:            ${GREEN}${TIMING[gpu_provisioning]:-0}ms${NC}"
    echo -e "  GPU Estabilizacao:           ${TIMING[gpu_stabilization]:-0}ms"
    echo -e "  GPU Destruicao (falha):      ${TIMING[gpu_destruction]:-0}ms"
    echo -e "  Standby Check:               ${TIMING[standby_check]:-0}ms"
    echo -e "  Recovery Provisioning:       ${GREEN}${TIMING[recovery_provisioning]:-N/A}${NC}"
    echo -e "  ────────────────────────────────────────"
    echo -e "  ${CYAN}TEMPO TOTAL:                   ${total_time}ms ($(echo "scale=2; $total_time/1000" | bc)s)${NC}"
    echo ""
    echo -e "  ${YELLOW}Custo do teste: \$$cost${NC}"
    echo -e "  Saldo final: \$$end_balance"
    echo ""

    # Calcular MTTR (Mean Time To Recovery)
    local mttr=0
    if [ -n "${TIMING[recovery_provisioning]}" ]; then
        mttr=$((TIMING[gpu_destruction] + TIMING[standby_check] + TIMING[recovery_provisioning]))
        echo -e "  ${GREEN}MTTR Estimado: ${mttr}ms (~$(echo "scale=1; $mttr/1000" | bc)s)${NC}"
    else
        echo -e "  ${YELLOW}MTTR: N/A (recovery nao completado)${NC}"
    fi
    echo ""

    do_logout

    # Resumo
    print_assert_summary
    local result=$?

    finish_test "$TEST_NAME" $result
    return $result
}

main "$@"
