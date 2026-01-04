"""
Resilience Module - Centralized resilience patterns for Dumont Cloud.

Implements:
- Resource cleanup on partial failures
- Rate limiting for failover operations
- Circuit breaker for failing strategies
- Input validation
- Metrics collection
- Audit logging

Usage:
    from src.core.resilience import (
        validate_failover_input,
        rate_limit_failover,
        circuit_breaker,
        cleanup_orphaned_resources,
        FailoverMetrics,
        audit_log,
    )
"""

import os
import time
import json
import logging
import threading
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION FROM ENVIRONMENT
# =============================================================================

class FailoverConfig:
    """
    Failover configuration loaded from environment variables.
    All settings can be overridden via env vars.
    """

    # Timeouts (in seconds)
    TIMEOUT_PER_ROUND: int = int(os.getenv("FAILOVER_TIMEOUT_PER_ROUND", "90"))
    MAX_ROUNDS: int = int(os.getenv("FAILOVER_MAX_ROUNDS", "2"))
    SSH_CONNECT_TIMEOUT: int = int(os.getenv("FAILOVER_SSH_TIMEOUT", "15"))
    INFERENCE_TIMEOUT: int = int(os.getenv("FAILOVER_INFERENCE_TIMEOUT", "120"))
    VALIDATION_TIMEOUT: int = int(os.getenv("FAILOVER_VALIDATION_TIMEOUT", "60"))

    # B2/S3 Storage
    B2_ENDPOINT: str = os.getenv("B2_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")
    B2_BUCKET: str = os.getenv("B2_BUCKET", "dumoncloud-snapshot")
    B2_ACCESS_KEY: str = os.getenv("B2_KEY_ID", "")
    B2_SECRET_KEY: str = os.getenv("B2_APP_KEY", "")

    # Rate Limiting
    MAX_FAILOVERS_PER_MACHINE_24H: int = int(os.getenv("FAILOVER_MAX_PER_DAY", "5"))
    MIN_SECONDS_BETWEEN_FAILOVERS: int = int(os.getenv("FAILOVER_MIN_INTERVAL", "300"))  # 5 min

    # Circuit Breaker
    CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("FAILOVER_CIRCUIT_THRESHOLD", "3"))
    CIRCUIT_BREAKER_TIMEOUT: int = int(os.getenv("FAILOVER_CIRCUIT_TIMEOUT", "300"))  # 5 min

    # Cleanup
    ORPHAN_SNAPSHOT_AGE_DAYS: int = int(os.getenv("FAILOVER_ORPHAN_DAYS", "90"))
    AUTO_CLEANUP_ENABLED: bool = os.getenv("FAILOVER_AUTO_CLEANUP", "true").lower() == "true"

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Export all config as dict."""
        return {
            "timeout_per_round": cls.TIMEOUT_PER_ROUND,
            "max_rounds": cls.MAX_ROUNDS,
            "ssh_connect_timeout": cls.SSH_CONNECT_TIMEOUT,
            "inference_timeout": cls.INFERENCE_TIMEOUT,
            "validation_timeout": cls.VALIDATION_TIMEOUT,
            "b2_endpoint": cls.B2_ENDPOINT,
            "b2_bucket": cls.B2_BUCKET,
            "max_failovers_per_day": cls.MAX_FAILOVERS_PER_MACHINE_24H,
            "min_interval_seconds": cls.MIN_SECONDS_BETWEEN_FAILOVERS,
            "circuit_breaker_threshold": cls.CIRCUIT_BREAKER_THRESHOLD,
            "circuit_breaker_timeout": cls.CIRCUIT_BREAKER_TIMEOUT,
        }


# =============================================================================
# INPUT VALIDATION
# =============================================================================

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_failover_input(
    machine_id: int,
    ssh_host: str,
    ssh_port: int,
    workspace_path: str = "/workspace",
) -> None:
    """
    Validate failover input parameters.

    Raises:
        ValidationError: If any parameter is invalid
    """
    errors = []

    # machine_id
    if not isinstance(machine_id, int) or machine_id <= 0:
        errors.append(f"machine_id must be positive integer, got {machine_id}")

    # ssh_host
    if not ssh_host or not isinstance(ssh_host, str):
        errors.append("ssh_host must be non-empty string")
    elif len(ssh_host) > 255:
        errors.append("ssh_host too long (max 255 chars)")

    # ssh_port
    if not isinstance(ssh_port, int) or not (1 <= ssh_port <= 65535):
        errors.append(f"ssh_port must be 1-65535, got {ssh_port}")

    # workspace_path
    if not workspace_path or not workspace_path.startswith("/"):
        errors.append(f"workspace_path must be absolute path, got {workspace_path}")

    if errors:
        raise ValidationError("; ".join(errors))

    logger.debug(f"[Validation] Input validated: machine={machine_id}, host={ssh_host}:{ssh_port}")


# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, retry_after: int = 0):
        super().__init__(message)
        self.retry_after = retry_after


class FailoverRateLimiter:
    """
    Rate limiter for failover operations.

    Prevents:
    - More than N failovers per machine in 24h
    - Failovers within M seconds of each other
    """

    def __init__(self):
        self._lock = threading.Lock()
        # machine_id -> list of timestamps
        self._history: Dict[int, List[float]] = {}

    def check(self, machine_id: int) -> None:
        """
        Check if failover is allowed for this machine.

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        with self._lock:
            now = time.time()
            cutoff_24h = now - 86400  # 24 hours ago

            # Get and clean history
            history = self._history.get(machine_id, [])
            history = [t for t in history if t > cutoff_24h]
            self._history[machine_id] = history

            # Check 24h limit
            if len(history) >= FailoverConfig.MAX_FAILOVERS_PER_MACHINE_24H:
                oldest = min(history)
                retry_after = int(oldest + 86400 - now)
                raise RateLimitExceeded(
                    f"Machine {machine_id} has reached max {FailoverConfig.MAX_FAILOVERS_PER_MACHINE_24H} "
                    f"failovers in 24h. Try again in {retry_after}s",
                    retry_after=retry_after
                )

            # Check minimum interval
            if history:
                last_failover = max(history)
                elapsed = now - last_failover
                if elapsed < FailoverConfig.MIN_SECONDS_BETWEEN_FAILOVERS:
                    retry_after = int(FailoverConfig.MIN_SECONDS_BETWEEN_FAILOVERS - elapsed)
                    raise RateLimitExceeded(
                        f"Machine {machine_id} had failover {int(elapsed)}s ago. "
                        f"Minimum interval is {FailoverConfig.MIN_SECONDS_BETWEEN_FAILOVERS}s. "
                        f"Try again in {retry_after}s",
                        retry_after=retry_after
                    )

    def record(self, machine_id: int) -> None:
        """Record a failover for this machine."""
        with self._lock:
            if machine_id not in self._history:
                self._history[machine_id] = []
            self._history[machine_id].append(time.time())
            logger.debug(f"[RateLimiter] Recorded failover for machine {machine_id}")

    def get_stats(self, machine_id: int) -> Dict[str, Any]:
        """Get rate limit stats for a machine."""
        with self._lock:
            now = time.time()
            cutoff_24h = now - 86400
            history = [t for t in self._history.get(machine_id, []) if t > cutoff_24h]

            return {
                "machine_id": machine_id,
                "failovers_24h": len(history),
                "max_allowed": FailoverConfig.MAX_FAILOVERS_PER_MACHINE_24H,
                "remaining": max(0, FailoverConfig.MAX_FAILOVERS_PER_MACHINE_24H - len(history)),
                "last_failover": max(history) if history else None,
                "can_failover": len(history) < FailoverConfig.MAX_FAILOVERS_PER_MACHINE_24H,
            }


# Global rate limiter
_rate_limiter = FailoverRateLimiter()


def get_rate_limiter() -> FailoverRateLimiter:
    """Get global rate limiter instance."""
    return _rate_limiter


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, skip attempts
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitOpenError(Exception):
    """Raised when circuit is open."""
    pass


@dataclass
class CircuitStats:
    """Statistics for a circuit."""
    failures: int = 0
    successes: int = 0
    last_failure: Optional[float] = None
    last_success: Optional[float] = None
    state: CircuitState = CircuitState.CLOSED
    opened_at: Optional[float] = None


class CircuitBreaker:
    """
    Circuit breaker for failover strategies.

    When a strategy fails N times consecutively:
    - Circuit opens (skip attempts for M seconds)
    - After M seconds, circuit goes half-open (allow one test)
    - If test succeeds, circuit closes
    - If test fails, circuit re-opens
    """

    def __init__(
        self,
        threshold: int = None,
        timeout: int = None,
    ):
        self.threshold = threshold or FailoverConfig.CIRCUIT_BREAKER_THRESHOLD
        self.timeout = timeout or FailoverConfig.CIRCUIT_BREAKER_TIMEOUT
        self._lock = threading.Lock()
        self._circuits: Dict[str, CircuitStats] = {}

    def _get_circuit(self, name: str) -> CircuitStats:
        """Get or create circuit for strategy."""
        if name not in self._circuits:
            self._circuits[name] = CircuitStats()
        return self._circuits[name]

    def check(self, strategy: str) -> None:
        """
        Check if strategy can be attempted.

        Raises:
            CircuitOpenError: If circuit is open
        """
        with self._lock:
            circuit = self._get_circuit(strategy)
            now = time.time()

            if circuit.state == CircuitState.CLOSED:
                return  # OK to proceed

            if circuit.state == CircuitState.OPEN:
                # Check if timeout has passed
                if circuit.opened_at and (now - circuit.opened_at) >= self.timeout:
                    circuit.state = CircuitState.HALF_OPEN
                    logger.info(f"[CircuitBreaker] {strategy} circuit half-open, allowing test")
                    return
                else:
                    remaining = int(self.timeout - (now - circuit.opened_at)) if circuit.opened_at else 0
                    raise CircuitOpenError(
                        f"Strategy {strategy} circuit is OPEN after {circuit.failures} failures. "
                        f"Will retry in {remaining}s"
                    )

            # HALF_OPEN - allow one attempt
            return

    def record_success(self, strategy: str) -> None:
        """Record successful execution."""
        with self._lock:
            circuit = self._get_circuit(strategy)
            circuit.successes += 1
            circuit.last_success = time.time()
            circuit.failures = 0  # Reset consecutive failures
            circuit.state = CircuitState.CLOSED
            logger.debug(f"[CircuitBreaker] {strategy} success, circuit closed")

    def record_failure(self, strategy: str) -> None:
        """Record failed execution."""
        with self._lock:
            circuit = self._get_circuit(strategy)
            circuit.failures += 1
            circuit.last_failure = time.time()

            if circuit.failures >= self.threshold:
                circuit.state = CircuitState.OPEN
                circuit.opened_at = time.time()
                logger.warning(
                    f"[CircuitBreaker] {strategy} circuit OPENED after "
                    f"{circuit.failures} consecutive failures"
                )

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get all circuit stats."""
        with self._lock:
            return {
                name: {
                    "state": circuit.state.value,
                    "failures": circuit.failures,
                    "successes": circuit.successes,
                    "last_failure": circuit.last_failure,
                    "last_success": circuit.last_success,
                    "threshold": self.threshold,
                    "timeout": self.timeout,
                }
                for name, circuit in self._circuits.items()
            }

    def reset(self, strategy: str) -> None:
        """Manually reset a circuit."""
        with self._lock:
            if strategy in self._circuits:
                self._circuits[strategy] = CircuitStats()
                logger.info(f"[CircuitBreaker] {strategy} circuit reset")


# Global circuit breaker
_circuit_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    """Get global circuit breaker instance."""
    return _circuit_breaker


# =============================================================================
# RESOURCE CLEANUP
# =============================================================================

@dataclass
class OrphanedResource:
    """Represents an orphaned resource to clean up."""
    resource_type: str  # "gpu", "snapshot", "cpu_standby"
    resource_id: str
    created_at: Optional[float] = None
    reason: str = "orphaned"


class ResourceCleanup:
    """
    Manages cleanup of orphaned resources.

    Tracks resources created during failover and cleans up on failure.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # failover_id -> list of resources
        self._pending: Dict[str, List[OrphanedResource]] = {}

    def register(
        self,
        failover_id: str,
        resource_type: str,
        resource_id: str,
    ) -> None:
        """Register a resource for potential cleanup."""
        with self._lock:
            if failover_id not in self._pending:
                self._pending[failover_id] = []
            self._pending[failover_id].append(OrphanedResource(
                resource_type=resource_type,
                resource_id=resource_id,
                created_at=time.time(),
            ))
            logger.debug(
                f"[Cleanup] Registered {resource_type}:{resource_id} for failover {failover_id}"
            )

    def commit(self, failover_id: str) -> None:
        """
        Mark failover as successful - resources should NOT be cleaned up.
        """
        with self._lock:
            if failover_id in self._pending:
                del self._pending[failover_id]
                logger.debug(f"[Cleanup] Committed {failover_id}, resources retained")

    def rollback(
        self,
        failover_id: str,
        vast_service=None,
    ) -> List[Dict[str, Any]]:
        """
        Rollback a failed failover - clean up all registered resources.

        Returns list of cleanup results.
        """
        with self._lock:
            resources = self._pending.pop(failover_id, [])

        results = []
        for resource in resources:
            result = self._cleanup_resource(resource, vast_service)
            results.append(result)

        if results:
            logger.info(
                f"[Cleanup] Rolled back {failover_id}: {len(results)} resources cleaned"
            )

        return results

    def _cleanup_resource(
        self,
        resource: OrphanedResource,
        vast_service=None,
    ) -> Dict[str, Any]:
        """Clean up a single resource."""
        result = {
            "resource_type": resource.resource_type,
            "resource_id": resource.resource_id,
            "success": False,
            "error": None,
        }

        try:
            if resource.resource_type == "gpu" and vast_service:
                success = vast_service.destroy_instance(int(resource.resource_id))
                result["success"] = success
                if success:
                    logger.info(f"[Cleanup] Destroyed orphaned GPU {resource.resource_id}")
                else:
                    result["error"] = "destroy_instance returned False"

            elif resource.resource_type == "snapshot":
                # Snapshots are cleaned by garbage collector
                result["success"] = True
                result["note"] = "Will be cleaned by snapshot GC"

            elif resource.resource_type == "cpu_standby":
                # TODO: Implement GCP cleanup
                result["success"] = True
                result["note"] = "GCP cleanup not implemented"

            else:
                result["error"] = f"Unknown resource type: {resource.resource_type}"

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"[Cleanup] Failed to clean {resource.resource_type}:{resource.resource_id}: {e}")

        return result

    def get_pending(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all pending resources (for debugging)."""
        with self._lock:
            return {
                fid: [asdict(r) for r in resources]
                for fid, resources in self._pending.items()
            }


# Global cleanup manager
_cleanup_manager = ResourceCleanup()


def get_cleanup_manager() -> ResourceCleanup:
    """Get global cleanup manager instance."""
    return _cleanup_manager


# =============================================================================
# METRICS COLLECTION
# =============================================================================

@dataclass
class FailoverMetricPoint:
    """Single metric data point."""
    timestamp: float
    machine_id: int
    strategy: str
    success: bool
    duration_ms: int
    phase_failed: Optional[str] = None
    error: Optional[str] = None


class FailoverMetrics:
    """
    Collects metrics for failover operations.

    In production, these would be exported to Prometheus/Datadog.
    For now, keeps in-memory for API access.
    """

    def __init__(self, max_history: int = 1000):
        self._lock = threading.Lock()
        self._history: List[FailoverMetricPoint] = []
        self._max_history = max_history

        # Counters
        self._total_failovers = 0
        self._successful_failovers = 0
        self._failed_failovers = 0

        # By strategy
        self._by_strategy: Dict[str, Dict[str, int]] = {}

    def record(
        self,
        machine_id: int,
        strategy: str,
        success: bool,
        duration_ms: int,
        phase_failed: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record a failover metric."""
        with self._lock:
            point = FailoverMetricPoint(
                timestamp=time.time(),
                machine_id=machine_id,
                strategy=strategy,
                success=success,
                duration_ms=duration_ms,
                phase_failed=phase_failed,
                error=error,
            )

            self._history.append(point)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            self._total_failovers += 1
            if success:
                self._successful_failovers += 1
            else:
                self._failed_failovers += 1

            if strategy not in self._by_strategy:
                self._by_strategy[strategy] = {"success": 0, "failure": 0, "total_ms": 0}

            self._by_strategy[strategy]["success" if success else "failure"] += 1
            self._by_strategy[strategy]["total_ms"] += duration_ms

        logger.info(
            f"[Metrics] Failover recorded: machine={machine_id}, strategy={strategy}, "
            f"success={success}, duration={duration_ms}ms"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated metrics."""
        with self._lock:
            now = time.time()
            last_hour = [p for p in self._history if now - p.timestamp < 3600]
            last_day = [p for p in self._history if now - p.timestamp < 86400]

            return {
                "total": {
                    "failovers": self._total_failovers,
                    "successful": self._successful_failovers,
                    "failed": self._failed_failovers,
                    "success_rate": (
                        self._successful_failovers / self._total_failovers * 100
                        if self._total_failovers > 0 else 0
                    ),
                },
                "last_hour": {
                    "failovers": len(last_hour),
                    "successful": sum(1 for p in last_hour if p.success),
                    "failed": sum(1 for p in last_hour if not p.success),
                },
                "last_day": {
                    "failovers": len(last_day),
                    "successful": sum(1 for p in last_day if p.success),
                    "failed": sum(1 for p in last_day if not p.success),
                },
                "by_strategy": {
                    name: {
                        "success": stats["success"],
                        "failure": stats["failure"],
                        "avg_ms": (
                            stats["total_ms"] // (stats["success"] + stats["failure"])
                            if (stats["success"] + stats["failure"]) > 0 else 0
                        ),
                    }
                    for name, stats in self._by_strategy.items()
                },
                "recent_failures": [
                    {
                        "timestamp": p.timestamp,
                        "machine_id": p.machine_id,
                        "strategy": p.strategy,
                        "phase_failed": p.phase_failed,
                        "error": p.error[:100] if p.error else None,
                    }
                    for p in reversed(self._history[-10:])
                    if not p.success
                ],
            }


# Global metrics
_metrics = FailoverMetrics()


def get_metrics() -> FailoverMetrics:
    """Get global metrics instance."""
    return _metrics


# =============================================================================
# AUDIT LOGGING
# =============================================================================

@dataclass
class AuditEntry:
    """Audit log entry."""
    timestamp: str
    event_type: str
    machine_id: Optional[int]
    user_id: Optional[str]
    action: str
    result: str
    details: Dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """
    Audit logger for failover operations.

    Logs all failover actions for compliance and debugging.
    """

    def __init__(self, log_file: Optional[str] = None):
        self._lock = threading.Lock()
        self._log_file = log_file or os.path.expanduser("~/.dumont/failover_audit.jsonl")
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        """Ensure log directory exists."""
        os.makedirs(os.path.dirname(self._log_file), exist_ok=True)

    def log(
        self,
        event_type: str,
        action: str,
        result: str,
        machine_id: Optional[int] = None,
        user_id: Optional[str] = None,
        **details,
    ) -> None:
        """Log an audit entry."""
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            machine_id=machine_id,
            user_id=user_id,
            action=action,
            result=result,
            details=details,
        )

        with self._lock:
            try:
                with open(self._log_file, "a") as f:
                    f.write(json.dumps(asdict(entry)) + "\n")
            except Exception as e:
                logger.error(f"[Audit] Failed to write audit log: {e}")

        # Also log to standard logger
        logger.info(
            f"[Audit] {event_type}: {action} -> {result} "
            f"(machine={machine_id}, user={user_id})"
        )

    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit entries."""
        entries = []
        try:
            with open(self._log_file, "r") as f:
                lines = f.readlines()[-limit:]
                for line in lines:
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
        except FileNotFoundError:
            pass
        return entries


# Global audit logger
_audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    return _audit_logger


def audit_log(
    event_type: str,
    action: str,
    result: str,
    **kwargs,
) -> None:
    """Convenience function for audit logging."""
    _audit_logger.log(event_type, action, result, **kwargs)


# =============================================================================
# DECORATOR FOR RESILIENT FAILOVER
# =============================================================================

def resilient_failover(strategy: str):
    """
    Decorator that adds resilience to failover functions.

    Applies:
    - Input validation
    - Rate limiting
    - Circuit breaker
    - Resource cleanup on failure
    - Metrics collection
    - Audit logging
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(
            machine_id: int,
            ssh_host: str,
            ssh_port: int,
            failover_id: str,
            user_id: Optional[str] = None,
            **kwargs,
        ):
            start_time = time.time()

            try:
                # 1. Validate input
                validate_failover_input(machine_id, ssh_host, ssh_port)

                # 2. Check rate limit
                get_rate_limiter().check(machine_id)

                # 3. Check circuit breaker
                get_circuit_breaker().check(strategy)

                # 4. Audit log start
                audit_log(
                    "failover",
                    f"start_{strategy}",
                    "initiated",
                    machine_id=machine_id,
                    user_id=user_id,
                    failover_id=failover_id,
                )

                # 5. Execute
                result = await func(
                    machine_id=machine_id,
                    ssh_host=ssh_host,
                    ssh_port=ssh_port,
                    failover_id=failover_id,
                    **kwargs,
                )

                # 6. Record success
                duration_ms = int((time.time() - start_time) * 1000)

                if result.success:
                    get_circuit_breaker().record_success(strategy)
                    get_rate_limiter().record(machine_id)
                    get_cleanup_manager().commit(failover_id)
                    get_metrics().record(
                        machine_id, strategy, True, duration_ms
                    )
                    audit_log(
                        "failover",
                        f"complete_{strategy}",
                        "success",
                        machine_id=machine_id,
                        user_id=user_id,
                        failover_id=failover_id,
                        duration_ms=duration_ms,
                    )
                else:
                    get_circuit_breaker().record_failure(strategy)
                    get_cleanup_manager().rollback(failover_id)
                    get_metrics().record(
                        machine_id, strategy, False, duration_ms,
                        phase_failed=result.failed_phase,
                        error=result.error,
                    )
                    audit_log(
                        "failover",
                        f"failed_{strategy}",
                        "failure",
                        machine_id=machine_id,
                        user_id=user_id,
                        failover_id=failover_id,
                        error=result.error,
                        phase=result.failed_phase,
                    )

                return result

            except (ValidationError, RateLimitExceeded, CircuitOpenError) as e:
                # Known errors - don't record as circuit failure
                duration_ms = int((time.time() - start_time) * 1000)
                audit_log(
                    "failover",
                    f"rejected_{strategy}",
                    type(e).__name__,
                    machine_id=machine_id,
                    user_id=user_id,
                    error=str(e),
                )
                raise

            except Exception as e:
                # Unexpected error
                duration_ms = int((time.time() - start_time) * 1000)
                get_circuit_breaker().record_failure(strategy)
                get_cleanup_manager().rollback(failover_id)
                get_metrics().record(
                    machine_id, strategy, False, duration_ms,
                    error=str(e),
                )
                audit_log(
                    "failover",
                    f"error_{strategy}",
                    "exception",
                    machine_id=machine_id,
                    user_id=user_id,
                    failover_id=failover_id,
                    error=str(e),
                )
                raise

        return wrapper
    return decorator


# =============================================================================
# SNAPSHOT GARBAGE COLLECTOR
# =============================================================================

class SnapshotGarbageCollector:
    """
    Cleans up old/orphaned snapshots from B2/S3.
    """

    def __init__(self):
        self._last_run: Optional[float] = None

    async def run(
        self,
        dry_run: bool = True,
        max_age_days: int = None,
    ) -> Dict[str, Any]:
        """
        Run garbage collection on snapshots.

        Args:
            dry_run: If True, only report what would be deleted
            max_age_days: Delete snapshots older than this (default from config)

        Returns:
            Dict with GC results
        """
        import subprocess

        max_age = max_age_days or FailoverConfig.ORPHAN_SNAPSHOT_AGE_DAYS
        cutoff = time.time() - (max_age * 86400)

        results = {
            "dry_run": dry_run,
            "max_age_days": max_age,
            "snapshots_found": 0,
            "snapshots_to_delete": 0,
            "bytes_to_free": 0,
            "deleted": [],
            "errors": [],
        }

        try:
            # List all snapshots
            list_result = subprocess.run(
                [
                    "s5cmd",
                    "--endpoint-url", FailoverConfig.B2_ENDPOINT,
                    "ls",
                    f"s3://{FailoverConfig.B2_BUCKET}/snapshots/",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if list_result.returncode != 0:
                results["errors"].append(f"Failed to list snapshots: {list_result.stderr}")
                return results

            # Parse and filter old snapshots
            for line in list_result.stdout.strip().split('\n'):
                if not line.strip():
                    continue

                results["snapshots_found"] += 1

                # Parse s5cmd output: "2024-01-01 12:00:00   1234567   s3://bucket/path"
                parts = line.split()
                if len(parts) >= 4:
                    # Extract timestamp and check age
                    try:
                        date_str = f"{parts[0]} {parts[1]}"
                        snapshot_time = datetime.strptime(
                            date_str, "%Y-%m-%d %H:%M:%S"
                        ).timestamp()

                        if snapshot_time < cutoff:
                            size = int(parts[2]) if parts[2].isdigit() else 0
                            path = parts[3]

                            results["snapshots_to_delete"] += 1
                            results["bytes_to_free"] += size

                            if not dry_run:
                                # Actually delete
                                del_result = subprocess.run(
                                    [
                                        "s5cmd",
                                        "--endpoint-url", FailoverConfig.B2_ENDPOINT,
                                        "rm",
                                        path,
                                    ],
                                    capture_output=True,
                                    timeout=30,
                                )
                                if del_result.returncode == 0:
                                    results["deleted"].append(path)
                                else:
                                    results["errors"].append(
                                        f"Failed to delete {path}: {del_result.stderr}"
                                    )
                            else:
                                results["deleted"].append(f"[dry-run] {path}")

                    except (ValueError, IndexError) as e:
                        logger.debug(f"[GC] Could not parse line: {line}: {e}")

        except subprocess.TimeoutExpired:
            results["errors"].append("Timeout listing snapshots")
        except Exception as e:
            results["errors"].append(str(e))

        self._last_run = time.time()

        logger.info(
            f"[GC] Snapshot cleanup: found={results['snapshots_found']}, "
            f"to_delete={results['snapshots_to_delete']}, "
            f"bytes={results['bytes_to_free']}"
        )

        return results


# Global GC
_snapshot_gc = SnapshotGarbageCollector()


def get_snapshot_gc() -> SnapshotGarbageCollector:
    """Get global snapshot GC instance."""
    return _snapshot_gc
