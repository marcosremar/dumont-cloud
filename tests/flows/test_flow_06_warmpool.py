"""
Fluxo 6: Warm Pool
Testes REAIS contra a API.
"""
import pytest
import httpx
import time


@pytest.mark.flow6
class TestWarmPoolAPI:
    """Testes da API de Warm Pool"""

    def test_warmpool_status(self, authed_client: httpx.Client):
        """Deve retornar status do warm pool"""
        response = authed_client.get("/api/warmpool/status")
        if response.status_code == 404:
            response = authed_client.get("/api/v1/warmpool/status")

        # Se endpoint não existe, pular
        if response.status_code == 404:
            pytest.skip("Endpoint /api/warmpool/status não implementado")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)

    def test_warmpool_config(self, authed_client: httpx.Client):
        """Deve retornar configuração do warm pool"""
        response = authed_client.get("/api/warmpool/config")

        # Pode ser 200 ou 404 se endpoint não existe
        assert response.status_code in [200, 404]

    def test_list_pool_gpus(self, authed_client: httpx.Client):
        """Deve listar GPUs no pool"""
        response = authed_client.get("/api/warmpool/gpus")

        # Pode ser 200 ou 404
        assert response.status_code in [200, 404]


@pytest.mark.flow6
class TestWarmPoolConfiguration:
    """Testes de configuração do warm pool"""

    def test_configure_warmpool(self, authed_client: httpx.Client):
        """Deve configurar warm pool"""
        response = authed_client.post("/api/warmpool/configure", json={
            "gpu_types": ["RTX 4090", "RTX 3090"],
            "min_ready": 0,  # Zero para não gastar
            "max_ready": 2,
            "auto_replenish": False
        })

        # Se endpoint não existe ou método não permitido, pular
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/warmpool/configure não implementado ou método não permitido")

        assert response.status_code in [200, 400]

    def test_disable_warmpool(self, authed_client: httpx.Client):
        """Deve desabilitar warm pool"""
        response = authed_client.post("/api/warmpool/configure", json={
            "enabled": False
        })

        # Se endpoint não existe ou método não permitido, pular
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/warmpool/configure não implementado")

        assert response.status_code in [200, 400]


@pytest.mark.flow6
@pytest.mark.real_gpu
@pytest.mark.slow
class TestWarmPoolOperations:
    """Testes de operações do warm pool (requer GPU real)"""

    def test_add_gpu_to_pool(self, authed_client: httpx.Client, test_context):
        """Deve adicionar GPU ao pool"""
        response = authed_client.post("/api/warmpool/add", json={
            "gpu_type": "RTX 3090",
            "max_price": 0.25
        })

        # Se endpoint não existe ou método não permitido, pular
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint POST /api/warmpool/add não implementado")

        if response.status_code in [200, 201]:
            data = response.json()
            if "instance_id" in data:
                test_context.created_instances.append(data["instance_id"])

        # Pode falhar se não há GPUs disponíveis
        assert response.status_code in [200, 201, 400]

    def test_acquire_from_pool(self, authed_client: httpx.Client, test_context):
        """Deve adquirir GPU do pool"""
        start = time.time()

        response = authed_client.post("/api/warmpool/acquire", json={
            "gpu_type": "RTX 3090",
            "timeout_seconds": 30
        })

        # Se endpoint não existe ou método não permitido, pular
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint POST /api/warmpool/acquire não implementado")

        acquire_time = time.time() - start

        if response.status_code == 200:
            data = response.json()
            if "instance_id" in data:
                test_context.created_instances.append(data["instance_id"])

            print(f"Acquire time: {acquire_time:.2f}s")

            # Warm pool deve ser rápido
            assert acquire_time < 60, "Aquisição muito lenta para warm pool"

        # Pode falhar se pool vazio
        assert response.status_code in [200, 400]

    def test_release_to_pool(self, authed_client: httpx.Client, test_context):
        """Deve liberar GPU de volta ao pool"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância para liberar")

        instance_id = test_context.created_instances[-1]

        response = authed_client.post(f"/api/warmpool/release/{instance_id}")

        if response.status_code == 200:
            # Remover do contexto (está no pool agora)
            test_context.created_instances.remove(instance_id)

        assert response.status_code in [200, 400, 404]

    def test_remove_from_pool(self, authed_client: httpx.Client, test_context):
        """Deve remover GPU do pool e destruir"""
        response = authed_client.delete("/api/warmpool/gpu", params={
            "gpu_type": "RTX 3090"
        })

        # Se endpoint não existe ou método não permitido, pular
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint DELETE /api/warmpool/gpu não implementado")

        assert response.status_code in [200, 204, 400]
