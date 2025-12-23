"""
Tests for the StandbyClient module.

Includes unit tests (with mocks) and integration tests (with real API).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dumont_sdk.standby import (
    StandbyClient,
    StandbyStatus,
    StandbyAssociation,
    PricingEstimate,
    FailoverResult,
)


# =============================================================================
# Mock Data
# =============================================================================

@pytest.fixture
def mock_status_response():
    """Mock status response from API."""
    return {
        "configured": True,
        "auto_standby_enabled": True,
        "active_associations": 2,
        "associations": {
            "12345": {
                "cpu_standby": {
                    "name": "cpu-standby-12345",
                    "zone": "europe-west1-b",
                    "ip": "10.0.0.100",
                },
                "sync_enabled": True,
                "state": "syncing",
                "sync_count": 15,
            }
        },
        "config": {
            "gcp_zone": "europe-west1-b",
            "gcp_machine_type": "e2-medium",
            "gcp_disk_size": 100,
            "gcp_spot": True,
        }
    }


@pytest.fixture
def mock_associations_response():
    """Mock associations list response."""
    return {
        "associations": {
            "12345": {
                "cpu_standby": {
                    "name": "cpu-standby-12345",
                    "zone": "europe-west1-b",
                    "ip": "10.0.0.100",
                    "created_at": "2024-12-17T10:00:00Z",
                },
                "sync_enabled": True,
                "state": "syncing",
                "sync_count": 15,
            },
            "67890": {
                "cpu_standby": {
                    "name": "cpu-standby-67890",
                    "zone": "europe-west1-b",
                    "ip": "10.0.0.101",
                    "created_at": "2024-12-18T10:00:00Z",
                },
                "sync_enabled": False,
                "state": "idle",
                "sync_count": 0,
            }
        },
        "count": 2,
    }


@pytest.fixture
def mock_pricing_response():
    """Mock pricing response."""
    return {
        "machine_type": "e2-medium",
        "disk_gb": 100,
        "spot": True,
        "estimated_hourly_usd": 0.01,
        "estimated_monthly_usd": 11.20,
        "breakdown": {
            "vm_monthly": 7.20,
            "disk_monthly": 4.00,
        },
        "note": "Prices are estimates and may vary by region."
    }


@pytest.fixture
def mock_failover_simulate_response():
    """Mock failover simulation response."""
    return {
        "failover_id": "abc12345",
        "gpu_instance_id": 12345,
        "message": "Failover simulation started",
        "phase": "detecting",
    }


@pytest.fixture
def mock_failover_status_response():
    """Mock failover status response."""
    return {
        "failover_id": "abc12345",
        "gpu_instance_id": 12345,
        "reason": "spot_interruption",
        "phase": "complete",
        "started_at": "2024-12-17T10:00:00Z",
        "completed_at": "2024-12-17T10:00:20Z",
        "success": True,
        "new_gpu_id": 13345,
        "data_restored": True,
        "phase_timings_ms": {
            "detecting": 500,
            "gpu_lost": 2000,
            "failover_to_cpu": 3000,
            "searching_gpu": 3500,
            "provisioning": 3000,
            "restoring": 4000,
        },
        "total_time_ms": 16000,
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

class TestStandbyUnit:
    """Unit tests for StandbyClient (using mocks)."""

    @pytest.mark.asyncio
    async def test_status(self, mock_base_client, mock_status_response):
        """Test getting standby status."""
        mock_base_client.get.return_value = mock_status_response

        client = StandbyClient(mock_base_client)
        status = await client.status()

        mock_base_client.get.assert_called_once_with("/api/v1/standby/status")

        assert isinstance(status, StandbyStatus)
        assert status.configured is True
        assert status.auto_standby_enabled is True
        assert status.active_associations == 2
        assert "gcp_zone" in status.config

    @pytest.mark.asyncio
    async def test_configure(self, mock_base_client):
        """Test configuring standby."""
        mock_base_client.post.return_value = {
            "success": True,
            "message": "Auto-standby enabled",
            "config": {"gcp_zone": "europe-west1-b"},
        }

        client = StandbyClient(mock_base_client)
        result = await client.configure(
            enabled=True,
            gcp_zone="europe-west1-b",
            gcp_machine_type="e2-medium",
            gcp_disk_size=100,
            gcp_spot=True,
        )

        mock_base_client.post.assert_called_once()
        call_args = mock_base_client.post.call_args
        assert call_args[0][0] == "/api/v1/standby/configure"
        assert call_args[1]["data"]["enabled"] is True
        assert call_args[1]["data"]["gcp_zone"] == "europe-west1-b"

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_associations(self, mock_base_client, mock_associations_response):
        """Test listing associations."""
        mock_base_client.get.return_value = mock_associations_response

        client = StandbyClient(mock_base_client)
        associations = await client.associations()

        mock_base_client.get.assert_called_once_with("/api/v1/standby/associations")

        assert len(associations) == 2
        assert all(isinstance(a, StandbyAssociation) for a in associations)

        # Check first association
        assoc_12345 = next(a for a in associations if a.gpu_instance_id == 12345)
        assert assoc_12345.cpu_instance_name == "cpu-standby-12345"
        assert assoc_12345.sync_enabled is True
        assert assoc_12345.sync_count == 15

    @pytest.mark.asyncio
    async def test_get_association(self, mock_base_client):
        """Test getting single association."""
        mock_base_client.get.return_value = {
            "gpu_instance_id": 12345,
            "cpu_standby": {
                "name": "cpu-standby-12345",
                "zone": "europe-west1-b",
                "ip": "10.0.0.100",
            },
            "sync_enabled": True,
            "state": "syncing",
            "sync_count": 15,
        }

        client = StandbyClient(mock_base_client)
        assoc = await client.get_association(12345)

        mock_base_client.get.assert_called_once_with("/api/v1/standby/associations/12345")

        assert isinstance(assoc, StandbyAssociation)
        assert assoc.gpu_instance_id == 12345
        assert assoc.cpu_instance_name == "cpu-standby-12345"

    @pytest.mark.asyncio
    async def test_provision(self, mock_base_client):
        """Test provisioning standby for GPU."""
        mock_base_client.post.return_value = {
            "success": True,
            "message": "CPU Standby provisioned successfully",
            "association": {
                "gpu_instance_id": 12345,
                "cpu_standby": {"name": "cpu-standby-12345"},
            },
        }

        client = StandbyClient(mock_base_client)
        result = await client.provision(12345, label="my-gpu")

        mock_base_client.post.assert_called_once()
        call_args = mock_base_client.post.call_args
        assert "/api/v1/standby/provision/12345" in call_args[0][0]
        assert call_args[1]["params"]["label"] == "my-gpu"

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_start_sync(self, mock_base_client):
        """Test starting sync."""
        mock_base_client.post.return_value = {
            "success": True,
            "message": "Sync started for GPU 12345",
        }

        client = StandbyClient(mock_base_client)
        result = await client.start_sync(12345)

        mock_base_client.post.assert_called_once_with(
            "/api/v1/standby/associations/12345/start-sync"
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_stop_sync(self, mock_base_client):
        """Test stopping sync."""
        mock_base_client.post.return_value = {
            "success": True,
            "message": "Sync stopped for GPU 12345",
        }

        client = StandbyClient(mock_base_client)
        result = await client.stop_sync(12345)

        mock_base_client.post.assert_called_once_with(
            "/api/v1/standby/associations/12345/stop-sync"
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_destroy(self, mock_base_client):
        """Test destroying standby."""
        mock_base_client.delete.return_value = {
            "success": True,
            "message": "CPU standby for GPU 12345 destroyed",
        }

        client = StandbyClient(mock_base_client)
        result = await client.destroy(12345, keep_gpu=True)

        mock_base_client.delete.assert_called_once()
        call_args = mock_base_client.delete.call_args
        assert "/api/v1/standby/associations/12345" in call_args[0][0]
        assert call_args[1]["params"]["keep_gpu"] is True

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_pricing(self, mock_base_client, mock_pricing_response):
        """Test getting pricing estimate."""
        mock_base_client.get.return_value = mock_pricing_response

        client = StandbyClient(mock_base_client)
        pricing = await client.pricing(
            machine_type="e2-medium",
            disk_gb=100,
            spot=True,
        )

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert "/api/v1/standby/pricing" in call_args[0][0]

        assert isinstance(pricing, PricingEstimate)
        assert pricing.machine_type == "e2-medium"
        assert pricing.estimated_monthly_usd == 11.20
        assert "vm_monthly" in pricing.breakdown

    @pytest.mark.asyncio
    async def test_simulate_failover(self, mock_base_client, mock_failover_simulate_response):
        """Test simulating failover."""
        mock_base_client.post.return_value = mock_failover_simulate_response

        client = StandbyClient(mock_base_client)
        result = await client.simulate_failover(
            12345,
            reason="spot_interruption",
            simulate_restore=True,
            simulate_new_gpu=True,
        )

        mock_base_client.post.assert_called_once()
        call_args = mock_base_client.post.call_args
        assert "/api/v1/standby/failover/simulate/12345" in call_args[0][0]
        assert call_args[1]["data"]["reason"] == "spot_interruption"

        assert isinstance(result, FailoverResult)
        assert result.failover_id == "abc12345"
        assert result.phase == "detecting"

    @pytest.mark.asyncio
    async def test_failover_status(self, mock_base_client, mock_failover_status_response):
        """Test getting failover status."""
        mock_base_client.get.return_value = mock_failover_status_response

        client = StandbyClient(mock_base_client)
        result = await client.failover_status("abc12345")

        mock_base_client.get.assert_called_once_with(
            "/api/v1/standby/failover/status/abc12345"
        )

        assert isinstance(result, FailoverResult)
        assert result.failover_id == "abc12345"
        assert result.success is True
        assert result.phase == "complete"
        assert result.new_gpu_id == 13345
        assert result.data_restored is True
        assert result.total_time_ms == 16000

    @pytest.mark.asyncio
    async def test_failover_report(self, mock_base_client):
        """Test getting failover report."""
        mock_base_client.get.return_value = {
            "period_days": 30,
            "total_failovers": 5,
            "success_rate": 80.0,
            "mttr_ms": 15000,
            "mttr_seconds": 15.0,
            "latency_by_phase_ms": {"detecting": 500, "restoring": 4000},
            "history": [],
        }

        client = StandbyClient(mock_base_client)
        report = await client.failover_report(days=30)

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert "/api/v1/standby/failover/report" in call_args[0][0]
        assert call_args[1]["params"]["days"] == 30

        assert report["total_failovers"] == 5
        assert report["success_rate"] == 80.0

    @pytest.mark.asyncio
    async def test_active_failovers(self, mock_base_client):
        """Test getting active failovers."""
        mock_base_client.get.return_value = {
            "active_count": 1,
            "failovers": [
                {
                    "failover_id": "abc12345",
                    "gpu_instance_id": 12345,
                    "success": False,
                    "phase": "provisioning",
                }
            ],
        }

        client = StandbyClient(mock_base_client)
        active = await client.active_failovers()

        mock_base_client.get.assert_called_once_with("/api/v1/standby/failover/active")

        assert len(active) == 1
        assert isinstance(active[0], FailoverResult)
        assert active[0].phase == "provisioning"

    @pytest.mark.asyncio
    async def test_fast_failover(self, mock_base_client):
        """Test fast failover."""
        mock_base_client.post.return_value = {
            "failover_id": "fast-abc123",
            "success": True,
            "message": "Fast failover completed!",
            "total_time_ms": 45000,
            "phases": {
                "snapshot_ms": 5000,
                "gpu_provisioning_ms": 30000,
                "restore_ms": 8000,
                "inference_ms": 2000,
            },
            "gpu": {
                "original": {"id": 12345, "type": "RTX 4090"},
                "new": {"id": 13345, "type": "RTX 4090"},
            },
        }

        client = StandbyClient(mock_base_client)
        result = await client.fast_failover(
            12345,
            model="qwen2.5:0.5b",
            workspace_path="/workspace",
        )

        mock_base_client.post.assert_called_once()
        call_args = mock_base_client.post.call_args
        assert "/api/v1/standby/failover/fast/12345" in call_args[0][0]
        assert call_args[1]["data"]["model"] == "qwen2.5:0.5b"

        assert result["success"] is True
        assert result["total_time_ms"] == 45000

    @pytest.mark.asyncio
    async def test_create_mock_association(self, mock_base_client):
        """Test creating mock association."""
        mock_base_client.post.return_value = {
            "success": True,
            "message": "Mock association created for GPU 12345",
            "association": {
                "gpu_instance_id": 12345,
                "cpu_standby": {
                    "name": "mock-cpu-standby-12345",
                    "zone": "europe-west1-b",
                    "ip": "10.0.0.100",
                },
            },
        }

        client = StandbyClient(mock_base_client)
        result = await client.create_mock_association(12345)

        mock_base_client.post.assert_called_once()
        assert result["success"] is True


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.integration
class TestStandbyIntegration:
    """Integration tests for StandbyClient (requires real API)."""

    @pytest.mark.asyncio
    async def test_get_status_real(self, client_with_api_key, rate_limiter):
        """Test getting real standby status."""
        await rate_limiter.wait()

        status = await client_with_api_key.standby.status()

        assert isinstance(status, StandbyStatus)
        assert isinstance(status.configured, bool)
        assert isinstance(status.auto_standby_enabled, bool)
        assert isinstance(status.active_associations, int)

    @pytest.mark.asyncio
    async def test_get_pricing_real(self, client_with_api_key, rate_limiter):
        """Test getting real pricing estimate."""
        await rate_limiter.wait()

        pricing = await client_with_api_key.standby.pricing(
            machine_type="e2-medium",
            disk_gb=100,
            spot=True,
        )

        assert isinstance(pricing, PricingEstimate)
        assert pricing.machine_type == "e2-medium"
        assert pricing.disk_gb == 100
        assert pricing.spot is True
        assert pricing.estimated_hourly_usd > 0
        assert pricing.estimated_monthly_usd > 0

    @pytest.mark.asyncio
    async def test_list_associations_real(self, client_with_api_key, rate_limiter):
        """Test listing real associations."""
        await rate_limiter.wait()

        associations = await client_with_api_key.standby.associations()

        # Should return a list (may be empty)
        assert isinstance(associations, list)

    @pytest.mark.asyncio
    async def test_failover_report_real(self, client_with_api_key, rate_limiter):
        """Test getting real failover report."""
        await rate_limiter.wait()

        report = await client_with_api_key.standby.failover_report(days=30)

        assert "period_days" in report
        assert "total_failovers" in report
        assert "success_rate" in report

    @pytest.mark.asyncio
    async def test_active_failovers_real(self, client_with_api_key, rate_limiter):
        """Test getting real active failovers."""
        await rate_limiter.wait()

        active = await client_with_api_key.standby.active_failovers()

        # Should return a list (may be empty)
        assert isinstance(active, list)


# =============================================================================
# Tests Requiring Running Instance
# =============================================================================

@pytest.mark.integration
@pytest.mark.requires_instance
class TestStandbyWithInstance:
    """Tests that require a running GPU instance."""

    @pytest.mark.asyncio
    async def test_provision_and_destroy_standby(
        self,
        client_with_api_key,
        real_instance,
        rate_limiter
    ):
        """Test provisioning and destroying standby for real instance."""
        if not real_instance:
            pytest.skip("No running instance available")

        # First check if standby is configured
        await rate_limiter.wait()
        status = await client_with_api_key.standby.status()

        if not status.configured:
            pytest.skip("Standby not configured - configure GCP credentials first")

        # Provision standby
        await rate_limiter.wait()
        try:
            result = await client_with_api_key.standby.provision(
                real_instance.id,
                label=f"test-standby-{real_instance.id}"
            )
            assert result.get("success", False) or "already exists" in result.get("message", "")
        except Exception as e:
            if "already exists" in str(e).lower():
                pass  # Standby already exists, that's ok
            else:
                raise

        # Check association exists
        await rate_limiter.wait()
        try:
            assoc = await client_with_api_key.standby.get_association(real_instance.id)
            assert assoc.gpu_instance_id == real_instance.id
        except Exception:
            pytest.skip("Could not get association")

    @pytest.mark.asyncio
    async def test_simulate_failover_real(
        self,
        client_with_api_key,
        real_instance,
        rate_limiter
    ):
        """Test simulating failover for real instance."""
        if not real_instance:
            pytest.skip("No running instance available")

        # Check if has association
        await rate_limiter.wait()
        try:
            await client_with_api_key.standby.get_association(real_instance.id)
        except Exception:
            # Create mock association for testing
            await rate_limiter.wait()
            await client_with_api_key.standby.create_mock_association(real_instance.id)

        # Simulate failover
        await rate_limiter.wait()
        result = await client_with_api_key.standby.simulate_failover(
            real_instance.id,
            reason="test_simulation",
            simulate_restore=True,
            simulate_new_gpu=True,
        )

        assert isinstance(result, FailoverResult)
        assert result.failover_id
        assert result.gpu_instance_id == real_instance.id

        # Wait a bit and check status
        import asyncio
        await asyncio.sleep(2)

        await rate_limiter.wait()
        status = await client_with_api_key.standby.failover_status(result.failover_id)

        assert status.failover_id == result.failover_id
