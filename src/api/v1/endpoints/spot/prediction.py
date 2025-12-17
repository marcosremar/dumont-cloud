"""
Endpoint: Spot Price Prediction.

Previsão de preços Spot baseada em dados históricos.
"""
from fastapi import APIRouter
from datetime import datetime, timedelta

from ...schemas.spot.prediction import SpotPricePredictionItem, SpotPricePredictionResponse
from .....config.database import SessionLocal
from .....models.metrics import MarketSnapshot

router = APIRouter(tags=["Spot Prediction"])


@router.get("/prediction/{gpu_name}", response_model=SpotPricePredictionResponse)
async def get_spot_price_prediction(gpu_name: str):
    """
    Previsão de preços Spot para próximas 24h.

    Usa dados históricos para prever melhores horários.
    Retorna confiança e recomendações por hora.
    """
    db = SessionLocal()
    try:
        week_ago = datetime.utcnow() - timedelta(days=7)
        snapshots = db.query(MarketSnapshot).filter(
            MarketSnapshot.gpu_name == gpu_name,
            MarketSnapshot.machine_type == "interruptible",
            MarketSnapshot.timestamp >= week_ago,
        ).order_by(MarketSnapshot.timestamp.desc()).all()

        current_price = snapshots[0].avg_price if snapshots else 0.5

        # Agrupar por hora
        hour_prices = {i: [] for i in range(24)}
        for snap in snapshots:
            hour = snap.timestamp.hour
            if snap.avg_price:
                hour_prices[hour].append(snap.avg_price)

        predictions = []
        lowest_price = float('inf')
        best_hour = 0

        for hour in range(24):
            prices = hour_prices[hour]
            if prices:
                predicted = sum(prices) / len(prices)
                confidence = min(1.0, len(prices) / 20)
                availability = len(prices) * 3
            else:
                # Estimar baseado em padrões típicos
                if 2 <= hour <= 6:
                    predicted = current_price * 0.85
                elif 9 <= hour <= 17:
                    predicted = current_price * 1.1
                else:
                    predicted = current_price
                confidence = 0.3
                availability = 10

            if predicted < lowest_price:
                lowest_price = predicted
                best_hour = hour

            # Recomendação
            if predicted < current_price * 0.9:
                rec = "excellent"
            elif predicted < current_price:
                rec = "good"
            elif predicted < current_price * 1.1:
                rec = "fair"
            else:
                rec = "wait"

            predictions.append(SpotPricePredictionItem(
                hour_utc=hour,
                predicted_price=round(predicted, 4),
                confidence=round(confidence, 2),
                predicted_availability=availability,
                recommendation=rec,
            ))

        overall_confidence = sum(p.confidence for p in predictions) / 24

        return SpotPricePredictionResponse(
            gpu_name=gpu_name,
            current_price=round(current_price, 4),
            predictions_24h=predictions,
            best_time_to_rent=best_hour,
            predicted_lowest_price=round(lowest_price if lowest_price != float('inf') else current_price, 4),
            model_confidence=round(overall_confidence, 2),
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
