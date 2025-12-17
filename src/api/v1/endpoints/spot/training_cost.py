"""
Endpoint: Cost per Training Hour.

Custo por hora de treinamento de modelos.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta

from ...schemas.spot.training_cost import TrainingCostItem, TrainingCostResponse
from .....config.database import SessionLocal
from .....models.metrics import MarketSnapshot
from .constants import GPU_SPECS

router = APIRouter(tags=["Spot Training Cost"])


@router.get("/training-cost", response_model=TrainingCostResponse)
async def get_training_cost(
    min_vram: int = Query(8, ge=4, description="VRAM mínima em GB"),
    max_price: Optional[float] = Query(None, description="Preço máximo por hora"),
):
    """
    Custo por hora de treinamento.

    Compara GPUs por eficiência de treinamento de modelos.
    Inclui estimativa de tempo por época e batch size recomendado.
    """
    db = SessionLocal()
    try:
        recent_time = datetime.utcnow() - timedelta(hours=24)

        # Buscar spot e on-demand
        snapshots = db.query(MarketSnapshot).filter(
            MarketSnapshot.timestamp >= recent_time,
        ).order_by(MarketSnapshot.timestamp.desc()).all()

        gpu_prices = {}
        for snap in snapshots:
            gpu = snap.gpu_name
            if gpu not in gpu_prices:
                gpu_prices[gpu] = {}
            if snap.machine_type not in gpu_prices[gpu]:
                gpu_prices[gpu][snap.machine_type] = snap.avg_price or 0

        items = []
        for gpu_name, prices in gpu_prices.items():
            specs = GPU_SPECS.get(gpu_name)
            if not specs:
                continue

            vram = specs["vram"]
            if vram < min_vram:
                continue

            spot_price = prices.get("interruptible", 0)
            ondemand_price = prices.get("on-demand", spot_price * 1.5)

            if max_price and spot_price > max_price:
                continue

            tflops = specs["tflops"]
            batch_size = specs["batch_size"]

            # Custo por hora de treinamento (inclui overhead)
            training_overhead = 1.2
            cost_spot = spot_price * training_overhead
            cost_ondemand = ondemand_price * training_overhead

            # Tempo estimado por época (baseado em TFLOPS)
            epoch_time = 60 / (tflops / 10)

            # Rating de eficiência
            if tflops > 100 and spot_price < 1:
                rating = "excellent"
            elif tflops > 50 and spot_price < 0.8:
                rating = "good"
            elif tflops > 20:
                rating = "fair"
            else:
                rating = "poor"

            item = TrainingCostItem(
                gpu_name=gpu_name,
                vram_gb=vram,
                tflops=tflops,
                spot_price=round(spot_price, 4),
                ondemand_price=round(ondemand_price, 4),
                cost_per_training_hour_spot=round(cost_spot, 4),
                cost_per_training_hour_ondemand=round(cost_ondemand, 4),
                estimated_epoch_time_minutes=round(epoch_time, 1),
                efficiency_rating=rating,
                recommended_batch_size=batch_size,
                available_count=10,
            )
            items.append(item)

        # Ordenar por custo-eficiência
        items.sort(key=lambda x: x.cost_per_training_hour_spot / max(x.tflops, 1))

        most_cost_effective = items[0] if items else None
        fastest = max(items, key=lambda x: x.tflops) if items else None

        return TrainingCostResponse(
            items=items,
            most_cost_effective=most_cost_effective,
            fastest_training=fastest,
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
