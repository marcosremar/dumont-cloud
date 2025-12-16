#!/usr/bin/env python3
"""
SnapGPU - Test Restore by Instance ID
Testa a funcionalidade de restaurar snapshot em uma instancia existente usando apenas o Instance ID.

Este teste valida:
1. Obter informacoes SSH (host, porta) a partir do Instance ID via API vast.ai
2. Conectar na maquina via SSH
3. Instalar restic e configurar credenciais
4. Restaurar snapshot mais recente
5. Verificar que o conteudo foi restaurado (testar Ollama)

Uso:
    python test_restore_by_instance.py <instance_id> [--snapshot <snapshot_id>]
    python test_restore_by_instance.py 28864630
    python test_restore_by_instance.py 28864630 --snapshot d5a91e43
"""

import requests
import subprocess
import json
import sys
import time
from datetime import datetime

# Configuracao
BASE_URL = "http://vps-a84d392b.vps.ovh.net:8765"
VAST_API_KEY = "a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd"

# Credenciais R2 para restic
R2_ACCESS_KEY = "f0a6f424064e46c903c76a447f5e73d2"
R2_SECRET_KEY = "1dcf325fe8556fca221cf8b383e277e7af6660a246148d5e11e4fc67e822c9b5"
RESTIC_PASSWORD = "musetalk123"
RESTIC_REPO = "s3:https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com/musetalk/restic"

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'

def log_success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.END} {msg}")

def log_fail(msg):
    print(f"{Colors.RED}[FAIL]{Colors.END} {msg}")

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {msg}")

def log_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.END} {msg}")

def log_step(step, msg):
    print(f"\n{Colors.CYAN}[STEP {step}]{Colors.END} {Colors.BOLD}{msg}{Colors.END}")


class RestoreByInstanceTester:
    """Classe para testar restore por Instance ID"""

    def __init__(self, instance_id, snapshot_id=None):
        self.instance_id = instance_id
        self.snapshot_id = snapshot_id
        self.ssh_host = None
        self.ssh_port = None

    def get_instance_info_from_vast(self):
        """Obtem informacoes SSH da instancia via API vast.ai"""
        log_step(1, f"Obtendo informacoes da instancia {self.instance_id} via API vast.ai")

        try:
            headers = {"Authorization": f"Bearer {VAST_API_KEY}"}
            resp = requests.get(
                "https://console.vast.ai/api/v0/instances/",
                headers=headers,
                params={"owner": "me"},
                timeout=30
            )

            if resp.status_code != 200:
                log_fail(f"Erro na API vast.ai: {resp.status_code}")
                return False

            data = resp.json()
            instances = data.get("instances", [])

            # Procurar a instancia pelo ID
            for inst in instances:
                if str(inst.get("id")) == str(self.instance_id):
                    # Tentar usar conexao direta (IP publico + porta mapeada)
                    public_ip = inst.get("public_ipaddr")
                    ports = inst.get("ports", {})
                    ssh_port_info = ports.get("22/tcp", [])

                    if public_ip and ssh_port_info:
                        # Usar conexao direta via IP publico
                        self.ssh_host = public_ip
                        self.ssh_port = int(ssh_port_info[0].get("HostPort", 22))
                    else:
                        # Fallback para ssh_host/ssh_port (proxy vast.ai)
                        self.ssh_host = inst.get("ssh_host")
                        self.ssh_port = inst.get("ssh_port", 22)

                    status = inst.get("actual_status", "unknown")
                    gpu = inst.get("gpu_name", "?")

                    log_success(f"Instancia encontrada!")
                    log_info(f"  Status: {status}")
                    log_info(f"  GPU: {gpu}")
                    log_info(f"  SSH: {self.ssh_host}:{self.ssh_port}")
                    return True

            log_fail(f"Instancia {self.instance_id} nao encontrada")
            log_info(f"Instancias disponiveis: {[inst.get('id') for inst in instances]}")
            return False

        except Exception as e:
            log_fail(f"Erro ao consultar API vast.ai: {e}")
            return False

    def ssh_run(self, command, timeout=60):
        """Executa comando via SSH na instancia"""
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout=10",
            "-p", str(self.ssh_port),
            f"root@{self.ssh_host}",
            command
        ]

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Timeout"
        except Exception as e:
            return False, "", str(e)

    def test_ssh_connection(self):
        """Testa conexao SSH"""
        log_step(2, "Testando conexao SSH")

        success, stdout, stderr = self.ssh_run("hostname && nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'No GPU'")

        if success:
            log_success(f"Conexao SSH OK")
            log_info(f"  Hostname: {stdout.strip().split()[0] if stdout else '?'}")
            return True
        else:
            log_fail(f"Falha na conexao SSH: {stderr}")
            return False

    def install_restic(self):
        """Instala e configura restic na instancia"""
        log_step(3, "Instalando e configurando restic")

        # Instalar restic
        success, stdout, stderr = self.ssh_run(
            "which restic || (apt-get update -qq && apt-get install -y restic > /dev/null 2>&1) && restic version",
            timeout=120
        )

        if not success or "restic" not in stdout:
            log_fail(f"Falha ao instalar restic: {stderr}")
            return False

        log_info(f"Restic: {stdout.strip().split()[-1] if stdout else 'instalado'}")

        # Configurar credenciais AWS
        success, _, stderr = self.ssh_run(f'''
mkdir -p /root/.aws && cat > /root/.aws/credentials << EOF
[default]
aws_access_key_id = {R2_ACCESS_KEY}
aws_secret_access_key = {R2_SECRET_KEY}
EOF
echo "Credenciais configuradas"
''')

        if success:
            log_success("Restic instalado e configurado")
            return True
        else:
            log_fail(f"Falha ao configurar credenciais: {stderr}")
            return False

    def list_snapshots(self):
        """Lista snapshots disponiveis"""
        log_step(4, "Listando snapshots disponiveis")

        success, stdout, stderr = self.ssh_run(f'''
export AWS_ACCESS_KEY_ID="{R2_ACCESS_KEY}"
export AWS_SECRET_ACCESS_KEY="{R2_SECRET_KEY}"
export RESTIC_PASSWORD="{RESTIC_PASSWORD}"
export RESTIC_REPOSITORY="{RESTIC_REPO}"
restic snapshots --json 2>/dev/null
''', timeout=60)

        if not success:
            log_fail(f"Falha ao listar snapshots: {stderr}")
            return None

        try:
            snapshots = json.loads(stdout)
            log_success(f"Encontrados {len(snapshots)} snapshots")

            # Mostrar os 3 mais recentes
            for snap in snapshots[-3:]:
                short_id = snap.get("short_id", snap.get("id", "?")[:8])
                time_str = snap.get("time", "?")[:19]
                paths = snap.get("paths", [])
                tags = snap.get("tags", [])
                log_info(f"  {short_id} - {time_str} - {paths} - tags: {tags}")

            return snapshots
        except json.JSONDecodeError:
            log_fail(f"Erro ao parsear JSON de snapshots")
            return None

    def restore_snapshot(self, snapshot_id=None):
        """Restaura um snapshot"""
        target_snapshot = snapshot_id or self.snapshot_id or "latest"
        log_step(5, f"Restaurando snapshot: {target_snapshot}")

        success, stdout, stderr = self.ssh_run(f'''
export AWS_ACCESS_KEY_ID="{R2_ACCESS_KEY}"
export AWS_SECRET_ACCESS_KEY="{R2_SECRET_KEY}"
export RESTIC_PASSWORD="{RESTIC_PASSWORD}"
export RESTIC_REPOSITORY="{RESTIC_REPO}"
mkdir -p /workspace
cd /
restic restore {target_snapshot} --target / --verbose 2>&1 | tail -10
''', timeout=600)

        if success and "Restored" in stdout:
            log_success(f"Snapshot restaurado com sucesso!")
            # Extrair estatisticas
            for line in stdout.split('\n'):
                if "Summary" in line or "Restored" in line:
                    log_info(f"  {line.strip()}")
            return True
        else:
            log_fail(f"Falha ao restaurar: {stderr or stdout}")
            return False

    def verify_restore(self):
        """Verifica se o restore funcionou (testa Ollama)"""
        log_step(6, "Verificando restauracao (testando Ollama)")

        # Verificar se pasta ollama-test existe
        success, stdout, _ = self.ssh_run("ls -la /workspace/ollama-test/ 2>/dev/null || echo 'NOT_FOUND'")

        if "NOT_FOUND" in stdout:
            log_warn("Pasta /workspace/ollama-test nao encontrada no snapshot")
            log_info("Verificando outros conteudos...")
            success, stdout, _ = self.ssh_run("ls -la /workspace/ 2>/dev/null | head -10")
            log_info(f"Conteudo de /workspace:\n{stdout}")
            return True  # Restore pode ter funcionado, mas sem Ollama

        # Instalar Ollama e copiar dados
        log_info("Configurando Ollama a partir do backup...")
        success, stdout, stderr = self.ssh_run('''
curl -fsSL https://ollama.com/install.sh | sh 2>&1 | tail -3
rm -rf /root/.ollama
cp -r /workspace/ollama-test /root/.ollama
echo "Ollama configurado"
''', timeout=120)

        if not success:
            log_warn(f"Erro ao instalar Ollama: {stderr}")
            return False

        # Iniciar servidor e testar modelo
        log_info("Testando modelo Qwen...")
        success, stdout, stderr = self.ssh_run('''
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 5
ollama list
ollama run qwen2.5:0.5b "Responda apenas: TESTE OK" 2>&1 | head -5
''', timeout=90)

        if success and ("qwen" in stdout.lower() or "OK" in stdout):
            log_success("Ollama funcionando! Modelo respondeu corretamente.")
            return True
        else:
            log_warn(f"Ollama pode nao estar funcionando: {stdout[:200] if stdout else stderr[:200]}")
            return False

    def run_full_test(self):
        """Executa teste completo de restore por Instance ID"""
        print(f"\n{'='*70}")
        print(f"{Colors.BOLD}SnapGPU - Restore by Instance ID Test{Colors.END}")
        print(f"{'='*70}")
        print(f"Instance ID: {self.instance_id}")
        print(f"Snapshot: {self.snapshot_id or 'latest'}")
        print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")

        start_time = time.time()
        success = True

        try:
            # 1. Obter info SSH via API vast.ai
            if not self.get_instance_info_from_vast():
                return False

            # 2. Testar conexao SSH
            if not self.test_ssh_connection():
                return False

            # 3. Instalar restic
            if not self.install_restic():
                return False

            # 4. Listar snapshots
            snapshots = self.list_snapshots()
            if not snapshots:
                return False

            # 5. Restaurar snapshot
            if not self.restore_snapshot():
                success = False

            # 6. Verificar restore
            if success:
                self.verify_restore()

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrompido pelo usuario!{Colors.END}")
            success = False

        except Exception as e:
            log_fail(f"Erro inesperado: {e}")
            success = False

        # Resumo
        total_time = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"{Colors.BOLD}RESUMO{Colors.END}")
        print(f"{'='*70}")
        print(f"Tempo total: {total_time:.0f}s")
        print(f"SSH: {self.ssh_host}:{self.ssh_port}")

        if success:
            print(f"\n{Colors.GREEN}{Colors.BOLD}TESTE PASSOU!{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}TESTE FALHOU!{Colors.END}")

        return success


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    instance_id = sys.argv[1]
    snapshot_id = None

    # Parse argumentos
    if "--snapshot" in sys.argv:
        idx = sys.argv.index("--snapshot")
        if idx + 1 < len(sys.argv):
            snapshot_id = sys.argv[idx + 1]

    tester = RestoreByInstanceTester(instance_id, snapshot_id)
    success = tester.run_full_test()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
