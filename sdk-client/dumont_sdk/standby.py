"""
CPU Standby management module.

Allows managing CPU standby VMs for GPU failover/recovery.
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StandbyStatus:
    """Status of the CPU standby system."""
    configured: bool
    auto_standby_enabled: bool
    active_associations: int
    associations: Dict[str, Any]
    config: Dict[str, Any]


@dataclass
class StandbyAssociation:
    """Association between GPU and CPU standby."""
    gpu_instance_id: int
    cpu_instance_name: str
    cpu_instance_zone: str
    cpu_instance_ip: Optional[str]
    sync_enabled: bool
    state: Optional[str] = None
    sync_count: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class PricingEstimate:
    """Estimated pricing for CPU standby."""
    machine_type: str
    disk_gb: int
    spot: bool
    estimated_hourly_usd: float
    estimated_monthly_usd: float
    breakdown: Dict[str, float]


@dataclass
class FailoverResult:
    """Result of a failover operation."""
    failover_id: str
    gpu_instance_id: int
    success: bool
    phase: str
    total_time_ms: Optional[int] = None
    new_gpu_id: Optional[int] = None
    data_restored: bool = False
    error: Optional[str] = None
    phase_timings: Optional[Dict[str, int]] = None


class StandbyClient:
    """
    Client for CPU Standby management.

    The CPU Standby system provides automatic failover capability:
    - When a GPU instance is created, a CPU standby VM is provisioned in GCP
    - Data is continuously synced from GPU to CPU standby
    - On GPU failure, workload fails over to CPU standby
    - System automatically provisions new GPU and restores data

    Example:
        async with DumontClient(api_key="...") as client:
            # Check status
            status = await client.standby.status()
            print(f"Active associations: {status.active_associations}")

            # Configure auto-standby
            await client.standby.configure(
                enabled=True,
                gcp_zone="europe-west1-b",
                gcp_machine_type="e2-medium"
            )

            # Provision standby for existing GPU
            await client.standby.provision(gpu_instance_id=12345)
    """

    def __init__(self, base_client):
        self._client = base_client

    async def status(self) -> StandbyStatus:
        """
        Get status of the CPU standby system.

        Returns:
            StandbyStatus with configuration and active associations
        """
        response = await self._client.get("/api/v1/standby/status")

        return StandbyStatus(
            configured=response.get("configured", False),
            auto_standby_enabled=response.get("auto_standby_enabled", False),
            active_associations=response.get("active_associations", 0),
            associations=response.get("associations", {}),
            config=response.get("config", {}),
        )

    async def configure(
        self,
        enabled: bool = True,
        gcp_zone: str = "europe-west1-b",
        gcp_machine_type: str = "e2-medium",
        gcp_disk_size: int = 100,
        gcp_spot: bool = True,
        sync_interval: int = 30,
        auto_failover: bool = True,
        auto_recovery: bool = True,
    ) -> Dict[str, Any]:
        """
        Configure the auto-standby system.

        When enabled, creating a GPU instance will automatically:
        1. Provision a CPU standby VM in GCP
        2. Start syncing data GPU → CPU
        3. Enable automatic failover on GPU failure

        Requires GCP credentials to be configured in user settings.

        Args:
            enabled: Enable/disable auto-standby
            gcp_zone: GCP zone for standby VM (e.g., "europe-west1-b")
            gcp_machine_type: GCP machine type (e.g., "e2-medium")
            gcp_disk_size: Disk size in GB
            gcp_spot: Use Spot VM (cheaper)
            sync_interval: Sync interval in seconds
            auto_failover: Enable automatic failover
            auto_recovery: Enable automatic GPU recovery

        Returns:
            Configuration result with estimated costs
        """
        data = {
            "enabled": enabled,
            "gcp_zone": gcp_zone,
            "gcp_machine_type": gcp_machine_type,
            "gcp_disk_size": gcp_disk_size,
            "gcp_spot": gcp_spot,
            "sync_interval": sync_interval,
            "auto_failover": auto_failover,
            "auto_recovery": auto_recovery,
        }

        return await self._client.post("/api/v1/standby/configure", data=data)

    async def associations(self) -> List[StandbyAssociation]:
        """
        List all active GPU ↔ CPU standby associations.

        Returns:
            List of associations
        """
        response = await self._client.get("/api/v1/standby/associations")
        associations_data = response.get("associations", {})

        result = []
        for gpu_id, assoc in associations_data.items():
            cpu_standby = assoc.get("cpu_standby", {})
            result.append(
                StandbyAssociation(
                    gpu_instance_id=int(gpu_id),
                    cpu_instance_name=cpu_standby.get("name", ""),
                    cpu_instance_zone=cpu_standby.get("zone", ""),
                    cpu_instance_ip=cpu_standby.get("ip"),
                    sync_enabled=assoc.get("sync_enabled", False),
                    state=assoc.get("state"),
                    sync_count=assoc.get("sync_count"),
                    created_at=cpu_standby.get("created_at"),
                )
            )

        return result

    async def get_association(self, gpu_instance_id: int) -> StandbyAssociation:
        """
        Get CPU standby association for a specific GPU.

        Args:
            gpu_instance_id: ID of the GPU instance

        Returns:
            Association details

        Raises:
            DumontError: If no association exists
        """
        response = await self._client.get(f"/api/v1/standby/associations/{gpu_instance_id}")

        cpu_standby = response.get("cpu_standby", {})
        return StandbyAssociation(
            gpu_instance_id=response.get("gpu_instance_id", gpu_instance_id),
            cpu_instance_name=cpu_standby.get("name", ""),
            cpu_instance_zone=cpu_standby.get("zone", ""),
            cpu_instance_ip=cpu_standby.get("ip"),
            sync_enabled=response.get("sync_enabled", False),
            state=response.get("state"),
            sync_count=response.get("sync_count"),
        )

    async def provision(
        self,
        gpu_instance_id: int,
        label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Manually provision CPU Standby for an existing GPU instance.

        Use this for GPU instances created before auto-standby was enabled.

        Args:
            gpu_instance_id: ID of the GPU instance
            label: Optional label for the CPU standby VM

        Returns:
            Association info

        Raises:
            DumontError: If standby not configured or provisioning fails
        """
        params = {}
        if label:
            params["label"] = label

        return await self._client.post(
            f"/api/v1/standby/provision/{gpu_instance_id}",
            params=params
        )

    async def start_sync(self, gpu_instance_id: int) -> Dict[str, Any]:
        """
        Start synchronization for a GPU ↔ CPU standby pair.

        Begins continuous sync of /workspace from GPU to CPU.

        Args:
            gpu_instance_id: ID of the GPU instance

        Returns:
            Sync start result
        """
        return await self._client.post(
            f"/api/v1/standby/associations/{gpu_instance_id}/start-sync"
        )

    async def stop_sync(self, gpu_instance_id: int) -> Dict[str, Any]:
        """
        Stop synchronization for a GPU ↔ CPU standby pair.

        Args:
            gpu_instance_id: ID of the GPU instance

        Returns:
            Sync stop result
        """
        return await self._client.post(
            f"/api/v1/standby/associations/{gpu_instance_id}/stop-sync"
        )

    async def destroy(
        self,
        gpu_instance_id: int,
        keep_gpu: bool = True,
    ) -> Dict[str, Any]:
        """
        Destroy the CPU standby for a GPU instance.

        This removes the CPU standby VM and stops sync/failover.

        Args:
            gpu_instance_id: ID of the GPU instance
            keep_gpu: Keep the GPU instance running (default True)

        Returns:
            Destruction result
        """
        params = {"keep_gpu": keep_gpu}
        return await self._client.delete(
            f"/api/v1/standby/associations/{gpu_instance_id}",
            params=params
        )

    async def pricing(
        self,
        machine_type: str = "e2-medium",
        disk_gb: int = 100,
        spot: bool = True,
    ) -> PricingEstimate:
        """
        Get estimated pricing for CPU standby.

        Args:
            machine_type: GCP machine type
            disk_gb: Disk size in GB
            spot: Use Spot VM pricing

        Returns:
            Pricing estimate
        """
        params = {
            "machine_type": machine_type,
            "disk_gb": disk_gb,
            "spot": spot,
        }

        response = await self._client.get("/api/v1/standby/pricing", params=params)

        return PricingEstimate(
            machine_type=response.get("machine_type", machine_type),
            disk_gb=response.get("disk_gb", disk_gb),
            spot=response.get("spot", spot),
            estimated_hourly_usd=response.get("estimated_hourly_usd", 0),
            estimated_monthly_usd=response.get("estimated_monthly_usd", 0),
            breakdown=response.get("breakdown", {}),
        )

    # =========================================================================
    # Failover Operations
    # =========================================================================

    async def simulate_failover(
        self,
        gpu_instance_id: int,
        reason: str = "spot_interruption",
        simulate_restore: bool = True,
        simulate_new_gpu: bool = True,
    ) -> FailoverResult:
        """
        Simulate a GPU failover for testing purposes.

        This simulates a complete failover journey without actual resources:
        1. GPU Lost - Detects GPU failure
        2. Failover to CPU Standby - Switches to CPU backup
        3. Searching GPU - Searches for replacement
        4. Provisioning - Provisions new GPU
        5. Restoring - Restores data from CPU backup
        6. Complete - Failover complete

        Args:
            gpu_instance_id: ID of the GPU instance
            reason: Failure reason (spot_interruption, hardware_failure, etc)
            simulate_restore: Simulate data restoration
            simulate_new_gpu: Simulate new GPU provisioning

        Returns:
            FailoverResult with failover_id to track progress
        """
        data = {
            "reason": reason,
            "simulate_restore": simulate_restore,
            "simulate_new_gpu": simulate_new_gpu,
        }

        response = await self._client.post(
            f"/api/v1/standby/failover/simulate/{gpu_instance_id}",
            data=data
        )

        return FailoverResult(
            failover_id=response.get("failover_id", ""),
            gpu_instance_id=response.get("gpu_instance_id", gpu_instance_id),
            success=response.get("success", False),
            phase=response.get("phase", "detecting"),
        )

    async def failover_status(self, failover_id: str) -> FailoverResult:
        """
        Get status of an ongoing or completed failover.

        Args:
            failover_id: ID from simulate_failover or fast_failover

        Returns:
            Current failover status with phase and timings
        """
        response = await self._client.get(f"/api/v1/standby/failover/status/{failover_id}")

        return FailoverResult(
            failover_id=response.get("failover_id", failover_id),
            gpu_instance_id=response.get("gpu_instance_id", 0),
            success=response.get("success", False),
            phase=response.get("phase", "unknown"),
            total_time_ms=response.get("total_time_ms"),
            new_gpu_id=response.get("new_gpu_id"),
            data_restored=response.get("data_restored", False),
            phase_timings=response.get("phase_timings_ms"),
        )

    async def failover_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Get failover report with metrics.

        Args:
            days: Number of days to include in report

        Returns:
            Report with success rate, MTTR, latency breakdown, history
        """
        params = {"days": days}
        return await self._client.get("/api/v1/standby/failover/report", params=params)

    async def active_failovers(self) -> List[FailoverResult]:
        """
        Get list of currently active (in-progress) failovers.

        Returns:
            List of active failovers
        """
        response = await self._client.get("/api/v1/standby/failover/active")
        failovers = response.get("failovers", [])

        return [
            FailoverResult(
                failover_id=f.get("failover_id", ""),
                gpu_instance_id=f.get("gpu_instance_id", 0),
                success=f.get("success", False),
                phase=f.get("phase", "unknown"),
                total_time_ms=f.get("total_time_ms"),
                new_gpu_id=f.get("new_gpu_id"),
                data_restored=f.get("data_restored", False),
                phase_timings=f.get("phase_timings_ms"),
            )
            for f in failovers
        ]

    async def fast_failover(
        self,
        gpu_instance_id: int,
        model: str = "qwen2.5:0.5b",
        test_prompt: str = "Hello, what is your name?",
        workspace_path: str = "/workspace",
        skip_inference: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute fast failover using race strategy.

        This uses GPUProvisioner with race strategy:
        - Provisions 5 GPUs in parallel per round
        - First GPU to have SSH ready wins
        - Deletes the other 4
        - Up to 4 rounds (20 GPUs total)

        Much faster and more reliable than standard failover.

        Args:
            gpu_instance_id: ID of the GPU instance
            model: Ollama model for inference test
            test_prompt: Prompt to test inference
            workspace_path: Path to restore
            skip_inference: Skip inference test

        Returns:
            Failover result with detailed metrics
        """
        data = {
            "model": model,
            "test_prompt": test_prompt,
            "workspace_path": workspace_path,
            "skip_inference": skip_inference,
        }

        return await self._client.post(
            f"/api/v1/standby/failover/fast/{gpu_instance_id}",
            data=data
        )

    async def test_real_failover(
        self,
        gpu_instance_id: int,
        model: str = "qwen2.5:0.5b",
        test_prompt: str = "Hello, what is your name?",
        workspace_path: str = "/workspace",
        skip_inference: bool = False,
        destroy_original_gpu: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a REAL failover test with actual B2 snapshots.

        This performs a complete, realistic failover test:
        1. Snapshot Creation: Creates real snapshot in Backblaze B2
        2. GPU Simulation: Simulates GPU failure
        3. GPU Provisioning: Finds and provisions a new GPU
        4. Restore: Restores snapshot from B2 to new GPU
        5. Inference Test: Verifies model works after restore

        WARNING: This test will:
        - Create real data in Backblaze B2 (costs apply)
        - Provision a new GPU instance (costs apply)
        - Take several minutes to complete

        Args:
            gpu_instance_id: ID of the GPU instance
            model: Ollama model for inference test
            test_prompt: Prompt to test inference
            workspace_path: Path to backup/restore
            skip_inference: Skip inference test
            destroy_original_gpu: Actually destroy original GPU

        Returns:
            Detailed test results with all metrics
        """
        data = {
            "model": model,
            "test_prompt": test_prompt,
            "workspace_path": workspace_path,
            "skip_inference": skip_inference,
            "destroy_original_gpu": destroy_original_gpu,
        }

        return await self._client.post(
            f"/api/v1/standby/failover/test-real/{gpu_instance_id}",
            data=data
        )

    async def get_real_failover_report(self, failover_id: str) -> Dict[str, Any]:
        """
        Get detailed report for a specific real failover test.

        Args:
            failover_id: ID of the real failover test

        Returns:
            Detailed report with all metrics and timings
        """
        return await self._client.get(
            f"/api/v1/standby/failover/test-real/report/{failover_id}"
        )

    async def real_failover_history(
        self,
        days: int = 30,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Get history of all real failover tests.

        Args:
            days: Number of days to include
            limit: Maximum number of results

        Returns:
            Summary metrics and list of tests
        """
        params = {"days": days, "limit": limit}
        return await self._client.get(
            "/api/v1/standby/failover/test-real/history",
            params=params
        )

    # =========================================================================
    # Testing Helpers
    # =========================================================================

    async def create_mock_association(
        self,
        gpu_instance_id: int = 12345,
    ) -> Dict[str, Any]:
        """
        Create a mock standby association for testing.

        Creates a fake GPU ↔ CPU standby association without actually
        provisioning any resources. Use it to test failover simulation.

        Args:
            gpu_instance_id: Mock GPU instance ID

        Returns:
            Mock association info
        """
        params = {"gpu_instance_id": gpu_instance_id}
        return await self._client.post(
            "/api/v1/standby/test/create-mock-association",
            params=params
        )
