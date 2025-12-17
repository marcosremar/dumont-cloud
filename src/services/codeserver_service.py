"""
Service para instalacao e configuracao do code-server em instancias GPU.

Responsabilidades (Single Responsibility):
- Instalar code-server via script oficial
- Configurar settings (tema, trust, etc)
- Iniciar/parar code-server
- Verificar status
"""
import subprocess
from typing import Optional, Dict, Any
from dataclasses import dataclass


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


class CodeServerService:
    """Service para gerenciar code-server em instancias remotas"""

    # Script de instalacao do code-server
    INSTALL_SCRIPT = "curl -fsSL https://code-server.dev/install.sh | sh -s -- --method=standalone"

    # Configuracoes padrao do VS Code
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
        """
        Inicializa o service com conexao SSH.

        Args:
            ssh_host: IP ou hostname do servidor
            ssh_port: Porta SSH
            ssh_user: Usuario SSH (padrao: root)
        """
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user

    def _ssh_cmd(self, command: str, timeout: int = 60) -> tuple[bool, str]:
        """
        Executa comando via SSH.

        Args:
            command: Comando a executar
            timeout: Timeout em segundos

        Returns:
            Tupla (sucesso, output)
        """
        ssh_command = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout={min(timeout, 30)}",
            "-p", str(self.ssh_port),
            f"{self.ssh_user}@{self.ssh_host}",
            command
        ]

        try:
            result = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = result.stdout + result.stderr
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "Timeout ao executar comando SSH"
        except Exception as e:
            return False, str(e)

    def is_installed(self) -> bool:
        """Verifica se code-server esta instalado"""
        success, output = self._ssh_cmd("which code-server || ls ~/.local/bin/code-server 2>/dev/null")
        return success and ("code-server" in output)

    def install(self, config: Optional[CodeServerConfig] = None) -> Dict[str, Any]:
        """
        Instala code-server na instancia.

        Args:
            config: Configuracao opcional (usa padrao se nao especificado)

        Returns:
            Dict com status da instalacao
        """
        config = config or CodeServerConfig()

        # Verificar se ja esta instalado
        if self.is_installed():
            return {"success": True, "message": "code-server ja instalado", "already_installed": True}

        # Instalar code-server
        success, output = self._ssh_cmd(self.INSTALL_SCRIPT, timeout=120)

        if not success:
            return {"success": False, "error": f"Falha na instalacao: {output}"}

        return {"success": True, "message": "code-server instalado com sucesso"}

    def configure(self, config: Optional[CodeServerConfig] = None) -> Dict[str, Any]:
        """
        Configura code-server com settings personalizados.

        Args:
            config: Configuracao do code-server

        Returns:
            Dict com status da configuracao
        """
        import json

        config = config or CodeServerConfig()

        # Montar settings.json
        settings = self.DEFAULT_SETTINGS.copy()
        settings["workbench.colorTheme"] = config.theme
        settings["security.workspace.trust.enabled"] = config.trust_enabled
        settings["editor.fontSize"] = config.font_size

        if not config.auto_save:
            settings["files.autoSave"] = "off"

        settings_json = json.dumps(settings, indent=4)

        # Determinar diretorio de configuracao baseado no usuario
        if config.user == "root":
            config_dir = "/root/.local/share/code-server/User"
        else:
            config_dir = f"/home/{config.user}/.local/share/code-server/User"

        # Criar diretorio e settings
        setup_script = f"""
mkdir -p {config_dir}
cat > {config_dir}/settings.json << 'SETTINGS_EOF'
{settings_json}
SETTINGS_EOF
echo "Settings configurados em {config_dir}/settings.json"
"""

        success, output = self._ssh_cmd(setup_script)

        if not success:
            return {"success": False, "error": f"Falha na configuracao: {output}"}

        return {"success": True, "message": "code-server configurado", "config_dir": config_dir}

    def start(self, config: Optional[CodeServerConfig] = None) -> Dict[str, Any]:
        """
        Inicia code-server.

        Args:
            config: Configuracao do code-server

        Returns:
            Dict com status
        """
        config = config or CodeServerConfig()

        # Parar instancia existente
        self._ssh_cmd("pkill -f code-server 2>/dev/null", timeout=10)

        # Iniciar code-server
        start_cmd = f"""
sleep 2
nohup ~/.local/bin/code-server --auth {config.auth} --bind-addr 0.0.0.0:{config.port} {config.workspace} > /tmp/code-server.log 2>&1 &
sleep 3
pgrep -f code-server > /dev/null && echo "RUNNING" || echo "FAILED"
"""

        success, output = self._ssh_cmd(start_cmd, timeout=30)

        if "RUNNING" in output:
            return {
                "success": True,
                "message": f"code-server rodando na porta {config.port}",
                "port": config.port,
                "workspace": config.workspace
            }

        return {"success": False, "error": f"Falha ao iniciar: {output}"}

    def stop(self) -> Dict[str, Any]:
        """Para code-server"""
        success, output = self._ssh_cmd("pkill -f code-server", timeout=10)
        return {"success": True, "message": "code-server parado"}

    def status(self) -> Dict[str, Any]:
        """Retorna status do code-server"""
        success, output = self._ssh_cmd("pgrep -f code-server && echo 'RUNNING' || echo 'STOPPED'")

        if "RUNNING" in output:
            # Pegar porta em uso
            port_check = self._ssh_cmd("netstat -tlnp 2>/dev/null | grep code-server | head -1")
            return {"running": True, "output": output}

        return {"running": False, "output": output}

    def setup_full(self, config: Optional[CodeServerConfig] = None) -> Dict[str, Any]:
        """
        Instalacao e configuracao completa do code-server.
        Metodo conveniente que executa install + configure + start.

        Args:
            config: Configuracao do code-server

        Returns:
            Dict com status de cada etapa
        """
        config = config or CodeServerConfig()
        results = {"steps": []}

        # 1. Instalar
        install_result = self.install(config)
        results["steps"].append({"step": "install", **install_result})

        if not install_result["success"] and not install_result.get("already_installed"):
            results["success"] = False
            results["error"] = "Falha na instalacao"
            return results

        # 2. Configurar
        config_result = self.configure(config)
        results["steps"].append({"step": "configure", **config_result})

        if not config_result["success"]:
            results["success"] = False
            results["error"] = "Falha na configuracao"
            return results

        # 3. Iniciar
        start_result = self.start(config)
        results["steps"].append({"step": "start", **start_result})

        if not start_result["success"]:
            results["success"] = False
            results["error"] = "Falha ao iniciar"
            return results

        results["success"] = True
        results["message"] = f"code-server instalado e rodando na porta {config.port}"
        results["port"] = config.port

        return results


def setup_codeserver_on_instance(
    ssh_host: str,
    ssh_port: int,
    ssh_user: str = "root",
    code_port: int = 8080,
    workspace: str = "/workspace",
    theme: str = "Default Dark+",
) -> Dict[str, Any]:
    """
    Funcao helper para setup rapido do code-server.

    Args:
        ssh_host: IP do servidor
        ssh_port: Porta SSH
        ssh_user: Usuario SSH
        code_port: Porta do code-server
        workspace: Diretorio workspace
        theme: Tema do VS Code

    Returns:
        Dict com resultado do setup
    """
    config = CodeServerConfig(
        port=code_port,
        workspace=workspace,
        theme=theme,
        user=ssh_user,
    )

    service = CodeServerService(ssh_host, ssh_port, ssh_user)
    return service.setup_full(config)
