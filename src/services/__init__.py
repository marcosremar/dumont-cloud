"""Dumont Cloud Services"""

# GPU services
from .gpu import (
    GPUProvisioner,
    provision_gpu_fast,
    ProvisionResult,
    GPUSnapshotService,
    GPUAdvisor,
    GPUCheckpointService,
    GPUMonitorAgent,
    VastAIService,
)

# Storage services
from .storage import (
    ResticService,
    create_snapshot_service_b2,
    create_snapshot_service_r2,
    create_snapshot_service_default,
)

# Standby services
from .standby import CPUStandbyService, StandbyManager, AutoHibernationManager

# Warm Pool services
from .warmpool import (
    WarmPoolManager,
    WarmPoolState,
    get_warm_pool_manager,
    HostFinder,
    MultiGPUHost,
    VolumeService,
    # Regional Volume Failover
    RegionalVolumeFailover,
    RegionalVolumeInfo,
    RegionalFailoverResult,
    get_regional_volume_failover,
    # Cloud Storage Failover (Backblaze B2, R2, S3)
    CloudStorageFailover,
    CloudStorageConfig,
    CloudStorageType,
    CloudFailoverResult,
    MountMethod,
    create_b2_failover,
    create_r2_failover,
)

# Failover Orchestrator
from .failover_orchestrator import (
    FailoverOrchestrator,
    OrchestratedFailoverResult,
    get_failover_orchestrator,
    execute_orchestrated_failover,
)

# Other services
from .deploy_wizard import DeployWizardService, DeployConfig, get_wizard_service

__all__ = [
    # GPU
    "GPUProvisioner",
    "provision_gpu_fast",
    "ProvisionResult",
    "GPUSnapshotService",
    "GPUAdvisor",
    "GPUCheckpointService",
    "GPUMonitorAgent",
    "VastAIService",
    # Storage
    "ResticService",
    "create_snapshot_service_b2",
    "create_snapshot_service_r2",
    "create_snapshot_service_default",
    # Standby
    "CPUStandbyService",
    "StandbyManager",
    "AutoHibernationManager",
    # Warm Pool
    "WarmPoolManager",
    "WarmPoolState",
    "get_warm_pool_manager",
    "HostFinder",
    "MultiGPUHost",
    "VolumeService",
    # Regional Volume Failover
    "RegionalVolumeFailover",
    "RegionalVolumeInfo",
    "RegionalFailoverResult",
    "get_regional_volume_failover",
    # Cloud Storage Failover (Backblaze B2, R2, S3)
    "CloudStorageFailover",
    "CloudStorageConfig",
    "CloudStorageType",
    "CloudFailoverResult",
    "MountMethod",
    "create_b2_failover",
    "create_r2_failover",
    # Failover Orchestrator
    "FailoverOrchestrator",
    "OrchestratedFailoverResult",
    "get_failover_orchestrator",
    "execute_orchestrated_failover",
    # Other
    "DeployWizardService",
    "DeployConfig",
    "get_wizard_service",
]
