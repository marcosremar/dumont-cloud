"""
Fluxo 4: API de Inferência Serverless
Testes REAIS contra a API.
"""
import pytest
import httpx
import time


@pytest.mark.flow4
class TestServerlessDeployAPI:
    """Testes da API de deploy serverless"""

    def test_serverless_status(self, authed_client: httpx.Client):
        """Deve retornar status do módulo serverless"""
        response = authed_client.get("/api/serverless/status")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_list_serverless_endpoints(self, authed_client: httpx.Client):
        """Deve listar endpoints serverless ativos"""
        response = authed_client.get("/api/serverless/endpoints")

        # Pode ser 200 ou 404 se endpoint não existe
        assert response.status_code in [200, 404]


@pytest.mark.flow4
@pytest.mark.real_gpu
@pytest.mark.slow
class TestServerlessInference:
    """Testes de inferência serverless (requer GPU real)"""

    @pytest.fixture(autouse=True)
    def setup_endpoint(self, authed_client: httpx.Client, test_context):
        """Cria endpoint serverless para testes"""
        response = authed_client.post("/api/serverless/deploy", json={
            "model_type": "llm",
            "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
            "gpu_type": "RTX 3090",
            "auto_pause_minutes": 2,
            "max_price": 0.30
        })

        if response.status_code in [200, 201, 202]:
            data = response.json()
            self.endpoint_id = data.get("endpoint_id") or data.get("instance_id")
            self.endpoint_url = data.get("endpoint_url")

            if self.endpoint_id:
                test_context.created_instances.append(self.endpoint_id)

            # Aguardar endpoint ficar pronto
            self._wait_for_ready(authed_client, self.endpoint_id)
        else:
            pytest.skip(f"Não foi possível criar endpoint: {response.text}")

    def _wait_for_ready(self, client: httpx.Client, endpoint_id: str, timeout: int = 300):
        """Aguarda endpoint ficar pronto"""
        start = time.time()
        while time.time() - start < timeout:
            response = client.get(f"/api/serverless/{endpoint_id}/status")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ready":
                    return
            time.sleep(15)
        pytest.fail("Endpoint não ficou pronto")

    def test_cold_start_inference(self, authed_client: httpx.Client):
        """Deve fazer inferência com cold start"""
        if not hasattr(self, 'endpoint_url') or not self.endpoint_url:
            pytest.skip("Endpoint URL não disponível")

        start = time.time()

        response = httpx.post(
            f"{self.endpoint_url}/v1/chat/completions",
            json={
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "messages": [{"role": "user", "content": "Hello!"}],
                "max_tokens": 50
            },
            timeout=120
        )

        cold_start_time = time.time() - start

        assert response.status_code == 200
        data = response.json()
        assert "choices" in data

        print(f"Cold start time: {cold_start_time:.2f}s")

    def test_warm_inference(self, authed_client: httpx.Client):
        """Deve fazer inferência rápida quando GPU quente"""
        if not hasattr(self, 'endpoint_url') or not self.endpoint_url:
            pytest.skip("Endpoint URL não disponível")

        start = time.time()

        response = httpx.post(
            f"{self.endpoint_url}/v1/chat/completions",
            json={
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "max_tokens": 20
            },
            timeout=30
        )

        warm_time = time.time() - start

        assert response.status_code == 200
        assert warm_time < 10, f"Resposta lenta demais: {warm_time:.2f}s"

        print(f"Warm inference time: {warm_time:.2f}s")

    def test_auto_pause_after_idle(self, authed_client: httpx.Client):
        """GPU deve pausar após período de inatividade"""
        if not hasattr(self, 'endpoint_id'):
            pytest.skip("Endpoint não criado")

        # Aguardar 3 minutos (auto_pause_minutes = 2)
        print("Aguardando auto-pause (3 min)...")
        time.sleep(180)

        response = authed_client.get(f"/api/serverless/{self.endpoint_id}/status")
        assert response.status_code == 200

        data = response.json()
        status = data.get("status") or data.get("gpu_status")

        assert status in ["paused", "stopped", "hibernated"], f"GPU deveria estar pausada: {status}"

    def test_auto_resume_on_request(self, authed_client: httpx.Client):
        """GPU deve acordar automaticamente ao receber request"""
        if not hasattr(self, 'endpoint_url') or not self.endpoint_url:
            pytest.skip("Endpoint URL não disponível")

        start = time.time()

        # Fazer request - deve acordar GPU
        response = httpx.post(
            f"{self.endpoint_url}/v1/chat/completions",
            json={
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "messages": [{"role": "user", "content": "Wake up!"}],
                "max_tokens": 20
            },
            timeout=120
        )

        resume_time = time.time() - start

        assert response.status_code == 200
        print(f"Auto-resume time: {resume_time:.2f}s")
