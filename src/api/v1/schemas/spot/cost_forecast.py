"""Schema para Cost Forecast - Previsao de custos 7 dias."""
from pydantic import BaseModel, Field
from typing import List, Optional


class HourlyPredictionItem(BaseModel):
    """Previsao de preco por hora."""
    hour: int = Field(..., ge=0, le=23, description="Hora do dia (0-23)")
    timestamp: str = Field(..., description="Timestamp ISO da previsao")
    price: float = Field(..., ge=0, description="Preco previsto $/hora")


class DailyCostForecastItem(BaseModel):
    """Previsao de custo diario."""
    day: str = Field(..., description="Data no formato YYYY-MM-DD")
    forecasted_cost: float = Field(..., ge=0, description="Custo previsto para o dia")
    confidence_interval: List[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Intervalo de confianca [lower, upper]"
    )
    avg_hourly_price: float = Field(..., ge=0, description="Preco medio por hora")
    hourly_predictions: List[HourlyPredictionItem] = Field(
        default_factory=list,
        description="Previsoes por hora"
    )


class CostForecastResponse(BaseModel):
    """Resposta completa do forecast de custos."""
    gpu_name: str = Field(..., description="Nome da GPU")
    machine_type: str = Field(default="interruptible", description="Tipo de maquina")
    usage_hours_per_day: float = Field(..., ge=0, le=24, description="Horas de uso por dia")
    daily_forecasts: List[DailyCostForecastItem] = Field(
        ...,
        description="Previsoes de custo para cada dia"
    )
    total_7day_cost: float = Field(..., ge=0, description="Custo total previsto para 7 dias")
    total_confidence_interval: List[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Intervalo de confianca total [lower, upper]"
    )
    best_day: Optional[str] = Field(None, description="Dia com menor custo previsto")
    lowest_daily_cost: Optional[float] = Field(None, ge=0, description="Menor custo diario previsto")
    model_confidence: float = Field(..., ge=0, le=1, description="Confianca do modelo (0-1)")
    generated_at: str = Field(..., description="Timestamp de geracao da previsao")


class CostForecastErrorResponse(BaseModel):
    """Resposta de erro para forecast."""
    error: str = Field(..., description="Mensagem de erro")
    required_data_points: int = Field(default=50, description="Minimo de pontos necessarios")
    available_data_points: Optional[int] = Field(None, description="Pontos disponiveis")
