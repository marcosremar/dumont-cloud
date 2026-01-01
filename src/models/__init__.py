"""Modelos de banco de dados."""

from .price_history import PriceHistory, PriceAlert
from .instance_status import InstanceStatus, HibernationEvent
from .metrics import MarketSnapshot, ProviderReliability, PricePrediction, CostEfficiencyRanking
from .machine_history import MachineAttempt, MachineBlacklist, MachineStats
from .snapshot_config import SnapshotConfig
from .economy import SavingsHistory, ProviderPricing
from .user import User
from .email_verification_token import EmailVerificationToken
from .snapshot_metadata import SnapshotMetadata, SnapshotStatus, DeletionReason
from .email_preferences import EmailPreference
from .email_delivery_log import EmailDeliveryLog
from .shareable_report import ShareableReport
from .webhook_config import WebhookConfig, WebhookLog
from .cost_optimization import UsageMetrics
from .currency import ExchangeRate, UserCurrencyPreference, SUPPORTED_CURRENCIES
from .sso_config import SSOConfig, SSOUserMapping
from .rbac import (
    Team,
    Role,
    Permission,
    TeamMember,
    TeamInvitation,
    role_permissions,
    SYSTEM_ROLES,
    PERMISSIONS,
    ROLE_PERMISSIONS,
)
from .reservation import Reservation, ReservationStatus
from .reservation_credit import ReservationCredit, CreditStatus, CreditTransactionType

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
    # Snapshot lifecycle
    'SnapshotMetadata',
    'SnapshotStatus',
    'DeletionReason',
    # Email reports
    'EmailPreference',
    'EmailDeliveryLog',
    # Shareable reports
    'ShareableReport',
    # Webhook integrations
    'WebhookConfig',
    'WebhookLog',
    # Cost optimization models
    'UsageMetrics',
    # Currency models for multi-currency pricing
    'ExchangeRate',
    'UserCurrencyPreference',
    'SUPPORTED_CURRENCIES',
    # SSO Configuration
    'SSOConfig',
    'SSOUserMapping',
    # RBAC models
    'Team',
    'Role',
    'Permission',
    'TeamMember',
    'TeamInvitation',
    'role_permissions',
    'SYSTEM_ROLES',
    'PERMISSIONS',
    'ROLE_PERMISSIONS',
    # Reservation system models
    'Reservation',
    'ReservationStatus',
    'ReservationCredit',
    'CreditStatus',
    'CreditTransactionType',
]
