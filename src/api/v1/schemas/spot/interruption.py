"""Schema para Interruption Rate."""
from pydantic import BaseModel, Field
from typing import List, Optional


class InterruptionRateItem(BaseModel):
    """Taxa de interrupção por provedor."""
    machine_id: int
    hostname: Optional[str] = None
    geolocation: Optional[str] = None
    gpu_name: Optional[str] = None
    interruption_rate: float = Field(..., ge=0, le=1, description="Taxa de interrupção (0-1)")
    avg_uptime_hours: float = Field(..., description="Tempo médio de uptime em horas")
    total_rentals: int
    successful_completions: int
    reliability_score: float = Field(..., ge=0, le=1)
    risk_level: str = Field(..., description="low, medium, high")


class InterruptionRateResponse(BaseModel):
    """Ranking de taxa de interrupção por provedor."""
    items: List[InterruptionRateItem]
    avg_interruption_rate: float
    safest_providers: int = Field(..., description="Provedores com rate < 5%")
    generated_at: str
