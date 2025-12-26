"""
Fluxo 3: Desenvolvimento Interativo + Serverless
Testes REAIS contra a API.
"""
import pytest
import httpx
import time
import socket


@pytest.mark.flow3
class TestInstancesAPI:
    """Testes da API de instâncias"""

    def test_list_instances(self, authed_client):
        """Deve listar instâncias do usuário"""
        response = authed_client.get("/api/instances")

        # Se API externa indisponível após retries, pular
        if response.status_code == 503:
            pytest.skip("API Vast.ai indisponível (503 após retries)")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_list_offers(self, authed_client):
        """Deve listar ofertas de GPU"""
        response = authed_client.get("/api/instances/offers")

        # Se API externa indisponível após retries, pular
        if response.status_code == 503:
            pytest.skip("API Vast.ai indisponível (503 após retries)")

        assert response.status_code == 200
        data = response.json()

        # Deve ter ofertas disponíveis
        offers = data.get("offers", data) if isinstance(data, dict) else data
        assert len(offers) > 0, "Nenhuma oferta de GPU disponível"


@pytest.mark.flow3
@pytest.mark.real_gpu
@pytest.mark.slow
class TestInstanceCreation:
    """Testes de criação de instância (requer GPU real)"""

    def test_create_instance(self, authed_client: httpx.Client, test_context):
        """Deve criar uma instância GPU"""
        # Primeiro, obter uma oferta disponível (sem filtro para mais opções)
        offers_response = authed_client.get("/api/instances/offers")

        # Se API externa indisponível após retries, pular
        if offers_response.status_code == 503:
            pytest.skip("API Vast.ai indisponível (503 após retries)")

        if offers_response.status_code != 200:
            pytest.skip(f"Não foi possível obter ofertas: {offers_response.status_code}")

        offers_data = offers_response.json()
        offers = offers_data.get("offers", offers_data) if isinstance(offers_data, dict) else offers_data

        if not offers:
            pytest.skip("Nenhuma oferta de GPU disponível")

        # Filtrar ofertas com preço moderado (mais estáveis que as mais baratas)
        # Ofertas muito baratas são muito disputadas e ficam indisponíveis rapidamente
        moderate_offers = [
            o for o in offers
            if 0.10 <= (o.get("dph_total") or o.get("price") or 999) <= 0.50
        ]
        # Se não houver ofertas moderadas, usar as mais baratas
        if not moderate_offers:
            moderate_offers = [o for o in offers if (o.get("dph_total") or o.get("price") or 999) <= 0.50]

        # Ordenar por preço e pegar as 20 primeiras (mais opções = menos chance de falha)
        cheap_offers = sorted(moderate_offers, key=lambda x: x.get("dph_total", 999))[:20]

        if not cheap_offers:
            pytest.skip("Nenhuma oferta com preço <= $0.50/hr")

        # Tentar múltiplas ofertas até uma funcionar
        last_error = None
        attempts = 0
        max_attempts = len(cheap_offers)

        # Script SSH como o Wizard usa (instala openssh-server rapidamente)
        ssh_install_script = """apt-get update && apt-get install -y --no-install-recommends openssh-server && mkdir -p /var/run/sshd /root/.ssh && echo "PermitRootLogin yes" >> /etc/ssh/sshd_config && /usr/sbin/sshd"""

        for offer in cheap_offers:
            offer_id = offer.get("id") or offer.get("offer_id")
            gpu_name = offer.get("gpu_name", "unknown")
            price = offer.get("dph_total", 0)
            print(f"Tentando oferta {offer_id} ({gpu_name}) @ ${price:.3f}/hr...")

            response = authed_client.post("/api/instances", json={
                "offer_id": offer_id,
                # Usar ollama/ollama como o Wizard (leve e aceita SSH install)
                "image": "ollama/ollama",
                "disk_size": 20,
                "skip_validation": True,
                "onstart_cmd": ssh_install_script  # Instala SSH como Wizard
            })

            # Se endpoint não permite, pular
            if response.status_code in [404, 405]:
                pytest.skip("Endpoint POST /api/instances não implementado")

            if response.status_code in [200, 201, 202]:
                break  # Sucesso!

            last_error = response.text
            attempts += 1
            print(f"  Oferta {offer_id} falhou: {response.status_code} ({attempts}/{max_attempts})")

            # Pequeno delay entre tentativas para evitar rate limiting
            time.sleep(1)

        assert response.status_code in [200, 201, 202], f"Todas as ofertas falharam. Último erro: {last_error}"
        data = response.json()

        assert "instance_id" in data or "id" in data
        instance_id = data.get("instance_id") or data.get("id")
        test_context.created_instances.append(instance_id)

    def test_instance_becomes_running(self, authed_client: httpx.Client, test_context):
        """Instância deve ficar running"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância criada")

        instance_id = test_context.created_instances[-1]

        # Aguardar até 3 minutos
        start = time.time()
        while time.time() - start < 180:
            response = authed_client.get(f"/api/instances/{instance_id}")
            assert response.status_code == 200

            data = response.json()
            status = data.get("status") or data.get("actual_status")

            if status == "running":
                return  # Sucesso

            if status in ["failed", "error", "terminated"]:
                pytest.fail(f"Instância falhou: {status}")

            time.sleep(10)

        pytest.fail("Instância não ficou running em 3 minutos")

    def test_ssh_available(self, authed_client: httpx.Client, test_context):
        """SSH deve estar disponível (com retry como Wizard)"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância criada")

        instance_id = test_context.created_instances[-1]
        response = authed_client.get(f"/api/instances/{instance_id}")
        data = response.json()

        ssh_host = data.get("ssh_host")
        ssh_port = data.get("ssh_port")

        if not ssh_host or not ssh_port:
            pytest.skip("SSH info não disponível")

        # Retry com timeout estendido (SSH install pode demorar 60-90s)
        # apt-get update + install + sshd start pode demorar
        max_attempts = 60  # 60 tentativas * 2s = 120s
        for attempt in range(max_attempts):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # 3s timeout per attempt
            result = sock.connect_ex((ssh_host, int(ssh_port)))
            sock.close()

            if result == 0:
                return  # SSH disponível

            if attempt < max_attempts - 1:
                time.sleep(2)

        pytest.fail(f"SSH não acessível em {ssh_host}:{ssh_port} após 120s")


@pytest.mark.flow3
class TestServerlessAPI:
    """Testes da API serverless (sem GPU real)"""

    def test_serverless_status(self, authed_client: httpx.Client):
        """Deve retornar status do serverless"""
        response = authed_client.get("/api/serverless/status")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_serverless_config(self, authed_client: httpx.Client):
        """Deve retornar configuração serverless"""
        response = authed_client.get("/api/serverless/config")

        # Pode ser 200 ou 404
        assert response.status_code in [200, 404]


@pytest.mark.flow3
@pytest.mark.real_gpu
@pytest.mark.slow
class TestServerlessPauseResume:
    """Testes de pause/resume serverless"""

    def test_pause_instance(self, authed_client: httpx.Client, test_context):
        """Deve pausar instância"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância criada")

        instance_id = test_context.created_instances[-1]
        response = authed_client.post(f"/api/instances/{instance_id}/pause")

        assert response.status_code in [200, 202]

    def test_instance_paused(self, authed_client: httpx.Client, test_context):
        """Instância deve estar pausada (com retry como Wizard)"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância criada")

        instance_id = test_context.created_instances[-1]

        # Aguardar pause com retry - VAST.ai pode demorar até 2+ min para pausar
        timeout = 120
        check_interval = 5
        start = time.time()

        last_data = None
        while time.time() - start < timeout:
            response = authed_client.get(f"/api/instances/{instance_id}")
            if response.status_code != 200:
                time.sleep(check_interval)
                continue

            data = response.json()
            last_data = data
            status = data.get("status") or data.get("actual_status")
            actual = data.get("actual_status")

            # VAST.ai usa intended_status="stopped" quando pausado via state: stopped
            # actual_status pode ser "exited" ou similar quando realmente parado
            if status in ["stopped", "paused", "exited", "offline"]:
                return  # Sucesso

            # Também verificar actual_status separadamente
            if actual in ["stopped", "paused", "exited", "offline"]:
                return  # Sucesso

            time.sleep(check_interval)

        pytest.fail(f"Instância não pausou em {timeout}s (último status: status={status}, data={last_data})")

    def test_resume_instance(self, authed_client: httpx.Client, test_context):
        """Deve resumir instância pausada"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância criada")

        instance_id = test_context.created_instances[-1]
        response = authed_client.post(f"/api/instances/{instance_id}/resume")

        assert response.status_code in [200, 202]

    def test_instance_running_after_resume(self, authed_client: httpx.Client, test_context):
        """Instância deve voltar a running após resume (timeout maior como Wizard)"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância criada")

        instance_id = test_context.created_instances[-1]

        # Aguardar resume - VAST.ai pode demorar até 3 minutos para resumir
        # CHECK_INTERVAL similar ao Wizard (5s para ser responsivo)
        start = time.time()
        timeout = 180  # 3 minutos
        check_interval = 5  # 5s entre checks

        while time.time() - start < timeout:
            response = authed_client.get(f"/api/instances/{instance_id}")
            data = response.json()
            status = data.get("status") or data.get("actual_status")

            if status == "running":
                return  # Sucesso

            # Se ainda pausado/loading, continuar aguardando
            if status in ["paused", "stopped", "loading", "starting", "exited"]:
                time.sleep(check_interval)
                continue

            # Status inesperado - falhar
            if status in ["failed", "error", "terminated"]:
                pytest.fail(f"Resume falhou: status={status}")

            time.sleep(check_interval)

        pytest.fail(f"Instância não voltou a running após {timeout}s (último status: {status})")

    def test_destroy_instance(self, authed_client: httpx.Client, test_context):
        """Deve destruir instância"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância criada")

        instance_id = test_context.created_instances[-1]
        response = authed_client.delete(f"/api/instances/{instance_id}")

        assert response.status_code in [200, 202, 204]

        # Remover do contexto (já destruída)
        test_context.created_instances.remove(instance_id)
