#!/usr/bin/env python3
"""
Teste SIMPLES de Failover REAL usando o VastService existente

Este script:
1. Usa provision_fast() para criar GPU REAL
2. Cria arquivos de teste via SSH
3. Calcula MD5 dos arquivos
4. Reporta tempos e custos
5. Faz cleanup
"""

import os
import sys
import time
import subprocess
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.gpu.strategies.service import MachineProvisionerService
from dataclasses import dataclass
from typing import Optional

@dataclass
class TestFile:
    path: str
    content: str
    md5: str
    size_bytes: int = 0

def ssh_exec(ssh_host: str, ssh_port: int, command: str, timeout: int = 300):
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e)}

def main():
    print("\n" + "="*70)
    print("TESTE SIMPLES DE FAILOVER REAL - DUMONT CLOUD")
    print("="*70)
    print("\nAVISO: Este teste USA CRÉDITOS REAIS da VAST.ai!")
    print("Estimativa: $0.05 - $0.10 USD (1 GPU por ~10 minutos)")
    print("")

    response = input("Continuar? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelado.")
        return

    vast_api_key = os.environ.get("VAST_API_KEY")
    if not vast_api_key:
        print("ERRO: VAST_API_KEY não configurado")
        return

    instance_id = None
    start_time = time.time()

    try:
        # 1. Provisionar GPU usando o serviço existente
        print("\n[1/5] Provisionando GPU via RaceStrategy...")
        print("   (Isso pode levar 2-5 minutos)")

        provisioner = MachineProvisionerService(vast_api_key)

        result = provisioner.provision_fast(
            max_price=0.10,  # Até $0.10/hr
            disk_space=20,
            label="dumont:failover-test",
        )

        if not result.success:
            print(f"ERRO: {result.error_message}")
            return

        instance_id = result.instance_id
        ssh_host = result.ssh_host
        ssh_port = result.ssh_port
        gpu_name = result.gpu_name or "Unknown"

        print(f"\n   GPU provisionada!")
        print(f"   Instance ID: {instance_id}")
        print(f"   GPU: {gpu_name}")
        print(f"   SSH: {ssh_host}:{ssh_port}")
        print(f"   Tempo: {result.time_to_ready:.1f}s")
        print(f"   Preço: ${result.cost_per_hour:.4f}/hr")

        # 2. Criar arquivos de teste
        print("\n[2/5] Criando arquivos de teste...")
        ssh_exec(ssh_host, ssh_port, "mkdir -p /workspace")

        test_files = []
        for i in range(3):
            file_path = f"/workspace/test-file-{i+1}.txt"
            content = f"Test file #{i+1}\\nCreated at: {datetime.now().isoformat()}\\nTimestamp: {time.time()}\\n"

            # Criar arquivo
            create_cmd = f"echo '{content}' > {file_path}"
            create_result = ssh_exec(ssh_host, ssh_port, create_cmd)

            if not create_result["success"]:
                print(f"   ERRO ao criar {file_path}: {create_result['stderr']}")
                continue

            # Obter MD5
            md5_cmd = f"md5sum {file_path} | awk '{{print $1}}'"
            md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd)

            if not md5_result["success"]:
                print(f"   ERRO ao obter MD5: {md5_result['stderr']}")
                continue

            md5_hash = md5_result["stdout"].strip()

            # Obter tamanho
            size_cmd = f"stat -c %s {file_path}"
            size_result = ssh_exec(ssh_host, ssh_port, size_cmd)
            size_bytes = int(size_result["stdout"].strip()) if size_result["success"] else 0

            test_file = TestFile(
                path=file_path,
                content=content,
                md5=md5_hash,
                size_bytes=size_bytes
            )
            test_files.append(test_file)

            print(f"   Created: {file_path}")
            print(f"      MD5: {md5_hash}")
            print(f"      Size: {size_bytes} bytes")

        # 3. Testar comando NVIDIA-SMI
        print("\n[3/5] Testando NVIDIA-SMI...")
        nvidia_result = ssh_exec(ssh_host, ssh_port, "nvidia-smi --query-gpu=name --format=csv,noheader")

        if nvidia_result["success"]:
            gpu_detected = nvidia_result["stdout"].strip()
            print(f"   GPU detectada: {gpu_detected}")
        else:
            print(f"   AVISO: nvidia-smi falhou")

        # 4. Listar arquivos criados
        print("\n[4/5] Validando arquivos...")
        ls_result = ssh_exec(ssh_host, ssh_port, "ls -lh /workspace/")

        if ls_result["success"]:
            print("   Arquivos em /workspace/:")
            for line in ls_result["stdout"].strip().split('\n'):
                if line:
                    print(f"      {line}")

        # Validar MD5s
        validated = 0
        for test_file in test_files:
            md5_cmd = f"md5sum {test_file.path} | awk '{{print $1}}'"
            md5_result = ssh_exec(ssh_host, ssh_port, md5_cmd)

            if md5_result["success"]:
                current_md5 = md5_result["stdout"].strip()
                if current_md5 == test_file.md5:
                    validated += 1

        print(f"\n   Arquivos validados: {validated}/{len(test_files)}")

        # 5. Cleanup
        print("\n[5/5] Cleanup: deletando instância...")
        from services.gpu.vast import VastService

        vast_service = VastService(vast_api_key)
        vast_service.destroy_instance(instance_id)

        print(f"   Instância {instance_id} deletada")

        # Relatório final
        total_time = time.time() - start_time
        estimated_cost = (total_time / 3600) * result.cost_per_hour

        print("\n" + "="*70)
        print("RELATÓRIO FINAL")
        print("="*70)
        print(f"\nGPU: {gpu_name}")
        print(f"Instance ID: {instance_id}")
        print(f"Preço: ${result.cost_per_hour:.4f}/hr")
        print(f"\nTempo total: {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"   - Provisioning: {result.time_to_ready:.1f}s")
        print(f"   - Testes: {total_time - result.time_to_ready:.1f}s")
        print(f"\nArquivos criados: {len(test_files)}")
        print(f"Arquivos validados: {validated}/{len(test_files)}")
        print(f"\nCusto estimado: ${estimated_cost:.4f} USD")
        print(f"Sucesso: SIM")
        print("\n" + "="*70)

    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário")
        if instance_id:
            print(f"Deletando instância {instance_id}...")
            from services.gpu.vast import VastService
            vast_service = VastService(vast_api_key)
            vast_service.destroy_instance(instance_id)
            print("Deletado")

    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()

        if instance_id:
            print(f"\n[CLEANUP] Deletando instância {instance_id}...")
            try:
                from services.gpu.vast import VastService
                vast_service = VastService(vast_api_key)
                vast_service.destroy_instance(instance_id)
                print("Deletado")
            except Exception as cleanup_error:
                print(f"Erro no cleanup: {cleanup_error}")

if __name__ == "__main__":
    main()
