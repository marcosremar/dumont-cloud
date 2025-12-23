"""
Failover Orchestrator module.

Allows executing and monitoring failover operations with multiple strategies:
- GPU Warm Pool (fast, ~30-60s)
- CPU Standby + Snapshot (fallback, ~10-20min)
- Regional Volume (persistent storage)
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FailoverExecutionResult:
    """Result of a failover execution."""
    success: bool
    failover_id: str
    machine_id: int
    strategy_attempted: str
    strategy_succeeded: Optional[str] = None

    # New instance info
    new_gpu_id: Optional[int] = None
    new_ssh_host: Optional[str] = None
    new_ssh_port: Optional[int] = None
    new_gpu_name: Optional[str] = None

    # Timing
    warm_pool_attempt_ms: int = 0
    cpu_standby_attempt_ms: int = 0
    total_ms: int = 0

    # Errors
    error: Optional[str] = None
    warm_pool_error: Optional[str] = None
    cpu_standby_error: Optional[str] = None


@dataclass
class ReadinessStatus:
    """Failover readiness status for a machine."""
    machine_id: int
    effective_strategy: str
    warm_pool_ready: bool
    warm_pool_status: Optional[Dict[str, Any]]
    cpu_standby_ready: bool
    cpu_standby_status: Optional[Dict[str, Any]]
    overall_ready: bool


@dataclass
class StrategyInfo:
    """Information about a failover strategy."""
    id: str
    name: str
    description: str
    recovery_time: str
    cost: str
    requirements: List[str]


@dataclass
class RegionalVolume:
    """Regional volume for failover."""
    volume_id: int
    region: str
    size_gb: int
    name: Optional[str] = None
    status: Optional[str] = None


@dataclass
class RegionalFailoverResult:
    """Result of a regional volume failover."""
    success: bool
    volume_id: int
    old_instance_id: Optional[int]
    new_instance_id: Optional[int]
    new_gpu_name: Optional[str]
    region: Optional[str]
    failover_time_seconds: float
    message: str
    error: Optional[str]
    ssh_host: Optional[str]
    ssh_port: Optional[int]


@dataclass
class GPUOffer:
    """GPU offer in a region."""
    offer_id: int
    gpu_name: str
    num_gpus: int
    price_per_hour: float
    reliability: float
    geolocation: str


class FailoverClient:
    """
    Client for Failover Orchestrator operations.

    The failover system supports multiple strategies:
    1. GPU Warm Pool - Fastest (~30-60s), uses standby GPU on same host
    2. CPU Standby - Fallback (~10-20min), uses snapshot restore
    3. Regional Volume - Fast (~30-60s), uses persistent regional storage

    Example:
        async with DumontClient(api_key="...") as client:
            # Check readiness
            readiness = await client.failover.readiness(machine_id=123)
            if readiness.overall_ready:
                print("Machine is ready for failover!")

            # Execute failover
            result = await client.failover.execute(
                machine_id=123,
                gpu_instance_id=12345,
                ssh_host="192.168.1.100",
                ssh_port=22
            )
    """

    def __init__(self, base_client):
        self._client = base_client

    async def execute(
        self,
        machine_id: int,
        gpu_instance_id: int,
        ssh_host: str,
        ssh_port: int,
        workspace_path: str = "/workspace",
        force_strategy: Optional[str] = None,
    ) -> FailoverExecutionResult:
        """
        Execute failover for a machine.

        The system will try strategies in order:
        1. GPU Warm Pool (if enabled and available)
        2. CPU Standby + Snapshot (as fallback)

        Args:
            machine_id: Internal machine ID
            gpu_instance_id: Vast.ai instance ID
            ssh_host: Current SSH host
            ssh_port: Current SSH port
            workspace_path: Path to backup/restore
            force_strategy: Force specific strategy (warm_pool, cpu_standby, both)

        Returns:
            FailoverExecutionResult with new instance info
        """
        data = {
            "machine_id": machine_id,
            "gpu_instance_id": gpu_instance_id,
            "ssh_host": ssh_host,
            "ssh_port": ssh_port,
            "workspace_path": workspace_path,
        }
        if force_strategy:
            data["force_strategy"] = force_strategy

        response = await self._client.post("/api/v1/failover/execute", data=data)

        return FailoverExecutionResult(
            success=response.get("success", False),
            failover_id=response.get("failover_id", ""),
            machine_id=response.get("machine_id", machine_id),
            strategy_attempted=response.get("strategy_attempted", ""),
            strategy_succeeded=response.get("strategy_succeeded"),
            new_gpu_id=response.get("new_gpu_id"),
            new_ssh_host=response.get("new_ssh_host"),
            new_ssh_port=response.get("new_ssh_port"),
            new_gpu_name=response.get("new_gpu_name"),
            warm_pool_attempt_ms=response.get("warm_pool_attempt_ms", 0),
            cpu_standby_attempt_ms=response.get("cpu_standby_attempt_ms", 0),
            total_ms=response.get("total_ms", 0),
            error=response.get("error"),
            warm_pool_error=response.get("warm_pool_error"),
            cpu_standby_error=response.get("cpu_standby_error"),
        )

    async def readiness(self, machine_id: int) -> ReadinessStatus:
        """
        Check if a machine is ready for failover.

        Returns status of each configured strategy:
        - Warm Pool: if standby GPU is available
        - CPU Standby: if association with CPU standby exists

        Args:
            machine_id: Internal machine ID

        Returns:
            ReadinessStatus with details for each strategy
        """
        response = await self._client.get(f"/api/v1/failover/readiness/{machine_id}")

        return ReadinessStatus(
            machine_id=response.get("machine_id", machine_id),
            effective_strategy=response.get("effective_strategy", "disabled"),
            warm_pool_ready=response.get("warm_pool_ready", False),
            warm_pool_status=response.get("warm_pool_status"),
            cpu_standby_ready=response.get("cpu_standby_ready", False),
            cpu_standby_status=response.get("cpu_standby_status"),
            overall_ready=response.get("overall_ready", False),
        )

    async def status(self, machine_id: int) -> Dict[str, Any]:
        """
        Get detailed status of failover strategies for a machine.

        Includes recommendations for actions if needed.

        Args:
            machine_id: Internal machine ID

        Returns:
            Status with strategy details and recommendations
        """
        return await self._client.get(f"/api/v1/failover/status/{machine_id}")

    async def test(
        self,
        machine_id: int,
        gpu_instance_id: int,
        ssh_host: str,
        ssh_port: int,
        strategy: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Test failover for a machine.

        With dry_run=True (default), only checks if failover would be possible.
        With dry_run=False, executes the real failover.

        WARNING: dry_run=False will actually execute the failover!

        Args:
            machine_id: Internal machine ID
            gpu_instance_id: Vast.ai instance ID
            ssh_host: Current SSH host
            ssh_port: Current SSH port
            strategy: Strategy to test (optional)
            dry_run: If True, only simulate

        Returns:
            Test results
        """
        params = {
            "gpu_instance_id": gpu_instance_id,
            "ssh_host": ssh_host,
            "ssh_port": ssh_port,
            "dry_run": dry_run,
        }
        if strategy:
            params["strategy"] = strategy

        return await self._client.post(
            f"/api/v1/failover/test/{machine_id}",
            params=params
        )

    async def strategies(self) -> List[StrategyInfo]:
        """
        List available failover strategies.

        Returns:
            List of available strategies with descriptions
        """
        response = await self._client.get("/api/v1/failover/strategies")
        strategies_data = response.get("strategies", [])

        return [
            StrategyInfo(
                id=s.get("id", ""),
                name=s.get("name", ""),
                description=s.get("description", ""),
                recovery_time=s.get("recovery_time", ""),
                cost=s.get("cost", ""),
                requirements=s.get("requirements", []),
            )
            for s in strategies_data
        ]

    # =========================================================================
    # Regional Volume Operations
    # =========================================================================

    async def create_regional_volume(
        self,
        region: str,
        size_gb: int = 50,
        name: Optional[str] = None,
    ) -> RegionalVolume:
        """
        Create a regional volume for failover.

        The volume persists in the region even when the GPU is destroyed.

        Args:
            region: Region code (e.g., "US", "DE", "PL")
            size_gb: Volume size in GB
            name: Optional volume name

        Returns:
            Created volume info
        """
        data = {
            "region": region,
            "size_gb": size_gb,
        }
        if name:
            data["name"] = name

        response = await self._client.post(
            "/api/v1/failover/regional-volume/create",
            data=data
        )

        return RegionalVolume(
            volume_id=response.get("volume_id", 0),
            region=response.get("region", region),
            size_gb=response.get("size_gb", size_gb),
            name=name,
        )

    async def regional_failover(
        self,
        volume_id: int,
        region: str,
        old_instance_id: Optional[int] = None,
        preferred_gpus: Optional[List[str]] = None,
        max_price: Optional[float] = None,
        use_spot: bool = True,
        docker_image: str = "pytorch/pytorch:latest",
        mount_path: str = "/data",
    ) -> RegionalFailoverResult:
        """
        Execute failover using regional volume.

        Mounts the existing volume on a new GPU in the same region.
        Estimated time: 30-60 seconds.

        Args:
            volume_id: ID of existing volume
            region: Volume region
            old_instance_id: ID of old instance (for cleanup)
            preferred_gpus: Preferred GPU types (e.g., ["RTX_4090", "RTX_3090"])
            max_price: Maximum price per hour
            use_spot: Use spot instances
            docker_image: Docker image to use
            mount_path: Mount path for volume

        Returns:
            RegionalFailoverResult with new instance info
        """
        data = {
            "volume_id": volume_id,
            "region": region,
            "use_spot": use_spot,
            "docker_image": docker_image,
            "mount_path": mount_path,
        }
        if old_instance_id:
            data["old_instance_id"] = old_instance_id
        if preferred_gpus:
            data["preferred_gpus"] = preferred_gpus
        if max_price:
            data["max_price"] = max_price

        response = await self._client.post(
            "/api/v1/failover/regional-volume/failover",
            data=data
        )

        return RegionalFailoverResult(
            success=response.get("success", False),
            volume_id=response.get("volume_id", volume_id),
            old_instance_id=response.get("old_instance_id"),
            new_instance_id=response.get("new_instance_id"),
            new_gpu_name=response.get("new_gpu_name"),
            region=response.get("region"),
            failover_time_seconds=response.get("failover_time_seconds", 0),
            message=response.get("message", ""),
            error=response.get("error"),
            ssh_host=response.get("ssh_host"),
            ssh_port=response.get("ssh_port"),
        )

    async def list_regional_volumes(self) -> List[Dict[str, Any]]:
        """
        List all regional volumes for the user.

        Returns:
            List of volumes
        """
        response = await self._client.get("/api/v1/failover/regional-volume/list")
        return response.get("volumes", [])

    async def get_regional_volume(self, volume_id: int) -> Dict[str, Any]:
        """
        Get information about a specific volume.

        Args:
            volume_id: Volume ID

        Returns:
            Volume information
        """
        return await self._client.get(f"/api/v1/failover/regional-volume/{volume_id}")

    async def delete_regional_volume(self, volume_id: int) -> Dict[str, Any]:
        """
        Delete a regional volume.

        The volume must be detached from any instance.

        Args:
            volume_id: Volume ID

        Returns:
            Deletion result
        """
        return await self._client.delete(f"/api/v1/failover/regional-volume/{volume_id}")

    async def search_gpus_in_region(
        self,
        region: str,
        max_price: Optional[float] = None,
        gpu_name: Optional[str] = None,
    ) -> Optional[GPUOffer]:
        """
        Search for available GPUs in a region for failover.

        Args:
            region: Region code
            max_price: Maximum price per hour
            gpu_name: Specific GPU name

        Returns:
            GPUOffer if found, None otherwise
        """
        params = {}
        if max_price:
            params["max_price"] = max_price
        if gpu_name:
            params["gpu_name"] = gpu_name

        response = await self._client.get(
            f"/api/v1/failover/regional-volume/search/{region}",
            params=params
        )

        if response.get("found"):
            offer = response.get("offer", {})
            return GPUOffer(
                offer_id=offer.get("offer_id", 0),
                gpu_name=offer.get("gpu_name", ""),
                num_gpus=offer.get("num_gpus", 1),
                price_per_hour=offer.get("price_per_hour", 0),
                reliability=offer.get("reliability", 0),
                geolocation=offer.get("geolocation", ""),
            )

        return None
