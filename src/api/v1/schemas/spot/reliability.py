"""Schema para Reliability Score."""
from pydantic import BaseModel, Field
from typing import List, Optional


class ReliabilityScoreItem(BaseModel):
    """Score de confiabilidade de provedor."""
    machine_id: int
    hostname: Optional[str] = None
    geolocation: Optional[str] = None
    gpu_name: Optional[str] = None
    overall_score: float = Field(..., ge=0, le=100)
    uptime_score: float = Field(..., ge=0, le=100)
    price_stability_score: float = Field(..., ge=0, le=100)
    performance_score: float = Field(..., ge=0, le=100)
    history_days: int
    total_rentals: int
    recommendation: str = Field(..., description="excellent, good, fair, poor")
    user_rating_count: Optional[int] = Field(default=0, ge=0, description="Number of user ratings")
    user_rating_average: Optional[float] = Field(default=None, ge=0, le=5, description="Average user rating (0-5 scale)")


class ReliabilityScoreResponse(BaseModel):
    """Scores de confiabilidade de provedores."""
    items: List[ReliabilityScoreItem]
    excellent_providers: int
    avg_score: float
    generated_at: str
