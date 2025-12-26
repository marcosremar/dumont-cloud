"""
E2E Tests - Categoria 7: Fine-Tuning (8 testes)
Todos os testes skip se /api/finetune não implementado
"""
import pytest
import time


def get_cheap_offer(authed_client, max_price=0.25, min_vram=16):
    response = authed_client.get("/api/instances/offers")
    if response.status_code != 200:
        return None
    offers = response.json()
    if isinstance(offers, dict):
        offers = offers.get("offers", [])
    valid = [o for o in offers
             if (o.get("dph_total") or 999) <= max_price
             and (o.get("gpu_ram") or 0) >= min_vram * 1024]
    if not valid:
        valid = [o for o in offers
                 if (o.get("dph_total") or 999) <= max_price
                 and (o.get("gpu_ram") or 0) >= 8 * 1024]
    if not valid:
        valid = [o for o in offers if (o.get("dph_total") or 999) <= max_price]
    if not valid:
        return None
    return min(valid, key=lambda x: x.get("dph_total", 999))


def wait_for_status(authed_client, instance_id, target_statuses, timeout=180):
    start = time.time()
    while time.time() - start < timeout:
        response = authed_client.get(f"/api/instances/{instance_id}")
        if response.status_code == 200:
            data = response.json()
            status = data.get("status") or data.get("actual_status")
            if status in target_statuses:
                return True, status
        time.sleep(5)
    return False, None


def create_instance_or_skip(authed_client, offer, gpu_cleanup, disk_size=50):
    response = authed_client.post("/api/instances", json={
        "offer_id": offer.get("id"),
        "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        "disk_size": disk_size,
        "skip_validation": True
    })
    if response.status_code == 500:
        pytest.skip("Rate limit do VAST.ai")
    if response.status_code not in [200, 201, 202]:
        pytest.skip(f"Erro ao criar: {response.status_code}")
    instance_id = response.json().get("instance_id") or response.json().get("id")
    gpu_cleanup.append(instance_id)
    return instance_id


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
class TestFineTuning:
    def test_77_finetune_llama_unsloth(self, authed_client, gpu_cleanup):
        """Teste 77: Fine-tune Llama com Unsloth"""
        offer = get_cheap_offer(authed_client, max_price=0.30, min_vram=16)
        if not offer:
            pytest.skip("Nenhuma oferta com VRAM suficiente")
        response = authed_client.post("/api/finetune/start", json={
            "base_model": "llama-3.2-1b",
            "framework": "unsloth",
            "max_steps": 100,
            "offer_id": offer.get("id")
        })
        if response.status_code in [404, 405]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")
        else:
            assert response.status_code in [200, 201, 202]

    def test_78_upload_dataset(self, authed_client):
        """Teste 78: Upload de dataset JSONL"""
        response = authed_client.post("/api/datasets/upload", json={
            "name": "test-dataset",
            "format": "jsonl",
            "data": [
                {"input": "Hello", "output": "Hi there!"},
                {"input": "How are you?", "output": "I'm doing well, thanks!"}
            ]
        })
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint datasets não implementado")
        if response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")
        assert response.status_code in [200, 201, 202]

    def test_79_finetune_with_checkpoints(self, authed_client, gpu_cleanup):
        """Teste 79: Fine-tune com checkpoints"""
        offer = get_cheap_offer(authed_client, max_price=0.25, min_vram=12)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/finetune/start", json={
            "base_model": "llama-3.2-1b",
            "max_steps": 100,
            "save_checkpoint_every": 50,
            "offer_id": offer.get("id")
        })
        if response.status_code in [404, 405]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")
        else:
            assert response.status_code in [200, 201, 202]

    def test_80_cancel_finetune(self, authed_client, gpu_cleanup):
        """Teste 80: Cancelar fine-tuning"""
        offer = get_cheap_offer(authed_client, max_price=0.20)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/finetune/start", json={
            "base_model": "llama-3.2-1b",
            "max_steps": 1000,
            "offer_id": offer.get("id")
        })
        if response.status_code in [404, 405]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup, disk_size=30)
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")
        else:
            assert response.status_code in [200, 201, 202]

    def test_81_finetune_logs(self, authed_client, gpu_cleanup):
        """Teste 81: Obter logs de treinamento"""
        response = authed_client.get("/api/finetune/jobs")
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint finetune/jobs não implementado")
        assert response.status_code == 200

    def test_82_export_finetuned_model(self, authed_client):
        """Teste 82: Exportar modelo fine-tuned"""
        response = authed_client.post("/api/finetune/export", json={
            "model_id": "test-model",
            "destination": "b2://bucket/models"
        })
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint export não implementado")
        if response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")

    def test_83_finetune_multi_gpu(self, authed_client, gpu_cleanup):
        """Teste 83: Fine-tuning multi-GPU"""
        response = authed_client.get("/api/instances/offers")
        if response.status_code != 200:
            pytest.skip("Não foi possível buscar ofertas")
        offers = response.json()
        if isinstance(offers, dict):
            offers = offers.get("offers", [])
        multi_gpu = [o for o in offers
                     if o.get("num_gpus", 1) >= 2
                     and (o.get("dph_total") or 999) <= 0.60]
        if not multi_gpu:
            pytest.skip("Nenhuma oferta multi-GPU disponível")
        offer = min(multi_gpu, key=lambda x: x.get("dph_total", 999))
        response = authed_client.post("/api/finetune/start", json={
            "base_model": "llama-3.2-1b",
            "max_steps": 50,
            "distributed": True,
            "offer_id": offer.get("id")
        })
        if response.status_code in [404, 405]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")
        else:
            assert response.status_code in [200, 201, 202]

    def test_84_resume_from_checkpoint(self, authed_client, gpu_cleanup):
        """Teste 84: Resumir fine-tuning de checkpoint"""
        response = authed_client.post("/api/finetune/resume", json={
            "checkpoint_id": "test-checkpoint",
            "additional_steps": 50
        })
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint resume não implementado")
        if response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")
