"""
Cloud Storage Failover - Failover usando armazenamento na nuvem (Backblaze B2, R2, S3).

Estrategia de failover que usa armazenamento em nuvem em vez de volumes VAST.ai.
Permite failover GLOBAL - pode mover para qualquer regiao do mundo.

Opcoes de montagem:
1. rclone mount - Monta bucket como filesystem (requer FUSE)
2. restic restore - Restaura snapshot mais recente
3. s3fs/goofys - Monta via S3 API (B2 compativel)

Tempo de recuperacao estimado: ~30-120 segundos
- Depende do tamanho dos dados
- rclone mount: acesso imediato, download on-demand
- restic restore: download completo, mais lento mas mais confiavel
"""
import logging
import asyncio
import time
import subprocess
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import aiohttp

from .host_finder import HostFinder, GPUOffer

logger = logging.getLogger(__name__)


class CloudStorageType(str, Enum):
    """Tipos de armazenamento em nuvem suportados"""
    BACKBLAZE_B2 = "b2"
    CLOUDFLARE_R2 = "r2"
    AWS_S3 = "s3"


class MountMethod(str, Enum):
    """Metodos de montagem do storage"""
    RCLONE = "rclone"      # rclone mount - acesso on-demand
    RESTIC = "restic"      # restic restore - download completo
    S3FS = "s3fs"          # s3fs-fuse - S3 API


@dataclass
class CloudStorageConfig:
    """Configuracao do armazenamento em nuvem"""
    storage_type: CloudStorageType = CloudStorageType.BACKBLAZE_B2
    bucket_name: str = ""
    endpoint: str = ""  # Ex: s3.us-west-000.backblazeb2.com
    access_key: str = ""
    secret_key: str = ""
    # Para Restic
    restic_repo: str = ""
    restic_password: str = ""
    # Opcoes
    mount_method: MountMethod = MountMethod.RCLONE
    mount_path: str = "/data"
    cache_dir: str = "/tmp/rclone-cache"
    cache_size_gb: int = 10


@dataclass
class CloudFailoverResult:
    """Resultado de um failover com cloud storage"""
    success: bool
    storage_type: str
    mount_method: str
    old_instance_id: Optional[int] = None
    new_instance_id: Optional[int] = None
    new_gpu_name: Optional[str] = None
    region: Optional[str] = None
    failover_time_seconds: float = 0.0
    data_sync_time_seconds: float = 0.0
    message: str = ""
    error: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None


class CloudStorageFailover:
    """
    Gerencia failover usando armazenamento em nuvem.

    Vantagens sobre Regional Volume Failover:
    - Failover GLOBAL (qualquer regiao do mundo)
    - Dados persistem independente do VAST.ai
    - Mais opcoes de precos de GPUs
    - Backup automatico (com restic)

    Desvantagens:
    - Latencia de rede para acessar dados
    - Precisa de configuracao de credenciais
    """

    def __init__(
        self,
        vast_api_key: str,
        storage_config: CloudStorageConfig,
    ):
        self.api_key = vast_api_key
        self.api_url = "https://cloud.vast.ai/api/v0"
        self.storage = storage_config
        self.host_finder = HostFinder(vast_api_key)

    def _get_rclone_remote_config(self) -> str:
        """Gera configuracao do rclone para o storage"""
        if self.storage.storage_type == CloudStorageType.BACKBLAZE_B2:
            return f'''
[b2remote]
type = b2
account = {self.storage.access_key}
key = {self.storage.secret_key}
'''
        elif self.storage.storage_type == CloudStorageType.CLOUDFLARE_R2:
            return f'''
[r2remote]
type = s3
provider = Cloudflare
access_key_id = {self.storage.access_key}
secret_access_key = {self.storage.secret_key}
endpoint = {self.storage.endpoint}
'''
        else:  # AWS S3
            return f'''
[s3remote]
type = s3
provider = AWS
access_key_id = {self.storage.access_key}
secret_access_key = {self.storage.secret_key}
region = us-east-1
'''

    def _get_remote_name(self) -> str:
        """Retorna o nome do remote do rclone"""
        if self.storage.storage_type == CloudStorageType.BACKBLAZE_B2:
            return "b2remote"
        elif self.storage.storage_type == CloudStorageType.CLOUDFLARE_R2:
            return "r2remote"
        else:
            return "s3remote"

    def _get_mount_script(self) -> str:
        """Gera script para montar o storage na GPU"""
        remote = self._get_remote_name()
        mount_path = self.storage.mount_path
        cache_dir = self.storage.cache_dir
        cache_size = self.storage.cache_size_gb
        bucket = self.storage.bucket_name

        if self.storage.mount_method == MountMethod.RCLONE:
            # rclone mount com cache VFS para performance
            return f'''#!/bin/bash
set -e
echo "=== Instalando rclone ==="
if ! command -v rclone &> /dev/null; then
    curl -s https://rclone.org/install.sh | bash
fi

echo "=== Configurando rclone ==="
mkdir -p ~/.config/rclone
cat > ~/.config/rclone/rclone.conf << 'RCLONE_CONFIG'
{self._get_rclone_remote_config()}
RCLONE_CONFIG

echo "=== Montando {bucket} em {mount_path} ==="
mkdir -p {mount_path}
mkdir -p {cache_dir}

# Desmontar se ja estiver montado
fusermount -u {mount_path} 2>/dev/null || true

# Montar com cache VFS para melhor performance
rclone mount {remote}:{bucket} {mount_path} \\
    --vfs-cache-mode full \\
    --vfs-cache-max-size {cache_size}G \\
    --vfs-cache-max-age 24h \\
    --cache-dir {cache_dir} \\
    --dir-cache-time 30s \\
    --poll-interval 30s \\
    --buffer-size 128M \\
    --vfs-read-chunk-size 64M \\
    --vfs-read-chunk-size-limit 256M \\
    --transfers 16 \\
    --daemon

sleep 3
if mountpoint -q {mount_path}; then
    echo "MOUNT_SUCCESS"
    ls -la {mount_path}/
else
    echo "MOUNT_FAILED"
    exit 1
fi
'''

        elif self.storage.mount_method == MountMethod.RESTIC:
            # restic restore - download completo do ultimo snapshot
            restic_repo = self.storage.restic_repo
            restic_pass = self.storage.restic_password
            access_key = self.storage.access_key
            secret_key = self.storage.secret_key

            return f'''#!/bin/bash
set -e
echo "=== Instalando restic ==="
if ! command -v restic &> /dev/null; then
    wget -q https://github.com/restic/restic/releases/download/v0.17.3/restic_0.17.3_linux_amd64.bz2 -O /tmp/restic.bz2
    bunzip2 -f /tmp/restic.bz2
    chmod +x /tmp/restic
    mv /tmp/restic /usr/local/bin/restic
fi

echo "=== Configurando credenciais ==="
export AWS_ACCESS_KEY_ID="{access_key}"
export AWS_SECRET_ACCESS_KEY="{secret_key}"
export RESTIC_REPOSITORY="{restic_repo}"
export RESTIC_PASSWORD="{restic_pass}"

echo "=== Restaurando ultimo snapshot para {mount_path} ==="
mkdir -p {mount_path}

# Pegar ID do ultimo snapshot
LATEST=$(restic snapshots --json | python3 -c "import sys,json; snaps=json.load(sys.stdin); print(snaps[-1]['id'] if snaps else '')" 2>/dev/null || echo "")

if [ -z "$LATEST" ]; then
    echo "Nenhum snapshot encontrado, iniciando vazio"
    echo "RESTORE_EMPTY"
    exit 0
fi

echo "Restaurando snapshot $LATEST..."
restic restore $LATEST --target {mount_path} -o s3.connections=32

echo "RESTORE_SUCCESS"
du -sh {mount_path}/* 2>/dev/null | head -5
'''

        else:  # S3FS
            access_key = self.storage.access_key
            secret_key = self.storage.secret_key
            endpoint = self.storage.endpoint
            bucket = self.storage.bucket_name

            return f'''#!/bin/bash
set -e
echo "=== Instalando s3fs ==="
if ! command -v s3fs &> /dev/null; then
    apt-get update && apt-get install -y s3fs
fi

echo "=== Configurando credenciais ==="
echo "{access_key}:{secret_key}" > ~/.passwd-s3fs
chmod 600 ~/.passwd-s3fs

echo "=== Montando {bucket} em {mount_path} ==="
mkdir -p {mount_path}

# Desmontar se ja estiver montado
fusermount -u {mount_path} 2>/dev/null || true

s3fs {bucket} {mount_path} \\
    -o passwd_file=~/.passwd-s3fs \\
    -o url=https://{endpoint} \\
    -o use_path_request_style \\
    -o allow_other

if mountpoint -q {mount_path}; then
    echo "MOUNT_SUCCESS"
    ls -la {mount_path}/
else
    echo "MOUNT_FAILED"
    exit 1
fi
'''

    async def find_cheapest_gpu(
        self,
        preferred_gpus: Optional[List[str]] = None,
        max_price: Optional[float] = None,
        min_reliability: float = 0.90,
        exclude_regions: Optional[List[str]] = None,
    ) -> Optional[GPUOffer]:
        """
        Busca a GPU mais barata em qualquer regiao.

        Com cloud storage, nao precisamos ficar na mesma regiao!
        """
        try:
            all_offers = await self.host_finder.search_offers(
                min_gpus=1,
                max_price=max_price or 1.0,
                verified=False,
                min_reliability=min_reliability,
            )

            if exclude_regions:
                exclude_upper = [r.upper() for r in exclude_regions]
                all_offers = [
                    o for o in all_offers
                    if not any(r in o.geolocation.upper() for r in exclude_upper)
                ]

            if not all_offers:
                return None

            # Filtrar por GPUs preferidas
            gpu_names = preferred_gpus or ["RTX_4090", "RTX_3090", "RTX_4080", "RTX_5090", "A100"]

            for gpu_name in gpu_names:
                matching = [o for o in all_offers if gpu_name in o.gpu_name]
                if matching:
                    matching.sort(key=lambda o: o.price_per_hour)
                    return matching[0]

            # Se nao achou preferida, retorna a mais barata
            all_offers.sort(key=lambda o: o.price_per_hour)
            return all_offers[0]

        except Exception as e:
            logger.error(f"Failed to find GPU: {e}")
            return None

    async def provision_gpu_with_cloud_storage(
        self,
        offer_id: int,
        docker_image: str = "pytorch/pytorch:latest",
        use_spot: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Provisiona uma GPU e configura montagem do cloud storage.
        """
        try:
            mount_script = self._get_mount_script()

            # Escapar aspas simples no script para o onstart
            mount_script_escaped = mount_script.replace("'", "'\\''")

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                # Criar script de setup
                onstart_script = f'''
mkdir -p /opt/dumont
cat > /opt/dumont/mount-storage.sh << 'MOUNTSCRIPT'
{mount_script}
MOUNTSCRIPT
chmod +x /opt/dumont/mount-storage.sh
/opt/dumont/mount-storage.sh > /var/log/mount-storage.log 2>&1 &
'''

                payload = {
                    "client_id": "me",
                    "image": docker_image,
                    "disk": 20,
                    "runtype": "ssh",
                    "onstart": "echo 'GPU started' > /tmp/gpu-ready.txt",
                }

                async with session.put(
                    f"{self.api_url}/asks/{offer_id}/",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status not in [200, 201]:
                        text = await response.text()
                        logger.error(f"Failed to provision GPU: {response.status} - {text}")
                        return None

                    data = await response.json()
                    instance_id = data.get("new_contract")

                    return {
                        "instance_id": instance_id,
                        "mount_script": mount_script,
                    }

        except Exception as e:
            logger.error(f"Failed to provision GPU: {e}")
            return None

    async def wait_for_instance_ready(
        self,
        instance_id: int,
        timeout_seconds: int = 180
    ) -> Optional[Dict[str, Any]]:
        """Aguarda uma instancia ficar pronta."""
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }

                    async with session.get(
                        f"{self.api_url}/instances/{instance_id}/",
                        headers=headers
                    ) as response:
                        if response.status != 200:
                            await asyncio.sleep(5)
                            continue

                        data = await response.json()
                        status = data.get("actual_status", "")

                        if status == "running":
                            return {
                                "instance_id": instance_id,
                                "status": status,
                                "ssh_host": data.get("ssh_host"),
                                "ssh_port": data.get("ssh_port"),
                                "gpu_name": data.get("gpu_name"),
                                "geolocation": data.get("geolocation"),
                            }

            except Exception as e:
                logger.warning(f"Error checking instance: {e}")

            await asyncio.sleep(5)

        return None

    async def setup_cloud_storage_on_instance(
        self,
        ssh_host: str,
        ssh_port: int,
        timeout_seconds: int = 120,
    ) -> bool:
        """
        Configura o cloud storage em uma instancia via SSH.
        """
        mount_script = self._get_mount_script()

        try:
            # Executar script via SSH
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=30",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    mount_script,
                ],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )

            success = (
                "MOUNT_SUCCESS" in result.stdout or
                "RESTORE_SUCCESS" in result.stdout or
                "RESTORE_EMPTY" in result.stdout
            )

            if success:
                logger.info(f"Cloud storage mounted successfully on {ssh_host}")
            else:
                logger.error(f"Mount failed: {result.stdout} {result.stderr}")

            return success

        except subprocess.TimeoutExpired:
            logger.error("Timeout setting up cloud storage")
            return False
        except Exception as e:
            logger.error(f"Failed to setup cloud storage: {e}")
            return False

    async def execute_failover(
        self,
        old_instance_id: Optional[int] = None,
        preferred_gpus: Optional[List[str]] = None,
        max_price: Optional[float] = None,
        docker_image: str = "pytorch/pytorch:latest",
        timeout_seconds: int = 180,
    ) -> CloudFailoverResult:
        """
        Executa failover para nova GPU com cloud storage.

        1. Busca GPU mais barata (qualquer regiao)
        2. Provisiona GPU
        3. Monta cloud storage
        4. Destroi instancia antiga
        """
        start_time = time.time()

        try:
            # 1. Buscar GPU
            gpu_offer = await self.find_cheapest_gpu(
                preferred_gpus=preferred_gpus,
                max_price=max_price,
            )

            if not gpu_offer:
                return CloudFailoverResult(
                    success=False,
                    storage_type=self.storage.storage_type.value,
                    mount_method=self.storage.mount_method.value,
                    old_instance_id=old_instance_id,
                    error="No GPU available",
                )

            logger.info(f"Found GPU: {gpu_offer.gpu_name} at ${gpu_offer.price_per_hour}/hr in {gpu_offer.geolocation}")

            # 2. Provisionar GPU
            provision_result = await self.provision_gpu_with_cloud_storage(
                offer_id=gpu_offer.offer_id,
                docker_image=docker_image,
            )

            if not provision_result:
                return CloudFailoverResult(
                    success=False,
                    storage_type=self.storage.storage_type.value,
                    mount_method=self.storage.mount_method.value,
                    old_instance_id=old_instance_id,
                    error="Failed to provision GPU",
                )

            new_instance_id = provision_result["instance_id"]

            # 3. Aguardar instancia ficar pronta
            instance_info = await self.wait_for_instance_ready(
                instance_id=new_instance_id,
                timeout_seconds=timeout_seconds,
            )

            if not instance_info:
                return CloudFailoverResult(
                    success=False,
                    storage_type=self.storage.storage_type.value,
                    mount_method=self.storage.mount_method.value,
                    old_instance_id=old_instance_id,
                    new_instance_id=new_instance_id,
                    error="Timeout waiting for instance",
                )

            gpu_ready_time = time.time() - start_time

            # 4. Configurar cloud storage
            data_sync_start = time.time()
            storage_ok = await self.setup_cloud_storage_on_instance(
                ssh_host=instance_info["ssh_host"],
                ssh_port=instance_info["ssh_port"],
            )
            data_sync_time = time.time() - data_sync_start

            if not storage_ok:
                return CloudFailoverResult(
                    success=False,
                    storage_type=self.storage.storage_type.value,
                    mount_method=self.storage.mount_method.value,
                    old_instance_id=old_instance_id,
                    new_instance_id=new_instance_id,
                    ssh_host=instance_info["ssh_host"],
                    ssh_port=instance_info["ssh_port"],
                    error="Failed to mount cloud storage",
                )

            # 5. Destruir instancia antiga
            if old_instance_id:
                await self._destroy_instance(old_instance_id)

            total_time = time.time() - start_time

            return CloudFailoverResult(
                success=True,
                storage_type=self.storage.storage_type.value,
                mount_method=self.storage.mount_method.value,
                old_instance_id=old_instance_id,
                new_instance_id=new_instance_id,
                new_gpu_name=instance_info.get("gpu_name"),
                region=instance_info.get("geolocation"),
                failover_time_seconds=total_time,
                data_sync_time_seconds=data_sync_time,
                message=f"Failover completed in {total_time:.1f}s (GPU: {gpu_ready_time:.1f}s, Storage: {data_sync_time:.1f}s)",
                ssh_host=instance_info["ssh_host"],
                ssh_port=instance_info["ssh_port"],
            )

        except Exception as e:
            logger.error(f"Failover failed: {e}")
            return CloudFailoverResult(
                success=False,
                storage_type=self.storage.storage_type.value,
                mount_method=self.storage.mount_method.value,
                old_instance_id=old_instance_id,
                failover_time_seconds=time.time() - start_time,
                error=str(e),
            )

    async def _destroy_instance(self, instance_id: int) -> bool:
        """Destroi uma instancia"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.delete(
                    f"{self.api_url}/instances/{instance_id}/",
                    headers=headers
                ) as response:
                    return response.status in [200, 204]

        except Exception as e:
            logger.error(f"Failed to destroy instance: {e}")
            return False


# Factory functions
def create_b2_failover(
    vast_api_key: str,
    b2_key_id: str,
    b2_app_key: str,
    bucket_name: str,
    restic_repo: Optional[str] = None,
    restic_password: Optional[str] = None,
    mount_method: MountMethod = MountMethod.RCLONE,
    mount_path: str = "/data",
) -> CloudStorageFailover:
    """
    Cria um CloudStorageFailover configurado para Backblaze B2.

    Args:
        vast_api_key: API key do VAST.ai
        b2_key_id: Backblaze B2 Key ID
        b2_app_key: Backblaze B2 Application Key
        bucket_name: Nome do bucket B2
        restic_repo: Repositorio restic (se usar mount_method=RESTIC)
        restic_password: Senha do restic
        mount_method: Metodo de montagem (RCLONE, RESTIC, S3FS)
        mount_path: Caminho onde montar o storage
    """
    config = CloudStorageConfig(
        storage_type=CloudStorageType.BACKBLAZE_B2,
        bucket_name=bucket_name,
        access_key=b2_key_id,
        secret_key=b2_app_key,
        restic_repo=restic_repo or "",
        restic_password=restic_password or "",
        mount_method=mount_method,
        mount_path=mount_path,
    )

    return CloudStorageFailover(vast_api_key, config)


def create_r2_failover(
    vast_api_key: str,
    r2_access_key: str,
    r2_secret_key: str,
    r2_endpoint: str,
    bucket_name: str,
    mount_path: str = "/data",
) -> CloudStorageFailover:
    """
    Cria um CloudStorageFailover configurado para Cloudflare R2.
    """
    config = CloudStorageConfig(
        storage_type=CloudStorageType.CLOUDFLARE_R2,
        bucket_name=bucket_name,
        endpoint=r2_endpoint,
        access_key=r2_access_key,
        secret_key=r2_secret_key,
        mount_method=MountMethod.RCLONE,
        mount_path=mount_path,
    )

    return CloudStorageFailover(vast_api_key, config)
