"""
Schemas Pydantic para endpoints de métricas de mercado VAST.ai.

Os schemas de relatórios Spot estão em schemas/spot/ (modular)
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


class MarketSnapshotResponse(BaseModel):
    """Snapshot de mercado para uma GPU/tipo."""
    timestamp: str
    gpu_name: str
    machine_type: str
    min_price: float
    max_price: float
    avg_price: float
    median_price: float
    total_offers: int
    available_gpus: int
    verified_offers: int = 0
    avg_reliability: Optional[float] = None
    avg_total_flops: Optional[float] = None
    avg_dlperf: Optional[float] = None
    min_cost_per_tflops: Optional[float] = None
    avg_cost_per_tflops: Optional[float] = None
    region_distribution: Optional[Dict[str, int]] = None

    class Config:
        from_attributes = True


class MarketTypeSummary(BaseModel):
    """Resumo de mercado para um tipo de máquina."""
    current_avg_price: float
    current_min_price: float
    total_offers: int
    available_gpus: int
    avg_reliability: Optional[float] = None
    min_cost_per_tflops: Optional[float] = None
    trend_24h: Optional[Dict[str, Any]] = None
    last_update: str


class MarketSummaryResponse(BaseModel):
    """Resumo de mercado comparando tipos de máquina para uma GPU."""
    gpu_name: str
    types: Dict[str, MarketTypeSummary]
    spot_savings_percent: Optional[float] = Field(
        None,
        description="Economia percentual ao usar spot vs on-demand"
    )
    generated_at: str


class ProviderRankingResponse(BaseModel):
    """Ranking de provedor por confiabilidade."""
    machine_id: int
    hostname: Optional[str] = None
    geolocation: Optional[str] = None
    gpu_name: Optional[str] = None
    verified: bool = False
    reliability_score: float = Field(..., ge=0, le=1)
    availability_score: float = Field(0, ge=0, le=1)
    price_stability_score: float = Field(0, ge=0, le=1)
    total_observations: int = 0
    avg_price: Optional[float] = None
    min_price_seen: Optional[float] = None
    max_price_seen: Optional[float] = None
    avg_total_flops: Optional[float] = None
    avg_dlperf: Optional[float] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None

    class Config:
        from_attributes = True


class EfficiencyRankingResponse(BaseModel):
    """Ranking de eficiência de custo-benefício."""
    rank: int = Field(..., description="Ranking geral")
    rank_in_class: Optional[int] = Field(None, description="Ranking dentro da classe de GPU")
    offer_id: int
    gpu_name: str
    machine_type: str
    dph_total: float = Field(..., description="Preço por hora em USD")
    total_flops: Optional[float] = Field(None, description="TFLOPS total")
    gpu_ram: Optional[float] = Field(None, description="RAM da GPU em GB")
    dlperf: Optional[float] = Field(None, description="Deep Learning Performance score")
    cost_per_tflops: Optional[float] = Field(None, description="USD por TFLOPS")
    cost_per_gb_vram: Optional[float] = Field(None, description="USD por GB de VRAM")
    efficiency_score: float = Field(..., ge=0, le=100, description="Score de eficiência (0-100)")
    reliability: Optional[float] = Field(None, ge=0, le=1)
    verified: bool = False
    geolocation: Optional[str] = None

    class Config:
        from_attributes = True


class PricePredictionResponse(BaseModel):
    """Previsão de preços para uma GPU."""
    gpu_name: str
    machine_type: str
    hourly_predictions: Dict[str, float] = Field(
        ...,
        description="Previsões por hora UTC (0-23)"
    )
    daily_predictions: Dict[str, float] = Field(
        ...,
        description="Previsões por dia da semana"
    )
    best_hour_utc: int = Field(..., ge=0, le=23, description="Melhor hora UTC para alugar")
    best_day: str = Field(..., description="Melhor dia da semana")
    predicted_min_price: float = Field(..., description="Preço mínimo previsto")
    model_confidence: float = Field(..., ge=0, le=1, description="Confiança do modelo")
    model_version: str
    valid_until: str
    created_at: Optional[str] = None


class GpuComparisonItem(BaseModel):
    """Item de comparação de GPU."""
    gpu_name: str
    avg_price: float
    min_price: float
    total_offers: int
    avg_reliability: Optional[float] = None
    min_cost_per_tflops: Optional[float] = None
    avg_total_flops: Optional[float] = None


class ComparisonResponse(BaseModel):
    """Comparação entre múltiplas GPUs."""
    machine_type: str
    gpus: List[GpuComparisonItem]
    cheapest: Optional[GpuComparisonItem] = Field(None, description="GPU mais barata")
    best_value: Optional[GpuComparisonItem] = Field(None, description="Melhor custo-benefício")
    generated_at: str


class MarketStatsRequest(BaseModel):
    """Request para estatísticas de mercado."""
    gpu_name: Optional[str] = None
    machine_type: Optional[str] = Field(None, description="on-demand, interruptible, bid")
    hours: int = Field(24, ge=1, le=168, description="Horas de histórico")
    limit: int = Field(100, le=1000)


class ProviderFilterRequest(BaseModel):
    """Request para filtrar provedores."""
    geolocation: Optional[str] = None
    gpu_name: Optional[str] = None
    verified_only: bool = False
    min_observations: int = Field(10, ge=1)
    min_reliability: float = Field(0.0, ge=0, le=1)


class EfficiencyFilterRequest(BaseModel):
    """Request para filtrar rankings de eficiência."""
    gpu_name: Optional[str] = None
    machine_type: Optional[str] = None
    verified_only: bool = False
    min_reliability: float = Field(0.0, ge=0, le=1)
    max_price: Optional[float] = Field(None, description="Preço máximo por hora")
    geolocation: Optional[str] = None
