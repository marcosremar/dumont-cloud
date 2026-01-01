"""
Database model for snapshot scheduling configuration.

Stores per-instance snapshot scheduling settings including interval,
enabled status, and scheduling timestamps.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index, ForeignKey

from src.config.database import Base


class SnapshotConfig(Base):
    """
    Snapshot scheduling configuration per instance.

    Stores the snapshot interval and scheduling state for each instance.
    Used by the SnapshotScheduler to determine when to trigger snapshots.
    """
    __tablename__ = "snapshot_configs"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(String(100), unique=True, nullable=False, index=True)

    # Scheduling configuration
    interval_minutes = Column(Integer, nullable=False, default=15)  # Default: 15 minutes
    enabled = Column(Boolean, nullable=False, default=True)

    # Scheduling state
    next_snapshot_at = Column(DateTime, nullable=True)  # When next snapshot is scheduled
    last_snapshot_at = Column(DateTime, nullable=True)  # When last snapshot was taken

    # Last snapshot result
    last_snapshot_status = Column(String(20), nullable=True)  # success, failure, in_progress
    last_snapshot_error = Column(String(500), nullable=True)  # Error message if failed
    consecutive_failures = Column(Integer, nullable=False, default=0)  # For circuit breaker

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_snapshot_config_enabled', 'enabled', 'next_snapshot_at'),
        Index('idx_snapshot_config_status', 'last_snapshot_status'),
    )

    def __repr__(self):
        status = "enabled" if self.enabled else "disabled"
        return f"<SnapshotConfig(instance={self.instance_id}, interval={self.interval_minutes}min, {status})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'instance_id': self.instance_id,
            'interval_minutes': self.interval_minutes,
            'enabled': self.enabled,
            'next_snapshot_at': self.next_snapshot_at.isoformat() if self.next_snapshot_at else None,
            'last_snapshot_at': self.last_snapshot_at.isoformat() if self.last_snapshot_at else None,
            'last_snapshot_status': self.last_snapshot_status,
            'last_snapshot_error': self.last_snapshot_error,
            'consecutive_failures': self.consecutive_failures,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def is_overdue(self) -> bool:
        """
        Check if the snapshot is overdue.

        A snapshot is considered overdue if:
        - It's enabled and last_snapshot_at exists
        - Current time > last_snapshot_at + (2 * interval_minutes)
        """
        if not self.enabled or not self.last_snapshot_at:
            return False

        from datetime import timedelta
        overdue_threshold = self.last_snapshot_at + timedelta(minutes=self.interval_minutes * 2)
        return datetime.utcnow() > overdue_threshold

    @property
    def status(self) -> str:
        """
        Get the current snapshot status.

        Returns:
            'success' - Last snapshot was successful
            'failure' - Last snapshot failed
            'overdue' - Snapshot is overdue (> 2x interval elapsed)
            'pending' - No snapshot taken yet
            'disabled' - Snapshots are disabled for this instance
        """
        if not self.enabled:
            return 'disabled'
        if self.is_overdue:
            return 'overdue'
        if self.last_snapshot_status:
            return self.last_snapshot_status
        return 'pending'
