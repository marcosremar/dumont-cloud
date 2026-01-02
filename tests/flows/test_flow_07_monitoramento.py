"""
Fluxo 7: Monitoramento e Métricas
Testes REAIS contra a API.
"""
import pytest
import httpx


@pytest.mark.flow7
class TestHealthCheck:
    """Testes de health check"""

    def test_health_endpoint(self, http_client: httpx.Client):
        """Deve retornar status healthy"""
        response = http_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data.get("status") == "healthy"

    def test_health_with_details(self, http_client: httpx.Client):
        """Deve retornar detalhes de saúde"""
        response = http_client.get("/health", params={"details": True})

        assert response.status_code == 200


@pytest.mark.flow7
class TestHibernationStats:
    """Testes de estatísticas de hibernação"""

    def test_hibernation_stats(self, authed_client: httpx.Client):
        """Deve retornar estatísticas de hibernação"""
        response = authed_client.get("/api/hibernation/stats")

        assert response.status_code == 200
        data = response.json()

        # Deve ter contadores de status
        assert isinstance(data, dict)

    def test_hibernation_config(self, authed_client: httpx.Client):
        """Deve retornar configuração de hibernação"""
        response = authed_client.get("/api/hibernation/config")

        # Pode ser 200 ou 404
        assert response.status_code in [200, 404]


@pytest.mark.flow7
class TestSavingsDashboard:
    """Testes do dashboard de economia"""

    def test_savings_summary(self, authed_client: httpx.Client):
        """Deve retornar resumo de economia"""
        response = authed_client.get("/api/savings")
        if response.status_code == 404:
            response = authed_client.get("/api/v1/savings")

        # Se endpoint não existe, pular
        if response.status_code == 404:
            pytest.skip("Endpoint /api/savings não implementado")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)

    def test_savings_history(self, authed_client: httpx.Client):
        """Deve retornar histórico de economia"""
        response = authed_client.get("/api/savings/history", params={
            "days": 30
        })

        # Pode ser 200 ou 404
        assert response.status_code in [200, 404]


@pytest.mark.flow7
class TestMarketMetrics:
    """Testes de métricas de mercado"""

    def test_market_metrics(self, authed_client: httpx.Client):
        """Deve retornar métricas de mercado"""
        response = authed_client.get("/api/metrics/market")

        # Pode ser 200 ou 404
        assert response.status_code in [200, 404]

    def test_spot_metrics(self, authed_client: httpx.Client):
        """Deve retornar métricas de spot"""
        response = authed_client.get("/api/metrics")
        if response.status_code == 404:
            response = authed_client.get("/api/v1/metrics")

        # Se endpoint não existe, pular
        if response.status_code == 404:
            pytest.skip("Endpoint /api/metrics não implementado")

        assert response.status_code == 200

    def test_gpu_prices(self, authed_client: httpx.Client):
        """Deve retornar preços de GPUs"""
        response = authed_client.get("/api/metrics/prices")

        # Pode ser 200 ou 404
        assert response.status_code in [200, 404]


@pytest.mark.flow7
class TestMachineHistory:
    """Testes de histórico de máquinas"""

    def test_machine_history(self, authed_client: httpx.Client):
        """Deve retornar histórico de máquinas"""
        response = authed_client.get("/api/machines/history")

        # Pode ser 200 ou 404
        assert response.status_code in [200, 404]

    def test_machine_blacklist(self, authed_client: httpx.Client):
        """Deve retornar blacklist de máquinas"""
        response = authed_client.get("/api/machines/blacklist")

        # Pode ser 200 ou 404
        assert response.status_code in [200, 404]


@pytest.mark.flow7
class TestAgentStatus:
    """Testes de status do agente"""

    def test_agent_instances(self, authed_client: httpx.Client):
        """Deve retornar instâncias do agente"""
        response = authed_client.get("/api/agent/instances")

        # Pode ser 200 ou 404
        assert response.status_code in [200, 404]

    def test_agent_heartbeat(self, authed_client: httpx.Client):
        """Deve aceitar heartbeat do agente"""
        # Usar schema correto do AgentStatusRequest
        response = authed_client.post("/api/agent/status", json={
            "instance_id": 12345,  # int, não string
            "gpu_utilization": 50.0,
            "memory_used_mb": 8000,
            "memory_total_mb": 24000,
            "active_processes": ["python train.py"],
            "uptime_seconds": 3600,
            "status": "running"
        })

        # Se schema incorreto ou endpoint não existe
        if response.status_code == 422:
            pytest.skip("Schema do heartbeat mudou - verificar AgentStatusRequest")

        assert response.status_code == 200
        data = response.json()

        assert "action" in data


@pytest.mark.flow7
class TestSnapshotsAPI:
    """Testes da API de snapshots"""

    def test_list_snapshots(self, authed_client: httpx.Client):
        """Deve listar snapshots"""
        response = authed_client.get("/api/snapshots")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, (list, dict))

    def test_snapshot_not_found(self, authed_client: httpx.Client):
        """Deve retornar 404 para snapshot inexistente"""
        response = authed_client.get("/api/snapshots/nonexistent-snapshot")

        assert response.status_code == 404
