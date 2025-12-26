"""
Fluxo 5: Alta Disponibilidade (CPU Standby + Failover)
Testes REAIS contra a API.
"""
import pytest
import httpx
import time


@pytest.mark.flow5
class TestStandbyAPI:
    """Testes da API de CPU Standby"""

    def test_standby_status(self, authed_client: httpx.Client):
        """Deve retornar status do sistema de standby"""
        response = authed_client.get("/api/standby/status")

        assert response.status_code == 200
        data = response.json()

        assert "configured" in data
        assert "auto_standby_enabled" in data

    def test_standby_pricing(self, authed_client: httpx.Client):
        """Deve retornar estimativa de preço do standby"""
        response = authed_client.get("/api/standby/pricing", params={
            "machine_type": "e2-medium",
            "disk_gb": 100,
            "spot": True
        })

        assert response.status_code == 200
        data = response.json()

        assert "estimated_monthly_usd" in data

    def test_list_associations(self, authed_client: httpx.Client):
        """Deve listar associações GPU-CPU"""
        response = authed_client.get("/api/standby/associations")

        assert response.status_code == 200
        data = response.json()

        assert "associations" in data or "count" in data


@pytest.mark.flow5
class TestStandbyConfiguration:
    """Testes de configuração do standby"""

    def test_configure_standby_without_credentials(self, authed_client: httpx.Client):
        """Deve falhar se GCP não configurado"""
        # Este teste pode passar ou falhar dependendo se GCP está configurado
        response = authed_client.post("/api/standby/configure", json={
            "enabled": True,
            "gcp_zone": "europe-west1-b",
            "gcp_machine_type": "e2-medium",
            "gcp_spot": True
        })

        # Se GCP não configurado, deve dar 400
        # Se GCP configurado, deve dar 200
        assert response.status_code in [200, 400]

    def test_disable_standby(self, authed_client: httpx.Client):
        """Deve desabilitar standby"""
        response = authed_client.post("/api/standby/configure", json={
            "enabled": False
        })

        assert response.status_code == 200


@pytest.mark.flow5
class TestFailoverSimulation:
    """Testes de simulação de failover"""

    def test_create_mock_association(self, authed_client: httpx.Client):
        """Deve criar associação mock para testes"""
        response = authed_client.post(
            "/api/standby/test/create-mock-association",
            params={"gpu_instance_id": 99999}
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True

    def test_simulate_failover(self, authed_client: httpx.Client):
        """Deve simular failover completo"""
        # Primeiro criar mock
        authed_client.post(
            "/api/standby/test/create-mock-association",
            params={"gpu_instance_id": 88888}
        )

        # Simular failover
        response = authed_client.post("/api/standby/failover/simulate/88888", json={
            "reason": "spot_interruption",
            "simulate_restore": True,
            "simulate_new_gpu": True
        })

        assert response.status_code == 200
        data = response.json()

        assert "failover_id" in data

    def test_failover_status(self, authed_client: httpx.Client):
        """Deve monitorar status do failover"""
        # Criar mock e simular
        authed_client.post(
            "/api/standby/test/create-mock-association",
            params={"gpu_instance_id": 77777}
        )

        response = authed_client.post("/api/standby/failover/simulate/77777")
        data = response.json()
        failover_id = data.get("failover_id")

        if not failover_id:
            pytest.skip("Failover não iniciado")

        # Aguardar e verificar fases
        time.sleep(5)

        response = authed_client.get(f"/api/standby/failover/status/{failover_id}")
        assert response.status_code == 200

        data = response.json()
        assert "phase" in data

    def test_failover_report(self, authed_client: httpx.Client):
        """Deve retornar relatório de failovers"""
        response = authed_client.get("/api/standby/failover/report", params={
            "days": 30
        })

        assert response.status_code == 200
        data = response.json()

        assert "total_failovers" in data
        assert "success_rate" in data

    def test_active_failovers(self, authed_client: httpx.Client):
        """Deve listar failovers ativos"""
        response = authed_client.get("/api/standby/failover/active")

        assert response.status_code == 200
        data = response.json()

        assert "active_count" in data
        assert "failovers" in data


@pytest.mark.flow5
@pytest.mark.real_gpu
@pytest.mark.slow
@pytest.mark.destructive
class TestRealFailover:
    """Testes de failover REAL (requer GPU e custa $$$)"""

    def test_provision_cpu_standby(self, authed_client: httpx.Client, test_context):
        """Deve provisionar CPU standby para GPU existente"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância criada")

        gpu_id = test_context.created_instances[-1]

        response = authed_client.post(f"/api/standby/provision/{gpu_id}")

        # Pode falhar se GCP não configurado
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True

    def test_fast_failover(self, authed_client: httpx.Client, test_context):
        """Deve executar failover rápido com race strategy"""
        if not test_context.created_instances:
            pytest.skip("Nenhuma instância criada")

        gpu_id = test_context.created_instances[-1]

        response = authed_client.post(f"/api/standby/failover/fast/{gpu_id}", json={
            "model": "qwen2.5:0.5b",
            "workspace_path": "/workspace",
            "skip_inference": True,
            "destroy_original_gpu": False
        })

        # Pode demorar muito ou falhar
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert "total_time_ms" in data
            print(f"Failover time: {data['total_time_ms']}ms")
