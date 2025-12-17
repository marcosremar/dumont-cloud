"""
CPU Standby management API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel

from ..dependencies import require_auth, get_current_user_email
from ....services.standby_manager import get_standby_manager
from ....infrastructure.providers import FileUserRepository
from ....core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/standby", tags=["Standby"], dependencies=[Depends(require_auth)])


class StandbyConfigRequest(BaseModel):
    """Request to configure auto-standby"""
    enabled: bool = True
    gcp_zone: str = "europe-west1-b"
    gcp_machine_type: str = "e2-medium"
    gcp_disk_size: int = 100
    gcp_spot: bool = True
    sync_interval: int = 30
    auto_failover: bool = True
    auto_recovery: bool = True


class StandbyStatusResponse(BaseModel):
    """Status response for standby system"""
    configured: bool
    auto_standby_enabled: bool
    active_associations: int
    associations: Dict[str, Any]
    config: Dict[str, Any]


class StandbyAssociationResponse(BaseModel):
    """Response for a single standby association"""
    gpu_instance_id: int
    cpu_standby: Dict[str, Any]
    sync_enabled: bool
    state: Optional[str] = None
    sync_count: Optional[int] = None


@router.get("/status", response_model=StandbyStatusResponse)
async def get_standby_status():
    """
    Get status of the CPU standby system.

    Returns information about:
    - Whether auto-standby is configured and enabled
    - Active GPU ↔ CPU associations
    - Current configuration
    """
    manager = get_standby_manager()
    return manager.get_status()


@router.post("/configure")
async def configure_standby(
    request: StandbyConfigRequest,
    user_email: str = Depends(get_current_user_email),
):
    """
    Configure the auto-standby system.

    When enabled, creating a GPU instance will automatically:
    1. Provision a CPU standby VM in GCP
    2. Start syncing data GPU → CPU
    3. Enable automatic failover on GPU failure

    When a GPU is destroyed, its associated CPU standby is also destroyed.

    Requires GCP credentials to be configured in user settings.
    """
    # Get user's settings
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check for GCP credentials
    gcp_creds = user.settings.get("gcp_credentials")
    if not gcp_creds and request.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GCP credentials not configured. Please add gcp_credentials to your settings."
        )

    if not user.vast_api_key and request.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured."
        )

    # Configure the manager
    manager = get_standby_manager()

    if request.enabled:
        manager.configure(
            gcp_credentials=gcp_creds,
            vast_api_key=user.vast_api_key,
            auto_standby_enabled=True,
            config={
                'gcp_zone': request.gcp_zone,
                'gcp_machine_type': request.gcp_machine_type,
                'gcp_disk_size': request.gcp_disk_size,
                'gcp_spot': request.gcp_spot,
                'sync_interval': request.sync_interval,
                'auto_failover': request.auto_failover,
                'auto_recovery': request.auto_recovery,
            }
        )

        logger.info(f"Auto-standby enabled for user {user_email}")

        return {
            "success": True,
            "message": "Auto-standby enabled. New GPU instances will automatically have CPU backup.",
            "config": {
                "gcp_zone": request.gcp_zone,
                "gcp_machine_type": request.gcp_machine_type,
                "estimated_cost_monthly_usd": 7.20 if request.gcp_spot else 25.0,
            }
        }
    else:
        # Disable auto-standby
        manager._auto_standby_enabled = False
        logger.info(f"Auto-standby disabled for user {user_email}")

        return {
            "success": True,
            "message": "Auto-standby disabled. Existing associations will remain active.",
        }


@router.get("/associations")
async def list_associations():
    """
    List all active GPU ↔ CPU standby associations.

    Returns mapping of GPU instance IDs to their CPU standby info.
    """
    manager = get_standby_manager()
    return {
        "associations": manager.list_associations(),
        "count": len(manager._associations),
    }


@router.get("/associations/{gpu_instance_id}")
async def get_association(gpu_instance_id: int):
    """
    Get CPU standby association for a specific GPU.

    Returns details about the associated CPU standby, sync status, etc.
    """
    manager = get_standby_manager()
    association = manager.get_association(gpu_instance_id)

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No standby association for GPU {gpu_instance_id}"
        )

    return association


@router.post("/associations/{gpu_instance_id}/start-sync")
async def start_sync(gpu_instance_id: int):
    """
    Start synchronization for a GPU ↔ CPU standby pair.

    Begins continuous sync of /workspace from GPU to CPU.
    """
    manager = get_standby_manager()

    if gpu_instance_id not in manager._associations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No standby association for GPU {gpu_instance_id}"
        )

    success = manager.start_sync(gpu_instance_id)

    if success:
        return {
            "success": True,
            "message": f"Sync started for GPU {gpu_instance_id}",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start sync"
        )


@router.post("/associations/{gpu_instance_id}/stop-sync")
async def stop_sync(gpu_instance_id: int):
    """
    Stop synchronization for a GPU ↔ CPU standby pair.
    """
    manager = get_standby_manager()

    if gpu_instance_id not in manager._associations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No standby association for GPU {gpu_instance_id}"
        )

    success = manager.stop_sync(gpu_instance_id)

    return {
        "success": True,
        "message": f"Sync stopped for GPU {gpu_instance_id}",
    }


@router.delete("/associations/{gpu_instance_id}")
async def destroy_standby(
    gpu_instance_id: int,
    keep_gpu: bool = Query(True, description="Keep the GPU instance running"),
):
    """
    Destroy the CPU standby for a GPU instance.

    This removes the CPU standby VM and stops sync/failover.
    The GPU instance is kept running by default.
    """
    manager = get_standby_manager()

    if gpu_instance_id not in manager._associations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No standby association for GPU {gpu_instance_id}"
        )

    success = manager.on_gpu_destroyed(gpu_instance_id)

    if success:
        return {
            "success": True,
            "message": f"CPU standby for GPU {gpu_instance_id} destroyed",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to destroy CPU standby"
        )


@router.get("/pricing")
async def get_pricing(
    machine_type: str = Query("e2-medium", description="GCP machine type"),
    disk_gb: int = Query(100, description="Disk size in GB"),
    spot: bool = Query(True, description="Use Spot VM"),
):
    """
    Get estimated pricing for CPU standby.

    Returns estimated monthly cost for a CPU standby VM.
    """
    # Spot VM prices (approximate)
    spot_prices = {
        "e2-micro": 0.002,
        "e2-small": 0.005,
        "e2-medium": 0.010,
        "e2-standard-2": 0.020,
        "e2-standard-4": 0.040,
    }

    # On-demand prices (approximate)
    ondemand_prices = {
        "e2-micro": 0.008,
        "e2-small": 0.017,
        "e2-medium": 0.034,
        "e2-standard-2": 0.067,
        "e2-standard-4": 0.134,
    }

    prices = spot_prices if spot else ondemand_prices
    hourly = prices.get(machine_type, 0.010)
    monthly_vm = hourly * 720  # ~720 hours/month
    monthly_disk = disk_gb * 0.04  # $0.04/GB for standard disk

    return {
        "machine_type": machine_type,
        "disk_gb": disk_gb,
        "spot": spot,
        "estimated_hourly_usd": round(hourly, 4),
        "estimated_monthly_usd": round(monthly_vm + monthly_disk, 2),
        "breakdown": {
            "vm_monthly": round(monthly_vm, 2),
            "disk_monthly": round(monthly_disk, 2),
        },
        "note": "Prices are estimates and may vary by region."
    }
