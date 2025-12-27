"""
Market API Endpoints - Price prediction, host ranking, and market analysis
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from datetime import datetime

from ..dependencies import get_current_user_email

router = APIRouter(prefix="/market", tags=["Market"])


class PricePrediction(BaseModel):
    gpu_type: str
    current_price: float
    predicted_price: float
    prediction_hours: int
    confidence: float
    trend: str  # "up", "down", "stable"


class HostRanking(BaseModel):
    machine_id: int
    host_name: str
    reliability_score: float
    uptime_percent: float
    avg_response_time: float
    total_rentals: int
    gpu_types: List[str]


class MarketSnapshot(BaseModel):
    gpu_type: str
    avg_price: float
    min_price: float
    max_price: float
    available_count: int
    region: str


@router.get("/prediction")
async def get_price_prediction(
    gpu_type: str = Query("RTX 4090", description="GPU type"),
    hours: int = Query(24, ge=1, le=168, description="Prediction horizon in hours"),
    user_email: str = Depends(get_current_user_email),
):
    """
    Get price prediction for a GPU type
    """
    # Mock prediction data - would use ML model in production
    current_price = {
        "RTX 4090": 0.35,
        "RTX 3090": 0.25,
        "A100 PCIe": 1.50,
        "A100 SXM": 2.00,
        "H100 PCIe": 2.50,
        "H100 SXM": 3.00,
    }.get(gpu_type, 0.50)

    # Simulate price trend
    import random
    trend = random.choice(["up", "down", "stable"])
    delta = 0.05 if trend == "up" else (-0.05 if trend == "down" else 0)

    return PricePrediction(
        gpu_type=gpu_type,
        current_price=current_price,
        predicted_price=round(current_price * (1 + delta), 2),
        prediction_hours=hours,
        confidence=0.75,
        trend=trend,
    )


@router.get("/hosts/ranking")
async def get_host_ranking(
    min_reliability: float = Query(0.8, ge=0, le=1, description="Minimum reliability score"),
    gpu_type: Optional[str] = Query(None, description="Filter by GPU type"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    user_email: str = Depends(get_current_user_email),
):
    """
    Get ranking of hosts by reliability
    """
    # Mock ranking data
    hosts = [
        HostRanking(
            machine_id=12345,
            host_name="gpu-host-001",
            reliability_score=0.98,
            uptime_percent=99.5,
            avg_response_time=45.2,
            total_rentals=1234,
            gpu_types=["RTX 4090", "RTX 3090"],
        ),
        HostRanking(
            machine_id=12346,
            host_name="gpu-host-002",
            reliability_score=0.95,
            uptime_percent=98.0,
            avg_response_time=52.1,
            total_rentals=856,
            gpu_types=["A100 PCIe"],
        ),
        HostRanking(
            machine_id=12347,
            host_name="gpu-host-003",
            reliability_score=0.92,
            uptime_percent=97.5,
            avg_response_time=48.3,
            total_rentals=567,
            gpu_types=["RTX 4090"],
        ),
    ]

    # Filter by reliability
    filtered = [h for h in hosts if h.reliability_score >= min_reliability]

    # Filter by GPU type if specified
    if gpu_type:
        filtered = [h for h in filtered if gpu_type in h.gpu_types]

    return {"hosts": filtered[:limit], "count": len(filtered)}


@router.get("/stream")
async def get_market_stream(
    gpu_types: Optional[str] = Query(None, description="Comma-separated GPU types"),
    user_email: str = Depends(get_current_user_email),
):
    """
    Get real-time market data stream (snapshot)
    """
    gpu_list = gpu_types.split(",") if gpu_types else ["RTX 4090", "RTX 3090", "A100 PCIe"]

    snapshots = []
    for gpu in gpu_list:
        gpu = gpu.strip()
        base_price = {
            "RTX 4090": 0.35,
            "RTX 3090": 0.25,
            "A100 PCIe": 1.50,
            "A100 SXM": 2.00,
            "H100 PCIe": 2.50,
        }.get(gpu, 0.50)

        snapshots.append(MarketSnapshot(
            gpu_type=gpu,
            avg_price=base_price,
            min_price=round(base_price * 0.8, 2),
            max_price=round(base_price * 1.3, 2),
            available_count=50,
            region="US",
        ))

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "snapshots": snapshots,
    }


@router.get("/summary")
async def get_market_summary(
    user_email: str = Depends(get_current_user_email),
):
    """
    Get market summary with overall stats
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "total_gpus_available": 5432,
        "avg_price_per_hour": 0.45,
        "most_available_gpu": "RTX 4090",
        "cheapest_gpu": "RTX 3090",
        "regions": ["US", "EU", "Asia"],
        "price_trend": "stable",
    }
