"""
Migration Service - Domain Service (Business Logic)
Orchestrates instance migration between GPU and CPU types
"""
import logging
import time
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass

from .instance_service import InstanceService
from .snapshot_service import SnapshotService
from ...core.exceptions import MigrationException, NotFoundException

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of a migration operation"""
    success: bool
    new_instance_id: Optional[int] = None
    old_instance_id: Optional[int] = None
    snapshot_id: Optional[str] = None
    error: Optional[str] = None
    steps_completed: list = None

    def __post_init__(self):
        if self.steps_completed is None:
            self.steps_completed = []


class MigrationService:
    """
    Domain service for instance migration.
    Handles GPU <-> CPU migrations preserving workspace via snapshots.
    """

    # Timeouts (seconds)
    SSH_READY_TIMEOUT = 120
    RESTORE_TIMEOUT = 600

    def __init__(
        self,
        instance_service: InstanceService,
        snapshot_service: SnapshotService,
        vast_service,  # Direct vast service for CPU offers
    ):
        """
        Initialize migration service

        Args:
            instance_service: Instance management service
            snapshot_service: Snapshot management service
            vast_service: Direct vast.ai service for CPU-specific operations
        """
        self.instances = instance_service
        self.snapshots = snapshot_service
        self.vast = vast_service

    def migrate_instance(
        self,
        source_instance_id: int,
        target_type: Literal["gpu", "cpu"],
        gpu_name: Optional[str] = None,
        max_price: float = 2.0,
        region: Optional[str] = None,
        disk_size: int = 100,
        auto_destroy_source: bool = True,
    ) -> MigrationResult:
        """
        Migrate an instance from GPU to CPU or vice-versa.

        Flow:
        1. Validate source instance exists and is running
        2. Create snapshot of source instance
        3. Search for target offers (GPU or CPU)
        4. Create new instance
        5. Wait for SSH ready
        6. Restore snapshot to new instance
        7. Destroy source instance (if auto_destroy_source=True)

        Args:
            source_instance_id: ID of the source instance
            target_type: Target type ("gpu" or "cpu")
            gpu_name: GPU model if target_type is "gpu"
            max_price: Maximum price per hour
            region: Region filter
            disk_size: Disk size in GB
            auto_destroy_source: Destroy source after successful migration

        Returns:
            MigrationResult with details

        Raises:
            MigrationException: If migration fails
        """
        result = MigrationResult(
            success=False,
            old_instance_id=source_instance_id,
        )

        try:
            # Step 1: Validate source instance
            logger.info(f"[Migration] Step 1: Validating source instance {source_instance_id}")
            source = self.instances.get_instance(source_instance_id)

            if not source.is_running:
                raise MigrationException(f"Source instance {source_instance_id} is not running")

            if not source.ssh_host or not source.ssh_port:
                raise MigrationException(f"Source instance {source_instance_id} SSH not available")

            result.steps_completed.append("validate_source")
            logger.info(f"[Migration] Source instance validated: {source.gpu_name} ({source.num_gpus} GPUs)")

            # Step 2: Create snapshot
            logger.info(f"[Migration] Step 2: Creating snapshot of source instance")
            snapshot_result = self.snapshots.create_snapshot(
                ssh_host=source.ssh_host,
                ssh_port=source.ssh_port,
                source_path="/workspace",
                tags=["migration", f"from-{source_instance_id}"],
            )
            snapshot_id = snapshot_result.get("snapshot_id")
            if not snapshot_id:
                raise MigrationException("Failed to create snapshot")

            result.snapshot_id = snapshot_id
            result.steps_completed.append("create_snapshot")
            logger.info(f"[Migration] Snapshot created: {snapshot_id}")

            # Step 3: Search for target offers
            logger.info(f"[Migration] Step 3: Searching for {target_type} offers")
            if target_type == "cpu":
                offers = self.vast.search_cpu_offers(
                    min_cpu_cores=4,
                    min_cpu_ram=8,
                    min_disk=disk_size,
                    max_price=max_price,
                    region=region,
                    limit=10,
                )
            else:  # GPU
                if not gpu_name:
                    raise MigrationException("gpu_name is required for GPU migration")
                offers = self.vast.search_offers(
                    gpu_name=gpu_name,
                    num_gpus=1,
                    min_disk=disk_size,
                    max_price=max_price,
                    region=region,
                    limit=10,
                )

            if not offers:
                raise MigrationException(f"No {target_type} offers found matching criteria")

            target_offer = offers[0]  # Cheapest offer
            offer_id = target_offer.get("id")
            result.steps_completed.append("search_offers")
            logger.info(f"[Migration] Found offer: {offer_id} at ${target_offer.get('dph_total', 0):.4f}/hr")

            # Step 4: Create new instance
            logger.info(f"[Migration] Step 4: Creating new {target_type} instance")
            if target_type == "cpu":
                new_instance_id = self.vast.create_cpu_instance(
                    offer_id=offer_id,
                    disk=disk_size,
                    instance_id_hint=source_instance_id,
                )
            else:  # GPU
                new_instance_id = self.vast.create_instance(
                    offer_id=offer_id,
                    disk=disk_size,
                )

            if not new_instance_id:
                raise MigrationException("Failed to create new instance")

            result.new_instance_id = new_instance_id
            result.steps_completed.append("create_instance")
            logger.info(f"[Migration] New instance created: {new_instance_id}")

            # Step 5: Wait for SSH ready
            logger.info(f"[Migration] Step 5: Waiting for SSH ready on new instance")
            new_instance = self._wait_for_ssh_ready(new_instance_id)
            if not new_instance:
                raise MigrationException(f"New instance {new_instance_id} SSH not ready after timeout")

            result.steps_completed.append("ssh_ready")
            logger.info(f"[Migration] SSH ready on {new_instance.ssh_host}:{new_instance.ssh_port}")

            # Step 6: Restore snapshot
            logger.info(f"[Migration] Step 6: Restoring snapshot to new instance")
            restore_result = self.snapshots.restore_snapshot(
                snapshot_id=snapshot_id,
                ssh_host=new_instance.ssh_host,
                ssh_port=new_instance.ssh_port,
                target_path="/workspace",
                verify=False,
            )

            if not restore_result.get("success"):
                raise MigrationException(f"Failed to restore snapshot: {restore_result.get('errors')}")

            result.steps_completed.append("restore_snapshot")
            logger.info(f"[Migration] Snapshot restored successfully")

            # Step 7: Destroy source (if enabled)
            if auto_destroy_source:
                logger.info(f"[Migration] Step 7: Destroying source instance {source_instance_id}")
                destroy_success = self.instances.destroy_instance(source_instance_id)
                if destroy_success:
                    result.steps_completed.append("destroy_source")
                    logger.info(f"[Migration] Source instance destroyed")
                else:
                    logger.warning(f"[Migration] Failed to destroy source instance (migration still successful)")

            result.success = True
            logger.info(f"[Migration] Migration completed successfully! New instance: {new_instance_id}")
            return result

        except MigrationException:
            raise
        except NotFoundException as e:
            result.error = str(e)
            raise MigrationException(f"Instance not found: {e}")
        except Exception as e:
            result.error = str(e)
            logger.error(f"[Migration] Unexpected error: {e}")
            raise MigrationException(f"Migration failed: {e}")

    def _wait_for_ssh_ready(self, instance_id: int, timeout: int = None) -> Optional[Any]:
        """
        Wait for instance SSH to be ready

        Args:
            instance_id: Instance ID
            timeout: Timeout in seconds

        Returns:
            Instance object or None if timeout
        """
        timeout = timeout or self.SSH_READY_TIMEOUT
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                instance = self.instances.get_instance(instance_id)
                if instance.is_running and instance.ssh_host and instance.ssh_port:
                    return instance
            except Exception as e:
                logger.debug(f"Waiting for SSH: {e}")

            time.sleep(5)

        return None

    def get_migration_estimate(
        self,
        source_instance_id: int,
        target_type: Literal["gpu", "cpu"],
        gpu_name: Optional[str] = None,
        max_price: float = 2.0,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get estimated cost and time for migration

        Args:
            source_instance_id: Source instance ID
            target_type: Target type
            gpu_name: GPU name if target is GPU
            max_price: Max price filter
            region: Region filter

        Returns:
            Dictionary with estimates
        """
        try:
            source = self.instances.get_instance(source_instance_id)

            # Search target offers
            if target_type == "cpu":
                offers = self.vast.search_cpu_offers(
                    max_price=max_price,
                    region=region,
                    limit=5,
                )
            else:
                offers = self.vast.search_offers(
                    gpu_name=gpu_name,
                    max_price=max_price,
                    region=region,
                    limit=5,
                )

            if not offers:
                return {
                    "available": False,
                    "error": f"No {target_type} offers found",
                }

            cheapest = offers[0]

            return {
                "available": True,
                "source": {
                    "id": source.id,
                    "type": "gpu" if source.num_gpus > 0 else "cpu",
                    "gpu_name": source.gpu_name,
                    "cost_per_hour": source.dph_total,
                },
                "target": {
                    "type": target_type,
                    "gpu_name": gpu_name if target_type == "gpu" else None,
                    "cost_per_hour": cheapest.get("dph_total", 0),
                    "offer_id": cheapest.get("id"),
                },
                "estimated_time_minutes": 5,  # Approximate
                "offers_available": len(offers),
            }

        except Exception as e:
            return {
                "available": False,
                "error": str(e),
            }
