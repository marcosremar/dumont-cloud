#!/bin/bash
# Monitor do teste de deployment

LOG_FILE="/tmp/model_deploy_10_test.log"

echo "Monitorando teste de deployment..."
echo "Log file: $LOG_FILE"
echo ""

while true; do
    clear
    echo "========================================="
    echo "MONITOR - Teste Deploy 10 Modelos"
    echo "========================================="
    echo "Hora: $(date '+%H:%M:%S')"
    echo ""

    if [ -f "$LOG_FILE" ]; then
        # Mostrar últimas 50 linhas
        echo "ÚLTIMAS 50 LINHAS DO LOG:"
        echo "-----------------------------------------"
        tail -50 "$LOG_FILE"
        echo ""
        echo "-----------------------------------------"

        # Contar sucessos e erros
        SUCCESS_COUNT=$(grep -c "SUCCESS:" "$LOG_FILE" 2>/dev/null || echo "0")
        ERROR_COUNT=$(grep -c "ERROR:" "$LOG_FILE" 2>/dev/null || echo "0")

        echo "Status:"
        echo "  Sucessos: $SUCCESS_COUNT"
        echo "  Erros: $ERROR_COUNT"
    else
        echo "Aguardando início do teste..."
        echo "Log file ainda não criado: $LOG_FILE"
    fi

    echo ""
    echo "Pressione Ctrl+C para parar o monitor"
    echo "========================================="

    sleep 10
done
