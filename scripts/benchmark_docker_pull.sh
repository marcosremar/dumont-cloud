#!/bin/bash
# =============================================================================
# BENCHMARK DE ESTRATÉGIAS DE DOCKER PULL
# =============================================================================
# Testa diferentes formas de obter uma imagem Docker para ver qual é a mais rápida
# =============================================================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[✓]${NC} $1"; }
log_test() { echo -e "${CYAN}[TEST]${NC} $1"; }

# Limpar imagem antes de cada teste
cleanup_image() {
    local image=$1
    docker rmi -f $image 2>/dev/null || true
    # Limpar cache de layers
    docker system prune -f > /dev/null 2>&1 || true
}

# Função para medir tempo
measure_pull() {
    local label=$1
    local cmd=$2
    
    log_test "Testando: $label"
    
    local start_time=$(date +%s.%N)
    eval "$cmd" > /dev/null 2>&1
    local end_time=$(date +%s.%N)
    
    local duration=$(echo "$end_time - $start_time" | bc)
    log_ok "$label: ${duration}s"
    echo "$label|$duration"
}

# =============================================================================
# TESTES
# =============================================================================

echo ""
echo "============================================"
echo "  BENCHMARK DE DOCKER PULL - FRANÇA"
echo "============================================"
echo ""

# Verificar velocidade de rede primeiro
log_info "Testando velocidade de download..."
SPEED=$(curl -sL -o /dev/null -w '%{speed_download}' https://registry-1.docker.io/v2/ 2>/dev/null | awk '{print $1/1024/1024}')
echo "Velocidade estimada: ${SPEED} MB/s para Docker Hub"
echo ""

# Imagem de teste (nvidia/cuda é a que usamos no failover)
TEST_IMAGE="nvidia/cuda:12.1.0-runtime-ubuntu22.04"
RESULTS_FILE="/tmp/benchmark_results.txt"
> $RESULTS_FILE

echo "Imagem de teste: $TEST_IMAGE"
echo "============================================"
echo ""

# -----------------------------------------------------------------------------
# TESTE 1: Pull direto do Docker Hub (baseline)
# -----------------------------------------------------------------------------
log_info "TESTE 1: Docker Hub direto (baseline)"
cleanup_image $TEST_IMAGE

START=$(date +%s.%N)
docker pull $TEST_IMAGE
END=$(date +%s.%N)
TIME1=$(echo "$END - $START" | bc)
echo "1|Docker Hub (direto)|$TIME1" >> $RESULTS_FILE
log_ok "Docker Hub direto: ${TIME1}s"
echo ""

# Pegar tamanho da imagem
IMAGE_SIZE=$(docker images $TEST_IMAGE --format "{{.Size}}")
log_info "Tamanho da imagem: $IMAGE_SIZE"
echo ""

# -----------------------------------------------------------------------------
# TESTE 2: Pull com --platform específico
# -----------------------------------------------------------------------------
log_info "TESTE 2: Docker Hub com --platform linux/amd64"
cleanup_image $TEST_IMAGE

START=$(date +%s.%N)
docker pull --platform linux/amd64 $TEST_IMAGE
END=$(date +%s.%N)
TIME2=$(echo "$END - $START" | bc)
echo "2|Docker Hub (--platform)|$TIME2" >> $RESULTS_FILE
log_ok "Docker Hub --platform: ${TIME2}s"
echo ""

# -----------------------------------------------------------------------------
# TESTE 3: Usando mirror do Docker Hub (se existir)
# -----------------------------------------------------------------------------
log_info "TESTE 3: Mirror Europeu (mirror.gcr.io)"
cleanup_image $TEST_IMAGE

# Tentar usar mirror do Google
MIRROR_IMAGE="mirror.gcr.io/library/ubuntu:22.04"
START=$(date +%s.%N)
docker pull $MIRROR_IMAGE 2>/dev/null || echo "Mirror não disponível"
END=$(date +%s.%N)
TIME3=$(echo "$END - $START" | bc)
echo "3|Mirror GCR|$TIME3" >> $RESULTS_FILE
log_ok "Mirror GCR: ${TIME3}s"
echo ""

# -----------------------------------------------------------------------------
# TESTE 4: Usando registry europeu (quay.io)
# -----------------------------------------------------------------------------
log_info "TESTE 4: Quay.io (Red Hat registry)"
cleanup_image "quay.io/fedora/fedora:latest"

START=$(date +%s.%N)
docker pull quay.io/fedora/fedora:latest
END=$(date +%s.%N)
TIME4=$(echo "$END - $START" | bc)
echo "4|Quay.io|$TIME4" >> $RESULTS_FILE
log_ok "Quay.io: ${TIME4}s"
echo ""

# -----------------------------------------------------------------------------
# TESTE 5: Usando ghcr.io (GitHub Container Registry)
# -----------------------------------------------------------------------------
log_info "TESTE 5: GHCR (GitHub Container Registry)"
# Testar com uma imagem pública do GHCR
GHCR_IMAGE="ghcr.io/linuxserver/baseimage-ubuntu:jammy"
cleanup_image $GHCR_IMAGE

START=$(date +%s.%N)
docker pull $GHCR_IMAGE 2>/dev/null || echo "GHCR não disponível"
END=$(date +%s.%N)
TIME5=$(echo "$END - $START" | bc)
echo "5|GHCR|$TIME5" >> $RESULTS_FILE
log_ok "GHCR: ${TIME5}s"
echo ""

# -----------------------------------------------------------------------------
# TESTE 6: Pull concorrente (múltiplas conexões)
# -----------------------------------------------------------------------------
log_info "TESTE 6: Pull com max-concurrent-downloads=10"
cleanup_image $TEST_IMAGE

# Configurar dockerd para múltiplas conexões
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 10
}
EOF

# Reiniciar dockerd
pkill dockerd || true
sleep 2
dockerd > /tmp/docker.log 2>&1 &
sleep 5

START=$(date +%s.%N)
docker pull $TEST_IMAGE
END=$(date +%s.%N)
TIME6=$(echo "$END - $START" | bc)
echo "6|Concurrent (10)|$TIME6" >> $RESULTS_FILE
log_ok "Concurrent (10): ${TIME6}s"
echo ""

# -----------------------------------------------------------------------------
# TESTE 7: Salvar e restaurar via arquivo (simulando B2)
# -----------------------------------------------------------------------------
log_info "TESTE 7: docker save + docker load (simulando B2)"

# Salvar imagem
START=$(date +%s.%N)
docker save $TEST_IMAGE | gzip > /tmp/image.tar.gz
END=$(date +%s.%N)
SAVE_TIME=$(echo "$END - $START" | bc)
SAVE_SIZE=$(ls -lh /tmp/image.tar.gz | awk '{print $5}')
log_info "docker save: ${SAVE_TIME}s (arquivo: $SAVE_SIZE)"

# Limpar e carregar
cleanup_image $TEST_IMAGE
START=$(date +%s.%N)
docker load < /tmp/image.tar.gz
END=$(date +%s.%N)
TIME7=$(echo "$END - $START" | bc)
echo "7|docker load (local)|$TIME7" >> $RESULTS_FILE
log_ok "docker load: ${TIME7}s"
echo ""

# =============================================================================
# RESULTADOS
# =============================================================================

echo ""
echo "============================================"
echo "  RESULTADOS FINAIS"
echo "============================================"
echo ""
echo "Imagem testada: $TEST_IMAGE"
echo "Tamanho: $IMAGE_SIZE"
echo ""
echo "RANKING (mais rápido primeiro):"
echo "----------------------------------------"

# Ordenar resultados
sort -t'|' -k3 -n $RESULTS_FILE | while IFS='|' read num desc time; do
    printf "  %-25s %10.2fs\n" "$desc" "$time"
done

echo ""
echo "============================================"
echo ""

# Mostrar recomendação
BEST=$(sort -t'|' -k3 -n $RESULTS_FILE | head -1 | cut -d'|' -f2)
log_ok "RECOMENDAÇÃO: Use '$BEST' para máxima velocidade"
