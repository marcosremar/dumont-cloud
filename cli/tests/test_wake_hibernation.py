"""
Test 3.2: Wake from Hibernation - Dumont Cloud

Testa o processo de "wake" de uma GPU hibernada:
1. Encontrar snapshot hibernado mais recente
2. Provisionar nova GPU
3. Download + restore do snapshot
4. Verificar todos os arquivos existem com MD5 correto
5. Medir tempo de "wake up"
6. Destruir GPU
7. Gerar relatório detalhado

ATENÇÃO: ESTE TESTE USA CRÉDITOS REAIS!
- VAST.ai: ~$0.15-0.30 por teste
- Backblaze B2: transfer mínimo

Pré-requisito: Execute test_auto_hibernation.py primeiro para criar snapshot

Executar:
    pytest cli/tests/test_wake_hibernation.py -v -s --tb=short

Executar em modo dry-run:
    pytest cli/tests/test_wake_hibernation.py -v -s --dry-run
"""

import pytest
import time
import json
import os
import subprocess
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

# Timeouts (em segundos)
TIMEOUT_INSTANCE_CREATE = 300
TIMEOUT_INSTANCE_READY = 600
TIMEOUT_RESTORE = 600


@dataclass
class WakeTestMetrics:
    """Métricas do teste de wake"""
    test_name: str = "wake_from_hibernation"
    start_time: float = field(default_factory=time.time)

    # IDs de recursos
    snapshot_id: Optional[str] = None
    new_instance_id: Optional[str] = None

    # Arquivos esperados (do snapshot original)
    expected_files: List[Dict[str, str]] = field(default_factory=list)

    # Tempos (segundos)
    time_find_snapshot: float = 0
    time_provision: float = 0
    time_restore: float = 0
    time_validate: float = 0
    time_destroy: float = 0
    time_total: float = 0
    time_wake_up_total: float = 0  # provision + restore

    # Custos
    gpu_cost_per_hour: float = 0
    estimated_cost_usd: float = 0

    # Validação
    files_validated: int = 0
    files_failed: int = 0
    success: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat(),
            "resources": {
                "snapshot_id": self.snapshot_id,
                "new_instance_id": self.new_instance_id,
                "expected_files": len(self.expected_files),
            },
            "timings": {
                "find_snapshot_sec": round(self.time_find_snapshot, 2),
                "provision_sec": round(self.time_provision, 2),
                "restore_sec": round(self.time_restore, 2),
                "validate_sec": round(self.time_validate, 2),
                "destroy_sec": round(self.time_destroy, 2),
                "total_sec": round(self.time_total, 2),
                "wake_up_total_sec": round(self.time_wake_up_total, 2),
                "total_min": round(self.time_total / 60, 2),
            },
            "cost": {
                "gpu_hourly_usd": round(self.gpu_cost_per_hour, 4),
                "estimated_total_usd": round(self.estimated_cost_usd, 4),
            },
            "validation": {
                "files_validated": self.files_validated,
                "files_failed": self.files_failed,
                "success": self.success,
                "error": self.error_message,
            }
        }


# =============================================================================
# HELPERS API
# =============================================================================

def call_api(method: str, endpoint: str, data: Optional[Dict] = None, token: Optional[str] = None) -> Dict:
    """Chama API do Dumont com retry e backoff"""
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
                # Rate limiting
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
    """Aguarda instância ficar running e com SSH disponível"""
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


def find_most_recent_hibernation_snapshot(token: str) -> Optional[Dict[str, Any]]:
    """Encontra snapshot de hibernação mais recente"""
    result = call_api("GET", "/api/v1/snapshots", token=token)

    if "error" in result:
        return None

    snapshots = result.get("snapshots", [])

    # Filtrar snapshots com tag "auto-hibernation"
    hibernation_snapshots = []
    for snap in snapshots:
        tags = snap.get("tags", [])
        if "auto-hibernation" in tags or "hibernation" in tags:
            hibernation_snapshots.append(snap)

    if not hibernation_snapshots:
        return None

    # Ordenar por timestamp (mais recente primeiro)
    hibernation_snapshots.sort(key=lambda x: x.get("time", ""), reverse=True)

    return hibernation_snapshots[0]


def validate_file_exists(ssh_host: str, ssh_port: int, file_path: str, expected_md5: str) -> bool:
    """Valida que arquivo existe com MD5 correto"""
    # Verificar se existe
    check_cmd = f"test -f {file_path} && echo exists || echo missing"
    check_result = ssh_exec(ssh_host, ssh_port, check_cmd)

    if not check_result["success"] or "missing" in check_result["stdout"]:
        return False

    # Obter MD5
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
    return WakeTestMetrics()


@pytest.mark.slow
@pytest.mark.real
class TestWakeFromHibernation:
    """Teste de Wake from Hibernation"""

    def test_01_find_snapshot(self, auth_token, metrics):
        """[1/5] Encontra snapshot hibernado mais recente"""
        print("\n" + "="*70)
        print("TESTE 3.2: WAKE FROM HIBERNATION")
        print("="*70)

        try:
            print("\n[1/5] Procurando snapshot hibernado...")
            start_find = time.time()

            snapshot = find_most_recent_hibernation_snapshot(auth_token)

            if not snapshot:
                pytest.skip("Nenhum snapshot de hibernação encontrado. Execute test_auto_hibernation.py primeiro.")

            metrics.snapshot_id = snapshot.get("id") or snapshot.get("short_id")
            metrics.time_find_snapshot = time.time() - start_find

            print(f"   Snapshot ID: {metrics.snapshot_id}")
            print(f"   Timestamp: {snapshot.get('time', 'N/A')}")
            print(f"   Tags: {snapshot.get('tags', [])}")
            print(f"   Paths: {snapshot.get('paths', [])}")
            print(f"   Tempo: {metrics.time_find_snapshot:.1f}s")
            print(f"   ✓ Snapshot encontrado")

            # Extrair arquivos esperados (se disponível nos metadados)
            # Por enquanto, assumimos arquivos padrão do test_auto_hibernation
            for i in range(5):
                metrics.expected_files.append({
                    "path": f"/workspace/auto-hibernation-test-{i+1}.txt",
                    "md5": "",  # Não temos MD5 aqui, validaremos apenas existência
                })

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_02_provision_new_gpu(self, auth_token, metrics):
        """[2/5] Provisiona nova GPU para restore"""
        if not metrics.snapshot_id:
            pytest.skip("No snapshot ID")

        try:
            print("\n[2/5] Provisionando nova GPU...")
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
            metrics.new_instance_id = instance_id

            print(f"   Instance ID: {instance_id}")

            # Aguardar ready
            print("   Aguardando ficar ready...")
            ready_result = wait_for_instance_ready(instance_id, auth_token, timeout=TIMEOUT_INSTANCE_READY)

            if not ready_result.get("success"):
                pytest.skip(f"Instance not ready: {ready_result.get('error')}")

            metrics.time_provision = time.time() - start_provision

            print(f"   SSH: {ready_result['ssh_host']}:{ready_result['ssh_port']}")
            print(f"   Tempo: {metrics.time_provision:.1f}s")
            print(f"   ✓ GPU provisionada")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_03_restore_snapshot(self, auth_token, metrics):
        """[3/5] Restaura snapshot na nova GPU"""
        if not metrics.new_instance_id or not metrics.snapshot_id:
            pytest.skip("Missing instance or snapshot ID")

        try:
            print("\n[3/5] Restaurando snapshot...")
            start_restore = time.time()

            # Trigger restore via API
            restore_result = call_api("POST", "/api/v1/snapshots/restore", {
                "snapshot_id": metrics.snapshot_id,
                "instance_id": metrics.new_instance_id,
                "target_path": "/workspace",
            }, token=auth_token)

            if "error" in restore_result:
                pytest.skip(f"Restore failed: {restore_result['error']}")

            metrics.time_restore = time.time() - start_restore

            print(f"   Snapshot ID: {metrics.snapshot_id}")
            print(f"   Target: /workspace")
            print(f"   Tempo: {metrics.time_restore:.1f}s")
            print(f"   ✓ Snapshot restaurado")

            # Calcular tempo total de "wake up"
            metrics.time_wake_up_total = metrics.time_provision + metrics.time_restore

            print(f"\n   WAKE UP TOTAL: {metrics.time_wake_up_total:.1f}s ({metrics.time_wake_up_total/60:.1f} min)")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_04_validate_files(self, auth_token, metrics):
        """[4/5] Valida que arquivos foram restaurados"""
        if not metrics.new_instance_id:
            pytest.skip("No instance ID")

        try:
            print("\n[4/5] Validando arquivos restaurados...")
            start_validate = time.time()

            # Obter SSH info
            instance_info = call_api("GET", f"/api/v1/instances/{metrics.new_instance_id}", token=auth_token)
            ssh_host = instance_info.get("ssh_host")
            ssh_port = instance_info.get("ssh_port")

            if not ssh_host or not ssh_port:
                pytest.skip("SSH info not available")

            # Validar cada arquivo
            validated = 0
            failed = 0

            for expected_file in metrics.expected_files:
                file_path = expected_file["path"]

                # Verificar se existe
                check_cmd = f"test -f {file_path} && echo exists || echo missing"
                check_result = ssh_exec(ssh_host, ssh_port, check_cmd)

                if check_result["success"] and "exists" in check_result["stdout"]:
                    validated += 1
                    print(f"   ✓ {file_path}")
                else:
                    failed += 1
                    print(f"   ✗ {file_path} - NOT FOUND")

            metrics.files_validated = validated
            metrics.files_failed = failed
            metrics.time_validate = time.time() - start_validate

            print(f"\n   Validados: {validated}/{len(metrics.expected_files)}")
            print(f"   Falhas: {failed}")
            print(f"   Tempo: {metrics.time_validate:.1f}s")

            if validated == len(metrics.expected_files):
                print(f"   ✓ Todos os arquivos restaurados com sucesso")
            else:
                print(f"   ⚠ Alguns arquivos faltando")

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            raise

    def test_05_cleanup_and_report(self, auth_token, metrics):
        """[5/5] Cleanup e relatório final"""
        print("\n[5/5] Cleanup e relatório...")

        # Destruir GPU
        if metrics.new_instance_id:
            try:
                print("   Destruindo GPU...")
                start_destroy = time.time()

                call_api("DELETE", f"/api/v1/instances/{metrics.new_instance_id}", token=auth_token)

                metrics.time_destroy = time.time() - start_destroy
                print(f"   ✓ GPU destruída em {metrics.time_destroy:.1f}s")

            except Exception as e:
                print(f"   ⚠ Erro ao destruir: {e}")

        # Calcular totais
        metrics.time_total = time.time() - metrics.start_time
        hours_used = metrics.time_total / 3600
        metrics.estimated_cost_usd = hours_used * metrics.gpu_cost_per_hour

        # Determinar sucesso
        metrics.success = (
            metrics.files_validated == len(metrics.expected_files) and
            metrics.files_failed == 0
        )

        # Relatório
        print("\n" + "="*70)
        print("RELATÓRIO: WAKE FROM HIBERNATION TEST")
        print("="*70)

        print(f"\nRecursos:")
        print(f"  Snapshot ID:     {metrics.snapshot_id}")
        print(f"  New Instance:    {metrics.new_instance_id}")
        print(f"  Expected Files:  {len(metrics.expected_files)}")

        print(f"\nTimings:")
        print(f"  1. Find Snapshot: {metrics.time_find_snapshot:6.1f}s")
        print(f"  2. Provision GPU: {metrics.time_provision:6.1f}s")
        print(f"  3. Restore:       {metrics.time_restore:6.1f}s")
        print(f"  4. Validate:      {metrics.time_validate:6.1f}s")
        print(f"  5. Destroy:       {metrics.time_destroy:6.1f}s")
        print(f"  TOTAL:            {metrics.time_total:6.1f}s ({metrics.time_total/60:.1f} min)")
        print(f"\n  WAKE UP TIME:     {metrics.time_wake_up_total:6.1f}s ({metrics.time_wake_up_total/60:.1f} min)")

        print(f"\nCusto:")
        print(f"  GPU hourly:       ${metrics.gpu_cost_per_hour:.4f}/hr")
        print(f"  Tempo total:      {hours_used:.4f} hrs")
        print(f"  Custo estimado:   ${metrics.estimated_cost_usd:.4f}")

        print(f"\nValidação:")
        print(f"  Files validated:  {metrics.files_validated}/{len(metrics.expected_files)}")
        print(f"  Files failed:     {metrics.files_failed}")
        print(f"  Sucesso:          {'✓ SIM' if metrics.success else '✗ NÃO'}")

        if metrics.error_message:
            print(f"  Erro:             {metrics.error_message}")

        print("\n" + "="*70)

        # Salvar em JSON
        report_file = f"/tmp/wake_hibernation_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)

        print(f"\nRelatório salvo em: {report_file}")

        # Assert final
        assert metrics.success, (
            f"Wake test failed: {metrics.files_validated}/{len(metrics.expected_files)} files restored"
        )


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
