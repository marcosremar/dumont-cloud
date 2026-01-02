"""
Test 1.1: B2 Snapshot Upload - Phase 1 Failover Tests

ATENÇÃO: Este teste USA CRÉDITOS REAIS da VAST.ai e armazena dados no B2!

Passos:
1. Provisionar RTX 4090 (mais barata disponível)
2. Criar arquivos de teste (100 MB total)
3. Calcular MD5 checksums
4. Criar snapshot tar.gz
5. Upload para B2 bucket
6. Verificar upload com sucesso
7. Destruir GPU
8. Salvar relatório JSON com métricas

Para rodar:
    cd /Users/marcos/CascadeProjects/dumontcloud
    source venv/bin/activate
    pytest cli/tests/test_b2_snapshot.py -v -s --tb=short
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
INSTANCE_READY_TIMEOUT = 900  # 15 min para instância ficar running
SSH_READY_TIMEOUT = 300       # 5 min para SSH ficar pronto
FILE_CREATE_TIMEOUT = 600     # 10 min para criar arquivos
SNAPSHOT_CREATE_TIMEOUT = 600 # 10 min para criar snapshot
UPLOAD_TIMEOUT = 900          # 15 min para upload

# Rate limiting
RATE_LIMIT_INITIAL_DELAY = 3
RATE_LIMIT_MAX_RETRIES = 10
DELAY_POLL_STATUS = 10


# ============================================================
# Métricas
# ============================================================

@dataclass
class SnapshotMetrics:
    """Métricas do teste de snapshot"""
    test_name: str = "B2_Snapshot_Upload"
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
    time_to_provision: float = 0
    time_to_ssh_ready: float = 0
    time_to_create_files: float = 0
    time_to_create_snapshot: float = 0
    time_to_upload_b2: float = 0
    time_to_destroy: float = 0

    # Checksums
    file_checksums: Dict[str, str] = None

    # Status
    success: bool = False
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.file_checksums is None:
            self.file_checksums = {}

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
# Helper Functions
# ============================================================

def call_with_retry(func, max_retries=RATE_LIMIT_MAX_RETRIES):
    """Call function with exponential backoff on 429 errors"""
    delay = RATE_LIMIT_INITIAL_DELAY
    for attempt in range(max_retries):
        try:
            result = func()
            # Check for rate limit in response
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


def get_headers(token: str) -> Dict[str, str]:
    """Retorna headers com autenticação"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def search_cheapest_rtx4090(token: str) -> Optional[Dict[str, Any]]:
    """Busca a oferta mais barata de RTX 4090 na VAST.ai"""
    print("\n🔍 Buscando ofertas RTX 4090 na VAST.ai...")

    headers = {"Authorization": f"Bearer {VAST_API_KEY}"}

    # Query para buscar RTX 4090 on-demand
    query = {
        "rentable": {"eq": True},
        "gpu_name": {"eq": "RTX 4090"},
        "num_gpus": {"eq": 1},
        "disk_space": {"gte": 50},
        "verified": {"eq": True}
    }

    params = {
        "q": json.dumps(query),
        "order": "dph_total",  # Ordenar por preço
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

    result = call_with_retry(search)

    # A resposta pode ser {"offers": [...]} ou lista direta
    if isinstance(result, dict) and "offers" in result:
        offers = result["offers"]
    elif isinstance(result, list):
        offers = result
    else:
        print(f"❌ Resposta inesperada: {type(result)}")
        return None

    if not offers:
        print("❌ Nenhuma oferta encontrada!")
        return None

    # Filtrar ofertas disponíveis
    available = [o for o in offers if o.get("rentable", False)]

    if not available:
        print("❌ Nenhuma oferta disponível no momento!")
        return None

    cheapest = available[0]
    print(f"✅ Oferta encontrada:")
    print(f"   ID: {cheapest['id']}")
    print(f"   GPU: {cheapest['gpu_name']} x{cheapest['num_gpus']}")
    print(f"   Preço: ${cheapest['dph_total']:.4f}/hora")
    print(f"   Localização: {cheapest.get('geolocation', 'N/A')}")

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

        # Encontrar nossa instância
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
                password="",  # VAST usa key-based auth
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


def create_test_files(ssh: paramiko.SSHClient) -> Dict[str, str]:
    """Cria arquivos de teste na GPU e retorna checksums"""
    print(f"\n📝 Criando arquivos de teste...")

    # Criar diretório de trabalho
    sftp = ssh.open_sftp()
    work_dir = "/tmp/snapshot_test"

    exec_command(ssh, f"mkdir -p {work_dir}/data/subdir")

    checksums = {}

    # 1. Criar 10 arquivos de texto (5MB cada = 50MB total)
    print("   Criando arquivos de texto...")
    for i in range(10):
        filename = f"{work_dir}/data/text_{i:02d}.txt"
        content = f"Test file {i}\n" * (5 * 1024 * 1024 // 15)  # ~5MB

        # Upload via SFTP
        with sftp.open(filename, 'w') as f:
            f.write(content)

        # Calcular checksum
        checksum = exec_command(ssh, f"md5sum {filename} | awk '{{print $1}}'").strip()
        checksums[f"text_{i:02d}.txt"] = checksum

    # 2. Criar 5 arquivos binários (10MB cada = 50MB total)
    print("   Criando arquivos binários...")
    for i in range(5):
        filename = f"{work_dir}/data/binary_{i:02d}.bin"
        exec_command(ssh, f"dd if=/dev/urandom of={filename} bs=1M count=10 2>/dev/null")

        checksum = exec_command(ssh, f"md5sum {filename} | awk '{{print $1}}'").strip()
        checksums[f"binary_{i:02d}.bin"] = checksum

    # 3. Criar estrutura aninhada
    print("   Criando estrutura de diretórios...")
    exec_command(ssh, f"mkdir -p {work_dir}/data/subdir/deep")

    nested_file = f"{work_dir}/data/subdir/deep/nested.txt"
    exec_command(ssh, f"echo 'Nested file content' > {nested_file}")
    checksum = exec_command(ssh, f"md5sum {nested_file} | awk '{{print $1}}'").strip()
    checksums["subdir/deep/nested.txt"] = checksum

    sftp.close()

    print(f"✅ {len(checksums)} arquivos criados (total ~100MB)")
    return checksums


def exec_command(ssh: paramiko.SSHClient, command: str) -> str:
    """Executa comando SSH e retorna output"""
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    if exit_code != 0:
        raise Exception(f"Command failed: {command}\nError: {error}")

    return output


def create_snapshot(ssh: paramiko.SSHClient) -> str:
    """Cria snapshot tar.gz e retorna o caminho"""
    print(f"\n📦 Criando snapshot tar.gz...")

    snapshot_name = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
    snapshot_path = f"/tmp/{snapshot_name}"

    exec_command(
        ssh,
        f"tar -czf {snapshot_path} -C /tmp/snapshot_test/data ."
    )

    # Verificar tamanho
    size_output = exec_command(ssh, f"ls -lh {snapshot_path}")
    print(f"   {size_output.strip()}")

    # Obter tamanho em MB
    size_bytes = int(exec_command(ssh, f"stat -c%s {snapshot_path}").strip())
    size_mb = size_bytes / (1024 * 1024)

    print(f"✅ Snapshot criado: {snapshot_name} ({size_mb:.2f} MB)")

    return snapshot_path, snapshot_name, size_mb


def download_snapshot(ssh: paramiko.SSHClient, remote_path: str, local_path: str):
    """Download snapshot via SFTP"""
    print(f"\n⬇️  Downloading snapshot...")

    sftp = ssh.open_sftp()
    sftp.get(remote_path, local_path)
    sftp.close()

    print(f"✅ Download completo: {local_path}")


def upload_to_b2(local_file: str, b2_filename: str) -> Dict[str, Any]:
    """Upload arquivo para B2 e retorna informações"""
    print(f"\n☁️  Fazendo upload para B2...")
    print(f"   Bucket: {B2_BUCKET}")
    print(f"   Arquivo: {b2_filename}")

    # Inicializar B2 API
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_KEY_ID, B2_APPLICATION_KEY)

    # Obter bucket
    bucket = b2_api.get_bucket_by_name(B2_BUCKET)

    # Upload
    file_info = bucket.upload_local_file(
        local_file=local_file,
        file_name=b2_filename
    )

    print(f"✅ Upload completo!")
    print(f"   File ID: {file_info.id_}")
    print(f"   Size: {file_info.size / (1024*1024):.2f} MB")

    return {
        "file_id": file_info.id_,
        "file_name": file_info.file_name,
        "size": file_info.size,
        "upload_timestamp": file_info.upload_timestamp
    }


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
# Teste Principal
# ============================================================

@pytest.mark.real
def test_b2_snapshot_upload():
    """
    Test 1.1: B2 Snapshot Upload

    Provisiona GPU, cria arquivos de teste, faz snapshot e upload para B2.
    """
    metrics = SnapshotMetrics()
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
        print("TEST 1.1: B2 SNAPSHOT UPLOAD")
        print("=" * 70)

        # 1. Buscar oferta mais barata (usa VAST_API_KEY diretamente)
        start = time.time()
        offer = search_cheapest_rtx4090(None)  # Token não é mais necessário
        assert offer is not None, "Nenhuma oferta RTX 4090 disponível"

        metrics.gpu_name = f"{offer['gpu_name']} x{offer['num_gpus']}"
        metrics.gpu_cost_per_hour = offer['dph_total']

        # 2. Provisionar instância
        instance = provision_instance(None, offer['id'])  # Token não é mais necessário
        instance_id = instance['id']
        metrics.instance_id = str(instance_id)

        # 3. Aguardar running
        instance_info = wait_for_instance_running(instance_id)
        metrics.time_to_provision = time.time() - start

        # 4. Aguardar SSH
        start = time.time()
        ssh = wait_for_ssh_ready(instance_info)
        metrics.time_to_ssh_ready = time.time() - start

        # 5. Criar arquivos de teste
        start = time.time()
        checksums = create_test_files(ssh)
        metrics.time_to_create_files = time.time() - start
        metrics.file_checksums = checksums
        metrics.snapshot_files_count = len(checksums)

        # 6. Criar snapshot
        start = time.time()
        remote_snapshot, snapshot_name, size_mb = create_snapshot(ssh)
        metrics.time_to_create_snapshot = time.time() - start
        metrics.snapshot_name = snapshot_name
        metrics.snapshot_size_mb = size_mb

        # 7. Download snapshot
        local_snapshot = f"/tmp/{snapshot_name}"
        download_snapshot(ssh, remote_snapshot, local_snapshot)

        # 8. Upload para B2
        start = time.time()
        b2_info = upload_to_b2(local_snapshot, f"phase1-tests/{snapshot_name}")
        metrics.time_to_upload_b2 = time.time() - start

        # 9. Destruir instância
        start = time.time()
        destroy_instance(instance_id)
        metrics.time_to_destroy = time.time() - start
        instance_id = None  # Marcado como destruído

        # Sucesso!
        metrics.finish(success=True)

        print("\n" + "=" * 70)
        print("✅ TESTE COMPLETO COM SUCESSO!")
        print("=" * 70)
        print(f"Duração total: {metrics.duration_seconds/60:.1f} minutos")
        print(f"Custo estimado: ${metrics.total_instance_cost:.4f}")
        print(f"Snapshot: {snapshot_name} ({size_mb:.2f} MB)")
        print(f"Arquivos: {len(checksums)}")

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
        report_path = "/Users/marcos/CascadeProjects/dumontcloud/cli/tests/test_b2_snapshot_report.json"
        with open(report_path, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)

        print(f"\n📊 Relatório salvo: {report_path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
