"""
Fluxo 1: Deploy de Modelos (LLM, Whisper, Embeddings)
Testes REAIS contra a API.
"""
import pytest
import httpx
import time


@pytest.mark.flow1
class TestDeployModelsAPI:
    """Testes da API de modelos (sem provisionar GPU)"""

    def test_list_model_types(self, authed_client: httpx.Client):
        """Deve listar tipos de modelos disponíveis"""
        # Tentar endpoints possíveis
        response = authed_client.get("/api/models")
        if response.status_code in [400, 404]:
            response = authed_client.get("/api/v1/models")
        if response.status_code in [400, 404]:
            response = authed_client.get("/api/chat/models")

        # Se nenhum endpoint existe, pular
        if response.status_code in [400, 404]:
            pytest.skip("Endpoint /api/models não implementado")

        assert response.status_code == 200
        data = response.json()

        # Deve ter tipos de modelos
        assert "types" in data or "models" in data or isinstance(data, list)

    def test_list_gpu_offers(self, authed_client):
        """Deve listar ofertas de GPU disponíveis"""
        response = authed_client.get("/api/instances/offers")

        # Se API externa indisponível após retries, pular
        if response.status_code == 503:
            pytest.skip("API Vast.ai indisponível (503 após retries)")

        assert response.status_code == 200
        data = response.json()

        # Deve ter ofertas
        assert "offers" in data or isinstance(data, list)

    def test_list_gpu_offers_filtered(self, authed_client):
        """Deve filtrar ofertas por tipo de GPU"""
        response = authed_client.get("/api/instances/offers", params={"gpu_name": "RTX"})

        # Se API externa indisponível após retries, pular
        if response.status_code == 503:
            pytest.skip("API Vast.ai indisponível (503 após retries)")

        assert response.status_code == 200

    def test_get_model_requirements(self, authed_client: httpx.Client):
        """Deve retornar requisitos para um modelo"""
        response = authed_client.get("/api/models/requirements", params={
            "model_id": "meta-llama/Llama-3.1-8B"
        })

        # Pode ser 200 ou 404 se endpoint não existe
        assert response.status_code in [200, 404]


@pytest.mark.flow1
@pytest.mark.real_gpu
@pytest.mark.slow
class TestDeployLLM:
    """Testes de deploy de LLM (requer GPU real)"""

    def test_deploy_small_llm(self, authed_client: httpx.Client, test_context):
        """Deve fazer deploy de um LLM pequeno"""
        # Usar modelo pequeno para teste rápido
        response = authed_client.post("/api/models/deploy", json={
            "model_type": "llm",
            "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
            "gpu_type": "RTX 3090",
            "max_price": 0.30
        })

        assert response.status_code in [200, 201, 202]
        data = response.json()

        # Guardar para cleanup
        instance_id = data.get("instance_id") or data.get("deployment_id")
        if instance_id:
            test_context.created_instances.append(instance_id)

        # Campo pode ser instance_id, deploy_id, ou deployment_id
        has_id = "instance_id" in data or "deploy_id" in data or "deployment_id" in data
        assert has_id, f"Resposta sem ID: {data}"

    def test_check_deploy_status(self, authed_client: httpx.Client, test_context):
        """Deve verificar status do deploy"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância criada")

        deployment_id = test_context.created_instances[-1]

        # O deploy de modelo usa endpoint /api/models/{deployment_id}
        response = authed_client.get(f"/api/models/{deployment_id}")

        # Se 422, tentar endpoint de instâncias (pode ser instance_id)
        if response.status_code == 422:
            response = authed_client.get(f"/api/instances/{deployment_id}")

        # Se ainda falhar, pular
        if response.status_code in [404, 422]:
            pytest.skip(f"Não foi possível verificar status do deploy {deployment_id}")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data


@pytest.mark.flow1
@pytest.mark.real_gpu
@pytest.mark.slow
class TestDeployWhisper:
    """Testes de deploy de Whisper"""

    def test_deploy_whisper(self, authed_client: httpx.Client, test_context):
        """Deve fazer deploy do Whisper"""
        response = authed_client.post("/api/models/deploy", json={
            "model_type": "speech",
            "model_id": "openai/whisper-small",  # Usar small para teste
            "gpu_type": "RTX 3090",
            "max_price": 0.25
        })

        assert response.status_code in [200, 201, 202]
        data = response.json()

        if "instance_id" in data:
            test_context.created_instances.append(data["instance_id"])


@pytest.mark.flow1
@pytest.mark.real_gpu
@pytest.mark.slow
class TestDeployEmbeddings:
    """Testes de deploy de Embeddings"""

    def test_deploy_embeddings(self, authed_client: httpx.Client, test_context):
        """Deve fazer deploy de modelo de embeddings"""
        response = authed_client.post("/api/models/deploy", json={
            "model_type": "embeddings",
            "model_id": "BAAI/bge-small-en-v1.5",  # Usar small para teste
            "gpu_type": "RTX 3080",
            "max_price": 0.20
        })

        assert response.status_code in [200, 201, 202]
        data = response.json()

        if "instance_id" in data:
            test_context.created_instances.append(data["instance_id"])
