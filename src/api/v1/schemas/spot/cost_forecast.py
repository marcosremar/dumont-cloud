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


class OptimalTimingRequest(BaseModel):
    """Request para recomendacao de timing otimo."""
    gpu_name: str = Field(..., description="Nome da GPU (ex: RTX 4090, A100)")
    job_duration_hours: float = Field(
        ...,
        gt=0,
        le=168,
        description="Duracao do job em horas (max 7 dias)"
    )
    machine_type: str = Field(
        default="interruptible",
        description="Tipo de maquina (interruptible ou on-demand)"
    )


class TimeWindowItem(BaseModel):
    """Janela de tempo recomendada."""
    rank: int = Field(..., ge=1, description="Ranking da recomendacao (1=melhor)")
    start_time: str = Field(..., description="Horario de inicio recomendado (ISO format)")
    end_time: str = Field(..., description="Horario de fim estimado (ISO format)")
    estimated_cost: float = Field(..., ge=0, description="Custo estimado em $")
    avg_hourly_price: float = Field(..., ge=0, description="Preco medio por hora $")
    savings_vs_worst: float = Field(..., description="Economia vs pior horario em $")
    savings_percentage: float = Field(..., description="Percentual de economia vs pior horario")
    confidence: float = Field(..., ge=0, le=1, description="Confianca da recomendacao (0-1)")
    recommendation: str = Field(..., description="Tipo de recomendacao: excellent, good, fair")


class OptimalTimingResponse(BaseModel):
    """Resposta com recomendacoes de timing otimo."""
    gpu_name: str = Field(..., description="Nome da GPU")
    machine_type: str = Field(default="interruptible", description="Tipo de maquina")
    job_duration_hours: float = Field(..., description="Duracao do job em horas")
    current_price: float = Field(..., ge=0, description="Preco atual $/hora")
    time_windows: List[TimeWindowItem] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Top janelas de tempo recomendadas"
    )
    worst_time_cost: float = Field(..., ge=0, description="Custo no pior horario $")
    best_time_cost: float = Field(..., ge=0, description="Custo no melhor horario $")
    max_potential_savings: float = Field(..., ge=0, description="Economia maxima possivel $")
    model_confidence: float = Field(..., ge=0, le=1, description="Confianca do modelo (0-1)")
    generated_at: str = Field(..., description="Timestamp de geracao")


class HourlyAccuracyItem(BaseModel):
    """Metricas de acuracia por hora."""
    mape: float = Field(..., ge=0, description="MAPE para esta hora")
    num_samples: int = Field(..., ge=0, description="Numero de amostras")


class DailyAccuracyItem(BaseModel):
    """Metricas de acuracia por dia da semana."""
    mape: float = Field(..., ge=0, description="MAPE para este dia")
    num_samples: int = Field(..., ge=0, description="Numero de amostras")


class ForecastAccuracyResponse(BaseModel):
    """Resposta com metricas de acuracia do modelo de previsao."""
    gpu_name: str = Field(..., description="Nome da GPU")
    machine_type: str = Field(default="interruptible", description="Tipo de maquina")
    mape: float = Field(..., ge=0, description="Mean Absolute Percentage Error (%)")
    mae: float = Field(..., ge=0, description="Mean Absolute Error ($/hora)")
    rmse: float = Field(..., ge=0, description="Root Mean Square Error ($/hora)")
    r_squared: Optional[float] = Field(None, ge=0, le=1, description="Coeficiente de determinacao R2")
    num_predictions: int = Field(..., ge=0, description="Numero de previsoes avaliadas")
    num_actual_values: int = Field(..., ge=0, description="Numero de valores reais")
    num_samples: int = Field(..., ge=0, description="Numero de amostras pareadas")
    evaluation_period_days: int = Field(default=30, description="Periodo de avaliacao em dias")
    evaluation_start: str = Field(..., description="Inicio do periodo de avaliacao (ISO)")
    evaluation_end: str = Field(..., description="Fim do periodo de avaliacao (ISO)")
    hourly_accuracy: dict = Field(default_factory=dict, description="Acuracia por hora do dia")
    daily_accuracy: dict = Field(default_factory=dict, description="Acuracia por dia da semana")
    model_version: str = Field(..., description="Versao do modelo")
    generated_at: str = Field(..., description="Timestamp de geracao")


# ============================================================================
# Budget Alert Schemas
# ============================================================================


class BudgetAlertCreate(BaseModel):
    """Request para criar alerta de orcamento."""
    gpu_name: Optional[str] = Field(
        None,
        description="Nome da GPU (opcional, null = todos os GPUs)"
    )
    threshold: float = Field(
        ...,
        gt=0,
        description="Valor limite de orcamento em $ para 7 dias"
    )
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Email para receber alertas"
    )
    machine_type: str = Field(
        default="interruptible",
        description="Tipo de maquina (interruptible ou on-demand)"
    )
    alert_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Nome amigavel do alerta (opcional)"
    )
    enabled: bool = Field(
        default=True,
        description="Alerta ativo"
    )


class BudgetAlertUpdate(BaseModel):
    """Request para atualizar alerta de orcamento."""
    gpu_name: Optional[str] = Field(
        None,
        description="Nome da GPU (null = todos os GPUs)"
    )
    threshold: Optional[float] = Field(
        None,
        gt=0,
        description="Valor limite de orcamento em $ para 7 dias"
    )
    email: Optional[str] = Field(
        None,
        min_length=5,
        max_length=255,
        description="Email para receber alertas"
    )
    machine_type: Optional[str] = Field(
        None,
        description="Tipo de maquina (interruptible ou on-demand)"
    )
    alert_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Nome amigavel do alerta"
    )
    enabled: Optional[bool] = Field(
        None,
        description="Alerta ativo"
    )


class BudgetAlertResponse(BaseModel):
    """Resposta com dados do alerta de orcamento."""
    id: int = Field(..., description="ID do alerta")
    user_id: int = Field(..., description="ID do usuario")
    gpu_name: Optional[str] = Field(None, description="Nome da GPU (null = todos)")
    machine_type: str = Field(default="interruptible", description="Tipo de maquina")
    threshold_amount: float = Field(..., gt=0, description="Limite de orcamento em $")
    email: str = Field(..., description="Email para notificacoes")
    enabled: bool = Field(default=True, description="Alerta ativo")
    alert_name: Optional[str] = Field(None, description="Nome amigavel")
    last_triggered_at: Optional[str] = Field(None, description="Ultimo disparo (ISO)")
    last_forecasted_cost: Optional[float] = Field(None, description="Ultimo custo previsto")
    created_at: str = Field(..., description="Data de criacao (ISO)")


class BudgetAlertListResponse(BaseModel):
    """Resposta com lista de alertas de orcamento."""
    alerts: List[BudgetAlertResponse] = Field(
        default_factory=list,
        description="Lista de alertas"
    )
    total: int = Field(..., ge=0, description="Total de alertas")


class BudgetAlertDeleteResponse(BaseModel):
    """Resposta de exclusao de alerta."""
    success: bool = Field(..., description="Exclusao bem-sucedida")
    deleted_id: int = Field(..., description="ID do alerta excluido")
    message: str = Field(..., description="Mensagem de confirmacao")


# ============================================================================
# Calendar Integration Schemas
# ============================================================================


class CalendarEventItem(BaseModel):
    """Evento do calendario."""
    event_id: str = Field(..., description="ID do evento no Google Calendar")
    summary: str = Field(..., description="Titulo do evento")
    start: str = Field(..., description="Inicio do evento (ISO format)")
    end: str = Field(..., description="Fim do evento (ISO format)")
    description: Optional[str] = Field(None, description="Descricao do evento")
    location: Optional[str] = Field(None, description="Local do evento")
    all_day: bool = Field(default=False, description="Evento de dia inteiro")
    is_compute_intensive: bool = Field(
        default=False,
        description="Evento identificado como intensivo em computacao"
    )
    duration_hours: float = Field(..., ge=0, description="Duracao do evento em horas")
    suggested_start: Optional[str] = Field(
        None,
        description="Horario sugerido para melhor custo (ISO format)"
    )
    potential_savings: float = Field(
        default=0.0,
        ge=0,
        description="Economia potencial se reagendado ($)"
    )


class CalendarEventListResponse(BaseModel):
    """Resposta com lista de eventos do calendario."""
    events: List[CalendarEventItem] = Field(
        default_factory=list,
        description="Lista de eventos"
    )
    total: int = Field(..., ge=0, description="Total de eventos")
    compute_intensive_count: int = Field(
        ...,
        ge=0,
        description="Quantidade de eventos intensivos em computacao"
    )
    time_range_start: str = Field(..., description="Inicio do periodo consultado (ISO)")
    time_range_end: str = Field(..., description="Fim do periodo consultado (ISO)")
    calendar_connected: bool = Field(
        default=True,
        description="Calendario conectado"
    )
    generated_at: str = Field(..., description="Timestamp de geracao")


class CalendarStatusResponse(BaseModel):
    """Status da integracao com Google Calendar."""
    connected: bool = Field(..., description="Calendario conectado")
    needs_reauthorization: bool = Field(
        default=False,
        description="Requer nova autorizacao"
    )
    authorization_url: Optional[str] = Field(
        None,
        description="URL para autorizar acesso (se nao conectado)"
    )
    message: str = Field(..., description="Mensagem de status")


class CalendarSuggestionItem(BaseModel):
    """Sugestao de reagendamento para evento."""
    event_id: str = Field(..., description="ID do evento")
    event_summary: str = Field(..., description="Titulo do evento")
    original_start: str = Field(..., description="Horario original (ISO)")
    suggested_start: str = Field(..., description="Horario sugerido (ISO)")
    suggested_end: str = Field(..., description="Fim sugerido (ISO)")
    potential_savings: float = Field(..., ge=0, description="Economia potencial ($)")
    savings_percentage: float = Field(..., description="Percentual de economia")
    reason: str = Field(..., description="Motivo da sugestao")
    confidence: float = Field(..., ge=0, le=1, description="Confianca da sugestao (0-1)")


class CalendarSuggestionsRequest(BaseModel):
    """Request para obter sugestoes de reagendamento."""
    gpu_name: str = Field(..., description="Nome da GPU para previsao de custos")
    machine_type: str = Field(
        default="interruptible",
        description="Tipo de maquina (interruptible ou on-demand)"
    )
    days_ahead: int = Field(
        default=7,
        ge=1,
        le=14,
        description="Dias a frente para buscar eventos"
    )


class CalendarSuggestionsResponse(BaseModel):
    """Resposta com sugestoes de reagendamento."""
    suggestions: List[CalendarSuggestionItem] = Field(
        default_factory=list,
        description="Lista de sugestoes de reagendamento"
    )
    total_suggestions: int = Field(..., ge=0, description="Total de sugestoes")
    total_potential_savings: float = Field(
        ...,
        ge=0,
        description="Economia total potencial ($)"
    )
    events_analyzed: int = Field(..., ge=0, description="Eventos analisados")
    compute_intensive_events: int = Field(
        ...,
        ge=0,
        description="Eventos intensivos em computacao"
    )
    calendar_connected: bool = Field(default=True, description="Calendario conectado")
    generated_at: str = Field(..., description="Timestamp de geracao")
