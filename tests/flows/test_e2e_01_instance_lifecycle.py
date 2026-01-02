"""
E2E Tests - Categoria 1: Ciclo de Vida de Instâncias (15 testes)
Testes REAIS com GPU no VAST.ai - SEM SKIPS, com retry robusto
"""
import pytest
import time
import socket
from helpers import get_offer_with_retry, create_instance_resilient, wait_for_status_resilient, wait_for_ssh


@pytest.fixture(scope="module")
def gpu_cleanup(authed_client):
    created_ids = []
    yield created_ids
    for instance_id in created_ids:
        try:
            authed_client.delete(f"/api/instances/{instance_id}")
        except:
            pass


# =============================================================================
# TESTES BÁSICOS (1-5)
# =============================================================================

@pytest.mark.real_gpu
class TestInstanceBasics:
    def test_01_create_instance_cheap(self, authed_client, gpu_cleanup):
        """Teste 1: Criar instância barata"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        instance_id = create_instance_resilient(authed_client, offer, gpu_cleanup)
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

    def test_02_create_with_custom_image(self, authed_client, gpu_cleanup):
        """Teste 2: Criar com imagem customizada"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        instance_id = create_instance_resilient(
            authed_client, offer, gpu_cleanup,
            image="ollama/ollama", disk_size=30, onstart_cmd="ollama serve &"
        )
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

    def test_03_create_specific_gpu(self, authed_client, gpu_cleanup):
        """Teste 3: Criar instância com GPU específica (ou qualquer disponível)"""
        # Tenta 3090, depois 3080, depois qualquer uma
        offer = get_offer_with_retry(authed_client, max_price=0.50, gpu_filter="3090")
        instance_id = create_instance_resilient(authed_client, offer, gpu_cleanup)
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

    def test_04_create_with_ssh_install(self, authed_client, gpu_cleanup):
        """Teste 4: Criar com script de instalação SSH"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        ssh_script = "apt-get update && apt-get install -y openssh-server && mkdir -p /var/run/sshd && /usr/sbin/sshd"
        instance_id = create_instance_resilient(
            authed_client, offer, gpu_cleanup,
            image="ollama/ollama", disk_size=20, onstart_cmd=ssh_script
        )
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

        response = authed_client.get(f"/api/instances/{instance_id}")
        data = response.json()
        ssh_host = data.get("ssh_host")
        ssh_port = data.get("ssh_port") or 22
        if ssh_host:
            ssh_ready = wait_for_ssh(ssh_host, ssh_port, timeout=60)
            print(f"  SSH disponível: {ssh_ready}")

    def test_05_create_large_disk(self, authed_client, gpu_cleanup):
        """Teste 5: Criar com disco grande"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        instance_id = create_instance_resilient(authed_client, offer, gpu_cleanup, disk_size=50)
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)


# =============================================================================
# TESTES PAUSE/RESUME (6-10)
# =============================================================================

@pytest.mark.real_gpu
class TestPauseResume:
    def test_06_pause_running_instance(self, authed_client, gpu_cleanup):
        """Teste 6: Pausar instância running"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        instance_id = create_instance_resilient(authed_client, offer, gpu_cleanup)
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

        response = authed_client.post(f"/api/instances/{instance_id}/pause")
        assert response.status_code in [200, 202], f"Pause failed: {response.status_code}"

        wait_for_status_resilient(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=180)

    def test_07_resume_paused_instance(self, authed_client, gpu_cleanup):
        """Teste 7: Resume instância pausada"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        instance_id = create_instance_resilient(authed_client, offer, gpu_cleanup)
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

        # Pause
        authed_client.post(f"/api/instances/{instance_id}/pause")
        wait_for_status_resilient(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=180)

        # Resume
        response = authed_client.post(f"/api/instances/{instance_id}/resume")
        assert response.status_code in [200, 202], f"Resume failed: {response.status_code}"

        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

    def test_08_multiple_pause_resume(self, authed_client, gpu_cleanup):
        """Teste 8: Múltiplos pause/resume"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        instance_id = create_instance_resilient(authed_client, offer, gpu_cleanup)
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

        for i in range(2):
            # Pause
            authed_client.post(f"/api/instances/{instance_id}/pause")
            wait_for_status_resilient(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=180)

            # Resume
            authed_client.post(f"/api/instances/{instance_id}/resume")
            wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

    def test_09_cold_start_time(self, authed_client, gpu_cleanup):
        """Teste 9: Medir cold start time"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        instance_id = create_instance_resilient(authed_client, offer, gpu_cleanup)
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

        # Pause
        authed_client.post(f"/api/instances/{instance_id}/pause")
        wait_for_status_resilient(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=180)

        # Medir cold start
        start_time = time.time()
        authed_client.post(f"/api/instances/{instance_id}/resume")
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)
        cold_start = time.time() - start_time

        print(f"  Cold start time: {cold_start:.1f}s")
        assert cold_start < 120, f"Cold start muito lento: {cold_start}s"

    def test_10_pause_nonexistent(self, authed_client, gpu_cleanup):
        """Teste 10: Pausar instância inexistente"""
        response = authed_client.post("/api/instances/99999999/pause")
        assert response.status_code in [404, 500]


# =============================================================================
# TESTES DESTRUIÇÃO (11-15)
# =============================================================================

@pytest.mark.real_gpu
class TestDestruction:
    def test_11_destroy_running(self, authed_client, gpu_cleanup):
        """Teste 11: Destruir instância running"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        instance_id = create_instance_resilient(authed_client, offer, gpu_cleanup)
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

        response = authed_client.delete(f"/api/instances/{instance_id}")
        assert response.status_code in [200, 202, 204]

        # Remover do cleanup já que foi destruída
        if instance_id in gpu_cleanup:
            gpu_cleanup.remove(instance_id)

    def test_12_destroy_paused(self, authed_client, gpu_cleanup):
        """Teste 12: Destruir instância paused"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        instance_id = create_instance_resilient(authed_client, offer, gpu_cleanup)
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

        # Pause primeiro
        authed_client.post(f"/api/instances/{instance_id}/pause")
        wait_for_status_resilient(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=180)

        # Destroy
        response = authed_client.delete(f"/api/instances/{instance_id}")
        assert response.status_code in [200, 202, 204]

        if instance_id in gpu_cleanup:
            gpu_cleanup.remove(instance_id)

    def test_13_destroy_nonexistent(self, authed_client, gpu_cleanup):
        """Teste 13: Destruir instância inexistente"""
        response = authed_client.delete("/api/instances/99999999")
        assert response.status_code in [200, 404, 500]

    def test_14_get_instance_status(self, authed_client, gpu_cleanup):
        """Teste 14: Obter status de instância"""
        offer = get_offer_with_retry(authed_client, max_price=0.50)
        instance_id = create_instance_resilient(authed_client, offer, gpu_cleanup)
        wait_for_status_resilient(authed_client, instance_id, ["running"], timeout=300)

        response = authed_client.get(f"/api/instances/{instance_id}")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "actual_status" in data

    def test_15_list_instances(self, authed_client, gpu_cleanup):
        """Teste 15: Listar instâncias"""
        response = authed_client.get("/api/instances")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))
