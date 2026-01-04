"""
Failover Service - Orchestrates complete GPU failover process

This service coordinates:
1. Snapshot creation (GPUSnapshotService)
2. GPU provisioning with race strategy (GPUProvisioner)
3. Snapshot restoration
4. Inference testing

Resilience features:
- Input validation
- Rate limiting
- Circuit breaker
- Resource cleanup on failure
- Metrics collection
- Audit logging
"""

import asyncio
import time
import logging
import subprocess
import requests.exceptions
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from ..gpu.provisioner import GPUProvisioner, ProvisionResult
from ..gpu.snapshot import GPUSnapshotService
from ...core.resilience import (
    FailoverConfig,
    validate_failover_input,
    ValidationError,
    get_rate_limiter,
    RateLimitExceeded,
    get_circuit_breaker,
    CircuitOpenError,
    get_cleanup_manager,
    get_metrics,
    audit_log,
)

logger = logging.getLogger(__name__)


@dataclass
class FailoverResult:
    """Result of a complete failover operation"""
    success: bool
    failover_id: str

    # Original GPU info
    original_gpu_id: int
    original_ssh_host: str
    original_ssh_port: int

    # New GPU info
    new_gpu_id: Optional[int] = None
    new_ssh_host: Optional[str] = None
    new_ssh_port: Optional[int] = None
    new_gpu_name: Optional[str] = None

    # Snapshot info
    snapshot_id: Optional[str] = None
    snapshot_size_bytes: int = 0
    snapshot_type: Optional[str] = None  # "full" or "incremental"
    base_snapshot_id: Optional[str] = None  # For incremental snapshots
    files_changed: Optional[int] = None  # For incremental snapshots

    # Timing breakdown (all in milliseconds)
    snapshot_creation_ms: int = 0
    gpu_provisioning_ms: int = 0
    restore_ms: int = 0
    inference_test_ms: int = 0
    total_ms: int = 0

    # Inference test
    inference_success: Optional[bool] = None
    inference_response: Optional[str] = None

    # Error info
    error: Optional[str] = None
    failed_phase: Optional[str] = None

    # Extra details
    phase_timings: Dict[str, int] = field(default_factory=dict)
    gpus_tried: int = 0
    rounds_attempted: int = 0


class FailoverService:
    """
    Orchestrates complete GPU failover process.

    Features:
    - Input validation
    - Rate limiting (max 5 failovers per machine per 24h)
    - Circuit breaker (skip failing strategies)
    - Resource cleanup on failure
    - Metrics and audit logging

    Usage:
        service = FailoverService(vast_api_key="...")

        result = await service.execute_failover(
            gpu_instance_id=12345,
            ssh_host="ssh7.vast.ai",
            ssh_port=12345,
            model="qwen2.5:0.5b"
        )

        if result.success:
            logger.info(f"Failover complete! New GPU: {result.new_ssh_host}:{result.new_ssh_port}")
    """

    def __init__(
        self,
        vast_api_key: str,
        b2_endpoint: str = None,
        b2_bucket: str = None,
    ):
        self.vast_api_key = vast_api_key
        self.gpu_provisioner = GPUProvisioner(vast_api_key)

        # Use config from environment or defaults
        b2_endpoint = b2_endpoint or FailoverConfig.B2_ENDPOINT
        b2_bucket = b2_bucket or FailoverConfig.B2_BUCKET

        self.snapshot_service = GPUSnapshotService(b2_endpoint, b2_bucket)
        self._cleanup = get_cleanup_manager()
        self._metrics = get_metrics()
        self._rate_limiter = get_rate_limiter()
        self._circuit_breaker = get_circuit_breaker()

    async def execute_failover(
        self,
        gpu_instance_id: int,
        ssh_host: str,
        ssh_port: int,
        failover_id: str,
        workspace_path: str = "/workspace",
        model: Optional[str] = None,
        test_prompt: str = "Hello",
        min_gpu_ram: int = 10000,
        max_gpu_price: float = 1.0,
        user_id: Optional[str] = None,
        skip_rate_limit: bool = False,
    ) -> FailoverResult:
        """
        Execute a complete failover operation with resilience.

        Phases:
        1. Validate input and check rate limits
        2. Create snapshot of current GPU
        3. Provision new GPU using race strategy
        4. Restore snapshot to new GPU
        5. Test inference (if model specified)

        Args:
            gpu_instance_id: Current GPU instance ID
            ssh_host: Current GPU SSH host
            ssh_port: Current GPU SSH port
            failover_id: Unique ID for this failover
            workspace_path: Path to backup/restore
            model: Ollama model for inference test (optional)
            test_prompt: Prompt for inference test
            min_gpu_ram: Minimum GPU RAM for new GPU
            max_gpu_price: Maximum price for new GPU
            user_id: User who triggered failover (for audit)
            skip_rate_limit: Skip rate limiting (for automated recovery)

        Returns:
            FailoverResult with all details

        Raises:
            ValidationError: If input parameters are invalid
            RateLimitExceeded: If rate limit is exceeded
            CircuitOpenError: If circuit breaker is open
        """
        start_time = time.time()
        phase_timings = {}
        strategy = "cpu_standby"  # Strategy name for metrics

        result = FailoverResult(
            success=False,
            failover_id=failover_id,
            original_gpu_id=gpu_instance_id,
            original_ssh_host=ssh_host,
            original_ssh_port=ssh_port,
        )

        try:
            # ==============================================================
            # PHASE 0: Validation and Pre-checks
            # ==============================================================
            logger.info(f"[{failover_id}] Phase 0: Validating input...")

            # Validate input parameters
            validate_failover_input(gpu_instance_id, ssh_host, ssh_port, workspace_path)

            # Check rate limit
            if not skip_rate_limit:
                self._rate_limiter.check(gpu_instance_id)

            # Check circuit breaker
            self._circuit_breaker.check(strategy)

            # Audit log start
            audit_log(
                "failover",
                "start",
                "initiated",
                machine_id=gpu_instance_id,
                user_id=user_id,
                failover_id=failover_id,
            )
            # ============================================================
            # PHASE 1: Create Snapshot (Incremental if base exists)
            # ============================================================
            logger.info(f"[{failover_id}] Phase 1: Creating snapshot...")
            phase_start = time.time()

            snapshot_name = f"failover-{failover_id}"

            # Check for existing base snapshot (simulated - in production would query DB)
            # For now, try incremental by looking for periodic-{instance_id}-* pattern
            base_snapshot_id = self._find_latest_base_snapshot(gpu_instance_id)

            if base_snapshot_id:
                logger.info(f"[{failover_id}] Found base snapshot: {base_snapshot_id}, creating incremental...")
                try:
                    snapshot_info = self.snapshot_service.create_incremental_snapshot(
                        instance_id=str(gpu_instance_id),
                        ssh_host=ssh_host,
                        ssh_port=ssh_port,
                        base_snapshot_id=base_snapshot_id,
                        workspace_path=workspace_path,
                        snapshot_name=snapshot_name,
                    )
                    snapshot_info["snapshot_type"] = "incremental"
                except Exception as e:
                    logger.warning(f"[{failover_id}] Incremental snapshot failed, falling back to full: {e}")
                    base_snapshot_id = None

            if not base_snapshot_id:
                # Full snapshot (no base available or incremental failed)
                logger.info(f"[{failover_id}] No base snapshot, creating full snapshot...")
                snapshot_info = self.snapshot_service.create_snapshot(
                    instance_id=str(gpu_instance_id),
                    ssh_host=ssh_host,
                    ssh_port=ssh_port,
                    workspace_path=workspace_path,
                    snapshot_name=snapshot_name,
                )
                snapshot_info["snapshot_type"] = "full"

            phase_timings["snapshot_creation"] = int((time.time() - phase_start) * 1000)
            result.snapshot_creation_ms = phase_timings["snapshot_creation"]
            result.snapshot_id = snapshot_info.get("snapshot_id", snapshot_name)
            result.snapshot_size_bytes = snapshot_info.get("size_compressed", 0)
            result.snapshot_type = snapshot_info.get("snapshot_type", "full")
            result.base_snapshot_id = snapshot_info.get("base_snapshot_id") if base_snapshot_id else None
            result.files_changed = snapshot_info.get("files_changed")

            logger.info(
                f"[{failover_id}] Snapshot created ({result.snapshot_type}): "
                f"{result.snapshot_id} ({result.snapshot_size_bytes} bytes) in {result.snapshot_creation_ms}ms"
            )

            # ============================================================
            # PHASE 2: Provision New GPU (Race Strategy)
            # ============================================================
            logger.info(f"[{failover_id}] Phase 2: Provisioning new GPU...")
            phase_start = time.time()

            provision_result = await self.gpu_provisioner.provision_fast(
                min_gpu_ram=min_gpu_ram,
                max_price=max_gpu_price,
                gpus_per_round=5,
                timeout_per_round=90,  # 90s - real GPUs often take 60-90s
                max_rounds=2,  # Fewer rounds but longer timeout
            )

            phase_timings["gpu_provisioning"] = int((time.time() - phase_start) * 1000)
            result.gpu_provisioning_ms = phase_timings["gpu_provisioning"]
            result.gpus_tried = provision_result.gpus_tried
            result.rounds_attempted = provision_result.rounds_attempted

            if not provision_result.success:
                raise Exception(f"GPU provisioning failed: {provision_result.error}")

            result.new_gpu_id = provision_result.instance_id
            result.new_ssh_host = provision_result.ssh_host
            result.new_ssh_port = provision_result.ssh_port
            result.new_gpu_name = provision_result.gpu_name

            # Register new GPU for cleanup on failure
            self._cleanup.register(failover_id, "gpu", str(result.new_gpu_id))

            logger.info(
                f"[{failover_id}] GPU provisioned: {result.new_gpu_name} "
                f"({result.new_ssh_host}:{result.new_ssh_port}) in {result.gpu_provisioning_ms}ms"
            )

            # ============================================================
            # PHASE 3: Restore Snapshot
            # ============================================================
            logger.info(f"[{failover_id}] Phase 3: Restoring snapshot...")
            phase_start = time.time()

            restore_info = self.snapshot_service.restore_snapshot(
                snapshot_id=snapshot_name,
                ssh_host=result.new_ssh_host,
                ssh_port=result.new_ssh_port,
                workspace_path=workspace_path,
            )

            phase_timings["restore"] = int((time.time() - phase_start) * 1000)
            result.restore_ms = phase_timings["restore"]

            logger.info(f"[{failover_id}] Snapshot restored in {result.restore_ms}ms")

            # ============================================================
            # PHASE 3.5: Validate Restore
            # ============================================================
            logger.info(f"[{failover_id}] Phase 3.5: Validating restore...")
            phase_start = time.time()

            validation_result = self._validate_restore(
                ssh_host=result.new_ssh_host,
                ssh_port=result.new_ssh_port,
                workspace_path=workspace_path,
                snapshot_info=snapshot_info,
            )

            phase_timings["validation"] = int((time.time() - phase_start) * 1000)

            if not validation_result["success"]:
                raise Exception(f"Restore validation failed: {validation_result.get('error', 'Unknown error')}")

            logger.info(
                f"[{failover_id}] Restore validated: {validation_result.get('files_count', 0)} files "
                f"in {phase_timings['validation']}ms"
            )

            # ============================================================
            # PHASE 4: Test Inference (Optional)
            # ============================================================
            if model:
                logger.info(f"[{failover_id}] Phase 4: Testing inference with {model}...")
                phase_start = time.time()

                inference_result = await self._test_inference(
                    ssh_host=result.new_ssh_host,
                    ssh_port=result.new_ssh_port,
                    model=model,
                    prompt=test_prompt,
                )

                phase_timings["inference_test"] = int((time.time() - phase_start) * 1000)
                result.inference_test_ms = phase_timings["inference_test"]
                result.inference_success = inference_result.get("success", False)
                result.inference_response = inference_result.get("response")

                if result.inference_success:
                    logger.info(
                        f"[{failover_id}] Inference test passed in {result.inference_test_ms}ms"
                    )
                else:
                    logger.warning(
                        f"[{failover_id}] Inference test failed: {inference_result.get('error')}"
                    )

            # ============================================================
            # SUCCESS
            # ============================================================
            result.success = True
            result.total_ms = int((time.time() - start_time) * 1000)
            result.phase_timings = phase_timings

            # Record success in circuit breaker and rate limiter
            self._circuit_breaker.record_success(strategy)
            self._rate_limiter.record(gpu_instance_id)

            # Commit cleanup (don't clean up resources)
            self._cleanup.commit(failover_id)

            # Record metrics
            self._metrics.record(
                machine_id=gpu_instance_id,
                strategy=strategy,
                success=True,
                duration_ms=result.total_ms,
            )

            # Audit log success
            audit_log(
                "failover",
                "complete",
                "success",
                machine_id=gpu_instance_id,
                user_id=user_id,
                failover_id=failover_id,
                duration_ms=result.total_ms,
                new_gpu_id=result.new_gpu_id,
            )

            logger.info(
                f"[{failover_id}] FAILOVER COMPLETE in {result.total_ms}ms "
                f"(snapshot: {result.snapshot_creation_ms}ms, "
                f"gpu: {result.gpu_provisioning_ms}ms, "
                f"restore: {result.restore_ms}ms)"
            )

            return result

        except (ValidationError, RateLimitExceeded, CircuitOpenError) as e:
            # Pre-check failures - don't record as circuit failure
            logger.warning(f"[{failover_id}] FAILOVER REJECTED: {type(e).__name__}: {e}")
            result.error = str(e)
            result.total_ms = int((time.time() - start_time) * 1000)
            result.failed_phase = "validation"

            audit_log(
                "failover",
                "rejected",
                type(e).__name__,
                machine_id=gpu_instance_id,
                user_id=user_id,
                failover_id=failover_id,
                error=str(e),
            )

            return result

        except subprocess.TimeoutExpired as e:
            # SSH/command timeout
            logger.error(f"[{failover_id}] FAILOVER FAILED (timeout): {e}")
            result.error = f"Timeout: {e}"
            result.total_ms = int((time.time() - start_time) * 1000)
            result.phase_timings = phase_timings
            result.failed_phase = self._determine_failed_phase(phase_timings)

            self._handle_failure(
                failover_id, gpu_instance_id, user_id, strategy,
                result.total_ms, result.failed_phase, result.error
            )

            return result

        except requests.exceptions.RequestException as e:
            # Network/API errors
            logger.error(f"[{failover_id}] FAILOVER FAILED (network): {e}")
            result.error = f"Network error: {e}"
            result.total_ms = int((time.time() - start_time) * 1000)
            result.phase_timings = phase_timings
            result.failed_phase = self._determine_failed_phase(phase_timings)

            self._handle_failure(
                failover_id, gpu_instance_id, user_id, strategy,
                result.total_ms, result.failed_phase, result.error
            )

            return result

        except Exception as e:
            # Generic error
            logger.error(f"[{failover_id}] FAILOVER FAILED: {type(e).__name__}: {e}")
            result.error = str(e)
            result.total_ms = int((time.time() - start_time) * 1000)
            result.phase_timings = phase_timings
            result.failed_phase = self._determine_failed_phase(phase_timings)

            self._handle_failure(
                failover_id, gpu_instance_id, user_id, strategy,
                result.total_ms, result.failed_phase, result.error
            )

            return result

    def _determine_failed_phase(self, phase_timings: Dict[str, int]) -> str:
        """Determine which phase failed based on completed phases."""
        if "snapshot_creation" not in phase_timings:
            return "snapshot_creation"
        elif "gpu_provisioning" not in phase_timings:
            return "gpu_provisioning"
        elif "restore" not in phase_timings:
            return "restore"
        elif "validation" not in phase_timings:
            return "validation"
        else:
            return "inference_test"

    def _handle_failure(
        self,
        failover_id: str,
        machine_id: int,
        user_id: Optional[str],
        strategy: str,
        duration_ms: int,
        failed_phase: str,
        error: str,
    ) -> None:
        """Handle failover failure - cleanup, metrics, audit."""
        # Record failure in circuit breaker
        self._circuit_breaker.record_failure(strategy)

        # Rollback (cleanup orphaned resources)
        from ..gpu.vast import VastService
        try:
            vast_service = VastService(api_key=self.vast_api_key)
            cleanup_results = self._cleanup.rollback(failover_id, vast_service)
            if cleanup_results:
                logger.info(f"[{failover_id}] Cleaned up {len(cleanup_results)} orphaned resources")
        except Exception as ce:
            logger.error(f"[{failover_id}] Cleanup failed: {ce}")

        # Record metrics
        self._metrics.record(
            machine_id=machine_id,
            strategy=strategy,
            success=False,
            duration_ms=duration_ms,
            phase_failed=failed_phase,
            error=error,
        )

        # Audit log failure
        audit_log(
            "failover",
            "failed",
            "failure",
            machine_id=machine_id,
            user_id=user_id,
            failover_id=failover_id,
            error=error,
            phase=failed_phase,
            duration_ms=duration_ms,
        )

    async def _test_inference(
        self,
        ssh_host: str,
        ssh_port: int,
        model: str,
        prompt: str,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Test Ollama inference on the GPU"""
        try:
            # Check if Ollama is running
            check_cmd = f"curl -s http://localhost:11434/api/tags"
            result = subprocess.run(
                [
                    "ssh", "-p", str(ssh_port),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=10",
                    f"root@{ssh_host}",
                    check_cmd
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # Try to start Ollama
                subprocess.run(
                    [
                        "ssh", "-p", str(ssh_port),
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "UserKnownHostsFile=/dev/null",
                        f"root@{ssh_host}",
                        "nohup ollama serve > /dev/null 2>&1 &"
                    ],
                    capture_output=True,
                    timeout=10
                )
                await asyncio.sleep(5)

            # Run inference
            inference_cmd = f'ollama run {model} "{prompt}"'
            result = subprocess.run(
                [
                    "ssh", "-p", str(ssh_port),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=10",
                    f"root@{ssh_host}",
                    inference_cmd
                ],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "response": result.stdout.strip()[:500],  # Limit response size
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip()[:200],
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Inference timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _validate_restore(
        self,
        ssh_host: str,
        ssh_port: int,
        workspace_path: str,
        snapshot_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate that snapshot was restored correctly.

        Checks:
        1. Workspace directory exists
        2. File count matches expected (if available in snapshot_info)
        3. Basic file integrity

        Returns:
            Dict with success status, file counts, and any errors
        """
        try:
            # Count files in restored workspace
            count_cmd = f"find {workspace_path} -type f | wc -l"
            result = subprocess.run(
                [
                    "ssh", "-p", str(ssh_port),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=10",
                    f"root@{ssh_host}",
                    count_cmd
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to list files: {result.stderr.strip()[:200]}"
                }

            files_count = int(result.stdout.strip())

            # If snapshot info has file metadata, compare counts
            expected_files = None
            if "files" in snapshot_info:
                # Full snapshot with file metadata
                expected_files = len(snapshot_info["files"])
            elif "num_files" in snapshot_info:
                # Snapshot has file count
                expected_files = snapshot_info["num_files"]

            # Validate file count matches (with some tolerance for temp files)
            if expected_files is not None:
                # Allow up to 5% difference (for cache files, etc)
                tolerance = max(1, int(expected_files * 0.05))
                if abs(files_count - expected_files) > tolerance:
                    return {
                        "success": False,
                        "error": f"File count mismatch: expected ~{expected_files}, got {files_count}",
                        "files_count": files_count,
                        "expected_files": expected_files
                    }

            # Check workspace is not empty
            if files_count == 0:
                return {
                    "success": False,
                    "error": "Workspace is empty after restore",
                    "files_count": 0
                }

            # All checks passed
            return {
                "success": True,
                "files_count": files_count,
                "expected_files": expected_files
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Validation timeout"}
        except Exception as e:
            return {"success": False, "error": f"Validation error: {str(e)}"}

    def _find_latest_base_snapshot(self, gpu_instance_id: int) -> Optional[str]:
        """
        Encontra o snapshot base mais recente para uma GPU.

        Em produção, isso consultaria:
        1. Banco de dados de snapshots periódicos
        2. PeriodicSnapshotService.get_latest_snapshot()

        Para o teste, simula verificando B2 por padrão periodic-{instance_id}-*
        """
        try:
            import subprocess
            # Listar snapshots no B2 para esta instância
            result = subprocess.run(
                [
                    "s5cmd",
                    "--endpoint-url", self.snapshot_service.r2_endpoint,
                    "ls",
                    f"s3://{self.snapshot_service.r2_bucket}/snapshots/"
                ],
                capture_output=True,
                text=True,
                timeout=60  # Increased from 10s to handle large buckets
            )

            if result.returncode == 0:
                # Parse output para encontrar periodic-{instance_id}-*
                lines = result.stdout.strip().split('\n')
                base_snapshots = []

                for line in lines:
                    if f"periodic-{gpu_instance_id}-" in line or f"base-{gpu_instance_id}-" in line:
                        # Extrair nome do snapshot
                        parts = line.split('/')
                        if len(parts) > 0:
                            snapshot_name = parts[-1].rstrip('/')
                            if snapshot_name:
                                base_snapshots.append(snapshot_name)

                if base_snapshots:
                    # Retornar o mais recente (último timestamp)
                    base_snapshots.sort()
                    latest = base_snapshots[-1]
                    logger.info(f"[FailoverService] Found base snapshot: {latest}")
                    return latest

        except Exception as e:
            logger.warning(f"[FailoverService] Error finding base snapshot: {e}")

        return None


# Convenience function
async def execute_failover(
    vast_api_key: str,
    gpu_instance_id: int,
    ssh_host: str,
    ssh_port: int,
    failover_id: str,
    **kwargs
) -> FailoverResult:
    """Quick function to execute a failover"""
    service = FailoverService(vast_api_key)
    return await service.execute_failover(
        gpu_instance_id=gpu_instance_id,
        ssh_host=ssh_host,
        ssh_port=ssh_port,
        failover_id=failover_id,
        **kwargs
    )
