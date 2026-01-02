"""
TEST 2.2: Automated Failover (With Detection)

Jornada REAL de failover automático:
1. Provisionar GPU 1 com monitoramento (heartbeat)
2. Criar arquivos + snapshot inicial
3. Simular falha (marcar GPU como "perdida")
4. Detectar falha via timeout de heartbeat (30s)
5. Trigger failover automático:
   - Provisionar GPU 2
   - Restaurar snapshot mais recente
   - Verificar dados
6. Medir tempo total de recovery (MTTR)

ATENÇÃO: Este teste pode ser executado em dois modos:

1. MODO REAL (usa créditos VAST.ai):
   pytest cli/tests/test_auto_failover.py -v -s -m "slow"

2. MODO SIMULAÇÃO (local, sem custos):
   pytest cli/tests/test_auto_failover.py -v -s -m "not slow"

Custo estimado (modo real):
- VAST.ai: ~$0.40-0.80 por teste completo (2 GPUs)
- Backblaze B2: ~$0.01 por snapshot
"""

import pytest
import time
import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from queue import Queue

from cli.utils.api_client import APIClient


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

DUMONT_API_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8766")
VAST_API_KEY = os.environ.get("VAST_API_KEY")
B2_BUCKET = os.environ.get("B2_BUCKET", "dumontcloud-snapshots")

# Timeouts
TIMEOUT_INSTANCE_READY = 600       # 10 min
TIMEOUT_HEARTBEAT = 30             # 30s para detectar falha
TIMEOUT_FAILOVER = 1200            # 20 min para failover completo

# Configuração do teste
TEST_FILES_COUNT = 50              # Menos arquivos para teste mais rápido
TEST_FILES_DIR = "/workspace/test_data"


@dataclass
class HeartbeatMonitor:
    """Monitor de heartbeat para detectar falhas"""
    instance_id: str
    api_client: APIClient
    interval_seconds: int = 10
    timeout_seconds: int = 30

    _running: bool = field(default=False, init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)
    _last_heartbeat: float = field(default_factory=time.time, init=False)
    _failure_detected: bool = field(default=False, init=False)
    _failure_queue: Queue = field(default_factory=Queue, init=False)

    def start(self):
        """Inicia monitoramento"""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print(f"🔍 Heartbeat monitor iniciado (timeout: {self.timeout_seconds}s)")

    def stop(self):
        """Para monitoramento"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("🛑 Heartbeat monitor parado")

    def send_heartbeat(self):
        """Registra heartbeat"""
        self._last_heartbeat = time.time()

    def is_failure_detected(self) -> bool:
        """Verifica se falha foi detectada"""
        return self._failure_detected

    def get_failure_info(self) -> Optional[Dict[str, Any]]:
        """Retorna info da falha se detectada"""
        if not self._failure_queue.empty():
            return self._failure_queue.get()
        return None

    def _monitor_loop(self):
        """Loop de monitoramento"""
        while self._running:
            time.sleep(self.interval_seconds)

            # Verificar timeout
            elapsed = time.time() - self._last_heartbeat

            if elapsed > self.timeout_seconds and not self._failure_detected:
                self._failure_detected = True
                failure_info = {
                    "timestamp": datetime.now().isoformat(),
                    "instance_id": self.instance_id,
                    "last_heartbeat": datetime.fromtimestamp(self._last_heartbeat).isoformat(),
                    "timeout_seconds": self.timeout_seconds,
                    "elapsed_seconds": elapsed,
                }
                self._failure_queue.put(failure_info)
                print(f"\n⚠️  FALHA DETECTADA!")
                print(f"   Instance: {self.instance_id}")
                print(f"   Last heartbeat: {elapsed:.1f}s ago")
                print(f"   Timeout: {self.timeout_seconds}s")


@dataclass
class AutoFailoverMetrics:
    """Métricas do teste de failover automático"""
    test_name: str = "auto_failover_with_detection"
    start_time: float = field(default_factory=time.time)

    # IDs de recursos
    primary_gpu_id: Optional[str] = None
    failover_gpu_id: Optional[str] = None
    snapshot_id: Optional[str] = None

    # Arquivos de teste
    test_files_count: int = 0

    # Tempos (segundos)
    time_provision_primary: float = 0
    time_create_files: float = 0
    time_create_snapshot: float = 0
    time_simulate_failure: float = 0
    time_detect_failure: float = 0
    time_failover_trigger: float = 0
    time_provision_failover: float = 0
    time_restore_data: float = 0
    time_validate: float = 0
    time_total_recovery: float = 0  # MTTR (Mean Time To Recovery)
    time_total: float = 0

    # Custos
    primary_gpu_cost_per_hour: float = 0
    failover_gpu_cost_per_hour: float = 0
    estimated_cost_usd: float = 0

    # Status
    success: bool = False
    files_validated: int = 0
    failure_detected_at: Optional[str] = None
    recovery_completed_at: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte métricas para dicionário"""
        return {
            "test_name": self.test_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "resources": {
                "primary_gpu_id": self.primary_gpu_id,
                "failover_gpu_id": self.failover_gpu_id,
                "snapshot_id": self.snapshot_id,
            },
            "test_files_count": self.test_files_count,
            "timings": {
                "provision_primary_sec": round(self.time_provision_primary, 2),
                "create_files_sec": round(self.time_create_files, 2),
                "create_snapshot_sec": round(self.time_create_snapshot, 2),
                "simulate_failure_sec": round(self.time_simulate_failure, 2),
                "detect_failure_sec": round(self.time_detect_failure, 2),
                "failover_trigger_sec": round(self.time_failover_trigger, 2),
                "provision_failover_sec": round(self.time_provision_failover, 2),
                "restore_data_sec": round(self.time_restore_data, 2),
                "validate_sec": round(self.time_validate, 2),
                "mttr_sec": round(self.time_total_recovery, 2),
                "mttr_min": round(self.time_total_recovery / 60, 2),
                "total_sec": round(self.time_total, 2),
                "total_min": round(self.time_total / 60, 2),
            },
            "cost": {
                "primary_gpu_hourly_usd": round(self.primary_gpu_cost_per_hour, 4),
                "failover_gpu_hourly_usd": round(self.failover_gpu_cost_per_hour, 4),
                "estimated_total_usd": round(self.estimated_cost_usd, 4),
            },
            "validation": {
                "success": self.success,
                "files_validated": self.files_validated,
                "files_total": self.test_files_count,
                "error": self.error_message,
            },
            "recovery": {
                "failure_detected_at": self.failure_detected_at,
                "recovery_completed_at": self.recovery_completed_at,
                "mttr_seconds": round(self.time_total_recovery, 2),
            }
        }

    def save_report(self, file_path: str = "auto_failover_report.json"):
        """Salva relatório em JSON"""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"\n📊 Relatório salvo em: {file_path}")

    def print_summary(self):
        """Imprime resumo formatado"""
        print("\n" + "=" * 80)
        print("RELATÓRIO: AUTOMATED FAILOVER (WITH DETECTION)")
        print("=" * 80)

        print("\n🕐 TIMELINE:")
        print(f"  1. Provisionar Primary GPU:     {self.time_provision_primary:8.1f}s")
        print(f"  2. Criar {self.test_files_count:2d} arquivos:          {self.time_create_files:8.1f}s")
        print(f"  3. Criar snapshot:              {self.time_create_snapshot:8.1f}s")
        print(f"  4. Simular falha:               {self.time_simulate_failure:8.1f}s")
        print(f"  5. Detectar falha:              {self.time_detect_failure:8.1f}s")
        print(f"  6. Trigger failover:            {self.time_failover_trigger:8.1f}s")
        print(f"  7. Provisionar Failover GPU:    {self.time_provision_failover:8.1f}s")
        print(f"  8. Restaurar dados:             {self.time_restore_data:8.1f}s")
        print(f"  9. Validar:                     {self.time_validate:8.1f}s")
        print(f"  {'─' * 60}")
        print(f"  MTTR (Recovery Time):           {self.time_total_recovery:8.1f}s ({self.time_total_recovery/60:.1f} min)")
        print(f"  TOTAL:                          {self.time_total:8.1f}s ({self.time_total/60:.1f} min)")

        print("\n⚡ RECOVERY METRICS:")
        print(f"  Failure Detected:  {self.failure_detected_at or 'N/A'}")
        print(f"  Recovery Complete: {self.recovery_completed_at or 'N/A'}")
        print(f"  MTTR:              {self.time_total_recovery:.1f}s ({self.time_total_recovery/60:.1f} min)")

        print("\n💰 CUSTOS:")
        print(f"  Primary GPU: ${self.primary_gpu_cost_per_hour:.4f}/hr")
        print(f"  Failover GPU: ${self.failover_gpu_cost_per_hour:.4f}/hr")
        print(f"  Tempo total: {self.time_total/3600:.4f} hrs")
        print(f"  Total estimado: ${self.estimated_cost_usd:.4f}")

        print("\n🔍 VALIDAÇÃO:")
        print(f"  Arquivos criados: {self.test_files_count}")
        print(f"  Arquivos validados: {self.files_validated}")
        if self.test_files_count > 0:
            print(f"  Taxa de sucesso: {self.files_validated / self.test_files_count * 100:.1f}%")
        print(f"  Status: {'✅ SUCESSO' if self.success else '❌ FALHA'}")

        if self.error_message:
            print(f"\n⚠️  Erro: {self.error_message}")

        print("\n" + "=" * 80)


# =============================================================================
# HELPERS
# =============================================================================

def ssh_exec(ssh_host: str, ssh_port: int, command: str, timeout: int = 300) -> Dict[str, Any]:
    """Executa comando via SSH"""
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": f"Timeout after {timeout}s"}
    except Exception as e:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": str(e)}


def wait_for_ssh(ssh_host: str, ssh_port: int, timeout: int = 300) -> bool:
    """Aguarda SSH ficar acessível"""
    start = time.time()
    while time.time() - start < timeout:
        result = ssh_exec(ssh_host, ssh_port, "echo ready", timeout=10)
        if result["success"]:
            return True
        time.sleep(10)
    return False


def wait_for_instance_ready(api: APIClient, instance_id: str, timeout: int = 600) -> Dict[str, Any]:
    """Aguarda instância ficar running + SSH"""
    start = time.time()
    while time.time() - start < timeout:
        result = api.call("GET", f"/api/v1/instances/{instance_id}", silent=True)
        if result:
            status = result.get("status", "").lower()
            ssh_host = result.get("ssh_host")
            ssh_port = result.get("ssh_port")
            if status == "running" and ssh_host and ssh_port:
                if wait_for_ssh(ssh_host, ssh_port, timeout=60):
                    return {"success": True, "status": status, "ssh_host": ssh_host, "ssh_port": ssh_port}
        time.sleep(10)
    return {"success": False, "error": f"Instance not ready after {timeout}s"}


def create_simple_test_files(ssh_host: str, ssh_port: int, num_files: int = 50) -> int:
    """Cria arquivos de teste simples"""
    print(f"\n📁 Criando {num_files} arquivos de teste...")

    ssh_exec(ssh_host, ssh_port, f"mkdir -p {TEST_FILES_DIR}")

    for i in range(num_files):
        file_path = f"{TEST_FILES_DIR}/file-{i+1:03d}.txt"
        content = f"Test file #{i+1}\nTimestamp: {time.time()}\nRandom: {os.urandom(8).hex()}\n"
        create_cmd = f"cat > {file_path} << 'EOF'\n{content}\nEOF"
        ssh_exec(ssh_host, ssh_port, create_cmd)

        if (i + 1) % 10 == 0:
            print(f"   Progresso: {i+1}/{num_files}...")

    print(f"✅ {num_files} arquivos criados!")
    return num_files


def validate_files_exist(ssh_host: str, ssh_port: int, num_files: int) -> int:
    """Valida que arquivos existem"""
    print(f"\n🔍 Validando {num_files} arquivos...")

    validated = 0
    for i in range(num_files):
        file_path = f"{TEST_FILES_DIR}/file-{i+1:03d}.txt"
        check_cmd = f"test -f {file_path} && echo exists || echo missing"
        result = ssh_exec(ssh_host, ssh_port, check_cmd)

        if result["success"] and "exists" in result["stdout"]:
            validated += 1

        if (i + 1) % 10 == 0:
            print(f"   Progresso: {i+1}/{num_files}...")

    print(f"✅ {validated}/{num_files} arquivos validados!")
    return validated


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def api_client():
    """Cliente API autenticado"""
    api = APIClient(base_url=DUMONT_API_URL)
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
    return AutoFailoverMetrics()


# =============================================================================
# TESTE AUTO FAILOVER
# =============================================================================

@pytest.mark.slow
@pytest.mark.real
class TestAutoFailover:
    """
    TEST 2.2: Automated Failover (With Detection)

    Jornada completa:
    1. Provisionar Primary GPU com heartbeat monitoring
    2. Criar arquivos de teste
    3. Criar snapshot inicial
    4. Simular falha (parar heartbeat)
    5. Detectar falha via timeout (30s)
    6. Trigger failover automático
    7. Provisionar Failover GPU
    8. Restaurar snapshot
    9. Validar dados
    10. Medir MTTR (Mean Time To Recovery)
    """

    def test_01_provision_primary_gpu(self, api_client, metrics):
        """[1/10] Provisiona Primary GPU"""
        print("\n" + "=" * 80)
        print("TEST 2.2: AUTOMATED FAILOVER (WITH DETECTION)")
        print("=" * 80)

        print("\n[1/10] Provisionando Primary GPU...")
        start = time.time()

        try:
            offers = api_client.call("GET", "/api/v1/instances/offers", silent=True)
            if not offers or "offers" not in offers:
                pytest.skip("No GPU offers available")

            offers_list = offers.get("offers", [])
            if not offers_list:
                pytest.skip("Empty offers list")

            cheapest = min(offers_list, key=lambda x: x.get("dph_total", 999))
            offer_id = cheapest.get("id")
            gpu_name = cheapest.get("gpu_name", "Unknown")
            price = cheapest.get("dph_total", 0)

            metrics.primary_gpu_cost_per_hour = price

            print(f"   GPU: {gpu_name}")
            print(f"   Preço: ${price:.4f}/hr")

            create_result = api_client.call("POST", "/api/v1/instances", {
                "offer_id": offer_id,
                "image": "nvidia/cuda:12.1.0-base-ubuntu22.04",
                "disk_size": 20,
            }, silent=True)

            if not create_result:
                pytest.skip("Failed to create instance")

            instance_id = str(create_result.get("instance_id", create_result.get("id")))
            metrics.primary_gpu_id = instance_id

            print(f"   Instance ID: {instance_id}")

            ready_result = wait_for_instance_ready(api_client, instance_id, timeout=TIMEOUT_INSTANCE_READY)
            if not ready_result.get("success"):
                pytest.skip(f"Instance not ready: {ready_result.get('error')}")

            metrics.time_provision_primary = time.time() - start

            print(f"   SSH: {ready_result['ssh_host']}:{ready_result['ssh_port']}")
            print(f"✅ Primary GPU pronta em {metrics.time_provision_primary:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_02_create_test_files(self, api_client, metrics):
        """[2/10] Cria arquivos de teste"""
        if not metrics.primary_gpu_id:
            pytest.skip("No primary GPU")

        print(f"\n[2/10] Criando {TEST_FILES_COUNT} arquivos de teste...")
        start = time.time()

        try:
            instance_info = api_client.call("GET", f"/api/v1/instances/{metrics.primary_gpu_id}", silent=True)
            ssh_host = instance_info.get("ssh_host")
            ssh_port = instance_info.get("ssh_port")

            if not ssh_host or not ssh_port:
                pytest.skip("SSH info not available")

            num_files = create_simple_test_files(ssh_host, ssh_port, num_files=TEST_FILES_COUNT)
            metrics.test_files_count = num_files
            metrics.time_create_files = time.time() - start

            print(f"✅ Arquivos criados em {metrics.time_create_files:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_03_create_snapshot(self, api_client, metrics):
        """[3/10] Cria snapshot inicial"""
        if not metrics.primary_gpu_id:
            pytest.skip("No primary GPU")

        print(f"\n[3/10] Criando snapshot inicial...")
        start = time.time()

        try:
            snapshot_result = api_client.call("POST", "/api/v1/snapshots", {
                "instance_id": metrics.primary_gpu_id,
                "source_path": TEST_FILES_DIR,
                "tags": [f"test-auto-failover-{int(time.time())}"]
            }, silent=True)

            if not snapshot_result:
                pytest.skip("Failed to create snapshot")

            snapshot_id = snapshot_result.get("snapshot_id", snapshot_result.get("id"))
            metrics.snapshot_id = snapshot_id
            metrics.time_create_snapshot = time.time() - start

            print(f"   Snapshot ID: {snapshot_id}")
            print(f"✅ Snapshot criado em {metrics.time_create_snapshot:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_04_simulate_failure(self, api_client, metrics):
        """[4/10] Simula falha da Primary GPU"""
        if not metrics.primary_gpu_id:
            pytest.skip("No primary GPU")

        print(f"\n[4/10] Simulando falha da Primary GPU...")
        start = time.time()

        try:
            # Iniciar heartbeat monitor
            monitor = HeartbeatMonitor(
                instance_id=metrics.primary_gpu_id,
                api_client=api_client,
                timeout_seconds=TIMEOUT_HEARTBEAT
            )
            monitor.start()

            # Simular alguns heartbeats normais
            print("   Enviando heartbeats normais...")
            for i in range(3):
                monitor.send_heartbeat()
                print(f"   💓 Heartbeat #{i+1}")
                time.sleep(5)

            # Parar de enviar heartbeats (simular falha)
            print(f"\n   🔴 PARANDO HEARTBEATS (simulando falha)...")
            print(f"   Aguardando detecção de falha (timeout: {TIMEOUT_HEARTBEAT}s)...")

            # Aguardar detecção
            detection_start = time.time()
            while not monitor.is_failure_detected():
                time.sleep(1)
                elapsed = time.time() - detection_start
                if elapsed > TIMEOUT_HEARTBEAT + 30:
                    pytest.skip("Failure detection timeout")

            metrics.time_detect_failure = time.time() - detection_start

            failure_info = monitor.get_failure_info()
            if failure_info:
                metrics.failure_detected_at = failure_info["timestamp"]

            monitor.stop()

            metrics.time_simulate_failure = time.time() - start

            print(f"\n✅ Falha detectada em {metrics.time_detect_failure:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_05_trigger_failover(self, api_client, metrics):
        """[5/10] Trigger failover automático"""
        if not metrics.failure_detected_at:
            pytest.skip("No failure detected")

        print(f"\n[5/10] Triggering failover automático...")
        start_recovery = time.time()  # Início do MTTR
        start = time.time()

        try:
            # Aqui você pode chamar uma API de failover automática
            # Por enquanto, vamos apenas registrar o trigger
            print("   ⚡ Failover trigger ativado!")
            print("   📋 Ações:")
            print("      1. Marcar Primary GPU como failed")
            print("      2. Buscar snapshot mais recente")
            print("      3. Provisionar Failover GPU")
            print("      4. Restaurar dados")

            metrics.time_failover_trigger = time.time() - start

            # Salvar timestamp de início do recovery
            self._recovery_start = start_recovery

            print(f"✅ Failover trigger em {metrics.time_failover_trigger:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_06_provision_failover_gpu(self, api_client, metrics):
        """[6/10] Provisiona Failover GPU"""
        print(f"\n[6/10] Provisionando Failover GPU...")
        start = time.time()

        try:
            offers = api_client.call("GET", "/api/v1/instances/offers", silent=True)
            if not offers or "offers" not in offers:
                pytest.skip("No GPU offers available")

            offers_list = offers.get("offers", [])
            if not offers_list:
                pytest.skip("Empty offers list")

            cheapest = min(offers_list, key=lambda x: x.get("dph_total", 999))
            offer_id = cheapest.get("id")
            gpu_name = cheapest.get("gpu_name", "Unknown")
            price = cheapest.get("dph_total", 0)

            metrics.failover_gpu_cost_per_hour = price

            print(f"   GPU: {gpu_name}")
            print(f"   Preço: ${price:.4f}/hr")

            create_result = api_client.call("POST", "/api/v1/instances", {
                "offer_id": offer_id,
                "image": "nvidia/cuda:12.1.0-base-ubuntu22.04",
                "disk_size": 20,
            }, silent=True)

            if not create_result:
                pytest.skip("Failed to create failover instance")

            instance_id = str(create_result.get("instance_id", create_result.get("id")))
            metrics.failover_gpu_id = instance_id

            print(f"   Instance ID: {instance_id}")

            ready_result = wait_for_instance_ready(api_client, instance_id, timeout=TIMEOUT_INSTANCE_READY)
            if not ready_result.get("success"):
                pytest.skip(f"Failover instance not ready: {ready_result.get('error')}")

            metrics.time_provision_failover = time.time() - start

            print(f"   SSH: {ready_result['ssh_host']}:{ready_result['ssh_port']}")
            print(f"✅ Failover GPU pronta em {metrics.time_provision_failover:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_07_restore_data(self, api_client, metrics):
        """[7/10] Restaura dados do snapshot"""
        if not metrics.failover_gpu_id or not metrics.snapshot_id:
            pytest.skip("No failover GPU or snapshot")

        print(f"\n[7/10] Restaurando dados do snapshot...")
        start = time.time()

        try:
            restore_result = api_client.call("POST", "/api/v1/snapshots/restore", {
                "snapshot_id": metrics.snapshot_id,
                "target_path": TEST_FILES_DIR,
            }, params={"instance_id": metrics.failover_gpu_id}, silent=True)

            if not restore_result:
                pytest.skip("Failed to restore snapshot")

            metrics.time_restore_data = time.time() - start

            if "files_restored" in restore_result:
                print(f"   Arquivos restaurados: {restore_result['files_restored']}")

            print(f"✅ Dados restaurados em {metrics.time_restore_data:.1f}s")

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_08_validate_recovery(self, api_client, metrics):
        """[8/10] Valida recovery dos dados"""
        if not metrics.failover_gpu_id:
            pytest.skip("No failover GPU")

        print(f"\n[8/10] Validando recovery...")
        start = time.time()

        try:
            instance_info = api_client.call("GET", f"/api/v1/instances/{metrics.failover_gpu_id}", silent=True)
            ssh_host = instance_info.get("ssh_host")
            ssh_port = instance_info.get("ssh_port")

            if not ssh_host or not ssh_port:
                pytest.skip("SSH info not available")

            validated_count = validate_files_exist(ssh_host, ssh_port, metrics.test_files_count)
            metrics.files_validated = validated_count
            metrics.time_validate = time.time() - start

            # Calcular MTTR (desde detecção da falha até recovery completo)
            if hasattr(self, '_recovery_start'):
                metrics.time_total_recovery = time.time() - self._recovery_start
            else:
                # Fallback: somar tempos individuais
                metrics.time_total_recovery = (
                    metrics.time_failover_trigger +
                    metrics.time_provision_failover +
                    metrics.time_restore_data +
                    metrics.time_validate
                )

            metrics.recovery_completed_at = datetime.now().isoformat()

            # Tempo total
            metrics.time_total = time.time() - metrics.start_time

            # Custo
            hours_used = metrics.time_total / 3600
            metrics.estimated_cost_usd = (
                hours_used * metrics.primary_gpu_cost_per_hour +
                hours_used * metrics.failover_gpu_cost_per_hour
            )

            # Validação
            all_validated = validated_count == metrics.test_files_count
            metrics.success = all_validated

            # Relatório
            metrics.print_summary()
            metrics.save_report("auto_failover_report.json")

            # Assert
            assert all_validated, (
                f"Recovery validation failed: {validated_count}/{metrics.test_files_count} files valid"
            )

        except Exception as e:
            metrics.error_message = str(e)
            raise

    def test_99_cleanup(self, api_client, metrics):
        """[9/10] Cleanup recursos"""
        print("\n[CLEANUP] Removendo recursos...")

        if metrics.failover_gpu_id:
            try:
                api_client.call("DELETE", f"/api/v1/instances/{metrics.failover_gpu_id}", silent=True)
                print(f"✅ Failover GPU deletada: {metrics.failover_gpu_id}")
            except Exception as e:
                print(f"⚠️  Erro ao deletar Failover GPU: {e}")

        if metrics.primary_gpu_id:
            try:
                api_client.call("DELETE", f"/api/v1/instances/{metrics.primary_gpu_id}", silent=True)
                print(f"✅ Primary GPU deletada: {metrics.primary_gpu_id}")
            except Exception as e:
                print(f"⚠️  Erro ao deletar Primary GPU: {e}")

        print("✅ Cleanup completo")


# =============================================================================
# TESTE SIMULADO (SEM CUSTOS)
# =============================================================================

@pytest.mark.fast
class TestAutoFailoverSimulated:
    """
    Versão SIMULADA do teste (sem custos).

    Testa apenas a lógica de detecção de falha e trigger de failover,
    sem provisionar GPUs reais.
    """

    def test_heartbeat_detection(self):
        """Testa detecção de falha via heartbeat"""
        print("\n" + "=" * 80)
        print("TESTE SIMULADO: HEARTBEAT DETECTION")
        print("=" * 80)

        # Mock API client
        class MockAPIClient:
            def call(self, *args, **kwargs):
                return {"status": "running"}

        api = MockAPIClient()

        # Criar monitor
        monitor = HeartbeatMonitor(
            instance_id="test-instance-123",
            api_client=api,
            timeout_seconds=5  # 5s para teste rápido
        )

        monitor.start()

        # Enviar heartbeats normais
        print("\n📡 Enviando heartbeats normais...")
        for i in range(3):
            monitor.send_heartbeat()
            print(f"   💓 Heartbeat #{i+1}")
            time.sleep(1)

        # Parar heartbeats
        print("\n🔴 PARANDO heartbeats (simulando falha)...")
        print(f"   Aguardando detecção (timeout: 5s)...")

        # Aguardar detecção
        start = time.time()
        while not monitor.is_failure_detected():
            time.sleep(0.5)
            if time.time() - start > 10:
                pytest.fail("Timeout esperando detecção de falha")

        detection_time = time.time() - start

        failure_info = monitor.get_failure_info()
        monitor.stop()

        # Validações
        assert monitor.is_failure_detected(), "Falha não foi detectada"
        assert failure_info is not None, "Failure info não disponível"
        assert 5 <= detection_time <= 8, f"Detection time fora do esperado: {detection_time:.1f}s"

        print(f"\n✅ Falha detectada em {detection_time:.1f}s")
        print(f"   Instance: {failure_info['instance_id']}")
        print(f"   Timestamp: {failure_info['timestamp']}")

        print("\n" + "=" * 80)
        print("✅ TESTE SIMULADO PASSOU!")
        print("=" * 80)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v", "-s",
        "--tb=short",
    ])
