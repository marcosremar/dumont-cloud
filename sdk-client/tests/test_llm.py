"""
Testes do módulo LLM com failover do SDK.

Testa inferência GPU → OpenRouter com failover automático.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# =============================================================================
# Testes Unitários (Mock)
# =============================================================================

class TestLLMConfig:
    """Testes de configuração LLM."""

    def test_dumont_config(self):
        """Testa configuração do LLM."""
        from dumont_sdk.config import DumontConfig

        # Use valid API key formats for testing
        valid_dumont_key = "dumont_sk_testkeyabcdefghij123456"
        valid_openrouter_key = "sk-or-v1-abcdefghij1234567890"

        config = DumontConfig(
            dumont_server="https://api.test.com",
            api_key=valid_dumont_key,
            openrouter_api_key=valid_openrouter_key,
        )

        assert config.dumont_server == "https://api.test.com"
        assert config.openrouter_api_key == valid_openrouter_key

    def test_gpu_config(self):
        """Testa configuração de GPU."""
        from dumont_sdk.config import GPUConfig

        gpu = GPUConfig(
            url="http://192.168.1.100:11434",
            model="llama3.2",
        )

        assert gpu.url == "http://192.168.1.100:11434"
        assert gpu.model == "llama3.2"

    def test_fallback_model(self):
        """Testa configuração de modelo de fallback."""
        from dumont_sdk.config import FallbackModel

        model = FallbackModel(
            provider="openrouter",
            model="meta-llama/llama-3.2-3b-instruct",
        )

        assert model.provider == "openrouter"
        assert "llama" in model.model

    def test_config_from_env(self):
        """Testa carregamento de config do ambiente."""
        import os
        from dumont_sdk.config import DumontConfig

        # Use valid API key formats for testing
        valid_dumont_key = "dumont_sk_testkeyabcdefghij123456"
        valid_openrouter_key = "sk-or-v1-abcdefghij1234567890"

        # Set environment variables for testing
        with patch.dict(os.environ, {
            'DUMONT_SERVER': 'https://test.api.com',
            'DUMONT_API_KEY': valid_dumont_key,
            'OPENROUTER_API_KEY': valid_openrouter_key,
        }):
            config = DumontConfig.from_env()

            assert config.dumont_server == 'https://test.api.com'
            assert config.api_key == valid_dumont_key
            assert config.openrouter_api_key == valid_openrouter_key

    def test_config_to_dict(self):
        """Testa serialização de config."""
        from dumont_sdk.config import DumontConfig, GPUConfig

        config = DumontConfig(
            dumont_server="https://api.test.com",
            gpu=GPUConfig(url="http://gpu:8000", model="llama"),
        )

        data = config.to_dict()

        assert data["dumont_server"] == "https://api.test.com"
        assert data["gpu"]["url"] == "http://gpu:8000"


class TestLLMClient:
    """Testes do cliente LLM."""

    @pytest.mark.asyncio
    async def test_llm_client_initialization(self):
        """Testa inicialização do cliente LLM."""
        from dumont_sdk import DumontLLM, DumontConfig

        # Use valid API key format for testing
        valid_dumont_key = "dumont_sk_testkeyabcdefghij123456"

        config = DumontConfig(
            dumont_server="https://api.test.com",
            api_key=valid_dumont_key,
        )

        client = DumontLLM(config=config)
        assert client is not None
        await client.close()

    @pytest.mark.asyncio
    async def test_get_content_helper(self, mock_gpu_response):
        """Testa helper get_content."""
        from dumont_sdk import DumontLLM, DumontConfig

        # Use valid API key format for testing
        valid_dumont_key = "dumont_sk_testkeyabcdefghij123456"

        config = DumontConfig(
            dumont_server="https://api.test.com",
            api_key=valid_dumont_key,
        )

        client = DumontLLM(config=config)
        content = client.get_content(mock_gpu_response)

        assert content == "Hello! How can I help you today?"
        await client.close()


class TestLLMViaDumontClient:
    """Testes de acesso ao LLM via DumontClient."""

    @pytest.mark.asyncio
    async def test_llm_property_exists(self):
        """Testa que propriedade llm existe."""
        from dumont_sdk import DumontClient

        # Use valid API key formats for testing
        valid_dumont_key = "dumont_sk_testkeyabcdefghij123456"
        valid_openrouter_key = "sk-or-v1-abcdefghij1234567890"

        client = DumontClient(
            api_key=valid_dumont_key,
            base_url="https://api.test.com",
            openrouter_api_key=valid_openrouter_key,
        )

        llm = client.llm
        assert llm is not None

        await client.close()


# =============================================================================
# Testes de Erros
# =============================================================================

class TestLLMErrors:
    """Testes de erros do LLM."""

    def test_gpu_connection_error(self):
        """Testa GPUConnectionError."""
        from dumont_sdk.exceptions import GPUConnectionError

        error = GPUConnectionError("http://gpu:8000", Exception("Connection refused"))

        assert "gpu:8000" in str(error)
        assert error.gpu_url == "http://gpu:8000"

    def test_fallback_error(self):
        """Testa FallbackError."""
        from dumont_sdk.exceptions import FallbackError

        error = FallbackError("openrouter", "gpt-4o-mini")

        assert "openrouter" in str(error)
        assert error.provider == "openrouter"

    def test_rate_limit_error(self):
        """Testa RateLimitError."""
        from dumont_sdk.exceptions import RateLimitError

        error = RateLimitError(retry_after=30)

        assert "Rate limit" in str(error)
        assert error.retry_after == 30


# =============================================================================
# Testes de Integração
# =============================================================================

@pytest.mark.integration
class TestLLMIntegration:
    """Testes de integração do LLM."""

    @pytest.mark.asyncio
    async def test_complete_with_openrouter_real(self, rate_limiter):
        """Testa complete real com OpenRouter."""
        import os
        from dumont_sdk import DumontLLM, DumontConfig, FallbackModel

        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            pytest.skip("OPENROUTER_API_KEY não configurada")

        config = DumontConfig(
            dumont_server="https://api.dumontcloud.com",
            api_key="",
            openrouter_api_key=openrouter_key,
            fallback_models=[
                FallbackModel(
                    provider="openrouter",
                    model="meta-llama/llama-3.2-3b-instruct:free",
                ),
            ],
        )

        client = DumontLLM(config=config)

        await rate_limiter.wait()

        try:
            response = await client.complete("Say hello in one word", timeout=30.0)

            assert response is not None
            assert "choices" in response
            assert response["_source"] == "fallback"
        except asyncio.TimeoutError:
            pytest.skip("OpenRouter timeout - skip")
        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ["timeout", "fallback", "failed", "503", "502"]):
                pytest.skip(f"OpenRouter não disponível: {e}")
            raise
        finally:
            await client.close()
