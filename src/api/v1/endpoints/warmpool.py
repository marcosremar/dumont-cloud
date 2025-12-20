"""
Warm Pool API Endpoints.

Endpoints para gerenciar GPU Warm Pool:
- Status do warm pool
- Listar hosts com multiplas GPUs
- Habilitar/desabilitar warm pool
- Provisionar manualmente
- Testar failover
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.services.warmpool import (
    WarmPoolManager, WarmPoolState, get_warm_pool_manager,
    HostFinder, MultiGPUHost
)
from src.config.failover_settings import get_failover_settings_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/warmpool", tags=["warmpool"])


# ============ Schemas ============

class WarmPoolStatusResponse(BaseModel):
    """Resposta do status do warm pool"""
    machine_id: int
    state: str
    host_machine_id: Optional[int] = None
    volume_id: Optional[int] = None
    primary_gpu_id: Optional[int] = None
    standby_gpu_id: Optional[int] = None
    standby_state: str = "none"
    primary_ssh_host: Optional[str] = None
    primary_ssh_port: Optional[int] = None
    last_health_check: Optional[str] = None
    failover_count: int = 0
    last_failover_at: Optional[str] = None
    error_message: Optional[str] = None


class GPUOfferResponse(BaseModel):
    """Oferta de GPU"""
    offer_id: int
    machine_id: int
    gpu_name: str
    num_gpus: int
    price_per_hour: float
    reliability: float
    verified: bool
    geolocation: str


class MultiGPUHostResponse(BaseModel):
    """Host com multiplas GPUs"""
    machine_id: int
    total_gpus: int
    available_gpus: int
    gpu_name: str
    avg_price_per_hour: float
    reliability: float
    verified: bool
    geolocation: str
    can_create_warm_pool: bool
    offers: List[GPUOfferResponse] = []


class HostsListResponse(BaseModel):
    """Lista de hosts"""
    hosts: List[MultiGPUHostResponse]
    count: int


class ProvisionRequest(BaseModel):
    """Request para provisionar warm pool"""
    machine_id: int = Field(..., description="ID da maquina/instancia")
    host_machine_id: int = Field(..., description="ID do host VAST.ai com multiplas GPUs")
    gpu_name: Optional[str] = Field(None, description="Nome da GPU (ex: RTX_4090)")
    image: str = Field(
        "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        description="Imagem Docker"
    )
    disk_size: int = Field(50, description="Tamanho do disco em GB")
    volume_size: int = Field(100, description="Tamanho do volume em GB")


class ProvisionResponse(BaseModel):
    """Resposta do provisioning"""
    success: bool
    message: str
    status: Optional[WarmPoolStatusResponse] = None


class FailoverTestResponse(BaseModel):
    """Resposta do teste de failover"""
    success: bool
    message: str
    recovery_time_seconds: Optional[float] = None
    new_primary_gpu_id: Optional[int] = None


class EnableDisableResponse(BaseModel):
    """Resposta de enable/disable"""
    status: str
    message: str
    fallback: Optional[str] = None


# ============ Helper para obter API key ============

def get_vast_api_key() -> str:
    """Obtem API key do VAST.ai das configuracoes"""
    import os
    api_key = os.getenv("VAST_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="VAST_API_KEY not configured")
    return api_key


# ============ Endpoints ============

@router.get("/status/{machine_id}", response_model=WarmPoolStatusResponse)
async def get_status(machine_id: int):
    """
    Retorna status do warm pool para uma maquina.

    - **machine_id**: ID da maquina/instancia
    """
    try:
        api_key = get_vast_api_key()
        manager = get_warm_pool_manager(machine_id, api_key)
        status = manager.get_status()
        return WarmPoolStatusResponse(**status)
    except Exception as e:
        logger.error(f"Failed to get warm pool status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hosts", response_model=HostsListResponse)
async def list_multi_gpu_hosts(
    gpu_name: Optional[str] = Query(None, description="Filtrar por GPU (ex: RTX_4090)"),
    min_gpus: int = Query(2, description="Minimo de GPUs por host"),
    max_price: Optional[float] = Query(None, description="Preco maximo por hora"),
    verified: bool = Query(True, description="Apenas hosts verificados"),
):
    """
    Lista hosts com multiplas GPUs disponiveis.

    Util para encontrar hosts onde e possivel criar um warm pool.
    """
    try:
        api_key = get_vast_api_key()
        host_finder = HostFinder(api_key)

        hosts = await host_finder.find_multi_gpu_hosts(
            gpu_name=gpu_name,
            min_gpus=min_gpus,
            max_price=max_price,
            verified=verified,
        )

        host_responses = []
        for host in hosts:
            offers = [
                GPUOfferResponse(
                    offer_id=o.offer_id,
                    machine_id=o.machine_id,
                    gpu_name=o.gpu_name,
                    num_gpus=o.num_gpus,
                    price_per_hour=o.price_per_hour,
                    reliability=o.reliability,
                    verified=o.verified,
                    geolocation=o.geolocation,
                )
                for o in host.offers[:5]  # Limitar a 5 ofertas por host
            ]

            host_responses.append(MultiGPUHostResponse(
                machine_id=host.machine_id,
                total_gpus=host.total_gpus,
                available_gpus=host.available_gpus,
                gpu_name=host.gpu_name,
                avg_price_per_hour=host.avg_price_per_hour,
                reliability=host.reliability,
                verified=host.verified,
                geolocation=host.geolocation,
                can_create_warm_pool=host.can_create_warm_pool,
                offers=offers,
            ))

        return HostsListResponse(hosts=host_responses, count=len(host_responses))

    except Exception as e:
        logger.error(f"Failed to list multi-GPU hosts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/provision", response_model=ProvisionResponse)
async def provision_warm_pool(request: ProvisionRequest):
    """
    Provisiona um warm pool em um host especifico.

    Cria:
    1. Volume compartilhado
    2. GPU principal (running)
    3. GPU standby (stopped)
    """
    try:
        api_key = get_vast_api_key()
        host_finder = HostFinder(api_key)

        # Buscar host
        host = await host_finder.get_host_by_machine_id(request.host_machine_id)

        if not host:
            return ProvisionResponse(
                success=False,
                message=f"Host {request.host_machine_id} not found"
            )

        if not host.can_create_warm_pool:
            return ProvisionResponse(
                success=False,
                message=f"Host {request.host_machine_id} has only {host.available_gpus} GPUs, need 2+"
            )

        # Obter ou criar manager
        manager = get_warm_pool_manager(request.machine_id, api_key)

        # Atualizar config do volume
        manager.config.volume_size_gb = request.volume_size

        # Provisionar
        success = await manager.provision_warm_pool(
            host=host,
            image=request.image,
            disk_size=request.disk_size,
        )

        status = manager.get_status()

        return ProvisionResponse(
            success=success,
            message="Warm pool provisioned successfully" if success else "Failed to provision warm pool",
            status=WarmPoolStatusResponse(**status) if success else None,
        )

    except Exception as e:
        logger.error(f"Failed to provision warm pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable/{machine_id}", response_model=EnableDisableResponse)
async def enable_warm_pool(machine_id: int):
    """
    Habilita warm pool para uma maquina.

    Se a maquina ja tem warm pool ativo, nao faz nada.
    Se nao tem, busca um host adequado e provisiona.
    """
    try:
        settings_manager = get_failover_settings_manager()
        machine_config = settings_manager.get_machine_config(machine_id)

        machine_config.warm_pool_enabled = True
        machine_config.use_global_settings = False
        settings_manager.update_machine_config(machine_config)

        return EnableDisableResponse(
            status="enabled",
            message=f"Warm pool enabled for machine {machine_id}"
        )

    except Exception as e:
        logger.error(f"Failed to enable warm pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable/{machine_id}", response_model=EnableDisableResponse)
async def disable_warm_pool(machine_id: int):
    """
    Desabilita warm pool para uma maquina.

    O sistema usara CPU Standby como fallback.
    """
    try:
        settings_manager = get_failover_settings_manager()
        machine_config = settings_manager.get_machine_config(machine_id)

        machine_config.warm_pool_enabled = False
        machine_config.use_global_settings = False
        settings_manager.update_machine_config(machine_config)

        return EnableDisableResponse(
            status="disabled",
            message=f"Warm pool disabled for machine {machine_id}",
            fallback="cpu_standby"
        )

    except Exception as e:
        logger.error(f"Failed to disable warm pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/failover/test/{machine_id}", response_model=FailoverTestResponse)
async def test_failover(machine_id: int):
    """
    Testa failover (simula falha da GPU principal).

    CUIDADO: Isso vai iniciar a GPU standby e parar a principal.
    Use apenas para testes.
    """
    try:
        api_key = get_vast_api_key()
        manager = get_warm_pool_manager(machine_id, api_key)

        if manager.status.state != WarmPoolState.ACTIVE:
            return FailoverTestResponse(
                success=False,
                message=f"Cannot test failover in state {manager.status.state.value}"
            )

        import time
        start = time.time()

        success = await manager.trigger_failover()

        recovery_time = time.time() - start

        return FailoverTestResponse(
            success=success,
            message="Failover test completed" if success else "Failover test failed",
            recovery_time_seconds=recovery_time if success else None,
            new_primary_gpu_id=manager.status.primary_gpu_id if success else None,
        )

    except Exception as e:
        logger.error(f"Failed to test failover: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup/{machine_id}")
async def cleanup_warm_pool(machine_id: int):
    """
    Limpa todos os recursos do warm pool.

    Destroi:
    - GPU principal
    - GPU standby
    - Volume
    """
    try:
        api_key = get_vast_api_key()
        manager = get_warm_pool_manager(machine_id, api_key)

        await manager.cleanup()

        return {"success": True, "message": f"Warm pool for machine {machine_id} cleaned up"}

    except Exception as e:
        logger.error(f"Failed to cleanup warm pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))
