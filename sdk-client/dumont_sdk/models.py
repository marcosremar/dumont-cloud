"""
Módulo de gerenciamento de modelos LLM.

Instala e gerencia modelos via Ollama em instâncias GPU.
"""
import asyncio
import logging
import re
import shlex
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Regex para validar nomes de modelos Ollama (ex: llama3.2, qwen3:0.6b, codellama:7b)
MODEL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*(?::[a-zA-Z0-9._-]+)?$')


def _validate_model_name(model: str) -> str:
    """
    Valida e sanitiza nome de modelo para prevenir command injection.

    Args:
        model: Nome do modelo (ex: llama3.2, qwen3:0.6b)

    Returns:
        Nome do modelo validado

    Raises:
        ValueError: Se o nome do modelo for inválido
    """
    if not model or not isinstance(model, str):
        raise ValueError("Nome do modelo não pode ser vazio")

    model = model.strip()

    if len(model) > 100:
        raise ValueError("Nome do modelo muito longo (máximo 100 caracteres)")

    if not MODEL_NAME_PATTERN.match(model):
        raise ValueError(
            f"Nome de modelo inválido: {model!r}. "
            "Use apenas letras, números, pontos, hífens e underscores. "
            "Formato: nome ou nome:tag"
        )

    return model


@dataclass
class InstalledModel:
    """Modelo instalado em uma instância."""
    name: str
    size: str
    modified_at: Optional[str] = None
    digest: Optional[str] = None


@dataclass
class ModelInstallResult:
    """Resultado da instalação de um modelo."""
    success: bool
    model_name: str
    instance_id: int
    ollama_url: Optional[str] = None
    ssh_command: Optional[str] = None
    error: Optional[str] = None


class ModelsClient:
    """
    Cliente para gerenciamento de modelos LLM.

    Instala Ollama e modelos em instâncias GPU via SSH.

    Exemplo:
        async with DumontClient(api_key="...") as client:
            # Instalar modelo
            result = await client.models.install(
                instance_id=12345,
                model="llama3.2"
            )
            print(f"Ollama URL: {result.ollama_url}")

            # Listar modelos instalados
            models = await client.models.list(instance_id=12345)
    """

    def __init__(self, base_client):
        self._client = base_client

    async def install(
        self,
        instance_id: int,
        model: str,
        timeout: int = 1800,  # 30 minutos
    ) -> ModelInstallResult:
        """
        Instala Ollama e um modelo em uma instância.

        Args:
            instance_id: ID da instância
            model: Nome do modelo (ex: llama3.2, qwen3:0.6b, codellama:7b)
            timeout: Timeout em segundos

        Returns:
            ModelInstallResult com detalhes da instalação
        """
        # Validar nome do modelo para prevenir command injection
        try:
            model = _validate_model_name(model)
        except ValueError as e:
            return ModelInstallResult(
                success=False,
                model_name=model if isinstance(model, str) else "",
                instance_id=instance_id,
                error=str(e),
            )

        # Buscar info da instância
        from .instances import InstancesClient
        instances = InstancesClient(self._client)

        try:
            instance = await instances.get(instance_id)
        except Exception as e:
            return ModelInstallResult(
                success=False,
                model_name=model,
                instance_id=instance_id,
                error=f"Instância não encontrada: {e}",
            )

        if not instance.is_running:
            return ModelInstallResult(
                success=False,
                model_name=model,
                instance_id=instance_id,
                error=f"Instância não está rodando (status: {instance.status})",
            )

        host = instance.public_ipaddr or instance.ssh_host
        port = instance.ssh_port

        if not host or not port:
            return ModelInstallResult(
                success=False,
                model_name=model,
                instance_id=instance_id,
                error="Informações de SSH não disponíveis",
            )

        # Script de instalação do Ollama
        install_script = '''#!/bin/bash
set -e

echo ">>> Checking for Ollama..."
if command -v ollama &> /dev/null; then
    echo "OLLAMA_STATUS=already_installed"
else
    echo ">>> Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "OLLAMA_STATUS=installed"
fi

# Start Ollama service if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo ">>> Starting Ollama service..."
    nohup ollama serve > /var/log/ollama.log 2>&1 &
    sleep 3
fi

# Verify Ollama is running
if pgrep -x "ollama" > /dev/null; then
    echo "OLLAMA_RUNNING=yes"
else
    echo "OLLAMA_RUNNING=no"
fi

echo "OLLAMA_INSTALL_COMPLETE=yes"
'''

        # Executar instalação do Ollama
        try:
            ollama_result = await self._run_ssh_command(
                host, port, install_script, timeout=300
            )

            if "OLLAMA_INSTALL_COMPLETE=yes" not in ollama_result:
                return ModelInstallResult(
                    success=False,
                    model_name=model,
                    instance_id=instance_id,
                    error=f"Falha na instalação do Ollama: {ollama_result}",
                )

        except Exception as e:
            return ModelInstallResult(
                success=False,
                model_name=model,
                instance_id=instance_id,
                error=f"Erro SSH ao instalar Ollama: {e}",
            )

        # Script para baixar o modelo
        pull_script = f'''#!/bin/bash

# Ensure Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    nohup ollama serve > /var/log/ollama.log 2>&1 &
    sleep 3
fi

echo ">>> Pulling model: {model}"
ollama pull {model}
PULL_STATUS=$?

if [ $PULL_STATUS -eq 0 ]; then
    echo "MODEL_PULL_SUCCESS=yes"
    echo "MODEL_NAME={model}"
else
    echo "MODEL_PULL_SUCCESS=no"
    echo "MODEL_PULL_ERROR=$PULL_STATUS"
fi

# List installed models
echo ">>> Installed models:"
ollama list
'''

        # Executar pull do modelo
        try:
            pull_result = await self._run_ssh_command(
                host, port, pull_script, timeout=timeout
            )

            if "MODEL_PULL_SUCCESS=yes" not in pull_result:
                return ModelInstallResult(
                    success=False,
                    model_name=model,
                    instance_id=instance_id,
                    error=f"Falha ao baixar modelo: {pull_result}",
                )

        except asyncio.TimeoutError:
            return ModelInstallResult(
                success=False,
                model_name=model,
                instance_id=instance_id,
                error=f"Timeout ao baixar modelo (>{timeout}s)",
            )
        except Exception as e:
            return ModelInstallResult(
                success=False,
                model_name=model,
                instance_id=instance_id,
                error=f"Erro SSH ao baixar modelo: {e}",
            )

        # Sucesso!
        ollama_port = 11434
        return ModelInstallResult(
            success=True,
            model_name=model,
            instance_id=instance_id,
            ollama_url=f"http://{host}:{ollama_port}",
            ssh_command=f"ssh -p {port} root@{host}",
        )

    async def list(self, instance_id: int) -> List[InstalledModel]:
        """
        Lista modelos instalados em uma instância.

        Args:
            instance_id: ID da instância

        Returns:
            Lista de modelos instalados
        """
        from .instances import InstancesClient
        instances = InstancesClient(self._client)

        instance = await instances.get(instance_id)
        if not instance.is_running:
            return []

        host = instance.public_ipaddr or instance.ssh_host
        port = instance.ssh_port

        if not host or not port:
            return []

        try:
            result = await self._run_ssh_command(
                host, port,
                "ollama list 2>/dev/null | tail -n +2",
                timeout=30
            )

            models = []
            for line in result.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        models.append(InstalledModel(
                            name=parts[0],
                            size=parts[1] if len(parts) > 1 else "unknown",
                            modified_at=parts[2] if len(parts) > 2 else None,
                        ))

            return models

        except Exception as e:
            logger.warning(f"Erro ao listar modelos: {e}")
            return []

    async def remove(self, instance_id: int, model: str) -> bool:
        """
        Remove um modelo de uma instância.

        Args:
            instance_id: ID da instância
            model: Nome do modelo

        Returns:
            True se removido com sucesso
        """
        # Validar nome do modelo para prevenir command injection
        try:
            model = _validate_model_name(model)
        except ValueError as e:
            logger.warning(f"Nome de modelo inválido: {e}")
            return False

        from .instances import InstancesClient
        instances = InstancesClient(self._client)

        instance = await instances.get(instance_id)
        if not instance.is_running:
            return False

        host = instance.public_ipaddr or instance.ssh_host
        port = instance.ssh_port

        if not host or not port:
            return False

        try:
            await self._run_ssh_command(
                host, port,
                f"ollama rm {shlex.quote(model)}",
                timeout=60
            )
            return True
        except Exception as e:
            logger.warning(f"Erro ao remover modelo: {e}")
            return False

    async def fetch_available(self) -> List[Dict[str, Any]]:
        """
        Lista modelos disponíveis para instalação.

        Returns:
            Lista de modelos disponíveis no servidor
        """
        response = await self._client.get("/api/v1/models/available")
        return response

    async def run(
        self,
        instance_id: int,
        model: str,
        prompt: str,
    ) -> str:
        """
        Executa um prompt em um modelo.

        Args:
            instance_id: ID da instância
            model: Nome do modelo
            prompt: Prompt para executar

        Returns:
            Resposta do modelo

        Raises:
            ValueError: Se o nome do modelo for inválido
            Exception: Se a instância não estiver rodando ou SSH não disponível
        """
        # Validar nome do modelo para prevenir command injection
        model = _validate_model_name(model)

        from .instances import InstancesClient
        instances = InstancesClient(self._client)

        instance = await instances.get(instance_id)
        if not instance.is_running:
            raise Exception("Instância não está rodando")

        host = instance.public_ipaddr or instance.ssh_host
        port = instance.ssh_port

        if not host or not port:
            raise Exception("Informações de SSH não disponíveis")

        # Usa shlex.quote para escaping seguro do prompt
        escaped_prompt = shlex.quote(prompt)
        escaped_model = shlex.quote(model)

        result = await self._run_ssh_command(
            host, port,
            f"ollama run {escaped_model} {escaped_prompt}",
            timeout=120
        )

        return result

    async def _run_ssh_command(
        self,
        host: str,
        port: int,
        command: str,
        timeout: int = 60,
    ) -> str:
        """
        Executa comando via SSH.

        Args:
            host: Host SSH
            port: Porta SSH
            command: Comando para executar
            timeout: Timeout em segundos

        Returns:
            Output do comando
        """
        proc = await asyncio.create_subprocess_exec(
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=30',
            '-o', 'BatchMode=yes',
            '-p', str(port),
            f'root@{host}',
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            return stdout.decode() + stderr.decode()
        except asyncio.TimeoutError:
            proc.kill()
            raise
