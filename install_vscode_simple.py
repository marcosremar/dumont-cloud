#!/usr/bin/env python3
"""
Instala code-server via SSH direto
"""
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.providers.vast_provider import VastProvider
from src.core.config import settings

def ssh_cmd(host, port, command, timeout=180):
    """Execute SSH command"""
    ssh_key = os.path.expanduser("~/.ssh/id_rsa")
    cmd = [
        "ssh",
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", f"ConnectTimeout=30",
        "-p", str(port),
        f"root@{host}",
        command
    ]

    print(f"🔧 Executando: {command[:80]}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode == 0, result.stdout + result.stderr

def main():
    print("🔍 Buscando máquinas rodando...")

    vast_api_key = settings.vast.api_key
    if not vast_api_key:
        print("❌ VAST_API_KEY não configurada")
        return 1

    provider = VastProvider(vast_api_key)
    instances = provider.list_instances()
    running = [i for i in instances if i.actual_status == "running"]

    if not running:
        print("❌ Nenhuma máquina rodando")
        return 1

    machine = running[0]
    print(f"\n📦 Máquina: {machine.id} - {machine.gpu_name}")
    print(f"   SSH: {machine.ssh_host}:{machine.ssh_port}\n")

    # Step 1: Install curl
    print("📥 1/4 - Instalando curl...")
    ok, out = ssh_cmd(machine.ssh_host, machine.ssh_port,
        "apt-get update -qq && apt-get install -y -qq curl"
    )
    if not ok:
        print(f"   ⚠️  Warning: {out[:200]}")

    # Step 2: Install code-server
    print("📥 2/4 - Instalando code-server (pode demorar 1-2 min)...")
    ok, out = ssh_cmd(machine.ssh_host, machine.ssh_port,
        "curl -fsSL https://code-server.dev/install.sh | sh -s -- --method=standalone",
        timeout=240
    )
    if not ok:
        print(f"❌ Falha: {out}")
        return 1

    # Step 3: Configure
    print("⚙️  3/4 - Configurando...")
    ok, out = ssh_cmd(machine.ssh_host, machine.ssh_port, """
mkdir -p ~/.config/code-server
cat > ~/.config/code-server/config.yaml << 'EOF'
bind-addr: 0.0.0.0:8080
auth: none
cert: false
EOF
mkdir -p /workspace
echo "CONFIGURED"
""")
    if not ok or "CONFIGURED" not in out:
        print(f"❌ Falha na configuração: {out}")
        return 1

    # Step 4: Start code-server
    print("🚀 4/4 - Iniciando code-server...")
    ok, out = ssh_cmd(machine.ssh_host, machine.ssh_port, """
pkill -f code-server 2>/dev/null || true
nohup ~/.local/bin/code-server /workspace > /tmp/code-server.log 2>&1 &
sleep 2
if pgrep -f code-server > /dev/null; then
    echo "STARTED"
else
    echo "FAILED"
fi
""")

    if "STARTED" in out:
        # Get the public port mapping
        ports = machine.ports or {}
        port_mapping = ports.get("8080/tcp")

        if port_mapping and isinstance(port_mapping, list) and len(port_mapping) > 0:
            host_port = port_mapping[0].get("HostPort", 8080)
        else:
            host_port = 8080

        public_ip = machine.public_ipaddr or machine.ssh_host

        print(f"\n✅ VS Code instalado e rodando!")
        print(f"\n🌐 Acesse agora:")
        print(f"   http://{public_ip}:{host_port}/")
        print(f"\n💡 Ou clique em 'VS Code > Online (Web)' no dashboard")
        print(f"   http://dumontcloud.orb.local:4890/")
        return 0
    else:
        print(f"❌ Falha ao iniciar: {out}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
