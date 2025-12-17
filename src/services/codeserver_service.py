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
    # Dumont Cloud integration
    dumont_api_url: str = ""
    dumont_auth_token: str = ""
    dumont_machine_id: str = ""


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

    def install_machine_switcher_extension(self, config: CodeServerConfig) -> Dict[str, Any]:
        """
        Instala a extensao Dumont Machine Switcher no code-server.

        A extensao permite trocar entre maquinas GPU diretamente do VS Code.

        Args:
            config: Configuracao com credenciais do Dumont Cloud

        Returns:
            Dict com status da instalacao
        """
        import json

        # URL do .vsix hospedado (pode ser local ou remoto)
        # Por enquanto, vamos criar a configuracao para a extensao funcionar

        # Determinar diretorio home baseado no usuario
        if config.user == "root":
            home_dir = "/root"
        else:
            home_dir = f"/home/{config.user}"

        # Criar arquivo de configuracao do Dumont
        dumont_config = {
            "api_url": config.dumont_api_url,
            "auth_token": config.dumont_auth_token,
            "machine_id": config.dumont_machine_id
        }
        dumont_config_json = json.dumps(dumont_config, indent=2)

        setup_script = f"""
# Criar diretorio de configuracao do Dumont
mkdir -p {home_dir}/.dumont

# Salvar configuracao
cat > {home_dir}/.dumont/config.json << 'DUMONT_CONFIG_EOF'
{dumont_config_json}
DUMONT_CONFIG_EOF

# Configurar variaveis de ambiente para code-server
mkdir -p {home_dir}/.config/code-server

# Adicionar variaveis ao profile para persistencia
cat >> {home_dir}/.bashrc << 'BASHRC_EOF'

# Dumont Cloud Environment
export DUMONT_API_URL="{config.dumont_api_url}"
export DUMONT_AUTH_TOKEN="{config.dumont_auth_token}"
export DUMONT_MACHINE_ID="{config.dumont_machine_id}"
BASHRC_EOF

echo "Dumont Machine Switcher configurado"
"""

        success, output = self._ssh_cmd(setup_script, timeout=30)

        if not success:
            return {"success": False, "error": f"Falha ao configurar extensao: {output}"}

        return {
            "success": True,
            "message": "Dumont Machine Switcher configurado",
            "config_path": f"{home_dir}/.dumont/config.json"
        }

    def install_vsix_extension(self, vsix_url: str) -> Dict[str, Any]:
        """
        Instala uma extensao .vsix no code-server.

        Args:
            vsix_url: URL do arquivo .vsix para download

        Returns:
            Dict com status da instalacao
        """
        install_script = f"""
# Baixar extensao
cd /tmp
curl -fsSL -o extension.vsix "{vsix_url}"

# Instalar via code-server
~/.local/bin/code-server --install-extension /tmp/extension.vsix

# Limpar
rm -f /tmp/extension.vsix

echo "Extensao instalada"
"""

        success, output = self._ssh_cmd(install_script, timeout=120)

        if not success:
            return {"success": False, "error": f"Falha ao instalar extensao: {output}"}

        return {"success": True, "message": "Extensao instalada com sucesso"}

    def setup_full(self, config: Optional[CodeServerConfig] = None, vsix_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Instalacao e configuracao completa do code-server.
        Metodo conveniente que executa install + configure + start + extensao.

        Args:
            config: Configuracao do code-server
            vsix_url: URL opcional do .vsix da extensao Machine Switcher

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

        # 3. Configurar Machine Switcher (se credenciais fornecidas)
        if config.dumont_api_url and config.dumont_auth_token:
            switcher_result = self.install_machine_switcher_extension(config)
            results["steps"].append({"step": "machine_switcher_config", **switcher_result})

            # Instalar extensao .vsix se URL fornecida
            if vsix_url:
                vsix_result = self.install_vsix_extension(vsix_url)
                results["steps"].append({"step": "machine_switcher_vsix", **vsix_result})

        # 4. Iniciar
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
    dumont_api_url: str = "",
    dumont_auth_token: str = "",
    dumont_machine_id: str = "",
    vsix_url: Optional[str] = None,
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
        dumont_api_url: URL da API do Dumont Cloud (para Machine Switcher)
        dumont_auth_token: Token JWT do Dumont Cloud
        dumont_machine_id: ID da maquina atual
        vsix_url: URL do arquivo .vsix da extensao Machine Switcher

    Returns:
        Dict com resultado do setup
    """
    config = CodeServerConfig(
        port=code_port,
        workspace=workspace,
        theme=theme,
        user=ssh_user,
        dumont_api_url=dumont_api_url,
        dumont_auth_token=dumont_auth_token,
        dumont_machine_id=dumont_machine_id,
    )

    service = CodeServerService(ssh_host, ssh_port, ssh_user)
    return service.setup_full(config, vsix_url=vsix_url)
