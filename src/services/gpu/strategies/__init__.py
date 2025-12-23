"""
GPU Provisioning Strategies

Strategy Pattern for machine provisioning:
- RaceStrategy: Create multiple machines in parallel, first ready wins
- SingleStrategy: Create single machine and wait
- SpotStrategy: Use interruptible (spot) instances for cost savings

Usage:
    from src.services.gpu.strategies import RaceStrategy, MachineProvisionerService, ProvisionConfig

    config = ProvisionConfig(
        max_price=1.0,
        min_gpu_ram=10000,
        disk_space=50,
    )

    provisioner = MachineProvisionerService(api_key, strategy=RaceStrategy())
    result = provisioner.provision(config)
"""
from .base import (
    ProvisioningStrategy,
    ProvisionConfig,
    ProvisionResult,
    MachineCandidate,
)
from .race import RaceStrategy
from .single import SingleStrategy
from .service import MachineProvisionerService

__all__ = [
    "ProvisioningStrategy",
    "ProvisionConfig",
    "ProvisionResult",
    "MachineCandidate",
    "RaceStrategy",
    "SingleStrategy",
    "MachineProvisionerService",
]
