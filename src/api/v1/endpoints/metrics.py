"""
Endpoints de métricas de mercado VAST.ai.

Fornece acesso a:
- Snapshots de mercado (histórico de preços)
- Rankings de provedores por confiabilidade
- Rankings de custo-benefício
- Previsões de preço (ML)
- Comparação entre GPUs

Os relatórios Spot estão em endpoints/spot/ (modular)
"""
from fastapi import APIRouter, Query, HTTPException, status, Depends
from typing import Optional, List
from datetime import datetime, timedelta

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
from ....config.database import SessionLocal
from ....models.metrics import (
    MarketSnapshot,
    ProviderReliability,
    CostEfficiencyRanking,
    PricePrediction,
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
    db = SessionLocal()
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
    db = SessionLocal()
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
    db = SessionLocal()
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
    db = SessionLocal()
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
    db = SessionLocal()
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
    db = SessionLocal()
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
    db = SessionLocal()
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
