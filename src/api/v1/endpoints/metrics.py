"""
Endpoints de métricas de mercado VAST.ai.

Fornece acesso a:
- Snapshots de mercado (histórico de preços)
- Rankings de provedores por confiabilidade
- Rankings de custo-benefício
- Previsões de preço (ML)
- Comparação entre GPUs
- Reliability scores para máquinas individuais

Os relatórios Spot estão em endpoints/spot/ (modular)
"""
from fastapi import APIRouter, Query, HTTPException, status, Depends, Path
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import func

from ..schemas.metrics import (
    MarketSnapshotResponse,
    MarketSummaryResponse,
    MarketTypeSummary,
    ProviderRankingResponse,
    EfficiencyRankingResponse,
    PricePredictionResponse,
    ComparisonResponse,
    GpuComparisonItem,
)
from ..schemas.spot.reliability import (
    ReliabilityScoreItem,
    UptimeHistoryItem,
    UptimeHistoryResponse,
    MachineRatingRequest,
    MachineRatingResponse,
)
from ....config.database import get_session_factory
from ....models.metrics import (
    MarketSnapshot,
    ProviderReliability,
    CostEfficiencyRanking,
    PricePrediction,
)
from ....models.machine_history import (
    MachineStats,
    MachineUptimeHistory,
    UserMachineRating,
)
from ..dependencies import require_auth

router = APIRouter(
    prefix="/metrics",
    tags=["Market Metrics"],
    dependencies=[Depends(require_auth)]
)


@router.get("/market", response_model=List[MarketSnapshotResponse])
async def get_market_snapshots(
    gpu_name: Optional[str] = Query(None, description="Filtrar por GPU"),
    machine_type: Optional[str] = Query(
        None,
        description="Tipo: on-demand, interruptible, bid"
    ),
    hours: int = Query(24, ge=1, le=168, description="Horas de histórico"),
    limit: int = Query(100, le=1000, description="Limite de resultados"),
):
    """
    Retorna snapshots históricos do mercado.

    Dados agregados por GPU e tipo de máquina.
    Útil para visualizar tendências de preço ao longo do tempo.
    """
    db = get_session_factory()()
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        query = db.query(MarketSnapshot).filter(
            MarketSnapshot.timestamp >= start_time
        )

        if gpu_name:
            query = query.filter(MarketSnapshot.gpu_name == gpu_name)
        if machine_type:
            query = query.filter(MarketSnapshot.machine_type == machine_type)

        records = query.order_by(
            MarketSnapshot.timestamp.desc()
        ).limit(limit).all()

        return [
            MarketSnapshotResponse(
                timestamp=r.timestamp.isoformat(),
                gpu_name=r.gpu_name,
                machine_type=r.machine_type,
                min_price=r.min_price,
                max_price=r.max_price,
                avg_price=r.avg_price,
                median_price=r.median_price,
                total_offers=r.total_offers,
                available_gpus=r.available_gpus,
                verified_offers=r.verified_offers or 0,
                avg_reliability=r.avg_reliability,
                avg_total_flops=r.avg_total_flops,
                avg_dlperf=r.avg_dlperf,
                min_cost_per_tflops=r.min_cost_per_tflops,
                avg_cost_per_tflops=r.avg_cost_per_tflops,
                region_distribution=r.region_distribution,
            )
            for r in records
        ]
    finally:
        db.close()


@router.get("/market/summary")
async def get_market_summary(
    gpu_name: Optional[str] = Query(None, description="Nome da GPU (opcional - se não informado, retorna todas)"),
    machine_type: Optional[str] = Query(None, description="Tipo de máquina (opcional)"),
):
    """
    Retorna resumo de mercado agrupado por GPU e tipo de máquina.

    Se gpu_name não for especificado, retorna resumo de TODAS as GPUs.
    Formato: { "data": { "GPU_NAME": { "machine_type": { dados } } } }
    """
    db = get_session_factory()()
    try:
        # Build query for latest snapshots
        query = db.query(MarketSnapshot)

        if gpu_name:
            query = query.filter(MarketSnapshot.gpu_name == gpu_name)
        if machine_type:
            query = query.filter(MarketSnapshot.machine_type == machine_type)

        # Get all recent snapshots (last 24 hours)
        recent_time = datetime.utcnow() - timedelta(hours=24)
        snapshots = query.filter(
            MarketSnapshot.timestamp >= recent_time
        ).order_by(MarketSnapshot.timestamp.desc()).all()

        # Group by GPU and machine type - take latest for each
        seen = set()
        result = {}

        for snap in snapshots:
            key = (snap.gpu_name, snap.machine_type)
            if key in seen:
                continue
            seen.add(key)

            if snap.gpu_name not in result:
                result[snap.gpu_name] = {}

            result[snap.gpu_name][snap.machine_type] = {
                "min_price": snap.min_price,
                "max_price": snap.max_price,
                "avg_price": snap.avg_price,
                "median_price": snap.median_price,
                "total_offers": snap.total_offers,
                "available_gpus": snap.available_gpus,
                "avg_reliability": snap.avg_reliability,
                "min_cost_per_tflops": snap.min_cost_per_tflops,
                "last_update": snap.timestamp.isoformat(),
            }

        return {"data": result, "generated_at": datetime.utcnow().isoformat()}
    finally:
        db.close()


@router.get("/providers", response_model=List[ProviderRankingResponse])
async def get_provider_rankings(
    geolocation: Optional[str] = Query(None, description="Filtrar por região/país"),
    gpu_name: Optional[str] = Query(None, description="Filtrar por GPU"),
    verified_only: bool = Query(False, description="Apenas verificados"),
    min_observations: int = Query(1, ge=1, description="Mínimo de observações"),
    min_reliability: float = Query(0.0, ge=0, le=1, description="Reliability mínima"),
    order_by: str = Query("reliability_score", description="Ordenar por campo"),
    limit: int = Query(50, le=200, description="Limite de resultados"),
):
    """
    Retorna ranking de provedores por confiabilidade.

    Score considera: availability, estabilidade de preço, verificação, histórico.
    """
    db = get_session_factory()()
    try:
        query = db.query(ProviderReliability).filter(
            ProviderReliability.total_observations >= min_observations
        )

        if verified_only:
            query = query.filter(ProviderReliability.verified == True)
        if geolocation:
            query = query.filter(
                ProviderReliability.geolocation.ilike(f"%{geolocation}%")
            )
        if gpu_name:
            query = query.filter(ProviderReliability.gpu_name == gpu_name)
        if min_reliability > 0:
            query = query.filter(ProviderReliability.reliability_score >= min_reliability)

        # Ordenação
        order_col = getattr(ProviderReliability, order_by, ProviderReliability.reliability_score)
        query = query.order_by(order_col.desc())

        records = query.limit(limit).all()

        return [
            ProviderRankingResponse(
                machine_id=r.machine_id,
                hostname=r.hostname,
                geolocation=r.geolocation,
                gpu_name=r.gpu_name,
                verified=r.verified or False,
                reliability_score=r.reliability_score or 0,
                availability_score=r.availability_score or 0,
                price_stability_score=r.price_stability_score or 0,
                total_observations=r.total_observations or 0,
                avg_price=r.avg_price,
                min_price_seen=r.min_price_seen,
                max_price_seen=r.max_price_seen,
                avg_total_flops=r.avg_total_flops,
                avg_dlperf=r.avg_dlperf,
                first_seen=r.first_seen.isoformat() if r.first_seen else None,
                last_seen=r.last_seen.isoformat() if r.last_seen else None,
            )
            for r in records
        ]
    finally:
        db.close()


@router.get("/efficiency", response_model=List[EfficiencyRankingResponse])
async def get_efficiency_rankings(
    gpu_name: Optional[str] = Query(None, description="Filtrar por GPU"),
    machine_type: Optional[str] = Query(None, description="Tipo de máquina"),
    verified_only: bool = Query(False, description="Apenas verificados"),
    min_reliability: float = Query(0.0, ge=0, le=1, description="Reliability mínima"),
    max_price: Optional[float] = Query(None, description="Preço máximo por hora"),
    geolocation: Optional[str] = Query(None, description="Filtrar por região"),
    limit: int = Query(50, le=200, description="Limite de resultados"),
):
    """
    Retorna ranking de ofertas por custo-benefício.

    Score combina: $/TFLOPS, $/VRAM, reliability, verificação.
    """
    db = get_session_factory()()
    try:
        # Buscar rankings mais recentes
        latest_time = db.query(
            CostEfficiencyRanking.timestamp
        ).order_by(CostEfficiencyRanking.timestamp.desc()).first()

        if not latest_time:
            return []

        query = db.query(CostEfficiencyRanking).filter(
            CostEfficiencyRanking.timestamp == latest_time[0]
        )

        if gpu_name:
            query = query.filter(CostEfficiencyRanking.gpu_name == gpu_name)
        if machine_type:
            query = query.filter(CostEfficiencyRanking.machine_type == machine_type)
        if verified_only:
            query = query.filter(CostEfficiencyRanking.verified == True)
        if min_reliability > 0:
            query = query.filter(CostEfficiencyRanking.reliability >= min_reliability)
        if max_price:
            query = query.filter(CostEfficiencyRanking.dph_total <= max_price)
        if geolocation:
            query = query.filter(
                CostEfficiencyRanking.geolocation.ilike(f"%{geolocation}%")
            )

        records = query.order_by(
            CostEfficiencyRanking.efficiency_score.desc()
        ).limit(limit).all()

        return [
            EfficiencyRankingResponse(
                rank=r.rank_overall or 0,
                rank_in_class=r.rank_in_gpu_class,
                offer_id=r.offer_id,
                gpu_name=r.gpu_name,
                machine_type=r.machine_type,
                dph_total=r.dph_total,
                total_flops=r.total_flops,
                gpu_ram=r.gpu_ram,
                dlperf=r.dlperf,
                cost_per_tflops=r.cost_per_tflops,
                cost_per_gb_vram=r.cost_per_gb_vram,
                efficiency_score=r.efficiency_score,
                reliability=r.reliability,
                verified=r.verified or False,
                geolocation=r.geolocation,
            )
            for r in records
        ]
    finally:
        db.close()


@router.get("/predictions/{gpu_name}", response_model=PricePredictionResponse)
async def get_price_prediction(
    gpu_name: str,
    machine_type: str = Query("on-demand", description="Tipo de máquina"),
    force_refresh: bool = Query(False, description="Forçar novo cálculo"),
):
    """
    Retorna previsão de preços para uma GPU.

    Inclui:
    - Previsão por hora (próximas 24h)
    - Previsão por dia da semana
    - Melhor horário/dia para alugar
    """
    db = get_session_factory()()
    try:
        # Buscar previsão existente e válida
        if not force_refresh:
            existing = db.query(PricePrediction).filter(
                PricePrediction.gpu_name == gpu_name,
                PricePrediction.machine_type == machine_type,
                PricePrediction.valid_until >= datetime.utcnow(),
            ).order_by(PricePrediction.created_at.desc()).first()

            if existing:
                day_names = ['monday', 'tuesday', 'wednesday', 'thursday',
                             'friday', 'saturday', 'sunday']

                return PricePredictionResponse(
                    gpu_name=existing.gpu_name,
                    machine_type=existing.machine_type,
                    hourly_predictions=existing.predictions_hourly or {},
                    daily_predictions=existing.predictions_daily or {},
                    best_hour_utc=existing.best_hour_utc or 0,
                    best_day=day_names[existing.best_day_of_week] if existing.best_day_of_week is not None else 'unknown',
                    predicted_min_price=existing.predicted_min_price or 0,
                    model_confidence=existing.model_confidence or 0,
                    model_version=existing.model_version or 'unknown',
                    valid_until=existing.valid_until.isoformat() if existing.valid_until else '',
                    created_at=existing.created_at.isoformat() if existing.created_at else None,
                )

        # Se não há previsão, retornar erro (ML service precisa ser implementado)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Previsão não disponível para {gpu_name}. Execute o serviço de ML primeiro."
        )
    finally:
        db.close()


@router.get("/compare", response_model=ComparisonResponse)
async def compare_gpus(
    gpus: str = Query(..., description="GPUs separadas por vírgula"),
    machine_type: str = Query("on-demand", description="Tipo de máquina"),
):
    """
    Compara múltiplas GPUs em termos de preço e custo-benefício.
    """
    db = get_session_factory()()
    try:
        gpu_list = [g.strip() for g in gpus.split(",")]
        comparison = []

        for gpu_name in gpu_list:
            # Último snapshot
            latest = db.query(MarketSnapshot).filter(
                MarketSnapshot.gpu_name == gpu_name,
                MarketSnapshot.machine_type == machine_type,
            ).order_by(MarketSnapshot.timestamp.desc()).first()

            if latest:
                comparison.append(GpuComparisonItem(
                    gpu_name=gpu_name,
                    avg_price=latest.avg_price,
                    min_price=latest.min_price,
                    total_offers=latest.total_offers,
                    avg_reliability=latest.avg_reliability,
                    min_cost_per_tflops=latest.min_cost_per_tflops,
                    avg_total_flops=latest.avg_total_flops,
                ))

        # Ordenar por preço
        comparison.sort(key=lambda x: x.avg_price)

        # Identificar melhor custo-benefício
        best_value = None
        if comparison:
            with_tflops = [c for c in comparison if c.min_cost_per_tflops]
            if with_tflops:
                best_value = min(with_tflops, key=lambda x: x.min_cost_per_tflops)

        return ComparisonResponse(
            machine_type=machine_type,
            gpus=comparison,
            cheapest=comparison[0] if comparison else None,
            best_value=best_value,
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()


@router.get("/gpus", response_model=List[str])
async def list_available_gpus():
    """
    Lista todas as GPUs disponíveis com dados de mercado.
    """
    db = get_session_factory()()
    try:
        gpus = db.query(MarketSnapshot.gpu_name).distinct().all()
        return sorted([gpu[0] for gpu in gpus if gpu[0]])
    finally:
        db.close()


@router.get("/types", response_model=List[str])
async def list_machine_types():
    """
    Lista todos os tipos de máquina disponíveis.
    """
    return ["on-demand", "interruptible", "bid"]


@router.get("/savings/real")
async def get_real_savings(
    days: int = Query(30, ge=1, le=365, description="Período em dias"),
    user_id: Optional[str] = Query(None, description="Filtrar por usuário"),
):
    """
    Calcula a economia REAL baseada em eventos de hibernação.
    
    Analisa o histórico de hibernações e calcula:
    - Total de horas economizadas (máquinas desligadas)
    - Total em USD economizado
    - Média por dia
    - Breakdown por GPU
    """
    from ....models.instance_status import HibernationEvent, InstanceStatus
    from sqlalchemy import func
    
    db = get_session_factory()()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query base para eventos de hibernação
        query = db.query(HibernationEvent).filter(
            HibernationEvent.timestamp >= start_date,
            HibernationEvent.event_type.in_(["hibernated", "deleted"])
        )
        
        if user_id:
            # Filtrar por instâncias do usuário
            user_instances = db.query(InstanceStatus.instance_id).filter(
                InstanceStatus.user_id == user_id
            ).subquery()
            query = query.filter(HibernationEvent.instance_id.in_(user_instances))
        
        events = query.all()
        
        # Calcular economia
        total_savings_usd = 0.0
        total_idle_hours = 0.0
        gpu_breakdown = {}
        hibernation_count = 0
        
        for event in events:
            if event.savings_usd:
                total_savings_usd += event.savings_usd
            if event.idle_hours:
                total_idle_hours += event.idle_hours
            hibernation_count += 1
            
            # Buscar info da instância para breakdown
            instance = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == event.instance_id
            ).first()
            
            if instance and instance.gpu_type:
                gpu_type = instance.gpu_type
                if gpu_type not in gpu_breakdown:
                    gpu_breakdown[gpu_type] = {
                        "hibernations": 0,
                        "hours_saved": 0,
                        "usd_saved": 0
                    }
                gpu_breakdown[gpu_type]["hibernations"] += 1
                gpu_breakdown[gpu_type]["hours_saved"] += event.idle_hours or 0
                gpu_breakdown[gpu_type]["usd_saved"] += event.savings_usd or 0
        
        # Calcular médias
        avg_daily_savings = total_savings_usd / days if days > 0 else 0
        avg_daily_hours = total_idle_hours / days if days > 0 else 0
        
        # Projeção mensal
        projected_monthly = avg_daily_savings * 30
        
        return {
            "period_days": days,
            "summary": {
                "total_savings_usd": round(total_savings_usd, 2),
                "total_hours_saved": round(total_idle_hours, 1),
                "hibernation_count": hibernation_count,
                "avg_daily_savings_usd": round(avg_daily_savings, 2),
                "avg_daily_hours_saved": round(avg_daily_hours, 1),
                "projected_monthly_savings_usd": round(projected_monthly, 2),
            },
            "gpu_breakdown": gpu_breakdown,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    finally:
        db.close()


@router.get("/savings/history")
async def get_savings_history(
    days: int = Query(30, ge=1, le=365, description="Período em dias"),
    group_by: str = Query("day", description="Agrupar por: day, week, month"),
):
    """
    Retorna histórico de economia ao longo do tempo.
    
    Útil para gráficos de economia acumulada.
    """
    from ....models.instance_status import HibernationEvent
    from sqlalchemy import func, cast, Date
    
    db = get_session_factory()()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Agrupar por data
        query = db.query(
            cast(HibernationEvent.timestamp, Date).label("date"),
            func.count(HibernationEvent.id).label("count"),
            func.coalesce(func.sum(HibernationEvent.savings_usd), 0).label("savings"),
            func.coalesce(func.sum(HibernationEvent.idle_hours), 0).label("hours"),
        ).filter(
            HibernationEvent.timestamp >= start_date,
            HibernationEvent.event_type.in_(["hibernated", "deleted"])
        ).group_by(
            cast(HibernationEvent.timestamp, Date)
        ).order_by(
            cast(HibernationEvent.timestamp, Date)
        ).all()
        
        history = []
        cumulative_savings = 0
        
        for record in query:
            cumulative_savings += float(record.savings or 0)
            history.append({
                "date": record.date.isoformat() if record.date else None,
                "hibernations": record.count,
                "savings_usd": round(float(record.savings or 0), 2),
                "hours_saved": round(float(record.hours or 0), 1),
                "cumulative_savings_usd": round(cumulative_savings, 2),
            })
        
        return {
            "period_days": days,
            "group_by": group_by,
            "history": history,
            "total_cumulative_savings": round(cumulative_savings, 2),
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    finally:
        db.close()


@router.get("/hibernation/events")
async def get_hibernation_events(
    limit: int = Query(50, le=200, description="Limite de eventos"),
    instance_id: Optional[str] = Query(None, description="Filtrar por instância"),
    event_type: Optional[str] = Query(None, description="Filtrar por tipo"),
):
    """
    Lista eventos de hibernação recentes.
    """
    from ....models.instance_status import HibernationEvent
    
    db = get_session_factory()()
    try:
        query = db.query(HibernationEvent)
        
        if instance_id:
            query = query.filter(HibernationEvent.instance_id == instance_id)
        if event_type:
            query = query.filter(HibernationEvent.event_type == event_type)
        
        events = query.order_by(HibernationEvent.timestamp.desc()).limit(limit).all()

        return {
            "events": [e.to_dict() for e in events],
            "count": len(events),
        }

    finally:
        db.close()


# =============================================================================
# Reliability Router - Machine Reliability Scores
# =============================================================================

reliability_router = APIRouter(
    prefix="/reliability",
    tags=["Machine Reliability"],
    dependencies=[Depends(require_auth)]
)


def _calculate_reliability_score(
    uptime_pct: float,
    interruption_rate: float,
    avg_rating: Optional[float],
    rating_count: int
) -> float:
    """
    Calcula score de confiabilidade ponderado.

    Pesos:
    - Uptime: 40%
    - Interruption rate (inverso): 40%
    - User rating: 20%

    Se não houver ratings, repondera para 50/50 uptime/interruption.

    Args:
        uptime_pct: Percentual de uptime (0-100)
        interruption_rate: Taxa de interrupções (0-1, onde 0 é melhor)
        avg_rating: Média de ratings (1-5) ou None
        rating_count: Número de ratings

    Returns:
        Score de 0-100
    """
    # Normalizar uptime para 0-100
    uptime_score = min(100, max(0, uptime_pct))

    # Inverter interruption_rate (menos interrupções = melhor score)
    # interruption_rate 0 = 100 pontos, 1 = 0 pontos
    interruption_score = (1 - min(1.0, max(0, interruption_rate))) * 100

    # Se não houver ratings, usar apenas uptime e interruption (50/50)
    if rating_count == 0 or avg_rating is None:
        return round((uptime_score * 0.5) + (interruption_score * 0.5), 1)

    # Normalizar rating de 1-5 para 0-100
    rating_score = ((avg_rating - 1) / 4) * 100

    # Calcular score ponderado
    weighted_score = (
        (uptime_score * 0.4) +
        (interruption_score * 0.4) +
        (rating_score * 0.2)
    )

    return round(weighted_score, 1)


def _get_recommendation(score: float) -> str:
    """Retorna recomendação baseada no score."""
    if score >= 90:
        return "excellent"
    elif score >= 75:
        return "good"
    elif score >= 60:
        return "fair"
    return "poor"


@reliability_router.get("/machines/{machine_id}", response_model=ReliabilityScoreItem)
async def get_machine_reliability(
    machine_id: str = Path(..., description="ID da máquina"),
    provider: str = Query("vast", description="Provider da máquina"),
):
    """
    Retorna score de confiabilidade e métricas para uma máquina específica.

    O score é calculado com base em:
    - Uptime percentage (40% do peso)
    - Taxa de interrupções (40% do peso)
    - Ratings de usuários (20% do peso)

    Se não houver ratings, o peso é redistribuído para 50/50 uptime/interrupções.
    """
    db = get_session_factory()()
    try:
        # Buscar estatísticas da máquina
        machine_stats = db.query(MachineStats).filter(
            MachineStats.provider == provider,
            MachineStats.machine_id == machine_id
        ).first()

        # Buscar histórico de uptime dos últimos 30 dias
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        uptime_records = db.query(MachineUptimeHistory).filter(
            MachineUptimeHistory.provider == provider,
            MachineUptimeHistory.machine_id == machine_id,
            MachineUptimeHistory.date >= thirty_days_ago
        ).all()

        # Calcular uptime médio e taxa de interrupções
        if uptime_records:
            avg_uptime = sum(r.uptime_percentage for r in uptime_records) / len(uptime_records)
            total_interruptions = sum(r.interruption_count for r in uptime_records)
            # Taxa de interrupções: interrupções por dia normalizado
            interruption_rate = min(1.0, total_interruptions / (len(uptime_records) * 10))
            history_days = len(uptime_records)
        else:
            # Usar dados do MachineStats se não houver histórico diário
            avg_uptime = (machine_stats.success_rate * 100) if machine_stats else 0
            interruption_rate = 0
            history_days = 0

        # Buscar ratings de usuários
        rating_data = db.query(
            func.count(UserMachineRating.id).label('count'),
            func.avg(UserMachineRating.rating).label('avg')
        ).filter(
            UserMachineRating.provider == provider,
            UserMachineRating.machine_id == machine_id
        ).first()

        rating_count = rating_data.count or 0
        avg_rating = float(rating_data.avg) if rating_data.avg else None

        # Calcular scores
        overall_score = _calculate_reliability_score(
            uptime_pct=avg_uptime,
            interruption_rate=interruption_rate,
            avg_rating=avg_rating,
            rating_count=rating_count
        )

        # Score de uptime (0-100)
        uptime_score = min(100, max(0, avg_uptime))

        # Score de estabilidade de preço (usar taxa de sucesso como proxy)
        price_stability = (machine_stats.success_rate * 100) if machine_stats else 50

        # Score de performance (baseado no tempo médio para ficar pronto)
        if machine_stats and machine_stats.avg_time_to_ready:
            # Menos de 60s = 100, mais de 300s = 0
            perf_score = max(0, min(100, 100 - ((machine_stats.avg_time_to_ready - 60) / 2.4)))
        else:
            perf_score = 50  # Score neutro se não houver dados

        # Total de rentals (tentativas bem sucedidas)
        total_rentals = machine_stats.successful_attempts if machine_stats else 0

        return ReliabilityScoreItem(
            machine_id=int(machine_id) if machine_id.isdigit() else hash(machine_id) % 1000000,
            hostname=machine_stats.gpu_name if machine_stats else None,
            geolocation=machine_stats.geolocation if machine_stats else None,
            gpu_name=machine_stats.gpu_name if machine_stats else None,
            overall_score=overall_score,
            uptime_score=uptime_score,
            price_stability_score=round(price_stability, 1),
            performance_score=round(perf_score, 1),
            history_days=history_days,
            total_rentals=total_rentals,
            recommendation=_get_recommendation(overall_score),
            user_rating_count=rating_count,
            user_rating_average=round(avg_rating, 2) if avg_rating else None,
        )

    except Exception as e:
        # Em caso de erro, retornar dados mínimos em vez de falhar
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dados de confiabilidade não encontrados para máquina {machine_id}: {str(e)}"
        )
    finally:
        db.close()


@reliability_router.get("/machines/{machine_id}/history", response_model=UptimeHistoryResponse)
async def get_machine_reliability_history(
    machine_id: str = Path(..., description="ID da máquina"),
    provider: str = Query("vast", description="Provider da máquina"),
    days: int = Query(30, ge=1, le=90, description="Número de dias de histórico (máx 90)"),
):
    """
    Retorna histórico de uptime e interrupções de uma máquina.

    Dados diários dos últimos N dias (padrão: 30 dias) incluindo:
    - Percentual de uptime por dia
    - Contagem de interrupções
    - Duração média de interrupções
    - Resumo estatístico do período
    """
    db = get_session_factory()()
    try:
        # Calcular data de início
        start_date = datetime.utcnow() - timedelta(days=days)

        # Buscar registros de histórico
        uptime_records = db.query(MachineUptimeHistory).filter(
            MachineUptimeHistory.provider == provider,
            MachineUptimeHistory.machine_id == machine_id,
            MachineUptimeHistory.date >= start_date.date()
        ).order_by(MachineUptimeHistory.date.desc()).all()

        # Converter para items de resposta
        history_items = [
            UptimeHistoryItem(
                date=record.date.isoformat() if record.date else None,
                uptime_percentage=record.uptime_percentage or 0.0,
                interruption_count=record.interruption_count or 0,
                uptime_seconds=record.uptime_seconds,
                avg_interruption_duration=record.avg_interruption_duration_seconds,
            )
            for record in uptime_records
        ]

        # Calcular resumo estatístico
        summary = None
        if uptime_records:
            total_uptime = sum(r.uptime_percentage or 0 for r in uptime_records)
            total_interruptions = sum(r.interruption_count or 0 for r in uptime_records)
            avg_uptime = total_uptime / len(uptime_records)

            # Encontrar min e max uptime
            uptimes = [r.uptime_percentage for r in uptime_records if r.uptime_percentage is not None]
            min_uptime = min(uptimes) if uptimes else 0
            max_uptime = max(uptimes) if uptimes else 0

            summary = {
                "avg_uptime_percentage": round(avg_uptime, 2),
                "min_uptime_percentage": round(min_uptime, 2),
                "max_uptime_percentage": round(max_uptime, 2),
                "total_interruptions": total_interruptions,
                "days_with_data": len(uptime_records),
            }

        return UptimeHistoryResponse(
            machine_id=machine_id,
            provider=provider,
            days_requested=days,
            total_records=len(uptime_records),
            history=history_items,
            summary=summary,
            generated_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar histórico de uptime para máquina {machine_id}: {str(e)}"
        )
    finally:
        db.close()


@reliability_router.post("/machines/{machine_id}/rate", response_model=MachineRatingResponse)
async def rate_machine(
    machine_id: str = Path(..., description="ID da máquina a ser avaliada"),
    request: MachineRatingRequest = ...,
):
    """
    Submete uma avaliação de 1-5 estrelas para uma máquina.

    O rating é usado no cálculo do score de confiabilidade da máquina,
    contribuindo com 20% do peso no score final.

    Cada usuário pode avaliar cada máquina apenas uma vez.
    Se uma avaliação já existir, ela será atualizada.

    Args:
        machine_id: ID da máquina no provider
        request: Dados da avaliação (rating 1-5, comentário opcional)

    Returns:
        Confirmação da avaliação submetida
    """
    db = get_session_factory()()
    try:
        # TODO: Obter user_id do token de autenticação
        # Por enquanto, usar um placeholder
        user_id = "anonymous_user"

        # Verificar se já existe uma avaliação deste usuário para esta máquina
        existing_rating = db.query(UserMachineRating).filter(
            UserMachineRating.provider == request.provider,
            UserMachineRating.machine_id == machine_id,
            UserMachineRating.user_id == user_id
        ).first()

        if existing_rating:
            # Atualizar avaliação existente
            existing_rating.rating = request.rating
            existing_rating.comment = request.comment
            existing_rating.rental_duration_hours = request.rental_duration_hours
            existing_rating.instance_id = request.instance_id
            existing_rating.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_rating)

            return MachineRatingResponse(
                id=existing_rating.id,
                machine_id=machine_id,
                provider=request.provider,
                user_id=user_id,
                rating=existing_rating.rating,
                comment=existing_rating.comment,
                created_at=existing_rating.created_at.isoformat() if existing_rating.created_at else datetime.utcnow().isoformat(),
                message="Rating updated successfully"
            )

        # Criar nova avaliação
        new_rating = UserMachineRating(
            provider=request.provider,
            machine_id=machine_id,
            user_id=user_id,
            rating=request.rating,
            comment=request.comment,
            rental_duration_hours=request.rental_duration_hours,
            instance_id=request.instance_id,
        )

        # Buscar nome da GPU da máquina se disponível
        machine_stats = db.query(MachineStats).filter(
            MachineStats.provider == request.provider,
            MachineStats.machine_id == machine_id
        ).first()
        if machine_stats:
            new_rating.gpu_name = machine_stats.gpu_name

        db.add(new_rating)
        db.commit()
        db.refresh(new_rating)

        return MachineRatingResponse(
            id=new_rating.id,
            machine_id=machine_id,
            provider=request.provider,
            user_id=user_id,
            rating=new_rating.rating,
            comment=new_rating.comment,
            created_at=new_rating.created_at.isoformat() if new_rating.created_at else datetime.utcnow().isoformat(),
            message="Rating submitted successfully"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar avaliação para máquina {machine_id}: {str(e)}"
        )
    finally:
        db.close()
