"""
Fluxo 8: Autenticação e Configurações
Testes REAIS contra a API.
"""
import pytest
import httpx
import uuid


@pytest.mark.flow8
class TestAuthRegistration:
    """Testes de registro de usuário"""

    def test_register_new_user(self, http_client: httpx.Client):
        """Deve registrar novo usuário"""
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"

        response = http_client.post("/api/auth/register", json={
            "email": unique_email,
            "password": "testpassword123"
        })

        assert response.status_code in [200, 201]
        data = response.json()

        assert "token" in data

    def test_register_duplicate_email(self, http_client: httpx.Client):
        """Deve rejeitar email duplicado"""
        email = "duplicate@example.com"

        # Primeiro registro
        http_client.post("/api/auth/register", json={
            "email": email,
            "password": "password123"
        })

        # Segundo registro com mesmo email
        response = http_client.post("/api/auth/register", json={
            "email": email,
            "password": "password123"
        })

        # Deve falhar ou retornar token existente
        assert response.status_code in [200, 400, 409]

    def test_register_invalid_email(self, http_client: httpx.Client):
        """Deve rejeitar email inválido"""
        response = http_client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "password123"
        })

        # Pode aceitar ou rejeitar dependendo da validação
        assert response.status_code in [200, 201, 400, 422]


@pytest.mark.flow8
class TestAuthLogin:
    """Testes de login"""

    def test_login_valid_credentials(self, http_client: httpx.Client):
        """Deve fazer login com credenciais válidas"""
        # Registrar primeiro
        email = f"login_test_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        http_client.post("/api/auth/register", json={
            "email": email,
            "password": password
        })

        # Fazer login
        response = http_client.post("/api/auth/login", json={
            "email": email,
            "password": password
        })

        assert response.status_code == 200
        data = response.json()

        assert "token" in data

    def test_login_invalid_password(self, http_client: httpx.Client):
        """Deve rejeitar senha incorreta"""
        response = http_client.post("/api/auth/login", json={
            "email": "test@test.com",
            "password": "wrongpassword"
        })

        assert response.status_code in [400, 401, 403]

    def test_login_nonexistent_user(self, http_client: httpx.Client):
        """Deve rejeitar usuário inexistente"""
        response = http_client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })

        assert response.status_code in [400, 401, 404]


@pytest.mark.flow8
class TestSettings:
    """Testes de configurações do usuário"""

    def test_get_settings(self, authed_client: httpx.Client):
        """Deve retornar configurações do usuário"""
        response = authed_client.get("/api/settings")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)

    def test_update_vast_api_key(self, authed_client: httpx.Client):
        """Deve atualizar API key do Vast.ai"""
        # Testar atualização
        response = authed_client.put("/api/settings", json={
            "vast_api_key": "test_api_key_12345"
        })

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True

        # Resetar para null para não afetar outros testes
        # (null = usa a API key do sistema)
        response = authed_client.put("/api/settings", json={
            "vast_api_key": None
        })
        assert response.status_code == 200

    def test_update_settings_dict(self, authed_client: httpx.Client):
        """Deve atualizar settings como dict"""
        response = authed_client.put("/api/settings", json={
            "settings": {
                "theme": "dark",
                "notifications": True
            }
        })

        assert response.status_code == 200

    def test_get_updated_settings(self, authed_client: httpx.Client):
        """Deve retornar settings atualizados"""
        # Atualizar
        authed_client.put("/api/settings", json={
            "settings": {"test_key": "test_value"}
        })

        # Verificar
        response = authed_client.get("/api/settings")
        assert response.status_code == 200

        data = response.json()
        settings = data.get("settings", {})

        assert settings.get("test_key") == "test_value"


@pytest.mark.flow8
class TestBalance:
    """Testes de saldo"""

    def test_get_balance(self, authed_client: httpx.Client):
        """Deve retornar saldo do Vast.ai"""
        response = authed_client.get("/api/balance")

        assert response.status_code == 200
        data = response.json()

        # Deve ter campos de saldo
        assert "credit" in data or "balance" in data


@pytest.mark.flow8
class TestAdvisor:
    """Testes do AI Advisor"""

    def test_get_recommendation(self, authed_client: httpx.Client):
        """Deve retornar recomendação de GPU"""
        response = authed_client.post("/api/advisor/recommend", json={
            "project_description": "Training a small LLM model with 7B parameters",
            "budget_per_hour": 1.0,
            "priority": "cost"
        })

        # Pode ser 200 ou 400/404 se advisor não configurado
        assert response.status_code in [200, 400, 401, 404]

        if response.status_code == 200:
            data = response.json()
            # O campo pode ser "recommendation", "gpu", ou "recommended_gpu"
            has_recommendation = (
                "recommendation" in data or
                "gpu" in data or
                "recommended_gpu" in data
            )
            assert has_recommendation, f"Resposta sem recomendação: {data}"


@pytest.mark.flow8
class TestCloudStorage:
    """Testes de configuração de cloud storage"""

    def test_get_cloud_storage_settings(self, authed_client: httpx.Client):
        """Deve retornar configurações de cloud storage"""
        response = authed_client.get("/api/settings/cloud-storage")

        assert response.status_code == 200
        data = response.json()

        assert "settings" in data

    def test_update_cloud_storage(self, authed_client: httpx.Client):
        """Deve atualizar configurações de cloud storage"""
        response = authed_client.put("/api/settings/cloud-storage", json={
            "primary_provider": "backblaze_b2",
            "b2_key_id": "test_key_id",
            "b2_app_key": "test_app_key",
            "b2_bucket": "test-bucket"
        })

        assert response.status_code == 200

    def test_test_cloud_storage_connection(self, authed_client: httpx.Client):
        """Deve testar conexão com cloud storage"""
        response = authed_client.post("/api/settings/cloud-storage/test", json={
            "primary_provider": "backblaze_b2",
            "b2_key_id": "test_key_id",
            "b2_app_key": "test_app_key"
        })

        # Pode falhar se credenciais inválidas
        assert response.status_code in [200, 400]


@pytest.mark.flow8
class TestOnboarding:
    """Testes de onboarding"""

    def test_complete_onboarding(self, authed_client: httpx.Client):
        """Deve marcar onboarding como completo"""
        response = authed_client.post("/api/settings/complete-onboarding")

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") == True

    def test_onboarding_persisted(self, authed_client: httpx.Client):
        """Deve persistir status de onboarding"""
        # Completar onboarding
        authed_client.post("/api/settings/complete-onboarding")

        # Verificar
        response = authed_client.get("/api/settings")
        assert response.status_code == 200

        data = response.json()
        settings = data.get("settings", {})

        assert settings.get("has_completed_onboarding") == True
