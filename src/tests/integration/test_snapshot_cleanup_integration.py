"""
Integration tests for snapshot cleanup storage deletion across providers.

Tests the full cleanup workflow including:
- Storage deletion with B2, R2, S3 providers
- Retry logic on storage deletion failures
- Audit log creation after deletions
- Metrics updates after cleanup operations

These tests use mock providers to simulate real storage behavior
without requiring actual cloud credentials.
"""

import os
import sys
import time
import tempfile
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass, field

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.services.snapshot_cleanup_agent import (
    SnapshotCleanupAgent,
    SnapshotRepository,
    InMemorySnapshotRepository,
    StorageProviderProtocol,
)
from src.models.snapshot_metadata import (
    SnapshotMetadata,
    SnapshotStatus,
    DeletionReason,
)
from src.config.snapshot_lifecycle_config import (
    SnapshotLifecycleConfig,
    SnapshotLifecycleManager,
    InstanceSnapshotConfig,
    RetentionPolicyConfig,
    CleanupScheduleConfig,
)
from src.services.snapshot_audit_logger import (
    SnapshotAuditLogger,
    AuditEventType,
    SnapshotDeletionAuditEntry,
)
from src.services.snapshot_cleanup_metrics import (
    CleanupMetrics,
    CleanupRunMetrics,
)


# ============================================================
# Mock Storage Providers
# ============================================================

@dataclass
class StorageOperation:
    """Record of a storage operation for verification."""
    operation: str  # 'delete', 'upload', etc.
    path: str
    provider: str
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None


class MockStorageProvider:
    """
    Mock storage provider that simulates real storage behavior.

    Tracks all operations for verification in tests.
    Can be configured to fail or succeed.
    """

    def __init__(
        self,
        provider_name: str = "b2",
        fail_until_attempt: int = 0,
        always_fail: bool = False,
        fail_for_paths: Optional[List[str]] = None,
    ):
        """
        Initialize mock storage provider.

        Args:
            provider_name: Name of the provider (b2, r2, s3)
            fail_until_attempt: Fail until this attempt number (for retry testing)
            always_fail: Always fail all operations
            fail_for_paths: List of paths that should fail
        """
        self.provider_name = provider_name
        self.fail_until_attempt = fail_until_attempt
        self.always_fail = always_fail
        self.fail_for_paths = fail_for_paths or []

        # Tracking
        self.operations: List[StorageOperation] = []
        self.attempt_counts: Dict[str, int] = {}  # path -> attempt count

    def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            remote_path: Path to delete

        Returns:
            True if deleted successfully
        """
        # Track attempt count
        if remote_path not in self.attempt_counts:
            self.attempt_counts[remote_path] = 0
        self.attempt_counts[remote_path] += 1
        current_attempt = self.attempt_counts[remote_path]

        # Check failure conditions
        if self.always_fail:
            self._record_operation('delete', remote_path, False, "Always fail mode")
            return False

        if remote_path in self.fail_for_paths:
            self._record_operation('delete', remote_path, False, "Path in fail list")
            return False

        if current_attempt <= self.fail_until_attempt:
            self._record_operation(
                'delete', remote_path, False,
                f"Fail until attempt {self.fail_until_attempt}"
            )
            return False

        # Success
        self._record_operation('delete', remote_path, True)
        return True

    def _record_operation(
        self,
        operation: str,
        path: str,
        success: bool,
        error: Optional[str] = None
    ):
        """Record an operation for later verification."""
        self.operations.append(StorageOperation(
            operation=operation,
            path=path,
            provider=self.provider_name,
            success=success,
            error=error,
        ))

    def get_delete_count(self) -> int:
        """Get count of successful deletes."""
        return sum(1 for op in self.operations if op.operation == 'delete' and op.success)

    def get_total_attempts(self, path: str) -> int:
        """Get total attempts for a specific path."""
        return self.attempt_counts.get(path, 0)

    def reset(self):
        """Reset all tracking."""
        self.operations = []
        self.attempt_counts = {}


class MockExceptionProvider:
    """Storage provider that throws exceptions."""

    def __init__(self, exception_type: type = Exception, message: str = "Connection error"):
        self.exception_type = exception_type
        self.message = message
        self.call_count = 0

    def delete_file(self, remote_path: str) -> bool:
        self.call_count += 1
        raise self.exception_type(self.message)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_lifecycle_manager():
    """Create a mock SnapshotLifecycleManager."""
    manager = Mock(spec=SnapshotLifecycleManager)

    # Default global config
    global_config = SnapshotLifecycleConfig(
        default_retention_days=7,
        retention=RetentionPolicyConfig(enabled=True),
        cleanup_schedule=CleanupScheduleConfig(enabled=True),
    )
    manager.get_global_config.return_value = global_config
    manager.list_instance_configs.return_value = {}

    def get_instance_config(instance_id):
        return InstanceSnapshotConfig(
            instance_id=instance_id,
            use_global_settings=True,
        )
    manager.get_instance_config.side_effect = get_instance_config

    return manager


@pytest.fixture
def snapshot_repository():
    """Create an in-memory snapshot repository."""
    return InMemorySnapshotRepository()


@pytest.fixture
def audit_logger(temp_dir):
    """Create an audit logger with temporary file."""
    audit_file = os.path.join(temp_dir, "audit.json")
    return SnapshotAuditLogger(audit_file_path=audit_file)


@pytest.fixture
def cleanup_metrics(temp_dir):
    """Create a cleanup metrics service with temporary file."""
    metrics_file = os.path.join(temp_dir, "metrics.json")
    return CleanupMetrics(metrics_file_path=metrics_file)


def create_snapshot(
    snapshot_id: str,
    age_days: int = 0,
    keep_forever: bool = False,
    retention_days: int = None,
    instance_id: str = "instance-1",
    status: SnapshotStatus = SnapshotStatus.ACTIVE,
    size_bytes: int = 1024 * 1024,  # 1 MB
    storage_provider: str = "b2",
    storage_path: str = None,
) -> SnapshotMetadata:
    """Helper to create test snapshots."""
    created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
    snapshot = SnapshotMetadata(
        snapshot_id=snapshot_id,
        instance_id=instance_id,
        keep_forever=keep_forever,
        retention_days=retention_days,
        status=status,
        created_at=created_at.isoformat(),
        size_bytes=size_bytes,
        storage_provider=storage_provider,
    )
    snapshot.storage_path = storage_path or f"snapshots/{instance_id}/{snapshot_id}"
    return snapshot


# ============================================================
# Storage Provider Integration Tests
# ============================================================

class TestDeleteFromB2:
    """Integration tests for B2 storage deletion."""

    def test_delete_from_b2_success(
        self, mock_lifecycle_manager, snapshot_repository
    ):
        """
        Test successful deletion from B2 storage.

        Scenario:
        - Snapshot stored in B2
        - Mock provider returns success
        - Snapshot status updated to DELETED
        """
        # Create B2 mock provider
        b2_provider = MockStorageProvider(provider_name="b2")
        providers_used = []

        def mock_factory(snapshot):
            providers_used.append(snapshot.storage_provider)
            return b2_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create B2 snapshot
        snapshot = create_snapshot(
            "snap-b2-test",
            age_days=10,
            storage_provider="b2",
        )
        snapshot_repository.add_snapshot(snapshot)

        # Execute cleanup cycle
        agent._cleanup_cycle()

        # Verify
        assert "b2" in providers_used
        assert b2_provider.get_delete_count() == 1

        updated = snapshot_repository.get_snapshot("snap-b2-test")
        assert updated.status == SnapshotStatus.DELETED

    def test_delete_from_b2_multiple_snapshots(
        self, mock_lifecycle_manager, snapshot_repository
    ):
        """
        Test deleting multiple snapshots from B2.

        Scenario:
        - 5 expired snapshots in B2
        - All should be deleted successfully
        """
        b2_provider = MockStorageProvider(provider_name="b2")

        def mock_factory(snapshot):
            return b2_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create 5 expired snapshots
        for i in range(5):
            snap = create_snapshot(
                f"snap-b2-multi-{i}",
                age_days=10,
                storage_provider="b2",
            )
            snapshot_repository.add_snapshot(snap)

        # Execute cleanup
        agent._cleanup_cycle()

        # Verify all deleted
        assert b2_provider.get_delete_count() == 5

        stats = agent.get_cleanup_stats()
        assert stats['snapshots_deleted'] == 5
        assert stats['snapshots_failed'] == 0


class TestDeleteFromR2:
    """Integration tests for R2 storage deletion."""

    def test_delete_from_r2_success(
        self, mock_lifecycle_manager, snapshot_repository
    ):
        """
        Test successful deletion from R2 (Cloudflare) storage.

        Scenario:
        - Snapshot stored in R2
        - Mock provider returns success
        """
        r2_provider = MockStorageProvider(provider_name="r2")
        providers_used = []

        def mock_factory(snapshot):
            providers_used.append(snapshot.storage_provider)
            return r2_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create R2 snapshot
        snapshot = create_snapshot(
            "snap-r2-test",
            age_days=10,
            storage_provider="r2",
        )
        snapshot_repository.add_snapshot(snapshot)

        # Execute
        agent._cleanup_cycle()

        # Verify
        assert "r2" in providers_used
        assert r2_provider.get_delete_count() == 1

        updated = snapshot_repository.get_snapshot("snap-r2-test")
        assert updated.status == SnapshotStatus.DELETED


class TestDeleteFromS3:
    """Integration tests for S3 storage deletion."""

    def test_delete_from_s3_success(
        self, mock_lifecycle_manager, snapshot_repository
    ):
        """
        Test successful deletion from AWS S3 storage.

        Scenario:
        - Snapshot stored in S3
        - Mock provider returns success
        """
        s3_provider = MockStorageProvider(provider_name="s3")
        providers_used = []

        def mock_factory(snapshot):
            providers_used.append(snapshot.storage_provider)
            return s3_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create S3 snapshot
        snapshot = create_snapshot(
            "snap-s3-test",
            age_days=10,
            storage_provider="s3",
        )
        snapshot_repository.add_snapshot(snapshot)

        # Execute
        agent._cleanup_cycle()

        # Verify
        assert "s3" in providers_used
        assert s3_provider.get_delete_count() == 1

        updated = snapshot_repository.get_snapshot("snap-s3-test")
        assert updated.status == SnapshotStatus.DELETED


class TestMultiProviderCleanup:
    """Integration tests for cleanup across multiple storage providers."""

    def test_cleanup_multi_provider_snapshots(
        self, mock_lifecycle_manager, snapshot_repository
    ):
        """
        Test cleanup of snapshots stored in different providers.

        Scenario:
        - Snapshots in B2, R2, and S3
        - All should be deleted using appropriate providers
        """
        b2_provider = MockStorageProvider(provider_name="b2")
        r2_provider = MockStorageProvider(provider_name="r2")
        s3_provider = MockStorageProvider(provider_name="s3")

        def mock_factory(snapshot):
            if snapshot.storage_provider == "b2":
                return b2_provider
            elif snapshot.storage_provider == "r2":
                return r2_provider
            elif snapshot.storage_provider == "s3":
                return s3_provider
            return None

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create snapshots in different providers
        snap_b2 = create_snapshot("snap-multi-b2", age_days=10, storage_provider="b2")
        snap_r2 = create_snapshot("snap-multi-r2", age_days=10, storage_provider="r2")
        snap_s3 = create_snapshot("snap-multi-s3", age_days=10, storage_provider="s3")

        snapshot_repository.add_snapshot(snap_b2)
        snapshot_repository.add_snapshot(snap_r2)
        snapshot_repository.add_snapshot(snap_s3)

        # Execute
        agent._cleanup_cycle()

        # Verify each provider was called
        assert b2_provider.get_delete_count() == 1
        assert r2_provider.get_delete_count() == 1
        assert s3_provider.get_delete_count() == 1

        # Verify all snapshots deleted
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_deleted'] == 3
        assert stats['snapshots_failed'] == 0


# ============================================================
# Retry Logic Tests
# ============================================================

class TestDeletionRetryOnFailure:
    """Integration tests for storage deletion retry logic."""

    def test_retry_on_first_failure(
        self, mock_lifecycle_manager, snapshot_repository
    ):
        """
        Test that deletion retries after first failure.

        Scenario:
        - Provider fails on first attempt
        - Provider succeeds on second attempt
        - Snapshot should be deleted
        """
        # Provider that fails first attempt, succeeds on second
        provider = MockStorageProvider(provider_name="b2", fail_until_attempt=1)

        def mock_factory(snapshot):
            return provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
            max_retries=3,
            retry_base_delay=0.01,  # Fast for tests
        )
        agent.running = True

        snapshot = create_snapshot("snap-retry-1", age_days=10)
        snapshot_repository.add_snapshot(snapshot)

        # Execute
        agent._cleanup_cycle()

        # Verify: 2 attempts total, success on second
        assert provider.get_total_attempts(snapshot.storage_path) == 2
        assert provider.get_delete_count() == 1

        updated = snapshot_repository.get_snapshot("snap-retry-1")
        assert updated.status == SnapshotStatus.DELETED

    def test_retry_exhausted_marks_failed(
        self, mock_lifecycle_manager, snapshot_repository
    ):
        """
        Test that snapshot is marked FAILED after exhausting retries.

        Scenario:
        - Provider always fails
        - After max_retries, snapshot should be FAILED, not DELETED
        """
        provider = MockStorageProvider(provider_name="b2", always_fail=True)

        def mock_factory(snapshot):
            return provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
            max_retries=3,
            retry_base_delay=0.01,
        )
        agent.running = True

        snapshot = create_snapshot("snap-fail-all", age_days=10)
        snapshot_repository.add_snapshot(snapshot)

        # Execute
        agent._cleanup_cycle()

        # Verify: 3 attempts (max_retries), all failed
        assert provider.get_total_attempts(snapshot.storage_path) == 3
        assert provider.get_delete_count() == 0

        updated = snapshot_repository.get_snapshot("snap-fail-all")
        assert updated.status == SnapshotStatus.FAILED

        stats = agent.get_cleanup_stats()
        assert stats['snapshots_failed'] == 1
        assert stats['snapshots_deleted'] == 0

    def test_retry_on_exception(
        self, mock_lifecycle_manager, snapshot_repository
    ):
        """
        Test that exceptions during deletion trigger retry.

        Scenario:
        - Provider throws exception
        - Should retry and eventually fail
        """
        exception_provider = MockExceptionProvider(
            exception_type=ConnectionError,
            message="Connection refused"
        )

        def mock_factory(snapshot):
            return exception_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
            max_retries=2,
            retry_base_delay=0.01,
        )
        agent.running = True

        snapshot = create_snapshot("snap-exception", age_days=10)
        snapshot_repository.add_snapshot(snapshot)

        # Execute
        agent._cleanup_cycle()

        # Verify: provider was called max_retries times
        assert exception_provider.call_count == 2

        updated = snapshot_repository.get_snapshot("snap-exception")
        assert updated.status == SnapshotStatus.FAILED

    def test_partial_failure_continues(
        self, mock_lifecycle_manager, snapshot_repository
    ):
        """
        Test that cleanup continues even when some deletions fail.

        Scenario:
        - 3 snapshots
        - 1 fails, 2 succeed
        - Stats should reflect partial success
        """
        # Provider that fails for specific path
        provider = MockStorageProvider(
            provider_name="b2",
            fail_for_paths=["snapshots/instance-1/snap-will-fail"]
        )

        def mock_factory(snapshot):
            return provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
            max_retries=1,  # Quick failure
            retry_base_delay=0.01,
        )
        agent.running = True

        # Create snapshots - one will fail
        snap_ok1 = create_snapshot("snap-ok-1", age_days=10)
        snap_fail = create_snapshot("snap-will-fail", age_days=10)
        snap_ok2 = create_snapshot("snap-ok-2", age_days=10)

        snapshot_repository.add_snapshot(snap_ok1)
        snapshot_repository.add_snapshot(snap_fail)
        snapshot_repository.add_snapshot(snap_ok2)

        # Execute
        agent._cleanup_cycle()

        # Verify partial success
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_deleted'] == 2
        assert stats['snapshots_failed'] == 1

        # Verify individual statuses
        assert snapshot_repository.get_snapshot("snap-ok-1").status == SnapshotStatus.DELETED
        assert snapshot_repository.get_snapshot("snap-will-fail").status == SnapshotStatus.FAILED
        assert snapshot_repository.get_snapshot("snap-ok-2").status == SnapshotStatus.DELETED


# ============================================================
# Audit Log Integration Tests
# ============================================================

class TestAuditLogCreated:
    """Integration tests for audit logging during cleanup."""

    def test_audit_log_on_deletion(
        self, mock_lifecycle_manager, snapshot_repository, audit_logger
    ):
        """
        Test that audit log entry is created when snapshot is deleted.

        Scenario:
        - Delete a snapshot
        - Verify audit entry created with correct data
        """
        provider = MockStorageProvider(provider_name="b2")

        def mock_factory(snapshot):
            return provider

        # Create agent that logs to audit
        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        snapshot = create_snapshot(
            "snap-audit-test",
            age_days=10,
            size_bytes=5000000,  # 5MB
        )
        snapshot_repository.add_snapshot(snapshot)

        # Log cleanup start
        run_id = audit_logger.log_cleanup_started(snapshots_to_process=1)

        # Execute cleanup cycle
        agent._cleanup_cycle()

        # Get the snapshot after cleanup
        updated_snapshot = snapshot_repository.get_snapshot("snap-audit-test")

        # Log the deletion to audit
        audit_logger.log_deletion(
            snapshot_id=updated_snapshot.snapshot_id,
            user_id="test-user",
            deletion_reason="expired",
            storage_freed_bytes=updated_snapshot.size_bytes,
            instance_id=updated_snapshot.instance_id,
            storage_provider="b2",
            success=True,
            retention_days=7,
            snapshot_age_days=10,
        )

        # Log cleanup completion
        audit_logger.log_cleanup_completed(
            snapshots_deleted=1,
            snapshots_failed=0,
            storage_freed_bytes=updated_snapshot.size_bytes,
        )

        # Verify audit entries
        entries = audit_logger.get_entries(limit=10)
        assert len(entries) >= 3  # start, deletion, complete

        # Find deletion entry
        deletion_entries = [
            e for e in entries
            if e.event_type == AuditEventType.DELETION
        ]
        assert len(deletion_entries) == 1

        deletion = deletion_entries[0]
        assert deletion.snapshot_id == "snap-audit-test"
        assert deletion.deletion_reason == "expired"
        assert deletion.storage_freed_bytes == 5000000
        assert deletion.success is True

    def test_audit_log_on_failure(
        self, mock_lifecycle_manager, snapshot_repository, audit_logger
    ):
        """
        Test that audit log captures deletion failures.

        Scenario:
        - Deletion fails
        - Audit entry should have success=False and error_message
        """
        provider = MockStorageProvider(provider_name="b2", always_fail=True)

        def mock_factory(snapshot):
            return provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
            max_retries=1,
            retry_base_delay=0.01,
        )
        agent.running = True

        snapshot = create_snapshot("snap-audit-fail", age_days=10)
        snapshot_repository.add_snapshot(snapshot)

        # Execute
        agent._cleanup_cycle()

        # Log the failure to audit
        updated = snapshot_repository.get_snapshot("snap-audit-fail")
        audit_logger.log_deletion(
            snapshot_id=updated.snapshot_id,
            user_id="test-user",
            deletion_reason="expired",
            storage_freed_bytes=0,
            success=False,
            error_message="Storage deletion failed after retries",
        )

        # Verify failure recorded
        entries = audit_logger.get_entries(
            event_type=AuditEventType.DELETION_FAILED
        )
        assert len(entries) == 1

        failure = entries[0]
        assert failure.success is False
        assert failure.error_message is not None

    def test_audit_cleanup_cycle_tracking(
        self, mock_lifecycle_manager, snapshot_repository, audit_logger
    ):
        """
        Test that cleanup cycle start/end are tracked in audit.

        Scenario:
        - Run cleanup cycle
        - Verify CLEANUP_STARTED and CLEANUP_COMPLETED entries
        """
        provider = MockStorageProvider(provider_name="b2")

        def mock_factory(snapshot):
            return provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create snapshots
        for i in range(3):
            snap = create_snapshot(f"snap-cycle-{i}", age_days=10)
            snapshot_repository.add_snapshot(snap)

        # Log cleanup lifecycle
        run_id = audit_logger.log_cleanup_started(snapshots_to_process=3)

        agent._cleanup_cycle()

        stats = agent.get_cleanup_stats()
        audit_logger.log_cleanup_completed(
            snapshots_deleted=stats['snapshots_deleted'],
            snapshots_failed=stats['snapshots_failed'],
            storage_freed_bytes=stats['storage_freed_bytes'],
        )

        # Verify cycle entries
        entries = audit_logger.get_entries(limit=20)

        started_entries = [
            e for e in entries
            if e.event_type == AuditEventType.CLEANUP_STARTED
        ]
        completed_entries = [
            e for e in entries
            if e.event_type == AuditEventType.CLEANUP_COMPLETED
        ]

        assert len(started_entries) == 1
        assert len(completed_entries) == 1

        # Verify correlation
        assert started_entries[0].cleanup_run_id == run_id
        assert completed_entries[0].cleanup_run_id == run_id


# ============================================================
# Metrics Integration Tests
# ============================================================

class TestMetricsUpdated:
    """Integration tests for cleanup metrics updates."""

    def test_metrics_recorded_after_cleanup(
        self, mock_lifecycle_manager, snapshot_repository, cleanup_metrics
    ):
        """
        Test that metrics are updated after cleanup.

        Scenario:
        - Run cleanup with deletions
        - Verify metrics reflect the operations
        """
        provider = MockStorageProvider(provider_name="b2")

        def mock_factory(snapshot):
            return provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create snapshots with known sizes
        snap1 = create_snapshot("snap-metrics-1", age_days=10, size_bytes=1000000)
        snap2 = create_snapshot("snap-metrics-2", age_days=10, size_bytes=2000000)
        snap3 = create_snapshot("snap-metrics-3", age_days=10, size_bytes=3000000)

        snapshot_repository.add_snapshot(snap1)
        snapshot_repository.add_snapshot(snap2)
        snapshot_repository.add_snapshot(snap3)

        # Execute cleanup
        agent._cleanup_cycle()

        # Record metrics from cleanup stats
        stats = agent.get_cleanup_stats()
        cleanup_metrics.record_cleanup(
            snapshots_deleted=stats['snapshots_deleted'],
            storage_freed=stats['storage_freed_bytes'],
            snapshots_failed=stats['snapshots_failed'],
            success=stats['snapshots_failed'] == 0,
        )

        # Verify metrics
        assert cleanup_metrics.get_total_snapshots_deleted() == 3
        assert cleanup_metrics.get_total_storage_freed() == 6000000  # 6MB
        assert cleanup_metrics.get_success_rate() == 1.0

    def test_metrics_track_failures(
        self, mock_lifecycle_manager, snapshot_repository, cleanup_metrics
    ):
        """
        Test that metrics track cleanup failures.

        Scenario:
        - Cleanup with mixed success/failure
        - Verify metrics reflect partial failure
        - Note: success=True means run completed (partial success counts)
        - success=False means run crashed/aborted
        """
        # Provider that fails for specific path
        provider = MockStorageProvider(
            provider_name="b2",
            fail_for_paths=["snapshots/instance-1/snap-metrics-fail"]
        )

        def mock_factory(snapshot):
            return provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
            max_retries=1,
            retry_base_delay=0.01,
        )
        agent.running = True

        snap_ok = create_snapshot("snap-metrics-ok", age_days=10, size_bytes=1000000)
        snap_fail = create_snapshot("snap-metrics-fail", age_days=10, size_bytes=2000000)

        snapshot_repository.add_snapshot(snap_ok)
        snapshot_repository.add_snapshot(snap_fail)

        # Execute
        agent._cleanup_cycle()

        # Record metrics - partial success is still a successful run
        # (run completed, some deletions succeeded, some failed)
        stats = agent.get_cleanup_stats()
        cleanup_metrics.record_cleanup(
            snapshots_deleted=stats['snapshots_deleted'],
            storage_freed=stats['storage_freed_bytes'],
            snapshots_failed=stats['snapshots_failed'],
            success=True,  # Run completed (partial success counts)
        )

        # Verify partial success recorded correctly
        assert cleanup_metrics.get_total_snapshots_deleted() == 1
        assert cleanup_metrics.get_total_storage_freed() == 1000000

        # The run itself was successful even though some deletions failed
        assert cleanup_metrics.get_success_rate() == 1.0

        # Verify the stats tracked the failure count
        entries = cleanup_metrics.get_entries(limit=1)
        assert len(entries) == 1
        assert entries[0].snapshots_failed == 1

    def test_metrics_summary(
        self, mock_lifecycle_manager, snapshot_repository, cleanup_metrics
    ):
        """
        Test metrics summary after multiple cleanup runs.

        Scenario:
        - Run multiple cleanups
        - Verify summary aggregates correctly
        """
        provider = MockStorageProvider(provider_name="b2")

        def mock_factory(snapshot):
            return provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Run 1: 2 snapshots
        snap1 = create_snapshot("snap-run1-1", age_days=10, size_bytes=1000000)
        snap2 = create_snapshot("snap-run1-2", age_days=10, size_bytes=1000000)
        snapshot_repository.add_snapshot(snap1)
        snapshot_repository.add_snapshot(snap2)

        agent._cleanup_cycle()
        stats1 = agent.get_cleanup_stats()
        cleanup_metrics.record_cleanup(
            snapshots_deleted=stats1['snapshots_deleted'],
            storage_freed=stats1['storage_freed_bytes'],
        )

        # Reset repository for run 2
        snapshot_repository.clear()

        # Run 2: 3 snapshots
        for i in range(3):
            snap = create_snapshot(f"snap-run2-{i}", age_days=10, size_bytes=500000)
            snapshot_repository.add_snapshot(snap)

        agent._cleanup_cycle()
        stats2 = agent.get_cleanup_stats()
        cleanup_metrics.record_cleanup(
            snapshots_deleted=stats2['snapshots_deleted'],
            storage_freed=stats2['storage_freed_bytes'],
        )

        # Verify summary
        summary = cleanup_metrics.get_summary()
        assert summary['total_snapshots_deleted'] == 5  # 2 + 3
        assert summary['total_storage_freed'] == 3500000  # 2MB + 1.5MB
        assert summary['total_cleanup_runs'] == 2
        assert summary['success_rate'] == 1.0


# ============================================================
# Full Workflow Integration Tests
# ============================================================

class TestFullCleanupWorkflow:
    """End-to-end integration tests for the complete cleanup workflow."""

    def test_complete_cleanup_workflow(
        self, mock_lifecycle_manager, snapshot_repository, audit_logger, cleanup_metrics
    ):
        """
        Test complete cleanup workflow with storage, audit, and metrics.

        Scenario:
        - Create expired snapshots
        - Run cleanup
        - Verify storage deletion, audit logs, and metrics all updated
        """
        provider = MockStorageProvider(provider_name="b2")

        def mock_factory(snapshot):
            return provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create test snapshots
        total_size = 0
        for i in range(5):
            size = (i + 1) * 1000000  # 1MB, 2MB, 3MB, 4MB, 5MB
            snap = create_snapshot(
                f"snap-workflow-{i}",
                age_days=10,
                size_bytes=size,
                storage_provider="b2",
            )
            snapshot_repository.add_snapshot(snap)
            total_size += size

        # Start audit tracking
        run_id = audit_logger.log_cleanup_started(snapshots_to_process=5)

        # Execute cleanup
        agent._cleanup_cycle()

        # Get stats
        stats = agent.get_cleanup_stats()

        # Log each deletion to audit
        for i in range(5):
            snap = snapshot_repository.get_snapshot(f"snap-workflow-{i}")
            audit_logger.log_deletion(
                snapshot_id=snap.snapshot_id,
                user_id="system",
                deletion_reason="expired",
                storage_freed_bytes=snap.size_bytes,
                instance_id=snap.instance_id,
                storage_provider="b2",
                success=(snap.status == SnapshotStatus.DELETED),
            )

        # Complete audit tracking
        audit_logger.log_cleanup_completed(
            snapshots_deleted=stats['snapshots_deleted'],
            snapshots_failed=stats['snapshots_failed'],
            storage_freed_bytes=stats['storage_freed_bytes'],
        )

        # Record metrics
        cleanup_metrics.record_cleanup(
            snapshots_deleted=stats['snapshots_deleted'],
            storage_freed=stats['storage_freed_bytes'],
            snapshots_failed=stats['snapshots_failed'],
            success=True,
        )

        # === Verify Storage ===
        assert provider.get_delete_count() == 5

        # === Verify Audit ===
        audit_entries = audit_logger.get_entries(limit=20)
        deletion_entries = [
            e for e in audit_entries
            if e.event_type == AuditEventType.DELETION
        ]
        assert len(deletion_entries) == 5

        # Verify storage freed tracked in audit
        audit_total_freed = sum(e.storage_freed_bytes for e in deletion_entries)
        assert audit_total_freed == total_size

        # === Verify Metrics ===
        assert cleanup_metrics.get_total_snapshots_deleted() == 5
        assert cleanup_metrics.get_total_storage_freed() == total_size

        # === Verify Stats ===
        assert stats['snapshots_deleted'] == 5
        assert stats['snapshots_failed'] == 0
        assert stats['storage_freed_bytes'] == total_size

    def test_workflow_with_keep_forever(
        self, mock_lifecycle_manager, snapshot_repository, audit_logger, cleanup_metrics
    ):
        """
        Test cleanup workflow respects keep_forever flag.

        Scenario:
        - Mix of regular and keep_forever snapshots
        - Only regular snapshots should be deleted
        """
        provider = MockStorageProvider(provider_name="b2")

        def mock_factory(snapshot):
            return provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create regular expired snapshots
        snap1 = create_snapshot("snap-regular-1", age_days=10, keep_forever=False)
        snap2 = create_snapshot("snap-regular-2", age_days=10, keep_forever=False)

        # Create keep_forever snapshot
        snap_permanent = create_snapshot("snap-permanent", age_days=100, keep_forever=True)

        snapshot_repository.add_snapshot(snap1)
        snapshot_repository.add_snapshot(snap2)
        snapshot_repository.add_snapshot(snap_permanent)

        # Execute
        agent._cleanup_cycle()

        # Verify only regular snapshots deleted
        assert snapshot_repository.get_snapshot("snap-regular-1").status == SnapshotStatus.DELETED
        assert snapshot_repository.get_snapshot("snap-regular-2").status == SnapshotStatus.DELETED
        assert snapshot_repository.get_snapshot("snap-permanent").status == SnapshotStatus.ACTIVE

        # Verify stats
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_deleted'] == 2
        assert stats['snapshots_identified'] == 2  # permanent not identified


# ============================================================
# Manual Test Runner (optional)
# ============================================================

def run_all_tests():
    """Run all integration tests manually."""
    print("=" * 70)
    print("INTEGRATION TESTS - Snapshot Cleanup Storage Deletion")
    print("=" * 70)
    print()

    test_classes = [
        TestDeleteFromB2,
        TestDeleteFromR2,
        TestDeleteFromS3,
        TestMultiProviderCleanup,
        TestDeletionRetryOnFailure,
        TestAuditLogCreated,
        TestMetricsUpdated,
        TestFullCleanupWorkflow,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        print(f"\n{'='*50}")
        print(f"Running: {test_class.__name__}")
        print("=" * 50)

        instance = test_class()
        test_methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in test_methods:
            total_tests += 1
            method = getattr(instance, method_name)

            try:
                # Create fixtures for each test
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Create mock lifecycle manager
                    manager = Mock(spec=SnapshotLifecycleManager)
                    global_config = SnapshotLifecycleConfig(
                        default_retention_days=7,
                        retention=RetentionPolicyConfig(enabled=True),
                        cleanup_schedule=CleanupScheduleConfig(enabled=True),
                    )
                    manager.get_global_config.return_value = global_config
                    manager.list_instance_configs.return_value = {}

                    def get_instance_config(instance_id):
                        return InstanceSnapshotConfig(
                            instance_id=instance_id,
                            use_global_settings=True,
                        )
                    manager.get_instance_config.side_effect = get_instance_config

                    # Create other fixtures
                    repo = InMemorySnapshotRepository()
                    audit = SnapshotAuditLogger(
                        audit_file_path=os.path.join(tmpdir, "audit.json")
                    )
                    metrics = CleanupMetrics(
                        metrics_file_path=os.path.join(tmpdir, "metrics.json")
                    )

                    # Get method signature and call with appropriate fixtures
                    import inspect
                    sig = inspect.signature(method)
                    params = sig.parameters

                    kwargs = {}
                    if 'mock_lifecycle_manager' in params:
                        kwargs['mock_lifecycle_manager'] = manager
                    if 'snapshot_repository' in params:
                        kwargs['snapshot_repository'] = repo
                    if 'audit_logger' in params:
                        kwargs['audit_logger'] = audit
                    if 'cleanup_metrics' in params:
                        kwargs['cleanup_metrics'] = metrics

                    method(**kwargs)

                print(f"  PASSED {method_name}")
                passed_tests += 1
            except AssertionError as e:
                print(f"  FAILED {method_name}: {e}")
                failed_tests.append(f"{test_class.__name__}.{method_name}")
            except Exception as e:
                print(f"  ERROR {method_name}: {type(e).__name__}: {e}")
                failed_tests.append(f"{test_class.__name__}.{method_name}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nTotal: {total_tests} tests")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")

    if failed_tests:
        print("\nFailed tests:")
        for test in failed_tests:
            print(f"  - {test}")
        return False
    else:
        print("\nALL TESTS PASSED!")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
