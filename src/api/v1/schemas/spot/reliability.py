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


class UptimeHistoryItem(BaseModel):
    """Item de histórico de uptime diário."""
    date: str = Field(..., description="Data no formato YYYY-MM-DD")
    uptime_percentage: float = Field(..., ge=0, le=100, description="Percentual de uptime no dia")
    interruption_count: int = Field(..., ge=0, description="Número de interrupções no dia")
    uptime_seconds: Optional[int] = Field(default=None, description="Segundos de uptime no dia")
    avg_interruption_duration: Optional[float] = Field(default=None, description="Duração média de interrupções em segundos")


class UptimeHistoryResponse(BaseModel):
    """Resposta do histórico de uptime de uma máquina."""
    machine_id: str
    provider: str
    days_requested: int
    total_records: int
    history: List[UptimeHistoryItem]
    summary: Optional[dict] = Field(default=None, description="Resumo estatístico do período")
    generated_at: str


class MachineRatingRequest(BaseModel):
    """Request para avaliar uma máquina."""
    rating: int = Field(..., ge=1, le=5, description="Avaliação de 1-5 estrelas")
    comment: Optional[str] = Field(default=None, max_length=1000, description="Comentário opcional")
    rental_duration_hours: Optional[float] = Field(default=None, ge=0, description="Duração do aluguel em horas")
    instance_id: Optional[str] = Field(default=None, description="ID da instância relacionada")
    provider: str = Field(default="vast", description="Provider da máquina")


class MachineRatingResponse(BaseModel):
    """Response após submeter uma avaliação."""
    id: int
    machine_id: str
    provider: str
    user_id: str
    rating: int
    comment: Optional[str]
    created_at: str
    message: str = "Rating submitted successfully"
