"""
Endpoint: Safe Spot Windows.

Janelas de tempo seguras para usar instâncias Spot.
"""
from fastapi import APIRouter
from datetime import datetime, timedelta

from ...schemas.spot.safe_windows import SafeSpotWindowItem, SafeSpotWindowsResponse
from .....config.database import SessionLocal
from .....models.metrics import MarketSnapshot
from .constants import DAY_NAMES

router = APIRouter(tags=["Spot Safe Windows"])


@router.get("/safe-windows/{gpu_name}", response_model=SafeSpotWindowsResponse)
async def get_safe_spot_windows(gpu_name: str):
    """
    Janelas seguras para usar Spot.

    Identifica melhores horários e dias para usar spot com menor risco.
    Baseado em dados históricos de interrupção e disponibilidade.
    """
    db = SessionLocal()
    try:
        week_ago = datetime.utcnow() - timedelta(days=7)
        snapshots = db.query(MarketSnapshot).filter(
            MarketSnapshot.gpu_name == gpu_name,
            MarketSnapshot.machine_type == "interruptible",
            MarketSnapshot.timestamp >= week_ago,
        ).all()

        # Agrupar por hora e dia
        hour_data = {}

        for snap in snapshots:
            hour = snap.timestamp.hour
            day = DAY_NAMES[snap.timestamp.weekday()]
            key = (hour, day)

            if key not in hour_data:
                hour_data[key] = {"prices": [], "reliability": []}

            hour_data[key]["prices"].append(snap.avg_price or 0)
            hour_data[key]["reliability"].append(snap.avg_reliability or 0.7)

        windows = []
        for (hour, day), data in hour_data.items():
            avg_price = sum(data["prices"]) / len(data["prices"]) if data["prices"] else 0
            avg_reliability = sum(data["reliability"]) / len(data["reliability"]) if data["reliability"] else 0.7

            interruption_rate = 1 - avg_reliability
            availability = min(1.0, len(data["prices"]) / 24)

            if interruption_rate < 0.05 and availability > 0.5:
                rec = "highly_recommended"
            elif interruption_rate < 0.10:
                rec = "recommended"
            elif interruption_rate < 0.20:
                rec = "caution"
            else:
                rec = "avoid"

            window = SafeSpotWindowItem(
                hour_utc=hour,
                day_of_week=day,
                avg_interruption_rate=round(interruption_rate, 3),
                avg_spot_price=round(avg_price, 4),
                availability_score=round(availability, 2),
                recommendation=rec,
            )
            windows.append(window)

        # Se não há dados, gerar windows padrão
        if not windows:
            for day in DAY_NAMES:
                for hour in [3, 4, 5, 14, 15]:
                    windows.append(SafeSpotWindowItem(
                        hour_utc=hour,
                        day_of_week=day,
                        avg_interruption_rate=0.08,
                        avg_spot_price=0.0,
                        availability_score=0.7,
                        recommendation="recommended",
                    ))

        windows.sort(key=lambda x: (x.avg_interruption_rate, -x.availability_score))

        best = windows[0] if windows else None
        worst = windows[-1] if windows else None

        avg_rate = sum(w.avg_interruption_rate for w in windows) / len(windows) if windows else 0.1
        if avg_rate < 0.1:
            overall_risk = "low"
        elif avg_rate < 0.2:
            overall_risk = "medium"
        else:
            overall_risk = "high"

        return SafeSpotWindowsResponse(
            gpu_name=gpu_name,
            windows=windows[:24],
            best_window=best,
            worst_window=worst,
            overall_risk=overall_risk,
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
