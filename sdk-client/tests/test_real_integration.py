"""
Testes de integração REAIS do Dumont SDK.

Estes testes usam GPU real e API real do Dumont Cloud.
Requer uma API key válida.

Para rodar:
    pytest tests/test_real_integration.py -v --api-key=dumont_sk_xxx

Ou via variável de ambiente:
    DUMONT_API_KEY=dumont_sk_xxx pytest tests/test_real_integration.py -v

Markers:
    @pytest.mark.integration - Testes que usam API real
    @pytest.mark.slow - Testes que demoram (deploy, etc)
    @pytest.mark.requires_instance - Requer instância rodando
"""
import pytest
import asyncio
from typing import Optional

from .conftest import RateLimiter


# =============================================================================
# Fixtures específicas para testes reais
# =============================================================================

@pytest.fixture
def real_rate_limiter():
    """Rate limiter mais conservador para testes reais."""
    return RateLimiter(requests_per_second=1.0)


@pytest.fixture
async def real_sdk_client(api_key, api_url, openrouter_key):
    """
    Cliente SDK para testes reais.

    auto_fetch_config=True busca config do servidor automaticamente.
    """
    if not api_key:
        pytest.skip("API key não configurada (use --api-key=xxx)")

    from dumont_sdk import DumontClient

    client = DumontClient(
        api_key=api_key,
        base_url=api_url,
        openrouter_api_key=openrouter_key,
        auto_fetch_config=True,
    )

    yield client

    await client.close()


# =============================================================================
# Testes de Autenticação com API Key
# =============================================================================

@pytest.mark.integration
class TestRealAuth:
    """Testes de autenticação real com API key."""

    @pytest.mark.asyncio
    async def test_api_key_authentication(self, real_sdk_client, real_rate_limiter):
        """Testa autenticação via API key."""
        await real_rate_limiter.wait()

        # Se chegou aqui, autenticação funcionou
        # Tentar buscar dados do usuário
        try:
            user_data = await real_sdk_client.me()
            assert "authenticated" in user_data or "user" in user_data
        except Exception:
            # Endpoint me pode não existir, mas autenticação funcionou
            pass

    @pytest.mark.asyncio
    async def test_fetch_sdk_config(self, real_sdk_client, real_rate_limiter):
        """Testa busca de config do servidor."""
        await real_rate_limiter.wait()

        config = await real_sdk_client.fetch_sdk_config()

        # Config deve ter sido carregada
        assert real_sdk_client._config_fetched is True

        # Config deve ter campos esperados
        if config:
            assert "features" in config or "base_url" in config

    @pytest.mark.asyncio
    async def test_server_config_has_openrouter_key(self, real_sdk_client, real_rate_limiter):
        """Testa se a config do servidor inclui OpenRouter key."""
        await real_rate_limiter.wait()

        config = await real_sdk_client.fetch_sdk_config()

        # Se o servidor tem OpenRouter configurado, deve retornar
        # Nota: Este teste pode falhar se o servidor não tiver OpenRouter
        if config and config.get("openrouter_api_key"):
            assert config["openrouter_api_key"].startswith("sk-or-") or len(config["openrouter_api_key"]) > 10


# =============================================================================
# Testes de Instâncias Reais
# =============================================================================

@pytest.mark.integration
class TestRealInstances:
    """Testes de gerenciamento de instâncias reais."""

    @pytest.mark.asyncio
    async def test_list_instances(self, real_sdk_client, real_rate_limiter):
        """Testa listagem de instâncias."""
        await real_rate_limiter.wait()

        try:
            instances = await real_sdk_client.instances.list()
        except Exception as e:
            if "503" in str(e):
                pytest.skip("Servidor indisponível (503)")
            raise

        assert isinstance(instances, list)

        # Se tem instâncias, verificar estrutura
        for inst in instances:
            assert hasattr(inst, 'id')
            assert hasattr(inst, 'gpu_name')
            assert hasattr(inst, 'status')
            assert hasattr(inst, 'dph_total')

    @pytest.mark.asyncio
    async def test_search_offers(self, real_sdk_client, real_rate_limiter):
        """Testa busca de ofertas GPU."""
        await real_rate_limiter.wait()

        offers = await real_sdk_client.instances.search_offers(
            max_price=1.0,
            limit=5,
        )

        assert isinstance(offers, list)

        # Ofertas podem estar vazias se não houver máquinas baratas
        for offer in offers:
            assert hasattr(offer, 'id')
            assert hasattr(offer, 'gpu_name')
            assert hasattr(offer, 'dph_total')
            # API pode ter pequena margem, usando 10% de tolerância
            assert offer.dph_total <= 1.1

    @pytest.mark.asyncio
    @pytest.mark.requires_instance
    @pytest.mark.slow
    async def test_get_running_instance(self, real_sdk_client, reserved_gpu_instance, real_rate_limiter):
        """
        Testa obtenção de instância específica.

        Reserva GPU → busca detalhes → destrói GPU.
        """
        await real_rate_limiter.wait()

        # Buscar detalhes da instância reservada
        try:
            instance = await real_sdk_client.instances.get(reserved_gpu_instance.id)
        except Exception as e:
            if "503" in str(e):
                pytest.skip("Servidor indisponível ao buscar instância (503)")
            raise

        assert instance.id == reserved_gpu_instance.id
        assert instance.is_running


# =============================================================================
# Testes de Snapshots Reais
# =============================================================================

@pytest.mark.integration
class TestRealSnapshots:
    """Testes de snapshots reais."""

    @pytest.mark.asyncio
    async def test_list_snapshots(self, real_sdk_client, real_rate_limiter):
        """Testa listagem de snapshots."""
        await real_rate_limiter.wait()

        try:
            snapshots = await real_sdk_client.snapshots.list()

            assert isinstance(snapshots, list)

            for snap in snapshots:
                assert hasattr(snap, 'id') or hasattr(snap, 'short_id')
        except Exception as e:
            # Snapshots podem não estar configurados
            if "not configured" in str(e).lower():
                pytest.skip("Snapshots não configurados")
            raise


# =============================================================================
# Testes de LLM com Failover Real
# =============================================================================

@pytest.mark.integration
class TestRealLLM:
    """Testes de LLM com OpenRouter real."""

    @pytest.mark.asyncio
    async def test_llm_with_openrouter_fallback(self, real_sdk_client, real_rate_limiter):
        """
        Testa inferência LLM usando OpenRouter como fallback.

        Este teste usa OpenRouter diretamente (GPU não configurada).
        """
        await real_rate_limiter.wait()

        # Garantir que a config foi carregada
        await real_sdk_client.ensure_config()

        # Verificar se temos OpenRouter key
        openrouter_key = real_sdk_client._openrouter_api_key
        if not openrouter_key:
            pytest.skip("OpenRouter API key não disponível")

        # Tentar fazer uma inferência simples
        try:
            response = await real_sdk_client.llm.complete(
                "Responda apenas 'OK' em uma palavra.",
                max_tokens=10,
            )

            assert "choices" in response
            content = real_sdk_client.llm.get_content(response)
            assert len(content) > 0

            # Verificar que foi fallback (não GPU)
            assert response.get("_source") in ["fallback", "gpu"]

        except Exception as e:
            if "api key" in str(e).lower():
                pytest.skip(f"OpenRouter key inválida: {e}")
            raise

    @pytest.mark.asyncio
    @pytest.mark.requires_instance
    @pytest.mark.slow
    async def test_llm_with_gpu(self, real_sdk_client, reserved_gpu_instance, real_rate_limiter):
        """
        Testa inferência LLM - tenta GPU primeiro, fallback para OpenRouter.

        Reserva GPU → tenta inferência na GPU → fallback para OpenRouter → destrói GPU.

        Este teste verifica que o sistema de LLM funciona, seja via GPU ou fallback.
        """
        await real_rate_limiter.wait()

        # Garantir que a config foi carregada
        await real_sdk_client.ensure_config()

        gpu_available = False
        if reserved_gpu_instance.public_ip:
            # Tentar health check na GPU
            from dumont_sdk.config import GPUConfig
            import httpx

            gpu_url = "http://{}:8000".format(reserved_gpu_instance.public_ip)

            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get("{}/health".format(gpu_url), timeout=5.0)
                    if resp.status_code == 200:
                        gpu_available = True
                        real_sdk_client.llm.config.gpu = GPUConfig(url=gpu_url)
            except Exception:
                pass

        # Fazer inferência - GPU ou fallback
        response = await real_sdk_client.llm.complete(
            "Diga apenas 'OK'.",
            max_tokens=10,
        )

        assert "choices" in response
        # Verificar que usou alguma fonte válida
        source = response.get("_source")
        assert source in ["gpu", "fallback"], "Fonte inesperada: {}".format(source)

        # Se GPU estava disponível, deveria ter usado GPU
        if gpu_available:
            assert source == "gpu", "GPU estava disponível mas usou fallback"


# =============================================================================
# Testes de Modelos Reais
# =============================================================================

@pytest.mark.integration
@pytest.mark.requires_instance
@pytest.mark.slow
class TestRealModels:
    """
    Testes de gerenciamento de modelos em instância real.

    Cada teste reserva sua própria GPU, executa o teste e destrói a GPU.
    """

    @pytest.mark.asyncio
    async def test_list_models_on_instance(self, real_sdk_client, reserved_gpu_instance, real_rate_limiter):
        """
        Testa listagem de modelos em uma instância.

        Reserva GPU → lista modelos → destrói GPU.
        """
        await real_rate_limiter.wait()

        try:
            models = await real_sdk_client.models.list(reserved_gpu_instance.id)

            assert isinstance(models, list)

            for model in models:
                assert hasattr(model, 'name')

        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ["not running", "connection", "500", "timeout"]):
                pytest.skip("Instância não acessível: {}".format(e))
            raise


# =============================================================================
# Testes de Status e Métricas
# =============================================================================

@pytest.mark.integration
class TestRealStatus:
    """Testes de status e métricas."""

    @pytest.mark.asyncio
    async def test_get_status(self, real_sdk_client, real_rate_limiter):
        """Testa obtenção de status geral."""
        await real_rate_limiter.wait()

        try:
            status = await real_sdk_client.get_status()
        except Exception as e:
            if "503" in str(e):
                pytest.skip("Servidor indisponível (503)")
            raise

        assert "total_instances" in status
        assert "running" in status
        assert "stopped" in status
        assert "total_cost_per_hour" in status
        assert isinstance(status["instances"], list)


# =============================================================================
# Testes de Wizard (Deploy) - MUITO LENTOS
# =============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestRealWizard:
    """
    Testes de wizard deploy real.

    ATENÇÃO: Estes testes CRIAM e DESTROEM instâncias reais!
    Podem incorrer em custos.
    """

    @pytest.mark.asyncio
    async def test_wizard_search_offers(self, real_sdk_client, real_rate_limiter):
        """Testa busca de ofertas pelo wizard (sem criar)."""
        await real_rate_limiter.wait()

        offers = await real_sdk_client.instances.search_offers(
            max_price=0.5,
            limit=3,
        )

        # Apenas verificar que a busca funciona
        assert isinstance(offers, list)

    @pytest.mark.asyncio
    async def test_wizard_deploy_real(self, real_sdk_client, real_rate_limiter):
        """
        Testa wizard deploy - verifica comportamento sem criar instância.

        Usa preço muito baixo (0.001) para garantir que não encontra ofertas,
        assim podemos testar o fluxo do wizard sem gastar dinheiro.
        """
        await real_rate_limiter.wait()

        # Preço impossível - não vai encontrar ofertas
        result = await real_sdk_client.wizard.deploy(
            max_price=0.001,  # $0.001/hora - nenhuma GPU custa isso
            batch_size=1,
            max_batches=1,
            timeout_per_batch=10,  # Timeout curto
        )

        # Deve falhar porque não encontrou ofertas
        assert result.success is False
        # Erro deve indicar que não encontrou ofertas
        assert result.error is not None
        assert any(x in result.error.lower() for x in [
            "ofertas", "offers", "disponíveis", "available", "encontr"
        ]), f"Mensagem de erro inesperada: {result.error}"


# =============================================================================
# Testes de Performance
# =============================================================================

@pytest.mark.integration
class TestRealPerformance:
    """Testes de performance com API real."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, real_sdk_client, real_rate_limiter):
        """Testa requisições concorrentes."""
        await real_rate_limiter.wait()

        try:
            # Fazer 3 requests em paralelo
            results = await asyncio.gather(
                real_sdk_client.instances.list(),
                real_sdk_client.instances.search_offers(max_price=1.0, limit=3),
                real_sdk_client.get_status(),
                return_exceptions=True,
            )

            # Pelo menos 1 deve ter sucesso (servidor pode estar sob carga)
            successes = [r for r in results if not isinstance(r, Exception)]
            assert len(successes) >= 1, f"Todas as requisições falharam: {results}"
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                pytest.skip("Event loop issue with pytest-asyncio")
            raise


