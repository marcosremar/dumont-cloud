"""
Exchange Rate Scheduler for Multi-Currency Pricing

Uses APScheduler to run daily exchange rate updates at midnight UTC.
Integrates with FastAPI lifespan for proper startup/shutdown.

Usage:
    # In FastAPI lifespan:
    from src.core.scheduler import init_scheduler, shutdown_scheduler

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_scheduler()
        yield
        await shutdown_scheduler()
"""
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Scheduler instance (singleton)
_scheduler: Optional[AsyncIOScheduler] = None


async def update_exchange_rates_job() -> None:
    """
    Scheduled job to fetch and update exchange rates.

    This job runs daily at midnight UTC. On failure, it logs the error
    but does not crash - cached rates will be used as fallback.
    """
    from src.services.exchange_rate import ExchangeRateService
    from src.config.database import SessionLocal

    logger.info("Starting scheduled exchange rate update...")

    db = None
    try:
        # Create a new database session for the job
        db = SessionLocal()
        service = ExchangeRateService(db)

        # Fetch latest rates from external API
        rates = await service.fetch_latest_rates()

        logger.info(
            f"Exchange rates updated successfully: "
            f"{', '.join(f'{k}={v:.4f}' for k, v in rates.items())}"
        )

    except Exception as e:
        # Log error but don't crash - cached rates will be used
        logger.error(f"Failed to update exchange rates: {e}")

    finally:
        if db:
            db.close()


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """
    Get the scheduler instance.

    Returns:
        The AsyncIOScheduler instance, or None if not initialized.
    """
    return _scheduler


async def init_scheduler(run_immediately: bool = True) -> AsyncIOScheduler:
    """
    Initialize and start the APScheduler for exchange rate updates.

    Schedules a job to run daily at midnight UTC. Optionally runs
    the update immediately on startup to ensure fresh rates.

    Args:
        run_immediately: If True, fetch rates immediately on startup.
            Default is True to ensure rates are available.

    Returns:
        The configured AsyncIOScheduler instance.
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already initialized, skipping...")
        return _scheduler

    logger.info("Initializing exchange rate scheduler...")

    # Create the scheduler
    _scheduler = AsyncIOScheduler(
        timezone="UTC",
        job_defaults={
            "coalesce": True,  # Combine multiple missed runs into one
            "max_instances": 1,  # Only one instance of each job at a time
            "misfire_grace_time": 3600,  # 1 hour grace period for missed jobs
        }
    )

    # Add daily update job - runs at midnight UTC
    _scheduler.add_job(
        update_exchange_rates_job,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="update_exchange_rates_daily",
        name="Daily Exchange Rate Update",
        replace_existing=True,
    )

    # Start the scheduler
    _scheduler.start()
    logger.info("Exchange rate scheduler started (daily at 00:00 UTC)")

    # Optionally run immediately on startup
    if run_immediately:
        logger.info("Running initial exchange rate fetch...")
        try:
            await update_exchange_rates_job()
        except Exception as e:
            # Log but don't fail startup - we can use cached rates
            logger.warning(f"Initial exchange rate fetch failed: {e}")

    return _scheduler


async def shutdown_scheduler() -> None:
    """
    Gracefully shutdown the scheduler.

    Waits for running jobs to complete before shutting down.
    Safe to call even if scheduler is not initialized.
    """
    global _scheduler

    if _scheduler is None:
        logger.debug("Scheduler not initialized, nothing to shutdown")
        return

    logger.info("Shutting down exchange rate scheduler...")

    try:
        # Graceful shutdown - wait for running jobs to complete
        _scheduler.shutdown(wait=True)
        logger.info("Exchange rate scheduler stopped")
    except Exception as e:
        logger.error(f"Error during scheduler shutdown: {e}")
    finally:
        _scheduler = None


def add_custom_job(
    func,
    trigger,
    job_id: str,
    name: Optional[str] = None,
    replace_existing: bool = True,
) -> None:
    """
    Add a custom job to the scheduler.

    Useful for adding additional scheduled tasks beyond exchange rate updates.

    Args:
        func: The async function to run.
        trigger: APScheduler trigger (CronTrigger, IntervalTrigger, etc.)
        job_id: Unique job identifier.
        name: Human-readable job name.
        replace_existing: If True, replace existing job with same ID.

    Raises:
        RuntimeError: If scheduler is not initialized.
    """
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")

    _scheduler.add_job(
        func,
        trigger=trigger,
        id=job_id,
        name=name or job_id,
        replace_existing=replace_existing,
    )
    logger.info(f"Added custom job: {name or job_id}")


def get_scheduler_status() -> dict:
    """
    Get current scheduler status and job information.

    Returns:
        Dict with scheduler status and list of configured jobs.
    """
    if _scheduler is None:
        return {
            "status": "not_initialized",
            "running": False,
            "jobs": [],
        }

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {
        "status": "running" if _scheduler.running else "stopped",
        "running": _scheduler.running,
        "jobs": jobs,
    }
