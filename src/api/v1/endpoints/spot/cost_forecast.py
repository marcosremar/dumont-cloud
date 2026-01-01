"""
Endpoint: Cost Forecast.

Previsao de custos para os proximos 7 dias baseada em ML.
"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import List

from ...schemas.spot.cost_forecast import (
    BudgetAlertCreate,
    BudgetAlertDeleteResponse,
    BudgetAlertListResponse,
    BudgetAlertResponse,
    BudgetAlertUpdate,
    CalendarEventItem,
    CalendarEventListResponse,
    CalendarStatusResponse,
    CalendarSuggestionItem,
    CalendarSuggestionsRequest,
    CalendarSuggestionsResponse,
    CostForecastResponse,
    DailyCostForecastItem,
    ForecastAccuracyResponse,
    HourlyPredictionItem,
    OptimalTimingRequest,
    OptimalTimingResponse,
    TimeWindowItem,
)
from .....services.price_prediction_service import PricePredictionService
from .....services.calendar_integration_service import (
    CalendarIntegrationService,
    CalendarOAuthError,
    get_calendar_integration_service,
)
from .....config.database import SessionLocal
from .....models.metrics import BudgetAlert, MarketSnapshot

router = APIRouter(tags=["Cost Forecast"])


@router.get("/cost-forecast/{gpu_name}", response_model=CostForecastResponse)
async def get_cost_forecast(
    gpu_name: str,
    usage_hours_per_day: float = Query(
        default=8.0,
        ge=0.1,
        le=24.0,
        description="Horas de uso por dia para calculo de custo"
    ),
    machine_type: str = Query(
        default="interruptible",
        description="Tipo de maquina (interruptible ou on-demand)"
    ),
):
    """
    Previsao de custos para os proximos 7 dias.

    Usa modelo ML para prever precos horarios e agregar em custos diarios.
    Retorna intervalos de confianca baseados nas previsoes das arvores do Random Forest.

    - **gpu_name**: Nome da GPU (ex: RTX 4090, A100)
    - **usage_hours_per_day**: Horas de uso por dia (padrao: 8)
    - **machine_type**: Tipo de maquina - interruptible (spot) ou on-demand
    """
    service = PricePredictionService()

    # Gerar forecast de 7 dias
    forecast = service.forecast_costs_7day(
        gpu_name=gpu_name,
        machine_type=machine_type,
        hours_per_day=usage_hours_per_day,
    )

    if forecast is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Need at least 50 hours of price history to generate forecast",
                "required_data_points": 50,
            }
        )

    # Converter para response schema
    daily_forecasts = []
    total_cost = 0.0
    total_lower = 0.0
    total_upper = 0.0
    lowest_cost = float('inf')
    best_day = None

    for day_data in forecast:
        # Converter previsoes horarias
        hourly_items = [
            HourlyPredictionItem(
                hour=hp["hour"],
                timestamp=hp["timestamp"],
                price=hp["price"],
            )
            for hp in day_data.get("hourly_predictions", [])
        ]

        daily_item = DailyCostForecastItem(
            day=day_data["day"],
            forecasted_cost=day_data["forecasted_cost"],
            confidence_interval=day_data["confidence_interval"],
            avg_hourly_price=day_data["avg_hourly_price"],
            hourly_predictions=hourly_items,
        )
        daily_forecasts.append(daily_item)

        # Acumular totais
        total_cost += day_data["forecasted_cost"]
        total_lower += day_data["confidence_interval"][0]
        total_upper += day_data["confidence_interval"][1]

        # Encontrar melhor dia
        if day_data["forecasted_cost"] < lowest_cost:
            lowest_cost = day_data["forecasted_cost"]
            best_day = day_data["day"]

    # Calcular confianca do modelo
    model_confidence = service._calculate_confidence(gpu_name, machine_type)

    return CostForecastResponse(
        gpu_name=gpu_name,
        machine_type=machine_type,
        usage_hours_per_day=usage_hours_per_day,
        daily_forecasts=daily_forecasts,
        total_7day_cost=round(total_cost, 2),
        total_confidence_interval=[round(total_lower, 2), round(total_upper, 2)],
        best_day=best_day,
        lowest_daily_cost=round(lowest_cost, 2) if lowest_cost != float('inf') else None,
        model_confidence=model_confidence,
        generated_at=datetime.utcnow().isoformat(),
    )


@router.post("/optimal-timing", response_model=OptimalTimingResponse)
async def get_optimal_timing(request: OptimalTimingRequest):
    """
    Recomendacao de horarios otimos para executar jobs.

    Analisa previsoes de preco para os proximos 7 dias e retorna
    as melhores janelas de tempo para iniciar um job, ordenadas
    por economia de custo.

    - **gpu_name**: Nome da GPU (ex: RTX 4090, A100)
    - **job_duration_hours**: Duracao do job em horas
    - **machine_type**: Tipo de maquina - interruptible (spot) ou on-demand
    """
    service = PricePredictionService()

    # Gerar forecast de 7 dias com 1 hora de uso para obter precos horarios
    forecast = service.forecast_costs_7day(
        gpu_name=request.gpu_name,
        machine_type=request.machine_type,
        hours_per_day=1.0,  # Para obter precos por hora
    )

    if forecast is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Need at least 50 hours of price history to generate recommendations",
                "required_data_points": 50,
            }
        )

    # Coletar todas as previsoes horarias dos 7 dias
    all_hourly: List[dict] = []
    for day_data in forecast:
        for hp in day_data.get("hourly_predictions", []):
            all_hourly.append({
                "timestamp": hp["timestamp"],
                "price": hp["price"],
            })

    if not all_hourly:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "No hourly predictions available",
            }
        )

    # Calcular janelas de tempo possiveis
    job_hours = int(request.job_duration_hours)
    if job_hours < 1:
        job_hours = 1

    # Limitar ao numero de horas disponiveis
    max_start_idx = len(all_hourly) - job_hours
    if max_start_idx < 0:
        max_start_idx = 0

    windows = []
    for start_idx in range(max_start_idx + 1):
        end_idx = start_idx + job_hours
        if end_idx > len(all_hourly):
            end_idx = len(all_hourly)

        window_hours = all_hourly[start_idx:end_idx]
        if not window_hours:
            continue

        # Calcular custo da janela
        total_cost = sum(h["price"] for h in window_hours)
        avg_price = total_cost / len(window_hours)

        # Ajustar para duracao fracionaria
        actual_cost = avg_price * request.job_duration_hours

        start_time = window_hours[0]["timestamp"]
        end_time_dt = datetime.fromisoformat(start_time) + timedelta(hours=request.job_duration_hours)

        windows.append({
            "start_time": start_time,
            "end_time": end_time_dt.isoformat(),
            "estimated_cost": actual_cost,
            "avg_hourly_price": avg_price,
        })

    if not windows:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Could not calculate time windows",
            }
        )

    # Ordenar por custo (menor primeiro)
    windows.sort(key=lambda x: x["estimated_cost"])

    # Calcular pior custo para savings
    worst_cost = max(w["estimated_cost"] for w in windows)
    best_cost = windows[0]["estimated_cost"]

    # Obter preco atual
    db = SessionLocal()
    try:
        recent = db.query(MarketSnapshot).filter(
            MarketSnapshot.gpu_name == request.gpu_name,
            MarketSnapshot.machine_type == request.machine_type,
        ).order_by(MarketSnapshot.timestamp.desc()).first()
        current_price = recent.avg_price if recent else all_hourly[0]["price"]
    finally:
        db.close()

    # Calcular confianca do modelo
    model_confidence = service._calculate_confidence(request.gpu_name, request.machine_type)

    # Construir top 3 janelas
    top_windows = []
    for rank, window in enumerate(windows[:3], start=1):
        savings = worst_cost - window["estimated_cost"]
        savings_pct = (savings / worst_cost * 100) if worst_cost > 0 else 0

        # Determinar recomendacao
        if savings_pct >= 15:
            rec = "excellent"
        elif savings_pct >= 5:
            rec = "good"
        else:
            rec = "fair"

        # Confianca da janela baseada em quao perto esta do inicio
        # Janelas mais proximas tem maior confianca
        start_dt = datetime.fromisoformat(window["start_time"])
        hours_from_now = (start_dt - datetime.utcnow()).total_seconds() / 3600
        window_confidence = max(0.5, model_confidence - (hours_from_now * 0.005))
        window_confidence = min(1.0, window_confidence)

        top_windows.append(TimeWindowItem(
            rank=rank,
            start_time=window["start_time"],
            end_time=window["end_time"],
            estimated_cost=round(window["estimated_cost"], 2),
            avg_hourly_price=round(window["avg_hourly_price"], 4),
            savings_vs_worst=round(savings, 2),
            savings_percentage=round(savings_pct, 1),
            confidence=round(window_confidence, 2),
            recommendation=rec,
        ))

    return OptimalTimingResponse(
        gpu_name=request.gpu_name,
        machine_type=request.machine_type,
        job_duration_hours=request.job_duration_hours,
        current_price=round(current_price, 4),
        time_windows=top_windows,
        worst_time_cost=round(worst_cost, 2),
        best_time_cost=round(best_cost, 2),
        max_potential_savings=round(worst_cost - best_cost, 2),
        model_confidence=round(model_confidence, 2),
        generated_at=datetime.utcnow().isoformat(),
    )


@router.get("/forecast-accuracy/{gpu_name}", response_model=ForecastAccuracyResponse)
async def get_forecast_accuracy(
    gpu_name: str,
    machine_type: str = Query(
        default="interruptible",
        description="Tipo de maquina (interruptible ou on-demand)"
    ),
    days: int = Query(
        default=30,
        ge=1,
        le=90,
        description="Periodo de avaliacao em dias (padrao: 30)"
    ),
):
    """
    Metricas de acuracia do modelo de previsao de custos.

    Retorna MAPE (Mean Absolute Percentage Error), MAE, RMSE e R-squared
    comparando previsoes com valores reais do periodo especificado.

    - **gpu_name**: Nome da GPU (ex: RTX 4090, A100)
    - **machine_type**: Tipo de maquina - interruptible (spot) ou on-demand
    - **days**: Periodo de avaliacao em dias (padrao: 30, max: 90)
    """
    service = PricePredictionService()

    # Calcular metricas de acuracia
    accuracy = service.calculate_mape(
        gpu_name=gpu_name,
        machine_type=machine_type,
        days_to_evaluate=days,
        save_result=True,
    )

    if accuracy is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Insufficient data to calculate accuracy metrics",
                "message": "Need at least 10 actual price records and predictions to evaluate accuracy",
            }
        )

    return ForecastAccuracyResponse(
        gpu_name=accuracy["gpu_name"],
        machine_type=accuracy["machine_type"],
        mape=accuracy["mape"],
        mae=accuracy["mae"],
        rmse=accuracy["rmse"],
        r_squared=accuracy["r_squared"],
        num_predictions=accuracy["num_predictions"],
        num_actual_values=accuracy["num_actual_values"],
        num_samples=accuracy["num_samples"],
        evaluation_period_days=days,
        evaluation_start=accuracy["evaluation_start"],
        evaluation_end=accuracy["evaluation_end"],
        hourly_accuracy=accuracy["hourly_accuracy"],
        daily_accuracy=accuracy["daily_accuracy"],
        model_version=accuracy["model_version"],
        generated_at=datetime.utcnow().isoformat(),
    )


# ============================================================================
# Budget Alert Management Endpoints
# ============================================================================


@router.post("/budget-alerts", response_model=BudgetAlertResponse, status_code=201)
async def create_budget_alert(request: BudgetAlertCreate):
    """
    Criar alerta de orcamento.

    Configura um novo alerta que sera disparado quando o custo
    previsto para os proximos 7 dias exceder o limite configurado.

    - **gpu_name**: Nome da GPU (opcional, null = todos os GPUs)
    - **threshold**: Limite de orcamento em $ para 7 dias
    - **email**: Email para receber notificacoes
    - **machine_type**: Tipo de maquina (interruptible ou on-demand)
    - **alert_name**: Nome amigavel do alerta (opcional)
    - **enabled**: Alerta ativo (padrao: true)
    """
    db = SessionLocal()
    try:
        # Criar alerta no banco
        # TODO: Substituir user_id por valor do token de autenticacao
        alert = BudgetAlert(
            user_id=1,  # Placeholder - deve vir do token JWT
            gpu_name=request.gpu_name,
            machine_type=request.machine_type,
            threshold_amount=request.threshold,
            email=request.email,
            enabled=request.enabled,
            alert_name=request.alert_name,
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)

        return BudgetAlertResponse(
            id=alert.id,
            user_id=alert.user_id,
            gpu_name=alert.gpu_name,
            machine_type=alert.machine_type,
            threshold_amount=alert.threshold_amount,
            email=alert.email,
            enabled=alert.enabled,
            alert_name=alert.alert_name,
            last_triggered_at=alert.last_triggered_at.isoformat() if alert.last_triggered_at else None,
            last_forecasted_cost=alert.last_forecasted_cost,
            created_at=alert.created_at.isoformat(),
        )
    finally:
        db.close()


@router.get("/budget-alerts", response_model=BudgetAlertListResponse)
async def list_budget_alerts(
    user_id: int = Query(
        default=1,
        description="ID do usuario (placeholder para autenticacao)"
    ),
    gpu_name: str = Query(
        default=None,
        description="Filtrar por GPU especifica"
    ),
    enabled_only: bool = Query(
        default=False,
        description="Retornar apenas alertas ativos"
    ),
):
    """
    Listar alertas de orcamento do usuario.

    Retorna todos os alertas configurados, com opcao de filtrar
    por GPU ou status ativo.

    - **user_id**: ID do usuario (placeholder para autenticacao)
    - **gpu_name**: Filtrar por GPU especifica
    - **enabled_only**: Retornar apenas alertas ativos
    """
    db = SessionLocal()
    try:
        query = db.query(BudgetAlert).filter(BudgetAlert.user_id == user_id)

        if gpu_name:
            query = query.filter(BudgetAlert.gpu_name == gpu_name)

        if enabled_only:
            query = query.filter(BudgetAlert.enabled == True)

        alerts = query.order_by(BudgetAlert.created_at.desc()).all()

        alert_responses = [
            BudgetAlertResponse(
                id=alert.id,
                user_id=alert.user_id,
                gpu_name=alert.gpu_name,
                machine_type=alert.machine_type,
                threshold_amount=alert.threshold_amount,
                email=alert.email,
                enabled=alert.enabled,
                alert_name=alert.alert_name,
                last_triggered_at=alert.last_triggered_at.isoformat() if alert.last_triggered_at else None,
                last_forecasted_cost=alert.last_forecasted_cost,
                created_at=alert.created_at.isoformat(),
            )
            for alert in alerts
        ]

        return BudgetAlertListResponse(
            alerts=alert_responses,
            total=len(alert_responses),
        )
    finally:
        db.close()


@router.get("/budget-alerts/{alert_id}", response_model=BudgetAlertResponse)
async def get_budget_alert(alert_id: int):
    """
    Obter detalhes de um alerta de orcamento especifico.

    - **alert_id**: ID do alerta
    """
    db = SessionLocal()
    try:
        alert = db.query(BudgetAlert).filter(BudgetAlert.id == alert_id).first()

        if not alert:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Budget alert not found",
                    "alert_id": alert_id,
                }
            )

        return BudgetAlertResponse(
            id=alert.id,
            user_id=alert.user_id,
            gpu_name=alert.gpu_name,
            machine_type=alert.machine_type,
            threshold_amount=alert.threshold_amount,
            email=alert.email,
            enabled=alert.enabled,
            alert_name=alert.alert_name,
            last_triggered_at=alert.last_triggered_at.isoformat() if alert.last_triggered_at else None,
            last_forecasted_cost=alert.last_forecasted_cost,
            created_at=alert.created_at.isoformat(),
        )
    finally:
        db.close()


@router.put("/budget-alerts/{alert_id}", response_model=BudgetAlertResponse)
async def update_budget_alert(alert_id: int, request: BudgetAlertUpdate):
    """
    Atualizar alerta de orcamento existente.

    Atualiza apenas os campos fornecidos no request.
    Campos omitidos ou null mantem o valor atual.

    - **alert_id**: ID do alerta a atualizar
    - **gpu_name**: Nome da GPU (null = todos os GPUs)
    - **threshold**: Limite de orcamento em $
    - **email**: Email para notificacoes
    - **machine_type**: Tipo de maquina
    - **alert_name**: Nome amigavel
    - **enabled**: Alerta ativo
    """
    db = SessionLocal()
    try:
        alert = db.query(BudgetAlert).filter(BudgetAlert.id == alert_id).first()

        if not alert:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Budget alert not found",
                    "alert_id": alert_id,
                }
            )

        # Atualizar apenas campos fornecidos
        if request.gpu_name is not None:
            alert.gpu_name = request.gpu_name
        if request.threshold is not None:
            alert.threshold_amount = request.threshold
        if request.email is not None:
            alert.email = request.email
        if request.machine_type is not None:
            alert.machine_type = request.machine_type
        if request.alert_name is not None:
            alert.alert_name = request.alert_name
        if request.enabled is not None:
            alert.enabled = request.enabled

        db.commit()
        db.refresh(alert)

        return BudgetAlertResponse(
            id=alert.id,
            user_id=alert.user_id,
            gpu_name=alert.gpu_name,
            machine_type=alert.machine_type,
            threshold_amount=alert.threshold_amount,
            email=alert.email,
            enabled=alert.enabled,
            alert_name=alert.alert_name,
            last_triggered_at=alert.last_triggered_at.isoformat() if alert.last_triggered_at else None,
            last_forecasted_cost=alert.last_forecasted_cost,
            created_at=alert.created_at.isoformat(),
        )
    finally:
        db.close()


@router.delete("/budget-alerts/{alert_id}", response_model=BudgetAlertDeleteResponse)
async def delete_budget_alert(alert_id: int):
    """
    Excluir alerta de orcamento.

    Remove permanentemente um alerta de orcamento.

    - **alert_id**: ID do alerta a excluir
    """
    db = SessionLocal()
    try:
        alert = db.query(BudgetAlert).filter(BudgetAlert.id == alert_id).first()

        if not alert:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Budget alert not found",
                    "alert_id": alert_id,
                }
            )

        db.delete(alert)
        db.commit()

        return BudgetAlertDeleteResponse(
            success=True,
            deleted_id=alert_id,
            message=f"Budget alert {alert_id} deleted successfully",
        )
    finally:
        db.close()


# ============================================================================
# Calendar Integration Endpoints
# ============================================================================


@router.get("/calendar-events", response_model=CalendarEventListResponse)
async def get_calendar_events(
    days_ahead: int = Query(
        default=7,
        ge=1,
        le=14,
        description="Numero de dias a frente para buscar eventos"
    ),
    max_events: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Numero maximo de eventos a retornar"
    ),
):
    """
    Buscar eventos do Google Calendar.

    Retorna eventos do calendario do usuario para os proximos dias,
    identificando aqueles que sao intensivos em computacao
    (baseado em palavras-chave como 'training', 'gpu', 'render', etc).

    - **days_ahead**: Dias a frente para buscar eventos (padrao: 7, max: 14)
    - **max_events**: Numero maximo de eventos (padrao: 50, max: 100)

    Requer integracao com Google Calendar configurada.
    Retorna graceful degradation se OAuth expirado.
    """
    calendar_service = get_calendar_integration_service()

    time_min = datetime.utcnow()
    time_max = time_min + timedelta(days=days_ahead)

    try:
        events = calendar_service.fetch_events(
            time_min=time_min,
            time_max=time_max,
            max_results=max_events,
            identify_compute_intensive=True,
        )

        # Converter para schema de resposta
        event_items = []
        compute_intensive_count = 0

        for event in events:
            if event.is_compute_intensive:
                compute_intensive_count += 1

            event_items.append(CalendarEventItem(
                event_id=event.event_id,
                summary=event.summary,
                start=event.start.isoformat() if event.start else "",
                end=event.end.isoformat() if event.end else "",
                description=event.description,
                location=event.location,
                all_day=event.all_day,
                is_compute_intensive=event.is_compute_intensive,
                duration_hours=round(event._calculate_duration_hours(), 2),
                suggested_start=event.suggested_start.isoformat() if event.suggested_start else None,
                potential_savings=round(event.potential_savings, 2),
            ))

        return CalendarEventListResponse(
            events=event_items,
            total=len(event_items),
            compute_intensive_count=compute_intensive_count,
            time_range_start=time_min.isoformat(),
            time_range_end=time_max.isoformat(),
            calendar_connected=True,
            generated_at=datetime.utcnow().isoformat(),
        )

    except CalendarOAuthError as e:
        # Graceful degradation - return empty list with connection status
        return CalendarEventListResponse(
            events=[],
            total=0,
            compute_intensive_count=0,
            time_range_start=time_min.isoformat(),
            time_range_end=time_max.isoformat(),
            calendar_connected=False,
            generated_at=datetime.utcnow().isoformat(),
        )


@router.get("/calendar-status", response_model=CalendarStatusResponse)
async def get_calendar_status(
    redirect_uri: str = Query(
        default="http://localhost:8000/callback",
        description="URI de callback para OAuth"
    ),
):
    """
    Verificar status da integracao com Google Calendar.

    Retorna se o calendario esta conectado e se precisa reautorizacao.
    Se nao conectado, retorna URL para autorizar acesso.

    - **redirect_uri**: URI de callback para fluxo OAuth
    """
    calendar_service = get_calendar_integration_service()

    connected = calendar_service.is_connected
    needs_reauth = calendar_service.needs_reauthorization

    # Gerar URL de autorizacao se nao conectado
    auth_url = None
    if not connected or needs_reauth:
        auth_url = calendar_service.get_oauth_authorization_url(
            redirect_uri=redirect_uri,
        )

    # Mensagem de status
    if connected and not needs_reauth:
        message = "Google Calendar connected and ready"
    elif needs_reauth:
        message = "Calendar access expired. Please reconnect your calendar."
    else:
        message = "Calendar not connected. Please authorize access."

    return CalendarStatusResponse(
        connected=connected,
        needs_reauthorization=needs_reauth,
        authorization_url=auth_url,
        message=message,
    )


@router.post("/calendar-suggestions", response_model=CalendarSuggestionsResponse)
async def get_calendar_suggestions(request: CalendarSuggestionsRequest):
    """
    Obter sugestoes de reagendamento para eventos do calendario.

    Analisa eventos intensivos em computacao e sugere horarios
    otimos baseados na previsao de custos.

    - **gpu_name**: Nome da GPU para previsao de custos
    - **machine_type**: Tipo de maquina (interruptible ou on-demand)
    - **days_ahead**: Dias a frente para buscar eventos
    """
    calendar_service = get_calendar_integration_service()
    price_service = PricePredictionService()

    time_min = datetime.utcnow()
    time_max = time_min + timedelta(days=request.days_ahead)

    try:
        # Buscar eventos do calendario
        events = calendar_service.fetch_events(
            time_min=time_min,
            time_max=time_max,
            identify_compute_intensive=True,
        )

        if not events:
            return CalendarSuggestionsResponse(
                suggestions=[],
                total_suggestions=0,
                total_potential_savings=0.0,
                events_analyzed=0,
                compute_intensive_events=0,
                calendar_connected=True,
                generated_at=datetime.utcnow().isoformat(),
            )

        # Gerar forecast de custos para obter janelas otimas
        forecast = price_service.forecast_costs_7day(
            gpu_name=request.gpu_name,
            machine_type=request.machine_type,
            hours_per_day=1.0,  # Para obter precos horarios
        )

        if forecast is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Need at least 50 hours of price history for suggestions",
                    "required_data_points": 50,
                }
            )

        # Coletar previsoes horarias e construir janelas otimas
        all_hourly: List[dict] = []
        for day_data in forecast:
            for hp in day_data.get("hourly_predictions", []):
                all_hourly.append({
                    "timestamp": hp["timestamp"],
                    "price": hp["price"],
                })

        # Criar mapa de precos por hora
        hourly_prices = {}
        for hp in all_hourly:
            try:
                ts = datetime.fromisoformat(hp["timestamp"])
                hour_key = str(ts.hour)
                if hour_key not in hourly_prices:
                    hourly_prices[hour_key] = hp["price"]
            except (ValueError, KeyError):
                continue

        # Calcular janelas otimas ordenadas por preco
        if all_hourly:
            sorted_hours = sorted(all_hourly, key=lambda x: x["price"])
            optimal_windows = []

            for hp in sorted_hours[:10]:  # Top 10 janelas mais baratas
                try:
                    start = datetime.fromisoformat(hp["timestamp"])
                    optimal_windows.append({
                        "start_time": hp["timestamp"],
                        "end_time": (start + timedelta(hours=8)).isoformat(),
                        "estimated_cost": hp["price"] * 8,
                        "savings_amount": (all_hourly[0]["price"] - hp["price"]) * 8,
                    })
                except (ValueError, KeyError):
                    continue
        else:
            optimal_windows = []

        # Gerar sugestoes para eventos
        suggestions_data = calendar_service.get_suggestions_for_events(
            events=events,
            optimal_windows=optimal_windows,
            hourly_prices=hourly_prices,
        )

        # Converter para schema de resposta
        suggestion_items = []
        total_savings = 0.0

        for suggestion in suggestions_data:
            # Encontrar o titulo do evento
            event_summary = ""
            for event in events:
                if event.event_id == suggestion.event_id:
                    event_summary = event.summary
                    break

            suggestion_items.append(CalendarSuggestionItem(
                event_id=suggestion.event_id,
                event_summary=event_summary,
                original_start=suggestion.original_start.isoformat(),
                suggested_start=suggestion.suggested_start.isoformat(),
                suggested_end=suggestion.suggested_end.isoformat(),
                potential_savings=round(suggestion.potential_savings, 2),
                savings_percentage=round(suggestion.savings_percentage, 1),
                reason=suggestion.reason,
                confidence=round(suggestion.confidence, 2),
            ))
            total_savings += suggestion.potential_savings

        compute_intensive_count = sum(1 for e in events if e.is_compute_intensive)

        return CalendarSuggestionsResponse(
            suggestions=suggestion_items,
            total_suggestions=len(suggestion_items),
            total_potential_savings=round(total_savings, 2),
            events_analyzed=len(events),
            compute_intensive_events=compute_intensive_count,
            calendar_connected=True,
            generated_at=datetime.utcnow().isoformat(),
        )

    except CalendarOAuthError as e:
        # Graceful degradation
        return CalendarSuggestionsResponse(
            suggestions=[],
            total_suggestions=0,
            total_potential_savings=0.0,
            events_analyzed=0,
            compute_intensive_events=0,
            calendar_connected=False,
            generated_at=datetime.utcnow().isoformat(),
        )
