"""Modelos de banco de dados."""

from .price_history import PriceHistory, PriceAlert
from .instance_status import InstanceStatus, HibernationEvent
from .metrics import MarketSnapshot, ProviderReliability, PricePrediction, CostEfficiencyRanking
from .machine_history import MachineAttempt, MachineBlacklist, MachineStats
from .currency import ExchangeRate, UserCurrencyPreference, SUPPORTED_CURRENCIES

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
    # Currency models for multi-currency pricing
    'ExchangeRate',
    'UserCurrencyPreference',
    'SUPPORTED_CURRENCIES',
]
