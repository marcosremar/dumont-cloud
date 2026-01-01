"""
Metrics tracking for snapshot cleanup operations.

Tracks and persists cleanup operation metrics:
- snapshots_deleted: Number of snapshots deleted
- storage_freed: Storage freed in bytes
- cleanup_runs: Number of cleanup runs
- success_rate: Percentage of successful deletions

Metrics persist in JSON format for querying and reporting.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class CleanupRunMetrics:
    """
    Metrics for a single cleanup run.

    Stores detailed statistics about a cleanup operation
    for tracking and reporting purposes.
    """
    # Identification
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Cleanup statistics
    snapshots_deleted: int = 0
    snapshots_failed: int = 0
    snapshots_skipped: int = 0  # Skipped due to keep_forever or not expired

    # Storage metrics
    storage_freed: int = 0  # Bytes freed
    storage_scanned: int = 0  # Total bytes scanned

    # Timing
    duration_seconds: float = 0.0

    # Status
    success: bool = True
    error_message: Optional[str] = None

    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CleanupRunMetrics':
        """Create instance from dictionary."""
        return cls(
            run_id=data.get('run_id', str(uuid.uuid4())),
            timestamp=data.get('timestamp', datetime.now(timezone.utc).isoformat()),
            snapshots_deleted=data.get('snapshots_deleted', 0),
            snapshots_failed=data.get('snapshots_failed', 0),
            snapshots_skipped=data.get('snapshots_skipped', 0),
            storage_freed=data.get('storage_freed', 0),
            storage_scanned=data.get('storage_scanned', 0),
            duration_seconds=data.get('duration_seconds', 0.0),
            success=data.get('success', True),
            error_message=data.get('error_message'),
            metadata=data.get('metadata', {}),
        )

    def __repr__(self):
        return (f"<CleanupRunMetrics {self.run_id[:8]}... "
                f"deleted={self.snapshots_deleted} freed={self.storage_freed} bytes>")


class CleanupMetrics:
    """
    Service for tracking snapshot cleanup metrics.

    Provides methods to record cleanup operations and query
    aggregate metrics over time. Data persists to JSON file.
    """

    DEFAULT_METRICS_FILE = "snapshot_cleanup_metrics.json"

    def __init__(
        self,
        metrics_file_path: Optional[str] = None,
        max_entries: int = 10000,
    ):
        """
        Initialize the cleanup metrics service.

        Args:
            metrics_file_path: Path to the metrics file.
                              If None, uses default directory.
            max_entries: Maximum number of entries to retain (FIFO).
        """
        self._metrics_file_path = metrics_file_path
        self.max_entries = max_entries
        self._entries: List[CleanupRunMetrics] = []
        self._loaded = False

    @property
    def metrics_file_path(self) -> str:
        """Return the metrics file path."""
        if self._metrics_file_path:
            return self._metrics_file_path

        # Default directory: ~/.dumont/metrics/
        home_dir = Path.home()
        metrics_dir = home_dir / ".dumont" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        return str(metrics_dir / self.DEFAULT_METRICS_FILE)

    def _ensure_loaded(self) -> None:
        """Load entries from file if not already loaded."""
        if self._loaded:
            return

        try:
            if os.path.exists(self.metrics_file_path):
                with open(self.metrics_file_path, 'r') as f:
                    data = json.load(f)
                    entries_data = data.get('entries', [])
                    self._entries = [
                        CleanupRunMetrics.from_dict(e)
                        for e in entries_data
                    ]
                    logger.debug(f"Loaded {len(self._entries)} cleanup metrics entries")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading metrics file: {e}")
            self._entries = []

        self._loaded = True

    def _save(self) -> None:
        """Persist entries to the metrics file."""
        try:
            # Ensure directory exists
            metrics_dir = Path(self.metrics_file_path).parent
            metrics_dir.mkdir(parents=True, exist_ok=True)

            # Apply maximum entry limit
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries:]

            data = {
                'version': '1.0',
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'entry_count': len(self._entries),
                'entries': [e.to_dict() for e in self._entries],
            }

            with open(self.metrics_file_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._entries)} cleanup metrics entries")

        except IOError as e:
            logger.error(f"Error saving metrics file: {e}")

    def record_cleanup(
        self,
        snapshots_deleted: int = 0,
        storage_freed: int = 0,
        snapshots_failed: int = 0,
        snapshots_skipped: int = 0,
        storage_scanned: int = 0,
        duration_seconds: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CleanupRunMetrics:
        """
        Record a cleanup operation.

        Args:
            snapshots_deleted: Number of snapshots successfully deleted
            storage_freed: Bytes freed by deletion
            snapshots_failed: Number of deletions that failed
            snapshots_skipped: Number of snapshots skipped
            storage_scanned: Total bytes scanned during cleanup
            duration_seconds: Duration of cleanup operation
            success: Whether the overall operation succeeded
            error_message: Error message if operation failed
            metadata: Additional context information

        Returns:
            CleanupRunMetrics entry created
        """
        self._ensure_loaded()

        entry = CleanupRunMetrics(
            snapshots_deleted=snapshots_deleted,
            snapshots_failed=snapshots_failed,
            snapshots_skipped=snapshots_skipped,
            storage_freed=storage_freed,
            storage_scanned=storage_scanned,
            duration_seconds=duration_seconds,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )

        self._entries.append(entry)
        self._save()

        logger.info(
            f"Cleanup metrics recorded: deleted={snapshots_deleted}, "
            f"freed={storage_freed} bytes, failed={snapshots_failed}"
        )

        return entry

    def get_total_storage_freed(self, days: Optional[int] = None) -> int:
        """
        Get total storage freed across all cleanup runs.

        Args:
            days: If specified, only count last N days.
                  If None, count all time.

        Returns:
            Total bytes freed
        """
        self._ensure_loaded()

        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_iso = cutoff.isoformat()
            return sum(
                e.storage_freed for e in self._entries
                if e.success and e.timestamp >= cutoff_iso
            )

        return sum(e.storage_freed for e in self._entries if e.success)

    def get_total_snapshots_deleted(self, days: Optional[int] = None) -> int:
        """
        Get total number of snapshots deleted across all runs.

        Args:
            days: If specified, only count last N days.
                  If None, count all time.

        Returns:
            Total snapshots deleted
        """
        self._ensure_loaded()

        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_iso = cutoff.isoformat()
            return sum(
                e.snapshots_deleted for e in self._entries
                if e.timestamp >= cutoff_iso
            )

        return sum(e.snapshots_deleted for e in self._entries)

    def get_total_cleanup_runs(self, days: Optional[int] = None) -> int:
        """
        Get total number of cleanup runs.

        Args:
            days: If specified, only count last N days.
                  If None, count all time.

        Returns:
            Total cleanup runs
        """
        self._ensure_loaded()

        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_iso = cutoff.isoformat()
            return sum(1 for e in self._entries if e.timestamp >= cutoff_iso)

        return len(self._entries)

    def get_success_rate(self, days: Optional[int] = None) -> float:
        """
        Calculate the success rate of cleanup operations.

        Args:
            days: If specified, only consider last N days.
                  If None, consider all time.

        Returns:
            Success rate as a float between 0.0 and 1.0
        """
        self._ensure_loaded()

        entries = self._entries
        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_iso = cutoff.isoformat()
            entries = [e for e in entries if e.timestamp >= cutoff_iso]

        if not entries:
            return 1.0  # No failures means 100% success

        successful = sum(1 for e in entries if e.success)
        return successful / len(entries)

    def get_storage_freed_today(self) -> int:
        """
        Get storage freed today.

        Returns:
            Bytes freed today
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_iso = today_start.isoformat()

        self._ensure_loaded()

        return sum(
            e.storage_freed for e in self._entries
            if e.success and e.timestamp >= today_iso
        )

    def get_snapshots_deleted_today(self) -> int:
        """
        Get number of snapshots deleted today.

        Returns:
            Snapshots deleted today
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_iso = today_start.isoformat()

        self._ensure_loaded()

        return sum(
            e.snapshots_deleted for e in self._entries
            if e.timestamp >= today_iso
        )

    def get_entries(
        self,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success_only: bool = False,
    ) -> List[CleanupRunMetrics]:
        """
        Query cleanup run entries.

        Args:
            limit: Maximum entries to return
            offset: Offset for pagination
            start_date: Filter by start date (UTC)
            end_date: Filter by end date (UTC)
            success_only: Only return successful runs

        Returns:
            List of CleanupRunMetrics entries
        """
        self._ensure_loaded()

        filtered = self._entries.copy()

        if success_only:
            filtered = [e for e in filtered if e.success]

        if start_date:
            start_iso = start_date.isoformat()
            filtered = [e for e in filtered if e.timestamp >= start_iso]

        if end_date:
            end_iso = end_date.isoformat()
            filtered = [e for e in filtered if e.timestamp <= end_iso]

        # Sort by timestamp descending (most recent first)
        filtered.sort(key=lambda e: e.timestamp, reverse=True)

        return filtered[offset:offset + limit]

    def get_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get a summary of cleanup metrics.

        Args:
            days: Number of days to include in summary

        Returns:
            Dictionary with summary statistics
        """
        self._ensure_loaded()

        return {
            'total_storage_freed': self.get_total_storage_freed(days=days),
            'total_storage_freed_all_time': self.get_total_storage_freed(),
            'total_snapshots_deleted': self.get_total_snapshots_deleted(days=days),
            'total_cleanup_runs': self.get_total_cleanup_runs(days=days),
            'success_rate': self.get_success_rate(days=days),
            'storage_freed_today': self.get_storage_freed_today(),
            'snapshots_deleted_today': self.get_snapshots_deleted_today(),
            'period_days': days,
        }

    def clear(self) -> None:
        """Clear all metrics entries (for testing)."""
        self._entries = []
        self._loaded = True
        self._save()


# Singleton global instance
_cleanup_metrics: Optional[CleanupMetrics] = None


def get_cleanup_metrics() -> CleanupMetrics:
    """
    Get the global cleanup metrics instance.

    Returns:
        CleanupMetrics singleton
    """
    global _cleanup_metrics
    if _cleanup_metrics is None:
        _cleanup_metrics = CleanupMetrics()
    return _cleanup_metrics
