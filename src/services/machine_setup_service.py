"""
MachineSetupService - Setup completo de maquinas GPU.

Versao 2.0 - Com resiliencia:
- Retry com backoff exponencial em todas operacoes SSH
- Health checks em cada etapa
- Fallback e recovery automatico
- Logging detalhado

Integra todos os componentes necessarios:
- code-server (VS Code Web)
- DumontAgent (backup automatico via restic)
- Lsyncd (sync em tempo real com CPU backup)

Uso:
    service = MachineSetupService(ssh_host, ssh_port)
    result = service.setup_full(config)
"""
import subprocess
import os
import time
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from src.services.codeserver_service import CodeServerService, CodeServerConfig

logger = logging.getLogger(__name__)


@dataclass
class MachineSetupConfig:
    """Configuracao completa para setup de maquina GPU"""
    # Workspace
    workspace: str = "/workspace"

    # Code-server
    setup_codeserver: bool = True
    codeserver_port: int = 8080
    codeserver_auth: str = "none"
    codeserver_theme: str = "Default Dark+"

    # DumontAgent (backup via restic)
    setup_agent: bool = True
    dumont_server: str = ""  # URL do servidor Dumont para envio de status
    instance_id: str = ""

    # Restic/R2 credentials
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    restic_password: str = ""
    restic_repository: str = ""  # s3:s3.us-west-004.backblazeb2.com/bucket

    # Lsyncd (sync tempo real com CPU backup)
    setup_lsyncd: bool = False
    backup_host: str = ""  # root@IP da CPU backup

    # SSH
    ssh_user: str = "root"

    # Resiliencia
    max_retries: int = 3
    retry_delay: float = 2.0
    ssh_timeout: int = 120


class MachineSetupService:
    """
    Servico unificado para setup completo de maquinas GPU.

    Componentes instalados:
    1. code-server - VS Code no browser (porta 8080)
    2. DumontAgent - Backup automatico a cada 30s via restic
    3. Lsyncd - Sync em tempo real com CPU backup (opcional)
    """

    # Caminho dos scripts locais
    SCRIPTS_DIR = Path(__file__).parent.parent.parent / "agent"

    def __init__(self, ssh_host: str, ssh_port: int, ssh_user: str = "root"):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.codeserver = CodeServerService(ssh_host, ssh_port, ssh_user)

    def _ssh_cmd(
        self,
        command: str,
        timeout: int = 120,
        retries: int = 3,
        retry_delay: float = 2.0
    ) -> Tuple[bool, str]:
        """
        Executa comando via SSH com retry automatico e backoff exponencial.

        Args:
            command: Comando a executar
            timeout: Timeout em segundos
            retries: Numero de tentativas
            retry_delay: Delay entre tentativas (com backoff)

        Returns:
            Tupla (sucesso, output)
        """
        ssh_command = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-o", f"ConnectTimeout={min(timeout, 30)}",
            "-o", "ServerAliveInterval=10",
            "-o", "ServerAliveCountMax=3",
            "-p", str(self.ssh_port),
            f"{self.ssh_user}@{self.ssh_host}",
            command
        ]

        last_error = ""
        for attempt in range(retries):
            try:
                logger.debug(f"SSH attempt {attempt + 1}/{retries}: {command[:50]}...")
                result = subprocess.run(
                    ssh_command,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                output = result.stdout + result.stderr

                # Filtrar mensagens do VAST.ai que nao sao erros
                if result.returncode == 0:
                    return True, output

                # Verificar se o comando realmente falhou ou so tem warning
                if "Welcome to vast.ai" in output and result.returncode != 0:
                    # Tentar novamente - pode ser problema transiente
                    last_error = output
                    logger.warning(f"VAST.ai transient error, retrying...")
                else:
                    return False, output

            except subprocess.TimeoutExpired:
                last_error = f"Timeout ({timeout}s) na tentativa {attempt + 1}"
                logger.warning(last_error)
            except Exception as e:
                last_error = str(e)
                logger.warning(f"SSH error: {last_error}")

            if attempt < retries - 1:
                delay = retry_delay * (2 ** attempt)  # Backoff exponencial
                logger.info(f"Aguardando {delay}s antes de retry...")
                time.sleep(delay)

        return False, f"Falha apos {retries} tentativas: {last_error}"

    def _scp_file(
        self,
        local_path: str,
        remote_path: str,
        timeout: int = 60,
        retries: int = 3
    ) -> Tuple[bool, str]:
        """Copia arquivo local para remoto via SCP com retry."""
        scp_command = [
            "scp",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-P", str(self.ssh_port),
            local_path,
            f"{self.ssh_user}@{self.ssh_host}:{remote_path}"
        ]

        last_error = ""
        for attempt in range(retries):
            try:
                result = subprocess.run(
                    scp_command,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                if result.returncode == 0:
                    return True, result.stdout + result.stderr
                last_error = result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                last_error = f"Timeout ({timeout}s)"
            except Exception as e:
                last_error = str(e)

            if attempt < retries - 1:
                time.sleep(2 ** attempt)

        return False, f"SCP falhou apos {retries} tentativas: {last_error}"

    def check_ssh_connectivity(self, timeout: int = 30) -> Dict[str, Any]:
        """Verifica conectividade SSH com a maquina."""
        success, output = self._ssh_cmd("echo 'SSH_OK' && hostname", timeout=timeout, retries=3)
        if success and "SSH_OK" in output:
            hostname = output.replace("SSH_OK", "").strip().split("\n")[0]
            return {"success": True, "hostname": hostname}
        return {"success": False, "error": output}

    def check_gpu_available(self) -> Dict[str, Any]:
        """Verifica se GPU esta disponivel."""
        success, output = self._ssh_cmd(
            "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo 'NO_GPU'",
            timeout=30, retries=2
        )
        if success and "NO_GPU" not in output:
            gpu_info = output.strip().split("\n")[0]
            return {"success": True, "gpu": gpu_info}
        return {"success": False, "gpu": None}

    def setup_workspace(self, workspace: str = "/workspace") -> Dict[str, Any]:
        """Cria diretorio workspace se nao existir."""
        success, output = self._ssh_cmd(f"mkdir -p {workspace} && ls -la {workspace} | head -3")
        if success:
            return {"success": True, "message": f"Workspace {workspace} criado", "workspace": workspace}
        return {"success": False, "error": f"Falha ao criar workspace: {output}"}

    def setup_codeserver(self, config: MachineSetupConfig) -> Dict[str, Any]:
        """Instala e configura code-server"""
        cs_config = CodeServerConfig(
            port=config.codeserver_port,
            workspace=config.workspace,
            theme=config.codeserver_theme,
            auth=config.codeserver_auth,
            user=config.ssh_user,
        )
        return self.codeserver.setup_full(cs_config)

    def install_restic(self) -> Dict[str, Any]:
        """Instala restic para backup com retry."""
        install_script = '''#!/bin/bash
# Verificar se restic ja esta instalado
if command -v restic &> /dev/null && restic version 2>/dev/null | grep -q "0.17"; then
    echo "RESTIC_ALREADY_INSTALLED"
    restic version
    exit 0
fi

# Instalar dependencias
apt-get update -qq 2>/dev/null || true
apt-get install -y -qq wget bzip2 2>/dev/null || true

# Baixar e instalar restic
echo "Instalando restic 0.17.3..."
cd /tmp

# Tentar download ate 3 vezes
for i in 1 2 3; do
    if wget -q --timeout=30 https://github.com/restic/restic/releases/download/v0.17.3/restic_0.17.3_linux_amd64.bz2 -O restic.bz2; then
        break
    fi
    echo "Tentativa $i falhou, retrying..."
    sleep 2
done

# Verificar se baixou
if [ ! -f /tmp/restic.bz2 ]; then
    echo "RESTIC_DOWNLOAD_FAILED"
    exit 1
fi

# Descomprimir
bunzip2 -f /tmp/restic.bz2

if [ ! -f /tmp/restic ]; then
    echo "RESTIC_EXTRACT_FAILED"
    exit 1
fi

chmod +x /tmp/restic
mv /tmp/restic /usr/local/bin/restic

# Verificar instalacao
if restic version 2>/dev/null | grep -q "0.17"; then
    echo "RESTIC_INSTALLED"
    restic version
else
    echo "RESTIC_INSTALL_FAILED"
    exit 1
fi
'''
        success, output = self._ssh_cmd(install_script, timeout=180, retries=2)

        if "RESTIC_ALREADY_INSTALLED" in output or "RESTIC_INSTALLED" in output:
            return {"success": True, "message": "Restic instalado", "output": output}

        return {"success": False, "error": f"Falha ao instalar restic: {output}"}

    def setup_dumont_agent(self, config: MachineSetupConfig) -> Dict[str, Any]:
        """Instala DumontAgent para backup automatico com resiliencia."""

        # 1. Instalar restic primeiro
        restic_result = self.install_restic()
        if not restic_result.get("success"):
            return restic_result

        # 2. Script de instalacao do agente
        install_script = f'''#!/bin/bash
set -e

INSTALL_DIR="/opt/dumont"
mkdir -p "$INSTALL_DIR"
mkdir -p /var/log
mkdir -p {config.workspace}

# Criar configuracao
cat > "$INSTALL_DIR/config.env" << 'CONFIG_EOF'
export DUMONT_SERVER="{config.dumont_server}"
export INSTANCE_ID="{config.instance_id}"
export SYNC_DIRS="{config.workspace}"
export AWS_ACCESS_KEY_ID="{config.aws_access_key_id}"
export AWS_SECRET_ACCESS_KEY="{config.aws_secret_access_key}"
export RESTIC_PASSWORD="{config.restic_password}"
export RESTIC_REPOSITORY="{config.restic_repository}"
CONFIG_EOF
chmod 600 "$INSTALL_DIR/config.env"

# Criar script do agente
cat > "$INSTALL_DIR/dumont-agent.sh" << 'AGENT_EOF'
#!/bin/bash
VERSION="1.0.0"
INSTALL_DIR="/opt/dumont"
LOG_FILE="/var/log/dumont-agent.log"
LOCK_FILE="/tmp/dumont-agent.lock"
STATUS_FILE="/tmp/dumont-agent-status.json"
INTERVAL=30

source "$INSTALL_DIR/config.env"

log() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$1] $2" | tee -a "$LOG_FILE"
}}

send_status() {{
    cat > "$STATUS_FILE" << EOF
{{"agent":"DumontAgent","version":"$VERSION","instance_id":"$INSTANCE_ID","status":"$1","message":"$2","timestamp":"$(date -Iseconds)"}}
EOF
    if [ -n "$DUMONT_SERVER" ]; then
        curl -s -X POST "$DUMONT_SERVER/api/agent/status" -H "Content-Type: application/json" -d @"$STATUS_FILE" >/dev/null 2>&1 || true
    fi
}}

do_backup() {{
    log "INFO" "Iniciando backup de $SYNC_DIRS..."
    send_status "syncing" "Backup em progresso"
    if restic backup "$SYNC_DIRS" --tag auto --tag "instance:$INSTANCE_ID" --quiet -o s3.connections=16 2>&1 | tee -a "$LOG_FILE"; then
        log "INFO" "Backup concluido"
        send_status "idle" "Backup concluido"
        restic forget --keep-last 10 --tag auto --quiet 2>/dev/null
        return 0
    else
        log "ERROR" "Backup falhou"
        send_status "error" "Backup falhou"
        return 1
    fi
}}

if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        exit 0
    fi
fi
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

log "INFO" "=== DumontAgent v$VERSION Iniciado ==="
send_status "starting" "Agente iniciado"

while true; do
    if [ -d "$SYNC_DIRS" ]; then
        HASH=$(find "$SYNC_DIRS" -type f -mmin -1 2>/dev/null | sort | md5sum | cut -d" " -f1)
        if [ -n "$HASH" ]; then
            do_backup
        fi
    fi
    sleep "$INTERVAL"
done
AGENT_EOF
chmod +x "$INSTALL_DIR/dumont-agent.sh"

# Iniciar agente
pkill -f "dumont-agent.sh" 2>/dev/null || true
sleep 1
nohup "$INSTALL_DIR/dumont-agent.sh" > /dev/null 2>&1 &
sleep 2

if pgrep -f "dumont-agent.sh" > /dev/null; then
    echo "AGENT_INSTALLED=yes"
    echo "AGENT_PID=$(pgrep -f dumont-agent.sh)"
else
    echo "AGENT_INSTALLED=no"
fi
'''

        success, output = self._ssh_cmd(install_script, timeout=180)

        agent_installed = "AGENT_INSTALLED=yes" in output

        return {
            "success": agent_installed,
            "message": "DumontAgent instalado e rodando" if agent_installed else f"Falha: {output}",
            "output": output
        }

    def setup_lsyncd(self, config: MachineSetupConfig) -> Dict[str, Any]:
        """Configura lsyncd para sync em tempo real com CPU backup"""

        if not config.backup_host:
            return {"success": False, "error": "backup_host nao configurado"}

        lsyncd_script = f'''#!/bin/bash
apt-get update -qq
apt-get install -y lsyncd

mkdir -p /etc/lsyncd /var/log/lsyncd

cat > /etc/lsyncd/lsyncd.conf.lua << 'LSYNC_EOF'
settings {{
    logfile = "/var/log/lsyncd/lsyncd.log",
    statusFile = "/var/log/lsyncd/lsyncd.status",
    statusInterval = 5,
    maxDelays = 1,
    maxProcesses = 10,
}}

sync {{
    default.rssh,
    source = "{config.workspace}",
    host = "{config.backup_host}",
    targetdir = "{config.workspace}",
    rsync = {{
        archive = true,
        compress = true,
        _extra = {{
            "--delete",
            "--exclude=.git",
            "--exclude=.vscode-server",
            "--exclude=__pycache__",
            "--bwlimit=10000",
        }}
    }},
    ssh = {{
        _extra = {{"-o", "StrictHostKeyChecking=no"}}
    }},
    delay = 1,
}}
LSYNC_EOF

systemctl daemon-reload
systemctl enable lsyncd
systemctl restart lsyncd
sleep 2

if systemctl is-active --quiet lsyncd; then
    echo "LSYNCD_INSTALLED=yes"
else
    echo "LSYNCD_INSTALLED=no"
fi
'''

        success, output = self._ssh_cmd(lsyncd_script, timeout=120)

        lsyncd_installed = "LSYNCD_INSTALLED=yes" in output

        return {
            "success": lsyncd_installed,
            "message": f"Lsyncd configurado para sync com {config.backup_host}" if lsyncd_installed else f"Falha: {output}"
        }

    def setup_full(self, config: Optional[MachineSetupConfig] = None) -> Dict[str, Any]:
        """
        Setup completo da maquina GPU com resiliencia.

        Pre-checks:
        - Verifica conectividade SSH
        - Verifica GPU disponivel

        Instala todos os componentes configurados:
        1. Cria /workspace
        2. Instala code-server (VS Code Web)
        3. Instala DumontAgent (backup automatico)
        4. Configura lsyncd (sync tempo real - opcional)

        Returns:
            Dict com resultado de cada etapa
        """
        config = config or MachineSetupConfig()
        results = {
            "success": True,
            "steps": [],
            "ssh_host": self.ssh_host,
            "ssh_port": self.ssh_port,
        }

        # 0. Pre-check: Conectividade SSH
        logger.info(f"Verificando conectividade SSH com {self.ssh_host}:{self.ssh_port}")
        ssh_check = self.check_ssh_connectivity(timeout=config.ssh_timeout)
        results["steps"].append({"step": "ssh_check", **ssh_check})
        if not ssh_check.get("success"):
            results["success"] = False
            results["error"] = "Falha na conectividade SSH"
            return results

        # 0b. Pre-check: GPU disponivel
        gpu_check = self.check_gpu_available()
        results["steps"].append({"step": "gpu_check", **gpu_check})
        if gpu_check.get("gpu"):
            results["gpu"] = gpu_check["gpu"]
            logger.info(f"GPU encontrada: {gpu_check['gpu']}")

        # 1. Criar workspace
        workspace_result = self.setup_workspace(config.workspace)
        results["steps"].append({"step": "workspace", **workspace_result})

        # 2. Code-server
        if config.setup_codeserver:
            cs_result = self.setup_codeserver(config)
            results["steps"].append({"step": "codeserver", **cs_result})
            if cs_result.get("success"):
                results["codeserver_url"] = f"http://{self.ssh_host}:{config.codeserver_port}/"

        # 3. DumontAgent
        if config.setup_agent:
            agent_result = self.setup_dumont_agent(config)
            results["steps"].append({"step": "dumont_agent", **agent_result})

        # 4. Lsyncd (opcional)
        if config.setup_lsyncd and config.backup_host:
            lsyncd_result = self.setup_lsyncd(config)
            results["steps"].append({"step": "lsyncd", **lsyncd_result})

        # Verificar se todas as etapas obrigatorias passaram
        for step in results["steps"]:
            if not step.get("success", False):
                results["success"] = False
                results["error"] = f"Falha em: {step.get('step')}"
                break

        if results["success"]:
            results["message"] = "Setup completo da maquina GPU finalizado com sucesso"

        return results


def setup_gpu_machine(
    ssh_host: str,
    ssh_port: int,
    workspace: str = "/workspace",
    setup_codeserver: bool = True,
    setup_agent: bool = True,
    dumont_server: str = "",
    instance_id: str = "",
    restic_repository: str = "",
    restic_password: str = "",
    aws_access_key_id: str = "",
    aws_secret_access_key: str = "",
    setup_lsyncd: bool = False,
    backup_host: str = "",
) -> Dict[str, Any]:
    """
    Funcao helper para setup rapido de maquina GPU.

    Exemplo:
        result = setup_gpu_machine(
            ssh_host="12.16.140.162",
            ssh_port=30278,
            setup_codeserver=True,
            setup_agent=True,
            instance_id="29257475",
        )
    """
    config = MachineSetupConfig(
        workspace=workspace,
        setup_codeserver=setup_codeserver,
        setup_agent=setup_agent,
        dumont_server=dumont_server,
        instance_id=instance_id,
        restic_repository=restic_repository,
        restic_password=restic_password,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        setup_lsyncd=setup_lsyncd,
        backup_host=backup_host,
    )

    service = MachineSetupService(ssh_host, ssh_port)
    return service.setup_full(config)
