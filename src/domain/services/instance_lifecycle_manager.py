"""
Instance Lifecycle Manager - Centralized service for all instance status changes.

CRITICAL: All instance status changes (destroy, pause, resume, hibernate, wake)
MUST go through this service to ensure proper audit logging.

This service:
1. Logs all status changes with full audit trail (who, what, when, why)
2. Provides a single point of control for instance lifecycle
3. Enables tracking and debugging of instance status changes

Usage:
    lifecycle_manager = InstanceLifecycleManager(gpu_provider, db_session, user_id)

    # Destroy with audit
    await lifecycle_manager.destroy_instance(
        instance_id=12345,
        reason="User requested manual destruction",
        caller_source=CallerSource.API_USER,
    )

    # Pause with audit
    await lifecycle_manager.pause_instance(
        instance_id=12345,
        reason="GPU idle for 3 minutes",
        caller_source=CallerSource.AUTO_HIBERNATION,
    )
"""

import json
import logging
import inspect
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from ..repositories import IGpuProvider
from ..models import Instance
from ...models.lifecycle_event import (
    InstanceLifecycleEvent,
    LifecycleAction,
    CallerSource,
)

logger = logging.getLogger(__name__)


class InstanceLifecycleManager:
    """
    Centralized manager for all instance lifecycle operations.

    All destroy/pause/resume operations MUST go through this service
    to ensure proper audit logging and tracking.
    """

    def __init__(
        self,
        gpu_provider: IGpuProvider,
        db_session: Optional[Session] = None,
        user_id: str = "unknown",
    ):
        """
        Initialize lifecycle manager.

        Args:
            gpu_provider: GPU provider implementation (vast.ai, etc)
            db_session: SQLAlchemy session for audit logging (optional, but recommended)
            user_id: User email for audit trail
        """
        self.gpu_provider = gpu_provider
        self.db_session = db_session
        self.user_id = user_id

    def _get_caller_info(self) -> tuple[str, str, str, int]:
        """
        Get information about who called this method.

        Returns:
            Tuple of (function_name, module_name, file_path, line_number)
        """
        # Walk up the call stack to find the external caller
        stack = inspect.stack()
        for frame_info in stack[2:]:  # Skip _get_caller_info and the direct caller
            module = frame_info.frame.f_globals.get('__name__', 'unknown')
            # Skip internal calls
            if 'instance_lifecycle_manager' not in module:
                return (
                    frame_info.function,
                    module,
                    frame_info.filename,
                    frame_info.lineno,
                )
        return 'unknown', 'unknown', 'unknown', 0

    def _log_event(
        self,
        instance_id: int,
        action: LifecycleAction,
        reason: str,
        caller_source: CallerSource,
        success: bool = True,
        instance: Optional[Instance] = None,
        previous_status: Optional[str] = None,
        new_status: Optional[str] = None,
        reason_details: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[InstanceLifecycleEvent]:
        """
        Log a lifecycle event to the database.

        Args:
            instance_id: Instance ID
            action: The action being performed
            reason: Why this action is being performed
            caller_source: Who initiated this action
            success: Whether the action succeeded
            instance: Optional instance object for context
            previous_status: Status before the action
            new_status: Status after the action
            reason_details: Additional details about the reason
            snapshot_id: Snapshot ID if applicable
            metadata: Additional metadata as dict

        Returns:
            The created event, or None if no db session
        """
        # Get caller info
        caller_function, caller_module, caller_file_path, caller_line_number = self._get_caller_info()

        # Build event
        event = InstanceLifecycleEvent(
            instance_id=instance_id,
            instance_label=instance.label if instance else None,
            user_id=self.user_id,
            action=action.value,
            previous_status=previous_status,
            new_status=new_status,
            success=success,
            caller_source=caller_source.value,
            caller_function=caller_function,
            caller_module=caller_module,
            caller_file_path=caller_file_path,
            caller_line_number=caller_line_number,
            reason=reason,
            reason_details=reason_details,
            gpu_type=instance.gpu_name if instance else None,
            dph_total=instance.dph_total if instance else None,
            gpu_utilization=instance.gpu_util if instance else None,
            ssh_host=instance.ssh_host if instance else None,
            ssh_port=instance.ssh_port if instance else None,
            snapshot_id=snapshot_id,
            metadata_json=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow(),
        )

        # Log to Python logger
        log_level = logging.INFO if success else logging.ERROR
        logger.log(
            log_level,
            f"[LIFECYCLE] action={action.value} instance={instance_id} "
            f"caller={caller_source.value} reason=\"{reason}\" "
            f"success={success} user={self.user_id} "
            f"function={caller_function} module={caller_module} "
            f"file={caller_file_path}:{caller_line_number}"
        )

        # Save to database if session available
        if self.db_session:
            try:
                self.db_session.add(event)
                self.db_session.commit()
                return event
            except Exception as e:
                logger.error(f"Failed to log lifecycle event to DB: {e}")
                self.db_session.rollback()

        return event

    def destroy_instance(
        self,
        instance_id: int,
        reason: str,
        caller_source: CallerSource = CallerSource.UNKNOWN,
        reason_details: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Destroy an instance with full audit logging.

        Args:
            instance_id: Instance ID to destroy
            reason: REQUIRED - Why is this instance being destroyed?
            caller_source: Who initiated this destruction
            reason_details: Additional details about the reason
            snapshot_id: Snapshot ID if one was created before destruction
            metadata: Additional metadata to log

        Returns:
            True if successful, False otherwise
        """
        # Try to get instance info before destroying
        instance = None
        previous_status = None
        try:
            instance = self.gpu_provider.get_instance(instance_id)
            previous_status = instance.actual_status if instance else None
        except Exception:
            pass

        # Perform the destruction
        try:
            success = self.gpu_provider.destroy_instance(instance_id)
        except Exception as e:
            # Log the failure
            self._log_event(
                instance_id=instance_id,
                action=LifecycleAction.DESTROY,
                reason=reason,
                caller_source=caller_source,
                success=False,
                instance=instance,
                previous_status=previous_status,
                new_status="error",
                reason_details=f"Error: {str(e)}. Original details: {reason_details}",
                snapshot_id=snapshot_id,
                metadata=metadata,
            )
            raise

        # Log the event
        self._log_event(
            instance_id=instance_id,
            action=LifecycleAction.DESTROY,
            reason=reason,
            caller_source=caller_source,
            success=success,
            instance=instance,
            previous_status=previous_status,
            new_status="destroyed" if success else "error",
            reason_details=reason_details,
            snapshot_id=snapshot_id,
            metadata=metadata,
        )

        return success

    def pause_instance(
        self,
        instance_id: int,
        reason: str,
        caller_source: CallerSource = CallerSource.UNKNOWN,
        reason_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Pause an instance with full audit logging.

        Args:
            instance_id: Instance ID to pause
            reason: REQUIRED - Why is this instance being paused?
            caller_source: Who initiated this pause
            reason_details: Additional details about the reason
            metadata: Additional metadata to log

        Returns:
            True if successful, False otherwise
        """
        # Try to get instance info before pausing
        instance = None
        previous_status = None
        try:
            instance = self.gpu_provider.get_instance(instance_id)
            previous_status = instance.actual_status if instance else None
        except Exception:
            pass

        # Perform the pause
        try:
            success = self.gpu_provider.pause_instance(instance_id)
        except Exception as e:
            self._log_event(
                instance_id=instance_id,
                action=LifecycleAction.PAUSE,
                reason=reason,
                caller_source=caller_source,
                success=False,
                instance=instance,
                previous_status=previous_status,
                new_status="error",
                reason_details=f"Error: {str(e)}. Original details: {reason_details}",
                metadata=metadata,
            )
            raise

        # Log the event
        self._log_event(
            instance_id=instance_id,
            action=LifecycleAction.PAUSE,
            reason=reason,
            caller_source=caller_source,
            success=success,
            instance=instance,
            previous_status=previous_status,
            new_status="paused" if success else "error",
            reason_details=reason_details,
            metadata=metadata,
        )

        return success

    def resume_instance(
        self,
        instance_id: int,
        reason: str,
        caller_source: CallerSource = CallerSource.UNKNOWN,
        reason_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Resume a paused instance with full audit logging.

        Args:
            instance_id: Instance ID to resume
            reason: REQUIRED - Why is this instance being resumed?
            caller_source: Who initiated this resume
            reason_details: Additional details about the reason
            metadata: Additional metadata to log

        Returns:
            True if successful, False otherwise
        """
        # Try to get instance info before resuming
        instance = None
        previous_status = None
        try:
            instance = self.gpu_provider.get_instance(instance_id)
            previous_status = instance.actual_status if instance else None
        except Exception:
            pass

        # Perform the resume
        try:
            success = self.gpu_provider.resume_instance(instance_id)
        except Exception as e:
            self._log_event(
                instance_id=instance_id,
                action=LifecycleAction.RESUME,
                reason=reason,
                caller_source=caller_source,
                success=False,
                instance=instance,
                previous_status=previous_status,
                new_status="error",
                reason_details=f"Error: {str(e)}. Original details: {reason_details}",
                metadata=metadata,
            )
            raise

        # Log the event
        self._log_event(
            instance_id=instance_id,
            action=LifecycleAction.RESUME,
            reason=reason,
            caller_source=caller_source,
            success=success,
            instance=instance,
            previous_status=previous_status,
            new_status="running" if success else "error",
            reason_details=reason_details,
            metadata=metadata,
        )

        return success

    def create_instance(
        self,
        offer_id: int,
        image: str,
        disk_size: float,
        reason: str,
        caller_source: CallerSource = CallerSource.UNKNOWN,
        label: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        onstart_cmd: Optional[str] = None,
        docker_args: Optional[List[str]] = None,
        reason_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Instance:
        """
        Create an instance with full audit logging.

        Args:
            offer_id: GPU offer ID to create instance from
            image: Docker image to use
            disk_size: Disk size in GB
            reason: REQUIRED - Why is this instance being created?
            caller_source: Who initiated this creation
            label: Optional label for the instance
            env_vars: Optional environment variables
            onstart_cmd: Optional onstart command (for SSH/Jupyter mode containers)
            docker_args: Optional args to pass to Docker ENTRYPOINT (for images like vllm/vllm-openai)
            reason_details: Additional details about the reason
            metadata: Additional metadata to log

        Returns:
            The created Instance

        Raises:
            Exception: If creation fails
        """
        # Build metadata with creation params
        creation_metadata = metadata or {}
        creation_metadata.update({
            "offer_id": offer_id,
            "image": image,
            "disk_size": disk_size,
            "label": label,
            "has_env_vars": bool(env_vars),
            "has_onstart_cmd": bool(onstart_cmd),
            "has_docker_args": bool(docker_args),
        })

        # Perform the creation
        try:
            instance = self.gpu_provider.create_instance(
                offer_id=offer_id,
                image=image,
                disk_size=disk_size,
                label=label,
                env_vars=env_vars,
                onstart_cmd=onstart_cmd,
                docker_args=docker_args,
            )
        except Exception as e:
            # Log the failure with a temporary instance ID (0)
            self._log_event(
                instance_id=0,
                action=LifecycleAction.CREATE,
                reason=reason,
                caller_source=caller_source,
                success=False,
                instance=None,
                previous_status=None,
                new_status="error",
                reason_details=f"Error: {str(e)}. Offer ID: {offer_id}. Original details: {reason_details}",
                metadata=creation_metadata,
            )
            raise

        # Log the successful creation
        self._log_event(
            instance_id=instance.id,
            action=LifecycleAction.CREATE,
            reason=reason,
            caller_source=caller_source,
            success=True,
            instance=instance,
            previous_status=None,
            new_status=instance.actual_status,
            reason_details=reason_details,
            metadata=creation_metadata,
        )

        return instance

    def log_create(
        self,
        instance: Instance,
        reason: str,
        caller_source: CallerSource = CallerSource.UNKNOWN,
        reason_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log instance creation (call after creating an instance).

        DEPRECATED: Use create_instance() instead for full audit logging.

        Args:
            instance: The created instance
            reason: Why was this instance created?
            caller_source: Who initiated the creation
            reason_details: Additional details
            metadata: Additional metadata to log
        """
        self._log_event(
            instance_id=instance.id,
            action=LifecycleAction.CREATE,
            reason=reason,
            caller_source=caller_source,
            success=True,
            instance=instance,
            previous_status=None,
            new_status=instance.actual_status,
            reason_details=reason_details,
            metadata=metadata,
        )

    def log_create_by_id(
        self,
        instance_id: int,
        reason: str,
        caller_source: CallerSource = CallerSource.UNKNOWN,
        reason_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log instance creation by ID (for cases where only the ID is available).

        Use this when the creation was done by a legacy service that returns
        only the instance ID. This will fetch the instance details for logging.

        Args:
            instance_id: The created instance ID
            reason: Why was this instance created?
            caller_source: Who initiated the creation
            reason_details: Additional details
            metadata: Additional metadata to log
        """
        # Try to get instance info for better logging
        instance = None
        try:
            instance = self.gpu_provider.get_instance(instance_id)
        except Exception:
            pass

        self._log_event(
            instance_id=instance_id,
            action=LifecycleAction.CREATE,
            reason=reason,
            caller_source=caller_source,
            success=True,
            instance=instance,
            previous_status=None,
            new_status=instance.actual_status if instance else "created",
            reason_details=reason_details,
            metadata=metadata,
        )

    def log_hibernate(
        self,
        instance_id: int,
        reason: str,
        caller_source: CallerSource = CallerSource.UNKNOWN,
        snapshot_id: Optional[str] = None,
        instance: Optional[Instance] = None,
        reason_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log instance hibernation (snapshot created + instance destroyed).

        Args:
            instance_id: Instance ID
            reason: Why was this instance hibernated?
            caller_source: Who initiated the hibernation
            snapshot_id: The snapshot ID created
            instance: Optional instance object for context
            reason_details: Additional details
            metadata: Additional metadata to log
        """
        self._log_event(
            instance_id=instance_id,
            action=LifecycleAction.HIBERNATE,
            reason=reason,
            caller_source=caller_source,
            success=True,
            instance=instance,
            previous_status=instance.actual_status if instance else None,
            new_status="hibernated",
            reason_details=reason_details,
            snapshot_id=snapshot_id,
            metadata=metadata,
        )

    def log_wake(
        self,
        instance: Instance,
        reason: str,
        caller_source: CallerSource = CallerSource.UNKNOWN,
        snapshot_id: Optional[str] = None,
        reason_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log instance wake (instance restored from snapshot).

        Args:
            instance: The newly created instance
            reason: Why was this instance woken?
            caller_source: Who initiated the wake
            snapshot_id: The snapshot ID used to restore
            reason_details: Additional details
            metadata: Additional metadata to log
        """
        self._log_event(
            instance_id=instance.id,
            action=LifecycleAction.WAKE,
            reason=reason,
            caller_source=caller_source,
            success=True,
            instance=instance,
            previous_status="hibernated",
            new_status=instance.actual_status,
            reason_details=reason_details,
            snapshot_id=snapshot_id,
            metadata=metadata,
        )

    def get_instance_history(
        self,
        instance_id: int,
        limit: int = 100,
    ) -> List[InstanceLifecycleEvent]:
        """
        Get lifecycle history for a specific instance.

        Args:
            instance_id: Instance ID
            limit: Maximum number of events to return

        Returns:
            List of lifecycle events, newest first
        """
        if not self.db_session:
            return []

        return (
            self.db_session.query(InstanceLifecycleEvent)
            .filter(InstanceLifecycleEvent.instance_id == instance_id)
            .order_by(InstanceLifecycleEvent.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_user_history(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[InstanceLifecycleEvent]:
        """
        Get lifecycle history for a user.

        Args:
            user_id: User ID (defaults to current user)
            limit: Maximum number of events to return

        Returns:
            List of lifecycle events, newest first
        """
        if not self.db_session:
            return []

        uid = user_id or self.user_id
        return (
            self.db_session.query(InstanceLifecycleEvent)
            .filter(InstanceLifecycleEvent.user_id == uid)
            .order_by(InstanceLifecycleEvent.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_recent_destroys(
        self,
        hours: int = 24,
        limit: int = 50,
    ) -> List[InstanceLifecycleEvent]:
        """
        Get recent destroy events (useful for debugging).

        Args:
            hours: How many hours back to look
            limit: Maximum number of events

        Returns:
            List of destroy events, newest first
        """
        if not self.db_session:
            return []

        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        return (
            self.db_session.query(InstanceLifecycleEvent)
            .filter(InstanceLifecycleEvent.action == LifecycleAction.DESTROY.value)
            .filter(InstanceLifecycleEvent.created_at >= cutoff)
            .order_by(InstanceLifecycleEvent.created_at.desc())
            .limit(limit)
            .all()
        )
