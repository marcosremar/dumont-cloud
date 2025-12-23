"""
Testes do módulo de instâncias do SDK.

Testa list, create, pause, resume, destroy, sync, wake.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# =============================================================================
# Testes Unitários (Mock)
# =============================================================================

class TestInstancesUnit:
    """Testes unitários de instâncias."""

    @pytest.mark.asyncio
    async def test_list_instances(self, mock_instance_data):
        """Testa listagem de instâncias."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"instances": [mock_instance_data]}

            instances = await client.instances.list()

            assert len(instances) == 1
            assert instances[0].id == 12345
            assert instances[0].gpu_name == "RTX 4090"
            assert instances[0].is_running is True

        await client.close()

    @pytest.mark.asyncio
    async def test_get_instance(self, mock_instance_data):
        """Testa obter instância específica."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_instance_data

            instance = await client.instances.get(12345)

            assert instance.id == 12345
            assert instance.gpu_name == "RTX 4090"
            mock_get.assert_called_once_with("/api/v1/instances/12345")

        await client.close()

    @pytest.mark.asyncio
    async def test_search_offers(self, mock_offer_data):
        """Testa busca de ofertas."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"offers": [mock_offer_data]}

            offers = await client.instances.search_offers(
                gpu_name="RTX 4090",
                max_price=1.0,
            )

            assert len(offers) == 1
            assert offers[0].gpu_name == "RTX 4090"
            assert offers[0].dph_total == 0.45

        await client.close()

    @pytest.mark.asyncio
    async def test_create_instance(self, mock_instance_data):
        """Testa criação de instância."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_instance_data

            instance = await client.instances.create(
                offer_id=99999,
                disk_size=100,
                label="test-instance",
            )

            assert instance.id == 12345
            assert instance.gpu_name == "RTX 4090"

        await client.close()

    @pytest.mark.asyncio
    async def test_pause_instance(self):
        """Testa pausar instância."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"success": True}

            result = await client.instances.pause(12345)

            assert result["success"] is True
            mock_post.assert_called_once()

        await client.close()

    @pytest.mark.asyncio
    async def test_resume_instance(self):
        """Testa resumir instância."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"success": True}

            result = await client.instances.resume(12345)

            assert result["success"] is True

        await client.close()

    @pytest.mark.asyncio
    async def test_destroy_instance(self):
        """Testa destruir instância."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        with patch.object(client, 'delete', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"success": True}

            result = await client.instances.destroy(12345)

            assert result["success"] is True

        await client.close()

    @pytest.mark.asyncio
    async def test_wake_instance(self, mock_instance_data):
        """Testa acordar instância hibernada."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="test_key",
            base_url="https://api.test.com",
        )

        with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "success": True,
                "instance": mock_instance_data,
            }

            result = await client.instances.wake(12345)

            assert result["success"] is True
            assert "instance" in result

        await client.close()

    @pytest.mark.asyncio
    async def test_instance_ssh_command(self, mock_instance_data):
        """Testa propriedade ssh_command."""
        from dumont_sdk.instances import Instance

        instance = Instance(
            id=12345,
            status="running",
            actual_status="running",
            gpu_name="RTX 4090",
            num_gpus=1,
            gpu_ram=24,
            cpu_cores=16,
            cpu_ram=64,
            disk_space=100,
            public_ipaddr="192.168.1.100",
            ssh_port=22,
            dph_total=0.50,
        )

        assert "ssh" in instance.ssh_command
        assert "192.168.1.100" in instance.ssh_command

    @pytest.mark.asyncio
    async def test_instance_is_running(self):
        """Testa propriedade is_running."""
        from dumont_sdk.instances import Instance

        running_instance = Instance(
            id=1, status="running", actual_status="running",
            gpu_name="RTX 4090", num_gpus=1, gpu_ram=24,
            cpu_cores=16, cpu_ram=64, disk_space=100,
            dph_total=0.5,
        )

        stopped_instance = Instance(
            id=2, status="stopped", actual_status="exited",
            gpu_name="RTX 4090", num_gpus=1, gpu_ram=24,
            cpu_cores=16, cpu_ram=64, disk_space=100,
            dph_total=0.5,
        )

        assert running_instance.is_running is True
        assert stopped_instance.is_running is False


# =============================================================================
# Testes de Integração
# =============================================================================

@pytest.mark.integration
class TestInstancesIntegration:
    """Testes de integração de instâncias."""

    @pytest.mark.asyncio
    async def test_list_instances_real(self, client_with_api_key, rate_limiter):
        """Testa listagem real de instâncias."""
        await rate_limiter.wait()

        instances = await client_with_api_key.instances.list()

        assert isinstance(instances, list)
        # Pode estar vazia, mas deve ser uma lista

    @pytest.mark.asyncio
    async def test_search_offers_real(self, client_with_api_key, rate_limiter):
        """Testa busca real de ofertas."""
        await rate_limiter.wait()

        offers = await client_with_api_key.instances.search_offers(
            gpu_name="RTX",  # Busca genérica
            max_price=5.0,   # Preço alto para encontrar ofertas
            limit=5,
        )

        assert isinstance(offers, list)
        # Pode estar vazia dependendo da disponibilidade

    @pytest.mark.asyncio
    @pytest.mark.requires_instance
    @pytest.mark.slow
    async def test_get_instance_real(self, client_with_api_key, reserved_gpu_instance, rate_limiter):
        """
        Testa obter instância real.

        Este teste reserva uma GPU, executa o teste e depois destrói a GPU.
        """
        await rate_limiter.wait()

        try:
            instance = await client_with_api_key.instances.get(reserved_gpu_instance.id)

            assert instance.id == reserved_gpu_instance.id
            assert instance.gpu_name == reserved_gpu_instance.gpu_name
        except Exception as e:
            err_str = str(e).lower()
            # Instância pode ter sido destruída durante execução dos testes
            if any(x in err_str for x in ["não encontrad", "not found", "404", "recurso"]):
                pytest.skip(f"Instância foi destruída durante teste: {reserved_gpu_instance.id}")
            raise

    @pytest.mark.asyncio
    @pytest.mark.requires_instance
    @pytest.mark.slow
    async def test_sync_instance_real(self, client_with_api_key, reserved_gpu_instance, rate_limiter):
        """
        Testa sync de instância real.

        Este teste reserva uma GPU, executa o teste e depois destrói a GPU.
        """
        await rate_limiter.wait()

        # Sync leve, apenas verifica se endpoint funciona
        result = await client_with_api_key.instances.sync(
            instance_id=reserved_gpu_instance.id,
            source_path="/workspace",
        )

        assert isinstance(result, dict)


# =============================================================================
# Testes de Modelo de Dados
# =============================================================================

class TestInstanceModel:
    """Testes do modelo Instance."""

    def test_instance_from_dict(self, mock_instance_data):
        """Testa criação de Instance a partir de dict."""
        from dumont_sdk.instances import Instance

        instance = Instance(
            id=mock_instance_data["id"],
            status=mock_instance_data["status"],
            actual_status=mock_instance_data["actual_status"],
            gpu_name=mock_instance_data["gpu_name"],
            num_gpus=mock_instance_data["num_gpus"],
            gpu_ram=mock_instance_data["gpu_ram"],
            cpu_cores=mock_instance_data["cpu_cores"],
            cpu_ram=mock_instance_data["ram_gb"],  # API uses ram_gb, SDK uses cpu_ram
            disk_space=mock_instance_data["disk_gb"],  # API uses disk_gb, SDK uses disk_space
            public_ipaddr=mock_instance_data.get("public_ipaddr"),
            ssh_port=mock_instance_data.get("ssh_port"),
            dph_total=mock_instance_data["dph_total"],
            label=mock_instance_data.get("label"),
        )

        assert instance.id == 12345
        assert instance.gpu_name == "RTX 4090"
        assert instance.is_running is True
        assert instance.label == "test-instance"

    def test_gpu_offer_from_dict(self, mock_offer_data):
        """Testa criação de GPUOffer a partir de dict."""
        from dumont_sdk.instances import GPUOffer

        offer = GPUOffer(
            id=mock_offer_data["id"],
            gpu_name=mock_offer_data["gpu_name"],
            num_gpus=mock_offer_data["num_gpus"],
            gpu_ram=mock_offer_data["gpu_ram"],
            cpu_cores=mock_offer_data["cpu_cores"],
            cpu_ram=mock_offer_data["ram_gb"],  # API uses ram_gb, SDK uses cpu_ram
            disk_space=mock_offer_data["disk_gb"],  # API uses disk_gb, SDK uses disk_space
            inet_down=100.0,
            inet_up=100.0,
            dph_total=mock_offer_data["dph_total"],
            geolocation=mock_offer_data.get("geolocation"),
            reliability=mock_offer_data.get("reliability", 0.0),
        )

        assert offer.id == 99999
        assert offer.gpu_name == "RTX 4090"
        assert offer.dph_total == 0.45
        assert offer.geolocation == "US"
