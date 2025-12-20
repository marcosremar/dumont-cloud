"""
GPU Warm Pool Service - Estrategia principal de failover.

Utiliza multiplas GPUs do mesmo host fisico no VAST.ai,
compartilhando um Volume persistente para failover em 30-60 segundos.
"""
from .manager import WarmPoolManager, WarmPoolState, WarmPoolStatus, get_warm_pool_manager
from .host_finder import HostFinder, MultiGPUHost
from .volume_service import VolumeService
from .regional_volume_failover import (
    RegionalVolumeFailover,
    RegionalVolumeInfo,
    RegionalFailoverResult,
    RegionalFailoverState,
    get_regional_volume_failover,
)
from .cloud_storage_failover import (
    CloudStorageFailover,
    CloudStorageConfig,
    CloudStorageType,
    CloudFailoverResult,
    MountMethod,
    create_b2_failover,
    create_r2_failover,
)

__all__ = [
    'WarmPoolManager',
    'WarmPoolState',
    'WarmPoolStatus',
    'get_warm_pool_manager',
    'HostFinder',
    'MultiGPUHost',
    'VolumeService',
    # Regional Volume Failover
    'RegionalVolumeFailover',
    'RegionalVolumeInfo',
    'RegionalFailoverResult',
    'RegionalFailoverState',
    'get_regional_volume_failover',
    # Cloud Storage Failover (Backblaze B2, R2, S3)
    'CloudStorageFailover',
    'CloudStorageConfig',
    'CloudStorageType',
    'CloudFailoverResult',
    'MountMethod',
    'create_b2_failover',
    'create_r2_failover',
]
