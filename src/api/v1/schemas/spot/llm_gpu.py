"""Schema para Best GPU for LLM."""
from pydantic import BaseModel, Field
from typing import List, Optional


class LLMGpuItem(BaseModel):
    """GPU otimizada para LLM."""
    gpu_name: str
    vram_gb: float
    price_per_hour: float
    estimated_tokens_per_second: float
    cost_per_million_tokens: float
    recommended_models: List[str]
    efficiency_score: float = Field(..., ge=0, le=100)
    available_count: int
    machine_type: str


class BestGpuForLLMResponse(BaseModel):
    """Melhores GPUs para LLM por $/token."""
    items: List[LLMGpuItem]
    best_value: Optional[LLMGpuItem] = None
    best_performance: Optional[LLMGpuItem] = None
    generated_at: str
