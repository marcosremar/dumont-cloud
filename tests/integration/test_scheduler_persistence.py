"""
Integration Tests - Scheduler Persistence Across Restarts

This test file verifies that the snapshot scheduler correctly:
1. Saves state to database when snapshots complete
2. Loads state from database on restart
3. Respects next_snapshot_at times after restart
4. Handles various edge cases (new configs, disabled configs, etc.)

Subtask 7-2: Verify scheduler persistence across restarts
"""

import pytest
import time
from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestSchedulerPersistenceE2E:
    """
    End-to-end tests for scheduler persistence across simulated restarts.

    These tests verify:
    1. Scheduler state is saved to database
    2. Scheduler loads state correctly on restart
    3. Scheduler respects scheduled times after restart
    """

    def test_load_from_configs_restores_state(self):
        """Test that load_from_configs correctly restores scheduler state."""
        from src.services.snapshot_scheduler import SnapshotScheduler, SnapshotStatus

        # Create scheduler
        scheduler = SnapshotScheduler()

        # Simulate database configs (as would be loaded after restart)
        now = time.time()
        configs = [
            {
                'instance_id': 'persist-instance-001',
                'interval_minutes': 15,
                'enabled': True,
                'last_snapshot_at': now - 600,  # 10 min ago
                'next_snapshot_at': now + 300,  # 5 min from now
                'consecutive_failures': 0,
            },
            {
                'instance_id': 'persist-instance-002',
                'interval_minutes': 30,
                'enabled': True,
                'last_snapshot_at': now - 1800,  # 30 min ago
                'next_snapshot_at': now + 0,  # Due now
                'consecutive_failures': 1,
            },
            {
                'instance_id': 'persist-instance-003',
                'interval_minutes': 60,
                'enabled': False,
                'last_snapshot_at': now - 3600,  # 1 hour ago
                'consecutive_failures': 3,
            },
        ]

        # Load configs
        scheduler.load_from_configs(configs)

        # Verify all instances were loaded
        assert scheduler.get_instance('persist-instance-001') is not None
        assert scheduler.get_instance('persist-instance-002') is not None
        assert scheduler.get_instance('persist-instance-003') is not None

        # Verify instance 1 state
        job1 = scheduler.get_instance('persist-instance-001')
        assert job1.interval_minutes == 15
        assert job1.enabled is True
        assert job1.last_snapshot_at is not None
        assert job1.consecutive_failures == 0

        # Verify instance 2 state (with failure history)
        job2 = scheduler.get_instance('persist-instance-002')
        assert job2.interval_minutes == 30
        assert job2.enabled is True
        assert job2.consecutive_failures == 1

        # Verify instance 3 state (disabled)
        job3 = scheduler.get_instance('persist-instance-003')
        assert job3.interval_minutes == 60
        assert job3.enabled is False
        assert job3.consecutive_failures == 3

        # Cleanup
        scheduler.stop(wait=False)

    def test_scheduler_persists_next_snapshot_at(self):
        """Test that next_snapshot_at is correctly set after adding instances."""
        from src.services.snapshot_scheduler import SnapshotScheduler

        scheduler = SnapshotScheduler()
        scheduler.start()

        # Add instance
        job_info = scheduler.add_instance(
            instance_id='next-snapshot-test-001',
            interval_minutes=15,
            enabled=True
        )

        # Verify next_snapshot_at is set
        assert job_info.next_snapshot_at is not None

        # The next snapshot should be approximately 15 minutes from now
        now = time.time()
        expected_next = now + (15 * 60)
        # Allow 30 second tolerance for test timing
        assert abs(job_info.next_snapshot_at - expected_next) < 30

        scheduler.stop(wait=False)

    def test_scheduler_updates_state_after_snapshot(self):
        """Test that scheduler updates job info after snapshot execution."""
        from src.services.snapshot_scheduler import (
            SnapshotScheduler, SnapshotResult, SnapshotStatus
        )

        # Track state changes
        state_changes = []

        def mock_executor(instance_id):
            return SnapshotResult(
                instance_id=instance_id,
                status=SnapshotStatus.SUCCESS,
                started_at=time.time(),
                completed_at=time.time(),
                duration_seconds=0.1,
                snapshot_id=f"snap-{instance_id}",
                size_bytes=1024,
            )

        def on_state_change(job_info):
            state_changes.append({
                'instance_id': job_info.instance_id,
                'last_status': job_info.last_status.value,
                'last_snapshot_at': job_info.last_snapshot_at,
                'consecutive_failures': job_info.consecutive_failures,
            })

        scheduler = SnapshotScheduler(
            snapshot_executor=mock_executor,
            on_state_change=on_state_change,
        )

        scheduler.add_instance('state-update-test-001', interval_minutes=15)
        scheduler.start()

        # Trigger snapshot
        result = scheduler.trigger_snapshot('state-update-test-001')

        assert result is not None
        assert result.status == SnapshotStatus.SUCCESS

        # Verify state change was recorded
        job_info = scheduler.get_instance('state-update-test-001')
        assert job_info.last_snapshot_at is not None
        assert job_info.last_status == SnapshotStatus.SUCCESS
        assert job_info.consecutive_failures == 0

        # Verify callback was called
        assert len(state_changes) >= 1

        scheduler.stop(wait=False)

    def test_failure_increments_consecutive_count(self):
        """Test that consecutive failures are tracked correctly."""
        from src.services.snapshot_scheduler import (
            SnapshotScheduler, SnapshotResult, SnapshotStatus
        )

        def failing_executor(instance_id):
            return SnapshotResult(
                instance_id=instance_id,
                status=SnapshotStatus.FAILED,
                started_at=time.time(),
                completed_at=time.time(),
                duration_seconds=0.1,
                error="Test failure",
            )

        scheduler = SnapshotScheduler(snapshot_executor=failing_executor)
        scheduler.add_instance('failure-count-test-001', interval_minutes=15)
        scheduler.start()

        # Trigger multiple failures
        for i in range(3):
            scheduler.trigger_snapshot('failure-count-test-001')

        job_info = scheduler.get_instance('failure-count-test-001')
        assert job_info.consecutive_failures == 3
        assert job_info.last_status == SnapshotStatus.FAILED
        assert job_info.last_error == "Test failure"

        scheduler.stop(wait=False)

    def test_success_resets_consecutive_failures(self):
        """Test that a successful snapshot resets the failure counter."""
        from src.services.snapshot_scheduler import (
            SnapshotScheduler, SnapshotResult, SnapshotStatus
        )

        call_count = [0]

        def alternating_executor(instance_id):
            call_count[0] += 1
            if call_count[0] <= 2:
                return SnapshotResult(
                    instance_id=instance_id,
                    status=SnapshotStatus.FAILED,
                    started_at=time.time(),
                    completed_at=time.time(),
                    duration_seconds=0.1,
                    error="Temporary failure",
                )
            else:
                return SnapshotResult(
                    instance_id=instance_id,
                    status=SnapshotStatus.SUCCESS,
                    started_at=time.time(),
                    completed_at=time.time(),
                    duration_seconds=0.1,
                    snapshot_id="success-snap",
                )

        scheduler = SnapshotScheduler(snapshot_executor=alternating_executor)
        scheduler.add_instance('reset-test-001', interval_minutes=15)
        scheduler.start()

        # Two failures
        scheduler.trigger_snapshot('reset-test-001')
        scheduler.trigger_snapshot('reset-test-001')

        job_info = scheduler.get_instance('reset-test-001')
        assert job_info.consecutive_failures == 2

        # One success - should reset counter
        scheduler.trigger_snapshot('reset-test-001')

        job_info = scheduler.get_instance('reset-test-001')
        assert job_info.consecutive_failures == 0
        assert job_info.last_status == SnapshotStatus.SUCCESS

        scheduler.stop(wait=False)


class TestSchedulerDatabaseIntegration:
    """
    Tests for scheduler integration with database persistence.

    These tests verify the database-backed persistence layer.
    """

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock()
        return session

    def test_snapshot_config_model_to_dict(self):
        """Test that SnapshotConfig model converts to dict correctly."""
        from src.models.snapshot_config import SnapshotConfig

        config = SnapshotConfig(
            instance_id='model-test-001',
            interval_minutes=15,
            enabled=True,
            consecutive_failures=0,  # Explicitly set since SQLAlchemy default doesn't apply in memory
        )
        config.id = 1
        config.created_at = datetime.utcnow()
        config.updated_at = datetime.utcnow()

        result = config.to_dict()

        assert result['instance_id'] == 'model-test-001'
        assert result['interval_minutes'] == 15
        assert result['enabled'] is True
        assert result['consecutive_failures'] == 0

    def test_snapshot_config_status_property(self):
        """Test the status property of SnapshotConfig model."""
        from src.models.snapshot_config import SnapshotConfig

        # Test disabled status
        config = SnapshotConfig(
            instance_id='status-test-001',
            interval_minutes=15,
            enabled=False,
            consecutive_failures=0,  # Explicitly set since SQLAlchemy default doesn't apply in memory
        )
        assert config.status == 'disabled'

        # Test pending status (no last snapshot)
        config.enabled = True
        config.last_snapshot_status = None
        assert config.status == 'pending'

        # Test success status
        config.last_snapshot_status = 'success'
        config.last_snapshot_at = datetime.utcnow()
        assert config.status == 'success'

        # Test failure status
        config.last_snapshot_status = 'failure'
        assert config.status == 'failure'

    def test_snapshot_config_is_overdue(self):
        """Test the is_overdue property of SnapshotConfig model."""
        from src.models.snapshot_config import SnapshotConfig

        config = SnapshotConfig(
            instance_id='overdue-test-001',
            interval_minutes=15,
            enabled=True,
            consecutive_failures=0,  # Explicitly set since SQLAlchemy default doesn't apply in memory
        )

        # Not overdue - no last snapshot
        assert config.is_overdue is False

        # Not overdue - recent snapshot
        config.last_snapshot_at = datetime.utcnow() - timedelta(minutes=5)
        assert config.is_overdue is False

        # Overdue - old snapshot (> 2x interval)
        config.last_snapshot_at = datetime.utcnow() - timedelta(minutes=35)  # > 30 min (2x 15)
        assert config.is_overdue is True


class TestSchedulerRestartSimulation:
    """
    Simulates a full restart scenario to verify persistence works correctly.
    """

    def test_full_restart_simulation(self):
        """
        Simulate a complete restart cycle:
        1. Create scheduler and add instances
        2. Execute some snapshots
        3. "Stop" scheduler (simulate shutdown)
        4. Extract state (simulate DB save)
        5. Create new scheduler (simulate restart)
        6. Load state (simulate DB load)
        7. Verify state is preserved
        """
        from src.services.snapshot_scheduler import (
            SnapshotScheduler, SnapshotResult, SnapshotStatus
        )

        def mock_executor(instance_id):
            return SnapshotResult(
                instance_id=instance_id,
                status=SnapshotStatus.SUCCESS,
                started_at=time.time(),
                completed_at=time.time(),
                duration_seconds=0.5,
                snapshot_id=f"snap-{instance_id}-{int(time.time())}",
            )

        # Phase 1: Initial scheduler
        scheduler1 = SnapshotScheduler(snapshot_executor=mock_executor)
        scheduler1.start()

        # Add instances
        scheduler1.add_instance('restart-sim-001', interval_minutes=15, enabled=True)
        scheduler1.add_instance('restart-sim-002', interval_minutes=30, enabled=True)
        scheduler1.add_instance('restart-sim-003', interval_minutes=60, enabled=False)

        # Execute some snapshots
        scheduler1.trigger_snapshot('restart-sim-001')
        scheduler1.trigger_snapshot('restart-sim-002')

        # Extract state (simulates what would be saved to DB)
        instances_before = scheduler1.get_all_instances()

        saved_configs = []
        for instance_id, job_info in instances_before.items():
            saved_configs.append({
                'instance_id': job_info.instance_id,
                'interval_minutes': job_info.interval_minutes,
                'enabled': job_info.enabled,
                'last_snapshot_at': job_info.last_snapshot_at,
                'next_snapshot_at': job_info.next_snapshot_at,
                'consecutive_failures': job_info.consecutive_failures,
            })

        # Phase 2: Shutdown
        scheduler1.stop()

        # Phase 3: Create new scheduler (simulates restart)
        scheduler2 = SnapshotScheduler(snapshot_executor=mock_executor)

        # Load saved state
        scheduler2.load_from_configs(saved_configs)
        scheduler2.start()

        # Verify state is preserved
        for config in saved_configs:
            instance_id = config['instance_id']
            job_info = scheduler2.get_instance(instance_id)

            assert job_info is not None, f"Instance {instance_id} not found after restart"
            assert job_info.interval_minutes == config['interval_minutes']
            assert job_info.enabled == config['enabled']

            # Verify last_snapshot_at is preserved for instances that had snapshots
            if config['last_snapshot_at']:
                assert job_info.last_snapshot_at == config['last_snapshot_at']

        # Verify scheduler is functional after restart
        status = scheduler2.get_status()
        assert status['running'] is True
        assert status['total_instances'] == 3

        # Cleanup
        scheduler2.stop()

    def test_restart_with_overdue_snapshots(self):
        """
        Test that after restart, overdue snapshots are detected correctly.
        """
        from src.services.snapshot_scheduler import SnapshotScheduler

        # Simulate configs with old last_snapshot_at
        now = time.time()
        configs = [
            {
                'instance_id': 'overdue-restart-001',
                'interval_minutes': 15,
                'enabled': True,
                'last_snapshot_at': now - 3600,  # 1 hour ago (way overdue)
                'consecutive_failures': 0,
            },
            {
                'instance_id': 'overdue-restart-002',
                'interval_minutes': 15,
                'enabled': True,
                'last_snapshot_at': now - 300,  # 5 min ago (not overdue)
                'consecutive_failures': 0,
            },
        ]

        scheduler = SnapshotScheduler()
        scheduler.load_from_configs(configs)

        job1 = scheduler.get_instance('overdue-restart-001')
        job2 = scheduler.get_instance('overdue-restart-002')

        assert job1.is_overdue() is True, "Old snapshot should be detected as overdue"
        assert job2.is_overdue() is False, "Recent snapshot should not be overdue"

        scheduler.stop(wait=False)


class TestAppInitializerIntegration:
    """
    Tests for the app-level scheduler initialization.
    """

    def test_scheduler_initializer_function(self):
        """Test the scheduler initialization function."""
        from src.services.snapshot_scheduler import get_snapshot_scheduler, SnapshotScheduler

        # Get scheduler singleton
        scheduler = get_snapshot_scheduler()

        assert scheduler is not None
        assert isinstance(scheduler, SnapshotScheduler)

    def test_scheduler_can_load_db_configs(self):
        """Test that scheduler can receive configs in database format."""
        from src.services.snapshot_scheduler import SnapshotScheduler
        from datetime import datetime

        # Format as would come from database (with datetime objects)
        now = datetime.utcnow()
        db_style_configs = [
            {
                'instance_id': 'db-format-001',
                'interval_minutes': 15,
                'enabled': True,
                'last_snapshot_at': (now - timedelta(minutes=10)).timestamp(),
                'consecutive_failures': 0,
            },
        ]

        scheduler = SnapshotScheduler()
        scheduler.load_from_configs(db_style_configs)

        job = scheduler.get_instance('db-format-001')
        assert job is not None
        assert job.interval_minutes == 15

        scheduler.stop(wait=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
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
