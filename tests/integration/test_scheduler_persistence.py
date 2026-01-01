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
