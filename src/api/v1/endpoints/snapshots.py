"""
Snapshot management API endpoints
"""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas.request import CreateSnapshotRequest, RestoreSnapshotRequest, DeleteSnapshotRequest, SetKeepForeverRequest
from ..schemas.response import (
    ListSnapshotsResponse,
    SnapshotResponse,
    CreateSnapshotResponse,
    RestoreSnapshotResponse,
    SuccessResponse,
)
from ....domain.services import SnapshotService, InstanceService
from ....core.exceptions import SnapshotException, NotFoundException
from ..dependencies import get_snapshot_service, get_instance_service, require_auth, get_current_user_email
from ....models.snapshot_metadata import SnapshotMetadata, SnapshotStatus
from ....services.snapshot_audit_logger import get_snapshot_audit_logger


class SnapshotMetadataStore:
    """
    Simple file-based storage for snapshot metadata.

    Stores metadata in ~/.dumont/snapshot_metadata.json
    """

    DEFAULT_METADATA_FILE = "snapshot_metadata.json"

    def __init__(self, metadata_file_path: Optional[str] = None):
        self._metadata_file_path = metadata_file_path
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

    @property
    def metadata_file_path(self) -> str:
        """Returns the path to the metadata file."""
        if self._metadata_file_path:
            return self._metadata_file_path

        home_dir = Path.home()
        metadata_dir = home_dir / ".dumont"
        metadata_dir.mkdir(parents=True, exist_ok=True)

        return str(metadata_dir / self.DEFAULT_METADATA_FILE)

    def _ensure_loaded(self) -> None:
        """Load metadata from file if not already loaded."""
        if self._loaded:
            return

        try:
            if os.path.exists(self.metadata_file_path):
                with open(self.metadata_file_path, 'r') as f:
                    data = json.load(f)
                    self._metadata = data.get('snapshots', {})
        except (json.JSONDecodeError, IOError):
            self._metadata = {}

        self._loaded = True

    def _save(self) -> None:
        """Save metadata to file."""
        try:
            metadata_dir = Path(self.metadata_file_path).parent
            metadata_dir.mkdir(parents=True, exist_ok=True)

            data = {
                'version': '1.0',
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'snapshots': self._metadata,
            }

            with open(self.metadata_file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError:
            pass

    def get_metadata(self, snapshot_id: str) -> Optional[SnapshotMetadata]:
        """Get metadata for a snapshot."""
        self._ensure_loaded()

        if snapshot_id in self._metadata:
            return SnapshotMetadata.from_dict(self._metadata[snapshot_id])
        return None

    def set_metadata(self, snapshot_id: str, metadata: SnapshotMetadata) -> None:
        """Set metadata for a snapshot."""
        self._ensure_loaded()

        metadata.updated_at = datetime.now(timezone.utc).isoformat()
        self._metadata[snapshot_id] = metadata.to_dict()
        self._save()

    def update_keep_forever(self, snapshot_id: str, keep_forever: bool, user_id: str = "") -> SnapshotMetadata:
        """Update the keep_forever flag for a snapshot."""
        self._ensure_loaded()

        if snapshot_id in self._metadata:
            metadata = SnapshotMetadata.from_dict(self._metadata[snapshot_id])
        else:
            metadata = SnapshotMetadata(
                snapshot_id=snapshot_id,
                user_id=user_id,
                status=SnapshotStatus.ACTIVE,
            )

        metadata.keep_forever = keep_forever
        metadata.updated_at = datetime.now(timezone.utc).isoformat()

        self._metadata[snapshot_id] = metadata.to_dict()
        self._save()

        return metadata


# Global metadata store instance
_metadata_store: Optional[SnapshotMetadataStore] = None


def get_metadata_store() -> SnapshotMetadataStore:
    """Get the global metadata store instance."""
    global _metadata_store
    if _metadata_store is None:
        _metadata_store = SnapshotMetadataStore()
    return _metadata_store

router = APIRouter(prefix="/snapshots", tags=["Snapshots"], dependencies=[Depends(require_auth)])


@router.get("", response_model=ListSnapshotsResponse)
async def list_snapshots(
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
):
    """
    List all snapshots

    Returns list of all backups in the repository.
    """
    snapshots = snapshot_service.list_snapshots()

    snapshot_responses = [
        SnapshotResponse(
            id=snap["id"],
            short_id=snap["short_id"],
            time=snap["time"],
            hostname=snap["hostname"],
            tags=snap["tags"],
            paths=snap["paths"],
        )
        for snap in snapshots
    ]

    return ListSnapshotsResponse(snapshots=snapshot_responses, count=len(snapshot_responses))


@router.post("", response_model=CreateSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    request: CreateSnapshotRequest,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Create a new snapshot

    Creates a backup of the specified instance.
    """
    try:
        # Get instance details
        instance = instance_service.get_instance(request.instance_id)

        if not instance.is_running:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance {request.instance_id} is not running",
            )

        if not instance.ssh_host or not instance.ssh_port:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance {request.instance_id} SSH details not available",
            )

        # Create snapshot
        result = snapshot_service.create_snapshot(
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            source_path=request.source_path,
            tags=request.tags,
        )

        return CreateSnapshotResponse(
            success=True,
            snapshot_id=result["snapshot_id"],
            files_new=result["files_new"],
            files_changed=result["files_changed"],
            files_unmodified=result["files_unmodified"],
            total_files_processed=result["total_files_processed"],
            data_added=result["data_added"],
            total_bytes_processed=result["total_bytes_processed"],
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except SnapshotException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/restore", response_model=RestoreSnapshotResponse)
async def restore_snapshot(
    request: RestoreSnapshotRequest,
    instance_id: int,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Restore a snapshot

    Restores a backup to the specified instance.
    """
    try:
        # Get instance details
        instance = instance_service.get_instance(instance_id)

        if not instance.is_running:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance {instance_id} is not running",
            )

        if not instance.ssh_host or not instance.ssh_port:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance {instance_id} SSH details not available",
            )

        # Restore snapshot
        result = snapshot_service.restore_snapshot(
            snapshot_id=request.snapshot_id,
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            target_path=request.target_path,
            verify=request.verify,
        )

        return RestoreSnapshotResponse(
            success=result["success"],
            snapshot_id=result["snapshot_id"],
            target_path=result["target_path"],
            files_restored=result["files_restored"],
            errors=result["errors"],
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except SnapshotException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{snapshot_id}", response_model=SuccessResponse)
async def delete_snapshot(
    snapshot_id: str,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
):
    """
    Delete a snapshot

    Permanently deletes a backup.
    """
    success = snapshot_service.delete_snapshot(snapshot_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete snapshot {snapshot_id}",
        )

    return SuccessResponse(
        success=True,
        message=f"Snapshot {snapshot_id} deleted successfully",
    )


@router.post("/{snapshot_id}/keep-forever", response_model=SuccessResponse)
async def set_keep_forever(
    snapshot_id: str,
    request: SetKeepForeverRequest,
    user_email: str = Depends(get_current_user_email),
):
    """
    Set keep-forever flag on a snapshot

    Protects or unprotects a snapshot from automatic cleanup.
    When keep_forever is True, the snapshot will never be deleted by the
    automatic cleanup agent, regardless of retention policy.
    """
    try:
        # Get the metadata store
        metadata_store = get_metadata_store()

        # Update the keep_forever flag
        metadata = metadata_store.update_keep_forever(
            snapshot_id=snapshot_id,
            keep_forever=request.keep_forever,
            user_id=user_email,
        )

        # Log to audit
        audit_logger = get_snapshot_audit_logger()
        audit_logger.log_keep_forever_changed(
            snapshot_id=snapshot_id,
            user_id=user_email,
            keep_forever=request.keep_forever,
        )

        action = "protected" if request.keep_forever else "unprotected"
        return SuccessResponse(
            success=True,
            message=f"Snapshot {snapshot_id} {action} from automatic cleanup",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update snapshot {snapshot_id}: {str(e)}",
        )
