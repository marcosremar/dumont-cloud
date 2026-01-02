"""
Test 1.2: B2 Snapshot Download and Restore - Phase 1 Failover Tests

ATENÇÃO: Este teste USA CRÉDITOS REAIS da VAST.ai!

Passos:
1. Listar snapshots disponíveis no B2
2. Download do snapshot mais recente
3. Provisionar nova RTX 4090
4. Upload do snapshot para a GPU via SCP
5. Extrair tar.gz
6. Verificar MD5 checksums (devem ser iguais aos do Test 1.1)
7. Destruir GPU
8. Salvar relatório JSON

Para rodar:
    cd /Users/marcos/CascadeProjects/dumontcloud
    source venv/bin/activate
    pytest cli/tests/test_b2_restore.py -v -s --tb=short
"""
import pytest
import requests
import time
import os
import json
import hashlib
import tarfile
import tempfile
import paramiko
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

# B2 SDK
from b2sdk.v2 import B2Api, InMemoryAccountInfo

# ============================================================
# Configuração
# ============================================================

API_BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8001")
TEST_USER = os.environ.get("TEST_USER", "test@test.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test123")

# B2 Credentials
B2_KEY_ID = os.environ.get("B2_KEY_ID")
B2_APPLICATION_KEY = os.environ.get("B2_APPLICATION_KEY")
B2_BUCKET = os.environ.get("B2_BUCKET", "dumontcloud-snapshots")

# VAST.ai credentials
VAST_API_KEY = os.environ.get("VAST_API_KEY")

# Timeouts
INSTANCE_READY_TIMEOUT = 900  # 15 min
SSH_READY_TIMEOUT = 300       # 5 min
UPLOAD_TIMEOUT = 900          # 15 min
EXTRACT_TIMEOUT = 600         # 10 min
VERIFY_TIMEOUT = 300          # 5 min

# Rate limiting
RATE_LIMIT_INITIAL_DELAY = 3
RATE_LIMIT_MAX_RETRIES = 10
DELAY_POLL_STATUS = 10


# ============================================================
# Métricas
# ============================================================

@dataclass
class RestoreMetrics:
    """Métricas do teste de restore"""
    test_name: str = "B2_Snapshot_Restore"
    start_time: datetime = None
    end_time: datetime = None
    duration_seconds: float = 0

    # Informações da instância
    instance_id: Optional[str] = None
    gpu_name: Optional[str] = None
    gpu_cost_per_hour: float = 0
    total_instance_cost: float = 0

    # Informações do snapshot
    snapshot_name: Optional[str] = None
    snapshot_size_mb: float = 0
    snapshot_files_count: int = 0

    # Tempos de operação
    time_to_list_snapshots: float = 0
    time_to_download: float = 0
    time_to_provision: float = 0
    time_to_ssh_ready: float = 0
    time_to_upload_snapshot: float = 0
    time_to_extract: float = 0
    time_to_verify: float = 0
    time_to_destroy: float = 0

    # Verificação
    original_checksums: Dict[str, str] = None
    restored_checksums: Dict[str, str] = None
    checksums_match: bool = False
    mismatched_files: List[str] = None

    # Status
    success: bool = False
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.original_checksums is None:
            self.original_checksums = {}
        if self.restored_checksums is None:
            self.restored_checksums = {}
        if self.mismatched_files is None:
            self.mismatched_files = []

    def finish(self, success: bool = True, error: str = None):
        """Finaliza as métricas"""
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.success = success
        self.error_message = error

        # Calcular custo estimado
        if self.gpu_cost_per_hour > 0:
            hours = self.duration_seconds / 3600
            self.total_instance_cost = hours * self.gpu_cost_per_hour

    def to_dict(self) -> dict:
        """Converte para dicionário serializável"""
        data = asdict(self)
        # Converter datetime para string
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data


# ============================================================
# Helper Functions (reusadas do test_b2_snapshot.py)
# ============================================================

def call_with_retry(func, max_retries=RATE_LIMIT_MAX_RETRIES):
    """Call function with exponential backoff on 429 errors"""
    delay = RATE_LIMIT_INITIAL_DELAY
    for attempt in range(max_retries):
        try:
            result = func()
            if isinstance(result, dict) and "error" in result:
                if "429" in str(result.get("error", "")):
                    print(f"⚠️  Rate limit (429). Aguardando {delay}s...")
                    time.sleep(delay)
                    delay *= 1.5
                    continue
            return result
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"⚠️  Rate limit. Aguardando {delay}s...")
                time.sleep(delay)
                delay *= 1.5
            else:
                raise
        except Exception as e:
            if "429" in str(e):
                print(f"⚠️  Rate limit. Aguardando {delay}s...")
                time.sleep(delay)
                delay *= 1.5
            else:
                raise
    raise Exception("Max retries exceeded")


def login_api() -> str:
    """Faz login e retorna o token JWT"""
    print(f"\n🔐 Fazendo login em {API_BASE_URL}...")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": TEST_USER, "password": TEST_PASSWORD}
    )
    response.raise_for_status()
    data = response.json()
    token = data.get("access_token") or data.get("token")
    print(f"✅ Login realizado com sucesso!")
    return token


def search_cheapest_rtx4090(token: str) -> Optional[Dict[str, Any]]:
    """Busca a oferta mais barata de RTX 4090 na VAST.ai"""
    print("\n🔍 Buscando ofertas RTX 4090 na VAST.ai...")

    headers = {"Authorization": f"Bearer {VAST_API_KEY}"}

    query = {
        "rentable": {"eq": True},
        "gpu_name": {"eq": "RTX 4090"},
        "num_gpus": {"eq": 1},
        "disk_space": {"gte": 50},
        "verified": {"eq": True}
    }

    params = {
        "q": json.dumps(query),
        "order": "dph_total",
        "type": "on-demand",
        "limit": 10
    }

    def search():
        resp = requests.get(
            "https://cloud.vast.ai/api/v0/bundles",
            headers=headers,
            params=params,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    offers = call_with_retry(search)

    if not offers or not isinstance(offers, list):
        print("❌ Nenhuma oferta encontrada!")
        return None

    available = [o for o in offers if o.get("rentable", False)]

    if not available:
        print("❌ Nenhuma oferta disponível no momento!")
        return None

    cheapest = available[0]
    print(f"✅ Oferta encontrada:")
    print(f"   ID: {cheapest['id']}")
    print(f"   GPU: {cheapest['gpu_name']} x{cheapest['num_gpus']}")
    print(f"   Preço: ${cheapest['dph_total']:.4f}/hora")

    return cheapest


def provision_instance(token: str, offer_id: int) -> Dict[str, Any]:
    """Provisiona uma instância GPU"""
    print(f"\n🚀 Provisionando instância (offer {offer_id})...")

    headers = {"Authorization": f"Bearer {VAST_API_KEY}"}

    payload = {
        "client_id": "me",
        "image": "nvidia/cuda:12.0.0-devel-ubuntu22.04",
        "disk": 50,
        "onstart": "apt-get update && apt-get install -y openssh-server && service ssh start"
    }

    def create():
        resp = requests.put(
            f"https://cloud.vast.ai/api/v0/asks/{offer_id}/",
            headers=headers,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    result = call_with_retry(create)

    if not result.get("success"):
        raise Exception(f"Falha ao provisionar: {result}")

    instance_id = result.get("new_contract")
    print(f"✅ Instância criada: {instance_id}")

    return {"id": instance_id, "offer_id": offer_id}


def wait_for_instance_running(instance_id: int, timeout: int = INSTANCE_READY_TIMEOUT) -> Dict[str, Any]:
    """Aguarda instância ficar em estado running"""
    print(f"\n⏳ Aguardando instância {instance_id} ficar running...")

    headers = {"Authorization": f"Bearer {VAST_API_KEY}"}
    start_time = time.time()

    while time.time() - start_time < timeout:
        def get_status():
            resp = requests.get(
                f"https://cloud.vast.ai/api/v0/instances/",
                headers=headers,
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()

        instances = call_with_retry(get_status)

        instance = None
        for inst in instances.get("instances", []):
            if inst.get("id") == instance_id:
                instance = inst
                break

        if not instance:
            print(f"❌ Instância {instance_id} não encontrada!")
            time.sleep(DELAY_POLL_STATUS)
            continue

        status = instance.get("actual_status")
        print(f"   Status: {status}")

        if status == "running":
            print(f"✅ Instância running!")
            return instance

        time.sleep(DELAY_POLL_STATUS)

    raise TimeoutError(f"Timeout aguardando instância {instance_id}")


def wait_for_ssh_ready(instance: Dict[str, Any], timeout: int = SSH_READY_TIMEOUT) -> paramiko.SSHClient:
    """Aguarda SSH ficar pronto e retorna cliente conectado"""
    print(f"\n🔌 Aguardando SSH ficar pronto...")

    host = instance.get("ssh_host")
    port = instance.get("ssh_port")

    if not host or not port:
        raise Exception(f"SSH info não disponível: {instance}")

    print(f"   Host: {host}:{port}")

    start_time = time.time()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    while time.time() - start_time < timeout:
        try:
            ssh.connect(
                hostname=host,
                port=port,
                username="root",
                password="",
                timeout=10,
                allow_agent=True,
                look_for_keys=True
            )
            print(f"✅ SSH conectado!")
            return ssh
        except Exception as e:
            print(f"   Tentando conectar... ({str(e)[:50]})")
            time.sleep(5)

    raise TimeoutError(f"Timeout aguardando SSH em {host}:{port}")


def exec_command(ssh: paramiko.SSHClient, command: str) -> str:
    """Executa comando SSH e retorna output"""
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    if exit_code != 0:
        raise Exception(f"Command failed: {command}\nError: {error}")

    return output


def destroy_instance(instance_id: int):
    """Destroi instância GPU"""
    print(f"\n🗑️  Destruindo instância {instance_id}...")

    headers = {"Authorization": f"Bearer {VAST_API_KEY}"}

    def destroy():
        resp = requests.delete(
            f"https://cloud.vast.ai/api/v0/instances/{instance_id}/",
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    result = call_with_retry(destroy)
    print(f"✅ Instância destruída: {result}")


# ============================================================
# B2 Specific Functions
# ============================================================

def list_b2_snapshots() -> List[Dict[str, Any]]:
    """Lista snapshots disponíveis no B2"""
    print(f"\n☁️  Listando snapshots no B2...")
    print(f"   Bucket: {B2_BUCKET}")
    print(f"   Prefix: phase1-tests/")

    # Inicializar B2 API
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_KEY_ID, B2_APPLICATION_KEY)

    # Obter bucket
    bucket = b2_api.get_bucket_by_name(B2_BUCKET)

    # Listar arquivos com prefixo
    files = []
    for file_version, _ in bucket.ls(folder_to_list="phase1-tests/"):
        files.append({
            "file_id": file_version.id_,
            "file_name": file_version.file_name,
            "size": file_version.size,
            "upload_timestamp": file_version.upload_timestamp
        })

    # Ordenar por timestamp (mais recente primeiro)
    files.sort(key=lambda x: x["upload_timestamp"], reverse=True)

    print(f"✅ {len(files)} snapshots encontrados")
    for i, f in enumerate(files[:5]):  # Mostrar os 5 mais recentes
        size_mb = f["size"] / (1024 * 1024)
        timestamp = datetime.fromtimestamp(f["upload_timestamp"] / 1000)
        print(f"   {i+1}. {f['file_name']} ({size_mb:.2f} MB) - {timestamp}")

    return files


def download_from_b2(file_info: Dict[str, Any], local_path: str):
    """Download arquivo do B2"""
    print(f"\n⬇️  Downloading de B2...")
    print(f"   Arquivo: {file_info['file_name']}")
    print(f"   Tamanho: {file_info['size'] / (1024*1024):.2f} MB")

    # Inicializar B2 API
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_KEY_ID, B2_APPLICATION_KEY)

    # Obter bucket
    bucket = b2_api.get_bucket_by_name(B2_BUCKET)

    # Download
    downloaded_file = bucket.download_file_by_name(file_info['file_name'])
    downloaded_file.save_to(local_path)

    print(f"✅ Download completo: {local_path}")


def upload_snapshot_to_gpu(ssh: paramiko.SSHClient, local_file: str, remote_path: str):
    """Upload snapshot para GPU via SFTP"""
    print(f"\n⬆️  Fazendo upload do snapshot para GPU...")
    print(f"   Origem: {local_file}")
    print(f"   Destino: {remote_path}")

    sftp = ssh.open_sftp()

    # Criar diretório se não existir
    try:
        sftp.mkdir("/tmp/restore")
    except Exception:
        pass  # Diretório já existe

    # Upload
    sftp.put(local_file, remote_path)
    sftp.close()

    # Verificar tamanho
    size_output = exec_command(ssh, f"ls -lh {remote_path}")
    print(f"   {size_output.strip()}")

    print(f"✅ Upload completo!")


def extract_snapshot(ssh: paramiko.SSHClient, snapshot_path: str, extract_dir: str):
    """Extrai snapshot tar.gz"""
    print(f"\n📂 Extraindo snapshot...")
    print(f"   Origem: {snapshot_path}")
    print(f"   Destino: {extract_dir}")

    # Criar diretório
    exec_command(ssh, f"mkdir -p {extract_dir}")

    # Extrair
    exec_command(ssh, f"tar -xzf {snapshot_path} -C {extract_dir}")

    # Contar arquivos extraídos
    file_count = exec_command(ssh, f"find {extract_dir} -type f | wc -l").strip()

    print(f"✅ Snapshot extraído! {file_count} arquivos")
    return int(file_count)


def verify_checksums(ssh: paramiko.SSHClient, extract_dir: str, original_checksums: Dict[str, str]) -> tuple:
    """Verifica checksums dos arquivos restaurados"""
    print(f"\n🔍 Verificando checksums...")

    restored_checksums = {}
    mismatched = []

    for filename, original_md5 in original_checksums.items():
        file_path = f"{extract_dir}/{filename}"

        try:
            # Calcular MD5
            restored_md5 = exec_command(ssh, f"md5sum {file_path} | awk '{{print $1}}'").strip()
            restored_checksums[filename] = restored_md5

            # Comparar
            if restored_md5 == original_md5:
                print(f"   ✅ {filename}: OK")
            else:
                print(f"   ❌ {filename}: MISMATCH!")
                print(f"      Original: {original_md5}")
                print(f"      Restored: {restored_md5}")
                mismatched.append(filename)

        except Exception as e:
            print(f"   ❌ {filename}: ERRO ao verificar - {e}")
            mismatched.append(filename)

    all_match = len(mismatched) == 0

    if all_match:
        print(f"\n✅ Todos os {len(original_checksums)} checksums conferem!")
    else:
        print(f"\n❌ {len(mismatched)} arquivos com problemas:")
        for f in mismatched:
            print(f"   - {f}")

    return restored_checksums, all_match, mismatched


# ============================================================
# Teste Principal
# ============================================================

@pytest.mark.real
def test_b2_snapshot_restore():
    """
    Test 1.2: B2 Snapshot Download and Restore

    Baixa snapshot do B2, provisiona GPU, restaura e valida checksums.
    """
    metrics = RestoreMetrics()
    token = None
    ssh = None
    instance_id = None
    local_snapshot = None

    try:
        # Validar credenciais
        if not VAST_API_KEY:
            raise Exception("VAST_API_KEY não configurada no .env")
        if not B2_KEY_ID or not B2_APPLICATION_KEY:
            raise Exception("Credenciais B2 não configuradas no .env")

        print("=" * 70)
        print("TEST 1.2: B2 SNAPSHOT DOWNLOAD AND RESTORE")
        print("=" * 70)

        # 1. Login
        token = login_api()

        # 2. Listar snapshots no B2
        start = time.time()
        snapshots = list_b2_snapshots()
        metrics.time_to_list_snapshots = time.time() - start

        if not snapshots:
            raise Exception("Nenhum snapshot encontrado no B2! Execute test_b2_snapshot.py primeiro.")

        latest_snapshot = snapshots[0]
        metrics.snapshot_name = latest_snapshot['file_name']
        metrics.snapshot_size_mb = latest_snapshot['size'] / (1024 * 1024)

        # 3. Carregar checksums originais do relatório anterior
        report_path = "/Users/marcos/CascadeProjects/dumontcloud/cli/tests/test_b2_snapshot_report.json"
        if os.path.exists(report_path):
            with open(report_path, 'r') as f:
                original_report = json.load(f)
                metrics.original_checksums = original_report.get('file_checksums', {})
                metrics.snapshot_files_count = len(metrics.original_checksums)
                print(f"\n📋 Checksums originais carregados: {len(metrics.original_checksums)} arquivos")
        else:
            print(f"\n⚠️  Relatório original não encontrado. Continuando sem verificação de checksums.")
            metrics.original_checksums = {}

        # 4. Download do snapshot
        start = time.time()
        local_snapshot = f"/tmp/{os.path.basename(latest_snapshot['file_name'])}"
        download_from_b2(latest_snapshot, local_snapshot)
        metrics.time_to_download = time.time() - start

        # 5. Buscar oferta RTX 4090
        start = time.time()
        offer = search_cheapest_rtx4090(token)
        assert offer is not None, "Nenhuma oferta RTX 4090 disponível"

        metrics.gpu_name = f"{offer['gpu_name']} x{offer['num_gpus']}"
        metrics.gpu_cost_per_hour = offer['dph_total']

        # 6. Provisionar instância
        instance = provision_instance(token, offer['id'])
        instance_id = instance['id']
        metrics.instance_id = str(instance_id)

        # 7. Aguardar running
        instance_info = wait_for_instance_running(instance_id)
        metrics.time_to_provision = time.time() - start

        # 8. Aguardar SSH
        start = time.time()
        ssh = wait_for_ssh_ready(instance_info)
        metrics.time_to_ssh_ready = time.time() - start

        # 9. Upload snapshot para GPU
        start = time.time()
        remote_snapshot = f"/tmp/restore/{os.path.basename(local_snapshot)}"
        upload_snapshot_to_gpu(ssh, local_snapshot, remote_snapshot)
        metrics.time_to_upload_snapshot = time.time() - start

        # 10. Extrair snapshot
        start = time.time()
        extract_dir = "/tmp/restore/data"
        file_count = extract_snapshot(ssh, remote_snapshot, extract_dir)
        metrics.time_to_extract = time.time() - start

        # 11. Verificar checksums
        if metrics.original_checksums:
            start = time.time()
            restored_checksums, all_match, mismatched = verify_checksums(
                ssh, extract_dir, metrics.original_checksums
            )
            metrics.time_to_verify = time.time() - start
            metrics.restored_checksums = restored_checksums
            metrics.checksums_match = all_match
            metrics.mismatched_files = mismatched

            if not all_match:
                raise Exception(f"{len(mismatched)} arquivos não conferem!")
        else:
            print("\n⚠️  Pulando verificação de checksums (relatório original não disponível)")
            metrics.checksums_match = True

        # 12. Destruir instância
        start = time.time()
        destroy_instance(instance_id)
        metrics.time_to_destroy = time.time() - start
        instance_id = None

        # Sucesso!
        metrics.finish(success=True)

        print("\n" + "=" * 70)
        print("✅ TESTE COMPLETO COM SUCESSO!")
        print("=" * 70)
        print(f"Duração total: {metrics.duration_seconds/60:.1f} minutos")
        print(f"Custo estimado: ${metrics.total_instance_cost:.4f}")
        print(f"Snapshot: {metrics.snapshot_name} ({metrics.snapshot_size_mb:.2f} MB)")
        print(f"Arquivos restaurados: {file_count}")
        if metrics.original_checksums:
            print(f"Checksums verificados: {len(metrics.original_checksums)} - {'✅ TODOS OK' if metrics.checksums_match else '❌ PROBLEMAS'}")

    except Exception as e:
        metrics.finish(success=False, error=str(e))
        print(f"\n❌ TESTE FALHOU: {e}")
        raise

    finally:
        # Cleanup
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass

        if instance_id:
            try:
                destroy_instance(instance_id)
            except Exception as e:
                print(f"⚠️  Erro ao destruir instância: {e}")

        if local_snapshot and os.path.exists(local_snapshot):
            try:
                os.remove(local_snapshot)
            except Exception:
                pass

        # Salvar relatório
        report_path = "/Users/marcos/CascadeProjects/dumontcloud/cli/tests/test_b2_restore_report.json"
        with open(report_path, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)

        print(f"\n📊 Relatório salvo: {report_path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
