#!/usr/bin/env python3
"""
Dumont Cloud - SSH Failover para VS Code Desktop

Este script cria uma configuracao SSH que automaticamente
conecta na GPU ou na CPU backup, dependendo de qual esta disponivel.

Uso:
    python3 dumont_ssh_failover.py setup
    python3 dumont_ssh_failover.py status
    python3 dumont_ssh_failover.py connect

O VS Code Remote-SSH usa o ~/.ssh/config configurado pelo 'setup'.
"""

import os
import sys
import json
import socket
import subprocess
import time
from pathlib import Path

# Arquivo de configuracao do Dumont
CONFIG_DIR = Path.home() / ".dumont"
CONFIG_FILE = CONFIG_DIR / "ssh_config.json"
SSH_CONFIG = Path.home() / ".ssh" / "config"

def load_config():
    """Carrega configuracao de maquinas"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "gpu": {"host": None, "port": 22, "user": "root"},
        "cpu": {"host": None, "port": 22, "user": "root"},
        "workspace": "/workspace",
        "current": "gpu"
    }

def save_config(config):
    """Salva configuracao"""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def check_ssh_connection(host, port, timeout=3):
    """Verifica se consegue conectar via SSH"""
    if not host:
        return False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def get_active_machine():
    """Retorna a maquina ativa (GPU ou CPU)"""
    config = load_config()

    # Tenta GPU primeiro
    gpu = config.get("gpu", {})
    if gpu.get("host") and check_ssh_connection(gpu["host"], gpu.get("port", 22)):
        if config.get("current") != "gpu":
            config["current"] = "gpu"
            save_config(config)
            print(f"[Dumont] Conectando na GPU: {gpu['host']}:{gpu['port']}")
        return "gpu", gpu

    # Fallback para CPU
    cpu = config.get("cpu", {})
    if cpu.get("host") and check_ssh_connection(cpu["host"], cpu.get("port", 22)):
        if config.get("current") != "cpu":
            config["current"] = "cpu"
            save_config(config)
            print(f"[Dumont] GPU indisponivel! Failover para CPU: {cpu['host']}:{cpu['port']}")
        return "cpu", cpu

    print("[Dumont] ERRO: Nenhuma maquina disponivel!")
    return None, None

def setup_ssh_config():
    """Configura ~/.ssh/config para usar failover"""
    config = load_config()

    # Script proxy que decide qual maquina usar (compativel com macOS e Linux)
    proxy_script = CONFIG_DIR / "ssh_proxy.sh"
    proxy_script.write_text(f'''#!/bin/bash
# Dumont Cloud SSH Proxy - Failover automatico GPU/CPU
# Verifica SSH banner (nao apenas porta aberta) para garantir que SSH esta respondendo
CONFIG_FILE="{CONFIG_FILE}"

check_ssh_banner() {{
    local host=$1
    local port=$2
    # Tenta ler o banner SSH com timeout de 3 segundos
    # SSH servers respondem com "SSH-2.0-..." ou similar
    # Usa nc com timeout e verifica se resposta comeca com "SSH-"
    local banner=$(echo "" | nc -w 3 "$host" "$port" 2>/dev/null | head -c 4)
    [[ "$banner" == "SSH-" ]]
    return $?
}}

if [ -f "$CONFIG_FILE" ]; then
    GPU_HOST=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('gpu',{{}}).get('host',''))")
    GPU_PORT=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('gpu',{{}}).get('port',22))")
    CPU_HOST=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('cpu',{{}}).get('host',''))")
    CPU_PORT=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('cpu',{{}}).get('port',22))")

    # Tenta GPU primeiro - verifica se SSH responde com banner
    if [ -n "$GPU_HOST" ]; then
        if check_ssh_banner "$GPU_HOST" "$GPU_PORT"; then
            exec nc "$GPU_HOST" "$GPU_PORT"
        fi
    fi

    # Fallback para CPU - verifica se SSH responde
    if [ -n "$CPU_HOST" ]; then
        if check_ssh_banner "$CPU_HOST" "$CPU_PORT"; then
            echo "[Dumont] GPU offline - Failover para CPU" >&2
            exec nc "$CPU_HOST" "$CPU_PORT"
        fi
    fi
fi

echo "[Dumont] Nenhuma maquina disponivel!" >&2
exit 1
''')
    os.chmod(proxy_script, 0o755)

    # Configuracao SSH para Dumont
    ssh_entry = f'''
# Dumont Cloud - GPU/CPU com failover automatico
Host dumont dumont-workspace
    User root
    ProxyCommand {proxy_script}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
    ServerAliveInterval 30
    ServerAliveCountMax 3
    # VS Code Remote-SSH
    ForwardAgent yes

# Dumont GPU direto (sem failover)
Host dumont-gpu
    HostName {config.get("gpu", {}).get("host", "GPU_NOT_CONFIGURED")}
    Port {config.get("gpu", {}).get("port", 22)}
    User root
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

# Dumont CPU direto (sem failover)
Host dumont-cpu
    HostName {config.get("cpu", {}).get("host", "CPU_NOT_CONFIGURED")}
    Port {config.get("cpu", {}).get("port", 22)}
    User root
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
'''

    # Ler config existente e remover entradas Dumont antigas
    existing = ""
    if SSH_CONFIG.exists():
        existing = SSH_CONFIG.read_text()
        # Remove blocos Dumont existentes
        lines = existing.split('\n')
        new_lines = []
        skip_block = False
        for line in lines:
            if line.startswith('# Dumont Cloud'):
                skip_block = True
            elif skip_block and line.startswith('Host ') and 'dumont' not in line.lower():
                skip_block = False
                new_lines.append(line)
            elif not skip_block:
                new_lines.append(line)
        existing = '\n'.join(new_lines).strip()

    # Escrever nova config
    new_config = existing + '\n' + ssh_entry if existing else ssh_entry
    SSH_CONFIG.parent.mkdir(exist_ok=True)
    SSH_CONFIG.write_text(new_config)
    os.chmod(SSH_CONFIG, 0o600)

    print(f"[Dumont] SSH configurado em {SSH_CONFIG}")
    print(f"[Dumont] Proxy script: {proxy_script}")
    print()
    print("Para conectar no VS Code:")
    print("  1. Instale a extensao 'Remote - SSH'")
    print("  2. Pressione Cmd+Shift+P (Mac) ou Ctrl+Shift+P (Windows/Linux)")
    print("  3. Digite 'Remote-SSH: Connect to Host'")
    print("  4. Selecione 'dumont' ou 'dumont-workspace'")
    print()
    print("O VS Code conectara automaticamente na GPU ou CPU disponivel!")

def configure_machines(gpu_host, gpu_port, cpu_host, cpu_port):
    """Configura as maquinas GPU e CPU"""
    config = load_config()

    if gpu_host:
        config["gpu"] = {
            "host": gpu_host.split(':')[0] if ':' in gpu_host else gpu_host,
            "port": int(gpu_host.split(':')[1]) if ':' in gpu_host else int(gpu_port),
            "user": "root"
        }

    if cpu_host:
        config["cpu"] = {
            "host": cpu_host.split(':')[0] if ':' in cpu_host else cpu_host,
            "port": int(cpu_host.split(':')[1]) if ':' in cpu_host else int(cpu_port),
            "user": "root"
        }

    save_config(config)
    print(f"[Dumont] GPU: {config['gpu']}")
    print(f"[Dumont] CPU: {config['cpu']}")

def status():
    """Mostra status das maquinas"""
    config = load_config()

    print("=== Dumont Cloud SSH Status ===")
    print()

    gpu = config.get("gpu", {})
    if gpu.get("host"):
        gpu_ok = check_ssh_connection(gpu["host"], gpu.get("port", 22))
        status = "[OK]" if gpu_ok else "[OFFLINE]"
        print(f"GPU: {gpu['host']}:{gpu['port']} {status}")
    else:
        print("GPU: Nao configurada")

    cpu = config.get("cpu", {})
    if cpu.get("host"):
        cpu_ok = check_ssh_connection(cpu["host"], cpu.get("port", 22))
        status = "[OK]" if cpu_ok else "[OFFLINE]"
        print(f"CPU: {cpu['host']}:{cpu['port']} {status}")
    else:
        print("CPU: Nao configurada")

    print()
    print(f"Maquina atual: {config.get('current', 'nenhuma')}")

    machine_type, machine = get_active_machine()
    if machine:
        print(f"Maquina ativa: {machine_type} ({machine['host']}:{machine['port']})")
    else:
        print("Nenhuma maquina disponivel!")

def watch():
    """Monitora e exibe status em tempo real"""
    print("=== Dumont Cloud SSH Monitor ===")
    print("Pressione Ctrl+C para sair")
    print()

    while True:
        config = load_config()
        gpu = config.get("gpu", {})
        cpu = config.get("cpu", {})

        gpu_ok = check_ssh_connection(gpu.get("host"), gpu.get("port", 22)) if gpu.get("host") else False
        cpu_ok = check_ssh_connection(cpu.get("host"), cpu.get("port", 22)) if cpu.get("host") else False

        gpu_status = "[OK]" if gpu_ok else "[X]"
        cpu_status = "[OK]" if cpu_ok else "[X]"

        current = config.get("current", "?")
        active = "GPU" if gpu_ok else ("CPU" if cpu_ok else "NONE")

        print(f"\r[{time.strftime('%H:%M:%S')}] GPU: {gpu_status}  CPU: {cpu_status}  Ativo: {active}    ", end="", flush=True)

        time.sleep(5)

def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  dumont_ssh_failover.py setup                     - Configura SSH")
        print("  dumont_ssh_failover.py config GPU_HOST GPU_PORT CPU_HOST CPU_PORT")
        print("  dumont_ssh_failover.py status                    - Mostra status")
        print("  dumont_ssh_failover.py watch                     - Monitor tempo real")
        print("  dumont_ssh_failover.py connect                   - Conecta SSH")
        print()
        print("Exemplo:")
        print("  dumont_ssh_failover.py config ssh9.vast.ai 35678 35.240.1.1 22")
        print("  dumont_ssh_failover.py setup")
        print("  ssh dumont  # Conecta automaticamente na maquina disponivel")
        return

    cmd = sys.argv[1]

    if cmd == "setup":
        setup_ssh_config()
    elif cmd == "config" and len(sys.argv) >= 6:
        configure_machines(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
        setup_ssh_config()
    elif cmd == "status":
        status()
    elif cmd == "watch":
        try:
            watch()
        except KeyboardInterrupt:
            print("\nEncerrado.")
    elif cmd == "connect":
        machine_type, machine = get_active_machine()
        if machine:
            os.execvp("ssh", ["ssh", "-p", str(machine["port"]), f"{machine['user']}@{machine['host']}"])
        else:
            print("Nenhuma maquina disponivel!")
            sys.exit(1)
    else:
        print(f"Comando desconhecido: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
