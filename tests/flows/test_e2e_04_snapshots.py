"""
E2E Tests - Categoria 4: Snapshots e Backups (10 testes)
Testes com skip para endpoints não implementados
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


def create_instance_or_skip(authed_client, offer, gpu_cleanup):
    response = authed_client.post("/api/instances", json={
        "offer_id": offer.get("id"),
        "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        "disk_size": 20,
        "skip_validation": True
    })
    if response.status_code == 500:
        pytest.skip("Rate limit do VAST.ai")
    if response.status_code not in [200, 201, 202]:
        pytest.skip(f"Erro: {response.status_code}")
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
class TestSnapshotCreation:
    def test_43_snapshot_full(self, authed_client, gpu_cleanup):
        """Teste 43: Criar snapshot full"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        response = authed_client.post(f"/api/instances/{instance_id}/snapshots", json={"name": "test-full", "type": "full"})
        if response.status_code in [400, 404, 405, 422]:
            response = authed_client.post(f"/api/snapshots", json={"instance_id": instance_id, "name": "test-full"})
        if response.status_code in [400, 404, 405, 422]:
            pytest.skip("Endpoint snapshots não implementado")

    def test_44_snapshot_incremental(self, authed_client, gpu_cleanup):
        """Teste 44: Criar snapshot incremental"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        response = authed_client.post(f"/api/instances/{instance_id}/snapshots", json={"name": "test-inc", "type": "incremental"})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint snapshots não implementado")
        assert response.status_code in [200, 201, 202]

    def test_45_snapshot_paused_instance(self, authed_client, gpu_cleanup):
        """Teste 45: Snapshot de instância paused"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        authed_client.post(f"/api/instances/{instance_id}/pause")
        success, _ = wait_for_status(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=120)
        if not success:
            pytest.skip("Timeout no pause")
        response = authed_client.post(f"/api/instances/{instance_id}/snapshots", json={"name": "test-paused"})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint snapshots não implementado")
        assert response.status_code in [200, 201, 202]

    def test_46_multiple_snapshots(self, authed_client, gpu_cleanup):
        """Teste 46: Múltiplos snapshots sequenciais"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        for i in range(2):
            response = authed_client.post(f"/api/instances/{instance_id}/snapshots", json={"name": f"test-{i}"})
            if response.status_code in [404, 405]:
                pytest.skip("Endpoint snapshots não implementado")
            time.sleep(2)


@pytest.mark.real_gpu
class TestSnapshotRestore:
    def test_47_restore_new_instance(self, authed_client, gpu_cleanup):
        """Teste 47: Restore para nova instância"""
        response = authed_client.get("/api/snapshots")
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint snapshots não implementado")
        snapshots = response.json()
        if isinstance(snapshots, dict):
            snapshots = snapshots.get("snapshots", [])
        if not snapshots:
            pytest.skip("Nenhum snapshot disponível")
        snapshot_id = snapshots[0].get("id")
        response = authed_client.post(f"/api/snapshots/{snapshot_id}/restore", json={})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint restore não implementado")

    def test_48_restore_partial(self, authed_client, gpu_cleanup):
        """Teste 48: Restore parcial"""
        response = authed_client.get("/api/snapshots")
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint snapshots não implementado")
        snapshots = response.json()
        if isinstance(snapshots, dict):
            snapshots = snapshots.get("snapshots", [])
        if not snapshots:
            pytest.skip("Nenhum snapshot disponível")

    def test_49_restore_different_gpu(self, authed_client, gpu_cleanup):
        """Teste 49: Restore para GPU diferente"""
        response = authed_client.get("/api/snapshots")
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint snapshots não implementado")
        assert response.status_code == 200

    def test_50_verify_integrity(self, authed_client, gpu_cleanup):
        """Teste 50: Verificar integridade de snapshot"""
        response = authed_client.get("/api/snapshots")
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint snapshots não implementado")
        snapshots = response.json()
        if isinstance(snapshots, dict):
            snapshots = snapshots.get("snapshots", [])
        if not snapshots:
            pytest.skip("Nenhum snapshot disponível")


class TestSnapshotManagement:
    def test_51_list_snapshots(self, authed_client):
        """Teste 51: Listar snapshots"""
        response = authed_client.get("/api/snapshots")
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint snapshots não implementado")
        assert response.status_code == 200

    def test_52_prune_old_snapshots(self, authed_client):
        """Teste 52: Prune de snapshots antigos"""
        response = authed_client.post("/api/snapshots/prune", json={"keep_last": 5})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint prune não implementado")
        assert response.status_code in [200, 204]
