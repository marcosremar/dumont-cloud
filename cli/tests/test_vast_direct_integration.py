#!/usr/bin/env python3
"""
Teste DIRETO de Integração VAST.ai - Dumont Cloud

Este script testa a integração REAL com a VAST.ai SEM depender do backend.
Usa a VAST_API_KEY diretamente para:

1. Buscar ofertas disponíveis
2. Provisionar GPU (RTX 4090 ou similar, < $0.50/h)
3. Aguardar instância ficar running
4. Conectar via SSH
5. Criar arquivo de teste
6. Verificar arquivo existe
7. Destruir instância
8. Gerar relatório com métricas REAIS

ATENÇÃO: ESTE TESTE USA CRÉDITOS REAIS!
Executar: python cli/tests/test_vast_direct_integration.py
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

# Adicionar src ao path para importar VastService
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from src.services.gpu.vast import VastService


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

VAST_API_KEY = os.environ.get("VAST_API_KEY")
if not VAST_API_KEY:
    print("ERROR: VAST_API_KEY não encontrada no .env")
    sys.exit(1)

# Filtros para buscar GPU
MAX_PRICE = 0.50  # USD/hora (máximo)
MIN_DISK = 20     # GB
MIN_RELIABILITY = 0.90  # 90%+

# Timeouts
TIMEOUT_INSTANCE_READY = 600  # 10 min
TIMEOUT_SSH_READY = 300       # 5 min


@dataclass
class TestMetrics:
    """Métricas coletadas durante o teste"""
    test_name: str = "vast_direct_integration"
    start_time: float = field(default_factory=time.time)

    # IDs e recursos
    offer_id: Optional[int] = None
    instance_id: Optional[int] = None
    gpu_name: Optional[str] = None
    gpu_price: float = 0.0

    # SSH info
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None

    # Tempos (segundos)
    time_search_offers: float = 0
    time_create_instance: float = 0
    time_wait_running: float = 0
    time_wait_ssh: float = 0
    time_create_file: float = 0
    time_verify_file: float = 0
    time_destroy: float = 0
    time_total: float = 0

    # Status
    success: bool = False
    error_message: Optional[str] = None
    file_created: bool = False
    file_verified: bool = False

    # Custo
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat(),
            "resources": {
                "offer_id": self.offer_id,
                "instance_id": self.instance_id,
                "gpu_name": self.gpu_name,
                "gpu_price_per_hour": round(self.gpu_price, 4),
            },
            "ssh": {
                "host": self.ssh_host,
                "port": self.ssh_port,
            },
            "timings": {
                "search_offers_sec": round(self.time_search_offers, 2),
                "create_instance_sec": round(self.time_create_instance, 2),
                "wait_running_sec": round(self.time_wait_running, 2),
                "wait_ssh_sec": round(self.time_wait_ssh, 2),
                "create_file_sec": round(self.time_create_file, 2),
                "verify_file_sec": round(self.time_verify_file, 2),
                "destroy_sec": round(self.time_destroy, 2),
                "total_sec": round(self.time_total, 2),
                "total_min": round(self.time_total / 60, 2),
            },
            "validation": {
                "file_created": self.file_created,
                "file_verified": self.file_verified,
                "success": self.success,
                "error": self.error_message,
            },
            "cost": {
                "estimated_usd": round(self.estimated_cost_usd, 4),
            }
        }


# =============================================================================
# SSH HELPERS
# =============================================================================

def ssh_exec(host: str, port: int, command: str, timeout: int = 30) -> Dict[str, Any]:
    """Executa comando via SSH"""
    cmd = [
        "ssh",
        "-p", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        "-o", "LogLevel=ERROR",
        f"root@{host}",
        command
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Timeout after {timeout}s",
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


def wait_for_ssh(host: str, port: int, timeout: int = 300) -> bool:
    """Aguarda SSH ficar disponível"""
    print(f"   Aguardando SSH em {host}:{port}...")
    start = time.time()

    while time.time() - start < timeout:
        result = ssh_exec(host, port, "echo ready", timeout=5)
        if result["success"] and "ready" in result["stdout"]:
            elapsed = time.time() - start
            print(f"   ✓ SSH disponível após {elapsed:.1f}s")
            return True

        # Aguardar antes de tentar novamente
        time.sleep(10)

    print(f"   ✗ SSH timeout após {timeout}s")
    return False


# =============================================================================
# TESTE PRINCIPAL
# =============================================================================

def run_vast_integration_test() -> TestMetrics:
    """
    Executa teste completo de integração VAST.ai

    Returns:
        TestMetrics com resultados
    """
    metrics = TestMetrics()
    vast = VastService(VAST_API_KEY)

    print("\n" + "="*80)
    print("TESTE DE INTEGRAÇÃO REAL - VAST.AI")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Max price: ${MAX_PRICE}/hora")
    print(f"Min disk: {MIN_DISK} GB")
    print(f"Min reliability: {MIN_RELIABILITY}")
    print("="*80)

    try:
        # =====================================================================
        # PASSO 1: BUSCAR OFERTAS
        # =====================================================================
        print("\n[1/8] Buscando ofertas disponíveis...")
        start = time.time()

        offers = vast.search_offers(
            gpu_name="RTX 4090",  # Preferir RTX 4090 (barata e potente)
            num_gpus=1,
            min_disk=MIN_DISK,
            max_price=MAX_PRICE,
            min_reliability=MIN_RELIABILITY,
            machine_type="on-demand",
            limit=20
        )

        # Se não achar RTX 4090, buscar qualquer GPU
        if not offers:
            print("   Nenhuma RTX 4090 encontrada, buscando qualquer GPU...")
            offers = vast.search_offers(
                num_gpus=1,
                min_disk=MIN_DISK,
                max_price=MAX_PRICE,
                min_reliability=MIN_RELIABILITY,
                machine_type="on-demand",
                limit=20
            )

        metrics.time_search_offers = time.time() - start

        if not offers:
            raise Exception(f"Nenhuma oferta encontrada (max_price=${MAX_PRICE})")

        # Escolher a mais barata
        offer = min(offers, key=lambda x: x.get("dph_total", 999))

        metrics.offer_id = offer.get("id")
        metrics.gpu_name = offer.get("gpu_name", "Unknown")
        metrics.gpu_price = offer.get("dph_total", 0)

        print(f"   ✓ {len(offers)} ofertas encontradas")
        print(f"   Escolhida:")
        print(f"      GPU: {metrics.gpu_name}")
        print(f"      Preço: ${metrics.gpu_price:.4f}/hora")
        print(f"      Offer ID: {metrics.offer_id}")
        print(f"      Região: {offer.get('geolocation', 'Unknown')}")
        print(f"      Reliability: {offer.get('reliability2', 0):.1%}")
        print(f"   Tempo: {metrics.time_search_offers:.2f}s")

        # =====================================================================
        # PASSO 2: CRIAR INSTÂNCIA
        # =====================================================================
        print("\n[2/8] Provisionando instância...")
        start = time.time()

        instance_id = vast.create_instance(
            offer_id=metrics.offer_id,
            image="nvidia/cuda:12.1.0-base-ubuntu22.04",
            disk=MIN_DISK,
            use_template=False,  # Usar imagem direta (mais confiável para SSH)
            onstart_cmd="touch ~/.no_auto_tmux && apt-get update -qq",
            label="vast-integration-test"
        )

        metrics.time_create_instance = time.time() - start

        if not instance_id:
            raise Exception("Falha ao criar instância (create_instance retornou None)")

        metrics.instance_id = instance_id

        print(f"   ✓ Instância criada: {instance_id}")
        print(f"   Tempo: {metrics.time_create_instance:.2f}s")

        # =====================================================================
        # PASSO 3: AGUARDAR STATUS = RUNNING
        # =====================================================================
        print(f"\n[3/8] Aguardando status = running (até {TIMEOUT_INSTANCE_READY}s)...")
        start = time.time()

        status_info = None
        while time.time() - start < TIMEOUT_INSTANCE_READY:
            status_info = vast.get_instance_status(instance_id)

            if "error" in status_info:
                print(f"   Erro ao verificar status: {status_info['error']}")
                time.sleep(10)
                continue

            # Tratar status None
            actual_status = status_info.get("actual_status")
            status = actual_status.lower() if actual_status else "unknown"

            ssh_host = status_info.get("ssh_host")
            ssh_port = status_info.get("ssh_port")

            elapsed = time.time() - start
            print(f"   Status: {status} (elapsed: {elapsed:.1f}s)", end="\r")

            if status == "running" and ssh_host and ssh_port:
                metrics.ssh_host = ssh_host
                metrics.ssh_port = ssh_port
                break

            time.sleep(10)

        metrics.time_wait_running = time.time() - start

        if not metrics.ssh_host or not metrics.ssh_port:
            raise Exception(f"Instância não ficou running após {TIMEOUT_INSTANCE_READY}s")

        print(f"\n   ✓ Instância running")
        print(f"   SSH: {metrics.ssh_host}:{metrics.ssh_port}")
        print(f"   Tempo: {metrics.time_wait_running:.2f}s")

        # =====================================================================
        # PASSO 4: AGUARDAR SSH DISPONÍVEL
        # =====================================================================
        print(f"\n[4/8] Aguardando SSH ficar acessível (até {TIMEOUT_SSH_READY}s)...")
        start = time.time()

        ssh_ready = wait_for_ssh(metrics.ssh_host, metrics.ssh_port, timeout=TIMEOUT_SSH_READY)

        metrics.time_wait_ssh = time.time() - start

        if not ssh_ready:
            raise Exception(f"SSH não ficou disponível após {TIMEOUT_SSH_READY}s")

        print(f"   Tempo: {metrics.time_wait_ssh:.2f}s")

        # =====================================================================
        # PASSO 5: CRIAR ARQUIVO DE TESTE
        # =====================================================================
        print("\n[5/8] Criando arquivo de teste via SSH...")
        start = time.time()

        timestamp = int(time.time())
        test_file = f"/workspace/failover-test-{timestamp}.txt"
        test_content = f"Dumont Cloud Failover Test\\nTimestamp: {timestamp}\\nDate: {datetime.now().isoformat()}"

        # Criar diretório workspace
        result = ssh_exec(metrics.ssh_host, metrics.ssh_port, "mkdir -p /workspace")
        if not result["success"]:
            raise Exception(f"Falha ao criar /workspace: {result['stderr']}")

        # Criar arquivo
        create_cmd = f"echo '{test_content}' > {test_file}"
        result = ssh_exec(metrics.ssh_host, metrics.ssh_port, create_cmd)

        metrics.time_create_file = time.time() - start

        if not result["success"]:
            raise Exception(f"Falha ao criar arquivo: {result['stderr']}")

        metrics.file_created = True

        print(f"   ✓ Arquivo criado: {test_file}")
        print(f"   Tempo: {metrics.time_create_file:.2f}s")

        # =====================================================================
        # PASSO 6: VERIFICAR ARQUIVO EXISTE
        # =====================================================================
        print("\n[6/8] Verificando arquivo existe...")
        start = time.time()

        verify_cmd = f"test -f {test_file} && cat {test_file}"
        result = ssh_exec(metrics.ssh_host, metrics.ssh_port, verify_cmd)

        metrics.time_verify_file = time.time() - start

        if not result["success"]:
            raise Exception(f"Arquivo não encontrado: {result['stderr']}")

        # Verificar conteúdo
        if str(timestamp) not in result["stdout"]:
            raise Exception(f"Conteúdo do arquivo incorreto: {result['stdout']}")

        metrics.file_verified = True

        print(f"   ✓ Arquivo verificado")
        print(f"   Conteúdo:\n{result['stdout']}")
        print(f"   Tempo: {metrics.time_verify_file:.2f}s")

        # =====================================================================
        # PASSO 7: OBTER INFORMAÇÕES DA GPU
        # =====================================================================
        print("\n[7/8] Coletando informações da GPU...")

        # nvidia-smi
        nvidia_result = ssh_exec(metrics.ssh_host, metrics.ssh_port, "nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader", timeout=10)
        if nvidia_result["success"]:
            print(f"   GPU Info: {nvidia_result['stdout']}")
        else:
            print(f"   nvidia-smi não disponível (OK se não for GPU)")

        # Disk usage
        disk_result = ssh_exec(metrics.ssh_host, metrics.ssh_port, "df -h /workspace | tail -n1", timeout=10)
        if disk_result["success"]:
            print(f"   Disk: {disk_result['stdout']}")

        # =====================================================================
        # PASSO 8: DESTRUIR INSTÂNCIA
        # =====================================================================
        print("\n[8/8] Destruindo instância...")
        start = time.time()

        success = vast.destroy_instance(metrics.instance_id)

        metrics.time_destroy = time.time() - start

        if not success:
            print(f"   ⚠ Falha ao destruir instância (verifique manualmente!)")
        else:
            print(f"   ✓ Instância destruída")

        print(f"   Tempo: {metrics.time_destroy:.2f}s")

        # =====================================================================
        # CALCULAR MÉTRICAS FINAIS
        # =====================================================================
        metrics.time_total = time.time() - metrics.start_time
        hours_used = metrics.time_total / 3600
        metrics.estimated_cost_usd = hours_used * metrics.gpu_price

        metrics.success = (
            metrics.file_created and
            metrics.file_verified and
            success
        )

    except Exception as e:
        metrics.error_message = str(e)
        metrics.success = False
        print(f"\n✗ ERRO: {e}")

        # Tentar cleanup em caso de erro
        if metrics.instance_id:
            print("\n[CLEANUP] Tentando destruir instância após erro...")
            try:
                vast.destroy_instance(metrics.instance_id)
                print("   ✓ Instância destruída")
            except Exception as cleanup_error:
                print(f"   ⚠ Falha no cleanup: {cleanup_error}")

    return metrics


# =============================================================================
# RELATÓRIO FINAL
# =============================================================================

def print_report(metrics: TestMetrics):
    """Imprime relatório formatado"""
    print("\n" + "="*80)
    print("RELATÓRIO FINAL - TESTE DE INTEGRAÇÃO VAST.AI")
    print("="*80)

    print(f"\nTeste: {metrics.test_name}")
    print(f"Data: {datetime.fromtimestamp(metrics.start_time).isoformat()}")

    print("\nRecursos:")
    print(f"  Offer ID:     {metrics.offer_id}")
    print(f"  Instance ID:  {metrics.instance_id}")
    print(f"  GPU:          {metrics.gpu_name}")
    print(f"  Preço:        ${metrics.gpu_price:.4f}/hora")
    if metrics.ssh_host:
        print(f"  SSH:          {metrics.ssh_host}:{metrics.ssh_port}")

    print("\nTiming Breakdown:")
    print(f"  1. Buscar ofertas:      {metrics.time_search_offers:7.2f}s")
    print(f"  2. Criar instância:     {metrics.time_create_instance:7.2f}s")
    print(f"  3. Aguardar running:    {metrics.time_wait_running:7.2f}s")
    print(f"  4. Aguardar SSH:        {metrics.time_wait_ssh:7.2f}s")
    print(f"  5. Criar arquivo:       {metrics.time_create_file:7.2f}s")
    print(f"  6. Verificar arquivo:   {metrics.time_verify_file:7.2f}s")
    print(f"  7. Destruir instância:  {metrics.time_destroy:7.2f}s")
    print(f"  {'─'*40}")
    print(f"  TOTAL:                  {metrics.time_total:7.2f}s ({metrics.time_total/60:.1f} min)")

    print("\nValidação:")
    print(f"  Arquivo criado:   {'✓ SIM' if metrics.file_created else '✗ NÃO'}")
    print(f"  Arquivo verificado: {'✓ SIM' if metrics.file_verified else '✗ NÃO'}")
    print(f"  Sucesso geral:    {'✓ SIM' if metrics.success else '✗ NÃO'}")
    if metrics.error_message:
        print(f"  Erro:             {metrics.error_message}")

    print("\nCusto:")
    print(f"  Tempo total:      {metrics.time_total/3600:.4f} horas")
    print(f"  Preço/hora:       ${metrics.gpu_price:.4f}")
    print(f"  CUSTO ESTIMADO:   ${metrics.estimated_cost_usd:.4f}")

    print("\n" + "="*80)

    # Salvar JSON
    report_path = "/Users/marcos/CascadeProjects/dumontcloud/vast_integration_test_report.json"
    with open(report_path, "w") as f:
        json.dump(metrics.to_dict(), f, indent=2)

    print(f"\nRelatório JSON salvo em: {report_path}")
    print("="*80 + "\n")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n⚠️  ATENÇÃO: Este teste irá provisionar uma GPU REAL na VAST.ai!")
    print(f"   Custo estimado: ~${MAX_PRICE}/hora")
    print(f"   Duração estimada: ~5-15 minutos")
    print(f"   Custo total estimado: ~$0.10-0.30 USD\n")

    response = input("Deseja continuar? [y/N]: ")
    if response.lower() not in ['y', 'yes']:
        print("Teste cancelado pelo usuário.")
        sys.exit(0)

    # Executar teste
    metrics = run_vast_integration_test()

    # Imprimir relatório
    print_report(metrics)

    # Exit code
    sys.exit(0 if metrics.success else 1)
