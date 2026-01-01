"""
Snapshot Metrics - Prometheus metrics for snapshot operations in Dumont Cloud
Exposes metrics for monitoring snapshot success/failure, duration, and timestamps
"""

import logging
from typing import Optional
from datetime import datetime

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)


class SnapshotMetrics:
    """
    Prometheus metrics service for snapshot operations.

    Exposes the following metrics:
    - snapshot_success_total: Counter of successful snapshots by instance
    - snapshot_failure_total: Counter of failed snapshots by instance
    - snapshot_duration_seconds: Histogram of snapshot duration by instance
    - snapshot_last_timestamp: Gauge of last successful snapshot timestamp by instance
    - snapshot_in_progress: Gauge of currently running snapshots by instance
    - snapshot_size_bytes: Gauge of last snapshot size by instance
    - snapshot_consecutive_failures: Gauge of consecutive failures by instance
    """

    # Metric name prefix for Dumont Cloud
    METRIC_PREFIX = "dumont_snapshot"

    # Histogram buckets for snapshot duration (in seconds)
    # Covers from 1 second to 10 minutes
    DURATION_BUCKETS = (1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize SnapshotMetrics.

        Args:
            registry: Optional Prometheus registry. Uses default if not provided.
        """
        self._registry = registry or REGISTRY

        # Success counter
        self.success_total = Counter(
            f"{self.METRIC_PREFIX}_success_total",
            "Total number of successful snapshots",
            labelnames=["instance_id"],
            registry=self._registry,
        )

        # Failure counter
        self.failure_total = Counter(
            f"{self.METRIC_PREFIX}_failure_total",
            "Total number of failed snapshots",
            labelnames=["instance_id"],
            registry=self._registry,
        )

        # Duration histogram
        self.duration_seconds = Histogram(
            f"{self.METRIC_PREFIX}_duration_seconds",
            "Snapshot duration in seconds",
            labelnames=["instance_id"],
            buckets=self.DURATION_BUCKETS,
            registry=self._registry,
        )

        # Last snapshot timestamp (Unix timestamp)
        self.last_timestamp = Gauge(
            f"{self.METRIC_PREFIX}_last_timestamp",
            "Unix timestamp of the last successful snapshot",
            labelnames=["instance_id"],
            registry=self._registry,
        )

        # Currently running snapshots
        self.in_progress = Gauge(
            f"{self.METRIC_PREFIX}_in_progress",
            "Number of snapshots currently in progress (0 or 1)",
            labelnames=["instance_id"],
            registry=self._registry,
        )

        # Last snapshot size in bytes
        self.size_bytes = Gauge(
            f"{self.METRIC_PREFIX}_size_bytes",
            "Size of the last snapshot in bytes",
            labelnames=["instance_id"],
            registry=self._registry,
        )

        # Consecutive failures counter (for circuit breaker monitoring)
        self.consecutive_failures = Gauge(
            f"{self.METRIC_PREFIX}_consecutive_failures",
            "Number of consecutive snapshot failures",
            labelnames=["instance_id"],
            registry=self._registry,
        )

        # Scheduler status (1 = running, 0 = stopped)
        self.scheduler_running = Gauge(
            f"{self.METRIC_PREFIX}_scheduler_running",
            "Indicates if the snapshot scheduler is running (1) or stopped (0)",
            registry=self._registry,
        )

        # Total instances being monitored
        self.instances_total = Gauge(
            f"{self.METRIC_PREFIX}_instances_total",
            "Total number of instances registered for snapshots",
            registry=self._registry,
        )

        # Overdue instances count
        self.instances_overdue = Gauge(
            f"{self.METRIC_PREFIX}_instances_overdue",
            "Number of instances with overdue snapshots",
            registry=self._registry,
        )

        logger.info("SnapshotMetrics initialized")

    def record_success(
        self,
        instance_id: str,
        duration_seconds: float,
        size_bytes: Optional[int] = None,
    ) -> None:
        """
        Record a successful snapshot.

        Args:
            instance_id: Unique identifier of the instance
            duration_seconds: Time taken for the snapshot in seconds
            size_bytes: Optional size of the snapshot in bytes
        """
        self.success_total.labels(instance_id=instance_id).inc()
        self.duration_seconds.labels(instance_id=instance_id).observe(duration_seconds)
        self.last_timestamp.labels(instance_id=instance_id).set_to_current_time()
        self.consecutive_failures.labels(instance_id=instance_id).set(0)

        if size_bytes is not None:
            self.size_bytes.labels(instance_id=instance_id).set(size_bytes)

        logger.debug(
            f"Recorded successful snapshot for {instance_id}: "
            f"duration={duration_seconds:.2f}s, size={size_bytes or 'N/A'}"
        )

    def record_failure(
        self,
        instance_id: str,
        duration_seconds: float,
        consecutive_count: int = 1,
    ) -> None:
        """
        Record a failed snapshot.

        Args:
            instance_id: Unique identifier of the instance
            duration_seconds: Time taken before failure in seconds
            consecutive_count: Number of consecutive failures
        """
        self.failure_total.labels(instance_id=instance_id).inc()
        self.duration_seconds.labels(instance_id=instance_id).observe(duration_seconds)
        self.consecutive_failures.labels(instance_id=instance_id).set(consecutive_count)

        logger.debug(
            f"Recorded failed snapshot for {instance_id}: "
            f"duration={duration_seconds:.2f}s, consecutive_failures={consecutive_count}"
        )

    def set_in_progress(self, instance_id: str, in_progress: bool) -> None:
        """
        Set snapshot in-progress status.

        Args:
            instance_id: Unique identifier of the instance
            in_progress: True if snapshot is running, False otherwise
        """
        self.in_progress.labels(instance_id=instance_id).set(1 if in_progress else 0)

    def set_last_timestamp(self, instance_id: str, timestamp: float) -> None:
        """
        Set last snapshot timestamp manually.

        Args:
            instance_id: Unique identifier of the instance
            timestamp: Unix timestamp of the last snapshot
        """
        self.last_timestamp.labels(instance_id=instance_id).set(timestamp)

    def update_scheduler_status(
        self,
        running: bool,
        total_instances: int = 0,
        overdue_instances: int = 0,
    ) -> None:
        """
        Update scheduler status metrics.

        Args:
            running: Whether the scheduler is running
            total_instances: Total number of registered instances
            overdue_instances: Number of instances with overdue snapshots
        """
        self.scheduler_running.set(1 if running else 0)
        self.instances_total.set(total_instances)
        self.instances_overdue.set(overdue_instances)

    def clear_instance(self, instance_id: str) -> None:
        """
        Clear metrics for a specific instance.

        Called when an instance is removed from monitoring.

        Args:
            instance_id: Unique identifier of the instance
        """
        try:
            # Remove labels for this instance
            self.success_total.remove(instance_id)
            self.failure_total.remove(instance_id)
            self.duration_seconds.remove(instance_id)
            self.last_timestamp.remove(instance_id)
            self.in_progress.remove(instance_id)
            self.size_bytes.remove(instance_id)
            self.consecutive_failures.remove(instance_id)
            logger.debug(f"Cleared metrics for instance {instance_id}")
        except KeyError:
            # Label not found, ok to ignore
            pass


# Singleton instance
_snapshot_metrics: Optional[SnapshotMetrics] = None


def get_snapshot_metrics(
    registry: Optional[CollectorRegistry] = None,
) -> SnapshotMetrics:
    """
    Return singleton instance of SnapshotMetrics.

    Args:
        registry: Optional Prometheus registry. Uses default if not provided.
                  Only used on first call when creating the singleton.

    Returns:
        SnapshotMetrics singleton instance
    """
    global _snapshot_metrics

    if _snapshot_metrics is None:
        _snapshot_metrics = SnapshotMetrics(registry=registry)

    return _snapshot_metrics


def reset_snapshot_metrics() -> None:
    """
    Reset the singleton instance.

    Useful for testing to ensure a clean state.
    """
    global _snapshot_metrics
    _snapshot_metrics = None


if __name__ == "__main__":
    # Example usage
    import time
    from prometheus_client import generate_latest

    logging.basicConfig(level=logging.DEBUG)

    print("\nTesting SnapshotMetrics...\n")

    # Create metrics
    metrics = SnapshotMetrics()

    # Simulate snapshots
    print("1. Simulating successful snapshot for instance-001...")
    metrics.set_in_progress("instance-001", True)
    time.sleep(0.1)  # Simulate work
    metrics.set_in_progress("instance-001", False)
    metrics.record_success("instance-001", duration_seconds=2.5, size_bytes=1024000)

    print("2. Simulating failed snapshot for instance-002...")
    metrics.set_in_progress("instance-002", True)
    time.sleep(0.05)
    metrics.set_in_progress("instance-002", False)
    metrics.record_failure("instance-002", duration_seconds=1.0, consecutive_count=1)

    print("3. Updating scheduler status...")
    metrics.update_scheduler_status(running=True, total_instances=2, overdue_instances=0)

    print("\n4. Generated Prometheus metrics:\n")
    output = generate_latest(REGISTRY).decode("utf-8")

    # Print only snapshot-related metrics
    for line in output.split("\n"):
        if "dumont_snapshot" in line:
            print(line)

    print("\nTest completed!")
