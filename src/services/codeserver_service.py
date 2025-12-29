"""
Service para instalacao e configuracao do code-server em instancias GPU.

Versao 2.0 - Com resiliencia:
- Retry com backoff exponencial
- Liberacao automatica de porta
- Health check apos iniciar
- Tratamento robusto de erros
"""
import subprocess
import time
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CodeServerConfig:
    """Configuracao do code-server"""
    port: int = 8080
    auth: str = "none"
    workspace: str = "/workspace"
    theme: str = "Default Dark+"
    trust_enabled: bool = False
    font_size: int = 14
    auto_save: bool = True
    user: str = "root"
    # Dumont Cloud integration
    dumont_api_url: str = ""
    dumont_auth_token: str = ""
    dumont_machine_id: str = ""
    # Resiliencia
    max_retries: int = 3
    retry_delay: float = 2.0
    health_check_timeout: int = 10


class CodeServerService:
    """
    Service resiliente para gerenciar code-server em instancias remotas.

    Features:
    - Retry automatico com backoff exponencial
    - Liberacao de porta antes de iniciar
    - Health check HTTP apos iniciar
    - Fallback para portas alternativas
    """

    INSTALL_SCRIPT = "curl -fsSL https://code-server.dev/install.sh | sh -s -- --method=standalone"

    DEFAULT_SETTINGS = {
        "workbench.colorTheme": "Default Dark+",
        "security.workspace.trust.enabled": False,
        "security.workspace.trust.startupPrompt": "never",
        "security.workspace.trust.banner": "never",
        "security.workspace.trust.untrustedFiles": "open",
        "editor.fontSize": 14,
        "editor.fontFamily": "'Fira Code', 'Droid Sans Mono', 'monospace'",
        "editor.minimap.enabled": True,
        "editor.wordWrap": "on",
        "terminal.integrated.fontSize": 13,
        "files.autoSave": "afterDelay",
        "files.autoSaveDelay": 1000,
        "workbench.startupEditor": "none",
    }

    def __init__(self, ssh_host: str, ssh_port: int, ssh_user: str = "root"):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user

    def _ssh_cmd(
        self,
        command: str,
        timeout: int = 60,
        retries: int = 3,
        retry_delay: float = 2.0
    ) -> Tuple[bool, str]:
        """
        Executa comando via SSH com retry automatico.

        Args:
            command: Comando a executar
            timeout: Timeout em segundos
            retries: Numero de tentativas
            retry_delay: Delay entre tentativas (com backoff)

        Returns:
            Tupla (sucesso, output)
        """
        import os
        ssh_key = os.path.expanduser("~/.ssh/id_rsa")
        ssh_command = [
            "ssh",
            "-i", ssh_key,
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
                else:
                    return False, output

            except subprocess.TimeoutExpired:
                last_error = f"Timeout ({timeout}s) na tentativa {attempt + 1}"
            except Exception as e:
                last_error = str(e)

            if attempt < retries - 1:
                delay = retry_delay * (2 ** attempt)  # Backoff exponencial
                time.sleep(delay)

        return False, f"Falha apos {retries} tentativas: {last_error}"

    def _ensure_port_free(self, port: int) -> bool:
        """Garante que a porta esta livre, matando processo se necessario."""
        # Primeiro tenta pkill do code-server
        self._ssh_cmd(f"pkill -f 'code-server.*{port}' 2>/dev/null || true", timeout=10, retries=1)

        # Depois usa fuser para matar qualquer coisa na porta
        self._ssh_cmd(f"fuser -k {port}/tcp 2>/dev/null || true", timeout=10, retries=1)

        # Aguarda um pouco
        time.sleep(1)

        # Verifica se a porta esta livre
        success, output = self._ssh_cmd(
            f"netstat -tlnp 2>/dev/null | grep ':{port} ' || ss -tlnp | grep ':{port} ' || echo 'PORT_FREE'",
            timeout=10, retries=1
        )

        return "PORT_FREE" in output or not output.strip()

    def _health_check(self, port: int, timeout: int = 10) -> bool:
        """Verifica se code-server esta respondendo via HTTP."""
        success, output = self._ssh_cmd(
            f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout 5 http://localhost:{port}/ || echo 'FAIL'",
            timeout=timeout, retries=2
        )
        return success and ("200" in output or "302" in output)

    def is_installed(self) -> bool:
        """Verifica se code-server esta instalado"""
        success, output = self._ssh_cmd(
            "test -x ~/.local/bin/code-server && ~/.local/bin/code-server --version >/dev/null 2>&1 && echo 'CS_INSTALLED' || echo 'CS_NOT_FOUND'",
            retries=2
        )
        return success and "CS_INSTALLED" in output and "CS_NOT_FOUND" not in output

    def install(self, config: Optional[CodeServerConfig] = None) -> Dict[str, Any]:
        """Instala code-server com retry."""
        config = config or CodeServerConfig()

        if self.is_installed():
            return {"success": True, "message": "code-server ja instalado", "already_installed": True}

        # Garantir dependencias
        self._ssh_cmd("apt-get update -qq && apt-get install -y -qq curl", timeout=60, retries=2)

        # Instalar code-server
        success, output = self._ssh_cmd(
            self.INSTALL_SCRIPT,
            timeout=180,
            retries=config.max_retries
        )

        if not success:
            return {"success": False, "error": f"Falha na instalacao: {output}"}

        # Verificar instalacao
        if self.is_installed():
            return {"success": True, "message": "code-server instalado com sucesso"}

        return {"success": False, "error": "Instalacao completou mas binario nao encontrado"}

    def configure(self, config: Optional[CodeServerConfig] = None) -> Dict[str, Any]:
        """Configura code-server com settings personalizados."""
        import json

        config = config or CodeServerConfig()

        settings = self.DEFAULT_SETTINGS.copy()
        settings["workbench.colorTheme"] = config.theme
        settings["security.workspace.trust.enabled"] = config.trust_enabled
        settings["editor.fontSize"] = config.font_size

        if not config.auto_save:
            settings["files.autoSave"] = "off"

        settings_json = json.dumps(settings, indent=4)

        if config.user == "root":
            config_dir = "/root/.local/share/code-server/User"
            home_dir = "/root"
        else:
            config_dir = f"/home/{config.user}/.local/share/code-server/User"
            home_dir = f"/home/{config.user}"

        setup_script = f"""
mkdir -p {config_dir}
mkdir -p {home_dir}/.config/code-server

# Settings do VS Code
cat > {config_dir}/settings.json << 'SETTINGS_EOF'
{settings_json}
SETTINGS_EOF

# Config do code-server
cat > {home_dir}/.config/code-server/config.yaml << 'CONFIG_EOF'
bind-addr: 0.0.0.0:{config.port}
auth: {config.auth}
cert: false
CONFIG_EOF

echo "CONFIGURED"
"""

        success, output = self._ssh_cmd(setup_script, retries=config.max_retries)

        if success and "CONFIGURED" in output:
            return {"success": True, "message": "code-server configurado", "config_dir": config_dir}

        return {"success": False, "error": f"Falha na configuracao: {output}"}

    def start(self, config: Optional[CodeServerConfig] = None) -> Dict[str, Any]:
        """
        Inicia code-server com resiliencia.

        - Libera porta automaticamente
        - Cria workspace se nao existir
        - Faz health check apos iniciar
        - Tenta portas alternativas se necessario
        """
        config = config or CodeServerConfig()
        port = config.port

        # 1. Criar workspace
        self._ssh_cmd(f"mkdir -p {config.workspace}", timeout=10, retries=2)

        # 2. Tentar na porta configurada e alternativas
        ports_to_try = [port, port + 1, port + 2, 8888, 9000]

        for try_port in ports_to_try:
            # Liberar porta
            if not self._ensure_port_free(try_port):
                continue

            # Iniciar code-server
            start_cmd = f"""
nohup ~/.local/bin/code-server \\
    --auth {config.auth} \\
    --bind-addr 0.0.0.0:{try_port} \\
    --disable-telemetry \\
    {config.workspace} > /tmp/code-server-{try_port}.log 2>&1 &

# Aguardar inicializacao
for i in 1 2 3 4 5; do
    sleep 1
    if pgrep -f "code-server.*{try_port}" > /dev/null; then
        echo "STARTED_PORT_{try_port}"
        exit 0
    fi
done
echo "FAILED"
"""
            success, output = self._ssh_cmd(start_cmd, timeout=30, retries=1)

            if success and f"STARTED_PORT_{try_port}" in output:
                # Health check
                time.sleep(2)
                if self._health_check(try_port, config.health_check_timeout):
                    return {
                        "success": True,
                        "message": f"code-server rodando na porta {try_port}",
                        "port": try_port,
                        "workspace": config.workspace,
                        "url": f"http://{self.ssh_host}:{try_port}/"
                    }

        return {"success": False, "error": f"Falha ao iniciar em todas as portas tentadas: {ports_to_try}"}

    def stop(self) -> Dict[str, Any]:
        """Para code-server."""
        success, output = self._ssh_cmd("pkill -f code-server || true", timeout=10, retries=2)
        time.sleep(1)

        # Verificar se parou
        check_success, check_output = self._ssh_cmd("pgrep -f code-server || echo 'STOPPED'", timeout=10, retries=1)

        if "STOPPED" in check_output:
            return {"success": True, "message": "code-server parado"}
        return {"success": False, "message": "code-server pode ainda estar rodando"}

    def status(self) -> Dict[str, Any]:
        """Retorna status detalhado do code-server."""
        success, output = self._ssh_cmd("""
if pgrep -f code-server > /dev/null; then
    PORT=$(netstat -tlnp 2>/dev/null | grep code-server | awk '{print $4}' | grep -oE '[0-9]+$' | head -1)
    PORT=${PORT:-$(ss -tlnp | grep code-server | awk '{print $4}' | grep -oE '[0-9]+$' | head -1)}
    echo "RUNNING:$PORT"
else
    echo "STOPPED"
fi
""", retries=2)

        if "RUNNING:" in output:
            port = output.split("RUNNING:")[1].strip().split()[0]
            return {
                "running": True,
                "port": int(port) if port.isdigit() else None,
                "healthy": self._health_check(int(port)) if port.isdigit() else False
            }

        return {"running": False, "port": None, "healthy": False}

    def restart(self, config: Optional[CodeServerConfig] = None) -> Dict[str, Any]:
        """Reinicia code-server."""
        self.stop()
        time.sleep(2)
        return self.start(config)

    def setup_full(self, config: Optional[CodeServerConfig] = None, vsix_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Instalacao e configuracao completa com resiliencia.
        """
        config = config or CodeServerConfig()
        results = {"steps": [], "success": False}

        # 1. Instalar
        install_result = self.install(config)
        results["steps"].append({"step": "install", **install_result})

        if not install_result.get("success") and not install_result.get("already_installed"):
            results["error"] = "Falha na instalacao"
            return results

        # 2. Configurar
        config_result = self.configure(config)
        results["steps"].append({"step": "configure", **config_result})

        if not config_result.get("success"):
            results["error"] = "Falha na configuracao"
            return results

        # 3. Iniciar
        start_result = self.start(config)
        results["steps"].append({"step": "start", **start_result})

        if not start_result.get("success"):
            # Tentar uma vez mais com restart
            restart_result = self.restart(config)
            results["steps"].append({"step": "restart", **restart_result})

            if not restart_result.get("success"):
                results["error"] = "Falha ao iniciar"
                return results

            start_result = restart_result

        results["success"] = True
        results["message"] = f"code-server instalado e rodando na porta {start_result.get('port', config.port)}"
        results["port"] = start_result.get("port", config.port)
        results["url"] = start_result.get("url", f"http://{self.ssh_host}:{config.port}/")

        return results


def setup_codeserver_on_instance(
    ssh_host: str,
    ssh_port: int,
    ssh_user: str = "root",
    code_port: int = 8080,
    workspace: str = "/workspace",
    theme: str = "Default Dark+",
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Funcao helper para setup rapido do code-server.
    """
    config = CodeServerConfig(
        port=code_port,
        workspace=workspace,
        theme=theme,
        user=ssh_user,
        max_retries=max_retries,
    )

    service = CodeServerService(ssh_host, ssh_port, ssh_user)
    return service.setup_full(config)
