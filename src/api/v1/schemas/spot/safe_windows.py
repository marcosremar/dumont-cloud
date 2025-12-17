"""Schema para Safe Spot Windows."""
from pydantic import BaseModel, Field
from typing import List, Optional


class SafeSpotWindowItem(BaseModel):
    """Janela segura para usar spot."""
    hour_utc: int = Field(..., ge=0, le=23)
    day_of_week: str
    avg_interruption_rate: float
    avg_spot_price: float
    availability_score: float = Field(..., ge=0, le=1)
    recommendation: str = Field(..., description="highly_recommended, recommended, caution, avoid")


class SafeSpotWindowsResponse(BaseModel):
    """Janelas seguras para usar spot."""
    gpu_name: str
    windows: List[SafeSpotWindowItem]
    best_window: Optional[SafeSpotWindowItem] = None
    worst_window: Optional[SafeSpotWindowItem] = None
    overall_risk: str
    generated_at: str
