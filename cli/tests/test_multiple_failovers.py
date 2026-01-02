"""
Test 4.2: Multiple Failovers (5x) - Dumont Cloud

Testa múltiplos ciclos de failover para validar estabilidade:
1. Criar arquivos iniciais na GPU 1
2. Loop 5 vezes:
   - Criar snapshot
   - Destruir GPU atual
   - Provisionar nova GPU
   - Restaurar snapshot
   - Validar arquivos (MD5)
3. Calcular:
   - Taxa de sucesso (deve ser 100%)
   - Tempo médio por failover
   - Custo total acumulado
   - Variância nos tempos

ATENÇÃO: ESTE TESTE É CARO!
- VAST.ai: ~$1.50-3.00 (6 GPUs total)
- Backblaze B2: ~$0.05 (5 snapshots)
- Tempo total: ~30-60 min

Executar APENAS com flag --real:
    pytest cli/tests/test_multiple_failovers.py -v -s --real

Modo dry-run (simulação):
    pytest cli/tests/test_multiple_failovers.py -v -s --dry-run
"""

import pytest
import time
import json
import os
import subprocess
import statistics
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

DUMONT_API_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8766")
VAST_API_KEY = os.environ.get("VAST_API_KEY")
B2_ENDPOINT = os.environ.get("B2_ENDPOINT", "https://s3.us-west-000.backblazeb2.com")
B2_BUCKET = os.environ.get("B2_BUCKET", "dumontcloud-snapshots")

# Configuração do teste
NUM_FAILOVERS = 5  # Reduzido de 10 para 5

# Timeouts
TIMEOUT_INSTANCE_CREATE = 300
TIMEOUT_INSTANCE_READY = 600
TIMEOUT_SNAPSHOT_CREATE = 300
TIMEOUT_RESTORE = 300


@dataclass
class FailoverCycle:
    """Representa um ciclo de failover"""
    cycle_number: int
    old_instance_id: Optional[str] = None
    new_instance_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    time_snapshot: float = 0
    time_destroy: float = 0
    time_provision: float = 0
    time_restore: float = 0
    time_validate: float = 0
    time_total: float = 0
    files_validated: int = 0
    files_failed: int = 0
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class MultipleFailoversMetrics:
    """Métricas do teste de múltiplos failovers"""
    test_name: str = "multiple_failovers"
    start_time: float = field(default_factory=time.time)

    # Configuração
    num_failovers: int = NUM_FAILOVERS
    num_test_files: int = 3

    # ID inicial
    initial_instance_id: Optional[str] = None

    # Ciclos de failover
    failover_cycles: List[FailoverCycle] = field(default_factory=list)

    # Arquivos de teste
    test_files: List[Dict[str, str]] = field(default_factory=list)

    # Tempos agregados
    time_initial_setup: float = 0
    time_total: float = 0

    # Estatísticas
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0
    avg_failover_time: float = 0
    min_failover_time: float = 0
    max_failover_time: float = 0
    std_dev_failover_time: float = 0

    # Custos
    gpu_cost_per_hour: float = 0
    estimated_total_cost_usd: float = 0

    # Status geral
    all_succeeded: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat(),
            "config": {
                "num_failovers": self.num_failovers,
                "num_test_files": self.num_test_files,
            },
            "initial_instance_id": self.initial_instance_id,
            "cycles": [
                {
                    "cycle": cycle.cycle_number,
                    "old_instance": cycle.old_instance_id,
                    "new_instance": cycle.new_instance_id,
                    "snapshot": cycle.snapshot_id,
                    "timings": {
                        "snapshot_sec": round(cycle.time_snapshot, 2),
                        "destroy_sec": round(cycle.time_destroy, 2),
                        "provision_sec": round(cycle.time_provision, 2),
                        "restore_sec": round(cycle.time_restore, 2),
                        "validate_sec": round(cycle.time_validate, 2),
                        "total_sec": round(cycle.time_total, 2),
                    },
                    "validation": {
                        "files_validated": cycle.files_validated,
                        "files_failed": cycle.files_failed,
                        "success": cycle.success,
                    },
                    "error": cycle.error_message,
                }
                for cycle in self.failover_cycles
            ],
            "statistics": {
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "success_rate": round(self.success_rate, 4),
                "avg_failover_time_sec": round(self.avg_failover_time, 2),
                "min_failover_time_sec": round(self.min_failover_time, 2),
                "max_failover_time_sec": round(self.max_failover_time, 2),
                "std_dev_sec": round(self.std_dev_failover_time, 2),
            },
            "timings": {
                "initial_setup_sec": round(self.time_initial_setup, 2),
                "total_sec": round(self.time_total, 2),
                "total_min": round(self.time_total / 60, 2),
            },
            "cost": {
                "gpu_hourly_usd": round(self.gpu_cost_per_hour, 4),
                "estimated_total_usd": round(self.estimated_total_cost_usd, 4),
            },
            "validation": {
                "all_succeeded": self.all_succeeded,
                "error": self.error_message,
            }
        }


# =============================================================================
# HELPERS
# =============================================================================

def call_api(method: str, endpoint: str, data: Optional[Dict] = None, token: Optional[str] = None) -> Dict:
    """Chama API do Dumont com retry"""
    import requests

    url = f"{DUMONT_API_URL}{endpoint}"
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.ok:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"success": True, "raw": response.text}
            else:
                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f"   Rate limit (429). Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                return {
                    "error": f"HTTP {response.status_code}",
                    "detail": response.text[:200]
                }

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"error": "Request timeout"}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"error": str(e)}

    return {"error": "Max retries exceeded"}


def get_auth_token() -> Optional[str]:
    """Obtém token de autenticação"""
    result = call_api("POST", "/api/v1/auth/login", {
        "email": "test@test.com",
        "password": "test123"
    })

    return result.get("access_token")


def ssh_exec(ssh_host: str, ssh_port: int, command: str, timeout: int = 120) -> Dict[str, Any]:
    """Executa comando via SSH"""
    cmd = [
        "ssh",
        "-p", str(ssh_port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=30",
        "-o", "LogLevel=ERROR",
        f"root@{ssh_host}",
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
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timeout after {timeout}s",
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


def wait_for_ssh(ssh_host: str, ssh_port: int, timeout: int = 300) -> bool:
    """Aguarda SSH ficar acessível"""
    start = time.time()

    while time.time() - start < timeout:
        result = ssh_exec(ssh_host, ssh_port, "echo ready", timeout=10)
        if result["success"]:
            return True
        time.sleep(10)

    return False


def wait_for_instance_ready(instance_id: str, token: str, timeout: int = 600) -> Dict[str, Any]:
    """Aguarda instância ficar running"""
    start = time.time()

    while time.time() - start < timeout:
        result = call_api("GET", f"/api/v1/instances/{instance_id}", token=token)

        if "error" not in result:
            status = result.get("status", "").lower()
            ssh_host = result.get("ssh_host")
            ssh_port = result.get("ssh_port")

            if status == "running" and ssh_host and ssh_port:
                if wait_for_ssh(ssh_host, ssh_port, timeout=60):
                    return {
                        "success": True,
                        "status": status,
                        "ssh_host": ssh_host,
                        "ssh_port": ssh_port,
                    }

        time.sleep(10)

    return {
        "success": False,
        "error": f"Instance not ready after {timeout}s"
    }


def provision_gpu(auth_token: str) -> Dict[str, Any]:
    """Provisiona uma GPU"""
    offers = call_api("GET", "/api/v1/instances/offers", token=auth_token)

    if "error" in offers:
        return {"error": f"Failed to get offers: {offers['error']}"}

    offers_list = offers.get("offers", [])
    if not offers_list:
        return {"error": "No GPU offers available"}

    cheapest = min(offers_list, key=lambda x: x.get("dph_total", 999))
    offer_id = cheapest.get("id")
    gpu_name = cheapest.get("gpu_name", "Unknown")
    price = cheapest.get("dph_total", 0)

    create_result = call_api("POST", "/api/v1/instances", {
        "offer_id": offer_id,
        "image": "nvidia/cuda:12.1.0-base-ubuntu22.04",
        "disk_size": 20,
    }, token=auth_token)

    if "error" in create_result:
        return {"error": f"Failed to create instance: {create_result['error']}"}

    instance_id = str(create_result.get("instance_id", create_result.get("id")))

    ready_result = wait_for_instance_ready(instance_id, auth_token, timeout=TIMEOUT_INSTANCE_READY)

    if not ready_result.get("success"):
        return {"error": f"Instance not ready: {ready_result.get('error')}"}

    return {
        "success": True,
        "instance_id": instance_id,
        "ssh_host": ready_result["ssh_host"],
        "ssh_port": ready_result["ssh_port"],
        "gpu_name": gpu_name,
        "price_per_hour": price,
    }


def create_test_file(ssh_host: str, ssh_port: int, file_path: str, content: str) -> Dict[str, str]:
    """Cria arquivo de teste"""
    create_cmd = f"echo '{content}' > {file_path}"
    result = ssh_exec(ssh_host, ssh_port, create_cmd)

    if not result["success"]:
        raise Exception(f"Failed to create file: {result['stderr']}")

    # Obter MD5
    md5_cmd = f"md5sum {file_path} | awk '{{print $1}}'"
    md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd)

    md5_hash = md5_result["stdout"].strip() if md5_result["success"] else ""

    return {
        "path": file_path,
        "content": content,
        "md5": md5_hash,
    }


def validate_file(ssh_host: str, ssh_port: int, expected_file: Dict[str, str]) -> bool:
    """Valida arquivo com MD5"""
    file_path = expected_file["path"]
    expected_md5 = expected_file["md5"]

    # Verificar existência
    check_cmd = f"test -f {file_path} && echo exists || echo missing"
    check_result = ssh_exec(ssh_host, ssh_port, check_cmd)

    if not check_result["success"] or "missing" in check_result["stdout"]:
        return False

    # Verificar MD5
    md5_cmd = f"md5sum {file_path} | awk '{{print $1}}'"
    md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd)

    if not md5_result["success"]:
        return False

    actual_md5 = md5_result["stdout"].strip()

    return actual_md5 == expected_md5


# =============================================================================
# TESTES
# =============================================================================

@pytest.fixture(scope="module")
def auth_token():
    """Token de autenticação"""
    token = get_auth_token()
    if not token:
        pytest.skip("Failed to authenticate")
    return token


@pytest.fixture(scope="module")
def metrics():
    """Objeto para coletar métricas"""
    return MultipleFailoversMetrics()


@pytest.mark.slow
@pytest.mark.real
class TestMultipleFailovers:
    """Teste de múltiplos failovers (5x)"""

    def test_01_initial_setup(self, auth_token, metrics):
        """[1/7] Setup inicial: provisionar GPU e criar arquivos"""
        print("\n" + "="*70)
        print(f"TESTE 4.2: MULTIPLE FAILOVERS ({NUM_FAILOVERS}x)")
        print("="*70)

        try:
            print(f"\n[1/7] Setup inicial...")
            start_setup = time.time()

            # Provisionar GPU inicial
            print("   [a] Provisionando GPU inicial...")
            result = provision_gpu(auth_token)

            if "error" in result:
                pytest.skip(result["error"])

            metrics.initial_instance_id = result["instance_id"]
            metrics.gpu_cost_per_hour = result["price_per_hour"]

            ssh_host = result["ssh_host"]
            ssh_port = result["ssh_port"]

            print(f"       Instance ID: {metrics.initial_instance_id}")
            print(f"       GPU: {result['gpu_name']}")
            print(f"       Preço: ${result['price_per_hour']:.4f}/hr")

            # Criar arquivos de teste
            print(f"   [b] Criando {metrics.num_test_files} arquivos de teste...")
            ssh_exec(ssh_host, ssh_port, "mkdir -p /workspace")

            for i in range(metrics.num_test_files):
                file_path = f"/workspace/failover-test-{i+1}.txt"
                content = f"Multiple failovers test file #{i+1}\\nTimestamp: {time.time()}\\nCreated: {datetime.now().isoformat()}\\n"

                test_file = create_test_file(ssh_host, ssh_port, file_path, content)
                metrics.test_files.append(test_file)

                print(f"       Created: {file_path} (MD5: {test_file['md5'][:8]}...)")

            metrics.time_initial_setup = time.time() - start_setup

            print(f"   ✓ Setup completo em {metrics.time_initial_setup:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_02_run_failover_cycles(self, auth_token, metrics):
        """[2/7] Executa ciclos de failover"""
        if not metrics.initial_instance_id:
            pytest.skip("No initial instance")

        current_instance_id = metrics.initial_instance_id

        for cycle_num in range(1, NUM_FAILOVERS + 1):
            print(f"\n[Cycle {cycle_num}/{NUM_FAILOVERS}] Iniciando failover...")

            cycle = FailoverCycle(cycle_number=cycle_num)
            cycle.old_instance_id = current_instance_id

            try:
                start_cycle = time.time()

                # [a] Criar snapshot
                print(f"   [a] Criando snapshot...")
                start_snapshot = time.time()

                snapshot_result = call_api("POST", "/api/v1/snapshots", {
                    "instance_id": current_instance_id,
                    "source_path": "/workspace",
                    "tags": [f"multiple-failovers", f"cycle-{cycle_num}"],
                }, token=auth_token)

                if "error" in snapshot_result:
                    raise Exception(f"Snapshot failed: {snapshot_result['error']}")

                cycle.snapshot_id = snapshot_result.get("snapshot_id", snapshot_result.get("id"))
                cycle.time_snapshot = time.time() - start_snapshot

                print(f"       Snapshot: {cycle.snapshot_id} ({cycle.time_snapshot:.1f}s)")

                # [b] Destruir GPU antiga
                print(f"   [b] Destruindo GPU antiga...")
                start_destroy = time.time()

                call_api("DELETE", f"/api/v1/instances/{current_instance_id}", token=auth_token)

                cycle.time_destroy = time.time() - start_destroy
                print(f"       Destruída em {cycle.time_destroy:.1f}s")

                # [c] Provisionar nova GPU
                print(f"   [c] Provisionando nova GPU...")
                start_provision = time.time()

                new_gpu = provision_gpu(auth_token)

                if "error" in new_gpu:
                    raise Exception(f"Provision failed: {new_gpu['error']}")

                cycle.new_instance_id = new_gpu["instance_id"]
                current_instance_id = cycle.new_instance_id
                cycle.time_provision = time.time() - start_provision

                print(f"       New GPU: {cycle.new_instance_id} ({cycle.time_provision:.1f}s)")

                # [d] Restaurar snapshot
                print(f"   [d] Restaurando snapshot...")
                start_restore = time.time()

                restore_result = call_api("POST", "/api/v1/snapshots/restore", {
                    "snapshot_id": cycle.snapshot_id,
                    "instance_id": cycle.new_instance_id,
                    "target_path": "/workspace",
                }, token=auth_token)

                if "error" in restore_result:
                    raise Exception(f"Restore failed: {restore_result['error']}")

                cycle.time_restore = time.time() - start_restore
                print(f"       Restored in {cycle.time_restore:.1f}s")

                # [e] Validar arquivos
                print(f"   [e] Validando arquivos...")
                start_validate = time.time()

                # Obter SSH info da nova GPU
                instance_info = call_api("GET", f"/api/v1/instances/{cycle.new_instance_id}", token=auth_token)
                ssh_host = instance_info.get("ssh_host")
                ssh_port = instance_info.get("ssh_port")

                if not ssh_host or not ssh_port:
                    raise Exception("SSH info not available")

                validated = 0
                failed = 0

                for test_file in metrics.test_files:
                    if validate_file(ssh_host, ssh_port, test_file):
                        validated += 1
                    else:
                        failed += 1

                cycle.files_validated = validated
                cycle.files_failed = failed
                cycle.time_validate = time.time() - start_validate

                print(f"       Validated: {validated}/{len(metrics.test_files)}")

                # Verificar sucesso
                cycle.success = (validated == len(metrics.test_files))
                cycle.time_total = time.time() - start_cycle

                if cycle.success:
                    print(f"   ✓ Cycle {cycle_num} SUCESSO em {cycle.time_total:.1f}s")
                    metrics.success_count += 1
                else:
                    print(f"   ✗ Cycle {cycle_num} FALHOU ({failed} arquivos faltando)")
                    metrics.failure_count += 1

            except Exception as e:
                cycle.error_message = str(e)
                cycle.success = False
                metrics.failure_count += 1
                print(f"   ✗ Cycle {cycle_num} ERRO: {e}")

            finally:
                metrics.failover_cycles.append(cycle)

    def test_03_calculate_statistics(self, metrics):
        """[3/7] Calcula estatísticas"""
        print(f"\n[3/7] Calculando estatísticas...")

        if not metrics.failover_cycles:
            pytest.skip("No failover cycles completed")

        # Taxa de sucesso
        total_cycles = len(metrics.failover_cycles)
        metrics.success_rate = metrics.success_count / total_cycles if total_cycles > 0 else 0

        # Tempos
        failover_times = [cycle.time_total for cycle in metrics.failover_cycles if cycle.success]

        if failover_times:
            metrics.avg_failover_time = statistics.mean(failover_times)
            metrics.min_failover_time = min(failover_times)
            metrics.max_failover_time = max(failover_times)

            if len(failover_times) > 1:
                metrics.std_dev_failover_time = statistics.stdev(failover_times)
            else:
                metrics.std_dev_failover_time = 0

        print(f"   Success rate: {metrics.success_rate*100:.1f}%")
        print(f"   Avg time: {metrics.avg_failover_time:.1f}s")
        print(f"   Min time: {metrics.min_failover_time:.1f}s")
        print(f"   Max time: {metrics.max_failover_time:.1f}s")
        print(f"   Std dev: {metrics.std_dev_failover_time:.1f}s")

    def test_04_cleanup_final_instance(self, auth_token, metrics):
        """[4/7] Cleanup: destruir última GPU"""
        if metrics.failover_cycles:
            last_cycle = metrics.failover_cycles[-1]
            if last_cycle.new_instance_id:
                try:
                    print(f"\n[4/7] Destruindo última GPU...")
                    call_api("DELETE", f"/api/v1/instances/{last_cycle.new_instance_id}", token=auth_token)
                    print(f"   ✓ GPU destruída: {last_cycle.new_instance_id}")
                except Exception as e:
                    print(f"   ⚠ Warning: {e}")

    def test_05_generate_report(self, metrics):
        """[5/7] Gera relatório final"""
        print(f"\n[5/7] Gerando relatório...")

        # Calcular totais
        metrics.time_total = time.time() - metrics.start_time
        hours_used = metrics.time_total / 3600
        num_gpus = NUM_FAILOVERS + 1  # Initial + todas as novas
        metrics.estimated_total_cost_usd = hours_used * metrics.gpu_cost_per_hour * num_gpus

        # Determinar sucesso geral
        metrics.all_succeeded = (metrics.success_rate == 1.0)

        # Relatório
        print("\n" + "="*70)
        print("RELATÓRIO: MULTIPLE FAILOVERS TEST")
        print("="*70)

        print(f"\nConfiguração:")
        print(f"  Failovers:       {metrics.num_failovers}")
        print(f"  Test Files:      {metrics.num_test_files}")

        print(f"\nResultados:")
        print(f"  Cycles Success:  {metrics.success_count}/{len(metrics.failover_cycles)}")
        print(f"  Cycles Failed:   {metrics.failure_count}")
        print(f"  Success Rate:    {metrics.success_rate*100:.1f}%")

        print(f"\nEstatísticas de Tempo:")
        print(f"  Avg Failover:    {metrics.avg_failover_time:.1f}s")
        print(f"  Min Failover:    {metrics.min_failover_time:.1f}s")
        print(f"  Max Failover:    {metrics.max_failover_time:.1f}s")
        print(f"  Std Dev:         {metrics.std_dev_failover_time:.1f}s")

        print(f"\nTempo Total:")
        print(f"  Initial Setup:   {metrics.time_initial_setup:.1f}s")
        print(f"  TOTAL:           {metrics.time_total:.1f}s ({metrics.time_total/60:.1f} min)")

        print(f"\nCusto:")
        print(f"  GPU hourly:      ${metrics.gpu_cost_per_hour:.4f}/hr")
        print(f"  Tempo total:     {hours_used:.4f} hrs")
        print(f"  GPUs usadas:     {num_gpus}")
        print(f"  Total estimado:  ${metrics.estimated_total_cost_usd:.4f}")

        print(f"\nValidação:")
        print(f"  All Succeeded:   {'✓ SIM' if metrics.all_succeeded else '✗ NÃO'}")

        print("\n" + "="*70)

        # Salvar em JSON
        report_file = f"/tmp/multiple_failovers_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)

        print(f"\nRelatório salvo em: {report_file}")

        # Assert final
        assert metrics.all_succeeded, (
            f"Multiple failovers test failed: {metrics.success_rate*100:.1f}% success rate "
            f"({metrics.failure_count} failures)"
        )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v", "-s",
        "--tb=short",
        "-m", "slow and real",
    ])
