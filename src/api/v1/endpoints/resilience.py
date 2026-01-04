"""
Resilience API Endpoints

Provides API access to:
- Failover metrics and statistics
- Rate limiting status
- Circuit breaker status
- Resource cleanup
- Snapshot garbage collection
- Audit logs
- Configuration
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from ....core.resilience import (
    FailoverConfig,
    get_rate_limiter,
    get_circuit_breaker,
    get_cleanup_manager,
    get_metrics,
    get_audit_logger,
    get_snapshot_gc,
)
from ..dependencies import require_auth

router = APIRouter(
    prefix="/resilience",
    tags=["Resilience"],
    dependencies=[Depends(require_auth)],
)


# =============================================================================
# CONFIGURATION
# =============================================================================

@router.get("/config")
async def get_resilience_config():
    """
    Get current resilience configuration.

    Returns all configuration values loaded from environment variables.
    """
    return {
        "success": True,
        "config": FailoverConfig.to_dict(),
        "env_vars": {
            "FAILOVER_TIMEOUT_PER_ROUND": "Timeout per provisioning round (seconds)",
            "FAILOVER_MAX_ROUNDS": "Maximum provisioning rounds",
            "FAILOVER_SSH_TIMEOUT": "SSH connection timeout (seconds)",
            "FAILOVER_INFERENCE_TIMEOUT": "Inference test timeout (seconds)",
            "FAILOVER_MAX_PER_DAY": "Max failovers per machine per 24h",
            "FAILOVER_MIN_INTERVAL": "Min seconds between failovers",
            "FAILOVER_CIRCUIT_THRESHOLD": "Failures to open circuit",
            "FAILOVER_CIRCUIT_TIMEOUT": "Circuit breaker timeout (seconds)",
            "B2_ENDPOINT": "B2/S3 endpoint URL",
            "B2_BUCKET": "B2/S3 bucket name",
        },
    }


# =============================================================================
# METRICS
# =============================================================================

@router.get("/metrics")
async def get_failover_metrics():
    """
    Get failover metrics and statistics.

    Returns:
    - Total failovers (success/failure counts)
    - Last hour/day statistics
    - Statistics by strategy
    - Recent failures with details
    """
    metrics = get_metrics()
    return {
        "success": True,
        "metrics": metrics.get_stats(),
    }


# =============================================================================
# RATE LIMITING
# =============================================================================

@router.get("/rate-limit/{machine_id}")
async def get_rate_limit_status(machine_id: int):
    """
    Get rate limit status for a specific machine.

    Returns:
    - Failovers in last 24h
    - Remaining allowed failovers
    - Whether failover is currently allowed
    - Last failover timestamp
    """
    rate_limiter = get_rate_limiter()
    stats = rate_limiter.get_stats(machine_id)
    return {
        "success": True,
        "rate_limit": stats,
    }


@router.post("/rate-limit/{machine_id}/reset")
async def reset_rate_limit(machine_id: int):
    """
    Reset rate limit for a specific machine.

    Use with caution - allows immediate failover.
    """
    # Rate limiter doesn't have reset per-machine, but we can clear history
    rate_limiter = get_rate_limiter()
    rate_limiter._history.pop(machine_id, None)
    return {
        "success": True,
        "message": f"Rate limit reset for machine {machine_id}",
    }


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

@router.get("/circuit-breaker")
async def get_circuit_breaker_status():
    """
    Get circuit breaker status for all strategies.

    Returns status of each strategy circuit:
    - State (closed, open, half_open)
    - Failure count
    - Success count
    - Last failure/success timestamps
    """
    circuit_breaker = get_circuit_breaker()
    return {
        "success": True,
        "circuits": circuit_breaker.get_stats(),
    }


@router.post("/circuit-breaker/{strategy}/reset")
async def reset_circuit_breaker(strategy: str):
    """
    Reset circuit breaker for a specific strategy.

    Available strategies: cpu_standby, warm_pool, regional_volume
    """
    circuit_breaker = get_circuit_breaker()
    circuit_breaker.reset(strategy)
    return {
        "success": True,
        "message": f"Circuit breaker reset for strategy {strategy}",
    }


# =============================================================================
# RESOURCE CLEANUP
# =============================================================================

@router.get("/cleanup/pending")
async def get_pending_cleanup():
    """
    Get resources pending cleanup.

    These are resources created during failover that haven't been
    committed (success) or rolled back (failure) yet.
    """
    cleanup_manager = get_cleanup_manager()
    return {
        "success": True,
        "pending": cleanup_manager.get_pending(),
    }


@router.post("/cleanup/{failover_id}/rollback")
async def rollback_failover_resources(failover_id: str):
    """
    Manually rollback resources for a failed failover.

    Use this to clean up orphaned resources if automatic cleanup failed.
    """
    cleanup_manager = get_cleanup_manager()

    # Need VastService for GPU cleanup
    import os
    from ....services.gpu.vast import VastService

    vast_api_key = os.getenv("VAST_API_KEY")
    if not vast_api_key:
        raise HTTPException(status_code=400, detail="VAST_API_KEY not configured")

    vast_service = VastService(api_key=vast_api_key)
    results = cleanup_manager.rollback(failover_id, vast_service)

    return {
        "success": True,
        "message": f"Rolled back {len(results)} resources",
        "results": results,
    }


# =============================================================================
# SNAPSHOT GARBAGE COLLECTION
# =============================================================================

@router.get("/gc/status")
async def get_gc_status():
    """
    Get snapshot garbage collector status.

    Returns:
    - Last run timestamp
    - Configuration (max age, auto cleanup enabled)
    """
    gc = get_snapshot_gc()
    return {
        "success": True,
        "last_run": gc._last_run,
        "config": {
            "max_age_days": FailoverConfig.ORPHAN_SNAPSHOT_AGE_DAYS,
            "auto_cleanup_enabled": FailoverConfig.AUTO_CLEANUP_ENABLED,
        },
    }


@router.post("/gc/run")
async def run_garbage_collection(
    dry_run: bool = Query(default=True, description="If true, only report what would be deleted"),
    max_age_days: Optional[int] = Query(default=None, description="Override max age in days"),
):
    """
    Run snapshot garbage collection.

    By default runs in dry-run mode (reports but doesn't delete).
    Set dry_run=false to actually delete old snapshots.
    """
    gc = get_snapshot_gc()
    results = await gc.run(dry_run=dry_run, max_age_days=max_age_days)

    return {
        "success": True,
        "gc_results": results,
    }


# =============================================================================
# AUDIT LOGS
# =============================================================================

@router.get("/audit")
async def get_audit_logs(
    limit: int = Query(default=100, le=1000, description="Number of entries to return"),
):
    """
    Get recent audit log entries.

    Returns failover audit events including:
    - Start, complete, failed events
    - Machine IDs, user IDs
    - Timestamps and durations
    - Error details for failures
    """
    audit_logger = get_audit_logger()
    entries = audit_logger.get_recent(limit=limit)

    return {
        "success": True,
        "entries": entries,
        "count": len(entries),
    }


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def resilience_health():
    """
    Health check for resilience systems.

    Returns status of all resilience components.
    """
    metrics = get_metrics()
    circuit_breaker = get_circuit_breaker()
    cleanup_manager = get_cleanup_manager()

    stats = metrics.get_stats()
    circuits = circuit_breaker.get_stats()
    pending = cleanup_manager.get_pending()

    # Check for issues
    issues = []

    # Check if any circuit is open
    for name, circuit in circuits.items():
        if circuit["state"] == "open":
            issues.append(f"Circuit {name} is OPEN")

    # Check if there are stale pending cleanups
    if len(pending) > 5:
        issues.append(f"Too many pending cleanups: {len(pending)}")

    # Check recent failure rate
    if stats["last_hour"]["failovers"] > 0:
        failure_rate = stats["last_hour"]["failed"] / stats["last_hour"]["failovers"]
        if failure_rate > 0.5:
            issues.append(f"High failure rate in last hour: {failure_rate:.0%}")

    return {
        "success": True,
        "healthy": len(issues) == 0,
        "issues": issues,
        "summary": {
            "total_failovers": stats["total"]["failovers"],
            "success_rate": f"{stats['total']['success_rate']:.1f}%",
            "circuits_open": sum(1 for c in circuits.values() if c["state"] == "open"),
            "pending_cleanups": len(pending),
        },
    }
