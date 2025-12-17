"""Schema para Spot Price Prediction."""
from pydantic import BaseModel, Field
from typing import List


class SpotPricePredictionItem(BaseModel):
    """Previsão de preço spot."""
    hour_utc: int
    predicted_price: float
    confidence: float
    predicted_availability: int
    recommendation: str


class SpotPricePredictionResponse(BaseModel):
    """Previsão de preços spot."""
    gpu_name: str
    current_price: float
    predictions_24h: List[SpotPricePredictionItem]
    best_time_to_rent: int = Field(..., description="Melhor hora UTC")
    predicted_lowest_price: float
    model_confidence: float
    generated_at: str
