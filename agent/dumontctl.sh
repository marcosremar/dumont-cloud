#!/bin/bash
# dumontctl - Controle do DumontAgent
# Uso: dumontctl [start|stop|status|logs|backup]

INSTALL_DIR="/opt/dumont"
LOG_FILE="/var/log/dumont-agent.log"
LOCK_FILE="/tmp/dumont-agent.lock"
STATUS_FILE="/tmp/dumont-agent-status.json"

case "$1" in
    start)
        if [ -f "$LOCK_FILE" ]; then
            PID=$(cat "$LOCK_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo "DumontAgent ja esta rodando (PID $PID)"
                exit 1
            fi
        fi
        echo "Iniciando DumontAgent..."
        nohup "$INSTALL_DIR/dumont-agent.sh" > /dev/null 2>&1 &
        sleep 2
        if [ -f "$LOCK_FILE" ]; then
            echo "DumontAgent iniciado (PID $(cat $LOCK_FILE))"
        else
            echo "Falha ao iniciar DumontAgent"
            exit 1
        fi
        ;;

    stop)
        if [ -f "$LOCK_FILE" ]; then
            PID=$(cat "$LOCK_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo "Parando DumontAgent (PID $PID)..."
                kill "$PID"
                rm -f "$LOCK_FILE"
                echo "DumontAgent parado"
            else
                echo "DumontAgent nao esta rodando"
                rm -f "$LOCK_FILE"
            fi
        else
            echo "DumontAgent nao esta rodando"
        fi
        ;;

    restart)
        $0 stop
        sleep 1
        $0 start
        ;;

    status)
        if [ -f "$STATUS_FILE" ]; then
            cat "$STATUS_FILE" | python3 -m json.tool 2>/dev/null || cat "$STATUS_FILE"
        else
            echo "Status nao disponivel"
        fi

        if [ -f "$LOCK_FILE" ]; then
            PID=$(cat "$LOCK_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo ""
                echo "Processo: Rodando (PID $PID)"
            else
                echo ""
                echo "Processo: Parado (lock file obsoleto)"
            fi
        else
            echo ""
            echo "Processo: Parado"
        fi
        ;;

    logs)
        if [ -f "$LOG_FILE" ]; then
            tail -${2:-50} "$LOG_FILE"
        else
            echo "Arquivo de log nao encontrado"
        fi
        ;;

    logs-follow)
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "Arquivo de log nao encontrado"
        fi
        ;;

    backup)
        echo "Forcando backup imediato..."
        source "$INSTALL_DIR/config.env"
        restic backup "$SYNC_DIRS" --tag manual --quiet -o s3.connections=16
        echo "Backup concluido"
        ;;

    *)
        echo "DumontAgent Control"
        echo ""
        echo "Uso: dumontctl [comando]"
        echo ""
        echo "Comandos:"
        echo "  start       Inicia o agente"
        echo "  stop        Para o agente"
        echo "  restart     Reinicia o agente"
        echo "  status      Mostra status atual"
        echo "  logs [N]    Mostra ultimas N linhas do log (padrao: 50)"
        echo "  logs-follow Segue o log em tempo real"
        echo "  backup      Forca backup imediato"
        ;;
esac
