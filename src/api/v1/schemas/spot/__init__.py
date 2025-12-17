"""
Schemas Pydantic para relatórios Spot.

Organização modular por tipo de relatório.
"""
from .monitor import SpotPriceItem, SpotPriceMonitorResponse
from .savings import SavingsCalculatorItem, SavingsCalculatorResponse
from .interruption import InterruptionRateItem, InterruptionRateResponse
from .safe_windows import SafeSpotWindowItem, SafeSpotWindowsResponse
from .llm_gpu import LLMGpuItem, BestGpuForLLMResponse
from .prediction import SpotPricePredictionItem, SpotPricePredictionResponse
from .availability import InstantAvailabilityItem, InstantAvailabilityResponse
from .reliability import ReliabilityScoreItem, ReliabilityScoreResponse
from .training_cost import TrainingCostItem, TrainingCostResponse
from .fleet_strategy import FleetStrategyGpu, FleetStrategyResponse

__all__ = [
    # Monitor
    "SpotPriceItem",
    "SpotPriceMonitorResponse",
    # Savings
    "SavingsCalculatorItem",
    "SavingsCalculatorResponse",
    # Interruption
    "InterruptionRateItem",
    "InterruptionRateResponse",
    # Safe Windows
    "SafeSpotWindowItem",
    "SafeSpotWindowsResponse",
    # LLM GPU
    "LLMGpuItem",
    "BestGpuForLLMResponse",
    # Prediction
    "SpotPricePredictionItem",
    "SpotPricePredictionResponse",
    # Availability
    "InstantAvailabilityItem",
    "InstantAvailabilityResponse",
    # Reliability
    "ReliabilityScoreItem",
    "ReliabilityScoreResponse",
    # Training Cost
    "TrainingCostItem",
    "TrainingCostResponse",
    # Fleet Strategy
    "FleetStrategyGpu",
    "FleetStrategyResponse",
]
