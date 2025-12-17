"""
Endpoint: Spot Price Real-time Monitor.

Monitora preços spot em tempo real comparando com on-demand.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta

from ...schemas.spot.monitor import SpotPriceItem, SpotPriceMonitorResponse
from .....config.database import SessionLocal
from .....models.metrics import MarketSnapshot

router = APIRouter(tags=["Spot Monitor"])


@router.get("/monitor", response_model=SpotPriceMonitorResponse)
async def get_spot_price_monitor(
    gpu_name: Optional[str] = Query(None, description="Filtrar por GPU específica"),
):
    """
    Monitor de preços Spot em tempo real.

    Compara preços spot vs on-demand e mostra economia potencial.
    Retorna tendência de preços e melhor oferta.
    """
    db = SessionLocal()
    try:
        recent_time = datetime.utcnow() - timedelta(hours=24)
        snapshots = db.query(MarketSnapshot).filter(
            MarketSnapshot.timestamp >= recent_time
        ).order_by(MarketSnapshot.timestamp.desc()).all()

        # Agrupar por GPU
        gpu_data = {}
        for snap in snapshots:
            if gpu_name and snap.gpu_name != gpu_name:
                continue
            key = snap.gpu_name
            if key not in gpu_data:
                gpu_data[key] = {"spot": None, "ondemand": None, "history": []}

            if snap.machine_type == "interruptible" and not gpu_data[key]["spot"]:
                gpu_data[key]["spot"] = snap
            elif snap.machine_type == "on-demand" and not gpu_data[key]["ondemand"]:
                gpu_data[key]["ondemand"] = snap

            if snap.machine_type == "interruptible":
                gpu_data[key]["history"].append(snap.avg_price)

        items = []
        total_savings = 0
        count = 0

        for gpu, data in gpu_data.items():
            spot = data["spot"]
            ondemand = data["ondemand"]

            if not spot:
                continue

            spot_price = spot.avg_price or 0
            ondemand_price = ondemand.avg_price if ondemand else spot_price * 1.5

            if ondemand_price > 0:
                savings = ((ondemand_price - spot_price) / ondemand_price) * 100
            else:
                savings = 0

            # Calcular tendência
            history = data["history"][:5]
            if len(history) >= 2:
                if history[0] > history[-1] * 1.05:
                    trend = "up"
                elif history[0] < history[-1] * 0.95:
                    trend = "down"
                else:
                    trend = "stable"
            else:
                trend = "stable"

            item = SpotPriceItem(
                gpu_name=gpu,
                spot_price=round(spot_price, 4),
                ondemand_price=round(ondemand_price, 4),
                savings_percent=round(savings, 1),
                available_gpus=spot.available_gpus or 0,
                total_offers=spot.total_offers or 0,
                price_trend=trend,
                min_price=round(spot.min_price or 0, 4),
                last_update=spot.timestamp.isoformat(),
            )
            items.append(item)
            total_savings += savings
            count += 1

        items.sort(key=lambda x: x.savings_percent, reverse=True)

        avg_savings = total_savings / count if count > 0 else 0
        best_deal = items[0] if items else None

        return SpotPriceMonitorResponse(
            items=items,
            total_gpus_monitored=len(items),
            avg_savings_percent=round(avg_savings, 1),
            best_deal=best_deal,
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
