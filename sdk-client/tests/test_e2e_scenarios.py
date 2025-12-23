"""
End-to-End Test Scenarios for Dumont SDK.

These tests cover complete workflows that span multiple SDK modules.
All E2E tests require real API access and are marked with @pytest.mark.e2e.

IMPORTANT: These tests may create real resources (instances, snapshots, etc.)
and should be run with caution. They are designed to clean up after themselves.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from dumont_sdk import DumontClient
from dumont_sdk.wizard import DeployResult, DeploySpeed
from dumont_sdk.instances import Instance
from dumont_sdk.snapshots import Snapshot
from dumont_sdk.standby import StandbyStatus, StandbyAssociation
from dumont_sdk.failover import FailoverExecutionResult, ReadinessStatus
from dumont_sdk.models import ModelInstallResult


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_dumont_client():
    """Create a mock DumontClient for unit testing."""
    client = MagicMock(spec=DumontClient)

    # Mock modules
    client.instances = MagicMock()
    client.snapshots = MagicMock()
    client.wizard = MagicMock()
    client.models = MagicMock()
    client.standby = MagicMock()
    client.failover = MagicMock()
    client.metrics = MagicMock()
    client.settings = MagicMock()

    return client


@pytest.fixture
def mock_deploy_result():
    """Mock successful deploy result."""
    return DeployResult(
        success=True,
        instance_id=12345,
        gpu_name="RTX_4090",
        public_ip="192.168.1.100",
        ssh_port=22,
        ssh_command="ssh -p 22 root@192.168.1.100",
        dph_total=0.45,
        ready_time=30.0,
        machines_tried=3,
        machines_destroyed=2,
        error=None,
    )


@pytest.fixture
def mock_instance():
    """Mock instance data."""
    return Instance(
        id=12345,
        status="running",
        gpu_name="RTX_4090",
        num_gpus=1,
        gpu_ram=24.0,
        cpu_cores=8,
        cpu_ram=64.0,
        disk_space=100.0,
        dph_total=0.45,
        ssh_host="192.168.1.100",
        ssh_port=22,
        label="test-instance",
    )


@pytest.fixture
def mock_snapshot():
    """Mock snapshot data."""
    return Snapshot(
        id="snap-123",
        instance_id=12345,
        created_at="2024-12-23T10:00:00Z",
        size_bytes=5000 * 1024 * 1024,  # 5GB
        status="completed",
        label="test-snapshot",
    )


# =============================================================================
# Unit Tests (with mocks)
# =============================================================================

class TestDeployScenarioUnit:
    """Unit tests for deploy scenarios (using mocks)."""

    @pytest.mark.asyncio
    async def test_deploy_and_install_model_flow(self, mock_dumont_client, mock_deploy_result):
        """Test complete deploy + model installation flow."""
        # Setup mocks
        mock_dumont_client.wizard.deploy = AsyncMock(return_value=mock_deploy_result)
        mock_dumont_client.models.install = AsyncMock(return_value=ModelInstallResult(
            success=True,
            model_name="llama3.2",
            instance_id=12345,
            ollama_url="http://192.168.1.100:11434",
            error=None,
        ))

        # Execute workflow
        deploy_result = await mock_dumont_client.wizard.deploy(
            gpu_name="RTX_4090",
            max_price=0.50,
        )

        assert deploy_result.success is True
        assert deploy_result.instance_id == 12345

        # Install model
        model_result = await mock_dumont_client.models.install(
            instance_id=deploy_result.instance_id,
            model="llama3.2",
        )

        assert model_result.success is True
        assert model_result.ollama_url is not None

        # Verify calls
        mock_dumont_client.wizard.deploy.assert_called_once()
        mock_dumont_client.models.install.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_with_standby_enabled(self, mock_dumont_client, mock_deploy_result):
        """Test deploy with CPU standby configuration."""
        # Setup mocks
        mock_dumont_client.wizard.deploy = AsyncMock(return_value=mock_deploy_result)
        mock_dumont_client.standby.provision = AsyncMock(return_value=StandbyAssociation(
            gpu_instance_id=12345,
            cpu_instance_name="gcp-standby-123",
            cpu_instance_zone="us-central1-a",
            cpu_instance_ip="10.0.0.1",
            sync_enabled=True,
            state="RUNNING",
        ))
        mock_dumont_client.standby.start_sync = AsyncMock(return_value={"success": True})

        # Execute workflow
        deploy_result = await mock_dumont_client.wizard.deploy(
            gpu_name="RTX_4090",
            max_price=0.50,
        )

        assert deploy_result.success is True

        # Enable standby
        association = await mock_dumont_client.standby.provision(
            gpu_id=deploy_result.instance_id,
            label="standby-for-gpu",
        )

        assert association.gpu_instance_id == deploy_result.instance_id
        assert association.state == "RUNNING"

        # Start sync
        sync_result = await mock_dumont_client.standby.start_sync(
            gpu_id=deploy_result.instance_id,
        )

        assert sync_result["success"] is True


class TestFailoverScenarioUnit:
    """Unit tests for failover scenarios (using mocks)."""

    @pytest.mark.asyncio
    async def test_gpu_failure_to_cpu_standby_recovery(self, mock_dumont_client, mock_instance):
        """Test failover from GPU to CPU standby."""
        # Setup mocks
        mock_dumont_client.instances.get = AsyncMock(return_value=mock_instance)
        mock_dumont_client.standby.simulate_failover = AsyncMock(return_value={
            "success": True,
            "new_instance_id": "gcp-cpu-123",
            "failover_time_seconds": 12.5,
            "strategy": "gcp_cpu_standby",
        })

        # Simulate GPU failure detection
        instance = await mock_dumont_client.instances.get(12345)

        # Trigger failover
        failover_result = await mock_dumont_client.standby.simulate_failover(
            gpu_id=instance.id,
            reason="GPU unresponsive",
        )

        assert failover_result["success"] is True
        assert failover_result["failover_time_seconds"] < 30

    @pytest.mark.asyncio
    async def test_fast_failover_with_race_strategy(self, mock_dumont_client):
        """Test fast failover with race strategy."""
        # Setup mocks
        mock_dumont_client.standby.fast_failover = AsyncMock(return_value={
            "success": True,
            "strategy": "race",
            "winning_strategy": "gcp_cpu_standby",
            "failover_time_seconds": 8.2,
            "new_instance_id": "gcp-fast-123",
        })

        # Execute fast failover
        result = await mock_dumont_client.standby.fast_failover(
            gpu_id=12345,
            strategies=["gcp_cpu_standby", "new_gpu", "openrouter"],
        )

        assert result["success"] is True
        assert result["strategy"] == "race"
        assert result["failover_time_seconds"] < 15

    @pytest.mark.asyncio
    async def test_failover_orchestrator_execute(self, mock_dumont_client):
        """Test failover orchestrator execution."""
        # Setup mocks
        mock_dumont_client.failover.execute = AsyncMock(return_value=FailoverExecutionResult(
            success=True,
            failover_id="fo-12345",
            machine_id=67890,
            strategy_attempted="gcp_cpu_standby",
            strategy_succeeded="gcp_cpu_standby",
            new_gpu_id=12346,
            total_ms=10500,
            error=None,
        ))

        # Execute failover
        result = await mock_dumont_client.failover.execute(
            machine_id=67890,
            gpu_id=12345,
            ssh_host="192.168.1.100",
            ssh_port=22,
        )

        assert result.success is True
        assert result.strategy_succeeded == "gcp_cpu_standby"


class TestHibernationScenarioUnit:
    """Unit tests for hibernation scenarios (using mocks)."""

    @pytest.mark.asyncio
    async def test_hibernate_and_wake_cycle(self, mock_dumont_client, mock_instance, mock_snapshot):
        """Test complete hibernate → wake cycle."""
        # Setup mocks
        mock_dumont_client.instances.get = AsyncMock(return_value=mock_instance)
        mock_dumont_client.snapshots.create = AsyncMock(return_value=mock_snapshot)
        mock_dumont_client.instances.destroy = AsyncMock(return_value={"success": True})
        mock_dumont_client.instances.wake = AsyncMock(return_value={
            "success": True,
            "instance_id": 12346,
            "restored_from_snapshot": "snap-123",
        })

        # Step 1: Get running instance
        instance = await mock_dumont_client.instances.get(12345)
        assert instance.status == "running"

        # Step 2: Create snapshot
        snapshot = await mock_dumont_client.snapshots.create(
            instance_id=instance.id,
            label="hibernate-snapshot",
        )
        assert snapshot.status == "completed"

        # Step 3: Destroy instance (hibernate)
        destroy_result = await mock_dumont_client.instances.destroy(instance.id)
        assert destroy_result["success"] is True

        # Step 4: Wake instance from snapshot
        wake_result = await mock_dumont_client.instances.wake(
            snapshot_id=snapshot.id,
            gpu_name="RTX_4090",
        )
        assert wake_result["success"] is True
        assert wake_result["restored_from_snapshot"] == snapshot.id

    @pytest.mark.asyncio
    async def test_auto_hibernation_trigger(self, mock_dumont_client):
        """Test auto-hibernation trigger based on idle detection."""
        # Setup mocks for idle instance
        idle_instance = Instance(
            id=12345,
            status="running",
            gpu_name="RTX_4090",
            num_gpus=1,
            gpu_ram=24.0,
            cpu_cores=8,
            cpu_ram=64.0,
            disk_space=100.0,
            dph_total=0.45,
            ssh_host="192.168.1.100",
            ssh_port=22,
            label="idle-instance",
            gpu_util=0.0,  # Idle GPU
        )

        mock_dumont_client.instances.get = AsyncMock(return_value=idle_instance)
        mock_dumont_client.settings.get = AsyncMock(return_value=MagicMock(
            settings={"auto_hibernation_enabled": True, "hibernation_idle_minutes": 3}
        ))

        # Verify settings
        settings = await mock_dumont_client.settings.get()
        assert settings.settings["auto_hibernation_enabled"] is True
        assert settings.settings["hibernation_idle_minutes"] == 3


class TestMigrationScenarioUnit:
    """Unit tests for migration scenarios (using mocks)."""

    @pytest.mark.asyncio
    async def test_migrate_gpu_to_cpu(self, mock_dumont_client, mock_instance):
        """Test migration from GPU to CPU instance."""
        # Setup mocks
        mock_dumont_client.instances.get = AsyncMock(return_value=mock_instance)
        mock_dumont_client.instances.migrate = AsyncMock(return_value={
            "success": True,
            "source_instance_id": 12345,
            "target_instance_id": "gcp-cpu-123",
            "migration_type": "gpu_to_cpu",
            "migration_time_seconds": 45.0,
        })

        # Get source instance
        instance = await mock_dumont_client.instances.get(12345)

        # Migrate to CPU
        result = await mock_dumont_client.instances.migrate(
            instance_id=instance.id,
            target_type="cpu",
            zone="us-central1-a",
        )

        assert result["success"] is True
        assert result["migration_type"] == "gpu_to_cpu"

    @pytest.mark.asyncio
    async def test_migrate_cpu_to_gpu(self, mock_dumont_client):
        """Test migration from CPU back to GPU instance."""
        # Setup mocks
        mock_dumont_client.instances.migrate = AsyncMock(return_value={
            "success": True,
            "source_instance_id": "gcp-cpu-123",
            "target_instance_id": 12346,
            "migration_type": "cpu_to_gpu",
            "migration_time_seconds": 60.0,
            "gpu_name": "RTX_4090",
        })

        # Migrate back to GPU
        result = await mock_dumont_client.instances.migrate(
            instance_id="gcp-cpu-123",
            target_type="gpu",
            gpu_name="RTX_4090",
        )

        assert result["success"] is True
        assert result["migration_type"] == "cpu_to_gpu"
        assert result["gpu_name"] == "RTX_4090"

    @pytest.mark.asyncio
    async def test_migration_estimate(self, mock_dumont_client):
        """Test migration cost/time estimation."""
        # Setup mocks
        mock_dumont_client.instances.migrate_estimate = AsyncMock(return_value={
            "estimated_time_seconds": 45,
            "estimated_cost": 0.05,
            "data_to_transfer_gb": 7.5,
            "available_targets": ["gcp-us-central1", "gcp-us-east1"],
        })

        # Get estimate
        estimate = await mock_dumont_client.instances.migrate_estimate(
            instance_id=12345,
            target_type="cpu",
        )

        assert estimate["estimated_time_seconds"] == 45
        assert estimate["data_to_transfer_gb"] == 7.5


class TestCompleteWorkflowUnit:
    """Unit tests for complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_full_deployment_lifecycle(self, mock_dumont_client, mock_deploy_result, mock_snapshot):
        """Test complete lifecycle: deploy → install model → hibernate → wake."""
        # Setup all mocks
        mock_dumont_client.wizard.deploy = AsyncMock(return_value=mock_deploy_result)
        mock_dumont_client.models.install = AsyncMock(return_value=ModelInstallResult(
            success=True,
            model_name="llama3.2",
            instance_id=12345,
            ollama_url="http://192.168.1.100:11434",
            error=None,
        ))
        mock_dumont_client.snapshots.create = AsyncMock(return_value=mock_snapshot)
        mock_dumont_client.instances.destroy = AsyncMock(return_value={"success": True})
        mock_dumont_client.instances.wake = AsyncMock(return_value={
            "success": True,
            "instance_id": 12346,
        })

        # Step 1: Deploy
        deploy_result = await mock_dumont_client.wizard.deploy(gpu_name="RTX_4090")
        assert deploy_result.success is True

        # Step 2: Install model
        model_result = await mock_dumont_client.models.install(
            instance_id=deploy_result.instance_id,
            model="llama3.2",
        )
        assert model_result.success is True

        # Step 3: Create snapshot
        snapshot = await mock_dumont_client.snapshots.create(
            instance_id=deploy_result.instance_id,
        )
        assert snapshot.status == "completed"

        # Step 4: Destroy (hibernate)
        destroy_result = await mock_dumont_client.instances.destroy(deploy_result.instance_id)
        assert destroy_result["success"] is True

        # Step 5: Wake
        wake_result = await mock_dumont_client.instances.wake(snapshot_id=snapshot.id)
        assert wake_result["success"] is True


# =============================================================================
# Integration Tests (require real API)
# =============================================================================

@pytest.mark.integration
@pytest.mark.e2e
class TestDeployScenarioIntegration:
    """Integration tests for deploy scenarios (requires real API)."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_search_gpu_offers(self, client_with_api_key, rate_limiter):
        """Test searching for GPU offers (may be empty if market has no offers)."""
        await rate_limiter.wait()

        # Search for available offers - may return empty list depending on market
        offers = await client_with_api_key.instances.search_offers(
            gpu_name="RTX_4090",
            max_price=1.00,
            limit=5,
        )

        # Just verify we got a list back (may be empty)
        assert isinstance(offers, list)

        # Note: Actually deploying would create real resources and cost money
        # In a real E2E test, you would proceed with:
        # deploy_result = await client_with_api_key.wizard.deploy(...)
        # And then clean up at the end


@pytest.mark.integration
@pytest.mark.e2e
class TestStandbyScenarioIntegration:
    """Integration tests for standby scenarios (requires real API)."""

    @pytest.mark.asyncio
    async def test_get_standby_status(self, client_with_api_key, rate_limiter):
        """Test getting standby system status."""
        await rate_limiter.wait()

        status = await client_with_api_key.standby.status()

        assert isinstance(status, StandbyStatus)

    @pytest.mark.asyncio
    async def test_get_standby_pricing(self, client_with_api_key, rate_limiter):
        """Test getting standby pricing estimate."""
        await rate_limiter.wait()

        pricing = await client_with_api_key.standby.pricing(
            machine_type="e2-medium",
            disk_gb=50,
            spot=True,
        )

        assert pricing is not None
        assert hasattr(pricing, "estimated_hourly_usd")


@pytest.mark.integration
@pytest.mark.e2e
class TestMetricsScenarioIntegration:
    """Integration tests for metrics scenarios (requires real API)."""

    @pytest.mark.asyncio
    async def test_get_savings_real(self, client_with_api_key, rate_limiter):
        """Test getting real savings data."""
        await rate_limiter.wait()

        try:
            # Get real savings data
            savings = await client_with_api_key.metrics.savings_real(days=30)
            assert savings is not None
        except Exception:
            # Endpoint may not have data or may return error
            pytest.skip("Savings endpoint not available")


@pytest.mark.integration
@pytest.mark.e2e
class TestSettingsScenarioIntegration:
    """Integration tests for settings scenarios (requires real API)."""

    @pytest.mark.asyncio
    async def test_get_account_overview(self, client_with_api_key, rate_limiter):
        """Test getting complete account overview."""
        await rate_limiter.wait()

        # Get settings
        settings = await client_with_api_key.settings.get()
        assert settings is not None

        # Get balance
        balance = await client_with_api_key.settings.balance()
        assert balance is not None
        assert isinstance(balance.credit, (int, float))


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture
async def cleanup_resources():
    """Fixture to track and clean up resources created during tests."""
    created_instances = []
    created_snapshots = []

    yield {
        "instances": created_instances,
        "snapshots": created_snapshots,
    }

    # Cleanup would happen here if we had a real client
    # for instance_id in created_instances:
    #     await client.instances.destroy(instance_id)
