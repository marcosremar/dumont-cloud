"""Schema para Fleet Strategy."""
from pydantic import BaseModel, Field
from typing import List


class FleetStrategyGpu(BaseModel):
    """GPU na estratégia de fleet."""
    gpu_name: str
    allocation_percent: float
    count: int
    spot_price: float
    reliability_score: float
    role: str = Field(..., description="primary, backup, burst")


class FleetStrategyResponse(BaseModel):
    """Estratégia de fleet spot."""
    strategy_name: str
    total_gpus: int
    estimated_monthly_cost: float
    estimated_savings_vs_ondemand: float
    interruption_resilience: str = Field(..., description="low, medium, high")
    gpus: List[FleetStrategyGpu]
    recommendations: List[str]
    generated_at: str
