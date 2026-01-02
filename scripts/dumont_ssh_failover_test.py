#!/usr/bin/env python3
"""
Dumont SSH Failover Tester

Script auxiliar para executar testes REAIS de failover via SSH.
Permite executar comandos remotos em GPUs da VAST.ai e validar
transferência de dados.

Usage:
    python scripts/dumont_ssh_failover_test.py --instance-id 12345 --create-files
    python scripts/dumont_ssh_failover_test.py --instance-id 12345 --validate-files file1.txt file2.txt
"""

import argparse
import subprocess
import sys
import time
import json
import hashlib
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SSHConnection:
    """Representa conexão SSH com uma GPU"""
    host: str
    port: int
    instance_id: str

    def exec(self, command: str, timeout: int = 300) -> Dict[str, Any]:
        """Executa comando via SSH"""
        cmd = [
            "ssh",
            "-p", str(self.port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=30",
            "-o", "LogLevel=ERROR",
            f"root@{self.host}",
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
                "stderr": f"Timeout after {timeout}s",
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
            }


def get_instance_ssh_info(instance_id: str, vast_api_key: str) -> Optional[SSHConnection]:
    """Obtém informações SSH de uma instância VAST.ai"""
    import requests

    headers = {"Authorization": f"Bearer {vast_api_key}"}
    response = requests.get(
        "https://cloud.vast.ai/api/v0/instances/",
        headers=headers,
        timeout=30
    )

    if not response.ok:
        print(f"Error getting instances: {response.status_code}")
        return None

    instances = response.json().get("instances", [])

    for instance in instances:
        if str(instance.get("id")) == str(instance_id):
            ssh_host = instance.get("ssh_host")
            ssh_port = instance.get("ssh_port")

            if ssh_host and ssh_port:
                return SSHConnection(
                    host=ssh_host,
                    port=ssh_port,
                    instance_id=str(instance_id)
                )

    return None


def create_test_files(conn: SSHConnection, count: int = 3) -> List[Dict]:
    """
    Cria arquivos de teste na GPU e retorna metadados.

    Returns:
        Lista de dicts com {path, content, md5, size}
    """
    print(f"\nCreating {count} test files on GPU...")

    # Criar workspace
    conn.exec("mkdir -p /workspace")

    files = []

    for i in range(count):
        file_path = f"/workspace/test-file-{i+1}-{int(time.time())}.txt"
        content = f"Test file #{i+1}\\nCreated at: {time.time()}\\nInstance: {conn.instance_id}\\n"

        # Criar arquivo
        create_cmd = f"echo '{content}' > {file_path}"
        result = conn.exec(create_cmd)

        if not result["success"]:
            print(f"  ✗ Failed to create {file_path}: {result['stderr']}")
            continue

        # Obter MD5
        md5_cmd = f"md5sum {file_path} | awk '{{print $1}}'"
        md5_result = conn.exec(md5_cmd)

        if not md5_result["success"]:
            print(f"  ✗ Failed to get MD5 for {file_path}")
            continue

        md5_hash = md5_result["stdout"].strip()

        # Obter tamanho
        size_cmd = f"stat -c %s {file_path} 2>/dev/null || stat -f %z {file_path}"
        size_result = conn.exec(size_cmd)

        size_bytes = 0
        if size_result["success"]:
            try:
                size_bytes = int(size_result["stdout"].strip())
            except ValueError:
                pass

        files.append({
            "path": file_path,
            "content": content,
            "md5": md5_hash,
            "size": size_bytes,
        })

        print(f"  ✓ Created: {file_path}")
        print(f"     MD5: {md5_hash}")
        print(f"     Size: {size_bytes} bytes")

    return files


def validate_files(conn: SSHConnection, files: List[Dict]) -> int:
    """
    Valida que arquivos existem com MD5 correto.

    Returns:
        Número de arquivos válidos
    """
    print(f"\nValidating {len(files)} files on GPU...")

    validated = 0

    for file_info in files:
        file_path = file_info["path"]
        expected_md5 = file_info["md5"]

        # Verificar se arquivo existe
        check_cmd = f"test -f {file_path} && echo exists || echo missing"
        check_result = conn.exec(check_cmd)

        if not check_result["success"] or "missing" in check_result["stdout"]:
            print(f"  ✗ File missing: {file_path}")
            continue

        # Obter MD5 atual
        md5_cmd = f"md5sum {file_path} | awk '{{print $1}}'"
        md5_result = conn.exec(md5_cmd)

        if not md5_result["success"]:
            print(f"  ✗ Failed to get MD5: {file_path}")
            continue

        actual_md5 = md5_result["stdout"].strip()

        if actual_md5 == expected_md5:
            validated += 1
            print(f"  ✓ Valid: {file_path}")
            print(f"     MD5: {actual_md5}")
        else:
            print(f"  ✗ MD5 mismatch: {file_path}")
            print(f"     Expected: {expected_md5}")
            print(f"     Got:      {actual_md5}")

    return validated


def list_workspace_files(conn: SSHConnection):
    """Lista arquivos no workspace"""
    print(f"\nListing workspace files...")

    # Listar arquivos
    list_cmd = "find /workspace -type f -exec ls -lh {} \; 2>/dev/null"
    result = conn.exec(list_cmd)

    if result["success"]:
        files = result["stdout"].strip().split('\n')
        print(f"\n  Found {len(files)} files:")
        for file_line in files:
            print(f"    {file_line}")
    else:
        print(f"  Error: {result['stderr']}")


def main():
    parser = argparse.ArgumentParser(description="Dumont SSH Failover Tester")

    # Conexão
    parser.add_argument("--instance-id", required=True, help="VAST.ai instance ID")
    parser.add_argument("--vast-api-key", help="VAST.ai API key (or use VAST_API_KEY env)")

    # Ações
    parser.add_argument("--create-files", action="store_true", help="Create test files")
    parser.add_argument("--file-count", type=int, default=3, help="Number of files to create")
    parser.add_argument("--validate-files", help="Validate files (JSON file with file metadata)")
    parser.add_argument("--list-files", action="store_true", help="List workspace files")

    # SSH direto (opcional)
    parser.add_argument("--ssh-host", help="SSH host (if not using VAST API)")
    parser.add_argument("--ssh-port", type=int, help="SSH port")

    args = parser.parse_args()

    # Obter API key
    import os
    vast_api_key = args.vast_api_key or os.environ.get("VAST_API_KEY")

    # Obter conexão SSH
    if args.ssh_host and args.ssh_port:
        conn = SSHConnection(
            host=args.ssh_host,
            port=args.ssh_port,
            instance_id=args.instance_id
        )
    else:
        if not vast_api_key:
            print("Error: VAST API key required (--vast-api-key or VAST_API_KEY env)")
            sys.exit(1)

        print(f"Getting SSH info for instance {args.instance_id}...")
        conn = get_instance_ssh_info(args.instance_id, vast_api_key)

        if not conn:
            print(f"Error: Could not get SSH info for instance {args.instance_id}")
            sys.exit(1)

    print(f"\nConnected to: {conn.host}:{conn.port}")

    # Executar ações
    if args.create_files:
        files = create_test_files(conn, args.file_count)

        # Salvar metadados em JSON
        output_file = f"failover_files_{args.instance_id}.json"
        with open(output_file, 'w') as f:
            json.dump(files, f, indent=2)

        print(f"\n✓ File metadata saved to: {output_file}")
        print(f"  Use this file to validate after failover:")
        print(f"  python {sys.argv[0]} --instance-id <NEW_ID> --validate-files {output_file}")

    elif args.validate_files:
        # Carregar metadados
        with open(args.validate_files, 'r') as f:
            files = json.load(f)

        validated = validate_files(conn, files)

        print(f"\n{'='*60}")
        print(f"VALIDATION RESULT")
        print(f"{'='*60}")
        print(f"  Files validated: {validated}/{len(files)}")
        print(f"  Success rate:    {validated/len(files)*100:.1f}%")
        print(f"{'='*60}")

        # Exit code: 0 se todos validados, 1 caso contrário
        sys.exit(0 if validated == len(files) else 1)

    elif args.list_files:
        list_workspace_files(conn)

    else:
        print("No action specified. Use --create-files, --validate-files, or --list-files")
        sys.exit(1)


if __name__ == "__main__":
    main()
