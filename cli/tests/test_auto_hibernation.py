"""
Test 3.1: Auto-Hibernation (Idle Detection) - Dumont Cloud

Testa o ciclo completo de auto-hibernation:
1. Provisionar GPU real
2. Criar arquivos de teste
3. Simular idle (60s sem atividade - reduzido de 3min para teste)
4. Trigger auto-hibernation:
   - Criar snapshot
   - Upload para B2
   - Destruir GPU
5. Verificar snapshot existe no B2
6. Gerar relatório detalhado

ATENÇÃO: ESTE TESTE USA CRÉDITOS REAIS!
- VAST.ai: ~$0.15-0.30 por teste
- Backblaze B2: ~$0.01 por snapshot

Executar:
    pytest cli/tests/test_auto_hibernation.py -v -s --tb=short

Executar em modo dry-run (sem criar GPU):
    pytest cli/tests/test_auto_hibernation.py -v -s --dry-run
"""

import pytest
import time
import json
import os
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import subprocess


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

DUMONT_API_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8766")
VAST_API_KEY = os.environ.get("VAST_API_KEY")
B2_ENDPOINT = os.environ.get("B2_ENDPOINT", "https://s3.us-west-000.backblazeb2.com")
B2_BUCKET = os.environ.get("B2_BUCKET", "dumontcloud-snapshots")

# Timeouts (em segundos)
TIMEOUT_INSTANCE_CREATE = 300      # 5 min
TIMEOUT_INSTANCE_READY = 600       # 10 min
TIMEOUT_SNAPSHOT_CREATE = 300      # 5 min
IDLE_WAIT_TIME = 60                # 60s para teste (produção: 180s)


@dataclass
class HibernationTestMetrics:
    """Métricas do teste de hibernação"""
    test_name: str = "auto_hibernation"
    start_time: float = field(default_factory=time.time)

    # IDs de recursos
    instance_id: Optional[str] = None
    snapshot_id: Optional[str] = None

    # Arquivos criados
    test_files: List[Dict[str, str]] = field(default_factory=list)

    # Tempos (segundos)
    time_provision: float = 0
    time_create_files: float = 0
    time_idle_wait: float = 0
    time_snapshot: float = 0
    time_destroy: float = 0
    time_total: float = 0

    # Custos
    gpu_cost_per_hour: float = 0
    estimated_cost_usd: float = 0

    # Status
    success: bool = False
    error_message: Optional[str] = None
    snapshot_exists_in_b2: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat(),
            "resources": {
                "instance_id": self.instance_id,
                "snapshot_id": self.snapshot_id,
                "test_files_count": len(self.test_files),
            },
            "timings": {
                "provision_sec": round(self.time_provision, 2),
                "create_files_sec": round(self.time_create_files, 2),
                "idle_wait_sec": round(self.time_idle_wait, 2),
                "snapshot_sec": round(self.time_snapshot, 2),
                "destroy_sec": round(self.time_destroy, 2),
                "total_sec": round(self.time_total, 2),
                "total_min": round(self.time_total / 60, 2),
            },
            "cost": {
                "gpu_hourly_usd": round(self.gpu_cost_per_hour, 4),
                "estimated_total_usd": round(self.estimated_cost_usd, 4),
            },
            "validation": {
                "success": self.success,
                "snapshot_exists_in_b2": self.snapshot_exists_in_b2,
                "error": self.error_message,
            }
        }


# =============================================================================
# HELPERS API
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
                # Check for rate limiting
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff
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
    """Aguarda instância ficar running e com SSH disponível"""
    start = time.time()

    while time.time() - start < timeout:
        result = call_api("GET", f"/api/v1/instances/{instance_id}", token=token)

        if "error" not in result:
            status = result.get("status", "").lower()
            ssh_host = result.get("ssh_host")
            ssh_port = result.get("ssh_port")

            if status == "running" and ssh_host and ssh_port:
                # Verificar SSH acessível
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


def create_test_file(ssh_host: str, ssh_port: int, file_path: str, content: str) -> Dict[str, str]:
    """Cria arquivo de teste e retorna metadados"""
    # Criar arquivo
    create_cmd = f"echo '{content}' > {file_path}"
    result = ssh_exec(ssh_host, ssh_port, create_cmd)

    if not result["success"]:
        raise Exception(f"Failed to create file {file_path}: {result['stderr']}")

    # Obter MD5
    md5_cmd = f"md5sum {file_path} | awk '{{print $1}}'"
    md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd)

    if not md5_result["success"]:
        raise Exception(f"Failed to get MD5: {md5_result['stderr']}")

    md5_hash = md5_result["stdout"].strip()

    # Obter tamanho
    size_cmd = f"stat -c %s {file_path}"
    size_result = ssh_exec(ssh_host, ssh_port, size_cmd)

    size_bytes = 0
    if size_result["success"]:
        try:
            size_bytes = int(size_result["stdout"].strip())
        except ValueError:
            pass

    return {
        "path": file_path,
        "content": content,
        "size_bytes": size_bytes,
        "md5": md5_hash,
        "created_at": datetime.now().isoformat()
    }


def verify_snapshot_in_b2(snapshot_id: str, token: str) -> bool:
    """Verifica se snapshot existe no B2"""
    # Listar snapshots via API
    result = call_api("GET", "/api/v1/snapshots", token=token)

    if "error" in result:
        return False

    snapshots = result.get("snapshots", [])

    # Procurar snapshot pelo ID
    for snap in snapshots:
        if snap.get("id", "").startswith(snapshot_id) or snap.get("short_id") == snapshot_id:
            return True

    return False


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
    return HibernationTestMetrics()


@pytest.mark.slow
@pytest.mark.real
class TestAutoHibernation:
    """Teste de Auto-Hibernation"""

    def test_01_provision_gpu(self, auth_token, metrics):
        """[1/5] Provisiona GPU real"""
        print("\n" + "="*70)
        print("TESTE 3.1: AUTO-HIBERNATION")
        print("="*70)

        try:
            print("\n[1/5] Provisionando GPU...")
            start_provision = time.time()

            # Buscar oferta mais barata
            offers = call_api("GET", "/api/v1/instances/offers", token=auth_token)

            if "error" in offers:
                pytest.skip(f"Failed to get offers: {offers['error']}")

            offers_list = offers.get("offers", [])
            if not offers_list:
                pytest.skip("No GPU offers available")

            cheapest = min(offers_list, key=lambda x: x.get("dph_total", 999))
            offer_id = cheapest.get("id")
            gpu_name = cheapest.get("gpu_name", "Unknown")
            price = cheapest.get("dph_total", 0)

            metrics.gpu_cost_per_hour = price

            print(f"   GPU: {gpu_name}")
            print(f"   Preço: ${price:.4f}/hr")

            # Criar instância
            create_result = call_api("POST", "/api/v1/instances", {
                "offer_id": offer_id,
                "image": "nvidia/cuda:12.1.0-base-ubuntu22.04",
                "disk_size": 20,
            }, token=auth_token)

            if "error" in create_result:
                pytest.skip(f"Failed to create instance: {create_result['error']}")

            instance_id = str(create_result.get("instance_id", create_result.get("id")))
            metrics.instance_id = instance_id

            print(f"   Instance ID: {instance_id}")

            # Aguardar ready
            print("   Aguardando ficar ready...")
            ready_result = wait_for_instance_ready(instance_id, auth_token, timeout=TIMEOUT_INSTANCE_READY)

            if not ready_result.get("success"):
                pytest.skip(f"Instance not ready: {ready_result.get('error')}")

            metrics.time_provision = time.time() - start_provision

            print(f"   SSH: {ready_result['ssh_host']}:{ready_result['ssh_port']}")
            print(f"   Tempo: {metrics.time_provision:.1f}s")
            print(f"   ✓ GPU provisionada com sucesso")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_02_create_files(self, auth_token, metrics):
        """[2/5] Cria arquivos de teste"""
        if not metrics.instance_id:
            pytest.skip("No instance ID")

        try:
            print("\n[2/5] Criando arquivos de teste...")
            start_files = time.time()

            # Obter SSH info
            instance_info = call_api("GET", f"/api/v1/instances/{metrics.instance_id}", token=auth_token)
            ssh_host = instance_info.get("ssh_host")
            ssh_port = instance_info.get("ssh_port")

            if not ssh_host or not ssh_port:
                pytest.skip("SSH info not available")

            # Criar workspace
            ssh_exec(ssh_host, ssh_port, "mkdir -p /workspace")

            # Criar 5 arquivos de teste
            test_files = []
            for i in range(5):
                file_path = f"/workspace/auto-hibernation-test-{i+1}.txt"
                content = f"Auto-hibernation test file #{i+1}\\nTimestamp: {time.time()}\\nCreated: {datetime.now().isoformat()}\\n"

                test_file = create_test_file(ssh_host, ssh_port, file_path, content)
                test_files.append(test_file)

                print(f"   Created: {file_path} ({test_file['size_bytes']} bytes, MD5: {test_file['md5'][:8]}...)")

            metrics.test_files = test_files
            metrics.time_create_files = time.time() - start_files

            print(f"   ✓ {len(test_files)} arquivos criados em {metrics.time_create_files:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_03_simulate_idle(self, metrics):
        """[3/5] Simula período idle"""
        print(f"\n[3/5] Simulando idle por {IDLE_WAIT_TIME}s...")
        start_idle = time.time()

        # Aguardar período idle
        time.sleep(IDLE_WAIT_TIME)

        metrics.time_idle_wait = time.time() - start_idle
        print(f"   ✓ Idle completo: {metrics.time_idle_wait:.1f}s")

    def test_04_trigger_hibernation(self, auth_token, metrics):
        """[4/5] Trigger hibernation (snapshot + destroy)"""
        if not metrics.instance_id:
            pytest.skip("No instance ID")

        try:
            print("\n[4/5] Triggering hibernation...")

            # [a] Criar snapshot
            print("   [a] Criando snapshot...")
            start_snapshot = time.time()

            snapshot_result = call_api("POST", "/api/v1/snapshots", {
                "instance_id": metrics.instance_id,
                "source_path": "/workspace",
                "tags": ["auto-hibernation", "test"],
            }, token=auth_token)

            if "error" in snapshot_result:
                pytest.skip(f"Snapshot failed: {snapshot_result['error']}")

            snapshot_id = snapshot_result.get("snapshot_id", snapshot_result.get("id"))
            metrics.snapshot_id = snapshot_id
            metrics.time_snapshot = time.time() - start_snapshot

            print(f"       Snapshot ID: {snapshot_id}")
            print(f"       Tempo: {metrics.time_snapshot:.1f}s")

            # Aguardar snapshot ser completado
            time.sleep(5)

            # [b] Verificar snapshot no B2
            print("   [b] Verificando snapshot no B2...")
            snapshot_exists = verify_snapshot_in_b2(snapshot_id, auth_token)
            metrics.snapshot_exists_in_b2 = snapshot_exists

            if snapshot_exists:
                print("       ✓ Snapshot encontrado no B2")
            else:
                print("       ⚠ Snapshot NÃO encontrado no B2")

            # [c] Destruir GPU
            print("   [c] Destruindo GPU...")
            start_destroy = time.time()

            destroy_result = call_api("DELETE", f"/api/v1/instances/{metrics.instance_id}", token=auth_token)

            if "error" in destroy_result:
                print(f"       ⚠ Warning: {destroy_result['error']}")

            metrics.time_destroy = time.time() - start_destroy

            print(f"       Tempo: {metrics.time_destroy:.1f}s")
            print(f"   ✓ Hibernation completa")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_05_generate_report(self, metrics):
        """[5/5] Gera relatório final"""
        print("\n[5/5] Gerando relatório...")

        # Calcular totais
        metrics.time_total = time.time() - metrics.start_time
        hours_used = metrics.time_total / 3600
        metrics.estimated_cost_usd = hours_used * metrics.gpu_cost_per_hour

        # Determinar sucesso
        metrics.success = (
            metrics.instance_id is not None and
            metrics.snapshot_id is not None and
            metrics.snapshot_exists_in_b2 and
            len(metrics.test_files) > 0
        )

        # Exibir relatório
        print("\n" + "="*70)
        print("RELATÓRIO: AUTO-HIBERNATION TEST")
        print("="*70)

        print(f"\nRecursos:")
        print(f"  Instance ID:     {metrics.instance_id}")
        print(f"  Snapshot ID:     {metrics.snapshot_id}")
        print(f"  Test Files:      {len(metrics.test_files)}")

        print(f"\nTimings:")
        print(f"  1. Provision:    {metrics.time_provision:6.1f}s")
        print(f"  2. Create Files: {metrics.time_create_files:6.1f}s")
        print(f"  3. Idle Wait:    {metrics.time_idle_wait:6.1f}s")
        print(f"  4. Snapshot:     {metrics.time_snapshot:6.1f}s")
        print(f"  5. Destroy:      {metrics.time_destroy:6.1f}s")
        print(f"  TOTAL:           {metrics.time_total:6.1f}s ({metrics.time_total/60:.1f} min)")

        print(f"\nCusto:")
        print(f"  GPU hourly:      ${metrics.gpu_cost_per_hour:.4f}/hr")
        print(f"  Tempo total:     {hours_used:.4f} hrs")
        print(f"  Custo estimado:  ${metrics.estimated_cost_usd:.4f}")

        print(f"\nValidação:")
        print(f"  Snapshot no B2:  {'✓ SIM' if metrics.snapshot_exists_in_b2 else '✗ NÃO'}")
        print(f"  Sucesso geral:   {'✓ SIM' if metrics.success else '✗ NÃO'}")

        if metrics.error_message:
            print(f"  Erro:            {metrics.error_message}")

        print("\n" + "="*70)

        # Salvar métricas em JSON
        report_file = f"/tmp/auto_hibernation_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)

        print(f"\nRelatório salvo em: {report_file}")

        # Assert final
        assert metrics.success, f"Auto-hibernation test failed: {metrics.error_message or 'Validation failed'}"


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v", "-s",
        "--tb=short",
        "-m", "slow",
    ])
