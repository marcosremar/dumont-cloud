"""
Instance management API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from typing import Optional

from ..schemas.request import SearchOffersRequest, CreateInstanceRequest, MigrateInstanceRequest, MigrationEstimateRequest

logger = logging.getLogger(__name__)
from ..schemas.response import (
    SearchOffersResponse,
    GpuOfferResponse,
    ListInstancesResponse,
    InstanceResponse,
    SuccessResponse,
    MigrationResponse,
    MigrationEstimateResponse,
    SyncResponse,
    SyncStatusResponse,
)
from ....domain.services import InstanceService, MigrationService, SyncService
from ....core.exceptions import NotFoundException, VastAPIException, MigrationException
from ..dependencies import get_instance_service, get_migration_service, get_sync_service, require_auth
from ....services.standby_manager import get_standby_manager

router = APIRouter(prefix="/instances", tags=["Instances"], dependencies=[Depends(require_auth)])


@router.get("/offers", response_model=SearchOffersResponse)
async def search_offers(
    gpu_name: Optional[str] = Query(None, description="Filter by GPU model (e.g., RTX_4090, A100)"),
    num_gpus: int = Query(1, ge=1, le=8, description="Number of GPUs"),
    min_gpu_ram: float = Query(0, description="Minimum GPU RAM in GB"),
    min_cpu_cores: int = Query(1, description="Minimum CPU cores"),
    min_cpu_ram: float = Query(1, description="Minimum CPU RAM in GB"),
    min_disk: float = Query(50, description="Minimum disk space in GB"),
    min_inet_down: float = Query(100, description="Minimum download speed in Mbps"),
    min_inet_up: float = Query(100, description="Minimum upload speed in Mbps"),
    max_price: float = Query(10.0, description="Maximum price per hour in USD"),
    min_reliability: float = Query(0.0, ge=0, le=1, description="Minimum reliability score (0-1)"),
    region: Optional[str] = Query(None, description="Region filter: US, EU, ASIA"),
    verified_only: bool = Query(False, description="Only verified hosts"),
    static_ip: bool = Query(False, description="Require static IP"),
    cuda_version: Optional[str] = Query(None, description="Minimum CUDA version"),
    order_by: str = Query("dph_total", description="Order by field: dph_total, gpu_ram, reliability"),
    limit: int = Query(50, le=100, description="Maximum results"),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Search available GPU offers with advanced filters

    Returns list of available GPU instances matching filters.
    Supports filtering by GPU specs, network, price, reliability and more.
    """
    offers = instance_service.search_offers(
        gpu_name=gpu_name,
        num_gpus=num_gpus,
        min_gpu_ram=min_gpu_ram,
        min_cpu_cores=min_cpu_cores,
        min_cpu_ram=min_cpu_ram,
        max_price=max_price,
        region=region,
        min_disk=min_disk,
        min_inet_down=min_inet_down,
        min_reliability=min_reliability,
        verified_only=verified_only,
        static_ip=static_ip,
        limit=limit,
    )

    offer_responses = [
        GpuOfferResponse(
            id=offer.id,
            gpu_name=offer.gpu_name,
            num_gpus=offer.num_gpus,
            gpu_ram=offer.gpu_ram,
            cpu_cores=offer.cpu_cores,
            cpu_ram=offer.cpu_ram,
            disk_space=offer.disk_space,
            inet_down=offer.inet_down,
            inet_up=offer.inet_up,
            dph_total=offer.dph_total,
            geolocation=offer.geolocation,
            reliability=offer.reliability,
            cuda_version=offer.cuda_version,
            verified=offer.verified,
            static_ip=offer.static_ip,
        )
        for offer in offers
    ]

    return SearchOffersResponse(offers=offer_responses, count=len(offer_responses))


@router.get("", response_model=ListInstancesResponse)
async def list_instances(
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    List all user instances

    Returns all GPU instances owned by the user.
    """
    instances = instance_service.list_instances()

    instance_responses = [
        InstanceResponse(
            id=inst.id,
            status=inst.status,
            actual_status=inst.actual_status,
            gpu_name=inst.gpu_name,
            num_gpus=inst.num_gpus,
            gpu_ram=inst.gpu_ram,
            cpu_cores=inst.cpu_cores,
            cpu_ram=inst.cpu_ram,
            disk_space=inst.disk_space,
            dph_total=inst.dph_total,
            public_ipaddr=inst.public_ipaddr,
            ssh_host=inst.ssh_host,
            ssh_port=inst.ssh_port,
            start_date=inst.start_date.isoformat() if inst.start_date else None,
            label=inst.label,
            ports=inst.ports,
            gpu_util=inst.gpu_util,
            gpu_temp=inst.gpu_temp,
            cpu_util=inst.cpu_util,
            ram_used=inst.ram_used,
            ram_total=inst.ram_total,
        )
        for inst in instances
    ]

    return ListInstancesResponse(instances=instance_responses, count=len(instance_responses))


@router.post("", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    request: CreateInstanceRequest,
    background_tasks: BackgroundTasks,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Create a new GPU instance

    Creates instance from a GPU offer.
    If auto-standby is enabled, also creates a CPU standby for failover.
    """
    try:
        instance = instance_service.create_instance(
            offer_id=request.offer_id,
            image=request.image,
            disk_size=request.disk_size,
            label=request.label,
            ports=request.ports,
        )

        # Auto-criar CPU standby em background (não bloqueia resposta)
        standby_manager = get_standby_manager()
        if standby_manager.is_auto_standby_enabled():
            logger.info(f"Scheduling CPU standby creation for GPU {instance.id}")
            background_tasks.add_task(
                standby_manager.on_gpu_created,
                gpu_instance_id=instance.id,
                label=request.label
            )

        return InstanceResponse(
            id=instance.id,
            status=instance.status,
            actual_status=instance.actual_status,
            gpu_name=instance.gpu_name,
            num_gpus=instance.num_gpus,
            gpu_ram=instance.gpu_ram,
            cpu_cores=instance.cpu_cores,
            cpu_ram=instance.cpu_ram,
            disk_space=instance.disk_space,
            dph_total=instance.dph_total,
            public_ipaddr=instance.public_ipaddr,
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            label=instance.label,
            ports=instance.ports,
        )
    except VastAPIException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Get instance details

    Returns detailed information about a specific instance.
    """
    try:
        instance = instance_service.get_instance(instance_id)

        return InstanceResponse(
            id=instance.id,
            status=instance.status,
            actual_status=instance.actual_status,
            gpu_name=instance.gpu_name,
            num_gpus=instance.num_gpus,
            gpu_ram=instance.gpu_ram,
            cpu_cores=instance.cpu_cores,
            cpu_ram=instance.cpu_ram,
            disk_space=instance.disk_space,
            dph_total=instance.dph_total,
            public_ipaddr=instance.public_ipaddr,
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            start_date=instance.start_date.isoformat() if instance.start_date else None,
            label=instance.label,
            ports=instance.ports,
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{instance_id}", response_model=SuccessResponse)
async def destroy_instance(
    instance_id: int,
    background_tasks: BackgroundTasks,
    destroy_standby: bool = Query(True, description="Also destroy associated CPU standby"),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Destroy an instance

    Permanently deletes a GPU instance.
    If destroy_standby=true (default), also destroys the associated CPU standby.
    """
    success = instance_service.destroy_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to destroy instance {instance_id}",
        )

    # Destruir CPU standby associado em background
    if destroy_standby:
        standby_manager = get_standby_manager()
        if standby_manager.get_association(instance_id):
            logger.info(f"Scheduling CPU standby destruction for GPU {instance_id}")
            background_tasks.add_task(
                standby_manager.on_gpu_destroyed,
                gpu_instance_id=instance_id
            )

    return SuccessResponse(
        success=True,
        message=f"Instance {instance_id} destroyed successfully",
    )


@router.post("/{instance_id}/pause", response_model=SuccessResponse)
async def pause_instance(
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Pause an instance

    Pauses a running instance without destroying it.
    """
    success = instance_service.pause_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause instance {instance_id}",
        )

    return SuccessResponse(
        success=True,
        message=f"Instance {instance_id} paused successfully",
    )


@router.post("/{instance_id}/resume", response_model=SuccessResponse)
async def resume_instance(
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Resume a paused instance

    Resumes a previously paused instance.
    """
    success = instance_service.resume_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume instance {instance_id}",
        )

    return SuccessResponse(
        success=True,
        message=f"Instance {instance_id} resumed successfully",
    )


@router.post("/{instance_id}/migrate", response_model=MigrationResponse)
async def migrate_instance(
    instance_id: int,
    request: MigrateInstanceRequest,
    migration_service: MigrationService = Depends(get_migration_service),
):
    """
    Migrate instance between GPU and CPU

    Migrates an instance from GPU to CPU or vice-versa.
    Creates a snapshot, provisions new instance, restores snapshot,
    and optionally destroys the source instance.
    """
    # Validate target_type
    if request.target_type not in ["gpu", "cpu"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_type must be 'gpu' or 'cpu'",
        )

    # Validate gpu_name for GPU migration
    if request.target_type == "gpu" and not request.gpu_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="gpu_name is required for GPU migration",
        )

    try:
        result = migration_service.migrate_instance(
            source_instance_id=instance_id,
            target_type=request.target_type,
            gpu_name=request.gpu_name,
            max_price=request.max_price,
            region=request.region,
            disk_size=request.disk_size,
            auto_destroy_source=request.auto_destroy_source,
        )

        return MigrationResponse(
            success=result.success,
            new_instance_id=result.new_instance_id,
            old_instance_id=result.old_instance_id,
            snapshot_id=result.snapshot_id,
            error=result.error,
            steps_completed=result.steps_completed,
        )

    except MigrationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{instance_id}/migrate/estimate", response_model=MigrationEstimateResponse)
async def estimate_migration(
    instance_id: int,
    request: MigrationEstimateRequest,
    migration_service: MigrationService = Depends(get_migration_service),
):
    """
    Get migration estimate

    Returns estimated cost and availability for migrating an instance.
    """
    # Validate target_type
    if request.target_type not in ["gpu", "cpu"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_type must be 'gpu' or 'cpu'",
        )

    estimate = migration_service.get_migration_estimate(
        source_instance_id=instance_id,
        target_type=request.target_type,
        gpu_name=request.gpu_name,
        max_price=request.max_price,
        region=request.region,
    )

    return MigrationEstimateResponse(**estimate)


@router.post("/{instance_id}/sync", response_model=SyncResponse)
async def sync_instance(
    instance_id: int,
    force: bool = Query(False, description="Force sync even if recently synced"),
    source_path: str = Query("/workspace", description="Path to sync"),
    sync_service: SyncService = Depends(get_sync_service),
):
    """
    Perform incremental sync for an instance

    Uses Restic's deduplication to only upload changed data.
    After first sync, subsequent syncs are typically 10-100x faster.

    Returns detailed statistics about what was synced.
    """
    result = sync_service.sync_instance(
        instance_id=instance_id,
        source_path=source_path,
        force=force,
    )

    # Format data_added for human readability
    data_added = sync_service._format_bytes(result.data_added_bytes)

    return SyncResponse(
        success=result.success,
        instance_id=result.instance_id,
        snapshot_id=result.snapshot_id,
        files_new=result.files_new,
        files_changed=result.files_changed,
        files_unmodified=result.files_unmodified,
        data_added=data_added,
        data_added_bytes=result.data_added_bytes,
        duration_seconds=result.duration_seconds,
        is_incremental=result.is_incremental,
        error=result.error,
    )


@router.get("/{instance_id}/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    instance_id: int,
    sync_service: SyncService = Depends(get_sync_service),
):
    """
    Get sync status for an instance

    Returns information about last sync, current sync state,
    and statistics from the most recent sync operation.
    """
    stats = sync_service.get_sync_stats(instance_id)

    return SyncStatusResponse(
        instance_id=stats["instance_id"],
        synced=stats["synced"],
        is_syncing=stats.get("is_syncing", False),
        last_sync=stats.get("last_sync"),
        last_sync_ago=stats.get("last_sync_ago", "Never"),
        last_snapshot_id=stats.get("last_snapshot_id"),
        sync_count=stats.get("sync_count", 0),
        last_stats=stats.get("last_stats"),
        error=stats.get("error"),
    )
