"""
Failover API Endpoints.

Endpoints para executar e monitorar failover:
- Executar failover manualmente
- Verificar prontidão para failover
- Histórico de failovers
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from src.services.failover_orchestrator import (
    FailoverOrchestrator,
    OrchestratedFailoverResult,
    get_failover_orchestrator,
    execute_orchestrated_failover,
)
from src.services.warmpool import (
    RegionalVolumeFailover,
    RegionalFailoverResult,
    get_regional_volume_failover,
)
from src.config.failover_settings import get_failover_settings_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/failover", tags=["failover"])


# ============ Schemas ============

class FailoverRequest(BaseModel):
    """Request para executar failover"""
    machine_id: int = Field(..., description="ID da máquina (interno)")
    gpu_instance_id: int = Field(..., description="ID da instância GPU (Vast.ai)")
    ssh_host: str = Field(..., description="Host SSH atual")
    ssh_port: int = Field(..., description="Porta SSH atual")
    workspace_path: str = Field("/workspace", description="Caminho do workspace")
    force_strategy: Optional[str] = Field(
        None,
        description="Forçar estratégia específica: warm_pool, cpu_standby, both"
    )


class FailoverResponse(BaseModel):
    """Resposta de execução de failover"""
    success: bool
    failover_id: str
    machine_id: int
    strategy_attempted: str
    strategy_succeeded: Optional[str] = None

    # Nova instância
    new_gpu_id: Optional[int] = None
    new_ssh_host: Optional[str] = None
    new_ssh_port: Optional[int] = None
    new_gpu_name: Optional[str] = None

    # Timing
    warm_pool_attempt_ms: int = 0
    cpu_standby_attempt_ms: int = 0
    total_ms: int = 0

    # Erros
    error: Optional[str] = None
    warm_pool_error: Optional[str] = None
    cpu_standby_error: Optional[str] = None


class ReadinessResponse(BaseModel):
    """Resposta de verificação de prontidão"""
    machine_id: int
    effective_strategy: str
    warm_pool_ready: bool
    warm_pool_status: Optional[Dict[str, Any]] = None
    cpu_standby_ready: bool
    cpu_standby_status: Optional[Dict[str, Any]] = None
    overall_ready: bool


class StrategyStatusResponse(BaseModel):
    """Status resumido das estratégias"""
    machine_id: int
    effective_strategy: str
    warm_pool: Dict[str, Any]
    cpu_standby: Dict[str, Any]
    recommended_action: Optional[str] = None


# ============ Endpoints ============

@router.post("/execute", response_model=FailoverResponse)
async def execute_failover(request: FailoverRequest):
    """
    Executa failover para uma máquina.

    O sistema tentará as estratégias configuradas na ordem:
    1. GPU Warm Pool (se habilitado e disponível)
    2. CPU Standby + Snapshot (como fallback)

    Use `force_strategy` para forçar uma estratégia específica.
    """
    try:
        result = await execute_orchestrated_failover(
            machine_id=request.machine_id,
            gpu_instance_id=request.gpu_instance_id,
            ssh_host=request.ssh_host,
            ssh_port=request.ssh_port,
            workspace_path=request.workspace_path,
            force_strategy=request.force_strategy,
        )

        return FailoverResponse(
            success=result.success,
            failover_id=result.failover_id,
            machine_id=result.machine_id,
            strategy_attempted=result.strategy_attempted,
            strategy_succeeded=result.strategy_succeeded,
            new_gpu_id=result.new_gpu_id,
            new_ssh_host=result.new_ssh_host,
            new_ssh_port=result.new_ssh_port,
            new_gpu_name=result.new_gpu_name,
            warm_pool_attempt_ms=result.warm_pool_attempt_ms,
            cpu_standby_attempt_ms=result.cpu_standby_attempt_ms,
            total_ms=result.total_ms,
            error=result.error,
            warm_pool_error=result.warm_pool_error,
            cpu_standby_error=result.cpu_standby_error,
        )

    except Exception as e:
        logger.error(f"Failed to execute failover: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/readiness/{machine_id}", response_model=ReadinessResponse)
async def check_readiness(machine_id: int):
    """
    Verifica se a máquina está pronta para failover.

    Retorna status de cada estratégia configurada:
    - Warm Pool: se tem standby GPU disponível
    - CPU Standby: se tem associação com CPU standby
    """
    try:
        orchestrator = get_failover_orchestrator()
        result = await orchestrator.check_failover_readiness(machine_id)

        return ReadinessResponse(**result)

    except Exception as e:
        logger.error(f"Failed to check readiness: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{machine_id}", response_model=StrategyStatusResponse)
async def get_failover_status(machine_id: int):
    """
    Retorna status detalhado das estratégias de failover.

    Inclui recomendações de ação se necessário.
    """
    try:
        settings_manager = get_failover_settings_manager()
        effective_config = settings_manager.get_effective_config(machine_id)

        # Verificar readiness
        orchestrator = get_failover_orchestrator()
        readiness = await orchestrator.check_failover_readiness(machine_id)

        # Determinar ação recomendada
        recommended_action = None
        strategy = effective_config['effective_strategy']

        if strategy == 'disabled':
            recommended_action = "Failover está desabilitado. Considere habilitar para proteção."

        elif strategy in ['warm_pool', 'both']:
            if not readiness['warm_pool_ready']:
                if readiness.get('warm_pool_status', {}).get('state') == 'disabled':
                    recommended_action = "Provisione um warm pool para failover rápido."
                else:
                    recommended_action = "Warm pool não está pronto. Verifique o status."

        elif strategy == 'cpu_standby':
            if not readiness['cpu_standby_ready']:
                recommended_action = "Configure CPU Standby para esta máquina."

        return StrategyStatusResponse(
            machine_id=machine_id,
            effective_strategy=strategy,
            warm_pool=effective_config['warm_pool'],
            cpu_standby=effective_config['cpu_standby'],
            recommended_action=recommended_action,
        )

    except Exception as e:
        logger.error(f"Failed to get failover status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/{machine_id}")
async def test_failover(
    machine_id: int,
    gpu_instance_id: int = Query(..., description="ID da instância GPU"),
    ssh_host: str = Query(..., description="Host SSH atual"),
    ssh_port: int = Query(..., description="Porta SSH atual"),
    strategy: Optional[str] = Query(None, description="Estratégia a testar"),
    dry_run: bool = Query(True, description="Se True, apenas simula sem executar"),
):
    """
    Testa failover para uma máquina.

    Com dry_run=True (padrão), apenas verifica se o failover seria possível.
    Com dry_run=False, executa o failover real.

    ATENÇÃO: dry_run=False vai realmente executar o failover!
    """
    try:
        orchestrator = get_failover_orchestrator()

        if dry_run:
            # Apenas verificar readiness
            readiness = await orchestrator.check_failover_readiness(machine_id)

            return {
                "dry_run": True,
                "would_succeed": readiness['overall_ready'],
                "readiness": readiness,
                "message": "Use dry_run=False para executar o failover real"
            }

        else:
            # Executar failover real
            result = await orchestrator.execute_failover(
                machine_id=machine_id,
                gpu_instance_id=gpu_instance_id,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                force_strategy=strategy,
            )

            return {
                "dry_run": False,
                "success": result.success,
                "failover_id": result.failover_id,
                "strategy_succeeded": result.strategy_succeeded,
                "total_ms": result.total_ms,
                "new_instance": {
                    "gpu_id": result.new_gpu_id,
                    "ssh_host": result.new_ssh_host,
                    "ssh_port": result.new_ssh_port,
                } if result.success else None,
                "error": result.error,
            }

    except Exception as e:
        logger.error(f"Failed to test failover: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def list_strategies():
    """
    Lista as estratégias de failover disponíveis.
    """
    return {
        "strategies": [
            {
                "id": "warm_pool",
                "name": "GPU Warm Pool",
                "description": "Failover rápido (~30-60s) usando GPU standby no mesmo host",
                "recovery_time": "30-60 segundos",
                "cost": "Apenas armazenamento quando standby está parado",
                "requirements": [
                    "Host com múltiplas GPUs",
                    "Volume compartilhado VAST.ai",
                ],
            },
            {
                "id": "cpu_standby",
                "name": "CPU Standby + Snapshot",
                "description": "Failover via snapshot e nova GPU (~10-20min)",
                "recovery_time": "10-20 minutos",
                "cost": "CPU standby no GCP + armazenamento de snapshots",
                "requirements": [
                    "Credenciais GCP",
                    "Bucket B2/S3 para snapshots",
                ],
            },
            {
                "id": "both",
                "name": "Warm Pool + CPU Standby",
                "description": "Warm Pool como primário, CPU Standby como fallback",
                "recovery_time": "30-60s (warm pool) ou 10-20min (fallback)",
                "cost": "Combinado de ambas estratégias",
                "requirements": [
                    "Requisitos de ambas estratégias",
                ],
            },
            {
                "id": "regional_volume",
                "name": "Regional Volume Failover",
                "description": "Failover usando volume persistente regional (~30-60s)",
                "recovery_time": "30-60 segundos",
                "cost": "Volume regional (~$1-3/mês para 50GB)",
                "requirements": [
                    "Volume VAST.ai na região",
                    "GPUs disponíveis na mesma região",
                ],
            },
            {
                "id": "all",
                "name": "Todas as Estratégias",
                "description": "Warm Pool + Regional Volume + CPU Standby",
                "recovery_time": "6s (warm) → 30-60s (regional) → 10-20min (cpu)",
                "cost": "Combinado de todas estratégias",
                "requirements": [
                    "Requisitos de todas estratégias",
                ],
            },
            {
                "id": "disabled",
                "name": "Desabilitado",
                "description": "Nenhuma proteção de failover automático",
                "recovery_time": "Manual",
                "cost": "Nenhum",
                "requirements": [],
            },
        ]
    }


# ============ Regional Volume Failover Endpoints ============

class RegionalVolumeRequest(BaseModel):
    """Request para criar volume regional"""
    region: str = Field(..., description="Código da região (ex: US, DE, PL)")
    size_gb: int = Field(50, description="Tamanho do volume em GB")
    name: Optional[str] = Field(None, description="Nome opcional do volume")


class RegionalFailoverRequest(BaseModel):
    """Request para executar failover regional"""
    volume_id: int = Field(..., description="ID do volume existente")
    region: str = Field(..., description="Região do volume")
    old_instance_id: Optional[int] = Field(None, description="ID da instância antiga")
    preferred_gpus: Optional[List[str]] = Field(
        None,
        description="GPUs preferidas (ex: ['RTX_4090', 'RTX_3090'])"
    )
    max_price: Optional[float] = Field(None, description="Preço máximo por hora")
    use_spot: bool = Field(True, description="Usar instâncias spot")
    docker_image: str = Field("pytorch/pytorch:latest", description="Imagem Docker")
    mount_path: str = Field("/data", description="Caminho de montagem")


class RegionalVolumeResponse(BaseModel):
    """Resposta de criação de volume"""
    success: bool
    volume_id: Optional[int] = None
    region: Optional[str] = None
    size_gb: Optional[int] = None
    error: Optional[str] = None


class RegionalFailoverResponse(BaseModel):
    """Resposta de failover regional"""
    success: bool
    volume_id: int
    old_instance_id: Optional[int] = None
    new_instance_id: Optional[int] = None
    new_gpu_name: Optional[str] = None
    region: Optional[str] = None
    failover_time_seconds: float = 0.0
    message: str = ""
    error: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None


@router.post("/regional-volume/create", response_model=RegionalVolumeResponse)
async def create_regional_volume(request: RegionalVolumeRequest):
    """
    Cria um volume regional para failover.

    O volume persiste na região mesmo quando a GPU é destruída.
    """
    try:
        failover = get_regional_volume_failover()
        result = await failover.create_regional_volume(
            region=request.region,
            size_gb=request.size_gb,
            name=request.name,
        )

        if result:
            return RegionalVolumeResponse(
                success=True,
                volume_id=result.volume_id,
                region=result.region,
                size_gb=result.size_gb,
            )
        else:
            return RegionalVolumeResponse(
                success=False,
                error="Failed to create volume",
            )

    except Exception as e:
        logger.error(f"Failed to create regional volume: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/regional-volume/failover", response_model=RegionalFailoverResponse)
async def execute_regional_failover(request: RegionalFailoverRequest):
    """
    Executa failover usando volume regional.

    Monta o volume existente em uma nova GPU da mesma região.
    Tempo estimado: 30-60 segundos.
    """
    try:
        failover = get_regional_volume_failover()
        result = await failover.execute_failover(
            volume_id=request.volume_id,
            region=request.region,
            old_instance_id=request.old_instance_id,
            preferred_gpus=request.preferred_gpus,
            max_price=request.max_price,
            use_spot=request.use_spot,
            docker_image=request.docker_image,
            mount_path=request.mount_path,
        )

        return RegionalFailoverResponse(
            success=result.success,
            volume_id=result.volume_id,
            old_instance_id=result.old_instance_id,
            new_instance_id=result.new_instance_id,
            new_gpu_name=result.new_gpu_name,
            region=result.region,
            failover_time_seconds=result.failover_time_seconds,
            message=result.message,
            error=result.error,
            ssh_host=result.ssh_host,
            ssh_port=result.ssh_port,
        )

    except Exception as e:
        logger.error(f"Failed to execute regional failover: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regional-volume/list")
async def list_regional_volumes():
    """
    Lista todos os volumes regionais do usuário.
    """
    try:
        failover = get_regional_volume_failover()
        volumes = await failover.list_user_volumes()

        return {
            "volumes": volumes,
            "count": len(volumes),
        }

    except Exception as e:
        logger.error(f"Failed to list volumes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regional-volume/{volume_id}")
async def get_regional_volume(volume_id: int):
    """
    Obtém informações de um volume específico.
    """
    try:
        failover = get_regional_volume_failover()
        volume = await failover.get_volume_info(volume_id)

        if volume:
            return volume
        else:
            raise HTTPException(status_code=404, detail="Volume not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get volume: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/regional-volume/{volume_id}")
async def delete_regional_volume(volume_id: int):
    """
    Deleta um volume regional.

    O volume deve estar desanexado de qualquer instância.
    """
    try:
        failover = get_regional_volume_failover()
        success = await failover.delete_volume(volume_id)

        if success:
            return {"success": True, "message": f"Volume {volume_id} deleted"}
        else:
            return {"success": False, "error": "Failed to delete volume"}

    except Exception as e:
        logger.error(f"Failed to delete volume: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regional-volume/search/{region}")
async def search_gpus_in_region(
    region: str,
    max_price: Optional[float] = Query(None, description="Preço máximo por hora"),
    gpu_name: Optional[str] = Query(None, description="Nome da GPU específica"),
):
    """
    Busca GPUs disponíveis em uma região para failover.
    """
    try:
        failover = get_regional_volume_failover()
        preferred_gpus = [gpu_name] if gpu_name else None

        gpu_offer = await failover.find_gpu_in_region(
            region=region,
            preferred_gpus=preferred_gpus,
            max_price=max_price,
        )

        if gpu_offer:
            return {
                "found": True,
                "offer": {
                    "offer_id": gpu_offer.offer_id,
                    "gpu_name": gpu_offer.gpu_name,
                    "num_gpus": gpu_offer.num_gpus,
                    "price_per_hour": gpu_offer.price_per_hour,
                    "reliability": gpu_offer.reliability,
                    "geolocation": gpu_offer.geolocation,
                },
            }
        else:
            return {
                "found": False,
                "message": f"No GPU available in region {region}",
            }

    except Exception as e:
        logger.error(f"Failed to search GPUs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
