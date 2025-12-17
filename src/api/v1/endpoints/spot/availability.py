"""
Endpoint: Instant Spot Availability.

Disponibilidade instantânea de GPUs Spot.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta

from ...schemas.spot.availability import InstantAvailabilityItem, InstantAvailabilityResponse
from .....config.database import SessionLocal
from .....models.metrics import MarketSnapshot

router = APIRouter(tags=["Spot Availability"])


@router.get("/availability", response_model=InstantAvailabilityResponse)
async def get_instant_availability(
    gpu_name: Optional[str] = Query(None, description="Filtrar por GPU"),
    min_available: int = Query(1, ge=1, description="Mínimo de GPUs disponíveis"),
):
    """
    Disponibilidade instantânea de GPUs Spot.

    Mostra GPUs disponíveis agora para aluguel imediato.
    Inclui distribuição por região e tempo estimado de provisão.
    """
    db = SessionLocal()
    try:
        recent_time = datetime.utcnow() - timedelta(hours=1)
        query = db.query(MarketSnapshot).filter(
            MarketSnapshot.machine_type == "interruptible",
            MarketSnapshot.timestamp >= recent_time,
        )

        if gpu_name:
            query = query.filter(MarketSnapshot.gpu_name == gpu_name)

        snapshots = query.order_by(MarketSnapshot.timestamp.desc()).all()

        # Agrupar por GPU (último snapshot)
        gpu_data = {}
        for snap in snapshots:
            if snap.gpu_name not in gpu_data:
                gpu_data[snap.gpu_name] = snap

        items = []
        total = 0
        fastest = None
        fastest_count = 0

        for gpu, snap in gpu_data.items():
            available = snap.available_gpus or 0
            if available < min_available:
                continue

            # Distribuição por região
            regions = snap.region_distribution or {"US": available // 2, "EU": available // 3, "Other": available // 6}

            # Verificados
            verified = snap.verified_offers or 0

            # Tempo estimado de provisão
            if available > 20:
                provision_time = "< 1 min"
            elif available > 5:
                provision_time = "1-3 min"
            else:
                provision_time = "3-5 min"

            item = InstantAvailabilityItem(
                gpu_name=gpu,
                available_now=available,
                spot_price=round(snap.min_price or 0, 4),
                time_to_provision=provision_time,
                regions=regions if isinstance(regions, dict) else {"Global": available},
                verified_count=verified,
                best_offer_id=None,
            )
            items.append(item)
            total += available

            if available > fastest_count:
                fastest_count = available
                fastest = gpu

        items.sort(key=lambda x: x.available_now, reverse=True)

        return InstantAvailabilityResponse(
            items=items,
            total_available=total,
            fastest_gpu=fastest,
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
