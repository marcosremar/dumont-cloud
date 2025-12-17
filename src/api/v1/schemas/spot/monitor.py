"""Schema para Spot Price Monitor."""
from pydantic import BaseModel, Field
from typing import List, Optional


class SpotPriceItem(BaseModel):
    """Item de preço spot em tempo real."""
    gpu_name: str
    spot_price: float = Field(..., description="Preço spot atual")
    ondemand_price: float = Field(..., description="Preço on-demand para comparação")
    savings_percent: float = Field(..., description="Economia percentual")
    available_gpus: int = Field(..., description="GPUs disponíveis")
    total_offers: int = Field(..., description="Total de ofertas")
    price_trend: str = Field(..., description="Tendência: up, down, stable")
    min_price: float = Field(..., description="Menor preço encontrado")
    last_update: str


class SpotPriceMonitorResponse(BaseModel):
    """Monitor de preços spot em tempo real."""
    items: List[SpotPriceItem]
    total_gpus_monitored: int
    avg_savings_percent: float
    best_deal: Optional[SpotPriceItem] = None
    generated_at: str
