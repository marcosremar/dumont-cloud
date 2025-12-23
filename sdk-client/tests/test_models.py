"""
Testes do módulo de modelos do SDK.

Testa instalação e gerenciamento de modelos Ollama via SSH.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from .conftest import make_test_instance


# =============================================================================
# Testes Unitários (Mock)
# =============================================================================

class TestModelsUnit:
    """Testes unitários do módulo de modelos."""

    def test_installed_model_dataclass(self):
        """Testa dataclass InstalledModel."""
        from dumont_sdk.models import InstalledModel

        model = InstalledModel(
            name="llama3.2:latest",
            size="4.7GB",
            modified_at="2024-12-17",
            digest="abc123",
        )

        assert model.name == "llama3.2:latest"
        assert model.size == "4.7GB"

    def test_model_install_result_success(self):
        """Testa ModelInstallResult de sucesso."""
        from dumont_sdk.models import ModelInstallResult

        result = ModelInstallResult(
            success=True,
            model_name="llama3.2",
            instance_id=12345,
            ollama_url="http://192.168.1.100:11434",
            ssh_command="ssh -p 22 root@192.168.1.100",
        )

        assert result.success is True
        assert result.ollama_url is not None
        assert "11434" in result.ollama_url

    def test_model_install_result_failure(self):
        """Testa ModelInstallResult de falha."""
        from dumont_sdk.models import ModelInstallResult

        result = ModelInstallResult(
            success=False,
            model_name="llama3.2",
            instance_id=12345,
            error="Instância não encontrada",
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_install_instance_not_running(self):
        """Testa install quando instância não está rodando."""
        from dumont_sdk import DumontClient
        from dumont_sdk.instances import InstancesClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        stopped_instance = make_test_instance(
            status="stopped",
            actual_status="exited",
        )

        # Mock InstancesClient.get diretamente no módulo
        with patch.object(InstancesClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = stopped_instance

            result = await client.models.install(12345, "llama3.2")

            assert result.success is False
            assert "não está rodando" in result.error

        await client.close()

    @pytest.mark.asyncio
    async def test_install_no_ssh_info(self):
        """Testa install quando não há info de SSH."""
        from dumont_sdk import DumontClient
        from dumont_sdk.instances import InstancesClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        instance = make_test_instance(
            public_ipaddr=None,
            ssh_port=None,
        )

        with patch.object(InstancesClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = instance

            result = await client.models.install(12345, "llama3.2")

            assert result.success is False
            assert "SSH" in result.error

        await client.close()

    @pytest.mark.asyncio
    async def test_install_success(self):
        """Testa instalação bem-sucedida."""
        from dumont_sdk import DumontClient
        from dumont_sdk.instances import InstancesClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        instance = make_test_instance()

        with patch.object(InstancesClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = instance

            with patch.object(
                client.models, '_run_ssh_command', new_callable=AsyncMock
            ) as mock_ssh:
                mock_ssh.side_effect = [
                    "OLLAMA_INSTALL_COMPLETE=yes\nOLLAMA_RUNNING=yes",
                    "MODEL_PULL_SUCCESS=yes\nMODEL_NAME=llama3.2",
                ]

                result = await client.models.install(12345, "llama3.2")

                assert result.success is True
                assert result.ollama_url == "http://192.168.1.100:11434"
                assert result.model_name == "llama3.2"

        await client.close()

    @pytest.mark.asyncio
    async def test_install_ollama_fails(self):
        """Testa quando instalação do Ollama falha."""
        from dumont_sdk import DumontClient
        from dumont_sdk.instances import InstancesClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        instance = make_test_instance()

        with patch.object(InstancesClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = instance

            with patch.object(
                client.models, '_run_ssh_command', new_callable=AsyncMock
            ) as mock_ssh:
                mock_ssh.return_value = "Error: failed to install"

                result = await client.models.install(12345, "llama3.2")

                assert result.success is False
                assert "Ollama" in result.error

        await client.close()

    @pytest.mark.asyncio
    async def test_list_models(self):
        """Testa listagem de modelos instalados."""
        from dumont_sdk import DumontClient
        from dumont_sdk.instances import InstancesClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        instance = make_test_instance()

        with patch.object(InstancesClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = instance

            with patch.object(
                client.models, '_run_ssh_command', new_callable=AsyncMock
            ) as mock_ssh:
                mock_ssh.return_value = "llama3.2:latest\t4.7GB\t2024-12-17\nqwen3:0.6b\t600MB\t2024-12-16"

                models = await client.models.list(12345)

                assert len(models) == 2
                assert models[0].name == "llama3.2:latest"
                assert models[1].name == "qwen3:0.6b"

        await client.close()

    @pytest.mark.asyncio
    async def test_remove_model(self):
        """Testa remoção de modelo."""
        from dumont_sdk import DumontClient
        from dumont_sdk.instances import InstancesClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        instance = make_test_instance()

        with patch.object(InstancesClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = instance

            with patch.object(
                client.models, '_run_ssh_command', new_callable=AsyncMock
            ) as mock_ssh:
                mock_ssh.return_value = "deleted 'llama3.2'"

                result = await client.models.remove(12345, "llama3.2")

                assert result is True
                mock_ssh.assert_called_once()

        await client.close()

    @pytest.mark.asyncio
    async def test_run_prompt(self):
        """Testa execução de prompt."""
        from dumont_sdk import DumontClient
        from dumont_sdk.instances import InstancesClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        instance = make_test_instance()

        with patch.object(InstancesClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = instance

            with patch.object(
                client.models, '_run_ssh_command', new_callable=AsyncMock
            ) as mock_ssh:
                mock_ssh.return_value = "Hello! I am an AI assistant."

                response = await client.models.run(12345, "llama3.2", "Hello!")

                assert response == "Hello! I am an AI assistant."

        await client.close()


# =============================================================================
# Testes de SSH
# =============================================================================

class TestSSHCommands:
    """Testes de comandos SSH."""

    @pytest.mark.asyncio
    async def test_run_ssh_command_timeout(self):
        """Testa timeout de comando SSH."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        # Mock subprocess que nunca termina
        async def mock_create_subprocess(*args, **kwargs):
            mock_proc = MagicMock()

            async def slow_communicate():
                await asyncio.sleep(10)  # Nunca retorna a tempo
                return (b"", b"")

            mock_proc.communicate = slow_communicate
            mock_proc.kill = MagicMock()
            return mock_proc

        with patch(
            'asyncio.create_subprocess_exec',
            side_effect=mock_create_subprocess
        ):
            with pytest.raises(asyncio.TimeoutError):
                await client.models._run_ssh_command(
                    host="192.168.1.100",
                    port=22,
                    command="echo test",
                    timeout=1,
                )

        await client.close()

    @pytest.mark.asyncio
    async def test_run_ssh_command_success(self):
        """Testa comando SSH bem-sucedido."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        async def mock_create_subprocess(*args, **kwargs):
            mock_proc = MagicMock()

            async def quick_communicate():
                return (b"stdout output", b"stderr output")

            mock_proc.communicate = quick_communicate
            return mock_proc

        with patch(
            'asyncio.create_subprocess_exec',
            side_effect=mock_create_subprocess
        ):
            result = await client.models._run_ssh_command(
                host="192.168.1.100",
                port=22,
                command="echo test",
                timeout=60,
            )

            assert "stdout output" in result

        await client.close()


# =============================================================================
# Testes de Integração
# =============================================================================

@pytest.mark.integration
@pytest.mark.requires_instance
@pytest.mark.slow
class TestModelsIntegration:
    """Testes de integração do módulo de modelos."""

    @pytest.mark.asyncio
    async def test_list_models_real(
        self, client_with_api_key, reserved_gpu_instance, rate_limiter
    ):
        """
        Testa listagem real de modelos.

        Reserva GPU → lista modelos → destrói GPU.
        """
        await rate_limiter.wait()

        models = await client_with_api_key.models.list(reserved_gpu_instance.id)

        assert isinstance(models, list)
        # Pode estar vazia se Ollama não estiver instalado

    @pytest.mark.asyncio
    async def test_fetch_available_real(
        self, client_with_api_key, rate_limiter
    ):
        """Testa busca de modelos disponíveis no servidor."""
        await rate_limiter.wait()

        # O servidor tem endpoint /models/available com modelos pré-definidos
        available = await client_with_api_key.models.fetch_available()
        assert isinstance(available, list)
        assert len(available) > 0
        # Verificar estrutura do modelo (retorna dict, não dataclass)
        for model in available:
            assert 'name' in model
            assert 'size' in model
            assert 'provider' in model

    @pytest.mark.asyncio
    async def test_install_model_real(
        self, client_with_api_key, reserved_gpu_instance, rate_limiter
    ):
        """
        Testa instalação de modelo em instância real.

        Reserva GPU → instala modelo → destrói GPU.

        Se a instância tem SSH disponível, tenta instalar um modelo pequeno.
        Se não tem SSH, verifica que o SDK retorna erro apropriado.
        """
        await rate_limiter.wait()

        # Verificar se instância tem SSH configurado
        has_ssh = reserved_gpu_instance.ssh_port is not None and reserved_gpu_instance.public_ip

        # Tentar instalar modelo pequeno (nomic-embed-text = 274MB)
        result = await client_with_api_key.models.install(
            instance_id=reserved_gpu_instance.id,
            model="nomic-embed-text",
            timeout=300,  # 5 minutos para modelo pequeno
        )

        if has_ssh:
            # Com SSH, deve ter sucesso ou erro específico de conexão
            if not result.success:
                # Erros aceitáveis: timeout, conexão recusada
                assert any(x in result.error.lower() for x in [
                    "timeout", "connection", "refused", "ssh"
                ]), "Erro inesperado: {}".format(result.error)
        else:
            # Sem SSH, deve retornar erro informando que não tem SSH
            assert result.success is False
            assert "ssh" in result.error.lower() or "não disponíveis" in result.error.lower()
