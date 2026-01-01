"""
End-to-end tests for full snapshot cleanup workflow.

Tests the complete cleanup flow from end-to-end:
- Expired snapshot identification and deletion
- Keep-forever protection enforcement
- Configurable retention policy adherence
- Complete audit trail creation
- Accurate metrics tracking
- Manual cleanup trigger via agent

These tests simulate real-world scenarios using mocked storage
providers to verify the full system integration.
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
# Mock Storage Provider
# ============================================================

@dataclass
class StorageOperation:
    """Record of a storage operation for verification."""
    operation: str
    path: str
    provider: str
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None


class MockStorageProvider:
    """Mock storage provider for E2E tests."""

    def __init__(
        self,
        provider_name: str = "b2",
        fail_for_paths: Optional[List[str]] = None,
    ):
        self.provider_name = provider_name
        self.fail_for_paths = fail_for_paths or []
        self.operations: List[StorageOperation] = []
        self.deleted_paths: List[str] = []

    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from mock storage."""
        if remote_path in self.fail_for_paths:
            self.operations.append(StorageOperation(
                operation='delete',
                path=remote_path,
                provider=self.provider_name,
                success=False,
                error="Path in fail list",
            ))
            return False

        self.operations.append(StorageOperation(
            operation='delete',
            path=remote_path,
            provider=self.provider_name,
            success=True,
        ))
        self.deleted_paths.append(remote_path)
        return True

    def get_delete_count(self) -> int:
        """Get count of successful deletes."""
        return len(self.deleted_paths)

    def was_deleted(self, path: str) -> bool:
        """Check if a path was deleted."""
        return path in self.deleted_paths


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
    """Create a mock SnapshotLifecycleManager with configurable defaults."""
    manager = Mock(spec=SnapshotLifecycleManager)

    # Global config with 7-day default
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


@pytest.fixture
def mock_storage_provider():
    """Create a mock storage provider."""
    return MockStorageProvider(provider_name="b2")


def create_snapshot(
    snapshot_id: str,
    age_days: int = 0,
    keep_forever: bool = False,
    retention_days: Optional[int] = None,
    instance_id: str = "instance-1",
    user_id: str = "user-1",
    status: SnapshotStatus = SnapshotStatus.ACTIVE,
    size_bytes: int = 1024 * 1024,
    storage_provider: str = "b2",
    storage_path: Optional[str] = None,
) -> SnapshotMetadata:
    """Helper to create test snapshots with specific age."""
    created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
    snapshot = SnapshotMetadata(
        snapshot_id=snapshot_id,
        instance_id=instance_id,
        user_id=user_id,
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
# E2E Test: Expired Snapshot Cleanup
# ============================================================

class TestExpiredSnapshotDeleted:
    """
    E2E tests for expired snapshot deletion flow.

    Flow:
    1. Create snapshot with 7-day retention
    2. Simulate time passage (8 days)
    3. Run cleanup job
    4. Verify snapshot deleted from storage and database
    5. Verify audit log created
    """

    def test_expired_snapshot_deleted(
        self, mock_lifecycle_manager, snapshot_repository, audit_logger,
        cleanup_metrics, mock_storage_provider
    ):
        """
        Full E2E test: Expired snapshot is deleted with complete audit trail.

        Steps:
        1. Create a snapshot that is 10 days old (expired with 7-day retention)
        2. Run cleanup cycle
        3. Verify:
           - Snapshot deleted from storage
           - Snapshot marked as DELETED in repository
           - Audit entry created
           - Metrics updated
        """
        # Setup agent
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create expired snapshot (10 days old, 7-day retention = expired)
        snapshot = create_snapshot(
            "snap-expired-001",
            age_days=10,
            size_bytes=5000000,  # 5MB
            keep_forever=False,
        )
        snapshot_repository.add_snapshot(snapshot)

        # Log cleanup start
        run_id = audit_logger.log_cleanup_started(snapshots_to_process=1)

        # Execute cleanup
        agent._cleanup_cycle()

        # Get cleanup stats
        stats = agent.get_cleanup_stats()

        # Log deletion to audit
        updated_snapshot = snapshot_repository.get_snapshot("snap-expired-001")
        audit_logger.log_deletion(
            snapshot_id=updated_snapshot.snapshot_id,
            user_id="system",
            deletion_reason="expired",
            storage_freed_bytes=updated_snapshot.size_bytes,
            instance_id=updated_snapshot.instance_id,
            storage_provider="b2",
            success=(updated_snapshot.status == SnapshotStatus.DELETED),
            retention_days=7,
            snapshot_age_days=10,
        )

        # Log cleanup completion
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

        # === VERIFY: Storage Deletion ===
        assert mock_storage_provider.get_delete_count() == 1
        assert mock_storage_provider.was_deleted(snapshot.storage_path)

        # === VERIFY: Database Status ===
        updated = snapshot_repository.get_snapshot("snap-expired-001")
        assert updated.status == SnapshotStatus.DELETED

        # === VERIFY: Cleanup Stats ===
        assert stats['snapshots_identified'] == 1
        assert stats['snapshots_deleted'] == 1
        assert stats['snapshots_failed'] == 0
        assert stats['storage_freed_bytes'] == 5000000

        # === VERIFY: Audit Log ===
        audit_entries = audit_logger.get_entries(limit=20)
        deletion_entries = [
            e for e in audit_entries
            if e.event_type == AuditEventType.DELETION
        ]
        assert len(deletion_entries) == 1

        deletion = deletion_entries[0]
        assert deletion.snapshot_id == "snap-expired-001"
        assert deletion.deletion_reason == "expired"
        assert deletion.storage_freed_bytes == 5000000
        assert deletion.success is True
        assert deletion.retention_days == 7
        assert deletion.snapshot_age_days == 10

        # === VERIFY: Metrics ===
        assert cleanup_metrics.get_total_snapshots_deleted() == 1
        assert cleanup_metrics.get_total_storage_freed() == 5000000

    def test_multiple_expired_snapshots_deleted(
        self, mock_lifecycle_manager, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: Multiple expired snapshots are deleted in order.

        Verifies that oldest snapshots are processed first.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create snapshots with different ages (all expired)
        snap_old = create_snapshot("snap-oldest", age_days=30, size_bytes=1000000)
        snap_mid = create_snapshot("snap-middle", age_days=15, size_bytes=2000000)
        snap_new = create_snapshot("snap-newest", age_days=8, size_bytes=3000000)

        snapshot_repository.add_snapshot(snap_old)
        snapshot_repository.add_snapshot(snap_mid)
        snapshot_repository.add_snapshot(snap_new)

        # Execute cleanup
        agent._cleanup_cycle()

        # Verify all deleted
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_deleted'] == 3
        assert stats['storage_freed_bytes'] == 6000000

        # Verify all storage paths deleted
        assert mock_storage_provider.get_delete_count() == 3


# ============================================================
# E2E Test: Keep Forever Protection
# ============================================================

class TestKeepForeverProtected:
    """
    E2E tests for keep_forever protection.

    Flow:
    1. Create snapshot with keep_forever=true
    2. Simulate time passage (30 days)
    3. Run cleanup job
    4. Verify snapshot NOT deleted
    """

    def test_keep_forever_protected(
        self, mock_lifecycle_manager, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: Snapshot with keep_forever=true is never deleted.

        Even after 30 days (way past 7-day retention), the snapshot
        should remain protected.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create old snapshot with keep_forever=True
        snapshot = create_snapshot(
            "snap-permanent",
            age_days=100,  # Very old
            keep_forever=True,
            size_bytes=10000000,  # 10MB
        )
        snapshot_repository.add_snapshot(snapshot)

        # Execute cleanup
        agent._cleanup_cycle()

        # Verify NOT deleted
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_identified'] == 0
        assert stats['snapshots_deleted'] == 0

        # Verify storage not touched
        assert mock_storage_provider.get_delete_count() == 0

        # Verify snapshot still active in repository
        updated = snapshot_repository.get_snapshot("snap-permanent")
        assert updated.status == SnapshotStatus.ACTIVE
        assert updated.keep_forever is True

    def test_keep_forever_mixed_with_expired(
        self, mock_lifecycle_manager, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: Mix of keep_forever and regular snapshots.

        Only regular expired snapshots should be deleted.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create protected snapshots
        snap_protected_1 = create_snapshot(
            "snap-protected-1",
            age_days=50,
            keep_forever=True,
        )
        snap_protected_2 = create_snapshot(
            "snap-protected-2",
            age_days=30,
            keep_forever=True,
        )

        # Create regular expired snapshots
        snap_expired_1 = create_snapshot(
            "snap-expired-1",
            age_days=10,
            keep_forever=False,
        )
        snap_expired_2 = create_snapshot(
            "snap-expired-2",
            age_days=8,
            keep_forever=False,
        )

        # Create non-expired snapshot
        snap_fresh = create_snapshot(
            "snap-fresh",
            age_days=3,  # Not expired (within 7-day retention)
            keep_forever=False,
        )

        snapshot_repository.add_snapshot(snap_protected_1)
        snapshot_repository.add_snapshot(snap_protected_2)
        snapshot_repository.add_snapshot(snap_expired_1)
        snapshot_repository.add_snapshot(snap_expired_2)
        snapshot_repository.add_snapshot(snap_fresh)

        # Execute cleanup
        agent._cleanup_cycle()

        # Verify only expired regular snapshots deleted
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_identified'] == 2  # Only the expired non-protected
        assert stats['snapshots_deleted'] == 2

        # Verify protected snapshots remain
        assert snapshot_repository.get_snapshot("snap-protected-1").status == SnapshotStatus.ACTIVE
        assert snapshot_repository.get_snapshot("snap-protected-2").status == SnapshotStatus.ACTIVE
        assert snapshot_repository.get_snapshot("snap-fresh").status == SnapshotStatus.ACTIVE

        # Verify expired snapshots deleted
        assert snapshot_repository.get_snapshot("snap-expired-1").status == SnapshotStatus.DELETED
        assert snapshot_repository.get_snapshot("snap-expired-2").status == SnapshotStatus.DELETED


# ============================================================
# E2E Test: Configurable Retention
# ============================================================

class TestConfigurableRetention:
    """
    E2E tests for configurable retention periods.

    Flow:
    1. Set user retention to 30 days
    2. Create snapshot
    3. Simulate 15 days
    4. Run cleanup
    5. Verify snapshot NOT deleted
    """

    def test_custom_retention_respected(
        self, mock_lifecycle_manager, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: Custom per-snapshot retention is respected.

        Snapshot with 30-day retention should not be deleted at 15 days.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create snapshot with custom 30-day retention
        snapshot = create_snapshot(
            "snap-custom-retention",
            age_days=15,  # 15 days old
            retention_days=30,  # Custom 30-day retention
            keep_forever=False,
        )
        snapshot_repository.add_snapshot(snapshot)

        # Execute cleanup
        agent._cleanup_cycle()

        # Verify NOT deleted (15 days < 30 day retention)
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_identified'] == 0
        assert stats['snapshots_deleted'] == 0

        updated = snapshot_repository.get_snapshot("snap-custom-retention")
        assert updated.status == SnapshotStatus.ACTIVE

    def test_custom_retention_expired(
        self, mock_lifecycle_manager, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: Custom retention expires correctly.

        Snapshot with 30-day retention should be deleted at 35 days.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create snapshot with custom 30-day retention that has expired
        snapshot = create_snapshot(
            "snap-custom-expired",
            age_days=35,  # 35 days old
            retention_days=30,  # Custom 30-day retention - EXPIRED
            keep_forever=False,
        )
        snapshot_repository.add_snapshot(snapshot)

        # Execute cleanup
        agent._cleanup_cycle()

        # Verify deleted (35 days > 30 day retention)
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_identified'] == 1
        assert stats['snapshots_deleted'] == 1

        updated = snapshot_repository.get_snapshot("snap-custom-expired")
        assert updated.status == SnapshotStatus.DELETED

    def test_zero_retention_keeps_forever(
        self, mock_lifecycle_manager, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: retention_days=0 means keep indefinitely.

        Zero retention should be treated as "never expire".
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create very old snapshot with retention_days=0
        snapshot = create_snapshot(
            "snap-zero-retention",
            age_days=365,  # 1 year old
            retention_days=0,  # Zero means keep forever
            keep_forever=False,
        )
        snapshot_repository.add_snapshot(snapshot)

        # Execute cleanup
        agent._cleanup_cycle()

        # Verify NOT deleted
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_identified'] == 0
        assert stats['snapshots_deleted'] == 0

        updated = snapshot_repository.get_snapshot("snap-zero-retention")
        assert updated.status == SnapshotStatus.ACTIVE

    def test_instance_retention_override(
        self, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: Instance-level retention overrides global default.
        """
        # Create custom lifecycle manager with instance override
        manager = Mock(spec=SnapshotLifecycleManager)
        global_config = SnapshotLifecycleConfig(
            default_retention_days=7,  # Global: 7 days
            retention=RetentionPolicyConfig(enabled=True),
            cleanup_schedule=CleanupScheduleConfig(enabled=True),
        )
        manager.get_global_config.return_value = global_config
        manager.list_instance_configs.return_value = {}

        def get_instance_config(instance_id):
            if instance_id == "instance-long-retention":
                # Instance with 60-day retention
                config = InstanceSnapshotConfig(
                    instance_id=instance_id,
                    use_global_settings=False,
                    retention_days=60,
                    cleanup_enabled=True,
                )
                return config
            return InstanceSnapshotConfig(
                instance_id=instance_id,
                use_global_settings=True,
            )
        manager.get_instance_config.side_effect = get_instance_config

        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Snapshot on instance with long retention (60 days)
        snap_long = create_snapshot(
            "snap-long-instance",
            age_days=30,  # 30 days old
            instance_id="instance-long-retention",
        )

        # Snapshot on instance with default retention (7 days)
        snap_default = create_snapshot(
            "snap-default-instance",
            age_days=30,  # 30 days old
            instance_id="instance-default",
        )

        snapshot_repository.add_snapshot(snap_long)
        snapshot_repository.add_snapshot(snap_default)

        # Execute cleanup
        agent._cleanup_cycle()

        # snap-long should NOT be deleted (30 < 60 days)
        # snap-default SHOULD be deleted (30 > 7 days)
        assert snapshot_repository.get_snapshot("snap-long-instance").status == SnapshotStatus.ACTIVE
        assert snapshot_repository.get_snapshot("snap-default-instance").status == SnapshotStatus.DELETED


# ============================================================
# E2E Test: Audit Trail
# ============================================================

class TestAuditTrailComplete:
    """
    E2E tests for audit trail completeness.

    Flow:
    1. Run cleanup job with deletions
    2. Query audit log
    3. Verify all deletions logged with required fields
    """

    def test_audit_trail_complete(
        self, mock_lifecycle_manager, snapshot_repository, audit_logger,
        mock_storage_provider
    ):
        """
        E2E test: Complete audit trail with all required metadata.

        Verifies:
        - Cleanup started/completed events
        - Deletion events for each snapshot
        - All required fields populated
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create expired snapshots
        snap1 = create_snapshot("snap-audit-1", age_days=10, size_bytes=1000000)
        snap2 = create_snapshot("snap-audit-2", age_days=12, size_bytes=2000000)
        snap3 = create_snapshot("snap-audit-3", age_days=14, size_bytes=3000000)

        snapshot_repository.add_snapshot(snap1)
        snapshot_repository.add_snapshot(snap2)
        snapshot_repository.add_snapshot(snap3)

        # Start audit tracking
        run_id = audit_logger.log_cleanup_started(
            snapshots_to_process=3,
            metadata={'triggered_by': 'test', 'trigger_type': 'e2e'},
        )

        # Execute cleanup
        agent._cleanup_cycle()
        stats = agent.get_cleanup_stats()

        # Log deletions to audit
        for snap_id in ["snap-audit-1", "snap-audit-2", "snap-audit-3"]:
            snap = snapshot_repository.get_snapshot(snap_id)
            audit_logger.log_deletion(
                snapshot_id=snap.snapshot_id,
                user_id="system",
                deletion_reason="expired",
                storage_freed_bytes=snap.size_bytes,
                instance_id=snap.instance_id,
                storage_provider="b2",
                success=(snap.status == SnapshotStatus.DELETED),
                retention_days=7,
            )

        # Complete audit tracking
        audit_logger.log_cleanup_completed(
            snapshots_deleted=stats['snapshots_deleted'],
            snapshots_failed=stats['snapshots_failed'],
            storage_freed_bytes=stats['storage_freed_bytes'],
        )

        # === VERIFY: Audit entries ===
        entries = audit_logger.get_entries(limit=20)

        # Verify cleanup started
        started_entries = [e for e in entries if e.event_type == AuditEventType.CLEANUP_STARTED]
        assert len(started_entries) == 1
        assert started_entries[0].cleanup_run_id == run_id

        # Verify cleanup completed
        completed_entries = [e for e in entries if e.event_type == AuditEventType.CLEANUP_COMPLETED]
        assert len(completed_entries) == 1
        assert completed_entries[0].storage_freed_bytes == 6000000  # 1 + 2 + 3 MB

        # Verify all deletions logged
        deletion_entries = [e for e in entries if e.event_type == AuditEventType.DELETION]
        assert len(deletion_entries) == 3

        # Verify all required fields on each deletion
        for deletion in deletion_entries:
            assert deletion.snapshot_id != ""
            assert deletion.deletion_reason == "expired"
            assert deletion.storage_freed_bytes > 0
            assert deletion.storage_provider == "b2"
            assert deletion.success is True
            assert deletion.timestamp is not None
            assert deletion.retention_days == 7

        # Verify total storage freed matches
        total_freed = sum(d.storage_freed_bytes for d in deletion_entries)
        assert total_freed == 6000000

    def test_audit_trail_on_failure(
        self, mock_lifecycle_manager, snapshot_repository, audit_logger
    ):
        """
        E2E test: Audit trail captures failures correctly.
        """
        # Provider that fails
        fail_provider = MockStorageProvider(
            provider_name="b2",
            fail_for_paths=["snapshots/instance-1/snap-will-fail"],
        )

        def mock_factory(snapshot):
            return fail_provider

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

        snapshot = create_snapshot("snap-will-fail", age_days=10)
        snapshot_repository.add_snapshot(snapshot)

        # Execute cleanup
        audit_logger.log_cleanup_started(snapshots_to_process=1)
        agent._cleanup_cycle()

        # Log the failure
        updated = snapshot_repository.get_snapshot("snap-will-fail")
        audit_logger.log_deletion(
            snapshot_id=updated.snapshot_id,
            user_id="system",
            deletion_reason="expired",
            storage_freed_bytes=0,
            success=False,
            error_message="Storage deletion failed after retries",
        )

        audit_logger.log_cleanup_completed(
            snapshots_deleted=0,
            snapshots_failed=1,
            storage_freed_bytes=0,
        )

        # Verify failure logged
        entries = audit_logger.get_entries(event_type=AuditEventType.DELETION_FAILED)
        assert len(entries) == 1
        assert entries[0].success is False
        assert entries[0].error_message is not None


# ============================================================
# E2E Test: Metrics Accuracy
# ============================================================

class TestMetricsAccurate:
    """
    E2E tests for metrics tracking accuracy.

    Flow:
    1. Run cleanup job
    2. Query metrics
    3. Verify storage_cleaned and snapshots_deleted accurate
    """

    def test_metrics_accurate(
        self, mock_lifecycle_manager, snapshot_repository, cleanup_metrics,
        mock_storage_provider
    ):
        """
        E2E test: Metrics accurately reflect cleanup operations.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create snapshots with known sizes
        snap1 = create_snapshot("snap-m1", age_days=10, size_bytes=1000000)
        snap2 = create_snapshot("snap-m2", age_days=10, size_bytes=2000000)
        snap3 = create_snapshot("snap-m3", age_days=10, size_bytes=3000000)
        snap4 = create_snapshot("snap-m4", age_days=10, size_bytes=4000000)

        snapshot_repository.add_snapshot(snap1)
        snapshot_repository.add_snapshot(snap2)
        snapshot_repository.add_snapshot(snap3)
        snapshot_repository.add_snapshot(snap4)

        # Execute cleanup
        agent._cleanup_cycle()
        stats = agent.get_cleanup_stats()

        # Record metrics
        cleanup_metrics.record_cleanup(
            snapshots_deleted=stats['snapshots_deleted'],
            storage_freed=stats['storage_freed_bytes'],
            snapshots_failed=stats['snapshots_failed'],
            success=True,
        )

        # === VERIFY: Metrics ===
        assert cleanup_metrics.get_total_snapshots_deleted() == 4
        assert cleanup_metrics.get_total_storage_freed() == 10000000  # 1+2+3+4 MB
        assert cleanup_metrics.get_success_rate() == 1.0

        # Verify today's metrics
        assert cleanup_metrics.get_snapshots_deleted_today() == 4
        assert cleanup_metrics.get_storage_freed_today() == 10000000

    def test_metrics_summary_aggregation(
        self, mock_lifecycle_manager, snapshot_repository, cleanup_metrics,
        mock_storage_provider
    ):
        """
        E2E test: Metrics summary aggregates multiple runs correctly.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

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

        # Clear for run 2
        snapshot_repository.clear()
        mock_storage_provider.operations = []
        mock_storage_provider.deleted_paths = []

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
        assert summary['total_cleanup_runs'] == 2
        assert summary['total_snapshots_deleted'] == 5  # 2 + 3
        assert summary['total_storage_freed'] == 3500000  # 2MB + 1.5MB
        assert summary['success_rate'] == 1.0


# ============================================================
# E2E Test: Manual Cleanup Trigger
# ============================================================

class TestManualCleanupTrigger:
    """
    E2E tests for manual cleanup trigger.

    Tests the trigger_manual_cleanup method.
    """

    def test_manual_cleanup_trigger(
        self, mock_lifecycle_manager, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: Manual cleanup trigger works correctly.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create expired snapshots
        snap1 = create_snapshot("snap-manual-1", age_days=10, size_bytes=1000000)
        snap2 = create_snapshot("snap-manual-2", age_days=10, size_bytes=2000000)
        snapshot_repository.add_snapshot(snap1)
        snapshot_repository.add_snapshot(snap2)

        # Trigger manual cleanup
        stats = agent.trigger_manual_cleanup(dry_run=False)

        # Verify results
        assert stats['snapshots_identified'] == 2
        assert stats['snapshots_deleted'] == 2
        assert stats['storage_freed_bytes'] == 3000000
        assert stats['started_at'] is not None
        assert stats['completed_at'] is not None

    def test_manual_cleanup_dry_run(
        self, mock_lifecycle_manager, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: Manual cleanup with dry_run mode.

        Snapshots should be identified but not deleted.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,  # Agent not in dry_run
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create expired snapshot
        snapshot = create_snapshot("snap-dryrun", age_days=10, size_bytes=5000000)
        snapshot_repository.add_snapshot(snapshot)

        # Trigger manual cleanup with dry_run=True
        stats = agent.trigger_manual_cleanup(dry_run=True)

        # Verify: Identified but not deleted
        assert stats['snapshots_identified'] == 1
        assert stats['snapshots_deleted'] == 1  # dry_run returns True on delete

        # Verify storage was NOT touched
        assert mock_storage_provider.get_delete_count() == 0

        # Verify snapshot still active
        updated = snapshot_repository.get_snapshot("snap-dryrun")
        assert updated.status == SnapshotStatus.ACTIVE


# ============================================================
# E2E Test: Edge Cases
# ============================================================

class TestEdgeCases:
    """
    E2E tests for edge cases and error handling.
    """

    def test_empty_repository(
        self, mock_lifecycle_manager, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: Cleanup handles empty repository gracefully.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Execute on empty repository
        agent._cleanup_cycle()

        stats = agent.get_cleanup_stats()
        assert stats['snapshots_identified'] == 0
        assert stats['snapshots_deleted'] == 0
        assert stats['snapshots_failed'] == 0

    def test_all_snapshots_fresh(
        self, mock_lifecycle_manager, snapshot_repository, mock_storage_provider
    ):
        """
        E2E test: No deletions when all snapshots are fresh.
        """
        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create fresh snapshots (within 7-day retention)
        for i in range(5):
            snap = create_snapshot(f"snap-fresh-{i}", age_days=i)  # 0-4 days old
            snapshot_repository.add_snapshot(snap)

        # Execute cleanup
        agent._cleanup_cycle()

        stats = agent.get_cleanup_stats()
        assert stats['snapshots_identified'] == 0
        assert stats['snapshots_deleted'] == 0

    def test_partial_failure_continues(
        self, mock_lifecycle_manager, snapshot_repository
    ):
        """
        E2E test: Cleanup continues even when some deletions fail.
        """
        # Provider that fails for specific path
        provider = MockStorageProvider(
            provider_name="b2",
            fail_for_paths=["snapshots/instance-1/snap-fail"],
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

        # Create snapshots - one will fail
        snap_ok1 = create_snapshot("snap-ok-1", age_days=10)
        snap_fail = create_snapshot("snap-fail", age_days=10)
        snap_ok2 = create_snapshot("snap-ok-2", age_days=10)

        snapshot_repository.add_snapshot(snap_ok1)
        snapshot_repository.add_snapshot(snap_fail)
        snapshot_repository.add_snapshot(snap_ok2)

        # Execute cleanup
        agent._cleanup_cycle()

        # Verify partial success
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_deleted'] == 2
        assert stats['snapshots_failed'] == 1

        # Verify individual statuses
        assert snapshot_repository.get_snapshot("snap-ok-1").status == SnapshotStatus.DELETED
        assert snapshot_repository.get_snapshot("snap-fail").status == SnapshotStatus.FAILED
        assert snapshot_repository.get_snapshot("snap-ok-2").status == SnapshotStatus.DELETED

    def test_cleanup_disabled(self, snapshot_repository, mock_storage_provider):
        """
        E2E test: Cleanup respects disabled global config.
        """
        # Create lifecycle manager with cleanup disabled
        manager = Mock(spec=SnapshotLifecycleManager)
        global_config = SnapshotLifecycleConfig(
            default_retention_days=7,
            retention=RetentionPolicyConfig(enabled=False),  # Disabled
            cleanup_schedule=CleanupScheduleConfig(enabled=False),  # Disabled
        )
        manager.get_global_config.return_value = global_config

        def mock_factory(snapshot):
            return mock_storage_provider

        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=False,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=manager,
            storage_provider_factory=mock_factory,
        )
        agent.running = True

        # Create expired snapshot
        snapshot = create_snapshot("snap-disabled-test", age_days=100)
        snapshot_repository.add_snapshot(snapshot)

        # Execute cleanup
        agent._cleanup_cycle()

        # Verify nothing deleted (cleanup disabled)
        stats = agent.get_cleanup_stats()
        assert stats['snapshots_identified'] == 0
        assert stats['snapshots_deleted'] == 0

        # Snapshot should still be active
        assert snapshot_repository.get_snapshot("snap-disabled-test").status == SnapshotStatus.ACTIVE


# ============================================================
# Manual Test Runner
# ============================================================

def run_all_tests():
    """Run all E2E tests manually."""
    print("=" * 70)
    print("END-TO-END TESTS - Snapshot Cleanup Workflow")
    print("=" * 70)
    print()

    test_classes = [
        TestExpiredSnapshotDeleted,
        TestKeepForeverProtected,
        TestConfigurableRetention,
        TestAuditTrailComplete,
        TestMetricsAccurate,
        TestManualCleanupTrigger,
        TestEdgeCases,
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

                    # Create fixtures
                    repo = InMemorySnapshotRepository()
                    audit = SnapshotAuditLogger(
                        audit_file_path=os.path.join(tmpdir, "audit.json")
                    )
                    metrics = CleanupMetrics(
                        metrics_file_path=os.path.join(tmpdir, "metrics.json")
                    )
                    storage = MockStorageProvider(provider_name="b2")

                    # Get method parameters
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
                    if 'mock_storage_provider' in params:
                        kwargs['mock_storage_provider'] = storage

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
        print("\nALL E2E TESTS PASSED!")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
