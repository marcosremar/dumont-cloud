"""
Test 4.1: Large Model Snapshot - Dumont Cloud

Testa snapshot de arquivos grandes (simulando modelos LLM):
1. Provisionar GPU
2. Criar arquivo grande (1GB de dados aleatórios - simula modelo)
3. Calcular MD5 do arquivo
4. Criar snapshot comprimido
5. Upload para B2 (medir velocidade MB/s)
6. Destruir GPU 1
7. Provisionar GPU 2
8. Download snapshot (medir velocidade)
9. Verificar MD5
10. Destruir GPU 2
11. Relatório com métricas de transfer rate

ATENÇÃO: ESTE TESTE USA CRÉDITOS REAIS E PODE SER CARO!
- VAST.ai: ~$0.50-1.00 (2 GPUs + tempo de transfer)
- Backblaze B2: ~$0.01 para 1GB

Executar apenas com flag --real:
    pytest cli/tests/test_large_snapshot.py -v -s --real

Modo dry-run (simulação sem GPU):
    pytest cli/tests/test_large_snapshot.py -v -s --dry-run
"""

import pytest
import time
import json
import os
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

DUMONT_API_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8766")
VAST_API_KEY = os.environ.get("VAST_API_KEY")
B2_ENDPOINT = os.environ.get("B2_ENDPOINT", "https://s3.us-west-000.backblazeb2.com")
B2_BUCKET = os.environ.get("B2_BUCKET", "dumontcloud-snapshots")

# Configurações do teste
LARGE_FILE_SIZE_MB = 1024  # 1GB
LARGE_FILE_SIZE_BYTES = LARGE_FILE_SIZE_MB * 1024 * 1024

# Timeouts (em segundos)
TIMEOUT_INSTANCE_CREATE = 300
TIMEOUT_INSTANCE_READY = 600
TIMEOUT_CREATE_LARGE_FILE = 600     # 10 min para criar arquivo de 1GB
TIMEOUT_SNAPSHOT_CREATE = 1200      # 20 min para snapshot de 1GB
TIMEOUT_RESTORE = 1200              # 20 min para restore


@dataclass
class LargeSnapshotMetrics:
    """Métricas do teste de snapshot grande"""
    test_name: str = "large_model_snapshot"
    start_time: float = field(default_factory=time.time)

    # IDs de recursos
    gpu1_instance_id: Optional[str] = None
    gpu2_instance_id: Optional[str] = None
    snapshot_id: Optional[str] = None

    # Arquivo grande
    large_file_path: str = "/workspace/large-model.bin"
    large_file_size_mb: float = 0
    large_file_md5: Optional[str] = None

    # Tempos (segundos)
    time_provision_gpu1: float = 0
    time_create_large_file: float = 0
    time_calculate_md5: float = 0
    time_snapshot_create: float = 0
    time_destroy_gpu1: float = 0
    time_provision_gpu2: float = 0
    time_restore: float = 0
    time_validate_md5: float = 0
    time_destroy_gpu2: float = 0
    time_total: float = 0

    # Velocidades de transferência
    upload_speed_mbps: float = 0
    download_speed_mbps: float = 0

    # Snapshot info
    snapshot_size_compressed_mb: float = 0
    compression_ratio: float = 0

    # Custos
    gpu_cost_per_hour: float = 0
    estimated_cost_usd: float = 0

    # Status
    success: bool = False
    error_message: Optional[str] = None
    md5_matches: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat(),
            "resources": {
                "gpu1_instance_id": self.gpu1_instance_id,
                "gpu2_instance_id": self.gpu2_instance_id,
                "snapshot_id": self.snapshot_id,
            },
            "large_file": {
                "path": self.large_file_path,
                "size_mb": round(self.large_file_size_mb, 2),
                "md5": self.large_file_md5,
            },
            "timings": {
                "provision_gpu1_sec": round(self.time_provision_gpu1, 2),
                "create_file_sec": round(self.time_create_large_file, 2),
                "calculate_md5_sec": round(self.time_calculate_md5, 2),
                "snapshot_create_sec": round(self.time_snapshot_create, 2),
                "destroy_gpu1_sec": round(self.time_destroy_gpu1, 2),
                "provision_gpu2_sec": round(self.time_provision_gpu2, 2),
                "restore_sec": round(self.time_restore, 2),
                "validate_md5_sec": round(self.time_validate_md5, 2),
                "destroy_gpu2_sec": round(self.time_destroy_gpu2, 2),
                "total_sec": round(self.time_total, 2),
                "total_min": round(self.time_total / 60, 2),
            },
            "transfer": {
                "upload_speed_mbps": round(self.upload_speed_mbps, 2),
                "download_speed_mbps": round(self.download_speed_mbps, 2),
                "snapshot_compressed_mb": round(self.snapshot_size_compressed_mb, 2),
                "compression_ratio": round(self.compression_ratio, 2),
            },
            "cost": {
                "gpu_hourly_usd": round(self.gpu_cost_per_hour, 4),
                "estimated_total_usd": round(self.estimated_cost_usd, 4),
            },
            "validation": {
                "success": self.success,
                "md5_matches": self.md5_matches,
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


def ssh_exec(ssh_host: str, ssh_port: int, command: str, timeout: int = 300) -> Dict[str, Any]:
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
    """Provisiona uma GPU (helper reutilizável)"""
    # Buscar oferta mais barata
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

    # Criar instância
    create_result = call_api("POST", "/api/v1/instances", {
        "offer_id": offer_id,
        "image": "nvidia/cuda:12.1.0-base-ubuntu22.04",
        "disk_size": 30,  # Mais espaço para arquivo grande
    }, token=auth_token)

    if "error" in create_result:
        return {"error": f"Failed to create instance: {create_result['error']}"}

    instance_id = str(create_result.get("instance_id", create_result.get("id")))

    # Aguardar ready
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
    return LargeSnapshotMetrics()


@pytest.mark.slow
@pytest.mark.real
class TestLargeModelSnapshot:
    """Teste de snapshot de arquivo grande (simula modelo LLM)"""

    def test_01_provision_gpu1_and_create_large_file(self, auth_token, metrics):
        """[1/10] Provisiona GPU 1 e cria arquivo grande (1GB)"""
        print("\n" + "="*70)
        print("TESTE 4.1: LARGE MODEL SNAPSHOT")
        print("="*70)

        try:
            print(f"\n[1/10] Provisionando GPU 1...")
            start_provision = time.time()

            result = provision_gpu(auth_token)

            if "error" in result:
                pytest.skip(result["error"])

            metrics.gpu1_instance_id = result["instance_id"]
            metrics.gpu_cost_per_hour = result["price_per_hour"]
            metrics.time_provision_gpu1 = time.time() - start_provision

            ssh_host = result["ssh_host"]
            ssh_port = result["ssh_port"]

            print(f"   GPU: {result['gpu_name']}")
            print(f"   Instance ID: {metrics.gpu1_instance_id}")
            print(f"   SSH: {ssh_host}:{ssh_port}")
            print(f"   Tempo: {metrics.time_provision_gpu1:.1f}s")
            print(f"   ✓ GPU 1 provisionada")

            # Criar arquivo grande (1GB de dados aleatórios)
            print(f"\n[2/10] Criando arquivo grande ({LARGE_FILE_SIZE_MB}MB)...")
            start_create_file = time.time()

            # Criar workspace
            ssh_exec(ssh_host, ssh_port, "mkdir -p /workspace")

            # Criar arquivo de 1GB usando dd (mais rápido que random)
            # dd if=/dev/urandom of=/workspace/large-model.bin bs=1M count=1024
            create_cmd = f"dd if=/dev/urandom of={metrics.large_file_path} bs=1M count={LARGE_FILE_SIZE_MB} 2>&1"
            create_result = ssh_exec(ssh_host, ssh_port, create_cmd, timeout=TIMEOUT_CREATE_LARGE_FILE)

            if not create_result["success"]:
                pytest.skip(f"Failed to create large file: {create_result['stderr']}")

            metrics.time_create_large_file = time.time() - start_create_file

            # Obter tamanho real
            size_cmd = f"du -m {metrics.large_file_path} | awk '{{print $1}}'"
            size_result = ssh_exec(ssh_host, ssh_port, size_cmd)

            if size_result["success"]:
                try:
                    metrics.large_file_size_mb = float(size_result["stdout"].strip())
                except ValueError:
                    metrics.large_file_size_mb = LARGE_FILE_SIZE_MB

            print(f"   Tamanho: {metrics.large_file_size_mb:.2f} MB")
            print(f"   Tempo: {metrics.time_create_large_file:.1f}s")
            print(f"   Taxa: {metrics.large_file_size_mb / metrics.time_create_large_file:.2f} MB/s")
            print(f"   ✓ Arquivo grande criado")

            # Calcular MD5
            print(f"\n[3/10] Calculando MD5...")
            start_md5 = time.time()

            md5_cmd = f"md5sum {metrics.large_file_path} | awk '{{print $1}}'"
            md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd, timeout=300)

            if not md5_result["success"]:
                pytest.skip(f"Failed to calculate MD5: {md5_result['stderr']}")

            metrics.large_file_md5 = md5_result["stdout"].strip()
            metrics.time_calculate_md5 = time.time() - start_md5

            print(f"   MD5: {metrics.large_file_md5}")
            print(f"   Tempo: {metrics.time_calculate_md5:.1f}s")
            print(f"   ✓ MD5 calculado")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_02_create_snapshot(self, auth_token, metrics):
        """[4/10] Cria snapshot e faz upload para B2"""
        if not metrics.gpu1_instance_id:
            pytest.skip("No GPU 1 instance")

        try:
            print(f"\n[4/10] Criando snapshot (upload para B2)...")
            start_snapshot = time.time()

            snapshot_result = call_api("POST", "/api/v1/snapshots", {
                "instance_id": metrics.gpu1_instance_id,
                "source_path": "/workspace",
                "tags": ["large-model", "test", "1gb"],
            }, token=auth_token)

            if "error" in snapshot_result:
                pytest.skip(f"Snapshot failed: {snapshot_result['error']}")

            metrics.snapshot_id = snapshot_result.get("snapshot_id", snapshot_result.get("id"))
            metrics.time_snapshot_create = time.time() - start_snapshot

            # Obter tamanho comprimido (se disponível)
            size_compressed = snapshot_result.get("size_compressed", 0)
            if size_compressed:
                metrics.snapshot_size_compressed_mb = size_compressed / (1024 * 1024)
                metrics.compression_ratio = metrics.large_file_size_mb / metrics.snapshot_size_compressed_mb

            # Calcular velocidade de upload
            if metrics.time_snapshot_create > 0:
                metrics.upload_speed_mbps = (metrics.large_file_size_mb / metrics.time_snapshot_create) * 8  # MB/s -> Mbps

            print(f"   Snapshot ID: {metrics.snapshot_id}")
            print(f"   Tempo: {metrics.time_snapshot_create:.1f}s ({metrics.time_snapshot_create/60:.1f} min)")
            print(f"   Upload speed: {metrics.upload_speed_mbps:.2f} Mbps")

            if metrics.snapshot_size_compressed_mb > 0:
                print(f"   Compressed: {metrics.snapshot_size_compressed_mb:.2f} MB")
                print(f"   Compression: {metrics.compression_ratio:.2f}x")

            print(f"   ✓ Snapshot criado e enviado para B2")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_03_destroy_gpu1(self, auth_token, metrics):
        """[5/10] Destroi GPU 1"""
        if not metrics.gpu1_instance_id:
            pytest.skip("No GPU 1 instance")

        try:
            print(f"\n[5/10] Destruindo GPU 1...")
            start_destroy = time.time()

            call_api("DELETE", f"/api/v1/instances/{metrics.gpu1_instance_id}", token=auth_token)

            metrics.time_destroy_gpu1 = time.time() - start_destroy

            print(f"   Tempo: {metrics.time_destroy_gpu1:.1f}s")
            print(f"   ✓ GPU 1 destruída")

        except Exception as e:
            print(f"   ⚠ Warning: {e}")

    def test_04_provision_gpu2(self, auth_token, metrics):
        """[6/10] Provisiona GPU 2 para restore"""
        try:
            print(f"\n[6/10] Provisionando GPU 2...")
            start_provision = time.time()

            result = provision_gpu(auth_token)

            if "error" in result:
                pytest.skip(result["error"])

            metrics.gpu2_instance_id = result["instance_id"]
            metrics.time_provision_gpu2 = time.time() - start_provision

            print(f"   Instance ID: {metrics.gpu2_instance_id}")
            print(f"   Tempo: {metrics.time_provision_gpu2:.1f}s")
            print(f"   ✓ GPU 2 provisionada")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_05_restore_snapshot(self, auth_token, metrics):
        """[7/10] Restaura snapshot na GPU 2 (download do B2)"""
        if not metrics.gpu2_instance_id or not metrics.snapshot_id:
            pytest.skip("Missing GPU 2 or snapshot")

        try:
            print(f"\n[7/10] Restaurando snapshot (download do B2)...")
            start_restore = time.time()

            restore_result = call_api("POST", "/api/v1/snapshots/restore", {
                "snapshot_id": metrics.snapshot_id,
                "instance_id": metrics.gpu2_instance_id,
                "target_path": "/workspace",
            }, token=auth_token)

            if "error" in restore_result:
                pytest.skip(f"Restore failed: {restore_result['error']}")

            metrics.time_restore = time.time() - start_restore

            # Calcular velocidade de download
            if metrics.time_restore > 0:
                metrics.download_speed_mbps = (metrics.large_file_size_mb / metrics.time_restore) * 8  # Mbps

            print(f"   Tempo: {metrics.time_restore:.1f}s ({metrics.time_restore/60:.1f} min)")
            print(f"   Download speed: {metrics.download_speed_mbps:.2f} Mbps")
            print(f"   ✓ Snapshot restaurado")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_06_validate_md5(self, auth_token, metrics):
        """[8/10] Valida MD5 do arquivo restaurado"""
        if not metrics.gpu2_instance_id:
            pytest.skip("No GPU 2 instance")

        try:
            print(f"\n[8/10] Validando MD5...")
            start_validate = time.time()

            # Obter SSH info
            instance_info = call_api("GET", f"/api/v1/instances/{metrics.gpu2_instance_id}", token=auth_token)
            ssh_host = instance_info.get("ssh_host")
            ssh_port = instance_info.get("ssh_port")

            if not ssh_host or not ssh_port:
                pytest.skip("SSH info not available")

            # Calcular MD5 do arquivo restaurado
            md5_cmd = f"md5sum {metrics.large_file_path} | awk '{{print $1}}'"
            md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd, timeout=300)

            if not md5_result["success"]:
                pytest.skip(f"Failed to calculate MD5: {md5_result['stderr']}")

            restored_md5 = md5_result["stdout"].strip()
            metrics.time_validate_md5 = time.time() - start_validate

            print(f"   Original MD5:  {metrics.large_file_md5}")
            print(f"   Restored MD5:  {restored_md5}")
            print(f"   Tempo: {metrics.time_validate_md5:.1f}s")

            metrics.md5_matches = (restored_md5 == metrics.large_file_md5)

            if metrics.md5_matches:
                print(f"   ✓ MD5 MATCH - Integridade verificada!")
            else:
                print(f"   ✗ MD5 MISMATCH - Integridade FALHOU!")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_07_cleanup_and_report(self, auth_token, metrics):
        """[9/10] Cleanup e relatório final"""
        print(f"\n[9/10] Cleanup...")

        # Destruir GPU 2
        if metrics.gpu2_instance_id:
            try:
                start_destroy = time.time()
                call_api("DELETE", f"/api/v1/instances/{metrics.gpu2_instance_id}", token=auth_token)
                metrics.time_destroy_gpu2 = time.time() - start_destroy
                print(f"   ✓ GPU 2 destruída em {metrics.time_destroy_gpu2:.1f}s")
            except Exception as e:
                print(f"   ⚠ Warning: {e}")

        # Calcular totais
        metrics.time_total = time.time() - metrics.start_time
        hours_used = metrics.time_total / 3600
        metrics.estimated_cost_usd = hours_used * metrics.gpu_cost_per_hour * 2  # 2 GPUs

        # Determinar sucesso
        metrics.success = metrics.md5_matches

        # Relatório
        print("\n" + "="*70)
        print("RELATÓRIO: LARGE MODEL SNAPSHOT TEST")
        print("="*70)

        print(f"\nRecursos:")
        print(f"  GPU 1:           {metrics.gpu1_instance_id}")
        print(f"  GPU 2:           {metrics.gpu2_instance_id}")
        print(f"  Snapshot:        {metrics.snapshot_id}")

        print(f"\nArquivo:")
        print(f"  Path:            {metrics.large_file_path}")
        print(f"  Tamanho:         {metrics.large_file_size_mb:.2f} MB")
        print(f"  MD5:             {metrics.large_file_md5}")

        print(f"\nSnapshot:")
        print(f"  Compressed:      {metrics.snapshot_size_compressed_mb:.2f} MB")
        print(f"  Compression:     {metrics.compression_ratio:.2f}x")

        print(f"\nTransfer Speeds:")
        print(f"  Upload:          {metrics.upload_speed_mbps:.2f} Mbps")
        print(f"  Download:        {metrics.download_speed_mbps:.2f} Mbps")

        print(f"\nTimings:")
        print(f"  Provision GPU 1: {metrics.time_provision_gpu1:6.1f}s")
        print(f"  Create File:     {metrics.time_create_large_file:6.1f}s")
        print(f"  Calculate MD5:   {metrics.time_calculate_md5:6.1f}s")
        print(f"  Snapshot+Upload: {metrics.time_snapshot_create:6.1f}s ({metrics.time_snapshot_create/60:.1f} min)")
        print(f"  Destroy GPU 1:   {metrics.time_destroy_gpu1:6.1f}s")
        print(f"  Provision GPU 2: {metrics.time_provision_gpu2:6.1f}s")
        print(f"  Restore+Download:{metrics.time_restore:6.1f}s ({metrics.time_restore/60:.1f} min)")
        print(f"  Validate MD5:    {metrics.time_validate_md5:6.1f}s")
        print(f"  Destroy GPU 2:   {metrics.time_destroy_gpu2:6.1f}s")
        print(f"  TOTAL:           {metrics.time_total:6.1f}s ({metrics.time_total/60:.1f} min)")

        print(f"\nCusto:")
        print(f"  GPU hourly:      ${metrics.gpu_cost_per_hour:.4f}/hr")
        print(f"  Tempo total:     {hours_used:.4f} hrs")
        print(f"  Total (2 GPUs):  ${metrics.estimated_cost_usd:.4f}")

        print(f"\nValidação:")
        print(f"  MD5 Match:       {'✓ SIM' if metrics.md5_matches else '✗ NÃO'}")
        print(f"  Sucesso:         {'✓ SIM' if metrics.success else '✗ NÃO'}")

        if metrics.error_message:
            print(f"  Erro:            {metrics.error_message}")

        print("\n" + "="*70)

        # Salvar em JSON
        report_file = f"/tmp/large_snapshot_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)

        print(f"\nRelatório salvo em: {report_file}")

        # Assert final
        assert metrics.success, "Large snapshot test failed: MD5 mismatch"


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
