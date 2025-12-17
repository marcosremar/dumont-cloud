"""Schema para Savings Calculator."""
from pydantic import BaseModel, Field
from typing import List


class SavingsCalculatorItem(BaseModel):
    """Item de cálculo de economia spot vs on-demand."""
    gpu_name: str
    spot_price: float
    ondemand_price: float
    savings_per_hour: float
    savings_percent: float
    savings_per_day: float
    savings_per_week: float
    savings_per_month: float
    spot_available: int
    reliability_risk: str = Field(..., description="low, medium, high")


class SavingsCalculatorResponse(BaseModel):
    """Calculadora de economia spot vs on-demand."""
    items: List[SavingsCalculatorItem]
    total_potential_savings_month: float
    avg_savings_percent: float
    generated_at: str
