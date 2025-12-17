"""
Endpoint: Best GPU for LLM ($/Token).

Ranking de GPUs por custo-eficiência para inferência LLM.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta

from ...schemas.spot.llm_gpu import LLMGpuItem, BestGpuForLLMResponse
from .....config.database import SessionLocal
from .....models.metrics import MarketSnapshot
from .constants import GPU_SPECS, LLM_MODELS

router = APIRouter(tags=["Spot LLM GPU"])


@router.get("/llm-gpus", response_model=BestGpuForLLMResponse)
async def get_best_gpu_for_llm(
    min_vram: int = Query(8, ge=4, description="VRAM mínima em GB"),
    max_price: Optional[float] = Query(None, description="Preço máximo por hora"),
    model_size: Optional[str] = Query(None, description="Tamanho do modelo: 7B, 13B, 70B"),
):
    """
    Melhores GPUs para LLM ($/Token).

    Ranking de GPUs por custo-eficiência para inferência LLM.
    Considera VRAM, tokens/segundo e preço.
    """
    db = SessionLocal()
    try:
        recent_time = datetime.utcnow() - timedelta(hours=24)
        snapshots = db.query(MarketSnapshot).filter(
            MarketSnapshot.timestamp >= recent_time,
            MarketSnapshot.machine_type == "interruptible",
        ).order_by(MarketSnapshot.timestamp.desc()).all()

        # Agrupar por GPU
        gpu_data = {}
        for snap in snapshots:
            if snap.gpu_name not in gpu_data:
                gpu_data[snap.gpu_name] = snap

        items = []
        for gpu_name, snap in gpu_data.items():
            specs = GPU_SPECS.get(gpu_name)
            if not specs:
                continue

            vram = specs["vram"]
            if vram < min_vram:
                continue

            price = snap.avg_price or 0
            if max_price and price > max_price:
                continue

            tokens_per_sec = specs["tokens_per_sec"]
            tokens_per_hour = tokens_per_sec * 3600

            if price > 0:
                cost_per_million = (price / tokens_per_hour) * 1_000_000
            else:
                cost_per_million = 0

            # Encontrar modelos recomendados
            recommended = []
            for vram_req, models in LLM_MODELS.items():
                if vram >= vram_req:
                    recommended = models

            # Filtrar por tamanho de modelo
            if model_size:
                recommended = [m for m in recommended if model_size in m]

            # Calcular score de eficiência
            efficiency = 100 - (cost_per_million * 10)
            efficiency = max(0, min(100, efficiency))

            item = LLMGpuItem(
                gpu_name=gpu_name,
                vram_gb=vram,
                price_per_hour=round(price, 4),
                estimated_tokens_per_second=tokens_per_sec,
                cost_per_million_tokens=round(cost_per_million, 4),
                recommended_models=recommended[:3],
                efficiency_score=round(efficiency, 1),
                available_count=snap.available_gpus or 0,
                machine_type="interruptible",
            )
            items.append(item)

        items.sort(key=lambda x: x.cost_per_million_tokens if x.cost_per_million_tokens > 0 else float('inf'))

        best_value = items[0] if items else None
        best_perf = max(items, key=lambda x: x.estimated_tokens_per_second) if items else None

        return BestGpuForLLMResponse(
            items=items,
            best_value=best_value,
            best_performance=best_perf,
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
