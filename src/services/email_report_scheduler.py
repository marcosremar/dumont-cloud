"""
Email Report Scheduler using APScheduler.

Schedules and executes weekly email reports for users with APScheduler's
BackgroundScheduler and CronTrigger for precise timing.

Features:
- Weekly email reports every Monday at 8:00 AM UTC
- Configurable via environment variables
- SQLAlchemy job store for persistence across restarts
- Batch processing with rate limiting and concurrency control
- Thread-pool based concurrent email sending within batches
- Integration with existing email services
"""

import os
import logging
import threading
from concurrent.futures import ThreadPoolExecutor as ConcurrentThreadPoolExecutor
from concurrent.futures import as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from src.config.database import SessionLocal, DATABASE_URL
from src.models.email_preferences import EmailPreference
from src.services.email_sender import send_weekly_report, get_email_sender
from src.services.email_composer import compose_weekly_report
from src.services.email_analytics_aggregator import aggregate_user_usage
from src.services.email_recommendations import generate_recommendations

logger = logging.getLogger(__name__)

# Configuration from environment variables
EMAIL_SEND_HOUR = int(os.getenv('EMAIL_SEND_HOUR', '8'))
EMAIL_SEND_MINUTE = int(os.getenv('EMAIL_SEND_MINUTE', '0'))
EMAIL_SEND_DAY = os.getenv('EMAIL_SEND_DAY', 'mon')  # Monday
EMAIL_TIMEZONE = os.getenv('EMAIL_TIMEZONE', 'UTC')
ENABLE_EMAIL_REPORTS = os.getenv('ENABLE_EMAIL_REPORTS', 'true').lower() == 'true'

# Batch processing configuration
BATCH_SIZE = int(os.getenv('EMAIL_BATCH_SIZE', '50'))
BATCH_DELAY_SECONDS = float(os.getenv('EMAIL_BATCH_DELAY', '1.0'))  # Delay between batches
MAX_CONCURRENT_SENDS = int(os.getenv('EMAIL_MAX_CONCURRENT', '10'))  # Concurrent sends per batch


@dataclass
class BatchStatistics:
    """Statistics for a batch email send operation."""

    sent: int = 0
    failed: int = 0
    skipped: int = 0
    total_users: int = 0
    batches_processed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Calculate total duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        total = self.sent + self.failed
        if total == 0:
            return 100.0
        return (self.sent / total) * 100

    @property
    def emails_per_second(self) -> float:
        """Calculate throughput in emails per second."""
        if self.duration_seconds <= 0:
            return 0.0
        return (self.sent + self.failed) / self.duration_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'sent': self.sent,
            'failed': self.failed,
            'skipped': self.skipped,
            'total_users': self.total_users,
            'batches_processed': self.batches_processed,
            'duration_seconds': self.duration_seconds,
            'success_rate': round(self.success_rate, 1),
            'emails_per_second': round(self.emails_per_second, 2),
            'errors': self.errors[:10],  # Limit errors to first 10
        }


@dataclass
class UserEmailTask:
    """Represents a single user email send task."""

    user_pref: EmailPreference
    user_id: str
    user_email: str

    @classmethod
    def from_preference(cls, pref: EmailPreference) -> 'UserEmailTask':
        """Create task from EmailPreference object."""
        return cls(
            user_pref=pref,
            user_id=pref.user_id,
            user_email=pref.email,
        )


class EmailReportScheduler:
    """
    Weekly email report scheduler using APScheduler.

    Manages the scheduling and execution of weekly GPU usage report emails.
    Uses APScheduler's BackgroundScheduler with a CronTrigger to run every
    Monday at a configurable time.
    """

    def __init__(
        self,
        send_hour: int = EMAIL_SEND_HOUR,
        send_minute: int = EMAIL_SEND_MINUTE,
        send_day: str = EMAIL_SEND_DAY,
        timezone: str = EMAIL_TIMEZONE,
        use_jobstore: bool = True,
    ):
        """
        Initialize the email report scheduler.

        Args:
            send_hour: Hour to send emails (0-23, default: 8)
            send_minute: Minute to send emails (0-59, default: 0)
            send_day: Day of week to send ('mon', 'tue', etc., default: 'mon')
            timezone: Timezone for scheduling (default: 'UTC')
            use_jobstore: Whether to use SQLAlchemy job store for persistence
        """
        self.send_hour = send_hour
        self.send_minute = send_minute
        self.send_day = send_day
        self.timezone = timezone
        self.scheduler = None
        self.running = False

        # Configure job stores
        jobstores = {}
        if use_jobstore:
            try:
                jobstores['default'] = SQLAlchemyJobStore(url=DATABASE_URL)
                logger.info("APScheduler configured with SQLAlchemy job store")
            except Exception as e:
                logger.warning(f"Failed to configure SQLAlchemy job store: {e}")
                logger.info("Using in-memory job store instead")

        # Configure executors
        executors = {
            'default': ThreadPoolExecutor(max_workers=3)
        }

        # Configure scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            timezone=ZoneInfo(timezone),
        )

        logger.info(
            f"EmailReportScheduler initialized: "
            f"send_day={send_day}, send_hour={send_hour}:{send_minute:02d}, "
            f"timezone={timezone}"
        )

    def start(self):
        """Start the scheduler and add the weekly email job."""
        if not ENABLE_EMAIL_REPORTS:
            logger.warning("Email reports disabled (ENABLE_EMAIL_REPORTS=false)")
            return

        if self.running:
            logger.warning("EmailReportScheduler already running")
            return

        try:
            # Create cron trigger for weekly emails
            trigger = CronTrigger(
                day_of_week=self.send_day,
                hour=self.send_hour,
                minute=self.send_minute,
                timezone=ZoneInfo(self.timezone),
            )

            # Add the job (replace if exists)
            self.scheduler.add_job(
                func=self._send_weekly_reports,
                trigger=trigger,
                id='weekly_email_reports',
                name='Weekly GPU Usage Email Reports',
                replace_existing=True,
                misfire_grace_time=3600,  # Allow 1 hour grace time
            )

            # Start the scheduler
            self.scheduler.start()
            self.running = True

            # Log next run time
            job = self.scheduler.get_job('weekly_email_reports')
            if job and job.next_run_time:
                logger.info(
                    f"APScheduler initialized with weekly_email_reports job "
                    f"scheduled for Mondays at {self.send_hour:02d}:{self.send_minute:02d} {self.timezone}"
                )
                logger.info(f"Next scheduled run: {job.next_run_time}")
            else:
                logger.info("APScheduler started, job scheduled")

        except Exception as e:
            logger.error(f"Failed to start EmailReportScheduler: {e}", exc_info=True)
            raise

    def stop(self):
        """Stop the scheduler gracefully."""
        if not self.running:
            return

        logger.info("Stopping EmailReportScheduler...")

        try:
            self.scheduler.shutdown(wait=False)
            self.running = False
            logger.info("EmailReportScheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")

    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self.running and self.scheduler.running

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the scheduler.

        Returns:
            Dictionary with scheduler status information
        """
        status = {
            'enabled': ENABLE_EMAIL_REPORTS,
            'running': self.is_running(),
            'timezone': self.timezone,
            'schedule': f'{self.send_day} {self.send_hour:02d}:{self.send_minute:02d}',
            'batch_config': {
                'batch_size': BATCH_SIZE,
                'max_concurrent': MAX_CONCURRENT_SENDS,
                'delay_seconds': BATCH_DELAY_SECONDS,
            },
        }

        if self.scheduler:
            job = self.scheduler.get_job('weekly_email_reports')
            if job:
                status['next_run'] = job.next_run_time.isoformat() if job.next_run_time else None
                status['job_id'] = job.id
                status['job_name'] = job.name

        return status

    def trigger_now(self) -> Dict[str, Any]:
        """
        Trigger the weekly email job immediately (for testing).

        Returns:
            Dictionary with execution results
        """
        logger.info("Manual trigger: sending weekly reports now")
        return self._send_weekly_reports()

    def trigger_test_batch(
        self,
        limit: int = 5,
        user_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Trigger a test batch send with limited users (for testing).

        This method allows testing the batch sending logic without
        sending emails to all eligible users. Useful for verifying
        concurrency control and batch processing work correctly.

        Args:
            limit: Maximum number of users to send to (default: 5)
            user_ids: Optional list of specific user IDs to send to.
                     If provided, limit is ignored.

        Returns:
            Dictionary with execution results including batch statistics
        """
        start_time = datetime.utcnow()
        logger.info("=" * 60)
        logger.info(f"Starting TEST batch email send - {start_time}")
        logger.info(f"  Limit: {limit}, User IDs: {user_ids}")
        logger.info("=" * 60)

        # Check if email sender is configured
        sender = get_email_sender()
        if not sender.is_configured():
            logger.error("Email sender not configured - RESEND_API_KEY missing")
            return {'error': 'Email sender not configured', 'sent': 0, 'failed': 0}

        db = SessionLocal()
        try:
            # Query eligible users with optional filters
            query = db.query(EmailPreference).filter(
                EmailPreference.frequency == 'weekly',
                EmailPreference.unsubscribed == False,
            )

            if user_ids:
                query = query.filter(EmailPreference.user_id.in_(user_ids))
                eligible_users = query.all()
            else:
                eligible_users = query.limit(limit).all()

            logger.info(f"Test batch: Found {len(eligible_users)} users to process")

            if not eligible_users:
                return {
                    'sent': 0,
                    'failed': 0,
                    'skipped': 0,
                    'duration_seconds': 0,
                    'test_mode': True,
                }

            # Process the test batch
            results = self._process_users_batch(db, eligible_users)
            results['test_mode'] = True

            duration = (datetime.utcnow() - start_time).total_seconds()
            results['duration_seconds'] = duration

            logger.info(
                f"Test batch complete: "
                f"sent={results['sent']}, failed={results['failed']}, "
                f"skipped={results['skipped']}, duration={duration:.1f}s"
            )

            return results

        except Exception as e:
            logger.error(f"Error in test batch send: {e}", exc_info=True)
            return {'error': str(e), 'sent': 0, 'failed': 0, 'test_mode': True}
        finally:
            db.close()

    def get_batch_config(self) -> Dict[str, Any]:
        """
        Get current batch processing configuration.

        Returns:
            Dictionary with batch configuration parameters
        """
        return {
            'batch_size': BATCH_SIZE,
            'max_concurrent_sends': MAX_CONCURRENT_SENDS,
            'batch_delay_seconds': BATCH_DELAY_SECONDS,
            'skip_zero_usage': os.getenv('EMAIL_SKIP_ZERO_USAGE', 'true').lower() == 'true',
        }

    def _send_weekly_reports(self) -> Dict[str, Any]:
        """
        Send weekly reports to all eligible users.

        This is the main job function called by APScheduler.

        Returns:
            Dictionary with send statistics
        """
        start_time = datetime.utcnow()
        logger.info("=" * 60)
        logger.info(f"Starting weekly email report send - {start_time}")
        logger.info("=" * 60)

        # Check if email sender is configured
        sender = get_email_sender()
        if not sender.is_configured():
            logger.error("Email sender not configured - RESEND_API_KEY missing")
            return {'error': 'Email sender not configured', 'sent': 0, 'failed': 0}

        # Get eligible users
        db = SessionLocal()
        try:
            eligible_users = self._get_eligible_users(db)
            logger.info(f"Found {len(eligible_users)} eligible users for weekly reports")

            if not eligible_users:
                logger.info("No eligible users found, skipping send")
                return {'sent': 0, 'failed': 0, 'skipped': 0, 'duration_seconds': 0}

            # Process users in batches
            results = self._process_users_batch(db, eligible_users)

            duration = (datetime.utcnow() - start_time).total_seconds()
            results['duration_seconds'] = duration

            logger.info(
                f"Weekly email send complete: "
                f"sent={results['sent']}, failed={results['failed']}, "
                f"skipped={results['skipped']}, duration={duration:.1f}s"
            )

            return results

        except Exception as e:
            logger.error(f"Error in weekly email send: {e}", exc_info=True)
            return {'error': str(e), 'sent': 0, 'failed': 0}
        finally:
            db.close()

    def _get_eligible_users(self, db) -> List[EmailPreference]:
        """
        Get users eligible for weekly email reports.

        Args:
            db: Database session

        Returns:
            List of EmailPreference objects for eligible users
        """
        try:
            users = db.query(EmailPreference).filter(
                EmailPreference.frequency == 'weekly',
                EmailPreference.unsubscribed == False,
            ).all()
            return users
        except Exception as e:
            logger.error(f"Error querying eligible users: {e}")
            return []

    def _process_users_batch(
        self,
        db,
        users: List[EmailPreference]
    ) -> Dict[str, Any]:
        """
        Process users in batches with concurrency control.

        Uses ThreadPoolExecutor to send emails concurrently within each batch,
        with configurable concurrency limits and rate limiting between batches.

        Args:
            db: Database session
            users: List of eligible users

        Returns:
            Dictionary with send statistics including throughput metrics
        """
        import time

        stats = BatchStatistics(
            total_users=len(users),
            start_time=datetime.utcnow(),
        )

        # Create thread-local storage for database sessions
        # Each thread needs its own session for thread-safety
        thread_local = threading.local()

        def get_thread_session():
            """Get or create a database session for the current thread."""
            if not hasattr(thread_local, 'session'):
                thread_local.session = SessionLocal()
            return thread_local.session

        def close_thread_session():
            """Close the database session for the current thread if it exists."""
            if hasattr(thread_local, 'session'):
                try:
                    thread_local.session.close()
                except Exception:
                    pass

        def send_email_task(task: UserEmailTask) -> Dict[str, Any]:
            """
            Send email for a single user task.

            This function runs in a thread pool worker and uses
            a thread-local database session.

            Args:
                task: UserEmailTask with user info

            Returns:
                Dictionary with result status
            """
            thread_session = get_thread_session()

            try:
                # Re-fetch preference to check current unsubscribed status
                user_pref = thread_session.query(EmailPreference).filter(
                    EmailPreference.user_id == task.user_id
                ).first()

                if user_pref is None:
                    return {
                        'status': 'skipped',
                        'user_id': task.user_id,
                        'reason': 'User preference not found',
                    }

                if user_pref.unsubscribed:
                    return {
                        'status': 'skipped',
                        'user_id': task.user_id,
                        'reason': 'User unsubscribed',
                    }

                # Send email to user
                success = self._send_user_report(thread_session, user_pref)

                return {
                    'status': 'sent' if success else 'failed',
                    'user_id': task.user_id,
                    'email': task.user_email,
                }

            except Exception as e:
                logger.error(f"Error sending email to {task.user_email}: {e}")
                return {
                    'status': 'failed',
                    'user_id': task.user_id,
                    'email': task.user_email,
                    'error': str(e),
                }

        # Process users in batches
        total_batches = (len(users) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_num in range(total_batches):
            batch_start = batch_num * BATCH_SIZE
            batch_end = min(batch_start + BATCH_SIZE, len(users))
            batch_users = users[batch_start:batch_end]

            logger.info(
                f"Processing batch {batch_num + 1}/{total_batches} "
                f"({len(batch_users)} users, concurrent={MAX_CONCURRENT_SENDS})"
            )

            # Create tasks for this batch
            tasks = [UserEmailTask.from_preference(pref) for pref in batch_users]

            # Process batch concurrently using ThreadPoolExecutor
            with ConcurrentThreadPoolExecutor(max_workers=MAX_CONCURRENT_SENDS) as executor:
                # Submit all tasks for concurrent execution
                future_to_task = {
                    executor.submit(send_email_task, task): task
                    for task in tasks
                }

                # Collect results as they complete
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        status = result.get('status', 'failed')

                        if status == 'sent':
                            stats.sent += 1
                        elif status == 'skipped':
                            stats.skipped += 1
                            logger.info(
                                f"Skipped {task.user_email}: "
                                f"{result.get('reason', 'unknown')}"
                            )
                        else:
                            stats.failed += 1
                            if 'error' in result:
                                stats.errors.append({
                                    'user_id': task.user_id,
                                    'email': task.user_email,
                                    'error': result['error'],
                                })

                    except Exception as e:
                        logger.error(
                            f"Task exception for {task.user_email}: {e}"
                        )
                        stats.failed += 1
                        stats.errors.append({
                            'user_id': task.user_id,
                            'email': task.user_email,
                            'error': str(e),
                        })

            stats.batches_processed += 1

            # Rate limiting delay between batches (not after last batch)
            if batch_num < total_batches - 1:
                logger.info(
                    f"Batch {batch_num + 1} complete: "
                    f"sent={stats.sent}, failed={stats.failed}, skipped={stats.skipped}. "
                    f"Pausing {BATCH_DELAY_SECONDS}s for rate limit..."
                )
                time.sleep(BATCH_DELAY_SECONDS)

        # Clean up thread-local sessions
        close_thread_session()

        stats.end_time = datetime.utcnow()

        logger.info(
            f"Batch processing complete: {stats.batches_processed} batches, "
            f"{stats.emails_per_second:.2f} emails/sec"
        )

        return stats.to_dict()

    def _send_user_report(self, db, user_pref: EmailPreference) -> bool:
        """
        Send a weekly report to a single user.

        Args:
            db: Database session
            user_pref: User's email preferences

        Returns:
            True if sent successfully, False otherwise
        """
        user_id = user_pref.user_id
        user_email = user_pref.email

        logger.info(f"Sending weekly report to {user_email} (user_id={user_id})")

        try:
            # Aggregate user analytics
            analytics_data = aggregate_user_usage(db, user_id)

            # Check if user has any usage
            current_week = analytics_data.get('current_week', {})
            has_usage = current_week.get('has_usage', False)

            if not has_usage:
                # Skip users with zero usage (configurable behavior)
                skip_zero_usage = os.getenv('EMAIL_SKIP_ZERO_USAGE', 'true').lower() == 'true'
                if skip_zero_usage:
                    logger.info(f"Skipping {user_email} - no GPU usage this week")
                    return True  # Consider skipped as success (not a failure)

            # Generate recommendations
            recommendations = generate_recommendations(
                current_week=current_week,
                previous_week=analytics_data.get('previous_week', {}),
                week_over_week=analytics_data.get('week_over_week', {}),
                gpu_breakdown=analytics_data.get('gpu_breakdown', [])
            )

            # Extract user name (if available)
            user_name = None  # Could be fetched from user profile if available

            # Compose the email
            email_content = compose_weekly_report(
                user_id=user_id,
                user_email=user_email,
                user_name=user_name,
                analytics_data=analytics_data,
                recommendations=recommendations,
            )

            # Send with logging
            result = send_weekly_report(
                db_session=db,
                user_id=user_id,
                to=user_email,
                subject=email_content.subject,
                html=email_content.html_body,
                week_start=email_content.week_start,
                week_end=email_content.week_end,
            )

            if result.success:
                logger.info(f"Successfully sent report to {user_email}, email_id={result.email_id}")
                return True
            else:
                logger.error(f"Failed to send report to {user_email}: {result.error}")
                return False

        except Exception as e:
            logger.error(f"Error sending report to {user_email}: {e}", exc_info=True)
            return False


# Singleton instance for convenience
_scheduler: Optional[EmailReportScheduler] = None


def get_email_scheduler() -> EmailReportScheduler:
    """
    Get the default email scheduler singleton.

    Returns:
        EmailReportScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = EmailReportScheduler()
    return _scheduler


def init_email_scheduler() -> Optional[EmailReportScheduler]:
    """
    Initialize and start the email scheduler.

    This is the main entry point for starting the email scheduler service.
    Should be called during application startup.

    Returns:
        EmailReportScheduler instance if enabled, None otherwise
    """
    if not ENABLE_EMAIL_REPORTS:
        logger.info("Email reports disabled - not starting scheduler")
        return None

    try:
        scheduler = get_email_scheduler()
        scheduler.start()
        return scheduler
    except Exception as e:
        logger.error(f"Failed to initialize email scheduler: {e}", exc_info=True)
        return None


def shutdown_email_scheduler():
    """
    Shutdown the email scheduler.

    Should be called during application shutdown.
    """
    global _scheduler
    if _scheduler is not None:
        _scheduler.stop()
        _scheduler = None
        logger.info("Email scheduler shutdown complete")
