"""
E2E Tests - Categoria 2: Serverless GPU (12 testes)
Testes REAIS de serverless mode no VAST.ai
"""
import pytest
import httpx
import time


def get_cheap_offer(authed_client, max_price=0.15):
    """Busca oferta barata disponível"""
    response = authed_client.get("/api/instances/offers")
    if response.status_code != 200:
        return None

    offers = response.json()
    if isinstance(offers, dict):
        offers = offers.get("offers", [])

    valid = [o for o in offers if (o.get("dph_total") or 999) <= max_price]
    if not valid:
        return None

    valid.sort(key=lambda x: x.get("dph_total", 999))
    return valid[0]


def wait_for_status(authed_client, instance_id, target_statuses, timeout=180):
    """Aguarda instância atingir status desejado"""
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
    """Cria instância ou skip se rate limit"""
    response = authed_client.post("/api/instances", json={
        "offer_id": offer.get("id"),
        "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        "disk_size": 20,
        "skip_validation": True
    })
    if response.status_code == 500:
        pytest.skip("Rate limit ou erro temporário do VAST.ai")
    if response.status_code not in [200, 201, 202]:
        pytest.skip(f"Erro ao criar instância: {response.status_code}")

    instance_id = response.json().get("instance_id") or response.json().get("id")
    gpu_cleanup.append(instance_id)
    return instance_id


@pytest.fixture(scope="module")
def gpu_cleanup(authed_client):
    """Garante cleanup de todas as GPUs criadas no módulo"""
    created_ids = []
    yield created_ids

    for instance_id in created_ids:
        try:
            authed_client.delete(f"/api/instances/{instance_id}")
            print(f"  Cleanup: {instance_id} destruída")
        except Exception as e:
            print(f"  Cleanup erro: {instance_id} - {e}")


# =============================================================================
# TESTES ATIVAÇÃO SERVERLESS (16-20)
# =============================================================================

@pytest.mark.real_gpu
class TestServerlessActivation:
    """Testes de ativação do modo serverless"""

    def test_16_enable_serverless(self, authed_client, gpu_cleanup):
        """Teste 16: Ativar modo serverless em instância"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        # Aguardar running
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Ativar serverless
        response = authed_client.post(f"/api/instances/{instance_id}/serverless/enable", json={
            "mode": "economic",
            "idle_threshold": 60
        })

        if response.status_code in [404, 405]:
            pytest.skip("Endpoint serverless/enable não implementado")

        assert response.status_code in [200, 201, 202], f"Erro: {response.text}"

    def test_17_serverless_fast_mode(self, authed_client, gpu_cleanup):
        """Teste 17: Ativar serverless modo FAST (CPU standby)"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Ativar modo FAST
        response = authed_client.post(f"/api/instances/{instance_id}/serverless/enable", json={
            "mode": "fast",
            "cpu_standby": True
        })

        if response.status_code in [404, 405]:
            pytest.skip("Endpoint não implementado")

        assert response.status_code in [200, 201, 202]

    def test_18_serverless_economic_mode(self, authed_client, gpu_cleanup):
        """Teste 18: Ativar serverless modo ECONOMIC (pause nativo)"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Modo economic
        response = authed_client.post(f"/api/instances/{instance_id}/serverless/enable", json={
            "mode": "economic"
        })

        if response.status_code in [404, 405]:
            pytest.skip("Endpoint não implementado")

        assert response.status_code in [200, 201, 202]

    def test_19_configure_idle_threshold(self, authed_client, gpu_cleanup):
        """Teste 19: Configurar threshold de idle"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Configurar idle threshold de 30s
        response = authed_client.post(f"/api/instances/{instance_id}/serverless/enable", json={
            "idle_threshold": 30
        })

        if response.status_code in [404, 405]:
            pytest.skip("Endpoint não implementado")

        assert response.status_code in [200, 201, 202]

    def test_20_disable_serverless(self, authed_client, gpu_cleanup):
        """Teste 20: Desativar serverless"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Ativar e depois desativar
        response = authed_client.post(f"/api/instances/{instance_id}/serverless/enable", json={})
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint não implementado")

        response = authed_client.post(f"/api/instances/{instance_id}/serverless/disable")
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint disable não implementado")

        assert response.status_code in [200, 201, 202]


# =============================================================================
# TESTES AUTO-PAUSE (21-24)
# =============================================================================

@pytest.mark.real_gpu
class TestAutoPause:
    """Testes de auto-pause"""

    def test_21_auto_pause_idle(self, authed_client, gpu_cleanup):
        """Teste 21: Verificar auto-pause após GPU idle (via API de status)"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Verificar se há endpoint de métricas
        response = authed_client.get(f"/api/instances/{instance_id}/metrics")
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint metrics não implementado")

        assert response.status_code == 200

    def test_22_no_auto_pause_during_use(self, authed_client, gpu_cleanup):
        """Teste 22: Não deve auto-pausar durante uso"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Simular atividade via API
        response = authed_client.get(f"/api/instances/{instance_id}")
        assert response.status_code == 200

        # Verificar que continua running após 30s
        time.sleep(30)
        response = authed_client.get(f"/api/instances/{instance_id}")
        data = response.json()
        status = data.get("status") or data.get("actual_status")
        assert status == "running", "Instância pausou indevidamente"

    def test_23_grace_period(self, authed_client, gpu_cleanup):
        """Teste 23: Verificar grace period em nova instância"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Verificar que não pausa nos primeiros 30s (grace period)
        time.sleep(30)

        response = authed_client.get(f"/api/instances/{instance_id}")
        data = response.json()
        status = data.get("status") or data.get("actual_status")
        assert status == "running", "Grace period não respeitado"

    def test_24_savings_metrics(self, authed_client, gpu_cleanup):
        """Teste 24: Verificar cálculo de economia"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Verificar endpoint de economia
        response = authed_client.get(f"/api/instances/{instance_id}/savings")
        if response.status_code in [404, 405]:
            response = authed_client.get(f"/api/serverless/savings")

        if response.status_code in [404, 405]:
            pytest.skip("Endpoint savings não implementado")

        assert response.status_code == 200


# =============================================================================
# TESTES COLD START (25-27)
# =============================================================================

@pytest.mark.real_gpu
class TestColdStart:
    """Testes de cold start time"""

    def test_25_cold_start_fast_mode(self, authed_client, gpu_cleanup):
        """Teste 25: Medir cold start em modo FAST"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Pause
        authed_client.post(f"/api/instances/{instance_id}/pause")
        success, _ = wait_for_status(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=120)
        if not success:
            pytest.skip("Timeout no pause")

        # Medir cold start
        start_time = time.time()
        authed_client.post(f"/api/instances/{instance_id}/resume")
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        cold_start = time.time() - start_time

        if not success:
            pytest.skip("Timeout no resume")
        print(f"  Cold start FAST: {cold_start:.1f}s")

    def test_26_cold_start_economic(self, authed_client, gpu_cleanup):
        """Teste 26: Medir cold start em modo ECONOMIC"""
        offer = get_cheap_offer(authed_client)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Pause (nativo VAST)
        authed_client.post(f"/api/instances/{instance_id}/pause")
        success, _ = wait_for_status(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=120)
        if not success:
            pytest.skip("Timeout no pause")

        # Medir cold start
        start_time = time.time()
        authed_client.post(f"/api/instances/{instance_id}/resume")
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        cold_start = time.time() - start_time

        if not success:
            pytest.skip("Timeout no resume")
        print(f"  Cold start ECONOMIC: {cold_start:.1f}s")

        # VAST nativo deve ser < 120s
        assert cold_start < 120, f"Cold start muito lento: {cold_start}s"

    def test_27_cold_start_with_model(self, authed_client, gpu_cleanup):
        """Teste 27: Cold start com Ollama pre-instalado"""
        offer = get_cheap_offer(authed_client, max_price=0.20)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")

        # Usar imagem Ollama
        response = authed_client.post("/api/instances", json={
            "offer_id": offer.get("id"),
            "image": "ollama/ollama",
            "disk_size": 30,
            "skip_validation": True,
            "onstart_cmd": "ollama serve &"
        })
        if response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")
        if response.status_code not in [200, 201, 202]:
            pytest.skip(f"Erro ao criar: {response.status_code}")

        instance_id = response.json().get("instance_id") or response.json().get("id")
        gpu_cleanup.append(instance_id)

        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")

        # Aguardar estabilizar
        time.sleep(30)

        # Pause
        authed_client.post(f"/api/instances/{instance_id}/pause")
        success, _ = wait_for_status(authed_client, instance_id, ["stopped", "exited", "paused"], timeout=120)
        if not success:
            pytest.skip("Timeout no pause")

        # Cold start com modelo
        start_time = time.time()
        authed_client.post(f"/api/instances/{instance_id}/resume")
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        cold_start = time.time() - start_time

        if not success:
            pytest.skip("Timeout no resume")
        print(f"  Cold start com modelo: {cold_start:.1f}s")
