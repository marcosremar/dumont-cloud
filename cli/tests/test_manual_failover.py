"""
TEST 2.1: Manual Failover (GPU → Snapshot → GPU)

Jornada REAL completa de failover manual:
1. Provisionar GPU 1 (Source)
2. Criar dataset de teste (100 arquivos com dados variados)
3. Calcular MD5 de todos os arquivos
4. Criar snapshot e upload para B2
5. Destruir GPU 1
6. Provisionar GPU 2 (Target)
7. Download snapshot do B2
8. Restaurar arquivos na GPU 2
9. Verificar MD5s (devem ser idênticos)
10. Destruir GPU 2

ATENÇÃO: Este teste usa CRÉDITOS REAIS!
- VAST.ai: ~$0.40-0.80 por teste completo (2 GPUs)
- Backblaze B2: ~$0.01 por snapshot

Executar:
    pytest cli/tests/test_manual_failover.py -v -s --tb=short

Executar apenas dry-run (sem criar GPUs):
    pytest cli/tests/test_manual_failover.py -v -s -m "not slow"
"""

import pytest
import time
import json
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from cli.utils.api_client import APIClient


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

# Credenciais e endpoints
DUMONT_API_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8766")
VAST_API_KEY = os.environ.get("VAST_API_KEY")
B2_ENDPOINT = os.environ.get("B2_ENDPOINT", "https://s3.us-west-000.backblazeb2.com")
B2_BUCKET = os.environ.get("B2_BUCKET", "dumontcloud-snapshots")
B2_KEY_ID = os.environ.get("B2_KEY_ID")
B2_APP_KEY = os.environ.get("B2_APPLICATION_KEY")

# Timeouts (em segundos)
TIMEOUT_INSTANCE_CREATE = 300      # 5 min para criar instância
TIMEOUT_INSTANCE_READY = 600       # 10 min para ficar running + SSH
TIMEOUT_SNAPSHOT_CREATE = 600      # 10 min para snapshot
TIMEOUT_FAILOVER = 1200            # 20 min para failover completo
TIMEOUT_RESTORE = 600              # 10 min para restore

# Configuração do teste
TEST_FILES_COUNT = 100             # Número de arquivos de teste
TEST_FILES_DIR = "/workspace/test_data"  # Diretório na GPU


@dataclass
class TestFile:
    """Representa um arquivo de teste"""
    path: str
    content: str
    size_bytes: int
    md5: str
    created_at: float


@dataclass
class FailoverMetrics:
    """Métricas do teste de failover"""
    test_name: str = "manual_failover_gpu_to_gpu"
    start_time: float = field(default_factory=time.time)

    # IDs de recursos
    source_gpu_id: Optional[str] = None
    target_gpu_id: Optional[str] = None
    snapshot_id: Optional[str] = None

    # Arquivos de teste
    test_files: List[TestFile] = field(default_factory=list)

    # Tempos (segundos)
    time_provision_source: float = 0
    time_create_files: float = 0
    time_create_snapshot: float = 0
    time_destroy_source: float = 0
    time_provision_target: float = 0
    time_restore_snapshot: float = 0
    time_validate: float = 0
    time_total: float = 0

    # Custos
    source_gpu_cost_per_hour: float = 0
    target_gpu_cost_per_hour: float = 0
    estimated_cost_usd: float = 0

    # Status
    success: bool = False
    files_validated: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte métricas para dicionário"""
        return {
            "test_name": self.test_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "resources": {
                "source_gpu_id": self.source_gpu_id,
                "target_gpu_id": self.target_gpu_id,
                "snapshot_id": self.snapshot_id,
            },
            "test_files_count": len(self.test_files),
            "timings": {
                "provision_source_sec": round(self.time_provision_source, 2),
                "create_files_sec": round(self.time_create_files, 2),
                "create_snapshot_sec": round(self.time_create_snapshot, 2),
                "destroy_source_sec": round(self.time_destroy_source, 2),
                "provision_target_sec": round(self.time_provision_target, 2),
                "restore_snapshot_sec": round(self.time_restore_snapshot, 2),
                "validate_sec": round(self.time_validate, 2),
                "total_sec": round(self.time_total, 2),
                "total_min": round(self.time_total / 60, 2),
            },
            "cost": {
                "source_gpu_hourly_usd": round(self.source_gpu_cost_per_hour, 4),
                "target_gpu_hourly_usd": round(self.target_gpu_cost_per_hour, 4),
                "estimated_total_usd": round(self.estimated_cost_usd, 4),
            },
            "validation": {
                "success": self.success,
                "files_validated": self.files_validated,
                "files_total": len(self.test_files),
                "error": self.error_message,
            }
        }

    def save_report(self, file_path: str = "manual_failover_report.json"):
        """Salva relatório em JSON"""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"\n📊 Relatório salvo em: {file_path}")

    def print_summary(self):
        """Imprime resumo formatado"""
        print("\n" + "=" * 80)
        print("RELATÓRIO: MANUAL FAILOVER (GPU → SNAPSHOT → GPU)")
        print("=" * 80)

        print("\n🕐 TIMELINE:")
        print(f"  1. Provisionar Source GPU:    {self.time_provision_source:8.1f}s")
        print(f"  2. Criar {len(self.test_files):3d} arquivos:     {self.time_create_files:8.1f}s")
        print(f"  3. Criar snapshot (B2):       {self.time_create_snapshot:8.1f}s")
        print(f"  4. Destruir Source GPU:       {self.time_destroy_source:8.1f}s")
        print(f"  5. Provisionar Target GPU:    {self.time_provision_target:8.1f}s")
        print(f"  6. Restaurar snapshot:        {self.time_restore_snapshot:8.1f}s")
        print(f"  7. Validar arquivos:          {self.time_validate:8.1f}s")
        print(f"  {'─' * 50}")
        print(f"  TOTAL:                        {self.time_total:8.1f}s ({self.time_total/60:.1f} min)")

        print("\n💰 CUSTOS:")
        print(f"  Source GPU: ${self.source_gpu_cost_per_hour:.4f}/hr")
        print(f"  Target GPU: ${self.target_gpu_cost_per_hour:.4f}/hr")
        print(f"  Tempo total: {self.time_total/3600:.4f} hrs")
        print(f"  Total estimado: ${self.estimated_cost_usd:.4f}")

        print("\n🔍 VALIDAÇÃO:")
        print(f"  Arquivos criados: {len(self.test_files)}")
        print(f"  Arquivos validados: {self.files_validated}")
        print(f"  Taxa de sucesso: {self.files_validated / len(self.test_files) * 100:.1f}%")
        print(f"  Status: {'✅ SUCESSO' if self.success else '❌ FALHA'}")

        if self.error_message:
            print(f"\n⚠️  Erro: {self.error_message}")

        print("\n" + "=" * 80)


# =============================================================================
# HELPERS SSH
# =============================================================================

def ssh_exec(ssh_host: str, ssh_port: int, command: str, timeout: int = 300) -> Dict[str, Any]:
    """Executa comando via SSH e retorna resultado"""
    import subprocess

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
    """Aguarda até que SSH esteja acessível"""
    start = time.time()

    while time.time() - start < timeout:
        result = ssh_exec(ssh_host, ssh_port, "echo ready", timeout=10)
        if result["success"]:
            return True
        time.sleep(10)

    return False


# =============================================================================
# HELPERS API
# =============================================================================

def wait_for_instance_ready(api: APIClient, instance_id: str, timeout: int = 600) -> Dict[str, Any]:
    """
    Aguarda instância ficar running e com SSH disponível.

    Returns:
        Dict com ssh_host, ssh_port, status
    """
    start = time.time()

    while time.time() - start < timeout:
        result = api.call("GET", f"/api/v1/instances/{instance_id}", silent=True)

        if result:
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


def create_test_files_on_gpu(
    ssh_host: str,
    ssh_port: int,
    num_files: int = 100
) -> List[TestFile]:
    """
    Cria múltiplos arquivos de teste na GPU.

    Args:
        ssh_host: SSH host da GPU
        ssh_port: SSH port da GPU
        num_files: Número de arquivos para criar

    Returns:
        Lista de TestFile com metadados
    """
    print(f"\n📁 Criando {num_files} arquivos de teste...")

    # Criar diretório
    ssh_exec(ssh_host, ssh_port, f"mkdir -p {TEST_FILES_DIR}")

    test_files = []

    for i in range(num_files):
        file_path = f"{TEST_FILES_DIR}/file-{i+1:03d}.txt"

        # Gerar conteúdo variado
        content = f"""Test File #{i+1}
Created: {datetime.now().isoformat()}
Timestamp: {time.time()}
Index: {i}
Random data: {os.urandom(16).hex()}
{'=' * 60}
"""

        # Criar arquivo
        create_cmd = f"cat > {file_path} << 'EOF'\n{content}\nEOF"
        result = ssh_exec(ssh_host, ssh_port, create_cmd)

        if not result["success"]:
            print(f"⚠️  Falha ao criar {file_path}: {result['stderr']}")
            continue

        # Obter MD5
        md5_cmd = f"md5sum {file_path} | awk '{{print $1}}'"
        md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd)

        if not md5_result["success"]:
            print(f"⚠️  Falha ao calcular MD5 de {file_path}")
            continue

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

        test_file = TestFile(
            path=file_path,
            content=content,
            size_bytes=size_bytes,
            md5=md5_hash,
            created_at=time.time()
        )

        test_files.append(test_file)

        # Print progress
        if (i + 1) % 20 == 0:
            print(f"   Progresso: {i+1}/{num_files} arquivos criados...")

    print(f"✅ {len(test_files)} arquivos criados com sucesso!")

    return test_files


def validate_files_on_gpu(
    ssh_host: str,
    ssh_port: int,
    expected_files: List[TestFile]
) -> int:
    """
    Valida que arquivos existem na GPU com MD5s corretos.

    Returns:
        Número de arquivos validados com sucesso
    """
    print(f"\n🔍 Validando {len(expected_files)} arquivos...")

    validated_count = 0

    for i, test_file in enumerate(expected_files):
        # Verificar se arquivo existe
        check_cmd = f"test -f {test_file.path} && echo exists || echo missing"
        check_result = ssh_exec(ssh_host, ssh_port, check_cmd)

        if not check_result["success"] or "missing" in check_result["stdout"]:
            print(f"❌ Arquivo ausente: {test_file.path}")
            continue

        # Obter MD5 atual
        md5_cmd = f"md5sum {test_file.path} | awk '{{print $1}}'"
        md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd)

        if not md5_result["success"]:
            print(f"❌ Erro ao obter MD5: {test_file.path}")
            continue

        actual_md5 = md5_result["stdout"].strip()

        if actual_md5 == test_file.md5:
            validated_count += 1
            # Print progress a cada 20 arquivos
            if (i + 1) % 20 == 0:
                print(f"   Progresso: {i+1}/{len(expected_files)} validados...")
        else:
            print(f"❌ MD5 mismatch: {test_file.path}")
            print(f"   Esperado: {test_file.md5}")
            print(f"   Obtido:   {actual_md5}")

    print(f"✅ {validated_count}/{len(expected_files)} arquivos validados!")

    return validated_count


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def api_client():
    """Cliente API autenticado"""
    api = APIClient(base_url=DUMONT_API_URL)

    # Login
    login_result = api.call("POST", "/api/v1/auth/login", {
        "email": "test@test.com",
        "password": "test123"
    }, silent=True)

    if not login_result or "access_token" not in login_result:
        pytest.skip("Failed to authenticate")

    return api


@pytest.fixture(scope="module")
def metrics():
    """Métricas do teste"""
    return FailoverMetrics()


# =============================================================================
# TESTE MANUAL FAILOVER
# =============================================================================

@pytest.mark.slow
@pytest.mark.real
class TestManualFailover:
    """
    TEST 2.1: Manual Failover (GPU → Snapshot → GPU)

    Jornada completa:
    1. Provisionar Source GPU
    2. Criar 100 arquivos de teste
    3. Criar snapshot em B2
    4. Destruir Source GPU
    5. Provisionar Target GPU
    6. Restaurar snapshot
    7. Validar todos os arquivos (MD5)
    """

    def test_01_provision_source_gpu(self, api_client, metrics):
        """[1/7] Provisiona Source GPU"""
        print("\n" + "=" * 80)
        print("TEST 2.1: MANUAL FAILOVER (GPU → SNAPSHOT → GPU)")
        print("=" * 80)

        print("\n[1/7] Provisionando Source GPU...")
        start = time.time()

        try:
            # Buscar oferta GPU barata
            offers = api_client.call("GET", "/api/v1/instances/offers", silent=True)

            if not offers or "offers" not in offers:
                pytest.skip("No GPU offers available")

            offers_list = offers.get("offers", [])
            if not offers_list:
                pytest.skip("Empty offers list")

            # Escolhe a mais barata
            cheapest = min(offers_list, key=lambda x: x.get("dph_total", 999))
            offer_id = cheapest.get("id")
            gpu_name = cheapest.get("gpu_name", "Unknown")
            price = cheapest.get("dph_total", 0)

            metrics.source_gpu_cost_per_hour = price

            print(f"   GPU: {gpu_name}")
            print(f"   Preço: ${price:.4f}/hr")

            # Criar instância
            create_result = api_client.call("POST", "/api/v1/instances", {
                "offer_id": offer_id,
                "image": "nvidia/cuda:12.1.0-base-ubuntu22.04",
                "disk_size": 20,
            }, silent=True)

            if not create_result:
                pytest.skip("Failed to create instance")

            instance_id = str(create_result.get("instance_id", create_result.get("id")))
            metrics.source_gpu_id = instance_id

            print(f"   Instance ID: {instance_id}")

            # Aguardar ficar ready
            print("   Aguardando SSH ready...")
            ready_result = wait_for_instance_ready(api_client, instance_id, timeout=TIMEOUT_INSTANCE_READY)

            if not ready_result.get("success"):
                pytest.skip(f"Instance not ready: {ready_result.get('error')}")

            metrics.time_provision_source = time.time() - start

            print(f"   SSH: {ready_result['ssh_host']}:{ready_result['ssh_port']}")
            print(f"✅ Source GPU pronta em {metrics.time_provision_source:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_02_create_test_files(self, api_client, metrics):
        """[2/7] Cria arquivos de teste na Source GPU"""
        if not metrics.source_gpu_id:
            pytest.skip("No source GPU")

        print(f"\n[2/7] Criando {TEST_FILES_COUNT} arquivos de teste...")
        start = time.time()

        try:
            # Obter SSH info
            instance_info = api_client.call("GET", f"/api/v1/instances/{metrics.source_gpu_id}", silent=True)
            ssh_host = instance_info.get("ssh_host")
            ssh_port = instance_info.get("ssh_port")

            if not ssh_host or not ssh_port:
                pytest.skip("SSH info not available")

            # Criar arquivos
            test_files = create_test_files_on_gpu(ssh_host, ssh_port, num_files=TEST_FILES_COUNT)
            metrics.test_files = test_files
            metrics.time_create_files = time.time() - start

            print(f"✅ {len(test_files)} arquivos criados em {metrics.time_create_files:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_03_create_snapshot(self, api_client, metrics):
        """[3/7] Cria snapshot em B2"""
        if not metrics.source_gpu_id or not metrics.test_files:
            pytest.skip("No source GPU or test files")

        print(f"\n[3/7] Criando snapshot em B2...")
        start = time.time()

        try:
            # Criar snapshot via API
            snapshot_result = api_client.call("POST", "/api/v1/snapshots", {
                "instance_id": metrics.source_gpu_id,
                "source_path": TEST_FILES_DIR,
                "tags": [f"test-manual-failover-{int(time.time())}"]
            }, silent=True)

            if not snapshot_result:
                pytest.skip("Failed to create snapshot")

            snapshot_id = snapshot_result.get("snapshot_id", snapshot_result.get("id"))
            metrics.snapshot_id = snapshot_id
            metrics.time_create_snapshot = time.time() - start

            print(f"   Snapshot ID: {snapshot_id}")

            # Info do snapshot
            if "data_added" in snapshot_result:
                size_mb = snapshot_result["data_added"] / 1024 / 1024
                print(f"   Tamanho: {size_mb:.2f} MB")

            print(f"✅ Snapshot criado em {metrics.time_create_snapshot:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_04_destroy_source_gpu(self, api_client, metrics):
        """[4/7] Destrói Source GPU"""
        if not metrics.source_gpu_id:
            pytest.skip("No source GPU")

        print(f"\n[4/7] Destruindo Source GPU...")
        start = time.time()

        try:
            api_client.call("DELETE", f"/api/v1/instances/{metrics.source_gpu_id}", silent=True)
            metrics.time_destroy_source = time.time() - start

            print(f"✅ Source GPU destruída em {metrics.time_destroy_source:.1f}s")

        except Exception as e:
            print(f"⚠️  Erro ao destruir Source GPU: {e}")

    def test_05_provision_target_gpu(self, api_client, metrics):
        """[5/7] Provisiona Target GPU"""
        print(f"\n[5/7] Provisionando Target GPU...")
        start = time.time()

        try:
            # Buscar nova GPU
            offers = api_client.call("GET", "/api/v1/instances/offers", silent=True)

            if not offers or "offers" not in offers:
                pytest.skip("No GPU offers available")

            offers_list = offers.get("offers", [])
            if not offers_list:
                pytest.skip("Empty offers list")

            # Escolhe a mais barata
            cheapest = min(offers_list, key=lambda x: x.get("dph_total", 999))
            offer_id = cheapest.get("id")
            gpu_name = cheapest.get("gpu_name", "Unknown")
            price = cheapest.get("dph_total", 0)

            metrics.target_gpu_cost_per_hour = price

            print(f"   GPU: {gpu_name}")
            print(f"   Preço: ${price:.4f}/hr")

            # Criar instância
            create_result = api_client.call("POST", "/api/v1/instances", {
                "offer_id": offer_id,
                "image": "nvidia/cuda:12.1.0-base-ubuntu22.04",
                "disk_size": 20,
            }, silent=True)

            if not create_result:
                pytest.skip("Failed to create target instance")

            instance_id = str(create_result.get("instance_id", create_result.get("id")))
            metrics.target_gpu_id = instance_id

            print(f"   Instance ID: {instance_id}")

            # Aguardar ficar ready
            print("   Aguardando SSH ready...")
            ready_result = wait_for_instance_ready(api_client, instance_id, timeout=TIMEOUT_INSTANCE_READY)

            if not ready_result.get("success"):
                pytest.skip(f"Target instance not ready: {ready_result.get('error')}")

            metrics.time_provision_target = time.time() - start

            print(f"   SSH: {ready_result['ssh_host']}:{ready_result['ssh_port']}")
            print(f"✅ Target GPU pronta em {metrics.time_provision_target:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_06_restore_snapshot(self, api_client, metrics):
        """[6/7] Restaura snapshot na Target GPU"""
        if not metrics.target_gpu_id or not metrics.snapshot_id:
            pytest.skip("No target GPU or snapshot")

        print(f"\n[6/7] Restaurando snapshot...")
        start = time.time()

        try:
            # Restaurar snapshot via API
            restore_result = api_client.call("POST", "/api/v1/snapshots/restore", {
                "snapshot_id": metrics.snapshot_id,
                "target_path": TEST_FILES_DIR,
            }, params={"instance_id": metrics.target_gpu_id}, silent=True)

            if not restore_result:
                pytest.skip("Failed to restore snapshot")

            metrics.time_restore_snapshot = time.time() - start

            if "files_restored" in restore_result:
                print(f"   Arquivos restaurados: {restore_result['files_restored']}")

            print(f"✅ Snapshot restaurado em {metrics.time_restore_snapshot:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_07_validate_files(self, api_client, metrics):
        """[7/7] Valida arquivos restaurados (MD5)"""
        if not metrics.target_gpu_id or not metrics.test_files:
            pytest.skip("No target GPU or test files")

        print(f"\n[7/7] Validando arquivos restaurados...")
        start = time.time()

        try:
            # Obter SSH info
            instance_info = api_client.call("GET", f"/api/v1/instances/{metrics.target_gpu_id}", silent=True)
            ssh_host = instance_info.get("ssh_host")
            ssh_port = instance_info.get("ssh_port")

            if not ssh_host or not ssh_port:
                pytest.skip("SSH info not available")

            # Validar arquivos
            validated_count = validate_files_on_gpu(ssh_host, ssh_port, metrics.test_files)
            metrics.files_validated = validated_count
            metrics.time_validate = time.time() - start

            # Calcular tempo total e custo
            metrics.time_total = time.time() - metrics.start_time
            hours_used = metrics.time_total / 3600
            metrics.estimated_cost_usd = (
                hours_used * metrics.source_gpu_cost_per_hour +
                hours_used * metrics.target_gpu_cost_per_hour
            )

            # Validação final
            all_validated = validated_count == len(metrics.test_files)
            metrics.success = all_validated

            # Imprimir resumo
            metrics.print_summary()

            # Salvar relatório
            metrics.save_report("manual_failover_report.json")

            # Assert final
            assert all_validated, (
                f"File validation failed: {validated_count}/{len(metrics.test_files)} files valid"
            )

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_99_cleanup(self, api_client, metrics):
        """[8/7] Cleanup: deleta recursos"""
        print("\n[CLEANUP] Removendo recursos...")

        # Deletar Target GPU
        if metrics.target_gpu_id:
            try:
                api_client.call("DELETE", f"/api/v1/instances/{metrics.target_gpu_id}", silent=True)
                print(f"✅ Target GPU deletada: {metrics.target_gpu_id}")
            except Exception as e:
                print(f"⚠️  Erro ao deletar Target GPU: {e}")

        # Deletar Source GPU (se ainda existir)
        if metrics.source_gpu_id:
            try:
                api_client.call("DELETE", f"/api/v1/instances/{metrics.source_gpu_id}", silent=True)
                print(f"✅ Source GPU deletada: {metrics.source_gpu_id}")
            except Exception as e:
                print(f"⚠️  Source GPU já foi deletada")

        print("✅ Cleanup completo")


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
