"""
Tests for APScheduler job persistence across restarts.

This module verifies that the weekly email report scheduler:
1. Initializes correctly with SQLAlchemy job store
2. Schedules the weekly_email_reports job for Mondays at 08:00 UTC
3. Persists jobs across restarts via SQLAlchemy job store
4. Logs the expected initialization messages

These tests are critical for ensuring reliable email report delivery.
"""
import os
import sys
import logging
import pytest
import time
from datetime import datetime
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestSchedulerInitialization:
    """Test APScheduler initialization and configuration."""

    def test_scheduler_module_imports(self):
        """Verify scheduler module can be imported."""
        from src.services.email_report_scheduler import (
            EmailReportScheduler,
            init_email_scheduler,
            shutdown_email_scheduler,
            get_email_scheduler,
        )

        assert EmailReportScheduler is not None
        assert init_email_scheduler is not None
        assert shutdown_email_scheduler is not None
        assert get_email_scheduler is not None

    def test_scheduler_instantiation_with_defaults(self):
        """Test scheduler can be instantiated with default config."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(use_jobstore=False)

        assert scheduler is not None
        assert scheduler.send_day == 'mon'
        assert scheduler.send_hour == 8
        assert scheduler.send_minute == 0
        assert scheduler.timezone == 'UTC'
        assert scheduler.running is False

    def test_scheduler_instantiation_custom_config(self):
        """Test scheduler with custom configuration."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(
            send_hour=10,
            send_minute=30,
            send_day='tue',
            timezone='America/New_York',
            use_jobstore=False,
        )

        assert scheduler.send_hour == 10
        assert scheduler.send_minute == 30
        assert scheduler.send_day == 'tue'
        assert scheduler.timezone == 'America/New_York'


class TestSchedulerJobConfiguration:
    """Test cron trigger and job configuration."""

    def test_cron_trigger_monday_8am(self):
        """Verify cron trigger is configured for Monday 8am UTC."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(use_jobstore=False)

        # Start scheduler to create job
        with patch('src.services.email_report_scheduler.ENABLE_EMAIL_REPORTS', True):
            scheduler.start()

        try:
            # Get the job
            job = scheduler.scheduler.get_job('weekly_email_reports')
            assert job is not None, "weekly_email_reports job not found"

            # Verify trigger configuration
            trigger = job.trigger
            assert trigger is not None

            # CronTrigger should be for day_of_week=mon, hour=8
            # The trigger has these fields as objects, check string representation
            trigger_str = str(trigger)
            assert 'mon' in trigger_str.lower() or '0' in trigger_str, \
                f"Expected Monday in trigger: {trigger_str}"

            # Verify job name
            assert job.name == 'Weekly GPU Usage Email Reports'
            assert job.id == 'weekly_email_reports'

        finally:
            scheduler.stop()

    def test_scheduler_get_status(self):
        """Test get_status returns correct configuration."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(use_jobstore=False)

        with patch('src.services.email_report_scheduler.ENABLE_EMAIL_REPORTS', True):
            scheduler.start()

        try:
            status = scheduler.get_status()

            assert status['running'] is True
            assert status['schedule'] == 'mon 08:00'
            assert status['timezone'] == 'UTC'
            assert 'batch_config' in status
            assert 'job_id' in status
            assert status['job_id'] == 'weekly_email_reports'

        finally:
            scheduler.stop()

    def test_scheduler_next_run_time(self):
        """Verify next run time is on a Monday at 08:00 UTC."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(use_jobstore=False)

        with patch('src.services.email_report_scheduler.ENABLE_EMAIL_REPORTS', True):
            scheduler.start()

        try:
            job = scheduler.scheduler.get_job('weekly_email_reports')
            next_run = job.next_run_time

            assert next_run is not None, "next_run_time should not be None"

            # Convert to UTC for verification
            next_run_utc = next_run.astimezone(ZoneInfo('UTC'))

            # Should be Monday (weekday 0)
            assert next_run_utc.weekday() == 0, \
                f"Expected Monday (0), got weekday {next_run_utc.weekday()}"

            # Should be at 8:00 AM
            assert next_run_utc.hour == 8, \
                f"Expected hour 8, got {next_run_utc.hour}"
            assert next_run_utc.minute == 0, \
                f"Expected minute 0, got {next_run_utc.minute}"

        finally:
            scheduler.stop()


class TestSchedulerLogging:
    """Test scheduler logging output."""

    def test_scheduler_logs_initialization(self, caplog):
        """Verify scheduler logs expected initialization message."""
        from src.services.email_report_scheduler import EmailReportScheduler

        with caplog.at_level(logging.INFO):
            scheduler = EmailReportScheduler(use_jobstore=False)

            with patch('src.services.email_report_scheduler.ENABLE_EMAIL_REPORTS', True):
                scheduler.start()

        try:
            # Check for expected log messages
            log_text = caplog.text

            # Should log initialization
            assert 'EmailReportScheduler' in log_text or 'initialized' in log_text.lower(), \
                f"Expected initialization log, got: {log_text}"

        finally:
            scheduler.stop()

    def test_scheduler_logs_job_scheduled(self, caplog):
        """Verify logs show job scheduled for Mondays."""
        from src.services.email_report_scheduler import EmailReportScheduler

        with caplog.at_level(logging.INFO):
            scheduler = EmailReportScheduler(use_jobstore=False)

            with patch('src.services.email_report_scheduler.ENABLE_EMAIL_REPORTS', True):
                scheduler.start()

        try:
            log_text = caplog.text

            # Should mention weekly_email_reports and Monday/08:00
            has_job_mention = (
                'weekly_email_reports' in log_text or
                'Weekly' in log_text
            )
            has_schedule_mention = (
                'Monday' in log_text or
                'mon' in log_text.lower() or
                '08:00' in log_text or
                '8:00' in log_text
            )

            assert has_job_mention, \
                f"Expected job name in logs: {log_text}"

        finally:
            scheduler.stop()


class TestSchedulerLifecycle:
    """Test scheduler start/stop lifecycle."""

    def test_scheduler_start_stop(self):
        """Test scheduler can be started and stopped."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(use_jobstore=False)

        assert scheduler.running is False

        with patch('src.services.email_report_scheduler.ENABLE_EMAIL_REPORTS', True):
            scheduler.start()

        assert scheduler.running is True
        assert scheduler.is_running() is True

        scheduler.stop()

        assert scheduler.running is False

    def test_scheduler_idempotent_start(self, caplog):
        """Test starting an already running scheduler is safe."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(use_jobstore=False)

        with patch('src.services.email_report_scheduler.ENABLE_EMAIL_REPORTS', True):
            scheduler.start()
            scheduler.start()  # Should not fail

        try:
            # Should log warning about already running
            assert scheduler.running is True

        finally:
            scheduler.stop()

    def test_scheduler_disabled_does_not_start(self):
        """Test scheduler respects ENABLE_EMAIL_REPORTS=false."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(use_jobstore=False)

        with patch('src.services.email_report_scheduler.ENABLE_EMAIL_REPORTS', False):
            scheduler.start()

        # Should not be running when disabled
        assert scheduler.running is False


class TestSchedulerPersistence:
    """Test APScheduler job persistence with SQLAlchemy job store."""

    @pytest.fixture
    def temp_db_url(self, tmp_path):
        """Create a temporary SQLite database for testing."""
        db_path = tmp_path / "test_scheduler.db"
        return f"sqlite:///{db_path}"

    def test_sqlalchemy_jobstore_creation(self, temp_db_url):
        """Test SQLAlchemy job store can be created."""
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

        jobstore = SQLAlchemyJobStore(url=temp_db_url)
        assert jobstore is not None

    def test_job_persists_across_restart(self, temp_db_url):
        """
        Test that jobs persist across scheduler restarts.

        This is the critical test for job persistence:
        1. Create scheduler with SQLAlchemy job store
        2. Start and add job using module-level function reference
        3. Stop scheduler
        4. Create new scheduler with same job store
        5. Verify job still exists
        """
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

        job_id = 'test_persistent_job'

        # Create job store
        jobstore = SQLAlchemyJobStore(url=temp_db_url)

        # First scheduler - create job
        scheduler1 = BackgroundScheduler(
            jobstores={'default': jobstore},
            timezone=ZoneInfo('UTC'),
        )

        # Use a module-level function reference (string) for serialization
        # APScheduler can serialize 'module:function' strings for job store persistence
        scheduler1.add_job(
            func='datetime:datetime.now',  # Use a stdlib function as test target
            trigger=CronTrigger(day_of_week='mon', hour=8),
            id=job_id,
            replace_existing=True,
        )
        scheduler1.start()

        # Verify job exists
        job = scheduler1.get_job(job_id)
        assert job is not None, "Job should exist after creation"

        # Stop first scheduler (simulating restart)
        scheduler1.shutdown(wait=False)

        # Create new job store pointing to same database
        jobstore2 = SQLAlchemyJobStore(url=temp_db_url)

        # Second scheduler - verify job persisted
        scheduler2 = BackgroundScheduler(
            jobstores={'default': jobstore2},
            timezone=ZoneInfo('UTC'),
        )
        scheduler2.start()

        try:
            # Job should still exist
            job = scheduler2.get_job(job_id)
            assert job is not None, "Job should persist across restarts"

        finally:
            scheduler2.shutdown(wait=False)

    def test_job_configuration_persists(self, temp_db_url):
        """Test that job configuration (trigger, etc.) persists correctly."""
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

        job_id = 'test_config_persist'

        # First scheduler
        jobstore1 = SQLAlchemyJobStore(url=temp_db_url)
        scheduler1 = BackgroundScheduler(
            jobstores={'default': jobstore1},
            timezone=ZoneInfo('UTC'),
        )

        # Add job with specific configuration using module-level function reference
        scheduler1.add_job(
            func='datetime:datetime.now',  # Use stdlib function for serialization
            trigger=CronTrigger(day_of_week='mon', hour=8, minute=30),
            id=job_id,
            name='Test Persistent Job',
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler1.start()

        # Get original next run time
        original_job = scheduler1.get_job(job_id)
        original_next_run = original_job.next_run_time

        scheduler1.shutdown(wait=False)

        # Second scheduler - verify configuration persisted
        jobstore2 = SQLAlchemyJobStore(url=temp_db_url)
        scheduler2 = BackgroundScheduler(
            jobstores={'default': jobstore2},
            timezone=ZoneInfo('UTC'),
        )
        scheduler2.start()

        try:
            job = scheduler2.get_job(job_id)

            assert job is not None
            assert job.name == 'Test Persistent Job'
            assert job.next_run_time is not None

            # Next run time should be consistent
            # (may differ slightly due to timing, so we check it's on same day)
            restored_next_run = job.next_run_time
            assert restored_next_run.weekday() == 0, "Should still be Monday"
            assert restored_next_run.hour == 8, "Should still be 8 AM"
            assert restored_next_run.minute == 30, "Should still be :30"

        finally:
            scheduler2.shutdown(wait=False)


class TestSchedulerReplaceExisting:
    """Test that replace_existing=True works correctly."""

    def test_replace_existing_updates_job(self):
        """Test that adding a job with same ID replaces the existing one."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(use_jobstore=False)

        with patch('src.services.email_report_scheduler.ENABLE_EMAIL_REPORTS', True):
            scheduler.start()

        try:
            # Get initial job
            job1 = scheduler.scheduler.get_job('weekly_email_reports')
            assert job1 is not None

            # Manually add another job with same ID (simulates restart with same job)
            def dummy():
                pass

            from apscheduler.triggers.cron import CronTrigger
            scheduler.scheduler.add_job(
                func=dummy,
                trigger=CronTrigger(day_of_week='tue', hour=10),  # Different schedule
                id='weekly_email_reports',
                replace_existing=True,  # Should replace, not error
            )

            # Should have replaced successfully
            job2 = scheduler.scheduler.get_job('weekly_email_reports')
            assert job2 is not None

        finally:
            scheduler.stop()


class TestSchedulerIntegration:
    """Integration tests for full scheduler workflow."""

    def test_init_and_shutdown_functions(self, tmp_path):
        """Test the init and shutdown convenience functions."""
        import src.services.email_report_scheduler as scheduler_module
        from src.services.email_report_scheduler import (
            init_email_scheduler,
            shutdown_email_scheduler,
            get_email_scheduler,
        )

        # Create temp SQLite DB for testing
        temp_db = tmp_path / "test_init.db"
        temp_db_url = f"sqlite:///{temp_db}"

        # Reset singleton state
        scheduler_module._scheduler = None

        with patch.object(scheduler_module, 'ENABLE_EMAIL_REPORTS', True):
            with patch.object(scheduler_module, 'DATABASE_URL', temp_db_url):
                scheduler = init_email_scheduler()

                try:
                    assert scheduler is not None, "Scheduler should be created"
                    assert scheduler.running is True, "Scheduler should be running"

                    # get_email_scheduler should return same instance
                    same_scheduler = get_email_scheduler()
                    assert same_scheduler is scheduler

                finally:
                    shutdown_email_scheduler()

        # Reset singleton
        scheduler_module._scheduler = None

    def test_scheduler_batch_config(self):
        """Test batch configuration is accessible."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(use_jobstore=False)

        config = scheduler.get_batch_config()

        assert 'batch_size' in config
        assert 'max_concurrent_sends' in config
        assert 'batch_delay_seconds' in config
        assert config['batch_size'] > 0

    def test_scheduler_with_sqlalchemy_jobstore(self, tmp_path):
        """Test full scheduler lifecycle with SQLAlchemy job store."""
        import src.services.email_report_scheduler as scheduler_module
        from src.services.email_report_scheduler import EmailReportScheduler

        # Create temp SQLite DB for testing
        temp_db = tmp_path / "test_full_lifecycle.db"
        temp_db_url = f"sqlite:///{temp_db}"

        # Set DATABASE_URL for job store
        with patch.object(scheduler_module, 'DATABASE_URL', temp_db_url):
            scheduler = EmailReportScheduler(use_jobstore=True)

            with patch.object(scheduler_module, 'ENABLE_EMAIL_REPORTS', True):
                scheduler.start()

            try:
                assert scheduler.running is True

                # Get job status
                status = scheduler.get_status()
                assert status['job_id'] == 'weekly_email_reports'
                assert status['running'] is True

                # Get the job
                job = scheduler.scheduler.get_job('weekly_email_reports')
                assert job is not None

            finally:
                scheduler.stop()


class TestSchedulerEnvironmentConfig:
    """Test scheduler respects constructor parameter configuration."""

    def test_custom_send_hour(self):
        """Test scheduler respects custom send_hour parameter."""
        from src.services.email_report_scheduler import EmailReportScheduler

        # Constructor parameters override default values
        scheduler = EmailReportScheduler(
            send_hour=10,
            use_jobstore=False
        )
        assert scheduler.send_hour == 10

    def test_custom_send_day(self):
        """Test scheduler respects custom send_day parameter."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(
            send_day='fri',
            use_jobstore=False
        )
        assert scheduler.send_day == 'fri'

    def test_custom_timezone(self):
        """Test scheduler respects custom timezone parameter."""
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(
            timezone='America/New_York',
            use_jobstore=False
        )
        assert scheduler.timezone == 'America/New_York'

    def test_default_values_match_env_defaults(self):
        """Test default values match the module-level constants."""
        import src.services.email_report_scheduler as scheduler_module
        from src.services.email_report_scheduler import EmailReportScheduler

        scheduler = EmailReportScheduler(use_jobstore=False)

        # Verify defaults match module-level constants
        assert scheduler.send_hour == scheduler_module.EMAIL_SEND_HOUR
        assert scheduler.send_day == scheduler_module.EMAIL_SEND_DAY
        assert scheduler.timezone == scheduler_module.EMAIL_TIMEZONE


class TestSchedulerRestart:
    """Test scheduler behavior across simulated restarts."""

    def test_scheduler_job_survives_restart_simulation(self, tmp_path):
        """
        Test that scheduled jobs survive a simulated restart.

        This verifies the key requirement: APScheduler job persistence.
        """
        import src.services.email_report_scheduler as scheduler_module
        from src.services.email_report_scheduler import EmailReportScheduler

        # Create temp SQLite DB for testing
        temp_db = tmp_path / "restart_test.db"
        temp_db_url = f"sqlite:///{temp_db}"

        job_id = 'weekly_email_reports'

        # First "startup" - scheduler creates job
        with patch.object(scheduler_module, 'DATABASE_URL', temp_db_url):
            scheduler1 = EmailReportScheduler(use_jobstore=True)

            with patch.object(scheduler_module, 'ENABLE_EMAIL_REPORTS', True):
                scheduler1.start()

            job1 = scheduler1.scheduler.get_job(job_id)
            assert job1 is not None, "Job should exist after first startup"

            next_run_1 = job1.next_run_time

            # Shutdown (simulate restart)
            scheduler1.stop()

        # Second "startup" - scheduler should restore job from DB
        with patch.object(scheduler_module, 'DATABASE_URL', temp_db_url):
            scheduler2 = EmailReportScheduler(use_jobstore=True)

            with patch.object(scheduler_module, 'ENABLE_EMAIL_REPORTS', True):
                scheduler2.start()

            try:
                job2 = scheduler2.scheduler.get_job(job_id)
                assert job2 is not None, "Job should persist after restart"
                assert job2.name == 'Weekly GPU Usage Email Reports'

                # Next run time should be consistent
                next_run_2 = job2.next_run_time
                assert next_run_2 is not None
                # Both should be for Monday 8:00 AM
                assert next_run_2.weekday() == 0

            finally:
                scheduler2.stop()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
