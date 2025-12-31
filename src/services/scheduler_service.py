"""
Scheduler Service - Background Job Management for GPU Reservation System

Manages scheduled tasks using APScheduler including:
- Daily credit expiration at midnight UTC
- Upcoming reservation allocation checks
- Reservation completion handling
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Callable, List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)


# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> Optional[BackgroundScheduler]:
    """Get the global scheduler instance."""
    return _scheduler


def init_scheduler(
    start: bool = False,
    timezone: str = "UTC"
) -> BackgroundScheduler:
    """
    Initialize the APScheduler BackgroundScheduler.

    Creates a scheduler with:
    - Memory-based job store (suitable for single-process apps)
    - Thread pool executor for job execution
    - UTC timezone by default

    Args:
        start: If True, starts the scheduler immediately
        timezone: Timezone for job scheduling (default: UTC)

    Returns:
        Configured BackgroundScheduler instance
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already initialized, returning existing instance")
        return _scheduler

    # Configure job stores
    jobstores = {
        'default': MemoryJobStore()
    }

    # Configure executors
    executors = {
        'default': ThreadPoolExecutor(max_workers=3)
    }

    # Job defaults
    job_defaults = {
        'coalesce': True,  # Combine missed runs into one
        'max_instances': 1,  # Only one instance of each job running at a time
        'misfire_grace_time': 60 * 60  # 1 hour grace period for misfires
    }

    _scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone=timezone
    )

    logger.info(f"Scheduler initialized with timezone={timezone}")

    if start:
        start_scheduler()

    return _scheduler


def start_scheduler() -> None:
    """Start the scheduler if not already running."""
    global _scheduler

    if _scheduler is None:
        logger.warning("Scheduler not initialized, initializing now")
        init_scheduler()

    if not _scheduler.running:
        _scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.debug("Scheduler already running")


def stop_scheduler(wait: bool = True) -> None:
    """
    Stop the scheduler gracefully.

    Args:
        wait: If True, waits for running jobs to complete
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=wait)
        logger.info("Scheduler stopped")


def add_credit_expiration_job(
    db_session_factory: Callable,
    hour: int = 0,
    minute: int = 0
) -> str:
    """
    Schedule the daily credit expiration job.

    Runs at midnight UTC by default to expire credits
    that have passed their 30-day expiration date.

    Args:
        db_session_factory: Callable that returns a database session
        hour: Hour to run (0-23, default: 0 for midnight)
        minute: Minute to run (0-59, default: 0)

    Returns:
        Job ID
    """
    global _scheduler

    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")

    job_id = "credit_expiration_daily"

    # Remove existing job if present
    existing = _scheduler.get_job(job_id)
    if existing:
        _scheduler.remove_job(job_id)
        logger.info(f"Removed existing job: {job_id}")

    # Add job with cron trigger
    _scheduler.add_job(
        func=_run_credit_expiration,
        trigger=CronTrigger(hour=hour, minute=minute, timezone="UTC"),
        id=job_id,
        name="Daily Credit Expiration",
        kwargs={"db_session_factory": db_session_factory},
        replace_existing=True
    )

    logger.info(
        f"Credit expiration job scheduled: runs daily at {hour:02d}:{minute:02d} UTC"
    )

    return job_id


def add_reservation_allocation_job(
    db_session_factory: Callable,
    allocation_callback: Callable,
    interval_minutes: int = 5
) -> str:
    """
    Schedule job to check and allocate upcoming reservations.

    Runs every N minutes to find reservations starting soon
    and trigger GPU allocation.

    Args:
        db_session_factory: Callable that returns a database session
        allocation_callback: Function to call for GPU allocation
        interval_minutes: Check interval in minutes (default: 5)

    Returns:
        Job ID
    """
    global _scheduler

    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")

    job_id = "reservation_allocation_check"

    # Remove existing job if present
    existing = _scheduler.get_job(job_id)
    if existing:
        _scheduler.remove_job(job_id)

    # Add job with interval trigger
    _scheduler.add_job(
        func=_run_reservation_allocation_check,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id=job_id,
        name="Reservation Allocation Check",
        kwargs={
            "db_session_factory": db_session_factory,
            "allocation_callback": allocation_callback
        },
        replace_existing=True
    )

    logger.info(
        f"Reservation allocation job scheduled: runs every {interval_minutes} minutes"
    )

    return job_id


def add_reservation_completion_job(
    db_session_factory: Callable,
    interval_minutes: int = 5
) -> str:
    """
    Schedule job to complete ended reservations.

    Runs every N minutes to find active reservations that
    have passed their end time and mark them as completed.

    Args:
        db_session_factory: Callable that returns a database session
        interval_minutes: Check interval in minutes (default: 5)

    Returns:
        Job ID
    """
    global _scheduler

    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")

    job_id = "reservation_completion_check"

    # Remove existing job if present
    existing = _scheduler.get_job(job_id)
    if existing:
        _scheduler.remove_job(job_id)

    # Add job with interval trigger
    _scheduler.add_job(
        func=_run_reservation_completion_check,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id=job_id,
        name="Reservation Completion Check",
        kwargs={"db_session_factory": db_session_factory},
        replace_existing=True
    )

    logger.info(
        f"Reservation completion job scheduled: runs every {interval_minutes} minutes"
    )

    return job_id


def get_jobs() -> List[dict]:
    """
    Get all scheduled jobs.

    Returns:
        List of job information dictionaries
    """
    global _scheduler

    if _scheduler is None:
        return []

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })

    return jobs


def trigger_job(job_id: str) -> bool:
    """
    Manually trigger a job immediately.

    Args:
        job_id: ID of the job to trigger

    Returns:
        True if job was triggered, False if not found
    """
    global _scheduler

    if _scheduler is None:
        return False

    job = _scheduler.get_job(job_id)
    if job:
        job.modify(next_run_time=datetime.now())
        logger.info(f"Manually triggered job: {job_id}")
        return True

    return False


def _run_credit_expiration(db_session_factory: Callable) -> int:
    """
    Internal function to run credit expiration.

    Args:
        db_session_factory: Callable that returns a database session

    Returns:
        Number of credits expired
    """
    logger.info("Running credit expiration job")

    try:
        from src.services.reservation_service import ReservationService

        db = db_session_factory()
        try:
            service = ReservationService(db)
            expired_count = service.expire_credits()
            logger.info(f"Credit expiration completed: {expired_count} credits expired")
            return expired_count
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Credit expiration job failed: {e}", exc_info=True)
        return 0


def _run_reservation_allocation_check(
    db_session_factory: Callable,
    allocation_callback: Callable
) -> int:
    """
    Internal function to check and allocate upcoming reservations.

    Args:
        db_session_factory: Callable that returns a database session
        allocation_callback: Function to call for each reservation needing allocation

    Returns:
        Number of reservations processed
    """
    logger.info("Running reservation allocation check")

    try:
        from src.services.reservation_service import ReservationService

        db = db_session_factory()
        try:
            service = ReservationService(db)
            # Get reservations starting in next 15 minutes
            upcoming = service.get_upcoming_reservations(minutes_ahead=15)

            processed = 0
            for reservation in upcoming:
                try:
                    allocation_callback(reservation)
                    processed += 1
                except Exception as e:
                    logger.error(
                        f"Failed to allocate reservation {reservation.id}: {e}"
                    )

            if processed > 0:
                logger.info(f"Allocation check completed: {processed} reservations processed")

            return processed
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Reservation allocation job failed: {e}", exc_info=True)
        return 0


def _run_reservation_completion_check(db_session_factory: Callable) -> int:
    """
    Internal function to complete ended reservations.

    Args:
        db_session_factory: Callable that returns a database session

    Returns:
        Number of reservations completed
    """
    logger.info("Running reservation completion check")

    try:
        from src.services.reservation_service import ReservationService
        from src.models.reservation import Reservation, ReservationStatus

        db = db_session_factory()
        try:
            now = datetime.utcnow()

            # Find active reservations that have ended
            ended_reservations = db.query(Reservation).filter(
                Reservation.status == ReservationStatus.ACTIVE,
                Reservation.end_time <= now
            ).all()

            service = ReservationService(db)
            completed = 0

            for reservation in ended_reservations:
                try:
                    service.complete_reservation(reservation.id)
                    completed += 1
                except Exception as e:
                    logger.error(
                        f"Failed to complete reservation {reservation.id}: {e}"
                    )

            if completed > 0:
                logger.info(f"Completion check completed: {completed} reservations completed")

            return completed
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Reservation completion job failed: {e}", exc_info=True)
        return 0


def setup_reservation_jobs(db_session_factory: Callable) -> None:
    """
    Set up all reservation-related scheduled jobs.

    This is a convenience function that sets up:
    - Daily credit expiration at midnight UTC
    - Reservation completion check every 5 minutes

    Args:
        db_session_factory: Callable that returns a database session
    """
    add_credit_expiration_job(db_session_factory)
    add_reservation_completion_job(db_session_factory)
    logger.info("All reservation scheduler jobs configured")
