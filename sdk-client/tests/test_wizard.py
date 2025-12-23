"""
Testes do módulo wizard deploy do SDK.

Testa deploy multi-start com batches.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from .conftest import make_test_instance, make_test_offer


# =============================================================================
# Testes Unitários (Mock)
# =============================================================================

class TestWizardUnit:
    """Testes unitários do wizard deploy."""

    def test_deploy_config_defaults(self):
        """Testa configuração padrão do deploy."""
        from dumont_sdk.wizard import DeployConfig, DeploySpeed

        config = DeployConfig()

        assert config.max_price == 2.0
        assert config.speed == DeploySpeed.FAST
        assert config.batch_size == 5
        assert config.max_batches == 3
        assert config.batch_timeout == 90

    def test_deploy_result_success(self):
        """Testa DeployResult de sucesso."""
        from dumont_sdk.wizard import DeployResult

        result = DeployResult(
            success=True,
            instance_id=12345,
            gpu_name="RTX 4090",
            public_ip="192.168.1.100",
            ssh_port=22,
            ssh_command="ssh -p 22 root@192.168.1.100",
            dph_total=0.50,
            ready_time=45.2,
            machines_tried=5,
            machines_destroyed=4,
        )

        assert result.is_success is True
        assert result.instance_id == 12345
        assert result.machines_destroyed == 4

    def test_deploy_result_failure(self):
        """Testa DeployResult de falha."""
        from dumont_sdk.wizard import DeployResult

        result = DeployResult(
            success=False,
            error="Nenhuma oferta encontrada",
        )

        assert result.is_success is False
        assert result.error == "Nenhuma oferta encontrada"

    @pytest.mark.asyncio
    async def test_wizard_on_progress_callback(self):
        """Testa callback de progresso."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        progress_events = []

        def on_progress(status, data):
            progress_events.append((status, data))

        client.wizard.on_progress(on_progress)
        client.wizard._emit_progress("searching", {"message": "Buscando..."})

        assert len(progress_events) == 1
        assert progress_events[0][0] == "searching"

        await client.close()

    @pytest.mark.asyncio
    async def test_deploy_no_offers(self):
        """Testa deploy quando não há ofertas."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"offers": []}

            result = await client.wizard.deploy(
                gpu_name="RTX 4090",
                max_price=1.0,
            )

            assert result.success is False
            assert "Nenhuma oferta" in result.error

        await client.close()

    @pytest.mark.asyncio
    async def test_quick_deploy_defaults(self):
        """Testa quick_deploy usa valores default."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        with patch.object(client.wizard, 'deploy', new_callable=AsyncMock) as mock_deploy:
            from dumont_sdk.wizard import DeployResult
            mock_deploy.return_value = DeployResult(success=True, instance_id=123)

            await client.wizard.quick_deploy(max_price=0.8)

            mock_deploy.assert_called_once()
            call_kwargs = mock_deploy.call_args[1]
            assert call_kwargs["max_price"] == 0.8
            assert call_kwargs["speed"] == "fast"
            assert call_kwargs["batch_size"] == 5

        await client.close()

    @pytest.mark.asyncio
    async def test_check_ssh_success(self):
        """Testa verificação de SSH bem-sucedida."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        async def mock_open_connection(host, port):
            mock_writer = MagicMock()
            mock_writer.close = MagicMock()
            mock_writer.wait_closed = AsyncMock()
            return (MagicMock(), mock_writer)

        with patch('asyncio.open_connection', side_effect=mock_open_connection):
            result = await client.wizard._check_ssh("192.168.1.1", 22)
            assert result is True

        await client.close()

    @pytest.mark.asyncio
    async def test_check_ssh_failure(self):
        """Testa verificação de SSH que falha."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        async def mock_open_connection(host, port):
            raise ConnectionRefusedError("Connection refused")

        with patch('asyncio.open_connection', side_effect=mock_open_connection):
            result = await client.wizard._check_ssh("192.168.1.1", 22)
            assert result is False

        await client.close()


# =============================================================================
# Testes de Enums e Tipos
# =============================================================================

class TestWizardTypes:
    """Testes dos tipos do wizard."""

    def test_deploy_speed_enum(self):
        """Testa enum DeploySpeed."""
        from dumont_sdk.wizard import DeploySpeed

        assert DeploySpeed.FAST.value == "fast"
        assert DeploySpeed.BALANCED.value == "balanced"
        assert DeploySpeed.CHEAP.value == "cheap"

    def test_deploy_status_enum(self):
        """Testa enum DeployStatus."""
        from dumont_sdk.wizard import DeployStatus

        assert DeployStatus.PENDING.value == "pending"
        assert DeployStatus.SEARCHING.value == "searching"
        assert DeployStatus.CREATING.value == "creating"
        assert DeployStatus.COMPLETED.value == "completed"
        assert DeployStatus.FAILED.value == "failed"


# =============================================================================
# Testes de Fluxo Completo (Mock)
# =============================================================================

class TestWizardFlow:
    """Testes de fluxo completo do wizard."""

    @pytest.mark.asyncio
    async def test_deploy_flow_success(self):
        """Testa fluxo completo de deploy com sucesso."""
        from dumont_sdk import DumontClient
        from dumont_sdk.instances import InstancesClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        offer = make_test_offer()
        instance = make_test_instance()

        progress_events = []
        client.wizard.on_progress(lambda s, d: progress_events.append(s))

        with patch.object(InstancesClient, 'search_offers', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [offer]

            with patch.object(InstancesClient, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = instance

                with patch.object(InstancesClient, 'get', new_callable=AsyncMock) as mock_get:
                    mock_get.return_value = instance

                    with patch.object(
                        client.wizard, '_check_ssh', new_callable=AsyncMock
                    ) as mock_ssh:
                        mock_ssh.return_value = True

                        result = await client.wizard.deploy(
                            gpu_name="RTX 4090",
                            max_price=1.0,
                            batch_size=1,
                            max_batches=1,
                            timeout_per_batch=5,
                        )

                        assert result.success is True
                        assert result.instance_id == 12345
                        assert "searching" in progress_events

        await client.close()

    @pytest.mark.asyncio
    async def test_deploy_flow_timeout(self):
        """Testa fluxo de deploy com timeout."""
        from dumont_sdk import DumontClient
        from dumont_sdk.instances import InstancesClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        offer = make_test_offer()

        # Instância que nunca fica pronta
        instance = make_test_instance(
            status="creating",
            actual_status="starting",
        )

        with patch.object(InstancesClient, 'search_offers', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [offer]

            with patch.object(InstancesClient, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = instance

                with patch.object(InstancesClient, 'get', new_callable=AsyncMock) as mock_get:
                    mock_get.return_value = instance

                    with patch.object(InstancesClient, 'destroy', new_callable=AsyncMock) as mock_destroy:
                        mock_destroy.return_value = {"success": True}

                        result = await client.wizard.deploy(
                            gpu_name="RTX 4090",
                            batch_size=1,
                            max_batches=1,
                            timeout_per_batch=1,
                        )

                        assert result.success is False
                        assert "Nenhuma máquina ficou pronta" in result.error

        await client.close()


# =============================================================================
# Testes de Integração
# =============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestWizardIntegration:
    """Testes de integração do wizard (muito lentos)."""

    @pytest.mark.asyncio
    async def test_deploy_real_dry_run(self, client_with_api_key, rate_limiter):
        """
        Testa busca de ofertas sem criar instâncias.

        Este teste só verifica se consegue buscar ofertas.
        """
        await rate_limiter.wait()

        # Apenas buscar ofertas, sem criar
        offers = await client_with_api_key.instances.search_offers(
            max_price=0.5,
            limit=5,
        )

        assert isinstance(offers, list)
        # Pode estar vazia se não houver ofertas baratas
