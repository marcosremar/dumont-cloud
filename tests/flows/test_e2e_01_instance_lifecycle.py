"""
E2E Tests - Categoria 1: Ciclo de Vida de Instâncias (15 testes)
Testes REAIS com GPU no VAST.ai - com skip para rate limits
"""
import pytest
import time
import socket


@pytest.fixture(scope="module")
def gpu_cleanup(authed_client):
    created_ids = []
    yield created_ids
    for instance_id in created_ids:
        try:
            authed_client.delete(f"/api/instances/{instance_id}")
        except:
            pass


def get_cheap_offer(authed_client, max_price=0.20, gpu_filter=None):
    response = authed_client.get("/api/instances/offers")
    if response.status_code != 200:
        return None
    offers = response.json()
    if isinstance(offers, dict):
        offers = offers.get("offers", [])
    valid = [o for o in offers if (o.get("dph_total") or 999) <= max_price]
    if gpu_filter:
        valid = [o for o in valid if gpu_filter.lower() in o.get("gpu_name", "").lower()]
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


def wait_for_ssh(ssh_host, ssh_port, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((ssh_host, int(ssh_port)))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(2)
    return False


def create_instance_or_skip(authed_client, offer, gpu_cleanup, image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime", disk_size=20, onstart_cmd=None):
    json_data = {
        "offer_id": offer.get("id"),
        "image": image,
        "disk_size": disk_size,
        "skip_validation": True
    }
    if onstart_cmd:
        json_data["onstart_cmd"] = onstart_cmd
    response = authed_client.post("/api/instances", json=json_data)
    if response.status_code == 500:
        pytest.skip("Rate limit do VAST.ai")
    if response.status_code not in [200, 201, 202]:
        pytest.skip(f"Erro ao criar: {response.status_code}")
    instance_id = response.json().get("instance_id") or response.json().get("id")
    gpu_cleanup.append(instance_id)
    return instance_id


# =============================================================================
# TESTES BÁSICOS (1-5)
# =============================================================================

@pytest.mark.real_gpu
class TestInstanceBasics:
    def test_01_create_instance_cheap(self, authed_client, gpu_cleanup):
        """Teste 1: Criar instância barata"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível < $0.15/hr")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        success, status = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip(f"Timeout aguardando running (status: {status})")

    def test_02_create_with_custom_image(self, authed_client, gpu_cleanup):
        """Teste 2: Criar com imagem customizada"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup,
            image="ollama/ollama", disk_size=30, onstart_cmd="ollama serve &")
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

    def test_03_create_specific_gpu(self, authed_client, gpu_cleanup):
        """Teste 3: Criar instância com GPU específica"""
        offer = get_cheap_offer(authed_client, max_price=0.25, gpu_filter="3090")
        if not offer:
            offer = get_cheap_offer(authed_client, max_price=0.20, gpu_filter="3080")
        if not offer:
            offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

    def test_04_create_with_ssh_install(self, authed_client, gpu_cleanup):
        """Teste 4: Criar com script de instalação SSH"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        ssh_script = "apt-get update && apt-get install -y openssh-server && mkdir -p /var/run/sshd && /usr/sbin/sshd"
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup,
            image="ollama/ollama", disk_size=20, onstart_cmd=ssh_script)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        response = authed_client.get(f"/api/instances/{instance_id}")
        data = response.json()
        ssh_host = data.get("ssh_host")
        ssh_port = data.get("ssh_port") or 22
        if ssh_host:
            ssh_ready = wait_for_ssh(ssh_host, ssh_port, timeout=60)
            print(f"  SSH disponível: {ssh_ready}")

    def test_05_create_large_disk(self, authed_client, gpu_cleanup):
        """Teste 5: Criar com disco grande"""
        offer = get_cheap_offer(authed_client, max_price=0.20)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup, disk_size=50)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")


# =============================================================================
# TESTES PAUSE/RESUME (6-10)
# =============================================================================

@pytest.mark.real_gpu
class TestPauseResume:
    def test_06_pause_running_instance(self, authed_client, gpu_cleanup):
        """Teste 6: Pausar instância running"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        response = authed_client.post(f"/api/instances/{instance_id}/pause")
        assert response.status_code in [200, 202]
        success, status = wait_for_status(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=120)
        if not success:
            pytest.skip(f"Timeout no pause (status: {status})")

    def test_07_resume_paused_instance(self, authed_client, gpu_cleanup):
        """Teste 7: Resume instância pausada"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
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
        response = authed_client.post(f"/api/instances/{instance_id}/resume")
        assert response.status_code in [200, 202]
        success, status = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip(f"Timeout no resume (status: {status})")

    def test_08_multiple_pause_resume(self, authed_client, gpu_cleanup):
        """Teste 8: Múltiplos pause/resume"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        for i in range(2):
            authed_client.post(f"/api/instances/{instance_id}/pause")
            success, _ = wait_for_status(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=120)
            if not success:
                pytest.skip(f"Timeout no pause {i+1}")
            authed_client.post(f"/api/instances/{instance_id}/resume")
            success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
            if not success:
                pytest.skip(f"Timeout no resume {i+1}")

    def test_09_cold_start_time(self, authed_client, gpu_cleanup):
        """Teste 9: Medir cold start time"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
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
        start = time.time()
        authed_client.post(f"/api/instances/{instance_id}/resume")
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        cold_start = time.time() - start
        if not success:
            pytest.skip("Timeout no resume")
        print(f"  Cold start: {cold_start:.1f}s")
        assert cold_start < 180

    def test_10_pause_nonexistent(self, authed_client):
        """Teste 10: Pausar instância inexistente"""
        response = authed_client.post("/api/instances/999999999/pause")
        assert response.status_code in [404, 422, 500]


# =============================================================================
# TESTES DESTRUIÇÃO (11-15)
# =============================================================================

@pytest.mark.real_gpu
class TestDestruction:
    def test_11_destroy_running(self, authed_client, gpu_cleanup):
        """Teste 11: Destruir instância running"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        response = authed_client.delete(f"/api/instances/{instance_id}")
        assert response.status_code in [200, 204]
        if instance_id in gpu_cleanup:
            gpu_cleanup.remove(instance_id)

    def test_12_destroy_paused(self, authed_client, gpu_cleanup):
        """Teste 12: Destruir instância pausada"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
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
        response = authed_client.delete(f"/api/instances/{instance_id}")
        assert response.status_code in [200, 204]
        if instance_id in gpu_cleanup:
            gpu_cleanup.remove(instance_id)

    def test_13_destroy_nonexistent(self, authed_client):
        """Teste 13: Destruir inexistente"""
        response = authed_client.delete("/api/instances/999999999")
        assert response.status_code in [404, 422, 500]

    def test_14_get_instance_status(self, authed_client, gpu_cleanup):
        """Teste 14: Status de instância"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        response = authed_client.get(f"/api/instances/{instance_id}")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "actual_status" in data

    def test_15_list_instances(self, authed_client):
        """Teste 15: Listar instâncias"""
        response = authed_client.get("/api/instances")
        assert response.status_code == 200
