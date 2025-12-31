"""
Repository interfaces (abstractions for Dependency Inversion Principle)
"""
from .gpu_provider import IGpuProvider
from .snapshot_provider import ISnapshotProvider
from .user_repository import IUserRepository
from .team_repository import ITeamRepository
from .role_repository import IRoleRepository
from .audit_repository import IAuditRepository

__all__ = [
    'IGpuProvider',
    'ISnapshotProvider',
    'IUserRepository',
    'ITeamRepository',
    'IRoleRepository',
    'IAuditRepository',
]
