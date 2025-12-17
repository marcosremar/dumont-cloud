"""
GPU Snapshot Service - Sistema de hibernação/restore de máquinas GPU
Usa ANS (GPU compression) + Cloudflare R2 com 32 partes paralelas
"""
import os
import time
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class GPUSnapshotService:
    """Serviço para criar e restaurar snapshots de workspaces GPU"""

    def __init__(self, r2_endpoint: str, r2_bucket: str):
        self.r2_endpoint = r2_endpoint
        self.r2_bucket = r2_bucket
        self.num_parts = 32  # Otimizado para 950 MB/s

    def create_snapshot(
        self,
        instance_id: str,
        ssh_host: str,
        ssh_port: int,
        workspace_path: str = "/workspace",
        snapshot_name: Optional[str] = None
    ) -> Dict:
        """
        Cria snapshot de uma máquina GPU (hibernar)

        Returns:
            {
                'snapshot_id': str,
                'size_original': int,
                'size_compressed': int,
                'compression_ratio': float,
                'upload_time': float,
                'parts': list
            }
        """
        if not snapshot_name:
            snapshot_name = f"{instance_id}_{int(time.time())}"

        logger.info(f"Criando snapshot {snapshot_name} para instância {instance_id}")

        start_time = time.time()

        # 1. Comprimir workspace com ANS (32 partes)
        logger.info("Comprimindo workspace com ANS (GPU)...")
        compress_script = self._generate_compress_script(workspace_path, self.num_parts)

        result = self._ssh_exec(ssh_host, ssh_port, compress_script)
        if result['returncode'] != 0:
            raise Exception(f"Erro na compressão: {result['stderr']}")

        # Parse do resultado
        compress_info = json.loads(result['stdout'])

        # 2. Upload das partes para R2
        logger.info(f"Upload de {self.num_parts} partes para R2...")
        upload_script = f"""
        s5cmd --numworkers {self.num_parts} --endpoint-url={self.r2_endpoint} \
            cp /tmp/snapshot_parts/*.ans s3://{self.r2_bucket}/snapshots/{snapshot_name}/
        """

        upload_start = time.time()
        result = self._ssh_exec(ssh_host, ssh_port, upload_script)
        upload_time = time.time() - upload_start

        if result['returncode'] != 0:
            raise Exception(f"Erro no upload: {result['stderr']}")

        # 3. Limpar arquivos temporários
        cleanup_script = "rm -rf /tmp/snapshot_parts"
        self._ssh_exec(ssh_host, ssh_port, cleanup_script)

        total_time = time.time() - start_time

        snapshot_info = {
            'snapshot_id': snapshot_name,
            'instance_id': instance_id,
            'created_at': datetime.utcnow().isoformat(),
            'workspace_path': workspace_path,
            'size_original': compress_info['original_size'],
            'size_compressed': compress_info['compressed_size'],
            'compression_ratio': compress_info['ratio'],
            'num_parts': self.num_parts,
            'upload_time': upload_time,
            'total_time': total_time,
            'r2_path': f"snapshots/{snapshot_name}/"
        }

        # Salvar metadados no R2
        self._save_snapshot_metadata(snapshot_info)

        logger.info(f"Snapshot criado: {snapshot_name} ({total_time:.1f}s)")
        return snapshot_info

    def restore_snapshot(
        self,
        snapshot_id: str,
        ssh_host: str,
        ssh_port: int,
        workspace_path: str = "/workspace"
    ) -> Dict:
        """
        Restaura snapshot em uma máquina GPU

        Returns:
            {
                'restored': bool,
                'download_time': float,
                'decompress_time': float,
                'total_time': float
            }
        """
        logger.info(f"Restaurando snapshot {snapshot_id}")

        start_time = time.time()

        # 1. Download paralelo das partes
        logger.info(f"Download de {self.num_parts} partes do R2...")
        download_script = f"""
        mkdir -p /tmp/restore_parts
        s5cmd --numworkers {self.num_parts} --endpoint-url={self.r2_endpoint} \
            cp "s3://{self.r2_bucket}/snapshots/{snapshot_id}/*" /tmp/restore_parts/
        """

        download_start = time.time()
        result = self._ssh_exec(ssh_host, ssh_port, download_script)
        download_time = time.time() - download_start

        if result['returncode'] != 0:
            raise Exception(f"Erro no download: {result['stderr']}")

        # 2. Descomprimir com ANS (GPU)
        logger.info("Descomprimindo com ANS (GPU)...")
        decompress_script = self._generate_decompress_script(workspace_path)

        decompress_start = time.time()
        result = self._ssh_exec(ssh_host, ssh_port, decompress_script)
        decompress_time = time.time() - decompress_start

        if result['returncode'] != 0:
            raise Exception(f"Erro na descompressão: {result['stderr']}")

        # 3. Limpar arquivos temporários
        cleanup_script = "rm -rf /tmp/restore_parts"
        self._ssh_exec(ssh_host, ssh_port, cleanup_script)

        total_time = time.time() - start_time

        logger.info(f"Snapshot restaurado: {snapshot_id} ({total_time:.1f}s)")

        return {
            'restored': True,
            'snapshot_id': snapshot_id,
            'download_time': download_time,
            'decompress_time': decompress_time,
            'total_time': total_time
        }

    def _generate_compress_script(self, workspace_path: str, num_parts: int) -> str:
        """Gera script para comprimir workspace em partes com ANS"""
        return f'''
import json
import time
import os
import glob
import subprocess
from nvidia import nvcomp
import numpy as np
import cupy as cp

cp.cuda.Device(0).use()

workspace = "{workspace_path}"
num_parts = {num_parts}

# Criar diretório para partes
os.makedirs("/tmp/snapshot_parts", exist_ok=True)

# 1. Criar tar do workspace
print("Criando tar do workspace...", flush=True)
subprocess.run(["tar", "-cf", "/tmp/workspace.tar", "-C", workspace, "."], check=True)

workspace_size = os.path.getsize("/tmp/workspace.tar")

# 2. Dividir em partes
print(f"Dividindo em {{num_parts}} partes...", flush=True)
part_size = workspace_size // num_parts
subprocess.run(
    ["split", "-b", str(part_size), "/tmp/workspace.tar", "/tmp/workspace.part_"],
    check=True
)

# 3. Comprimir cada parte com ANS
print("Comprimindo partes com ANS (GPU)...", flush=True)
parts = sorted(glob.glob("/tmp/workspace.part_*"))

total_compressed = 0
codec = nvcomp.Codec(algorithm="ANS")

for i, part_file in enumerate(parts):
    with open(part_file, "rb") as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)

    nv_array = nvcomp.as_array(data).cuda()
    compressed = codec.encode(nv_array)
    cp.cuda.Stream.null.synchronize()

    compressed_data = bytes(compressed.cpu())

    output_file = f"/tmp/snapshot_parts/part_{{i:03d}}.ans"
    with open(output_file, "wb") as f:
        f.write(compressed_data)

    total_compressed += len(compressed_data)

    # Limpar parte original
    os.remove(part_file)

# Limpar tar original
os.remove("/tmp/workspace.tar")

# Retornar info
result = {{
    "original_size": workspace_size,
    "compressed_size": total_compressed,
    "ratio": workspace_size / total_compressed,
    "num_parts": len(parts)
}}

print(json.dumps(result), flush=True)
'''

    def _generate_decompress_script(self, workspace_path: str) -> str:
        """Gera script para descomprimir partes ANS"""
        return f'''
import os
import glob
import subprocess
from nvidia import nvcomp
import numpy as np
import cupy as cp

cp.cuda.Device(0).use()

workspace = "{workspace_path}"

# 1. Descomprimir partes com ANS
print("Descomprimindo partes com ANS (GPU)...", flush=True)
parts = sorted(glob.glob("/tmp/restore_parts/part_*.ans"))

codec = nvcomp.Codec(algorithm="ANS")
all_data = []

for part_file in parts:
    with open(part_file, "rb") as f:
        compressed_data = f.read()

    compressed_np = np.frombuffer(compressed_data, dtype=np.uint8)
    nv_compressed = nvcomp.as_array(compressed_np).cuda()

    decompressed = codec.decode(nv_compressed)
    cp.cuda.Stream.null.synchronize()

    all_data.append(bytes(decompressed.cpu()))

# 2. Juntar partes
print("Juntando partes...", flush=True)
with open("/tmp/workspace_restored.tar", "wb") as f:
    for data in all_data:
        f.write(data)

# 3. Extrair tar
print("Extraindo workspace...", flush=True)
os.makedirs(workspace, exist_ok=True)
subprocess.run(
    ["tar", "-xf", "/tmp/workspace_restored.tar", "-C", workspace],
    check=True
)

# Limpar
os.remove("/tmp/workspace_restored.tar")

print("Restore completo!", flush=True)
'''

    def _ssh_exec(self, host: str, port: int, script: str) -> Dict:
        """Executa script via SSH"""
        cmd = [
            "ssh",
            "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            f"root@{host}",
            f"python3 << 'PYEOF'\n{script}\nPYEOF"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hora max
        )

        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }

    def _save_snapshot_metadata(self, snapshot_info: Dict):
        """Salva metadados do snapshot no R2"""
        metadata_file = f"/tmp/snapshot_metadata_{snapshot_info['snapshot_id']}.json"

        with open(metadata_file, 'w') as f:
            json.dump(snapshot_info, f, indent=2)

        # Upload metadados
        cmd = [
            "s5cmd",
            "--endpoint-url", self.r2_endpoint,
            "cp",
            metadata_file,
            f"s3://{self.r2_bucket}/snapshots/{snapshot_info['snapshot_id']}/metadata.json"
        ]

        subprocess.run(cmd, check=True)
        os.remove(metadata_file)

    def list_snapshots(self, instance_id: Optional[str] = None) -> List[Dict]:
        """Lista snapshots disponíveis"""
        cmd = [
            "s5cmd",
            "--endpoint-url", self.r2_endpoint,
            "ls",
            f"s3://{self.r2_bucket}/snapshots/"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse output e filtrar por instance_id se fornecido
        snapshots = []
        for line in result.stdout.split('\n'):
            if 'metadata.json' in line:
                # Extrair snapshot_id do path
                parts = line.split('/')
                if len(parts) >= 2:
                    snapshot_id = parts[-2]

                    # Carregar metadados
                    metadata = self._load_snapshot_metadata(snapshot_id)

                    if instance_id is None or metadata.get('instance_id') == instance_id:
                        snapshots.append(metadata)

        return snapshots

    def _load_snapshot_metadata(self, snapshot_id: str) -> Dict:
        """Carrega metadados de um snapshot"""
        metadata_file = f"/tmp/snapshot_metadata_{snapshot_id}.json"

        cmd = [
            "s5cmd",
            "--endpoint-url", self.r2_endpoint,
            "cp",
            f"s3://{self.r2_bucket}/snapshots/{snapshot_id}/metadata.json",
            metadata_file
        ]

        subprocess.run(cmd, capture_output=True)

        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            os.remove(metadata_file)
            return metadata

        return {}

    def delete_snapshot(self, snapshot_id: str):
        """Deleta um snapshot"""
        cmd = [
            "s5cmd",
            "--endpoint-url", self.r2_endpoint,
            "rm",
            f"s3://{self.r2_bucket}/snapshots/{snapshot_id}/*"
        ]

        subprocess.run(cmd, check=True)
        logger.info(f"Snapshot deletado: {snapshot_id}")
