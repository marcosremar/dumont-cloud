"""
File-based Fine-Tuning Job Storage
Stores fine-tuning jobs in a JSON file for persistence
"""
import json
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from ...domain.models.finetune_job import FineTuneJob, FineTuneStatus

logger = logging.getLogger(__name__)

# Default storage location
DEFAULT_STORAGE_PATH = Path.home() / ".dumont" / "finetune_jobs.json"


class FineTuneJobStorage:
    """
    File-based storage for fine-tuning jobs.
    Stores jobs in a JSON file for persistence across restarts.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize fine-tuning job storage.

        Args:
            storage_path: Path to JSON storage file (default: ~/.dumont/finetune_jobs.json)
        """
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_STORAGE_PATH
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Ensure storage directory and file exist"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_jobs({})

    def _load_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Load jobs from storage file"""
        try:
            with open(self.storage_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {self.storage_path}, starting fresh")
            return {}

    def _save_jobs(self, jobs: Dict[str, Dict[str, Any]]):
        """Save jobs to storage file"""
        with open(self.storage_path, "w") as f:
            json.dump(jobs, f, indent=2, default=str)

    def save_job(self, job: FineTuneJob) -> bool:
        """
        Save or update a fine-tuning job.

        Args:
            job: FineTuneJob to save

        Returns:
            True if successful
        """
        try:
            jobs = self._load_jobs()
            jobs[job.id] = job.to_dict()
            self._save_jobs(jobs)
            logger.debug(f"Saved job {job.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save job {job.id}: {e}")
            return False

    def get_job(self, job_id: str) -> Optional[FineTuneJob]:
        """
        Get a job by ID.

        Args:
            job_id: Job ID

        Returns:
            FineTuneJob or None if not found
        """
        jobs = self._load_jobs()
        job_data = jobs.get(job_id)

        if not job_data:
            return None

        try:
            return FineTuneJob.from_dict(job_data)
        except Exception as e:
            logger.error(f"Failed to parse job {job_id}: {e}")
            return None

    def get_jobs_by_user(self, user_id: str) -> List[FineTuneJob]:
        """
        Get all jobs for a user.

        Args:
            user_id: User ID (email)

        Returns:
            List of FineTuneJob
        """
        jobs = self._load_jobs()
        user_jobs = []

        for job_data in jobs.values():
            if job_data.get("user_id") == user_id:
                try:
                    user_jobs.append(FineTuneJob.from_dict(job_data))
                except Exception as e:
                    logger.error(f"Failed to parse job: {e}")

        # Sort by created_at descending (newest first)
        user_jobs.sort(key=lambda j: j.created_at, reverse=True)
        return user_jobs

    def get_running_jobs(self) -> List[FineTuneJob]:
        """
        Get all currently running jobs.

        Returns:
            List of running FineTuneJob
        """
        jobs = self._load_jobs()
        running_jobs = []

        running_statuses = {
            FineTuneStatus.PENDING.value,
            FineTuneStatus.UPLOADING.value,
            FineTuneStatus.QUEUED.value,
            FineTuneStatus.RUNNING.value,
        }

        for job_data in jobs.values():
            if job_data.get("status") in running_statuses:
                try:
                    running_jobs.append(FineTuneJob.from_dict(job_data))
                except Exception as e:
                    logger.error(f"Failed to parse job: {e}")

        return running_jobs

    def update_job_status(
        self,
        job_id: str,
        status: FineTuneStatus,
        error_message: Optional[str] = None,
        **kwargs
    ) -> Optional[FineTuneJob]:
        """
        Update job status and optional fields.

        Args:
            job_id: Job ID
            status: New status
            error_message: Error message if failed
            **kwargs: Additional fields to update

        Returns:
            Updated FineTuneJob or None if not found
        """
        job = self.get_job(job_id)
        if not job:
            return None

        job.status = status

        if error_message:
            job.error_message = error_message

        if status == FineTuneStatus.RUNNING and not job.started_at:
            job.started_at = datetime.now()

        if status in {FineTuneStatus.COMPLETED, FineTuneStatus.FAILED, FineTuneStatus.CANCELLED}:
            job.completed_at = datetime.now()

        # Update any additional fields
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)

        self.save_job(job)
        return job

    def update_job_progress(
        self,
        job_id: str,
        current_epoch: int = None,
        current_step: int = None,
        total_steps: int = None,
        loss: float = None,
    ) -> Optional[FineTuneJob]:
        """
        Update job training progress.

        Args:
            job_id: Job ID
            current_epoch: Current epoch number
            current_step: Current step number
            total_steps: Total steps
            loss: Current loss value

        Returns:
            Updated FineTuneJob or None
        """
        job = self.get_job(job_id)
        if not job:
            return None

        if current_epoch is not None:
            job.current_epoch = current_epoch
        if current_step is not None:
            job.current_step = current_step
        if total_steps is not None:
            job.total_steps = total_steps
        if loss is not None:
            job.loss = loss

        self.save_job(job)
        return job

    def add_job_log(self, job_id: str, log_message: str) -> bool:
        """
        Add a log message to a job.

        Args:
            job_id: Job ID
            log_message: Log message to add

        Returns:
            True if successful
        """
        job = self.get_job(job_id)
        if not job:
            return False

        timestamp = datetime.now().isoformat()
        job.logs.append(f"[{timestamp}] {log_message}")

        # Keep only last 1000 log lines
        if len(job.logs) > 1000:
            job.logs = job.logs[-1000:]

        return self.save_job(job)

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.

        Args:
            job_id: Job ID

        Returns:
            True if deleted
        """
        jobs = self._load_jobs()
        if job_id not in jobs:
            return False

        del jobs[job_id]
        self._save_jobs(jobs)
        logger.info(f"Deleted job {job_id}")
        return True


# Singleton instance
_storage: Optional[FineTuneJobStorage] = None


def get_finetune_storage() -> FineTuneJobStorage:
    """Get or create FineTuneJobStorage singleton"""
    global _storage
    if _storage is None:
        _storage = FineTuneJobStorage()
    return _storage
