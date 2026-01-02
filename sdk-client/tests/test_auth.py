"""
Testes de autenticação do SDK.

Testa login, logout, me, e gerenciamento de tokens.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# =============================================================================
# Testes Unitários (Mock)
# =============================================================================

class TestAuthUnit:
    """Testes unitários de autenticação."""

    @pytest.mark.asyncio
    async def test_client_initialization_with_api_key(self):
        """Testa inicialização com API key."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="dumont_sk_test123",
            base_url="https://api.test.com",
        )

        assert client.api_key == "dumont_sk_test123"
        assert client.base_url == "https://api.test.com"
        await client.close()

    @pytest.mark.asyncio
    async def test_client_initialization_without_api_key(self):
        """Testa inicialização sem API key."""
        from dumont_sdk import DumontClient

        client = DumontClient(base_url="https://api.test.com")

        assert client.api_key is None
        await client.close()

    @pytest.mark.asyncio
    async def test_login_sets_token(self):
        """Testa que login define o token."""
        from dumont_sdk import DumontClient

        client = DumontClient(base_url="https://api.test.com")

        # Mock do método post
        mock_response = {
            "access_token": "jwt_token_123",
            "token_type": "bearer",
            "user": {"id": 1, "email": "test@test.com"},
        }

        with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            # Mock save_token para não salvar em arquivo
            with patch.object(client, 'save_token') as mock_save:
                mock_save.side_effect = lambda t: setattr(client, '_token', t)

                result = await client.login("test@test.com", "password123")

                assert client._token == "jwt_token_123"
                assert result["access_token"] == "jwt_token_123"

        await client.close()

    @pytest.mark.asyncio
    async def test_logout_clears_token(self):
        """Testa que logout limpa o token."""
        from dumont_sdk import DumontClient

        client = DumontClient(base_url="https://api.test.com")
        client._token = "some_token"

        with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"success": True}

            with patch.object(client, 'clear_token') as mock_clear:
                mock_clear.side_effect = lambda: setattr(client, '_token', None)

                await client.logout()

                assert client._token is None

        await client.close()

    @pytest.mark.asyncio
    async def test_auth_header_with_token(self):
        """Testa header de autenticação com token."""
        from dumont_sdk import DumontClient

        client = DumontClient(base_url="https://api.test.com")
        client._token = "my_jwt_token"

        headers = client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer my_jwt_token"
        await client.close()

    @pytest.mark.asyncio
    async def test_auth_header_with_api_key(self):
        """Testa header de autenticação com API key."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="dumont_sk_abc123",
            base_url="https://api.test.com",
        )

        headers = client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer dumont_sk_abc123"
        await client.close()

    @pytest.mark.asyncio
    async def test_api_key_takes_precedence_over_token(self):
        """Testa que API key tem precedência sobre token JWT."""
        from dumont_sdk import DumontClient

        client = DumontClient(
            api_key="dumont_sk_abc123",
            base_url="https://api.test.com",
        )
        client._token = "jwt_token_xyz"

        headers = client._get_headers()

        # API key deve ter precedência (conforme implementação atual)
        assert headers["Authorization"] == "Bearer dumont_sk_abc123"
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Testa uso como context manager."""
        from dumont_sdk import DumontClient

        async with DumontClient(base_url="https://api.test.com") as client:
            assert client is not None
            assert hasattr(client, 'instances')
            assert hasattr(client, 'snapshots')

    @pytest.mark.asyncio
    async def test_me_endpoint(self):
        """Testa endpoint /me."""
        from dumont_sdk import DumontClient

        client = DumontClient(base_url="https://api.test.com")
        client._token = "test_token"

        mock_user = {
            "id": 1,
            "email": "test@test.com",
            "username": "testuser",
        }

        with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            result = await client.me()

            assert result["email"] == "test@test.com"
            mock_get.assert_called_once_with("/api/v1/auth/me")

        await client.close()


# =============================================================================
# Testes de Integração
# =============================================================================

@pytest.mark.integration
class TestAuthIntegration:
    """Testes de integração de autenticação."""

    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, sdk_client, rate_limiter):
        """Testa login com credenciais válidas."""
        import os

        username = os.environ.get("DUMONT_TEST_USERNAME")
        password = os.environ.get("DUMONT_TEST_PASSWORD")

        if not username or not password:
            pytest.skip("Credenciais de teste não configuradas")

        await rate_limiter.wait()
        result = await sdk_client.login(username, password)

        # API pode retornar "token" ou "access_token"
        assert "access_token" in result or "token" in result
        assert sdk_client._token is not None

    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self, sdk_client, rate_limiter):
        """Testa login com credenciais inválidas."""
        await rate_limiter.wait()

        with pytest.raises(Exception):
            await sdk_client.login("invalid@email.com", "wrongpassword")

    @pytest.mark.asyncio
    async def test_me_after_login(self, authenticated_client, rate_limiter):
        """Testa /me após login."""
        await rate_limiter.wait()
        result = await authenticated_client.me()

        # Resposta pode ter "email" diretamente ou dentro de "user"
        if "user" in result:
            user = result["user"]
            assert "email" in user or "username" in user
        else:
            assert "email" in result or "id" in result

    @pytest.mark.asyncio
    async def test_api_key_authentication(self, client_with_api_key, rate_limiter):
        """Testa autenticação via API key."""
        await rate_limiter.wait()

        # Deve conseguir listar instâncias com API key
        instances = await client_with_api_key.instances.list()

        assert isinstance(instances, list)


# =============================================================================
# Testes de Erro
# =============================================================================

class TestAuthErrors:
    """Testes de erros de autenticação."""

    @pytest.mark.asyncio
    async def test_request_without_auth_fails(self):
        """Testa que request sem auth falha."""
        from dumont_sdk import DumontClient

        client = DumontClient(base_url="https://api.dumontcloud.com")

        # Sem token ou API key, deve falhar
        with pytest.raises(Exception):
            await client.instances.list()

        await client.close()

    @pytest.mark.asyncio
    async def test_expired_token_handling(self):
        """Testa handling de token expirado."""
        from dumont_sdk import DumontClient
        from dumont_sdk.exceptions import AuthenticationError

        client = DumontClient(base_url="https://api.test.com")
        client._token = "expired_token_123"

        # Mock _request para simular 401
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = AuthenticationError("Não autenticado")

            with pytest.raises(AuthenticationError):
                await client.get("/api/v1/test")

        await client.close()
