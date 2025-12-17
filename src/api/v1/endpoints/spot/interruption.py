"""
Endpoint: Interruption Rate by Provider.

Taxa de interrupção por provedor para avaliar riscos.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

from ...schemas.spot.interruption import InterruptionRateItem, InterruptionRateResponse
from .....config.database import SessionLocal
from .....models.metrics import ProviderReliability

router = APIRouter(tags=["Spot Interruption"])


@router.get("/interruption-rates", response_model=InterruptionRateResponse)
async def get_interruption_rates(
    gpu_name: Optional[str] = Query(None, description="Filtrar por GPU"),
    geolocation: Optional[str] = Query(None, description="Filtrar por região"),
    max_rate: float = Query(1.0, ge=0, le=1, description="Taxa máxima de interrupção"),
    limit: int = Query(50, le=200, description="Limite de resultados"),
):
    """
    Taxa de interrupção por provedor.

    Mostra quais provedores têm menor risco de interrupção.
    Ordenado por taxa de interrupção (menor primeiro).
    """
    db = SessionLocal()
    try:
        query = db.query(ProviderReliability)

        if gpu_name:
            query = query.filter(ProviderReliability.gpu_name == gpu_name)
        if geolocation:
            query = query.filter(ProviderReliability.geolocation.ilike(f"%{geolocation}%"))

        providers = query.order_by(ProviderReliability.reliability_score.desc()).limit(limit).all()

        items = []
        total_rate = 0
        safe_count = 0

        for p in providers:
            reliability = p.reliability_score or 0.5
            interruption_rate = 1 - reliability

            if interruption_rate > max_rate:
                continue

            avg_uptime = reliability * 24  # horas estimadas

            if interruption_rate < 0.05:
                risk = "low"
                safe_count += 1
            elif interruption_rate < 0.15:
                risk = "medium"
            else:
                risk = "high"

            item = InterruptionRateItem(
                machine_id=p.machine_id,
                hostname=p.hostname,
                geolocation=p.geolocation,
                gpu_name=p.gpu_name,
                interruption_rate=round(interruption_rate, 3),
                avg_uptime_hours=round(avg_uptime, 1),
                total_rentals=p.total_observations or 1,
                successful_completions=int((p.total_observations or 1) * reliability),
                reliability_score=round(reliability, 3),
                risk_level=risk,
            )
            items.append(item)
            total_rate += interruption_rate

        items.sort(key=lambda x: x.interruption_rate)
        avg_rate = total_rate / len(items) if items else 0

        return InterruptionRateResponse(
            items=items,
            avg_interruption_rate=round(avg_rate, 3),
            safest_providers=safe_count,
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
