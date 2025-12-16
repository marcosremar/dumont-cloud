#!/bin/bash
# DumontAgent - Agente de sincronizacao para maquinas GPU
# Sincroniza workspace com Cloudflare R2 a cada 30 segundos
# Envia logs para o servidor central (Dumont Cloud)

VERSION="1.0.0"
AGENT_NAME="DumontAgent"
INSTALL_DIR="/opt/dumont"
LOG_FILE="/var/log/dumont-agent.log"
LOCK_FILE="/tmp/dumont-agent.lock"
STATUS_FILE="/tmp/dumont-agent-status.json"
INTERVAL=30

# Configuracoes (serao substituidas na instalacao)
DUMONT_SERVER="${DUMONT_SERVER:-}"
INSTANCE_ID="${INSTANCE_ID:-}"
SYNC_DIRS="${SYNC_DIRS:-/workspace}"

# Credenciais R2 (serao injetadas na instalacao)
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"
export RESTIC_PASSWORD="${RESTIC_PASSWORD:-}"
export RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-}"

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

    # Salvar status local
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

    # Enviar para servidor central se configurado
    if [ -n "$DUMONT_SERVER" ]; then
        curl -s -X POST "$DUMONT_SERVER/api/agent/status" \
            -H "Content-Type: application/json" \
            -d @"$STATUS_FILE" > /dev/null 2>&1 || true
    fi
}

check_dependencies() {
    if ! command -v restic &> /dev/null; then
        log "ERROR" "restic nao encontrado, instalando..."
        install_restic
    fi
}

install_restic() {
    log "INFO" "Instalando restic v0.17.3..."
    wget -q https://github.com/restic/restic/releases/download/v0.17.3/restic_0.17.3_linux_amd64.bz2 -O /tmp/restic.bz2 && \
    bunzip2 -f /tmp/restic.bz2 && \
    chmod +x /tmp/restic && \
    mv /tmp/restic /usr/local/bin/restic && \
    log "INFO" "restic instalado: $(/usr/local/bin/restic version)"
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

        # Limpar snapshots antigos (manter ultimos 10 automaticos)
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
            # Detectar mudancas (arquivos modificados no ultimo minuto)
            local current_hash=$(find "$SYNC_DIRS" -type f -mmin -1 2>/dev/null | sort | md5sum | cut -d" " -f1)

            if [ "$current_hash" != "$last_hash" ] && [ -n "$current_hash" ]; then
                if do_backup; then
                    last_hash="$current_hash"
                fi
            else
                send_status "idle" "Nenhuma mudanca detectada" ""
            fi
        else
            log "WARN" "Diretorio $SYNC_DIRS nao existe"
            send_status "warning" "Diretorio $SYNC_DIRS nao existe" ""
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

# Criar lock
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

# Banner
log "INFO" "=== $AGENT_NAME v$VERSION Iniciado ==="
log "INFO" "PID: $$"
log "INFO" "Intervalo: ${INTERVAL}s"
log "INFO" "Diretorio: $SYNC_DIRS"
log "INFO" "Instance ID: $INSTANCE_ID"

# Verificar dependencias
check_dependencies

# Enviar status inicial
send_status "starting" "Agente iniciado" ""

# Loop principal
main_loop
