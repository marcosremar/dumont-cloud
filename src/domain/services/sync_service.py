"""
Sync Service - Domain Service for Incremental Synchronization
Manages incremental sync between instances using Restic's deduplication
"""
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock

from .snapshot_service import SnapshotService
from .instance_service import InstanceService

logger = logging.getLogger(__name__)


@dataclass
class SyncStatus:
    """Status of a sync operation"""
    instance_id: int
    last_sync_time: Optional[datetime] = None
    last_snapshot_id: Optional[str] = None
    files_new: int = 0
    files_changed: int = 0
    files_unmodified: int = 0
    data_added_bytes: int = 0
    total_bytes: int = 0
    is_syncing: bool = False
    error: Optional[str] = None
    sync_count: int = 0


@dataclass
class SyncResult:
    """Result of a sync operation"""
    success: bool
    instance_id: int
    snapshot_id: Optional[str] = None
    files_new: int = 0
    files_changed: int = 0
    files_unmodified: int = 0
    data_added_bytes: int = 0
    total_bytes: int = 0
    duration_seconds: float = 0
    is_incremental: bool = True
    error: Optional[str] = None


class SyncService:
    """
    Service for managing incremental synchronization.
    Uses Restic's built-in deduplication for efficient incremental backups.
    """

    # In-memory tracking (could be moved to Redis/DB for persistence)
    _sync_status: Dict[int, SyncStatus] = {}
    _lock = Lock()

    def __init__(
        self,
        snapshot_service: SnapshotService,
        instance_service: InstanceService,
    ):
        self.snapshots = snapshot_service
        self.instances = instance_service

    def sync_instance(
        self,
        instance_id: int,
        source_path: str = "/workspace",
        force: bool = False,
        min_interval_seconds: int = 30,
    ) -> SyncResult:
        """
        Perform incremental sync for an instance.

        Restic automatically handles incremental backup:
        - Only new/changed file chunks are uploaded
        - Deduplication at block level (not file level)
        - Typically 10-100x faster than full backup after first sync

        Args:
            instance_id: Instance to sync
            source_path: Path to sync (default: /workspace)
            force: Force sync even if recently synced
            min_interval_seconds: Minimum interval between syncs

        Returns:
            SyncResult with statistics
        """
        start_time = time.time()

        # Check if already syncing
        with self._lock:
            status = self._sync_status.get(instance_id)
            if status and status.is_syncing:
                return SyncResult(
                    success=False,
                    instance_id=instance_id,
                    error="Sync already in progress",
                )

            # Check minimum interval
            if status and status.last_sync_time and not force:
                elapsed = (datetime.now() - status.last_sync_time).total_seconds()
                if elapsed < min_interval_seconds:
                    return SyncResult(
                        success=False,
                        instance_id=instance_id,
                        error=f"Synced {int(elapsed)}s ago. Wait {int(min_interval_seconds - elapsed)}s or use force=true",
                        is_incremental=True,
                    )

            # Mark as syncing
            if not status:
                status = SyncStatus(instance_id=instance_id)
                self._sync_status[instance_id] = status
            status.is_syncing = True
            status.error = None

        try:
            # Get instance details
            instance = self.instances.get_instance(instance_id)

            if not instance.is_running:
                raise Exception(f"Instance {instance_id} is not running")

            if not instance.ssh_host or not instance.ssh_port:
                raise Exception(f"Instance {instance_id} SSH not available")

            # Determine if this is first sync or incremental
            is_first_sync = status.last_snapshot_id is None

            logger.info(
                f"[Sync] Starting {'initial' if is_first_sync else 'incremental'} sync "
                f"for instance {instance_id}"
            )

            # Create snapshot (Restic handles incremental automatically)
            tags = [
                f"instance-{instance_id}",
                "auto-sync",
                f"sync-{status.sync_count + 1}",
            ]

            result = self.snapshots.create_snapshot(
                ssh_host=instance.ssh_host,
                ssh_port=instance.ssh_port,
                source_path=source_path,
                tags=tags,
            )

            duration = time.time() - start_time

            # Update status
            with self._lock:
                status.last_sync_time = datetime.now()
                status.last_snapshot_id = result.get("snapshot_id")
                status.files_new = result.get("files_new", 0)
                status.files_changed = result.get("files_changed", 0)
                status.files_unmodified = result.get("files_unmodified", 0)
                status.data_added_bytes = result.get("data_added", 0)
                status.total_bytes = result.get("total_bytes_processed", 0)
                status.is_syncing = False
                status.sync_count += 1

            # Calculate if truly incremental (most files unmodified)
            total_files = status.files_new + status.files_changed + status.files_unmodified
            is_incremental = (
                total_files > 0 and
                status.files_unmodified / total_files > 0.5
            ) if total_files > 0 else not is_first_sync

            logger.info(
                f"[Sync] Completed in {duration:.1f}s - "
                f"New: {status.files_new}, Changed: {status.files_changed}, "
                f"Unchanged: {status.files_unmodified}, Data added: {self._format_bytes(status.data_added_bytes)}"
            )

            return SyncResult(
                success=True,
                instance_id=instance_id,
                snapshot_id=status.last_snapshot_id,
                files_new=status.files_new,
                files_changed=status.files_changed,
                files_unmodified=status.files_unmodified,
                data_added_bytes=status.data_added_bytes,
                total_bytes=status.total_bytes,
                duration_seconds=duration,
                is_incremental=is_incremental,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[Sync] Failed for instance {instance_id}: {e}")

            with self._lock:
                status.is_syncing = False
                status.error = str(e)

            return SyncResult(
                success=False,
                instance_id=instance_id,
                error=str(e),
                duration_seconds=duration,
            )

    def get_sync_status(self, instance_id: int) -> Optional[SyncStatus]:
        """Get current sync status for an instance"""
        with self._lock:
            return self._sync_status.get(instance_id)

    def get_all_sync_status(self) -> Dict[int, SyncStatus]:
        """Get sync status for all tracked instances"""
        with self._lock:
            return dict(self._sync_status)

    def clear_sync_status(self, instance_id: int) -> bool:
        """Clear sync status for an instance (e.g., when destroyed)"""
        with self._lock:
            if instance_id in self._sync_status:
                del self._sync_status[instance_id]
                return True
            return False

    def get_sync_stats(self, instance_id: int) -> Dict[str, Any]:
        """Get detailed sync statistics for an instance"""
        status = self.get_sync_status(instance_id)

        if not status:
            return {
                "instance_id": instance_id,
                "synced": False,
                "message": "Never synced",
            }

        # Calculate time since last sync
        if status.last_sync_time:
            elapsed = datetime.now() - status.last_sync_time
            elapsed_str = self._format_duration(elapsed.total_seconds())
        else:
            elapsed_str = "Never"

        return {
            "instance_id": instance_id,
            "synced": status.last_snapshot_id is not None,
            "is_syncing": status.is_syncing,
            "last_sync": status.last_sync_time.isoformat() if status.last_sync_time else None,
            "last_sync_ago": elapsed_str,
            "last_snapshot_id": status.last_snapshot_id,
            "sync_count": status.sync_count,
            "last_stats": {
                "files_new": status.files_new,
                "files_changed": status.files_changed,
                "files_unmodified": status.files_unmodified,
                "data_added": self._format_bytes(status.data_added_bytes),
                "data_added_bytes": status.data_added_bytes,
            },
            "error": status.error,
        }

    @staticmethod
    def _format_bytes(bytes_count: int) -> str:
        """Format bytes to human readable string"""
        if bytes_count < 1024:
            return f"{bytes_count} B"
        elif bytes_count < 1024 * 1024:
            return f"{bytes_count / 1024:.1f} KB"
        elif bytes_count < 1024 * 1024 * 1024:
            return f"{bytes_count / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration to human readable string"""
        if seconds < 60:
            return f"{int(seconds)}s ago"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds / 3600)}h ago"
        else:
            return f"{int(seconds / 86400)}d ago"
