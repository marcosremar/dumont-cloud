#!/bin/bash
# =============================================================================
# TESTE E2E REALWORLD - FAILOVER COM OLLAMA + QWEN
# =============================================================================
# Este script testa o fluxo completo de failover com dados reais:
# 1. Instala Ollama na GPU
# 2. Baixa modelo QWen 2.5 0.5B em /workspace
# 3. Testa inferência
# 4. Simula queda de GPU
# 5. Restaura dados
# 6. Verifica se modelo ainda funciona
# 7. Mede tempos
# =============================================================================

set -e

# Configuração
API_URL="${API_URL:-http://localhost:8766}"
VAST_API_KEY="${VAST_API_KEY:-a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd}"
MODEL_NAME="qwen2.5:0.5b"
TEST_PROMPT="Olá, qual é o seu nome?"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# Função: Obter informações da instância
# =============================================================================
get_instance_info() {
    local instance_id=$1
    curl -s -H "Authorization: Bearer $VAST_API_KEY" \
        "https://console.vast.ai/api/v0/instances/" | \
        python3 -c "
import json, sys
data = json.load(sys.stdin)
for inst in data.get('instances', []):
    if inst['id'] == $instance_id:
        print(f\"{inst.get('ssh_port')}|{inst.get('ssh_host')}|{inst.get('actual_status')}\")
        break
"
}

# =============================================================================
# Função: Aguardar instância ficar pronta para SSH
# =============================================================================
wait_for_ssh() {
    local instance_id=$1
    local max_attempts=30
    local attempt=1

    log_info "Aguardando instância $instance_id ficar pronta para SSH..."

    while [ $attempt -le $max_attempts ]; do
        local info=$(get_instance_info $instance_id)
        local ssh_port=$(echo "$info" | cut -d'|' -f1)
        local ssh_host=$(echo "$info" | cut -d'|' -f2)
        local status=$(echo "$info" | cut -d'|' -f3)

        if [ "$status" = "running" ] && [ -n "$ssh_port" ] && [ "$ssh_port" != "None" ]; then
            # Tentar conectar
            if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p "$ssh_port" root@"$ssh_host" "echo 'OK'" 2>/dev/null; then
                log_ok "SSH pronto! Porta: $ssh_port Host: $ssh_host"
                echo "$ssh_port|$ssh_host"
                return 0
            fi
        fi

        log_info "Tentativa $attempt/$max_attempts - Status: $status"
        sleep 10
        ((attempt++))
    done

    log_error "Timeout aguardando SSH"
    return 1
}

# =============================================================================
# Função: Executar comando via SSH
# =============================================================================
run_ssh() {
    local ssh_port=$1
    local ssh_host=$2
    shift 2
    local cmd="$@"

    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -p "$ssh_port" root@"$ssh_host" "$cmd"
}

# =============================================================================
# Função: Instalar Ollama
# =============================================================================
install_ollama() {
    local ssh_port=$1
    local ssh_host=$2

    log_info "Instalando Ollama..."

    run_ssh "$ssh_port" "$ssh_host" "
        export OLLAMA_MODELS=/workspace/ollama_models
        mkdir -p /workspace/ollama_models

        if ! which ollama >/dev/null 2>&1; then
            curl -fsSL https://ollama.com/install.sh | sh
        fi

        # Verificar instalação
        ollama --version
    "

    log_ok "Ollama instalado"
}

# =============================================================================
# Função: Baixar modelo
# =============================================================================
download_model() {
    local ssh_port=$1
    local ssh_host=$2
    local model=$3

    log_info "Baixando modelo $model para /workspace..."

    local start_time=$(date +%s)

    run_ssh "$ssh_port" "$ssh_host" "
        export OLLAMA_MODELS=/workspace/ollama_models

        # Iniciar ollama em background se não estiver rodando
        pgrep ollama || (ollama serve &)
        sleep 3

        # Baixar modelo
        ollama pull $model

        # Verificar tamanho
        du -sh /workspace/ollama_models
    "

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_ok "Modelo baixado em ${duration}s"
    echo "$duration"
}

# =============================================================================
# Função: Testar inferência
# =============================================================================
test_inference() {
    local ssh_port=$1
    local ssh_host=$2
    local model=$3
    local prompt=$4

    log_info "Testando inferência com prompt: '$prompt'"

    local start_time=$(date +%s.%N)

    local response=$(run_ssh "$ssh_port" "$ssh_host" "
        export OLLAMA_MODELS=/workspace/ollama_models
        pgrep ollama || (ollama serve &)
        sleep 2
        echo '$prompt' | ollama run $model 2>/dev/null | head -3
    ")

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    log_ok "Resposta recebida em ${duration}s"
    echo "Resposta: $response"
    echo "$duration"
}

# =============================================================================
# Função: Verificar dados em /workspace
# =============================================================================
verify_workspace() {
    local ssh_port=$1
    local ssh_host=$2

    log_info "Verificando dados em /workspace..."

    run_ssh "$ssh_port" "$ssh_host" "
        echo '=== Estrutura de /workspace ==='
        ls -la /workspace/
        echo ''
        echo '=== Modelos Ollama ==='
        du -sh /workspace/ollama_models 2>/dev/null || echo 'Nenhum modelo encontrado'
        ls -la /workspace/ollama_models/ 2>/dev/null || true
    "
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    echo "============================================"
    echo "TESTE E2E REALWORLD - FAILOVER COM OLLAMA"
    echo "============================================"
    echo ""

    # Pegar instância rodando
    log_info "Buscando instância GPU rodando..."

    local instance_info=$(curl -s -H "Authorization: Bearer $VAST_API_KEY" \
        "https://console.vast.ai/api/v0/instances/" | \
        python3 -c "
import json, sys
data = json.load(sys.stdin)
for inst in data.get('instances', []):
    if inst.get('actual_status') == 'running':
        print(f\"{inst['id']}|{inst.get('ssh_port')}|{inst.get('ssh_host')}\")
        break
")

    if [ -z "$instance_info" ]; then
        log_error "Nenhuma instância rodando encontrada"
        exit 1
    fi

    local instance_id=$(echo "$instance_info" | cut -d'|' -f1)
    local ssh_port=$(echo "$instance_info" | cut -d'|' -f2)
    local ssh_host=$(echo "$instance_info" | cut -d'|' -f3)

    log_ok "Instância encontrada: ID=$instance_id"

    # Aguardar SSH
    local ssh_info=$(wait_for_ssh "$instance_id")
    if [ $? -ne 0 ]; then
        log_error "Falha ao conectar SSH"
        exit 1
    fi

    ssh_port=$(echo "$ssh_info" | cut -d'|' -f1)
    ssh_host=$(echo "$ssh_info" | cut -d'|' -f2)

    # Testar GPU
    log_info "Verificando GPU..."
    run_ssh "$ssh_port" "$ssh_host" "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader"

    # Instalar Ollama
    install_ollama "$ssh_port" "$ssh_host"

    # Baixar modelo
    local download_time=$(download_model "$ssh_port" "$ssh_host" "$MODEL_NAME")

    # Testar inferência ANTES do failover
    log_info "=== TESTE PRÉ-FAILOVER ==="
    local inference_time_before=$(test_inference "$ssh_port" "$ssh_host" "$MODEL_NAME" "$TEST_PROMPT")

    # Verificar workspace
    verify_workspace "$ssh_port" "$ssh_host"

    # TODO: Simular failover aqui
    log_warn "Simulação de failover não implementada neste script"
    log_info "Use: python cli.py failover simulate $instance_id"

    echo ""
    echo "============================================"
    echo "RESUMO DO TESTE"
    echo "============================================"
    echo "Instância: $instance_id"
    echo "GPU: $(run_ssh "$ssh_port" "$ssh_host" 'nvidia-smi --query-gpu=name --format=csv,noheader')"
    echo "Modelo: $MODEL_NAME"
    echo "Tempo download modelo: ${download_time}s"
    echo "Tempo inferência: ${inference_time_before}s"
    echo "============================================"
}

main "$@"
