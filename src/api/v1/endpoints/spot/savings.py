"""
Endpoint: Spot vs On-Demand Savings Calculator.

Calcula economia potencial ao usar Spot vs On-Demand.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta

from ...schemas.spot.savings import SavingsCalculatorItem, SavingsCalculatorResponse
from .....config.database import SessionLocal
from .....models.metrics import MarketSnapshot

router = APIRouter(tags=["Spot Savings"])


@router.get("/savings", response_model=SavingsCalculatorResponse)
async def get_savings_calculator(
    gpu_name: Optional[str] = Query(None, description="Filtrar por GPU"),
    hours_per_day: float = Query(8, ge=1, le=24, description="Horas de uso por dia"),
):
    """
    Calculadora de economia Spot vs On-Demand.

    Calcula economia potencial por hora, dia, semana e mês.
    Considera risco de interrupção baseado na confiabilidade.
    """
    db = SessionLocal()
    try:
        recent_time = datetime.utcnow() - timedelta(hours=24)
        snapshots = db.query(MarketSnapshot).filter(
            MarketSnapshot.timestamp >= recent_time
        ).order_by(MarketSnapshot.timestamp.desc()).all()

        gpu_data = {}
        for snap in snapshots:
            if gpu_name and snap.gpu_name != gpu_name:
                continue
            key = snap.gpu_name
            if key not in gpu_data:
                gpu_data[key] = {}
            if snap.machine_type not in gpu_data[key]:
                gpu_data[key][snap.machine_type] = snap

        items = []
        total_monthly_savings = 0
        total_savings_pct = 0
        count = 0

        for gpu, types in gpu_data.items():
            spot = types.get("interruptible")
            ondemand = types.get("on-demand")

            if not spot:
                continue

            spot_price = spot.avg_price or 0
            ondemand_price = ondemand.avg_price if ondemand else spot_price * 1.5

            savings_hour = ondemand_price - spot_price
            if ondemand_price > 0:
                savings_pct = (savings_hour / ondemand_price) * 100
            else:
                savings_pct = 0

            savings_day = savings_hour * hours_per_day
            savings_week = savings_day * 7
            savings_month = savings_day * 30

            # Determinar risco baseado em reliability
            reliability = spot.avg_reliability or 0.7
            if reliability >= 0.9:
                risk = "low"
            elif reliability >= 0.7:
                risk = "medium"
            else:
                risk = "high"

            item = SavingsCalculatorItem(
                gpu_name=gpu,
                spot_price=round(spot_price, 4),
                ondemand_price=round(ondemand_price, 4),
                savings_per_hour=round(savings_hour, 4),
                savings_percent=round(savings_pct, 1),
                savings_per_day=round(savings_day, 2),
                savings_per_week=round(savings_week, 2),
                savings_per_month=round(savings_month, 2),
                spot_available=spot.available_gpus or 0,
                reliability_risk=risk,
            )
            items.append(item)
            total_monthly_savings += savings_month
            total_savings_pct += savings_pct
            count += 1

        items.sort(key=lambda x: x.savings_per_month, reverse=True)
        avg_savings = total_savings_pct / count if count > 0 else 0

        return SavingsCalculatorResponse(
            items=items,
            total_potential_savings_month=round(total_monthly_savings, 2),
            avg_savings_percent=round(avg_savings, 1),
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
