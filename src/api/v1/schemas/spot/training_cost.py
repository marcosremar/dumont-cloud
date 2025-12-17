"""Schema para Training Cost."""
from pydantic import BaseModel, Field
from typing import List, Optional


class TrainingCostItem(BaseModel):
    """Custo por hora de treinamento."""
    gpu_name: str
    vram_gb: float
    tflops: float
    spot_price: float
    ondemand_price: float
    cost_per_training_hour_spot: float
    cost_per_training_hour_ondemand: float
    estimated_epoch_time_minutes: float
    efficiency_rating: str = Field(..., description="excellent, good, fair, poor")
    recommended_batch_size: int
    available_count: int


class TrainingCostResponse(BaseModel):
    """Custo por hora de treinamento."""
    items: List[TrainingCostItem]
    most_cost_effective: Optional[TrainingCostItem] = None
    fastest_training: Optional[TrainingCostItem] = None
    generated_at: str
