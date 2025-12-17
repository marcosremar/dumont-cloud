"""Schema para Instant Availability."""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class InstantAvailabilityItem(BaseModel):
    """Disponibilidade instantânea de spot."""
    gpu_name: str
    available_now: int
    spot_price: float
    time_to_provision: str = Field(..., description="Tempo estimado para provisionar")
    regions: Dict[str, int] = Field(..., description="Disponibilidade por região")
    verified_count: int
    best_offer_id: Optional[int] = None


class InstantAvailabilityResponse(BaseModel):
    """Disponibilidade instantânea de GPUs spot."""
    items: List[InstantAvailabilityItem]
    total_available: int
    fastest_gpu: Optional[str] = None
    generated_at: str
