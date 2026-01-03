"""
Serverless GPU API endpoints

Permite configurar GPUs para auto-pause/resume baseado em idle timeout.
Dois modos:
- FAST: Usa CPU Standby (recovery <1s)
- ECONOMIC: Usa VAST.ai pause/resume nativo (recovery ~7s, testado dez/2024)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

from ..dependencies import require_auth, get_current_user_email
from ....modules.serverless import get_serverless_manager, ServerlessMode
from ....infrastructure.providers import FileUserRepository
from ....core.config import get_settings

logger = logging.getLogger(__name__)

# Router com autenticação para operações de instância
router = APIRouter(prefix="/serverless", tags=["Serverless GPU"], dependencies=[Depends(require_auth)])

# Router público para info e pricing (sem auth)
public_router = APIRouter(prefix="/serverless", tags=["Serverless GPU"])


class ServerlessModeEnum(str, Enum):
    """Modos serverless disponíveis via API"""
    fast = "fast"           # CPU Standby - recovery <1s
    economic = "economic"   # VAST.ai pause/resume - recovery ~7s
    spot = "spot"           # Spot instances - 60-70% cheaper, recovery ~30s


class EnableServerlessRequest(BaseModel):
    """Request para habilitar modo serverless"""
    mode: ServerlessModeEnum = Field(
        ServerlessModeEnum.spot,  # Spot é o default agora (mais econômico)
        description="Modo: 'spot' (60-70% mais barato, ~30s recovery), 'economic' (~7s), ou 'fast' (<1s)"
    )
    idle_timeout_seconds: int = Field(
        10,
        ge=2,
        le=3600,
        description="Segundos de idle antes de pausar (2-3600)"
    )
    gpu_threshold: float = Field(
        5.0,
        ge=0,
        le=100,
        description="% GPU utilization abaixo do qual considera idle"
    )
    keep_warm: bool = Field(
        False,
        description="Se True, nunca pausa automaticamente (override)"
    )


class ServerlessStatusResponse(BaseModel):
    """Response com status serverless de uma instância"""
    instance_id: int
    mode: str
    is_paused: bool
    idle_timeout_seconds: int
    current_gpu_util: float
    idle_since: Optional[str]
    will_pause_at: Optional[str]
    total_savings_usd: float
    avg_cold_start_seconds: float


class ServerlessListResponse(BaseModel):
    """Response com lista de instâncias serverless"""
    count: int
    instances: List[Dict[str, Any]]


class CreateServerlessEndpointRequest(BaseModel):
    """Request para criar um endpoint serverless"""
    name: str = Field(..., description="Nome do endpoint")
    machine_type: str = Field("spot", description="Tipo de máquina: 'spot' ou 'on-demand'")
    gpu_name: str = Field("RTX 4090", description="Nome da GPU")
    region: str = Field("US", description="Região: US, EU, ASIA")
    min_instances: int = Field(0, ge=0, le=10, description="Mínimo de instâncias")
    max_instances: int = Field(5, ge=1, le=50, description="Máximo de instâncias")
    target_latency_ms: int = Field(500, ge=50, le=5000, description="Latência alvo em ms")
    timeout_seconds: int = Field(300, ge=30, le=3600, description="Timeout em segundos")
    docker_image: str = Field(..., description="Imagem Docker a usar")
    model_id: str = Field("", description="Model ID do HuggingFace")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Variáveis de ambiente")


class ServerlessEndpointResponse(BaseModel):
    """Response com dados de um endpoint serverless"""
    id: str
    name: str
    status: str
    machine_type: str
    gpu_name: str
    region: str
    created_at: str
    metrics: Dict[str, Any]
    pricing: Dict[str, Any]
    auto_scaling: Dict[str, Any]


class ServerlessStatsResponse(BaseModel):
    """Response com estatísticas serverless"""
    total_endpoints: int
    total_requests_24h: int
    avg_latency_ms: float
    total_cost_24h: float
    active_instances: int
    cold_starts_24h: int


# In-memory storage for serverless endpoints (would be database in production)
_serverless_endpoints: Dict[str, Dict[str, Any]] = {}


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/endpoints")
async def list_serverless_endpoints(
    user_email: str = Depends(get_current_user_email),
):
    """
    Lista todos os endpoints serverless do usuário.
    """
    user_endpoints = [
        ep for ep in _serverless_endpoints.values()
        if ep.get("user_email") == user_email
    ]
    return {"endpoints": user_endpoints}


@router.post("/endpoints")
async def create_serverless_endpoint(
    request: CreateServerlessEndpointRequest,
    user_email: str = Depends(get_current_user_email),
):
    """
    Cria um novo endpoint serverless.

    Deploy de modelo em GPU com auto-scaling e pricing otimizado.
    """
    import uuid
    from datetime import datetime

    # Get user's VAST API key
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured"
        )

    # Generate endpoint ID
    endpoint_id = f"ep-{uuid.uuid4().hex[:8]}"

    # GPU pricing (spot vs on-demand)
    gpu_prices = {
        "RTX 4090": {"spot": 0.18, "on-demand": 0.31},
        "RTX 4080": {"spot": 0.15, "on-demand": 0.25},
        "RTX 3090": {"spot": 0.12, "on-demand": 0.20},
        "RTX 3080": {"spot": 0.09, "on-demand": 0.15},
        "A100 40GB": {"spot": 0.38, "on-demand": 0.64},
        "A100 80GB": {"spot": 0.54, "on-demand": 0.90},
        "H100 PCIe": {"spot": 0.72, "on-demand": 1.20},
        "L40S": {"spot": 0.51, "on-demand": 0.85},
    }

    price_per_hour = gpu_prices.get(request.gpu_name, {"spot": 0.20, "on-demand": 0.30})
    price = price_per_hour["spot"] if request.machine_type == "spot" else price_per_hour["on-demand"]

    # Create endpoint data
    endpoint_data = {
        "id": endpoint_id,
        "name": request.name,
        "status": "provisioning",
        "machine_type": request.machine_type,
        "gpu_name": request.gpu_name,
        "region": request.region,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "user_email": user_email,
        "docker_image": request.docker_image,
        "model_id": request.model_id,
        "env_vars": request.env_vars,
        "metrics": {
            "requests_per_sec": 0,
            "avg_latency_ms": 0,
            "p99_latency_ms": 0,
            "cold_starts_24h": 0,
            "total_requests_24h": 0,
            "uptime_percent": 100,
        },
        "pricing": {
            "price_per_hour": price,
            "price_per_request": 0.00001,
            "cost_24h": 0,
        },
        "auto_scaling": {
            "enabled": True,
            "min_instances": request.min_instances,
            "max_instances": request.max_instances,
            "current_instances": 0,
        },
    }

    # Store endpoint
    _serverless_endpoints[endpoint_id] = endpoint_data

    logger.info(f"Created serverless endpoint {endpoint_id} by {user_email}: {request.name}")

    # TODO: Actually provision GPU on VAST.ai
    # For now, simulate provisioning by marking as running after a short delay
    import asyncio

    async def provision_endpoint():
        await asyncio.sleep(2)  # Simulate provisioning time
        if endpoint_id in _serverless_endpoints:
            _serverless_endpoints[endpoint_id]["status"] = "running"
            _serverless_endpoints[endpoint_id]["auto_scaling"]["current_instances"] = 1

    asyncio.create_task(provision_endpoint())

    return {
        **endpoint_data,
        "message": f"Endpoint '{request.name}' created successfully",
    }


@router.delete("/endpoints/{endpoint_id}")
async def delete_serverless_endpoint(
    endpoint_id: str,
    user_email: str = Depends(get_current_user_email),
):
    """
    Deleta um endpoint serverless.
    """
    if endpoint_id not in _serverless_endpoints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint {endpoint_id} not found"
        )

    endpoint = _serverless_endpoints[endpoint_id]
    if endpoint.get("user_email") != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this endpoint"
        )

    del _serverless_endpoints[endpoint_id]

    logger.info(f"Deleted serverless endpoint {endpoint_id} by {user_email}")

    return {"message": f"Endpoint {endpoint_id} deleted successfully"}


@router.post("/endpoints/{endpoint_id}/pause")
async def pause_serverless_endpoint(
    endpoint_id: str,
    user_email: str = Depends(get_current_user_email),
):
    """
    Pausa um endpoint serverless.
    """
    if endpoint_id not in _serverless_endpoints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint {endpoint_id} not found"
        )

    endpoint = _serverless_endpoints[endpoint_id]
    if endpoint.get("user_email") != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to pause this endpoint"
        )

    _serverless_endpoints[endpoint_id]["status"] = "paused"
    _serverless_endpoints[endpoint_id]["auto_scaling"]["current_instances"] = 0

    logger.info(f"Paused serverless endpoint {endpoint_id} by {user_email}")

    return {"message": f"Endpoint {endpoint_id} paused successfully", "status": "paused"}


@router.post("/endpoints/{endpoint_id}/resume")
async def resume_serverless_endpoint(
    endpoint_id: str,
    user_email: str = Depends(get_current_user_email),
):
    """
    Resume um endpoint serverless pausado.
    """
    if endpoint_id not in _serverless_endpoints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint {endpoint_id} not found"
        )

    endpoint = _serverless_endpoints[endpoint_id]
    if endpoint.get("user_email") != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to resume this endpoint"
        )

    _serverless_endpoints[endpoint_id]["status"] = "running"
    _serverless_endpoints[endpoint_id]["auto_scaling"]["current_instances"] = 1

    logger.info(f"Resumed serverless endpoint {endpoint_id} by {user_email}")

    return {"message": f"Endpoint {endpoint_id} resumed successfully", "status": "running"}


class UpdateServerlessEndpointRequest(BaseModel):
    """Request para atualizar configuração de endpoint serverless"""
    min_instances: Optional[int] = Field(None, ge=0, le=10, description="Mínimo de instâncias")
    max_instances: Optional[int] = Field(None, ge=1, le=50, description="Máximo de instâncias")
    machine_type: Optional[str] = Field(None, description="Tipo de máquina: 'spot' ou 'on-demand'")


@router.put("/endpoints/{endpoint_id}")
async def update_serverless_endpoint(
    endpoint_id: str,
    request: UpdateServerlessEndpointRequest,
    user_email: str = Depends(get_current_user_email),
):
    """
    Atualiza configuração de um endpoint serverless.
    """
    if endpoint_id not in _serverless_endpoints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint {endpoint_id} not found"
        )

    endpoint = _serverless_endpoints[endpoint_id]
    if endpoint.get("user_email") != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this endpoint"
        )

    # Update auto_scaling settings
    if request.min_instances is not None:
        _serverless_endpoints[endpoint_id]["auto_scaling"]["min_instances"] = request.min_instances
    if request.max_instances is not None:
        _serverless_endpoints[endpoint_id]["auto_scaling"]["max_instances"] = request.max_instances

    # Update machine type and recalculate pricing
    if request.machine_type is not None:
        _serverless_endpoints[endpoint_id]["machine_type"] = request.machine_type
        gpu_name = endpoint.get("gpu_name", "RTX 4090")
        gpu_prices = {
            "RTX 4090": {"spot": 0.18, "on-demand": 0.31},
            "RTX 4080": {"spot": 0.15, "on-demand": 0.25},
            "RTX 3090": {"spot": 0.12, "on-demand": 0.20},
            "RTX 3080": {"spot": 0.09, "on-demand": 0.15},
            "A100 40GB": {"spot": 0.38, "on-demand": 0.64},
            "A100 80GB": {"spot": 0.54, "on-demand": 0.90},
            "H100 PCIe": {"spot": 0.72, "on-demand": 1.20},
            "L40S": {"spot": 0.51, "on-demand": 0.85},
        }
        price_per_hour = gpu_prices.get(gpu_name, {"spot": 0.20, "on-demand": 0.30})
        price = price_per_hour["spot"] if request.machine_type == "spot" else price_per_hour["on-demand"]
        _serverless_endpoints[endpoint_id]["pricing"]["price_per_hour"] = price

    logger.info(f"Updated serverless endpoint {endpoint_id} by {user_email}")

    return {
        **_serverless_endpoints[endpoint_id],
        "message": f"Endpoint {endpoint_id} updated successfully"
    }


@router.get("/stats", response_model=ServerlessStatsResponse)
async def get_serverless_stats(
    user_email: str = Depends(get_current_user_email),
):
    """
    Retorna estatísticas dos endpoints serverless do usuário.
    """
    user_endpoints = [
        ep for ep in _serverless_endpoints.values()
        if ep.get("user_email") == user_email
    ]

    total_endpoints = len(user_endpoints)
    total_requests = sum(ep.get("metrics", {}).get("total_requests_24h", 0) for ep in user_endpoints)

    latencies = [ep.get("metrics", {}).get("avg_latency_ms", 0) for ep in user_endpoints if ep.get("metrics", {}).get("avg_latency_ms", 0) > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    total_cost = sum(ep.get("pricing", {}).get("cost_24h", 0) for ep in user_endpoints)
    active_instances = sum(ep.get("auto_scaling", {}).get("current_instances", 0) for ep in user_endpoints)
    cold_starts = sum(ep.get("metrics", {}).get("cold_starts_24h", 0) for ep in user_endpoints)

    return ServerlessStatsResponse(
        total_endpoints=total_endpoints,
        total_requests_24h=total_requests,
        avg_latency_ms=avg_latency,
        total_cost_24h=total_cost,
        active_instances=active_instances,
        cold_starts_24h=cold_starts,
    )


@router.post("/enable/{instance_id}")
async def enable_serverless(
    instance_id: int,
    request: EnableServerlessRequest = EnableServerlessRequest(),
    user_email: str = Depends(get_current_user_email),
):
    """
    Habilita modo serverless para uma instância GPU.

    Quando habilitado, a GPU será automaticamente pausada após ficar
    idle (GPU utilization < threshold) pelo tempo configurado.

    **Modos disponíveis:**

    - **fast**: Usa CPU Standby com sincronização contínua.
      Recovery ultra-rápido (<1s). Custo idle: ~$0.01/hr.
      Requer CPU Standby configurado previamente.

    - **economic**: Usa pause/resume nativo do VAST.ai.
      Recovery rápido (~7s). Custo idle: ~$0.005/hr.
      Não requer configuração adicional.

    **Idle detection:**
    A GPU é considerada idle quando utilization < gpu_threshold.
    O DumontAgent envia heartbeats com GPU utilization a cada 30s.

    **Exemplo de uso:**
    ```
    # Pausar após 10s idle, modo econômico
    dumont serverless enable 12345 --mode economic --timeout 10

    # Pausar após 60s idle, modo rápido
    dumont serverless enable 12345 --mode fast --timeout 60
    ```
    """
    # Get user's VAST API key
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured"
        )

    # Configure manager with VAST provider
    manager = get_serverless_manager()
    manager.configure(vast_api_key=user.vast_api_key)

    # Enable serverless
    result = manager.enable(
        instance_id=instance_id,
        mode=request.mode.value,
        idle_timeout_seconds=request.idle_timeout_seconds,
        gpu_threshold=request.gpu_threshold,
        keep_warm=request.keep_warm,
    )

    logger.info(f"Serverless enabled for {instance_id} by {user_email}: mode={request.mode.value}")

    return {
        **result,
        "message": f"Serverless mode '{request.mode.value}' enabled for instance {instance_id}",
        "behavior": {
            "will_pause_after": f"{request.idle_timeout_seconds}s of idle",
            "idle_threshold": f"GPU < {request.gpu_threshold}%",
            "recovery_time": "<1s" if request.mode == ServerlessModeEnum.fast else "~30s",
        }
    }


@router.post("/disable/{instance_id}")
async def disable_serverless(
    instance_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Desabilita modo serverless para uma instância.

    Se a instância estiver pausada, ela será resumida automaticamente.
    """
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured"
        )

    manager = get_serverless_manager()
    manager.configure(vast_api_key=user.vast_api_key)

    result = manager.disable(instance_id)

    if result.get("status") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not configured for serverless"
        )

    logger.info(f"Serverless disabled for {instance_id} by {user_email}")

    return {
        **result,
        "message": f"Serverless disabled for instance {instance_id}"
    }


@router.get("/status/{instance_id}", response_model=ServerlessStatusResponse)
async def get_serverless_status(
    instance_id: int,
):
    """
    Obtém status serverless de uma instância específica.

    Retorna:
    - Modo atual (fast/economic/disabled)
    - Se está pausada
    - GPU utilization atual
    - Quando vai pausar (se aplicável)
    - Economia acumulada
    """
    manager = get_serverless_manager()
    instance_status = manager.get_status(instance_id)

    if not instance_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not configured for serverless"
        )

    return ServerlessStatusResponse(
        instance_id=instance_status.instance_id,
        mode=instance_status.mode,
        is_paused=instance_status.is_paused,
        idle_timeout_seconds=instance_status.idle_timeout_seconds,
        current_gpu_util=instance_status.current_gpu_util,
        idle_since=instance_status.idle_since,
        will_pause_at=instance_status.will_pause_at,
        total_savings_usd=instance_status.total_savings_usd,
        avg_cold_start_seconds=instance_status.avg_cold_start_seconds,
    )


@router.get("/list", response_model=ServerlessListResponse)
async def list_serverless_instances():
    """
    Lista todas as instâncias com serverless configurado.

    Retorna status resumido de cada instância.
    """
    manager = get_serverless_manager()
    instances = manager.list_all()

    return ServerlessListResponse(
        count=len(instances),
        instances=instances,
    )


@router.post("/wake/{instance_id}")
async def wake_instance(
    instance_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Acorda uma instância pausada (on-demand).

    Use este endpoint para acordar uma GPU antes de enviar inferências.
    Retorna o tempo de cold start.

    **Exemplo de uso em código:**
    ```python
    # Antes de enviar inferência
    response = requests.post(f"/api/v1/serverless/wake/{instance_id}")
    cold_start = response.json()["cold_start_seconds"]

    # Agora pode enviar inferência
    result = send_inference(instance_id, prompt)
    ```
    """
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured"
        )

    manager = get_serverless_manager()
    manager.configure(vast_api_key=user.vast_api_key)

    result = manager.wake(instance_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )

    logger.info(f"Instance {instance_id} woken by {user_email}: {result.get('cold_start_seconds', 0)}s")

    return result


@router.post("/inference-start/{instance_id}")
async def notify_inference_start(instance_id: int):
    """
    Notifica que uma inferência começou.

    Reseta o idle timer para evitar que a GPU seja pausada
    durante processamento ativo.

    Chamado automaticamente pelo DumontAgent.
    """
    manager = get_serverless_manager()
    manager.on_inference_start(instance_id)

    return {"status": "ok", "idle_timer": "reset"}


@router.post("/inference-complete/{instance_id}")
async def notify_inference_complete(instance_id: int):
    """
    Notifica que uma inferência terminou.

    Inicia o idle timer. Se GPU ficar idle por mais que
    idle_timeout_seconds, será pausada automaticamente.

    Chamado automaticamente pelo DumontAgent.
    """
    manager = get_serverless_manager()
    manager.on_inference_complete(instance_id)

    return {"status": "ok", "idle_timer": "started"}


@public_router.get("/status")
async def get_serverless_global_status():
    """
    Retorna status geral do sistema serverless (público, sem auth).

    Inclui:
    - Total de instâncias configuradas
    - Instâncias ativas vs pausadas
    - Economia total estimada
    - Modos disponíveis
    """
    manager = get_serverless_manager()
    instances = manager.list_all()

    total = len(instances)
    paused = sum(1 for i in instances if i.get("is_paused", False))
    active = total - paused
    total_savings = sum(i.get("total_savings_usd", 0) for i in instances)

    return {
        "status": "operational",
        "total_instances": total,
        "active_instances": active,
        "paused_instances": paused,
        "total_savings_usd": round(total_savings, 2),
        "available_modes": [
            {"mode": "spot", "recovery_time": "~30s", "savings": "60-70%"},
            {"mode": "economic", "recovery_time": "~7s", "savings": "~83%"},
            {"mode": "fast", "recovery_time": "<1s", "savings": "~80%"},
        ],
        "features": [
            "auto-pause on idle",
            "auto-resume on request",
            "checkpoint sync",
            "gpu utilization monitoring",
        ]
    }


@public_router.get("/pricing")
async def get_serverless_pricing():
    """
    Retorna estimativas de custo para cada modo serverless.

    Compara custo de:
    - GPU ligada 24/7
    - Modo fast (CPU standby)
    - Modo economic (pause/resume)

    Baseado em uso estimado de 4h/dia de GPU ativa.
    """
    # Estimativas baseadas em GPU média $0.30/hr
    gpu_hourly = 0.30
    hours_per_day_active = 4
    hours_per_day_idle = 20
    days_per_month = 30

    # Custo 24/7
    cost_24_7 = gpu_hourly * 24 * days_per_month

    # Modo fast: GPU ativa + CPU standby durante idle
    cpu_standby_hourly = 0.01  # e2-medium spot
    cost_fast = (gpu_hourly * hours_per_day_active + cpu_standby_hourly * hours_per_day_idle) * days_per_month

    # Modo economic: GPU ativa + storage durante idle (praticamente zero)
    storage_hourly = 0.005  # Custo de storage para estado pausado
    cost_economic = (gpu_hourly * hours_per_day_active + storage_hourly * hours_per_day_idle) * days_per_month

    return {
        "assumptions": {
            "gpu_hourly_rate_usd": gpu_hourly,
            "active_hours_per_day": hours_per_day_active,
            "idle_hours_per_day": hours_per_day_idle,
            "days_per_month": days_per_month,
        },
        "monthly_costs": {
            "always_on": {
                "cost_usd": round(cost_24_7, 2),
                "description": "GPU ligada 24/7",
            },
            "serverless_fast": {
                "cost_usd": round(cost_fast, 2),
                "savings_usd": round(cost_24_7 - cost_fast, 2),
                "savings_percent": round((1 - cost_fast/cost_24_7) * 100, 1),
                "description": "Modo fast com CPU standby",
                "recovery_time": "<1 segundo",
            },
            "serverless_economic": {
                "cost_usd": round(cost_economic, 2),
                "savings_usd": round(cost_24_7 - cost_economic, 2),
                "savings_percent": round((1 - cost_economic/cost_24_7) * 100, 1),
                "description": "Modo economic com pause/resume",
                "recovery_time": "~7 segundos",
            },
        },
        "recommendation": "economic" if hours_per_day_active <= 4 else "fast",
        "note": "Preços são estimativas. Custo real depende do tipo de GPU e provedor.",
    }
