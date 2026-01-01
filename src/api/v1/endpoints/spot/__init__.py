"""
Endpoints Spot Reports.

Organização modular - cada relatório em seu próprio arquivo.
"""
from fastapi import APIRouter

from .monitor import router as monitor_router
from .savings import router as savings_router
from .interruption import router as interruption_router
from .safe_windows import router as safe_windows_router
from .llm_gpu import router as llm_gpu_router
from .prediction import router as prediction_router
from .availability import router as availability_router
from .reliability import router as reliability_router
from .training_cost import router as training_cost_router
from .fleet_strategy import router as fleet_strategy_router
from .cost_forecast import router as cost_forecast_router

# Router principal que agrega todos os sub-routers
router = APIRouter(
    prefix="/spot",
    tags=["Spot Reports"],
)

# Incluir todos os sub-routers
router.include_router(monitor_router)
router.include_router(savings_router)
router.include_router(interruption_router)
router.include_router(safe_windows_router)
router.include_router(llm_gpu_router)
router.include_router(prediction_router)
router.include_router(availability_router)
router.include_router(reliability_router)
router.include_router(training_cost_router)
router.include_router(fleet_strategy_router)
router.include_router(cost_forecast_router)

__all__ = ["router"]
