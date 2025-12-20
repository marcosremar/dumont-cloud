#!/bin/bash
# Real Test Utilities
# Funcoes para testes E2E reais com Vast.ai API

# Carrega utils base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/setup.sh"
source "$SCRIPT_DIR/../utils/assertions.sh"

# Configuracoes Vast.ai
VAST_API_KEY="${VAST_API_KEY:-a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd}"
VAST_API_URL="https://console.vast.ai/api/v0"
MAX_GPU_PRICE="${MAX_GPU_PRICE:-0.25}"  # Max $0.25/hora
MIN_BALANCE="${MIN_BALANCE:-0.50}"       # Minimo $0.50 para testes
INSTANCE_TIMEOUT="${INSTANCE_TIMEOUT:-180}"  # 3 minutos max

# Variavel global para cleanup
CREATED_INSTANCE_ID=""

# Verifica saldo na Vast.ai
get_vast_balance() {
    local response=$(curl -s "${VAST_API_URL}/users/current/?api_key=${VAST_API_KEY}" 2>/dev/null)
    local balance=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d.get(\"credit\", 0):.2f}')" 2>/dev/null)
    echo "$balance"
}

# Verifica se tem saldo suficiente
check_balance() {
    local required="${1:-$MIN_BALANCE}"
    local balance=$(get_vast_balance)

    if [ -z "$balance" ] || [ "$balance" == "0.00" ]; then
        log_error "Nao foi possivel verificar saldo da Vast.ai"
        return 1
    fi

    log_info "Saldo Vast.ai: \$$balance"

    if (( $(echo "$balance < $required" | bc -l) )); then
        log_error "Saldo insuficiente: \$$balance < \$$required"
        return 1
    fi

    log_success "Saldo suficiente para testes"
    return 0
}

# Busca GPU mais barata disponivel
find_cheapest_gpu() {
    local max_price="${1:-$MAX_GPU_PRICE}"

    log_step "Buscando GPU mais barata RENTAVEL (max \$$max_price/h)..." >&2

    # Buscar todas as ofertas ordenadas por preco e filtrar rentable no Python
    local response=$(curl -sL "${VAST_API_URL}/bundles/?order=dph_total&type=on-demand&limit=50&api_key=${VAST_API_KEY}" 2>/dev/null)

    # Filtra ofertas rentaveis e abaixo do preco maximo
    local offer=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    offers = data.get('offers', [])
    max_p = float('$max_price')
    for o in offers:
        # Filtra: rentable=true, num_gpus=1, preco <= max
        if o.get('rentable', False) and o.get('num_gpus', 0) == 1 and o.get('dph_total', 999) <= max_p:
            print(f\"{o['id']}|{o.get('gpu_name', 'Unknown')}|{o.get('dph_total', 0):.4f}|{o.get('geolocation', 'Unknown')}\")
            break
except Exception as e:
    pass
" 2>/dev/null)

    if [ -z "$offer" ]; then
        log_error "Nenhuma GPU RENTAVEL disponivel com preco <= \$$max_price/h" >&2
        # Mostrar opcoes disponiveis
        log_info "Verificando GPUs disponiveis..." >&2
        echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    offers = data.get('offers', [])
    print('TOP 5 GPUs mais baratas (rentaveis):', file=sys.stderr)
    count = 0
    for o in offers:
        if o.get('rentable', False) and o.get('num_gpus', 0) == 1:
            print(f\"  {o.get('gpu_name', '?'):20} \${o.get('dph_total', 0):.3f}/h - {o.get('geolocation', '?')}\", file=sys.stderr)
            count += 1
            if count >= 5:
                break
except:
    pass
" 2>&1 >&2
        return 1
    fi

    local offer_id=$(echo "$offer" | cut -d'|' -f1)
    local gpu_name=$(echo "$offer" | cut -d'|' -f2)
    local price=$(echo "$offer" | cut -d'|' -f3)
    local location=$(echo "$offer" | cut -d'|' -f4)

    log_success "GPU encontrada: $gpu_name @ \$$price/h ($location)" >&2
    log_info "Offer ID: $offer_id" >&2

    # Retorna APENAS o offer_id (sem logs)
    echo "$offer_id"
}

# Cria instancia e aguarda ficar pronta
create_instance_and_wait() {
    local offer_id="$1"
    local timeout="${2:-$INSTANCE_TIMEOUT}"

    log_step "Criando instancia (offer_id: $offer_id)..." >&2

    # Cria instancia via API
    local response=$(curl -s -X PUT "${VAST_API_URL}/asks/${offer_id}/" \
        -H "Authorization: Bearer ${VAST_API_KEY}" \
        -H "Content-Type: application/json" \
        -d '{
            "client_id": "me",
            "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
            "disk": 20,
            "onstart": "touch ~/.no_auto_tmux",
            "label": "e2e-test"
        }' 2>/dev/null)

    # Extrai instance_id
    local instance_id=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('new_contract', ''))
except:
    pass
" 2>/dev/null)

    if [ -z "$instance_id" ]; then
        log_error "Falha ao criar instancia: $response" >&2
        return 1
    fi

    log_success "Instancia criada: $instance_id" >&2
    CREATED_INSTANCE_ID="$instance_id"

    # Aguarda instancia ficar pronta
    log_step "Aguardando instancia ficar pronta (timeout: ${timeout}s)..." >&2

    local start_time=$(date +%s)
    local status=""

    while true; do
        local elapsed=$(($(date +%s) - start_time))

        if [ $elapsed -gt $timeout ]; then
            log_error "Timeout aguardando instancia ficar pronta" >&2
            return 1
        fi

        # Busca status da instancia
        local info=$(curl -s "${VAST_API_URL}/instances/${instance_id}/?api_key=${VAST_API_KEY}" 2>/dev/null)
        status=$(echo "$info" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # API retorna 'instances' como objeto para single instance, ou lista para todos
    instances_data = data.get('instances', data)
    if isinstance(instances_data, dict):
        # Single instance - instances e um objeto
        inst = instances_data
    elif isinstance(instances_data, list) and len(instances_data) > 0:
        inst = instances_data[0]
    else:
        inst = data
    # Prioridade: actual_status, cur_state, status_msg
    status = inst.get('actual_status') or inst.get('cur_state') or inst.get('status_msg') or 'unknown'
    print(status)
except Exception as e:
    print('error: ' + str(e))
" 2>/dev/null)

        # Mostra progresso baseado no status
        if [[ "$status" == "loading" || "$status" == "pulling" ]]; then
            log_info "Status: $status (${elapsed}s) - aguardando imagem..." >&2
        elif [[ "$status" == "exited" || "$status" == "stopped" || "$status" == "error" ]]; then
            log_error "Instancia falhou com status: $status" >&2
            return 1
        else
            log_info "Status: $status (${elapsed}s)" >&2
        fi

        if [[ "$status" == "running" ]]; then
            log_success "Instancia pronta!" >&2
            echo "$instance_id"
            return 0
        fi

        sleep 5
    done
}

# Obtem informacoes da instancia
get_instance_info() {
    local instance_id="$1"

    local response=$(curl -s "${VAST_API_URL}/instances/${instance_id}/?api_key=${VAST_API_KEY}" 2>/dev/null)
    echo "$response"
}

# Obtem SSH host e port
get_instance_ssh() {
    local instance_id="$1"

    local info=$(get_instance_info "$instance_id")
    local ssh_info=$(echo "$info" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    instances = data.get('instances', [data]) if isinstance(data.get('instances'), list) else [data]
    if instances:
        i = instances[0]
        host = i.get('ssh_host', i.get('public_ipaddr', ''))
        port = i.get('ssh_port', 22)
        print(f'{host}:{port}')
except:
    pass
" 2>/dev/null)

    echo "$ssh_info"
}

# Testa conexao SSH
test_ssh_connection() {
    local instance_id="$1"
    local timeout="${2:-30}"

    local ssh_info=$(get_instance_ssh "$instance_id")
    local host=$(echo "$ssh_info" | cut -d':' -f1)
    local port=$(echo "$ssh_info" | cut -d':' -f2)

    if [ -z "$host" ] || [ -z "$port" ]; then
        log_error "Nao foi possivel obter info SSH"
        return 1
    fi

    log_step "Testando SSH: $host:$port..."

    # Tenta conectar com timeout
    if timeout $timeout ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        -p "$port" root@"$host" "echo 'SSH OK'" 2>/dev/null; then
        log_success "Conexao SSH funcionando"
        return 0
    else
        log_warning "SSH nao acessivel ainda"
        return 1
    fi
}

# Pausa instancia
pause_instance() {
    local instance_id="$1"

    log_step "Pausando instancia $instance_id..."

    local response=$(curl -s -X PUT "${VAST_API_URL}/instances/${instance_id}/" \
        -H "Authorization: Bearer ${VAST_API_KEY}" \
        -H "Content-Type: application/json" \
        -d '{"paused": true}' 2>/dev/null)

    local success=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('true' if data.get('success', False) else 'false')
except:
    print('false')
" 2>/dev/null)

    if [ "$success" == "true" ]; then
        log_success "Instancia pausada"
        return 0
    else
        log_error "Falha ao pausar: $response"
        return 1
    fi
}

# Resume instancia
resume_instance() {
    local instance_id="$1"

    log_step "Resumindo instancia $instance_id..."

    local response=$(curl -s -X PUT "${VAST_API_URL}/instances/${instance_id}/" \
        -H "Authorization: Bearer ${VAST_API_KEY}" \
        -H "Content-Type: application/json" \
        -d '{"paused": false}' 2>/dev/null)

    local success=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('true' if data.get('success', False) else 'false')
except:
    print('false')
" 2>/dev/null)

    if [ "$success" == "true" ]; then
        log_success "Instancia resumida"
        return 0
    else
        log_error "Falha ao resumir: $response"
        return 1
    fi
}

# Destroi instancia
destroy_instance() {
    local instance_id="$1"

    if [ -z "$instance_id" ]; then
        log_warning "Nenhuma instancia para destruir"
        return 0
    fi

    log_step "Destruindo instancia $instance_id..."

    local response=$(curl -s -X DELETE "${VAST_API_URL}/instances/${instance_id}/" \
        -H "Authorization: Bearer ${VAST_API_KEY}" 2>/dev/null)

    log_success "Instancia $instance_id destruida"
    CREATED_INSTANCE_ID=""
    return 0
}

# Cleanup automatico em caso de erro/exit
cleanup_on_exit() {
    if [ -n "$CREATED_INSTANCE_ID" ]; then
        log_warning "Cleanup: Destruindo instancia $CREATED_INSTANCE_ID..."
        destroy_instance "$CREATED_INSTANCE_ID"
    fi
}

# Registra trap para cleanup
trap cleanup_on_exit EXIT ERR

# Aguarda status especifico
wait_for_status() {
    local instance_id="$1"
    local expected_status="$2"
    local timeout="${3:-60}"

    log_step "Aguardando status '$expected_status'..."

    local start_time=$(date +%s)

    while true; do
        local elapsed=$(($(date +%s) - start_time))

        if [ $elapsed -gt $timeout ]; then
            log_error "Timeout aguardando status '$expected_status'"
            return 1
        fi

        local info=$(get_instance_info "$instance_id")
        local status=$(echo "$info" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # API retorna 'instances' como objeto para single instance, ou lista para todos
    instances_data = data.get('instances', data)
    if isinstance(instances_data, dict):
        inst = instances_data
    elif isinstance(instances_data, list) and len(instances_data) > 0:
        inst = instances_data[0]
    else:
        inst = data
    status = inst.get('actual_status') or inst.get('cur_state') or inst.get('status_msg') or 'unknown'
    print(status)
except Exception as e:
    print('error: ' + str(e))
" 2>/dev/null)

        log_info "Status atual: $status"

        if [[ "$status" == *"$expected_status"* ]]; then
            log_success "Status alcancado: $status"
            return 0
        fi

        sleep 3
    done
}

# Calcula custo do teste
calculate_test_cost() {
    local start_balance="$1"
    local end_balance=$(get_vast_balance)

    local cost=$(echo "$start_balance - $end_balance" | bc -l 2>/dev/null || echo "0.00")
    log_info "Custo do teste: \$$cost"
    echo "$cost"
}
