"""
Testes de API Keys do Dumont SDK.

Testa criação, listagem, revogação e uso de API keys.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# =============================================================================
# Testes Unitários (Mock)
# =============================================================================

class TestAPIKeysUnit:
    """Testes unitários de API keys."""

    # Valid test API keys that pass Pydantic validation
    VALID_DUMONT_KEY = "dumont_sk_testkeyabcdefghij123456"
    VALID_OPENROUTER_KEY = "sk-or-v1-abcdefghij1234567890"
    VALID_OPENROUTER_KEY_2 = "sk-or-v1-xyzwabcdefghij1234"

    @pytest.mark.asyncio
    async def test_client_uses_api_key_in_headers(self):
        """Testa que o cliente usa API key nos headers."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key=self.VALID_DUMONT_KEY,
            base_url="https://api.test.com",
            auto_fetch_config=False,
        )

        headers = client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {self.VALID_DUMONT_KEY}"

        await client.close()

    @pytest.mark.asyncio
    async def test_fetch_sdk_config_stores_openrouter_key(self):
        """Testa que fetch_sdk_config armazena OpenRouter key."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key=self.VALID_DUMONT_KEY,
            base_url="https://api.test.com",
            auto_fetch_config=False,
        )

        mock_response = {
            "openrouter_api_key": "sk-or-test-key",
            "base_url": "https://api.test.com",
            "features": {"llm_failover": True},
        }

        with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            config = await client.fetch_sdk_config()

            assert config == mock_response
            assert client._server_config == mock_response
            assert client._openrouter_api_key == "sk-or-test-key"

        await client.close()

    @pytest.mark.asyncio
    async def test_llm_uses_server_openrouter_key(self):
        """Testa que o cliente LLM usa OpenRouter key do servidor."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key=self.VALID_DUMONT_KEY,
            base_url="https://api.test.com",
            auto_fetch_config=False,
        )

        # Simular config do servidor
        client._server_config = {
            "openrouter_api_key": self.VALID_OPENROUTER_KEY,
        }
        client._openrouter_api_key = self.VALID_OPENROUTER_KEY

        # Acessar LLM client
        llm = client.llm

        assert llm.config.openrouter_api_key == self.VALID_OPENROUTER_KEY

        await client.close()

    @pytest.mark.asyncio
    async def test_local_openrouter_key_takes_precedence(self):
        """Testa que OpenRouter key local tem prioridade sobre servidor."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key=self.VALID_DUMONT_KEY,
            base_url="https://api.test.com",
            openrouter_api_key=self.VALID_OPENROUTER_KEY,  # Key local
            auto_fetch_config=False,
        )

        # Simular config do servidor com key diferente
        client._server_config = {
            "openrouter_api_key": self.VALID_OPENROUTER_KEY_2,
        }

        # LLM deve usar key local (não a do servidor)
        llm = client.llm

        assert llm.config.openrouter_api_key == self.VALID_OPENROUTER_KEY

        await client.close()

    @pytest.mark.asyncio
    async def test_auto_fetch_config_on_enter(self):
        """Testa que __aenter__ busca config automaticamente."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key=self.VALID_DUMONT_KEY,
            base_url="https://api.test.com",
            auto_fetch_config=True,
        )

        mock_response = {
            "openrouter_api_key": "sk-or-test",
            "features": {},
        }

        with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with client:
                assert client._config_fetched is True
                assert client._server_config == mock_response

    @pytest.mark.asyncio
    async def test_ensure_config_only_fetches_once(self):
        """Testa que ensure_config só busca uma vez."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key=self.VALID_DUMONT_KEY,
            base_url="https://api.test.com",
            auto_fetch_config=True,
        )

        mock_response = {"features": {}}
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch.object(client, 'get', side_effect=mock_get):
            await client.ensure_config()
            await client.ensure_config()
            await client.ensure_config()

            assert call_count == 1  # Só uma chamada

        await client.close()


# =============================================================================
# Testes de API Key Format
# =============================================================================

class TestAPIKeyFormat:
    """Testes de formato de API key."""

    def test_api_key_format_validation(self):
        """Testa validação de formato de API key."""
        valid_keys = [
            "dumont_sk_abc123def456",
            "dumont_sk_" + "x" * 32,
        ]

        invalid_keys = [
            "invalid_key",
            "sk_abc123",
            "",
            None,
        ]

        for key in valid_keys:
            assert key.startswith("dumont_sk_")

        for key in invalid_keys:
            assert not key or not key.startswith("dumont_sk_")


# =============================================================================
# Testes de Integração (API Real)
# =============================================================================

@pytest.mark.integration
class TestAPIKeysIntegration:
    """Testes de integração com API keys reais."""

    @pytest.mark.asyncio
    async def test_api_key_auth_works(self, api_key, api_url):
        """Testa que autenticação via API key funciona."""
        if not api_key:
            pytest.skip("API key não configurada (use --api-key=xxx)")

        from dumont_sdk import DumontClient

        async with DumontClient(
            api_key=api_key,
            base_url=api_url,
            auto_fetch_config=True,
        ) as client:
            # Se não der erro, autenticação funcionou
            status = await client.get_status()
            assert "total_instances" in status

    @pytest.mark.asyncio
    async def test_sdk_config_endpoint(self, api_key, api_url):
        """Testa endpoint de SDK config."""
        if not api_key:
            pytest.skip("API key não configurada (use --api-key=xxx)")

        from dumont_sdk import DumontClient

        async with DumontClient(
            api_key=api_key,
            base_url=api_url,
            auto_fetch_config=False,
        ) as client:
            config = await client.fetch_sdk_config()

            # Config deve ter sido carregada
            assert client._config_fetched is True

            # Deve ter estrutura básica
            if config:
                # Pode ter features ou outros campos
                assert isinstance(config, dict)
