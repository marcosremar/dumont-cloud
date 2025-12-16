#!/bin/bash
# DumontAgent Installer
# Instala e configura o agente de sincronizacao em maquinas GPU

set -e

VERSION="1.0.0"
INSTALL_DIR="/opt/dumont"
SERVICE_NAME="dumont-agent"

echo "========================================"
echo "  DumontAgent Installer v$VERSION"
echo "========================================"

# Verificar root
if [ "$EUID" -ne 0 ]; then
    echo "ERRO: Execute como root"
    exit 1
fi

# Parametros (passados como variaveis de ambiente)
DUMONT_SERVER="${DUMONT_SERVER:-}"
INSTANCE_ID="${INSTANCE_ID:-unknown}"
SYNC_DIRS="${SYNC_DIRS:-/workspace}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"
RESTIC_PASSWORD="${RESTIC_PASSWORD:-}"
RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-}"

echo "[1/5] Criando diretorios..."
mkdir -p "$INSTALL_DIR"
mkdir -p /var/log

echo "[2/5] Instalando restic..."
if ! command -v restic &> /dev/null; then
    wget -q https://github.com/restic/restic/releases/download/v0.17.3/restic_0.17.3_linux_amd64.bz2 -O /tmp/restic.bz2
    bunzip2 -f /tmp/restic.bz2
    chmod +x /tmp/restic
    mv /tmp/restic /usr/local/bin/restic
    echo "   restic instalado: $(restic version)"
else
    echo "   restic ja instalado: $(restic version)"
fi

echo "[3/5] Instalando DumontAgent..."
cat > "$INSTALL_DIR/dumont-agent.sh" << 'AGENT_SCRIPT'
#!/bin/bash
# DumontAgent - Agente de sincronizacao para maquinas GPU
# Sincroniza workspace com Cloudflare R2 a cada 30 segundos

VERSION="1.0.0"
AGENT_NAME="DumontAgent"
INSTALL_DIR="/opt/dumont"
LOG_FILE="/var/log/dumont-agent.log"
LOCK_FILE="/tmp/dumont-agent.lock"
STATUS_FILE="/tmp/dumont-agent-status.json"
INTERVAL=30

# Carregar configuracao
source "$INSTALL_DIR/config.env"

log() {
    local level="$1"
    local msg="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $msg" | tee -a "$LOG_FILE"
}

send_status() {
    local status="$1"
    local message="$2"
    local last_backup="$3"

    cat > "$STATUS_FILE" << EOF
{
    "agent": "$AGENT_NAME",
    "version": "$VERSION",
    "instance_id": "$INSTANCE_ID",
    "status": "$status",
    "message": "$message",
    "last_backup": "$last_backup",
    "timestamp": "$(date -Iseconds)",
    "uptime": "$(uptime -p 2>/dev/null || echo 'unknown')"
}
EOF

    if [ -n "$DUMONT_SERVER" ]; then
        curl -s -X POST "$DUMONT_SERVER/api/agent/status" \
            -H "Content-Type: application/json" \
            -d @"$STATUS_FILE" > /dev/null 2>&1 || true
    fi
}

do_backup() {
    local start_time=$(date +%s)

    log "INFO" "Iniciando backup incremental de $SYNC_DIRS..."
    send_status "syncing" "Backup em progresso" ""

    if restic backup "$SYNC_DIRS" --tag auto --tag "instance:$INSTANCE_ID" --quiet -o s3.connections=16 2>&1 | tee -a "$LOG_FILE"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local timestamp=$(date -Iseconds)

        log "INFO" "Backup concluido em ${duration}s"
        send_status "idle" "Ultimo backup: ${duration}s" "$timestamp"

        restic forget --keep-last 10 --tag auto --quiet 2>/dev/null
        return 0
    else
        log "ERROR" "Backup falhou"
        send_status "error" "Backup falhou" ""
        return 1
    fi
}

main_loop() {
    local last_hash=""

    while true; do
        if [ -d "$SYNC_DIRS" ]; then
            local current_hash=$(find "$SYNC_DIRS" -type f -mmin -1 2>/dev/null | sort | md5sum | cut -d" " -f1)

            if [ "$current_hash" != "$last_hash" ] && [ -n "$current_hash" ]; then
                if do_backup; then
                    last_hash="$current_hash"
                fi
            else
                send_status "idle" "Aguardando mudancas" ""
            fi
        else
            log "WARN" "Diretorio $SYNC_DIRS nao existe"
            send_status "warning" "Diretorio nao existe" ""
        fi

        sleep "$INTERVAL"
    done
}

# Verificar se ja esta rodando
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "$AGENT_NAME ja esta rodando (PID $PID)"
        exit 1
    fi
fi

echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

log "INFO" "=== $AGENT_NAME v$VERSION Iniciado ==="
log "INFO" "PID: $$"
log "INFO" "Intervalo: ${INTERVAL}s"
log "INFO" "Diretorio: $SYNC_DIRS"
log "INFO" "Instance ID: $INSTANCE_ID"

send_status "starting" "Agente iniciado" ""

main_loop
AGENT_SCRIPT

chmod +x "$INSTALL_DIR/dumont-agent.sh"

echo "[4/5] Criando configuracao..."
cat > "$INSTALL_DIR/config.env" << EOF
# DumontAgent Configuration
export DUMONT_SERVER="$DUMONT_SERVER"
export INSTANCE_ID="$INSTANCE_ID"
export SYNC_DIRS="$SYNC_DIRS"
export AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY"
export RESTIC_PASSWORD="$RESTIC_PASSWORD"
export RESTIC_REPOSITORY="$RESTIC_REPOSITORY"
EOF

chmod 600 "$INSTALL_DIR/config.env"

echo "[5/5] Iniciando DumontAgent..."
# Matar instancia anterior se existir
pkill -f "dumont-agent.sh" 2>/dev/null || true
sleep 1

# Iniciar em background
nohup "$INSTALL_DIR/dumont-agent.sh" > /dev/null 2>&1 &
AGENT_PID=$!

sleep 2

if kill -0 "$AGENT_PID" 2>/dev/null; then
    echo ""
    echo "========================================"
    echo "  DumontAgent instalado com sucesso!"
    echo "========================================"
    echo "  PID: $AGENT_PID"
    echo "  Log: /var/log/dumont-agent.log"
    echo "  Status: /tmp/dumont-agent-status.json"
    echo "========================================"
else
    echo "ERRO: Falha ao iniciar DumontAgent"
    exit 1
fi
