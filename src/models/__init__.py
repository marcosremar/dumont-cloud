"""Modelos de banco de dados."""

from .price_history import PriceHistory, PriceAlert
from .instance_status import InstanceStatus, HibernationEvent
from .metrics import MarketSnapshot, ProviderReliability, PricePrediction, CostEfficiencyRanking
from .machine_history import MachineAttempt, MachineBlacklist, MachineStats
from .snapshot_config import SnapshotConfig
from .economy import SavingsHistory, ProviderPricing
from .user import User
from .email_verification_token import EmailVerificationToken

__all__ = [
    'PriceHistory',
    'PriceAlert',
    'InstanceStatus',
    'HibernationEvent',
    # Novos modelos de métricas expandidas
    'MarketSnapshot',
    'ProviderReliability',
    'PricePrediction',
    'CostEfficiencyRanking',
    # Machine history e blacklist
    'MachineAttempt',
    'MachineBlacklist',
    'MachineStats',
    # Snapshot scheduling
    'SnapshotConfig',
    # Economy widget models
    'SavingsHistory',
    'ProviderPricing',
    # User model with trial support
    'User',
    # Email verification token
    'EmailVerificationToken',
]
