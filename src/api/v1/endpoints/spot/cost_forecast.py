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
    CostForecastResponse,
    DailyCostForecastItem,
    ForecastAccuracyResponse,
    HourlyPredictionItem,
    OptimalTimingRequest,
    OptimalTimingResponse,
    TimeWindowItem,
)
from .....services.price_prediction_service import PricePredictionService
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
