"""
Endpoint: Cost Forecast.

Previsao de custos para os proximos 7 dias baseada em ML.
"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime

from ...schemas.spot.cost_forecast import (
    CostForecastResponse,
    DailyCostForecastItem,
    HourlyPredictionItem,
)
from .....services.price_prediction_service import PricePredictionService

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
