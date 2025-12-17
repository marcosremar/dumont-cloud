"""
Endpoint: Spot Fleet Strategy.

Estratégia de fleet para máxima eficiência e resiliência.
"""
from fastapi import APIRouter, Query
from datetime import datetime, timedelta

from ...schemas.spot.fleet_strategy import FleetStrategyGpu, FleetStrategyResponse
from .....config.database import SessionLocal
from .....models.metrics import MarketSnapshot
from .constants import GPU_SPECS

router = APIRouter(tags=["Spot Fleet Strategy"])


@router.get("/fleet-strategy", response_model=FleetStrategyResponse)
async def get_fleet_strategy(
    budget_monthly: float = Query(1000, ge=100, description="Orçamento mensal em USD"),
    min_gpus: int = Query(3, ge=1, description="Mínimo de GPUs"),
    priority: str = Query("balanced", description="Prioridade: cost, performance, balanced"),
):
    """
    Estratégia de Fleet Spot.

    Recomendação de mix de GPUs para máxima eficiência e resiliência.
    Considera orçamento, prioridade e distribuição de risco.
    """
    db = SessionLocal()
    try:
        recent_time = datetime.utcnow() - timedelta(hours=24)
        snapshots = db.query(MarketSnapshot).filter(
            MarketSnapshot.machine_type == "interruptible",
            MarketSnapshot.timestamp >= recent_time,
        ).order_by(MarketSnapshot.timestamp.desc()).all()

        # Agrupar por GPU
        gpu_data = {}
        for snap in snapshots:
            if snap.gpu_name not in gpu_data:
                gpu_data[snap.gpu_name] = snap

        # Calcular custo mensal por GPU (8h/dia * 30 dias)
        hours_per_month = 8 * 30
        gpu_costs = []

        for gpu, snap in gpu_data.items():
            price = snap.avg_price or 0
            monthly_cost = price * hours_per_month
            reliability = snap.avg_reliability or 0.7

            gpu_costs.append({
                "gpu": gpu,
                "price": price,
                "monthly": monthly_cost,
                "reliability": reliability,
            })

        # Ordenar por estratégia
        if priority == "cost":
            gpu_costs.sort(key=lambda x: x["monthly"])
        elif priority == "performance":
            gpu_costs.sort(key=lambda x: -GPU_SPECS.get(x["gpu"], {}).get("tflops", 0))
        else:  # balanced
            gpu_costs.sort(key=lambda x: x["monthly"] / max(GPU_SPECS.get(x["gpu"], {}).get("tflops", 1), 1))

        # Alocar GPUs
        allocated = []
        remaining_budget = budget_monthly
        total_gpus = 0

        for i, g in enumerate(gpu_costs):
            if remaining_budget < g["monthly"] or total_gpus >= min_gpus * 2:
                break

            count = min(
                int(remaining_budget / max(g["monthly"], 1)),
                3
            )
            if count < 1:
                continue

            # Role baseado na posição
            if i == 0:
                role = "primary"
                alloc_pct = 50
            elif i == 1:
                role = "backup"
                alloc_pct = 30
            else:
                role = "burst"
                alloc_pct = 20

            allocated.append(FleetStrategyGpu(
                gpu_name=g["gpu"],
                allocation_percent=alloc_pct,
                count=count,
                spot_price=round(g["price"], 4),
                reliability_score=round(g["reliability"], 2),
                role=role,
            ))

            remaining_budget -= g["monthly"] * count
            total_gpus += count

        # Calcular métricas
        total_monthly = budget_monthly - remaining_budget

        # Estimar economia vs on-demand
        ondemand_equivalent = total_monthly * 1.6
        savings = ondemand_equivalent - total_monthly

        # Resiliência
        avg_reliability = sum(g.reliability_score for g in allocated) / len(allocated) if allocated else 0
        if avg_reliability > 0.85 and len(allocated) >= 2:
            resilience = "high"
        elif avg_reliability > 0.7:
            resilience = "medium"
        else:
            resilience = "low"

        # Recomendações
        recommendations = []
        if len(allocated) < 2:
            recommendations.append("Adicione mais tipos de GPU para maior resiliência")
        if avg_reliability < 0.8:
            recommendations.append("Considere provedores com maior reliability")
        if priority == "cost":
            recommendations.append("Monitore preços spot para oportunidades de economia")
        recommendations.append(f"Economia estimada vs on-demand: ${savings:.2f}/mês")

        strategy_name = f"Fleet {priority.title()} - {total_gpus} GPUs"

        return FleetStrategyResponse(
            strategy_name=strategy_name,
            total_gpus=total_gpus,
            estimated_monthly_cost=round(total_monthly, 2),
            estimated_savings_vs_ondemand=round(savings, 2),
            interruption_resilience=resilience,
            gpus=allocated,
            recommendations=recommendations,
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
