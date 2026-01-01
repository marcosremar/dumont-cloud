"""
Email Report Scheduler using APScheduler.

Schedules and executes weekly email reports for users with APScheduler's
BackgroundScheduler and CronTrigger for precise timing.

Features:
- Weekly email reports every Monday at 8:00 AM UTC
- Configurable via environment variables
- SQLAlchemy job store for persistence across restarts
- Batch processing with rate limiting
- Integration with existing email services
"""

import os
import logging
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
BATCH_SIZE = 50
BATCH_DELAY_SECONDS = 1.0  # Delay between batches for rate limiting


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
    ) -> Dict[str, int]:
        """
        Process users in batches to respect rate limits.

        Args:
            db: Database session
            users: List of eligible users

        Returns:
            Dictionary with send statistics
        """
        import time

        sent = 0
        failed = 0
        skipped = 0

        for i, user_pref in enumerate(users):
            try:
                # Check unsubscribed flag immediately before sending
                db.refresh(user_pref)
                if user_pref.unsubscribed:
                    logger.info(f"User {user_pref.user_id} unsubscribed, skipping")
                    skipped += 1
                    continue

                # Send email to user
                success = self._send_user_report(db, user_pref)
                if success:
                    sent += 1
                else:
                    failed += 1

                # Rate limiting between batches
                if (i + 1) % BATCH_SIZE == 0:
                    logger.info(f"Processed {i + 1}/{len(users)} users, pausing for rate limit...")
                    time.sleep(BATCH_DELAY_SECONDS)

            except Exception as e:
                logger.error(f"Error processing user {user_pref.user_id}: {e}")
                failed += 1

        return {'sent': sent, 'failed': failed, 'skipped': skipped}

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
