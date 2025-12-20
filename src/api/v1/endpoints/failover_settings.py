"""
Failover Settings API Endpoints.

Endpoints para gerenciar configuracoes de failover:
- Configuracoes globais (padrao para novas maquinas)
- Configuracoes por maquina
- Habilitar/desabilitar estrategias
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.config.failover_settings import (
    FailoverSettings, FailoverStrategy,
    WarmPoolConfig, CPUStandbyConfig,
    MachineFailoverConfig,
    get_failover_settings_manager
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/failover/settings", tags=["failover-settings"])


# ============ Schemas ============

class WarmPoolConfigSchema(BaseModel):
    """Configuracao do GPU Warm Pool"""
    enabled: bool = True
    min_gpus_per_host: int = 2
    volume_size_gb: int = 100
    auto_provision_standby: bool = True
    fallback_to_cpu_standby: bool = True
    preferred_gpu_names: List[str] = ["RTX_4090", "RTX_3090", "A100"]
    health_check_interval_seconds: int = 10
    failover_timeout_seconds: int = 120
    auto_reprovision_standby: bool = True


class CPUStandbyConfigSchema(BaseModel):
    """Configuracao do CPU Standby"""
    enabled: bool = True
    gcp_zone: str = "europe-west1-b"
    gcp_machine_type: str = "e2-medium"
    gcp_disk_size_gb: int = 100
    gcp_spot: bool = True
    sync_interval_seconds: int = 30
    health_check_interval_seconds: int = 10
    failover_threshold: int = 3
    auto_failover: bool = True
    auto_recovery: bool = True
    snapshot_to_cloud: bool = True


class GlobalSettingsRequest(BaseModel):
    """Request para atualizar configuracoes globais"""
    default_strategy: str = Field(
        "both",
        description="Estrategia padrao: warm_pool, cpu_standby, both, disabled"
    )
    warm_pool: Optional[WarmPoolConfigSchema] = None
    cpu_standby: Optional[CPUStandbyConfigSchema] = None
    auto_apply_to_new_machines: bool = True
    notify_on_failover: bool = True
    notify_channels: List[str] = ["email", "slack"]


class GlobalSettingsResponse(BaseModel):
    """Resposta das configuracoes globais"""
    default_strategy: str
    warm_pool: WarmPoolConfigSchema
    cpu_standby: CPUStandbyConfigSchema
    auto_apply_to_new_machines: bool
    notify_on_failover: bool
    notify_channels: List[str]
    summary: Dict[str, Any]


class MachineConfigRequest(BaseModel):
    """Request para atualizar configuracao de maquina"""
    use_global_settings: bool = Field(
        True,
        description="Se True, usa configuracao global. Se False, usa config personalizada."
    )
    strategy: Optional[str] = Field(
        None,
        description="Estrategia: warm_pool, cpu_standby, both, disabled (se use_global=False)"
    )
    warm_pool_enabled: bool = True
    cpu_standby_enabled: bool = True


class MachineConfigResponse(BaseModel):
    """Resposta da configuracao de maquina"""
    machine_id: int
    use_global_settings: bool
    effective_strategy: str
    warm_pool: Dict[str, Any]
    cpu_standby: Dict[str, Any]
    stats: Dict[str, Any]


class AllMachinesConfigResponse(BaseModel):
    """Lista de configuracoes de todas as maquinas"""
    machines: Dict[str, MachineConfigResponse]
    count: int


# ============ Endpoints Globais ============

@router.get("/global", response_model=GlobalSettingsResponse)
async def get_global_settings():
    """
    Retorna configuracoes globais de failover.

    Estas sao as configuracoes padrao aplicadas a novas maquinas.
    """
    try:
        manager = get_failover_settings_manager()
        settings = manager.get_global_settings()

        return GlobalSettingsResponse(
            default_strategy=settings.default_strategy.value,
            warm_pool=WarmPoolConfigSchema(
                enabled=settings.warm_pool.enabled,
                min_gpus_per_host=settings.warm_pool.min_gpus_per_host,
                volume_size_gb=settings.warm_pool.volume_size_gb,
                auto_provision_standby=settings.warm_pool.auto_provision_standby,
                fallback_to_cpu_standby=settings.warm_pool.fallback_to_cpu_standby,
                preferred_gpu_names=settings.warm_pool.preferred_gpu_names,
                health_check_interval_seconds=settings.warm_pool.health_check_interval_seconds,
                failover_timeout_seconds=settings.warm_pool.failover_timeout_seconds,
                auto_reprovision_standby=settings.warm_pool.auto_reprovision_standby,
            ),
            cpu_standby=CPUStandbyConfigSchema(
                enabled=settings.cpu_standby.enabled,
                gcp_zone=settings.cpu_standby.gcp_zone,
                gcp_machine_type=settings.cpu_standby.gcp_machine_type,
                gcp_disk_size_gb=settings.cpu_standby.gcp_disk_size_gb,
                gcp_spot=settings.cpu_standby.gcp_spot,
                sync_interval_seconds=settings.cpu_standby.sync_interval_seconds,
                health_check_interval_seconds=settings.cpu_standby.health_check_interval_seconds,
                failover_threshold=settings.cpu_standby.failover_threshold,
                auto_failover=settings.cpu_standby.auto_failover,
                auto_recovery=settings.cpu_standby.auto_recovery,
                snapshot_to_cloud=settings.cpu_standby.snapshot_to_cloud,
            ),
            auto_apply_to_new_machines=settings.auto_apply_to_new_machines,
            notify_on_failover=settings.notify_on_failover,
            notify_channels=settings.notify_channels,
            summary={
                "warm_pool_enabled": settings.is_warm_pool_enabled(),
                "cpu_standby_enabled": settings.is_cpu_standby_enabled(),
                "description": _get_strategy_description(settings.default_strategy),
            }
        )

    except Exception as e:
        logger.error(f"Failed to get global settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/global", response_model=GlobalSettingsResponse)
async def update_global_settings(request: GlobalSettingsRequest):
    """
    Atualiza configuracoes globais de failover.

    Novas maquinas usarao estas configuracoes por padrao.
    """
    try:
        manager = get_failover_settings_manager()

        # Converter request para FailoverSettings
        warm_pool_config = WarmPoolConfig(
            enabled=request.warm_pool.enabled if request.warm_pool else True,
            min_gpus_per_host=request.warm_pool.min_gpus_per_host if request.warm_pool else 2,
            volume_size_gb=request.warm_pool.volume_size_gb if request.warm_pool else 100,
            auto_provision_standby=request.warm_pool.auto_provision_standby if request.warm_pool else True,
            fallback_to_cpu_standby=request.warm_pool.fallback_to_cpu_standby if request.warm_pool else True,
            preferred_gpu_names=request.warm_pool.preferred_gpu_names if request.warm_pool else ["RTX_4090", "RTX_3090", "A100"],
            health_check_interval_seconds=request.warm_pool.health_check_interval_seconds if request.warm_pool else 10,
            failover_timeout_seconds=request.warm_pool.failover_timeout_seconds if request.warm_pool else 120,
            auto_reprovision_standby=request.warm_pool.auto_reprovision_standby if request.warm_pool else True,
        )

        cpu_standby_config = CPUStandbyConfig(
            enabled=request.cpu_standby.enabled if request.cpu_standby else True,
            gcp_zone=request.cpu_standby.gcp_zone if request.cpu_standby else "europe-west1-b",
            gcp_machine_type=request.cpu_standby.gcp_machine_type if request.cpu_standby else "e2-medium",
            gcp_disk_size_gb=request.cpu_standby.gcp_disk_size_gb if request.cpu_standby else 100,
            gcp_spot=request.cpu_standby.gcp_spot if request.cpu_standby else True,
            sync_interval_seconds=request.cpu_standby.sync_interval_seconds if request.cpu_standby else 30,
            health_check_interval_seconds=request.cpu_standby.health_check_interval_seconds if request.cpu_standby else 10,
            failover_threshold=request.cpu_standby.failover_threshold if request.cpu_standby else 3,
            auto_failover=request.cpu_standby.auto_failover if request.cpu_standby else True,
            auto_recovery=request.cpu_standby.auto_recovery if request.cpu_standby else True,
            snapshot_to_cloud=request.cpu_standby.snapshot_to_cloud if request.cpu_standby else True,
        )

        settings = FailoverSettings(
            default_strategy=FailoverStrategy(request.default_strategy),
            warm_pool=warm_pool_config,
            cpu_standby=cpu_standby_config,
            auto_apply_to_new_machines=request.auto_apply_to_new_machines,
            notify_on_failover=request.notify_on_failover,
            notify_channels=request.notify_channels,
        )

        manager.update_global_settings(settings)

        # Retornar configuracoes atualizadas
        return await get_global_settings()

    except Exception as e:
        logger.error(f"Failed to update global settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Endpoints por Maquina ============

@router.get("/machines", response_model=AllMachinesConfigResponse)
async def list_machine_configs():
    """
    Lista configuracoes de failover de todas as maquinas.
    """
    try:
        manager = get_failover_settings_manager()
        configs = manager.list_machine_configs()

        machines = {}
        for machine_id, config in configs.items():
            effective = manager.get_effective_config(machine_id)
            machines[str(machine_id)] = MachineConfigResponse(
                machine_id=machine_id,
                use_global_settings=config.use_global_settings,
                effective_strategy=effective['effective_strategy'],
                warm_pool=effective['warm_pool'],
                cpu_standby=effective['cpu_standby'],
                stats=effective['stats'],
            )

        return AllMachinesConfigResponse(machines=machines, count=len(machines))

    except Exception as e:
        logger.error(f"Failed to list machine configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/machines/{machine_id}", response_model=MachineConfigResponse)
async def get_machine_config(machine_id: int):
    """
    Retorna configuracao de failover de uma maquina especifica.
    """
    try:
        manager = get_failover_settings_manager()
        effective = manager.get_effective_config(machine_id)
        config = manager.get_machine_config(machine_id)

        return MachineConfigResponse(
            machine_id=machine_id,
            use_global_settings=config.use_global_settings,
            effective_strategy=effective['effective_strategy'],
            warm_pool=effective['warm_pool'],
            cpu_standby=effective['cpu_standby'],
            stats=effective['stats'],
        )

    except Exception as e:
        logger.error(f"Failed to get machine config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/machines/{machine_id}", response_model=MachineConfigResponse)
async def update_machine_config(machine_id: int, request: MachineConfigRequest):
    """
    Atualiza configuracao de failover de uma maquina.

    Se `use_global_settings=True`, a maquina usara as configuracoes globais.
    Se `use_global_settings=False`, usara as configuracoes personalizadas.
    """
    try:
        manager = get_failover_settings_manager()
        config = manager.get_machine_config(machine_id)

        config.use_global_settings = request.use_global_settings

        if not request.use_global_settings:
            config.strategy = FailoverStrategy(request.strategy) if request.strategy else FailoverStrategy.BOTH
            config.warm_pool_enabled = request.warm_pool_enabled
            config.cpu_standby_enabled = request.cpu_standby_enabled

        manager.update_machine_config(config)

        return await get_machine_config(machine_id)

    except Exception as e:
        logger.error(f"Failed to update machine config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/machines/{machine_id}")
async def delete_machine_config(machine_id: int):
    """
    Remove configuracao personalizada de uma maquina.

    A maquina voltara a usar as configuracoes globais.
    """
    try:
        manager = get_failover_settings_manager()
        manager.delete_machine_config(machine_id)

        return {"success": True, "message": f"Machine {machine_id} config deleted, using global settings"}

    except Exception as e:
        logger.error(f"Failed to delete machine config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Endpoints de Conveniencia ============

@router.post("/machines/{machine_id}/use-global")
async def use_global_settings(machine_id: int):
    """
    Configura maquina para usar configuracoes globais.
    """
    request = MachineConfigRequest(use_global_settings=True)
    return await update_machine_config(machine_id, request)


@router.post("/machines/{machine_id}/enable-warm-pool")
async def enable_warm_pool_only(machine_id: int):
    """
    Habilita apenas GPU Warm Pool para uma maquina.
    """
    request = MachineConfigRequest(
        use_global_settings=False,
        strategy="warm_pool",
        warm_pool_enabled=True,
        cpu_standby_enabled=False,
    )
    return await update_machine_config(machine_id, request)


@router.post("/machines/{machine_id}/enable-cpu-standby")
async def enable_cpu_standby_only(machine_id: int):
    """
    Habilita apenas CPU Standby para uma maquina.
    """
    request = MachineConfigRequest(
        use_global_settings=False,
        strategy="cpu_standby",
        warm_pool_enabled=False,
        cpu_standby_enabled=True,
    )
    return await update_machine_config(machine_id, request)


@router.post("/machines/{machine_id}/enable-both")
async def enable_both_strategies(machine_id: int):
    """
    Habilita ambas estrategias (Warm Pool + CPU Standby) para uma maquina.
    """
    request = MachineConfigRequest(
        use_global_settings=False,
        strategy="both",
        warm_pool_enabled=True,
        cpu_standby_enabled=True,
    )
    return await update_machine_config(machine_id, request)


@router.post("/machines/{machine_id}/disable-failover")
async def disable_failover(machine_id: int):
    """
    Desabilita failover para uma maquina.
    """
    request = MachineConfigRequest(
        use_global_settings=False,
        strategy="disabled",
        warm_pool_enabled=False,
        cpu_standby_enabled=False,
    )
    return await update_machine_config(machine_id, request)


# ============ Helpers ============

def _get_strategy_description(strategy: FailoverStrategy) -> str:
    """Retorna descricao da estrategia"""
    descriptions = {
        FailoverStrategy.WARM_POOL: "GPU Warm Pool (failover em 30-60s)",
        FailoverStrategy.CPU_STANDBY: "CPU Standby (failover em 10-20min)",
        FailoverStrategy.BOTH: "GPU Warm Pool (principal) + CPU Standby (fallback)",
        FailoverStrategy.DISABLED: "Failover desabilitado",
    }
    return descriptions.get(strategy, "Unknown")
