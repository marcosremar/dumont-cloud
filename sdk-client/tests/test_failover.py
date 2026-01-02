"""
Tests for the FailoverClient module.

Includes unit tests (with mocks) and integration tests (with real API).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from dumont_sdk.failover import (
    FailoverClient,
    FailoverExecutionResult,
    ReadinessStatus,
    StrategyInfo,
    RegionalVolume,
    RegionalFailoverResult,
    GPUOffer,
)


# =============================================================================
# Mock Data
# =============================================================================

@pytest.fixture
def mock_execute_response():
    """Mock failover execution response."""
    return {
        "success": True,
        "failover_id": "fo-abc123",
        "machine_id": 123,
        "strategy_attempted": "both",
        "strategy_succeeded": "warm_pool",
        "new_gpu_id": 13345,
        "new_ssh_host": "192.168.1.200",
        "new_ssh_port": 22,
        "new_gpu_name": "RTX 4090",
        "warm_pool_attempt_ms": 45000,
        "cpu_standby_attempt_ms": 0,
        "total_ms": 45000,
        "error": None,
        "warm_pool_error": None,
        "cpu_standby_error": None,
    }


@pytest.fixture
def mock_readiness_response():
    """Mock readiness check response."""
    return {
        "machine_id": 123,
        "effective_strategy": "both",
        "warm_pool_ready": True,
        "warm_pool_status": {
            "state": "active",
            "gpu_available": True,
        },
        "cpu_standby_ready": True,
        "cpu_standby_status": {
            "association_exists": True,
            "sync_enabled": True,
        },
        "overall_ready": True,
    }


@pytest.fixture
def mock_strategies_response():
    """Mock strategies list response."""
    return {
        "strategies": [
            {
                "id": "warm_pool",
                "name": "GPU Warm Pool",
                "description": "Fast failover using standby GPU",
                "recovery_time": "30-60 seconds",
                "cost": "Storage only when stopped",
                "requirements": ["Multi-GPU host", "Shared volume"],
            },
            {
                "id": "cpu_standby",
                "name": "CPU Standby + Snapshot",
                "description": "Failover via snapshot restore",
                "recovery_time": "10-20 minutes",
                "cost": "GCP VM + snapshot storage",
                "requirements": ["GCP credentials", "B2/S3 bucket"],
            },
        ]
    }


@pytest.fixture
def mock_regional_failover_response():
    """Mock regional failover response."""
    return {
        "success": True,
        "volume_id": 999,
        "old_instance_id": 12345,
        "new_instance_id": 13345,
        "new_gpu_name": "RTX 4090",
        "region": "US",
        "failover_time_seconds": 45.5,
        "message": "Failover completed successfully",
        "error": None,
        "ssh_host": "192.168.1.200",
        "ssh_port": 22,
    }


@pytest.fixture
def mock_base_client():
    """Mock base client for unit tests."""
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.delete = AsyncMock()
    return client


# =============================================================================
# Unit Tests
# =============================================================================

class TestFailoverUnit:
    """Unit tests for FailoverClient (using mocks)."""

    @pytest.mark.asyncio
    async def test_execute_failover(self, mock_base_client, mock_execute_response):
        """Test executing failover."""
        mock_base_client.post.return_value = mock_execute_response

        client = FailoverClient(mock_base_client)
        result = await client.execute(
            machine_id=123,
            gpu_instance_id=12345,
            ssh_host="192.168.1.100",
            ssh_port=22,
            workspace_path="/workspace",
        )

        mock_base_client.post.assert_called_once()
        call_args = mock_base_client.post.call_args
        assert call_args[0][0] == "/api/v1/failover/execute"
        assert call_args[1]["data"]["machine_id"] == 123
        assert call_args[1]["data"]["gpu_instance_id"] == 12345

        assert isinstance(result, FailoverExecutionResult)
        assert result.success is True
        assert result.failover_id == "fo-abc123"
        assert result.strategy_succeeded == "warm_pool"
        assert result.new_gpu_id == 13345
        assert result.total_ms == 45000

    @pytest.mark.asyncio
    async def test_execute_failover_with_force_strategy(self, mock_base_client, mock_execute_response):
        """Test executing failover with forced strategy."""
        mock_base_client.post.return_value = mock_execute_response

        client = FailoverClient(mock_base_client)
        await client.execute(
            machine_id=123,
            gpu_instance_id=12345,
            ssh_host="192.168.1.100",
            ssh_port=22,
            force_strategy="warm_pool",
        )

        call_args = mock_base_client.post.call_args
        assert call_args[1]["data"]["force_strategy"] == "warm_pool"

    @pytest.mark.asyncio
    async def test_readiness(self, mock_base_client, mock_readiness_response):
        """Test checking readiness."""
        mock_base_client.get.return_value = mock_readiness_response

        client = FailoverClient(mock_base_client)
        result = await client.readiness(123)

        mock_base_client.get.assert_called_once_with("/api/v1/failover/readiness/123")

        assert isinstance(result, ReadinessStatus)
        assert result.machine_id == 123
        assert result.effective_strategy == "both"
        assert result.warm_pool_ready is True
        assert result.cpu_standby_ready is True
        assert result.overall_ready is True

    @pytest.mark.asyncio
    async def test_status(self, mock_base_client):
        """Test getting status."""
        mock_base_client.get.return_value = {
            "machine_id": 123,
            "effective_strategy": "both",
            "warm_pool": {"enabled": True},
            "cpu_standby": {"enabled": True},
            "recommended_action": None,
        }

        client = FailoverClient(mock_base_client)
        result = await client.status(123)

        mock_base_client.get.assert_called_once_with("/api/v1/failover/status/123")
        assert result["machine_id"] == 123
        assert result["effective_strategy"] == "both"

    @pytest.mark.asyncio
    async def test_test_failover_dry_run(self, mock_base_client):
        """Test failover test (dry run)."""
        mock_base_client.post.return_value = {
            "dry_run": True,
            "would_succeed": True,
            "readiness": {"overall_ready": True},
            "message": "Use dry_run=False to execute",
        }

        client = FailoverClient(mock_base_client)
        result = await client.test(
            machine_id=123,
            gpu_instance_id=12345,
            ssh_host="192.168.1.100",
            ssh_port=22,
            dry_run=True,
        )

        mock_base_client.post.assert_called_once()
        call_args = mock_base_client.post.call_args
        assert call_args[1]["params"]["dry_run"] is True

        assert result["dry_run"] is True
        assert result["would_succeed"] is True

    @pytest.mark.asyncio
    async def test_strategies(self, mock_base_client, mock_strategies_response):
        """Test listing strategies."""
        mock_base_client.get.return_value = mock_strategies_response

        client = FailoverClient(mock_base_client)
        strategies = await client.strategies()

        mock_base_client.get.assert_called_once_with("/api/v1/failover/strategies")

        assert len(strategies) == 2
        assert all(isinstance(s, StrategyInfo) for s in strategies)

        warm_pool = next(s for s in strategies if s.id == "warm_pool")
        assert warm_pool.name == "GPU Warm Pool"
        assert warm_pool.recovery_time == "30-60 seconds"

    @pytest.mark.asyncio
    async def test_create_regional_volume(self, mock_base_client):
        """Test creating regional volume."""
        mock_base_client.post.return_value = {
            "success": True,
            "volume_id": 999,
            "region": "US",
            "size_gb": 50,
        }

        client = FailoverClient(mock_base_client)
        result = await client.create_regional_volume(
            region="US",
            size_gb=50,
            name="my-volume",
        )

        mock_base_client.post.assert_called_once()
        call_args = mock_base_client.post.call_args
        assert "/api/v1/failover/regional-volume/create" in call_args[0][0]
        assert call_args[1]["data"]["region"] == "US"
        assert call_args[1]["data"]["size_gb"] == 50

        assert isinstance(result, RegionalVolume)
        assert result.volume_id == 999
        assert result.region == "US"

    @pytest.mark.asyncio
    async def test_regional_failover(self, mock_base_client, mock_regional_failover_response):
        """Test regional failover."""
        mock_base_client.post.return_value = mock_regional_failover_response

        client = FailoverClient(mock_base_client)
        result = await client.regional_failover(
            volume_id=999,
            region="US",
            old_instance_id=12345,
            preferred_gpus=["RTX_4090", "RTX_3090"],
            max_price=1.0,
        )

        mock_base_client.post.assert_called_once()
        call_args = mock_base_client.post.call_args
        assert "/api/v1/failover/regional-volume/failover" in call_args[0][0]
        assert call_args[1]["data"]["volume_id"] == 999
        assert call_args[1]["data"]["preferred_gpus"] == ["RTX_4090", "RTX_3090"]

        assert isinstance(result, RegionalFailoverResult)
        assert result.success is True
        assert result.new_instance_id == 13345
        assert result.failover_time_seconds == 45.5

    @pytest.mark.asyncio
    async def test_list_regional_volumes(self, mock_base_client):
        """Test listing regional volumes."""
        mock_base_client.get.return_value = {
            "volumes": [
                {"id": 999, "region": "US", "size_gb": 50},
                {"id": 1000, "region": "DE", "size_gb": 100},
            ],
            "count": 2,
        }

        client = FailoverClient(mock_base_client)
        volumes = await client.list_regional_volumes()

        mock_base_client.get.assert_called_once_with("/api/v1/failover/regional-volume/list")
        assert len(volumes) == 2

    @pytest.mark.asyncio
    async def test_get_regional_volume(self, mock_base_client):
        """Test getting regional volume."""
        mock_base_client.get.return_value = {
            "id": 999,
            "region": "US",
            "size_gb": 50,
            "status": "available",
        }

        client = FailoverClient(mock_base_client)
        volume = await client.get_regional_volume(999)

        mock_base_client.get.assert_called_once_with("/api/v1/failover/regional-volume/999")
        assert volume["id"] == 999
        assert volume["status"] == "available"

    @pytest.mark.asyncio
    async def test_delete_regional_volume(self, mock_base_client):
        """Test deleting regional volume."""
        mock_base_client.delete.return_value = {
            "success": True,
            "message": "Volume 999 deleted",
        }

        client = FailoverClient(mock_base_client)
        result = await client.delete_regional_volume(999)

        mock_base_client.delete.assert_called_once_with("/api/v1/failover/regional-volume/999")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_search_gpus_in_region_found(self, mock_base_client):
        """Test searching GPUs in region (found)."""
        mock_base_client.get.return_value = {
            "found": True,
            "offer": {
                "offer_id": 12345,
                "gpu_name": "RTX 4090",
                "num_gpus": 1,
                "price_per_hour": 0.45,
                "reliability": 0.98,
                "geolocation": "US",
            },
        }

        client = FailoverClient(mock_base_client)
        result = await client.search_gpus_in_region(
            region="US",
            max_price=1.0,
            gpu_name="RTX_4090",
        )

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert "/api/v1/failover/regional-volume/search/US" in call_args[0][0]
        assert call_args[1]["params"]["max_price"] == 1.0
        assert call_args[1]["params"]["gpu_name"] == "RTX_4090"

        assert isinstance(result, GPUOffer)
        assert result.gpu_name == "RTX 4090"
        assert result.price_per_hour == 0.45

    @pytest.mark.asyncio
    async def test_search_gpus_in_region_not_found(self, mock_base_client):
        """Test searching GPUs in region (not found)."""
        mock_base_client.get.return_value = {
            "found": False,
            "message": "No GPU available in region US",
        }

        client = FailoverClient(mock_base_client)
        result = await client.search_gpus_in_region(region="US")

        assert result is None


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.integration
class TestFailoverIntegration:
    """Integration tests for FailoverClient (requires real API)."""

    @pytest.mark.asyncio
    async def test_list_strategies_real(self, client_with_api_key, rate_limiter):
        """Test listing strategies from real API."""
        await rate_limiter.wait()

        strategies = await client_with_api_key.failover.strategies()

        assert isinstance(strategies, list)
        assert len(strategies) > 0

        # Should have at least warm_pool and cpu_standby
        strategy_ids = [s.id for s in strategies]
        assert "warm_pool" in strategy_ids or "cpu_standby" in strategy_ids

    @pytest.mark.asyncio
    async def test_list_regional_volumes_real(self, client_with_api_key, rate_limiter):
        """Test listing regional volumes from real API."""
        await rate_limiter.wait()

        volumes = await client_with_api_key.failover.list_regional_volumes()

        # Should return a list (may be empty)
        assert isinstance(volumes, list)


# =============================================================================
# Tests Requiring Running Instance
# =============================================================================

@pytest.mark.integration
@pytest.mark.requires_instance
class TestFailoverWithInstance:
    """Tests that require a running GPU instance."""

    @pytest.mark.asyncio
    async def test_check_readiness_real(
        self,
        client_with_api_key,
        real_instance,
        rate_limiter
    ):
        """Test checking readiness for real instance."""
        if not real_instance:
            pytest.skip("No running instance available")

        await rate_limiter.wait()

        # Use instance ID as machine_id (they may be the same)
        readiness = await client_with_api_key.failover.readiness(real_instance.id)

        assert isinstance(readiness, ReadinessStatus)
        assert readiness.machine_id == real_instance.id
        assert isinstance(readiness.overall_ready, bool)

    @pytest.mark.asyncio
    async def test_failover_status_real(
        self,
        client_with_api_key,
        real_instance,
        rate_limiter
    ):
        """Test getting failover status for real instance."""
        if not real_instance:
            pytest.skip("No running instance available")

        await rate_limiter.wait()

        status = await client_with_api_key.failover.status(real_instance.id)

        assert "machine_id" in status
        assert "effective_strategy" in status

    @pytest.mark.asyncio
    async def test_dry_run_failover(
        self,
        client_with_api_key,
        real_instance,
        rate_limiter
    ):
        """Test dry run failover for real instance."""
        if not real_instance:
            pytest.skip("No running instance available")

        await rate_limiter.wait()

        result = await client_with_api_key.failover.test(
            machine_id=real_instance.id,
            gpu_instance_id=real_instance.id,
            ssh_host=real_instance.public_ip or "127.0.0.1",
            ssh_port=real_instance.ssh_port or 22,
            dry_run=True,
        )

        assert result.get("dry_run") is True
        assert "would_succeed" in result

    @pytest.mark.asyncio
    async def test_search_gpus_in_region_real(
        self,
        client_with_api_key,
        rate_limiter
    ):
        """Test searching GPUs in region."""
        await rate_limiter.wait()

        # Search for GPUs in US region
        result = await client_with_api_key.failover.search_gpus_in_region(
            region="US",
            max_price=2.0,
        )

        # May or may not find GPUs
        if result is not None:
            assert isinstance(result, GPUOffer)
            assert result.gpu_name
            assert result.price_per_hour <= 2.0
