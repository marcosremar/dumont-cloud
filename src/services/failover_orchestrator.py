"""
Failover Orchestrator - Unified failover management

Orchestrates failover using configured strategies:
1. GPU Warm Pool (primary, ~30-60s) - uses standby GPU on same host
2. CPU Standby + Snapshot (fallback, ~10-20min) - uses GCP CPU instance

Configuration is managed by FailoverSettingsManager:
- Global defaults that apply to new machines
- Per-machine overrides for specific configurations
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from src.config.failover_settings import (
    FailoverStrategy,
    get_failover_settings_manager,
)
from src.services.warmpool import WarmPoolManager, WarmPoolState, get_warm_pool_manager
from src.services.standby import StandbyManager, FailoverService, FailoverResult

logger = logging.getLogger(__name__)


class FailoverPhase(str, Enum):
    """Current phase of failover"""
    IDLE = "idle"
    WARM_POOL_CHECK = "warm_pool_check"
    WARM_POOL_FAILOVER = "warm_pool_failover"
    CPU_STANDBY_CHECK = "cpu_standby_check"
    CPU_STANDBY_FAILOVER = "cpu_standby_failover"
    SNAPSHOT_RESTORE = "snapshot_restore"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OrchestratedFailoverResult:
    """Result of an orchestrated failover"""
    success: bool
    failover_id: str
    machine_id: int

    # Strategy used
    strategy_attempted: str  # "warm_pool", "cpu_standby", "both"
    strategy_succeeded: Optional[str] = None  # Which one actually worked

    # Original GPU info
    original_gpu_id: Optional[int] = None
    original_ssh_host: Optional[str] = None
    original_ssh_port: Optional[int] = None

    # New instance info
    new_gpu_id: Optional[int] = None
    new_ssh_host: Optional[str] = None
    new_ssh_port: Optional[int] = None
    new_gpu_name: Optional[str] = None

    # Timing (milliseconds)
    warm_pool_attempt_ms: int = 0
    cpu_standby_attempt_ms: int = 0
    total_ms: int = 0

    # Error info
    error: Optional[str] = None
    warm_pool_error: Optional[str] = None
    cpu_standby_error: Optional[str] = None

    # Details
    phase_history: list = field(default_factory=list)


class FailoverOrchestrator:
    """
    Unified failover orchestrator that manages both Warm Pool and CPU Standby strategies.

    Usage:
        orchestrator = FailoverOrchestrator(vast_api_key="...")

        result = await orchestrator.execute_failover(
            machine_id=123,
            gpu_instance_id=456,
            ssh_host="ssh.vast.ai",
            ssh_port=12345
        )

        if result.success:
            print(f"Failover succeeded via {result.strategy_succeeded}")
            print(f"New instance: {result.new_ssh_host}:{result.new_ssh_port}")
    """

    def __init__(
        self,
        vast_api_key: str,
        gcp_credentials: Optional[dict] = None,
        b2_endpoint: str = "https://s3.us-west-004.backblazeb2.com",
        b2_bucket: str = "dumoncloud-snapshot",
    ):
        self.vast_api_key = vast_api_key
        self.gcp_credentials = gcp_credentials
        self.b2_endpoint = b2_endpoint
        self.b2_bucket = b2_bucket
        self.settings_manager = get_failover_settings_manager()

    async def execute_failover(
        self,
        machine_id: int,
        gpu_instance_id: int,
        ssh_host: str,
        ssh_port: int,
        failover_id: Optional[str] = None,
        workspace_path: str = "/workspace",
        force_strategy: Optional[str] = None,
    ) -> OrchestratedFailoverResult:
        """
        Execute failover using configured strategies.

        Order of operations:
        1. Check machine/global settings for enabled strategies
        2. Try Warm Pool if enabled and available
        3. Fall back to CPU Standby if Warm Pool fails or is disabled

        Args:
            machine_id: Internal machine ID (for settings lookup)
            gpu_instance_id: Current GPU instance ID (Vast.ai)
            ssh_host: Current GPU SSH host
            ssh_port: Current GPU SSH port
            failover_id: Unique failover ID (auto-generated if not provided)
            workspace_path: Path to backup/restore
            force_strategy: Override settings and use specific strategy

        Returns:
            OrchestratedFailoverResult with details
        """
        import uuid
        start_time = time.time()

        if not failover_id:
            failover_id = f"fo-{uuid.uuid4().hex[:8]}"

        logger.info(f"[{failover_id}] Starting orchestrated failover for machine {machine_id}")

        # Get effective configuration
        effective_config = self.settings_manager.get_effective_config(machine_id)

        if force_strategy:
            strategy = force_strategy
        else:
            strategy = effective_config['effective_strategy']

        logger.info(f"[{failover_id}] Using strategy: {strategy}")

        result = OrchestratedFailoverResult(
            success=False,
            failover_id=failover_id,
            machine_id=machine_id,
            strategy_attempted=strategy,
            original_gpu_id=gpu_instance_id,
            original_ssh_host=ssh_host,
            original_ssh_port=ssh_port,
        )

        # Check if failover is disabled
        if strategy == "disabled":
            result.error = "Failover is disabled for this machine"
            result.total_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"[{failover_id}] Failover disabled for machine {machine_id}")
            return result

        # Track phases
        result.phase_history.append(("start", time.time()))

        # Try strategies based on configuration
        warm_pool_enabled = strategy in ["warm_pool", "both"]
        cpu_standby_enabled = strategy in ["cpu_standby", "both"]

        # ============================================================
        # PHASE 1: Try Warm Pool
        # ============================================================
        if warm_pool_enabled:
            result.phase_history.append((FailoverPhase.WARM_POOL_CHECK.value, time.time()))
            logger.info(f"[{failover_id}] Attempting Warm Pool failover...")

            warm_pool_start = time.time()
            warm_pool_result = await self._try_warm_pool_failover(
                machine_id=machine_id,
                failover_id=failover_id,
            )
            result.warm_pool_attempt_ms = int((time.time() - warm_pool_start) * 1000)

            if warm_pool_result['success']:
                logger.info(f"[{failover_id}] Warm Pool failover succeeded in {result.warm_pool_attempt_ms}ms")
                result.success = True
                result.strategy_succeeded = "warm_pool"
                result.new_gpu_id = warm_pool_result.get('new_gpu_id')
                result.new_ssh_host = warm_pool_result.get('new_ssh_host')
                result.new_ssh_port = warm_pool_result.get('new_ssh_port')
                result.new_gpu_name = warm_pool_result.get('new_gpu_name')
                result.phase_history.append((FailoverPhase.COMPLETED.value, time.time()))
                result.total_ms = int((time.time() - start_time) * 1000)
                return result
            else:
                result.warm_pool_error = warm_pool_result.get('error', 'Unknown error')
                logger.warning(f"[{failover_id}] Warm Pool failed: {result.warm_pool_error}")

        # ============================================================
        # PHASE 2: Try CPU Standby (if Warm Pool failed or disabled)
        # ============================================================
        if cpu_standby_enabled:
            result.phase_history.append((FailoverPhase.CPU_STANDBY_CHECK.value, time.time()))
            logger.info(f"[{failover_id}] Attempting CPU Standby failover...")

            cpu_standby_start = time.time()
            cpu_result = await self._try_cpu_standby_failover(
                machine_id=machine_id,
                gpu_instance_id=gpu_instance_id,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                failover_id=failover_id,
                workspace_path=workspace_path,
            )
            result.cpu_standby_attempt_ms = int((time.time() - cpu_standby_start) * 1000)

            if cpu_result['success']:
                logger.info(f"[{failover_id}] CPU Standby failover succeeded in {result.cpu_standby_attempt_ms}ms")
                result.success = True
                result.strategy_succeeded = "cpu_standby"
                result.new_gpu_id = cpu_result.get('new_gpu_id')
                result.new_ssh_host = cpu_result.get('new_ssh_host')
                result.new_ssh_port = cpu_result.get('new_ssh_port')
                result.phase_history.append((FailoverPhase.COMPLETED.value, time.time()))
                result.total_ms = int((time.time() - start_time) * 1000)
                return result
            else:
                result.cpu_standby_error = cpu_result.get('error', 'Unknown error')
                logger.warning(f"[{failover_id}] CPU Standby failed: {result.cpu_standby_error}")

        # ============================================================
        # FAILURE: No strategy succeeded
        # ============================================================
        result.phase_history.append((FailoverPhase.FAILED.value, time.time()))
        result.total_ms = int((time.time() - start_time) * 1000)

        if result.warm_pool_error and result.cpu_standby_error:
            result.error = f"All strategies failed. Warm Pool: {result.warm_pool_error}. CPU Standby: {result.cpu_standby_error}"
        elif result.warm_pool_error:
            result.error = f"Warm Pool failed: {result.warm_pool_error}"
        elif result.cpu_standby_error:
            result.error = f"CPU Standby failed: {result.cpu_standby_error}"
        else:
            result.error = "No failover strategy was attempted"

        logger.error(f"[{failover_id}] Failover failed: {result.error}")
        return result

    async def _try_warm_pool_failover(
        self,
        machine_id: int,
        failover_id: str,
    ) -> Dict[str, Any]:
        """
        Attempt failover using GPU Warm Pool.

        Returns:
            Dict with success status and new instance info
        """
        try:
            manager = get_warm_pool_manager(machine_id, self.vast_api_key)

            # Check if warm pool is active
            if manager.status.state != WarmPoolState.ACTIVE:
                return {
                    'success': False,
                    'error': f"Warm pool not active (state={manager.status.state.value})"
                }

            # Check if we have a standby ready
            if not manager.status.standby_gpu_id:
                return {
                    'success': False,
                    'error': "No standby GPU available in warm pool"
                }

            # Trigger failover
            logger.info(f"[{failover_id}] Triggering warm pool failover...")
            success = await manager.trigger_failover()

            if success:
                return {
                    'success': True,
                    'new_gpu_id': manager.status.primary_gpu_id,
                    'new_ssh_host': manager.status.primary_ssh_host,
                    'new_ssh_port': manager.status.primary_ssh_port,
                    'new_gpu_name': 'GPU',  # TODO: get actual GPU name
                }
            else:
                return {
                    'success': False,
                    'error': manager.status.error_message or "Failover trigger failed"
                }

        except Exception as e:
            logger.error(f"[{failover_id}] Warm pool error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _try_cpu_standby_failover(
        self,
        machine_id: int,
        gpu_instance_id: int,
        ssh_host: str,
        ssh_port: int,
        failover_id: str,
        workspace_path: str,
    ) -> Dict[str, Any]:
        """
        Attempt failover using CPU Standby + Snapshot restore.

        This uses the existing FailoverService which:
        1. Creates snapshot of current GPU
        2. Provisions new GPU
        3. Restores snapshot

        Returns:
            Dict with success status and new instance info
        """
        try:
            # Use existing FailoverService
            failover_service = FailoverService(
                vast_api_key=self.vast_api_key,
                b2_endpoint=self.b2_endpoint,
                b2_bucket=self.b2_bucket,
            )

            logger.info(f"[{failover_id}] Starting CPU Standby failover process...")

            result = await failover_service.execute_failover(
                gpu_instance_id=gpu_instance_id,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                failover_id=failover_id,
                workspace_path=workspace_path,
            )

            if result.success:
                return {
                    'success': True,
                    'new_gpu_id': result.new_gpu_id,
                    'new_ssh_host': result.new_ssh_host,
                    'new_ssh_port': result.new_ssh_port,
                    'new_gpu_name': result.new_gpu_name,
                    'snapshot_id': result.snapshot_id,
                    'total_ms': result.total_ms,
                }
            else:
                return {
                    'success': False,
                    'error': result.error or f"Failed at phase: {result.failed_phase}"
                }

        except Exception as e:
            logger.error(f"[{failover_id}] CPU Standby error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def check_failover_readiness(self, machine_id: int) -> Dict[str, Any]:
        """
        Check if failover is ready for a machine.

        Returns:
            Dict with readiness status for each strategy
        """
        effective_config = self.settings_manager.get_effective_config(machine_id)
        strategy = effective_config['effective_strategy']

        result = {
            'machine_id': machine_id,
            'effective_strategy': strategy,
            'warm_pool_ready': False,
            'warm_pool_status': None,
            'cpu_standby_ready': False,
            'cpu_standby_status': None,
            'overall_ready': False,
        }

        # Check Warm Pool
        if strategy in ['warm_pool', 'both']:
            try:
                manager = get_warm_pool_manager(machine_id, self.vast_api_key)
                status = manager.get_status()
                result['warm_pool_status'] = status
                result['warm_pool_ready'] = (
                    status.get('state') == 'active' and
                    status.get('standby_gpu_id') is not None
                )
            except Exception as e:
                result['warm_pool_status'] = {'error': str(e)}

        # Check CPU Standby
        if strategy in ['cpu_standby', 'both']:
            try:
                from src.services.standby import StandbyManager
                standby_manager = StandbyManager()
                association = standby_manager.get_association(machine_id)
                result['cpu_standby_status'] = association
                result['cpu_standby_ready'] = association is not None
            except Exception as e:
                result['cpu_standby_status'] = {'error': str(e)}

        # Overall readiness
        if strategy == 'warm_pool':
            result['overall_ready'] = result['warm_pool_ready']
        elif strategy == 'cpu_standby':
            result['overall_ready'] = result['cpu_standby_ready']
        elif strategy == 'both':
            result['overall_ready'] = result['warm_pool_ready'] or result['cpu_standby_ready']
        elif strategy == 'disabled':
            result['overall_ready'] = False

        return result


# Singleton instance
_orchestrator: Optional[FailoverOrchestrator] = None


def get_failover_orchestrator(
    vast_api_key: Optional[str] = None,
    gcp_credentials: Optional[dict] = None,
) -> FailoverOrchestrator:
    """Get or create the global FailoverOrchestrator instance"""
    global _orchestrator

    if _orchestrator is None:
        import os
        if not vast_api_key:
            vast_api_key = os.getenv("VAST_API_KEY", "")
        _orchestrator = FailoverOrchestrator(
            vast_api_key=vast_api_key,
            gcp_credentials=gcp_credentials,
        )

    return _orchestrator


# Convenience function
async def execute_orchestrated_failover(
    machine_id: int,
    gpu_instance_id: int,
    ssh_host: str,
    ssh_port: int,
    vast_api_key: Optional[str] = None,
    **kwargs
) -> OrchestratedFailoverResult:
    """Quick function to execute an orchestrated failover"""
    orchestrator = get_failover_orchestrator(vast_api_key)
    return await orchestrator.execute_failover(
        machine_id=machine_id,
        gpu_instance_id=gpu_instance_id,
        ssh_host=ssh_host,
        ssh_port=ssh_port,
        **kwargs
    )
