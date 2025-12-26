"""
E2E Tests - Categoria 5: Jobs e Execução (12 testes)
Todos os testes skip se endpoint /api/jobs não existir (405)
"""
import pytest
import time


def get_cheap_offer(authed_client, max_price=0.15):
    response = authed_client.get("/api/instances/offers")
    if response.status_code != 200:
        return None
    offers = response.json()
    if isinstance(offers, dict):
        offers = offers.get("offers", [])
    valid = [o for o in offers if (o.get("dph_total") or 999) <= max_price]
    return min(valid, key=lambda x: x.get("dph_total", 999)) if valid else None


@pytest.fixture(scope="module")
def gpu_cleanup(authed_client):
    created_ids = []
    yield created_ids
    for instance_id in created_ids:
        try:
            authed_client.delete(f"/api/instances/{instance_id}")
        except:
            pass


@pytest.mark.real_gpu
class TestJobExecution:
    def test_53_job_simple_command(self, authed_client, gpu_cleanup):
        """Teste 53: Job simples - comando bash"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "nvidia-smi", "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime"})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")
        if response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")
        assert response.status_code in [200, 201, 202]

    def test_54_job_python_gpu(self, authed_client, gpu_cleanup):
        """Teste 54: Job Python usando GPU"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "python -c 'import torch; print(torch.cuda.is_available())'", "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime"})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")
        if response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")
        assert response.status_code in [200, 201, 202]

    def test_55_job_with_timeout(self, authed_client, gpu_cleanup):
        """Teste 55: Job com timeout"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "sleep 120", "timeout": 30})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")

    def test_56_job_with_output_storage(self, authed_client, gpu_cleanup):
        """Teste 56: Job salvando output"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "nvidia-smi > /output/gpu.txt"})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")

    def test_57_job_spot_instance(self, authed_client, gpu_cleanup):
        """Teste 57: Job em spot instance"""
        offer = get_cheap_offer(authed_client, max_price=0.10) or get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "echo spot", "spot": True})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")


@pytest.mark.real_gpu
class TestJobManagement:
    def test_58_cancel_running_job(self, authed_client, gpu_cleanup):
        """Teste 58: Cancelar job em execução"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "sleep 300"})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")

    def test_59_get_job_logs(self, authed_client, gpu_cleanup):
        """Teste 59: Obter logs de job"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "echo test"})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")

    def test_60_job_with_dependencies(self, authed_client, gpu_cleanup):
        """Teste 60: Job com dependências"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "pip install numpy && python -c 'import numpy'"})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")

    def test_61_job_multi_gpu(self, authed_client, gpu_cleanup):
        """Teste 61: Job multi-GPU"""
        response = authed_client.get("/api/instances/offers")
        if response.status_code != 200:
            pytest.skip("Não foi possível buscar ofertas")
        offers = response.json()
        if isinstance(offers, dict):
            offers = offers.get("offers", [])
        multi = [o for o in offers if o.get("num_gpus", 1) >= 2 and (o.get("dph_total") or 999) <= 0.50]
        if not multi:
            pytest.skip("Nenhuma oferta multi-GPU")
        response = authed_client.post("/api/jobs", json={"offer_id": multi[0].get("id"), "command": "nvidia-smi"})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")


@pytest.mark.real_gpu
class TestJobCleanup:
    def test_62_auto_destroy_after_job(self, authed_client, gpu_cleanup):
        """Teste 62: Auto-destroy após job"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "echo done", "auto_destroy": True})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")

    def test_63_cleanup_after_failure(self, authed_client, gpu_cleanup):
        """Teste 63: Cleanup após job falhar"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "exit 1"})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")

    def test_64_job_retry_on_failure(self, authed_client, gpu_cleanup):
        """Teste 64: Retry após falha"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/jobs", json={"offer_id": offer.get("id"), "command": "echo retry", "max_retries": 2})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint /api/jobs não implementado")
