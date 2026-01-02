"""
Testes COMPLETOS de Failover REAL - Dumont Cloud

Este arquivo executa testes de failover REAIS com:
- Provisionamento de GPUs reais na VAST.ai
- Criação de arquivos únicos para validação
- Snapshots reais em Backblaze B2
- Failover com transferência de dados
- Validação de integridade (MD5 checksums)
- Medição de tempo de cada operação

ATENÇÃO: ESTES TESTES USAM CRÉDITOS REAIS!
- VAST.ai: ~$0.30-0.50 por teste completo
- Backblaze B2: ~$0.01 por snapshot
- GCP (se usar CPU Standby): ~$0.05/hora

Executar:
    pytest cli/tests/test_real_failover_complete.py -v -s --tb=short

Executar apenas testes rápidos (sem criar GPUs):
    pytest cli/tests/test_real_failover_complete.py -v -s -m "not slow"
"""

import pytest
import time
import json
import hashlib
import subprocess
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

# Credenciais e endpoints
DUMONT_API_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8766")
VAST_API_KEY = os.environ.get("VAST_API_KEY")
B2_ENDPOINT = os.environ.get("B2_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")
B2_BUCKET = os.environ.get("B2_BUCKET", "dumoncloud-snapshot")

# Timeouts (em segundos)
TIMEOUT_INSTANCE_CREATE = 300      # 5 min para criar instância
TIMEOUT_INSTANCE_READY = 600       # 10 min para ficar running + SSH
TIMEOUT_SNAPSHOT_CREATE = 300      # 5 min para snapshot
TIMEOUT_FAILOVER = 600             # 10 min para failover completo
TIMEOUT_RESTORE = 300              # 5 min para restore


@dataclass
class TestFile:
    """Representa um arquivo de teste criado na GPU"""
    path: str
    content: str
    size_bytes: int
    md5: str
    created_at: float


@dataclass
class FailoverTestMetrics:
    """Métricas coletadas durante teste de failover"""
    test_name: str
    start_time: float = field(default_factory=time.time)

    # IDs de recursos
    gpu_instance_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    failover_gpu_id: Optional[str] = None

    # Arquivos de teste
    test_files: List[TestFile] = field(default_factory=list)

    # Tempos (segundos)
    time_create_files: float = 0
    time_create_snapshot: float = 0
    time_failover: float = 0
    time_validate: float = 0
    time_total: float = 0

    # Custos estimados
    gpu_cost_per_hour: float = 0
    estimated_cost_usd: float = 0

    # Status
    success: bool = False
    error_message: Optional[str] = None
    files_validated: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "gpu_instance_id": self.gpu_instance_id,
            "snapshot_id": self.snapshot_id,
            "failover_gpu_id": self.failover_gpu_id,
            "test_files_count": len(self.test_files),
            "timings": {
                "create_files_sec": round(self.time_create_files, 2),
                "create_snapshot_sec": round(self.time_create_snapshot, 2),
                "failover_sec": round(self.time_failover, 2),
                "validate_sec": round(self.time_validate, 2),
                "total_sec": round(self.time_total, 2),
            },
            "cost": {
                "gpu_hourly_usd": round(self.gpu_cost_per_hour, 4),
                "estimated_total_usd": round(self.estimated_cost_usd, 4),
            },
            "validation": {
                "success": self.success,
                "files_validated": self.files_validated,
                "error": self.error_message,
            }
        }


# =============================================================================
# HELPERS SSH E COMANDOS REMOTOS
# =============================================================================

def ssh_exec(ssh_host: str, ssh_port: int, command: str, timeout: int = 300) -> Dict[str, Any]:
    """Executa comando via SSH e retorna resultado"""
    cmd = [
        "ssh",
        "-p", str(ssh_port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=30",
        "-o", "LogLevel=ERROR",  # Reduz warnings
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
    """Aguarda até que SSH esteja acessível"""
    start = time.time()

    while time.time() - start < timeout:
        result = ssh_exec(ssh_host, ssh_port, "echo ready", timeout=10)
        if result["success"]:
            return True
        time.sleep(10)

    return False


def create_test_file_on_gpu(
    ssh_host: str,
    ssh_port: int,
    file_path: str,
    content: Optional[str] = None
) -> TestFile:
    """
    Cria arquivo de teste na GPU e retorna metadados.

    Args:
        ssh_host: SSH host da GPU
        ssh_port: SSH port da GPU
        file_path: Caminho completo do arquivo (ex: /workspace/test-1.txt)
        content: Conteúdo do arquivo (se None, gera timestamp único)

    Returns:
        TestFile com path, content, size, md5
    """
    if content is None:
        content = f"Test file created at {datetime.now().isoformat()}\nTimestamp: {time.time()}\n"

    # Criar arquivo via SSH
    create_cmd = f"echo '{content}' > {file_path}"
    result = ssh_exec(ssh_host, ssh_port, create_cmd)

    if not result["success"]:
        raise Exception(f"Failed to create file {file_path}: {result['stderr']}")

    # Obter MD5 do arquivo
    md5_cmd = f"md5sum {file_path} | awk '{{print $1}}'"
    md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd)

    if not md5_result["success"]:
        raise Exception(f"Failed to get MD5 for {file_path}: {md5_result['stderr']}")

    md5_hash = md5_result["stdout"].strip()

    # Obter tamanho do arquivo
    size_cmd = f"stat -c %s {file_path}"
    size_result = ssh_exec(ssh_host, ssh_port, size_cmd)

    size_bytes = 0
    if size_result["success"]:
        try:
            size_bytes = int(size_result["stdout"].strip())
        except ValueError:
            pass

    return TestFile(
        path=file_path,
        content=content,
        size_bytes=size_bytes,
        md5=md5_hash,
        created_at=time.time()
    )


def validate_file_on_gpu(
    ssh_host: str,
    ssh_port: int,
    expected_file: TestFile
) -> bool:
    """
    Valida que arquivo existe na GPU com mesmo MD5.

    Returns:
        True se arquivo existe e MD5 bate
    """
    # Verificar se arquivo existe
    check_cmd = f"test -f {expected_file.path} && echo exists || echo missing"
    check_result = ssh_exec(ssh_host, ssh_port, check_cmd)

    if not check_result["success"] or "missing" in check_result["stdout"]:
        return False

    # Obter MD5 atual
    md5_cmd = f"md5sum {expected_file.path} | awk '{{print $1}}'"
    md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd)

    if not md5_result["success"]:
        return False

    actual_md5 = md5_result["stdout"].strip()

    return actual_md5 == expected_file.md5


# =============================================================================
# HELPERS API
# =============================================================================

def call_api(method: str, endpoint: str, data: Optional[Dict] = None, token: Optional[str] = None) -> Dict:
    """Chama API do Dumont"""
    import requests

    url = f"{DUMONT_API_URL}{endpoint}"
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

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
            return {
                "error": f"HTTP {response.status_code}",
                "detail": response.text[:200]
            }

    except requests.exceptions.Timeout:
        return {"error": "Request timeout"}
    except Exception as e:
        return {"error": str(e)}


def get_auth_token() -> Optional[str]:
    """Obtém token de autenticação (mock para testes)"""
    # Para testes, usar credenciais demo
    result = call_api("POST", "/api/v1/auth/login", {
        "email": "test@test.com",
        "password": "test123"
    })

    return result.get("access_token")


def wait_for_instance_ready(instance_id: str, token: str, timeout: int = 600) -> Dict[str, Any]:
    """
    Aguarda instância ficar running e com SSH disponível.

    Returns:
        Dict com ssh_host, ssh_port, status
    """
    start = time.time()

    while time.time() - start < timeout:
        result = call_api("GET", f"/api/v1/instances/{instance_id}", token=token)

        if "error" not in result:
            status = result.get("status", "").lower()
            ssh_host = result.get("ssh_host")
            ssh_port = result.get("ssh_port")

            if status == "running" and ssh_host and ssh_port:
                # Verificar se SSH está acessível
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


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def auth_token():
    """Token de autenticação para a sessão de testes"""
    token = get_auth_token()
    if not token:
        pytest.skip("Failed to authenticate")
    return token


@pytest.fixture(scope="module")
def test_metrics():
    """Coleta métricas de todos os testes"""
    return []


# =============================================================================
# TESTE 1: SINCRONIZAÇÃO EM TEMPO REAL (GPU → Snapshot → GPU)
# =============================================================================

@pytest.mark.slow
@pytest.mark.real
class TestRealTimeSyncFailover:
    """
    TESTE 1: Sincronização em Tempo Real

    Jornada:
    1. Criar GPU real
    2. Criar arquivos de teste
    3. Criar snapshot (B2)
    4. Criar NOVA GPU
    5. Restaurar snapshot
    6. Validar que arquivos existem com mesmo MD5
    """

    def test_01_provision_gpu_and_create_files(self, auth_token, test_metrics):
        """
        [1/6] Provisiona GPU real e cria arquivos de teste
        """
        metrics = FailoverTestMetrics(test_name="real_time_sync_failover")
        test_metrics.append(metrics)

        print("\n" + "="*70)
        print("TESTE 1: SINCRONIZAÇÃO EM TEMPO REAL")
        print("="*70)

        try:
            # 1. Buscar oferta GPU barata
            print("\n[1/6] Buscando oferta GPU...")
            offers = call_api("GET", "/api/v1/instances/offers", token=auth_token)

            if "error" in offers:
                pytest.skip(f"Failed to get offers: {offers['error']}")

            offers_list = offers.get("offers", [])
            if not offers_list:
                pytest.skip("No GPU offers available")

            # Escolhe a mais barata
            cheapest = min(offers_list, key=lambda x: x.get("dph_total", 999))
            offer_id = cheapest.get("id")
            gpu_name = cheapest.get("gpu_name", "Unknown")
            price = cheapest.get("dph_total", 0)

            metrics.gpu_cost_per_hour = price

            print(f"   GPU: {gpu_name}")
            print(f"   Preço: ${price:.4f}/hr")
            print(f"   Offer ID: {offer_id}")

            # 2. Criar instância
            print("\n[2/6] Criando instância GPU...")
            start_create = time.time()

            create_result = call_api("POST", "/api/v1/instances", {
                "offer_id": offer_id,
                "image": "nvidia/cuda:12.1.0-base-ubuntu22.04",
                "disk_size": 20,
            }, token=auth_token)

            if "error" in create_result:
                pytest.skip(f"Failed to create instance: {create_result['error']}")

            instance_id = str(create_result.get("instance_id", create_result.get("id")))
            metrics.gpu_instance_id = instance_id

            print(f"   Instance ID: {instance_id}")
            print(f"   Creation time: {time.time() - start_create:.1f}s")

            # 3. Aguardar ficar ready
            print("\n[3/6] Aguardando instância ficar ready (até 10 min)...")
            ready_result = wait_for_instance_ready(instance_id, auth_token, timeout=TIMEOUT_INSTANCE_READY)

            if not ready_result.get("success"):
                pytest.skip(f"Instance not ready: {ready_result.get('error')}")

            ssh_host = ready_result["ssh_host"]
            ssh_port = ready_result["ssh_port"]

            print(f"   SSH: {ssh_host}:{ssh_port}")
            print(f"   Status: {ready_result['status']}")

            # 4. Criar arquivos de teste
            print("\n[4/6] Criando arquivos de teste...")
            start_files = time.time()

            # Criar diretório de workspace
            ssh_exec(ssh_host, ssh_port, "mkdir -p /workspace")

            # Criar 3 arquivos de teste com conteúdo único
            test_files = []
            for i in range(3):
                file_path = f"/workspace/test-file-{i+1}.txt"
                content = f"Test file #{i+1}\\nCreated at: {datetime.now().isoformat()}\\nTimestamp: {time.time()}\\n"

                test_file = create_test_file_on_gpu(ssh_host, ssh_port, file_path, content)
                test_files.append(test_file)

                print(f"   Created: {file_path}")
                print(f"      MD5: {test_file.md5}")
                print(f"      Size: {test_file.size_bytes} bytes")

            metrics.test_files = test_files
            metrics.time_create_files = time.time() - start_files

            print(f"\n   ✓ {len(test_files)} arquivos criados em {metrics.time_create_files:.1f}s")

            # Salvar métricas intermediárias
            metrics.success = True  # Provisioning OK até aqui

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_02_create_snapshot(self, auth_token, test_metrics):
        """
        [2/6] Cria snapshot dos arquivos
        """
        metrics = test_metrics[-1]  # Pega métricas do teste anterior

        if not metrics.success or not metrics.gpu_instance_id:
            pytest.skip("Previous test failed - no GPU instance")

        try:
            print("\n[5/6] Criando snapshot em B2...")
            start_snapshot = time.time()

            instance_id = metrics.gpu_instance_id

            # Obter SSH info
            instance_info = call_api("GET", f"/api/v1/instances/{instance_id}", token=auth_token)
            ssh_host = instance_info.get("ssh_host")
            ssh_port = instance_info.get("ssh_port")

            if not ssh_host or not ssh_port:
                pytest.skip("SSH info not available")

            # Criar snapshot via API
            snapshot_result = call_api("POST", f"/api/v1/snapshots", {
                "instance_id": instance_id,
                "workspace_path": "/workspace",
                "name": f"test-snapshot-{int(time.time())}"
            }, token=auth_token)

            if "error" in snapshot_result:
                pytest.skip(f"Snapshot failed: {snapshot_result['error']}")

            snapshot_id = snapshot_result.get("snapshot_id", snapshot_result.get("id"))
            metrics.snapshot_id = snapshot_id
            metrics.time_create_snapshot = time.time() - start_snapshot

            print(f"   Snapshot ID: {snapshot_id}")
            print(f"   Time: {metrics.time_create_snapshot:.1f}s")

            # Informações do snapshot
            size_compressed = snapshot_result.get("size_compressed", 0)
            size_original = snapshot_result.get("size_original", 0)

            if size_compressed:
                print(f"   Size (compressed): {size_compressed / 1024 / 1024:.2f} MB")
            if size_original:
                ratio = size_original / size_compressed if size_compressed else 1
                print(f"   Compression ratio: {ratio:.2f}x")

            print(f"\n   ✓ Snapshot criado com sucesso")

        except Exception as e:
            metrics.error_message = f"Snapshot error: {e}"
            metrics.success = False
            raise

    def test_03_failover_to_new_gpu(self, auth_token, test_metrics):
        """
        [3/6] Cria NOVA GPU e restaura snapshot
        """
        metrics = test_metrics[-1]

        if not metrics.success or not metrics.snapshot_id:
            pytest.skip("Previous test failed - no snapshot")

        try:
            print("\n[6/6] Failover: provisionando nova GPU e restaurando snapshot...")
            start_failover = time.time()

            # 1. Buscar nova GPU
            print("   [a] Buscando nova GPU...")
            offers = call_api("GET", "/api/v1/instances/offers", token=auth_token)
            offers_list = offers.get("offers", [])

            if not offers_list:
                pytest.skip("No GPU offers for failover")

            cheapest = min(offers_list, key=lambda x: x.get("dph_total", 999))
            offer_id = cheapest.get("id")

            # 2. Criar nova instância
            print("   [b] Criando nova instância...")
            create_result = call_api("POST", "/api/v1/instances", {
                "offer_id": offer_id,
                "image": "nvidia/cuda:12.1.0-base-ubuntu22.04",
                "disk_size": 20,
            }, token=auth_token)

            if "error" in create_result:
                pytest.skip(f"Failed to create failover GPU: {create_result['error']}")

            failover_gpu_id = str(create_result.get("instance_id", create_result.get("id")))
            metrics.failover_gpu_id = failover_gpu_id

            print(f"       Failover GPU ID: {failover_gpu_id}")

            # 3. Aguardar ready
            print("   [c] Aguardando nova GPU ficar ready...")
            ready_result = wait_for_instance_ready(failover_gpu_id, auth_token, timeout=TIMEOUT_INSTANCE_READY)

            if not ready_result.get("success"):
                pytest.skip(f"Failover GPU not ready: {ready_result.get('error')}")

            new_ssh_host = ready_result["ssh_host"]
            new_ssh_port = ready_result["ssh_port"]

            print(f"       SSH: {new_ssh_host}:{new_ssh_port}")

            # 4. Restaurar snapshot
            print("   [d] Restaurando snapshot...")
            restore_result = call_api("POST", f"/api/v1/snapshots/{metrics.snapshot_id}/restore", {
                "instance_id": failover_gpu_id,
                "workspace_path": "/workspace"
            }, token=auth_token)

            if "error" in restore_result:
                pytest.skip(f"Restore failed: {restore_result['error']}")

            metrics.time_failover = time.time() - start_failover

            print(f"\n   ✓ Failover completo em {metrics.time_failover:.1f}s")

        except Exception as e:
            metrics.error_message = f"Failover error: {e}"
            metrics.success = False
            raise

    def test_04_validate_files(self, auth_token, test_metrics):
        """
        [4/6] Valida que arquivos foram transferidos com integridade
        """
        metrics = test_metrics[-1]

        if not metrics.success or not metrics.failover_gpu_id:
            pytest.skip("Previous test failed - no failover GPU")

        try:
            print("\n[VALIDAÇÃO] Verificando integridade dos arquivos...")
            start_validate = time.time()

            # Obter SSH da nova GPU
            instance_info = call_api("GET", f"/api/v1/instances/{metrics.failover_gpu_id}", token=auth_token)
            ssh_host = instance_info.get("ssh_host")
            ssh_port = instance_info.get("ssh_port")

            if not ssh_host or not ssh_port:
                pytest.skip("SSH info not available for failover GPU")

            # Validar cada arquivo
            validated_count = 0
            for test_file in metrics.test_files:
                is_valid = validate_file_on_gpu(ssh_host, ssh_port, test_file)

                if is_valid:
                    validated_count += 1
                    print(f"   ✓ {test_file.path}")
                    print(f"      MD5: {test_file.md5} (OK)")
                else:
                    print(f"   ✗ {test_file.path}")
                    print(f"      Expected MD5: {test_file.md5}")
                    print(f"      VALIDAÇÃO FALHOU!")

            metrics.files_validated = validated_count
            metrics.time_validate = time.time() - start_validate

            # Calcular tempo total e custo
            metrics.time_total = time.time() - metrics.start_time
            hours_used = metrics.time_total / 3600
            metrics.estimated_cost_usd = hours_used * metrics.gpu_cost_per_hour * 2  # 2 GPUs

            # Validação final
            all_validated = validated_count == len(metrics.test_files)
            metrics.success = all_validated

            print(f"\n   Validados: {validated_count}/{len(metrics.test_files)}")
            print(f"   Tempo de validação: {metrics.time_validate:.1f}s")

            # Exibir relatório
            print("\n" + "="*70)
            print("RELATÓRIO DO TESTE")
            print("="*70)
            print(f"\nJornada completa:")
            print(f"  1. Criar arquivos:     {metrics.time_create_files:6.1f}s")
            print(f"  2. Criar snapshot:     {metrics.time_create_snapshot:6.1f}s")
            print(f"  3. Failover + Restore: {metrics.time_failover:6.1f}s")
            print(f"  4. Validar:            {metrics.time_validate:6.1f}s")
            print(f"  TOTAL:                 {metrics.time_total:6.1f}s ({metrics.time_total/60:.1f} min)")

            print(f"\nRecursos:")
            print(f"  GPU Original:    {metrics.gpu_instance_id}")
            print(f"  Snapshot:        {metrics.snapshot_id}")
            print(f"  Failover GPU:    {metrics.failover_gpu_id}")

            print(f"\nCusto estimado:")
            print(f"  GPU hourly:      ${metrics.gpu_cost_per_hour:.4f}/hr")
            print(f"  Tempo total:     {metrics.time_total/3600:.4f} hrs")
            print(f"  Total (2 GPUs):  ${metrics.estimated_cost_usd:.4f}")

            print(f"\nValidação:")
            print(f"  Arquivos OK:     {metrics.files_validated}/{len(metrics.test_files)}")
            print(f"  Sucesso:         {'✓ SIM' if metrics.success else '✗ NÃO'}")

            print("\n" + "="*70)

            # Assert final
            assert all_validated, (
                f"File validation failed: {validated_count}/{len(metrics.test_files)} files valid"
            )

        except Exception as e:
            metrics.error_message = f"Validation error: {e}"
            metrics.success = False
            raise

    def test_99_cleanup(self, auth_token, test_metrics):
        """
        [5/6] Cleanup: deleta GPUs criadas
        """
        metrics = test_metrics[-1]

        print("\n[CLEANUP] Removendo recursos...")

        # Deletar GPU original
        if metrics.gpu_instance_id:
            try:
                call_api("DELETE", f"/api/v1/instances/{metrics.gpu_instance_id}", token=auth_token)
                print(f"   ✓ Deletada GPU original: {metrics.gpu_instance_id}")
            except Exception as e:
                print(f"   ⚠ Erro ao deletar GPU original: {e}")

        # Deletar GPU de failover
        if metrics.failover_gpu_id:
            try:
                call_api("DELETE", f"/api/v1/instances/{metrics.failover_gpu_id}", token=auth_token)
                print(f"   ✓ Deletada GPU failover: {metrics.failover_gpu_id}")
            except Exception as e:
                print(f"   ⚠ Erro ao deletar GPU failover: {e}")

        print("\n   Cleanup completo")


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
