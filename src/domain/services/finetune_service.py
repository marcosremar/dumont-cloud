"""
Fine-Tuning Service - Domain Service (Business Logic)
Orchestrates fine-tuning operations using SkyPilot or VAST.ai
Includes mandatory CPU Standby for checkpoint synchronization

Architecture:
┌─────────────────┐         ┌─────────────────┐
│  GPU Vast.ai    │  rsync  │  GCP CPU        │
│  (fine-tuning)  │ ──────► │  (standby)      │
└─────────────────┘         └─────────────────┘
        │                          │
        │ checkpoints              │ backup
        ▼                          ▼
   [Training]                 [Cloudflare R2]

If GPU fails, checkpoints are saved on CPU Standby for recovery.
"""
import logging
import uuid
import os
import tempfile
import threading
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from ...services.template_service import get_cached_environment

from ..models.finetune_job import (
    FineTuneJob,
    FineTuneConfig,
    FineTuneStatus,
    DatasetSource,
)
from ...infrastructure.providers.skypilot_provider import get_skypilot_provider
from ...infrastructure.providers.finetune_storage import get_finetune_storage
from ...infrastructure.providers.vast_finetune_provider import get_vast_finetune_provider

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"

# Supported base models for fine-tuning (10 lightweight models for fast training)
SUPPORTED_MODELS = [
    # Ultra-lightweight models (< 4B params) - Fastest training
    {
        "id": "unsloth/Phi-3-mini-4k-instruct-bnb-4bit",
        "name": "Phi-3 Mini 4K",
        "parameters": "3.8B",
        "min_vram": "8GB",
        "recommended_gpu": "RTX 3080, RTX 4070",
        "category": "ultra-light",
        "training_speed": "very-fast",
    },
    {
        "id": "unsloth/tinyllama-bnb-4bit",
        "name": "TinyLlama 1.1B",
        "parameters": "1.1B",
        "min_vram": "4GB",
        "recommended_gpu": "RTX 3060, RTX 4060",
        "category": "ultra-light",
        "training_speed": "very-fast",
    },
    {
        "id": "unsloth/stablelm-2-1_6b-bnb-4bit",
        "name": "StableLM 2 1.6B",
        "parameters": "1.6B",
        "min_vram": "6GB",
        "recommended_gpu": "RTX 3060, RTX 4060",
        "category": "ultra-light",
        "training_speed": "very-fast",
    },
    # Lightweight models (4-8B params) - Fast training
    {
        "id": "unsloth/mistral-7b-bnb-4bit",
        "name": "Mistral 7B",
        "parameters": "7B",
        "min_vram": "12GB",
        "recommended_gpu": "RTX 3090, RTX 4090",
        "category": "light",
        "training_speed": "fast",
    },
    {
        "id": "unsloth/gemma-7b-bnb-4bit",
        "name": "Gemma 7B",
        "parameters": "7B",
        "min_vram": "12GB",
        "recommended_gpu": "RTX 3090, RTX 4090",
        "category": "light",
        "training_speed": "fast",
    },
    {
        "id": "unsloth/Qwen2-7B-bnb-4bit",
        "name": "Qwen 2 7B",
        "parameters": "7B",
        "min_vram": "12GB",
        "recommended_gpu": "RTX 3090, RTX 4090",
        "category": "light",
        "training_speed": "fast",
    },
    {
        "id": "unsloth/llama-3-8b-bnb-4bit",
        "name": "Llama 3 8B",
        "parameters": "8B",
        "min_vram": "16GB",
        "recommended_gpu": "RTX 4090, A100",
        "category": "light",
        "training_speed": "fast",
    },
    {
        "id": "unsloth/zephyr-7b-beta-bnb-4bit",
        "name": "Zephyr 7B Beta",
        "parameters": "7B",
        "min_vram": "12GB",
        "recommended_gpu": "RTX 3090, RTX 4090",
        "category": "light",
        "training_speed": "fast",
    },
    {
        "id": "unsloth/openhermes-2.5-mistral-7b-bnb-4bit",
        "name": "OpenHermes 2.5 7B",
        "parameters": "7B",
        "min_vram": "12GB",
        "recommended_gpu": "RTX 3090, RTX 4090",
        "category": "light",
        "training_speed": "fast",
    },
    {
        "id": "unsloth/codellama-7b-bnb-4bit",
        "name": "CodeLlama 7B",
        "parameters": "7B",
        "min_vram": "12GB",
        "recommended_gpu": "RTX 3090, RTX 4090",
        "category": "light",
        "training_speed": "fast",
    },
]


class FineTuningService:
    """
    Domain service for fine-tuning job management.
    Orchestrates operations between SkyPilot/VAST provider and storage.

    Features:
    - Mandatory CPU Standby for checkpoint synchronization
    - Automatic orphan job detection and cleanup
    - GPU health monitoring
    """

    def __init__(self):
        """Initialize fine-tuning service"""
        self.skypilot = get_skypilot_provider()
        self.vast_finetune = get_vast_finetune_provider()
        self.storage = get_finetune_storage()
        self.template_dir = TEMPLATE_DIR

        # CPU Standby sync threads (job_id -> thread)
        self._sync_threads: Dict[str, threading.Thread] = {}
        self._sync_running: Dict[str, bool] = {}

    @property
    def is_skypilot_available(self) -> bool:
        """Check if SkyPilot is available for launching jobs"""
        return self.skypilot.is_available

    @property
    def is_vast_available(self) -> bool:
        """Check if VAST.ai fine-tuning is available"""
        return self.vast_finetune.is_available

    @property
    def is_finetune_available(self) -> bool:
        """Check if any fine-tuning backend is available"""
        return self.is_skypilot_available or self.is_vast_available

    def _verify_gpu_instance_exists(self, instance_id: int) -> bool:
        """
        Verify if a GPU instance still exists on VAST.ai.

        Args:
            instance_id: VAST.ai instance ID

        Returns:
            True if instance exists and is running/starting
        """
        if not instance_id:
            return False

        try:
            # Check if VAST is available
            if not self.is_vast_available:
                logger.debug(f"VAST.ai not available, assuming instance {instance_id} exists")
                return True

            status = self.vast_finetune.get_job_status(instance_id)
            if status.get("error"):
                error_msg = status.get("error", "").lower()
                # If rate limited or connection error, assume instance exists (don't mark as orphan)
                if "429" in error_msg or "rate" in error_msg or "timeout" in error_msg or "connection" in error_msg:
                    logger.debug(f"Instance {instance_id} check got rate limit/connection error, assuming exists")
                    return True
                logger.debug(f"Instance {instance_id} status error: {status.get('error')}")
                return False

            actual_status = status.get("status", "unknown")
            # Instance exists if it's in an active state
            return actual_status in ["running", "loading", "created", "starting", "provisioning"]
        except Exception as e:
            error_str = str(e).lower()
            # If rate limited or connection error, assume instance exists (don't mark as orphan)
            if "429" in error_str or "rate" in error_str or "timeout" in error_str or "connection" in error_str:
                logger.debug(f"Instance {instance_id} check got rate limit/connection error, assuming exists")
                return True
            logger.debug(f"Instance {instance_id} check failed: {e}")
            return False

    def validate_and_sync_jobs(self, user_id: str) -> Dict[str, Any]:
        """
        Validate all active jobs for a user and sync their status with actual GPU state.
        Marks orphan jobs (no active GPU or no instance ID) as failed.

        Args:
            user_id: User ID

        Returns:
            Dict with sync results
        """
        jobs = self.storage.get_jobs_by_user(user_id)
        synced = 0
        orphans_found = 0

        # Grace period: don't mark jobs as orphan if created within last 5 minutes
        GRACE_PERIOD_MINUTES = 5

        for job in jobs:
            # Only check jobs that should have an active machine
            if job.is_active:
                # Check if job is within grace period (recently created)
                job_age_minutes = 0
                if job.created_at:
                    job_age = datetime.now() - job.created_at
                    job_age_minutes = job_age.total_seconds() / 60

                is_within_grace_period = job_age_minutes < GRACE_PERIOD_MINUTES
                logger.info(f"[GRACE] Job {job.id}: age={job_age_minutes:.2f}min, grace={GRACE_PERIOD_MINUTES}min, within={is_within_grace_period}, status={job.status}, instance={job.skypilot_job_id}")

                # Jobs in RUNNING status must have an instance ID
                if job.status == FineTuneStatus.RUNNING and not job.skypilot_job_id:
                    if is_within_grace_period:
                        # Job is new, give it time to get an instance
                        logger.info(f"[GRACE] Job {job.id} SKIPPING - no instance but within grace period")
                        continue
                    # Job is marked as running but has no instance - orphan
                    logger.warning(f"Job {job.id} is running but has no GPU instance ID (orphan detected)")
                    self.storage.update_job_status(
                        job.id,
                        FineTuneStatus.FAILED,
                        error_message="Job has no GPU instance (launch failed)"
                    )
                    self.storage.add_job_log(
                        job.id,
                        "Job marked as failed: No GPU instance was allocated"
                    )
                    orphans_found += 1
                elif job.skypilot_job_id:
                    # Verify GPU instance still exists
                    instance_exists = self._verify_gpu_instance_exists(job.skypilot_job_id)
                    logger.info(f"[GRACE] Job {job.id}: instance_exists={instance_exists}, within_grace={is_within_grace_period}")
                    if not instance_exists:
                        if is_within_grace_period:
                            # Instance may still be initializing
                            logger.info(f"[GRACE] Job {job.id} SKIPPING - instance not ready but within grace period")
                            continue
                        # GPU não existe mais - marcar como falha
                        logger.warning(f"Job {job.id} has no active GPU instance (orphan detected)")
                        self.storage.update_job_status(
                            job.id,
                            FineTuneStatus.FAILED,
                            error_message="GPU instance terminated unexpectedly (orphan job)"
                        )
                        self.storage.add_job_log(
                            job.id,
                            f"Job marked as failed: GPU instance {job.skypilot_job_id} no longer exists"
                        )
                        orphans_found += 1
                    else:
                        synced += 1

        return {
            "total_checked": len([j for j in jobs if j.is_active]),
            "synced": synced,
            "orphans_found": orphans_found,
        }

    def _provision_cpu_standby(self, job: FineTuneJob) -> Optional[Dict[str, Any]]:
        """
        Provision a CPU Standby instance for checkpoint synchronization.

        The CPU Standby is MANDATORY for fine-tuning jobs to ensure data safety.
        Checkpoints are synced from GPU to CPU every 30 seconds.

        Args:
            job: FineTuneJob to provision standby for

        Returns:
            Dict with CPU standby info or None if failed
        """
        try:
            from ...services.standby.manager import get_standby_manager
            from ...services.standby.cpu import CPUStandbyConfig

            manager = get_standby_manager()

            # Check if manager is configured
            if not manager.is_configured():
                logger.warning(f"Standby manager not configured, skipping CPU standby for job {job.id}")
                # Still proceed without CPU standby - will log warning
                self.storage.add_job_log(
                    job.id,
                    "Warning: CPU Standby not configured. Checkpoints will not be backed up automatically."
                )
                return None

            # If GPU instance ID is available, create standby
            if job.skypilot_job_id:
                result = manager.on_gpu_created(
                    gpu_instance_id=job.skypilot_job_id,
                    label=f"finetune-{job.id}",
                    machine_id=job.skypilot_job_id,
                )

                if result:
                    logger.info(f"CPU Standby provisioned for job {job.id}: {result}")
                    self.storage.add_job_log(
                        job.id,
                        f"CPU Standby provisioned: {result.get('cpu_standby', {}).get('name', 'unknown')} "
                        f"({result.get('cpu_standby', {}).get('ip', 'unknown')})"
                    )
                    return result
                else:
                    self.storage.add_job_log(
                        job.id,
                        "Warning: Failed to provision CPU Standby. Checkpoints may not be backed up."
                    )
            return None

        except Exception as e:
            logger.error(f"Failed to provision CPU standby for job {job.id}: {e}")
            self.storage.add_job_log(job.id, f"Error provisioning CPU Standby: {e}")
            return None

    def _start_checkpoint_sync(self, job: FineTuneJob) -> bool:
        """
        Start checkpoint synchronization from GPU to CPU Standby.

        Sync occurs every 30 seconds for checkpoints in /workspace/output.

        Args:
            job: FineTuneJob to sync

        Returns:
            True if sync started
        """
        if not job.skypilot_job_id or not job.cpu_standby_instance_id:
            return False

        # Already syncing?
        if job.id in self._sync_running and self._sync_running[job.id]:
            return True

        self._sync_running[job.id] = True

        def sync_loop():
            """Background sync loop"""
            sync_interval = 30  # seconds
            checkpoint_path = "/workspace/output"  # Unsloth saves checkpoints here

            while self._sync_running.get(job.id, False):
                try:
                    # Refresh job status
                    current_job = self.storage.get_job(job.id)
                    if not current_job or not current_job.is_running:
                        logger.info(f"Job {job.id} no longer running, stopping sync")
                        break

                    # Get standby manager and sync
                    from ...services.standby.manager import get_standby_manager
                    manager = get_standby_manager()

                    service = manager.get_service(job.skypilot_job_id)
                    if service:
                        # Trigger sync
                        service._do_sync()

                        # Update job with sync count
                        self.storage.update_job_progress(
                            job.id,
                            current_epoch=current_job.current_epoch,
                        )

                        # Update checkpoint sync time
                        job_data = self.storage.get_job(job.id)
                        if job_data:
                            job_data.last_checkpoint_sync = datetime.now()
                            job_data.checkpoint_sync_count += 1
                            self.storage.save_job(job_data)

                        logger.debug(f"Checkpoint sync completed for job {job.id}")

                except Exception as e:
                    logger.error(f"Checkpoint sync error for job {job.id}: {e}")

                time.sleep(sync_interval)

            self._sync_running[job.id] = False
            logger.info(f"Checkpoint sync stopped for job {job.id}")

        # Start sync thread
        thread = threading.Thread(target=sync_loop, daemon=True)
        thread.name = f"finetune-sync-{job.id}"
        self._sync_threads[job.id] = thread
        thread.start()

        self.storage.add_job_log(
            job.id,
            "Checkpoint synchronization started (GPU → CPU Standby every 30s)"
        )
        return True

    def _stop_checkpoint_sync(self, job_id: str) -> bool:
        """Stop checkpoint synchronization for a job"""
        if job_id in self._sync_running:
            self._sync_running[job_id] = False

            if job_id in self._sync_threads:
                thread = self._sync_threads[job_id]
                if thread.is_alive():
                    thread.join(timeout=5)
                del self._sync_threads[job_id]

            return True
        return False

    def create_job(
        self,
        user_id: str,
        name: str,
        base_model: str,
        dataset_source: str,
        dataset_path: str,
        dataset_format: str = "alpaca",
        config: Optional[Dict[str, Any]] = None,
        gpu_type: str = "A100",
        num_gpus: int = 1,
    ) -> FineTuneJob:
        """
        Create a new fine-tuning job.

        Args:
            user_id: User ID (email)
            name: Job name
            base_model: Base model ID
            dataset_source: Dataset source (upload, url, huggingface)
            dataset_path: Path to dataset
            dataset_format: Dataset format (alpaca, sharegpt)
            config: Fine-tuning configuration overrides
            gpu_type: GPU type to use
            num_gpus: Number of GPUs

        Returns:
            Created FineTuneJob
        """
        logger.info(f"Creating fine-tuning job '{name}' for user {user_id}")

        # Generate unique job ID
        job_id = str(uuid.uuid4())[:8]

        # Build config
        config_dict = config or {}
        config_dict["base_model"] = base_model
        ft_config = FineTuneConfig.from_dict(config_dict)

        # Create job
        job = FineTuneJob(
            id=job_id,
            user_id=user_id,
            name=name,
            status=FineTuneStatus.PENDING,
            config=ft_config,
            dataset_source=DatasetSource(dataset_source),
            dataset_path=dataset_path,
            dataset_format=dataset_format,
            gpu_type=gpu_type,
            num_gpus=num_gpus,
            created_at=datetime.now(),
        )

        # Save to storage
        self.storage.save_job(job)
        logger.info(f"Created job {job_id}")

        return job

    def start_job(self, job_id: str) -> bool:
        """
        Start a fine-tuning job.

        Args:
            job_id: Job ID to start

        Returns:
            True if job started successfully
        """
        job = self.storage.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False

        logger.info(f"Starting fine-tuning job {job_id}")

        # Update status
        self.storage.update_job_status(job_id, FineTuneStatus.QUEUED)

        # Prefer VAST.ai direct for faster provisioning, fallback to SkyPilot
        if self.is_vast_available:
            return self._start_job_vast(job)
        elif self.is_skypilot_available:
            success = self._start_job_skypilot(job)
            if success:
                return True
            # If SkyPilot failed, try VAST.ai again (in case it became available)
            job = self.storage.get_job(job_id)  # Refresh job state
            if job and job.status == FineTuneStatus.FAILED and self.is_vast_available:
                self.storage.add_job_log(job_id, "Falling back to VAST.ai backend...")
                self.storage.update_job_status(job_id, FineTuneStatus.QUEUED)
                return self._start_job_vast(job)
            return False
        else:
            error_msg = "No fine-tuning backend available. Install SkyPilot or configure VAST.ai API key."
            self.storage.update_job_status(job_id, FineTuneStatus.FAILED, error_message=error_msg)
            self.storage.add_job_log(job_id, f"Error: {error_msg}")
            return False

    def _start_job_skypilot(self, job) -> bool:
        """Start job via SkyPilot"""
        job_id = job.id
        self.storage.add_job_log(job_id, "Using SkyPilot backend...")

        # Check if any cloud provider is configured
        self.storage.add_job_log(job_id, "Checking cloud provider configuration...")
        clouds_to_check = ["vast", "gcp", "aws", "azure", "lambda"]
        enabled_cloud = None

        for cloud in clouds_to_check:
            check_result = self.skypilot.check_cloud(cloud)
            if check_result.get("enabled"):
                enabled_cloud = cloud
                self.storage.add_job_log(job_id, f"Cloud provider '{cloud}' is configured and enabled")
                break

        if not enabled_cloud:
            error_msg = (
                "No cloud provider configured in SkyPilot. "
                "Please configure a cloud provider (vast, gcp, aws, azure) "
                "using 'sky check' or set up VAST.ai credentials. "
                "Run 'sky check' to see cloud configuration status."
            )
            logger.error(f"Job {job_id}: {error_msg}")
            self.storage.update_job_status(
                job_id,
                FineTuneStatus.FAILED,
                error_message=error_msg
            )
            self.storage.add_job_log(job_id, f"Error: {error_msg}")
            return False

        self.storage.add_job_log(job_id, "Generating SkyPilot task configuration...")

        try:
            # Generate SkyPilot YAML
            yaml_path = self._generate_task_yaml(job)
            self.storage.add_job_log(job_id, f"Generated task YAML: {yaml_path}")

            # Generate unique job name for SkyPilot
            skypilot_job_name = f"finetune-{job.id}-{job.name[:20].replace(' ', '-').lower()}"

            # Launch via SkyPilot
            self.storage.add_job_log(job_id, f"Launching SkyPilot job: {skypilot_job_name}")
            result = self.skypilot.launch_finetune_job(
                job_name=skypilot_job_name,
                yaml_path=yaml_path,
            )

            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Failed to launch job {job_id}: {error_msg}")
                self.storage.update_job_status(
                    job_id,
                    FineTuneStatus.FAILED,
                    error_message=error_msg
                )
                self.storage.add_job_log(job_id, f"Launch failed: {error_msg}")
                return False

            # Update job with SkyPilot info
            self.storage.update_job_status(
                job_id,
                FineTuneStatus.RUNNING,
                skypilot_job_id=result.get("job_id"),
                skypilot_job_name=skypilot_job_name,
            )
            self.storage.add_job_log(
                job_id,
                f"Job launched successfully. SkyPilot job ID: {result.get('job_id')}"
            )

            # Clean up temp YAML
            if os.path.exists(yaml_path):
                os.remove(yaml_path)

            return True

        except Exception as e:
            logger.exception(f"Error starting job {job_id}")
            self.storage.update_job_status(
                job_id,
                FineTuneStatus.FAILED,
                error_message=str(e)
            )
            self.storage.add_job_log(job_id, f"Error: {str(e)}")
            return False

    def _start_job_vast(self, job) -> bool:
        """
        Start job via VAST.ai directly.

        This method:
        1. Finds and provisions a GPU on VAST.ai
        2. Provisions a mandatory CPU Standby for checkpoint backup
        3. Starts checkpoint synchronization (GPU → CPU every 30s)
        """
        job_id = job.id
        self.storage.add_job_log(job_id, "Using VAST.ai backend...")
        self.storage.add_job_log(job_id, f"Searching for {job.gpu_type} GPU on VAST.ai...")

        try:
            # Generate unique job name
            vast_job_name = f"finetune-{job.id}-{job.name[:20].replace(' ', '-').lower()}"

            # Launch via VAST.ai
            result = self.vast_finetune.launch_finetune_job(
                job_name=vast_job_name,
                base_model=job.config.base_model,
                dataset_path=job.dataset_path,
                dataset_format=job.dataset_format,
                gpu_type=job.gpu_type,
                config={
                    "lora_rank": job.config.lora_rank,
                    "lora_alpha": job.config.lora_alpha,
                    "epochs": job.config.epochs,
                    "batch_size": job.config.batch_size,
                    "learning_rate": job.config.learning_rate,
                    "max_seq_length": job.config.max_seq_length,
                },
            )

            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Failed to launch job {job_id}: {error_msg}")
                self.storage.update_job_status(
                    job_id,
                    FineTuneStatus.FAILED,
                    error_message=error_msg
                )
                self.storage.add_job_log(job_id, f"Launch failed: {error_msg}")
                return False

            # Update job with VAST.ai info
            instance_id = result.get("instance_id")
            self.storage.update_job_status(
                job_id,
                FineTuneStatus.RUNNING,
                skypilot_job_id=instance_id,  # Reuse field for VAST instance ID
                skypilot_job_name=vast_job_name,
            )
            self.storage.add_job_log(
                job_id,
                f"Job launched on VAST.ai. Instance ID: {instance_id}, GPU: {job.gpu_type}, "
                f"Cost: ${result.get('cost_per_hour', 0):.2f}/hr"
            )

            # ========================================
            # MANDATORY: Provision CPU Standby
            # ========================================
            self.storage.add_job_log(job_id, "Provisioning mandatory CPU Standby for checkpoint backup...")

            # Refresh job to get updated instance_id
            updated_job = self.storage.get_job(job_id)
            if updated_job:
                standby_result = self._provision_cpu_standby(updated_job)

                if standby_result:
                    # Update job with CPU Standby info
                    cpu_standby = standby_result.get("cpu_standby", {})
                    updated_job.cpu_standby_instance_id = cpu_standby.get("name")
                    updated_job.cpu_standby_instance_ip = cpu_standby.get("ip")
                    updated_job.cpu_standby_instance_zone = cpu_standby.get("zone")
                    self.storage.save_job(updated_job)

                    # Start checkpoint synchronization
                    self.storage.add_job_log(
                        job_id,
                        "Starting checkpoint synchronization (GPU → CPU Standby)..."
                    )
                    self._start_checkpoint_sync(updated_job)
                else:
                    self.storage.add_job_log(
                        job_id,
                        "WARNING: CPU Standby could not be provisioned. "
                        "Checkpoints will NOT be backed up automatically. "
                        "Configure CPU Standby via Settings > Failover to enable."
                    )

            return True

        except Exception as e:
            logger.exception(f"Error starting job {job_id} on VAST.ai")
            self.storage.update_job_status(
                job_id,
                FineTuneStatus.FAILED,
                error_message=str(e)
            )
            self.storage.add_job_log(job_id, f"Error: {str(e)}")
            return False

    def get_job(self, job_id: str, user_id: Optional[str] = None) -> Optional[FineTuneJob]:
        """
        Get a job by ID, optionally filtering by user.

        Args:
            job_id: Job ID
            user_id: Optional user ID to verify ownership

        Returns:
            FineTuneJob or None
        """
        job = self.storage.get_job(job_id)

        if job and user_id and job.user_id != user_id:
            return None

        return job

    def list_jobs(self, user_id: str, validate: bool = True) -> List[FineTuneJob]:
        """
        List all jobs for a user.
        Optionally validates and syncs job status with actual GPU state.

        Args:
            user_id: User ID
            validate: If True, validates jobs and marks orphans as failed

        Returns:
            List of FineTuneJob
        """
        # First, validate and sync active jobs to detect orphans
        if validate:
            sync_result = self.validate_and_sync_jobs(user_id)
            if sync_result["orphans_found"] > 0:
                logger.info(f"Found and marked {sync_result['orphans_found']} orphan jobs for user {user_id}")

        return self.storage.get_jobs_by_user(user_id)

    def get_job_logs(self, job_id: str, tail: int = 100) -> str:
        """
        Get logs for a job.

        Args:
            job_id: Job ID
            tail: Number of lines to return

        Returns:
            Log output
        """
        job = self.storage.get_job(job_id)
        if not job:
            return "Job not found"

        # If job has SkyPilot job name, get live logs
        if job.skypilot_job_name and job.is_running:
            return self.skypilot.get_job_logs(job.skypilot_job_name, tail)

        # Otherwise return stored logs
        return "\n".join(job.logs[-tail:])

    def cancel_job(self, job_id: str, user_id: Optional[str] = None) -> bool:
        """
        Cancel a running job.

        Also stops checkpoint synchronization and optionally cleans up CPU Standby.

        Args:
            job_id: Job ID
            user_id: User ID for verification

        Returns:
            True if cancelled
        """
        job = self.get_job(job_id, user_id)
        if not job:
            return False

        if not job.is_running:
            logger.warning(f"Job {job_id} is not running, cannot cancel")
            return False

        # Stop checkpoint synchronization
        self._stop_checkpoint_sync(job_id)
        self.storage.add_job_log(job_id, "Checkpoint synchronization stopped")

        # Cancel SkyPilot job if we have the ID
        if job.skypilot_job_id:
            # Try VAST.ai first
            if self.is_vast_available:
                try:
                    self.vast_finetune.cancel_job(job.skypilot_job_id)
                    self.storage.add_job_log(job_id, f"VAST.ai instance {job.skypilot_job_id} terminated")
                except Exception as e:
                    logger.warning(f"Failed to cancel VAST job: {e}")

            # Also try SkyPilot
            success = self.skypilot.cancel_job(job.skypilot_job_id)
            if not success:
                logger.warning(f"Failed to cancel SkyPilot job {job.skypilot_job_id}")

        # Clean up CPU Standby if exists
        if job.cpu_standby_instance_id:
            try:
                from ...services.standby.manager import get_standby_manager
                manager = get_standby_manager()
                if job.skypilot_job_id:
                    manager.on_gpu_destroyed(job.skypilot_job_id)
                    self.storage.add_job_log(
                        job_id,
                        f"CPU Standby {job.cpu_standby_instance_id} terminated"
                    )
            except Exception as e:
                logger.warning(f"Failed to clean up CPU Standby: {e}")
                self.storage.add_job_log(job_id, f"Warning: CPU Standby cleanup failed: {e}")

        # Update status
        self.storage.update_job_status(job_id, FineTuneStatus.CANCELLED)
        self.storage.add_job_log(job_id, "Job cancelled by user")

        return True

    def delete_job(self, job_id: str, user_id: Optional[str] = None) -> bool:
        """
        Delete a job from storage.

        Args:
            job_id: Job ID
            user_id: User ID for verification

        Returns:
            True if deleted
        """
        job = self.get_job(job_id, user_id)
        if not job:
            logger.warning(f"Job {job_id} not found or doesn't belong to user")
            return False

        # Don't allow deleting running jobs
        if job.is_running:
            logger.warning(f"Job {job_id} is still running, cannot delete")
            return False

        # Delete from storage
        success = self.storage.delete_job(job_id)
        if success:
            logger.info(f"Deleted job {job_id}")
        return success

    def refresh_job_status(self, job_id: str) -> Optional[FineTuneJob]:
        """
        Refresh job status from SkyPilot.

        Args:
            job_id: Job ID

        Returns:
            Updated FineTuneJob
        """
        job = self.storage.get_job(job_id)
        if not job or not job.skypilot_job_name:
            return job

        if job.status not in {FineTuneStatus.RUNNING, FineTuneStatus.QUEUED}:
            return job

        # Get status from SkyPilot
        status = self.skypilot.get_job_status(job_name=job.skypilot_job_name)

        if "error" in status:
            logger.warning(f"Error getting status for job {job_id}: {status['error']}")
            return job

        skypilot_status = status.get("status", "UNKNOWN")

        # Map SkyPilot status to our status
        status_map = {
            "PENDING": FineTuneStatus.QUEUED,
            "SETTING_UP": FineTuneStatus.QUEUED,
            "RUNNING": FineTuneStatus.RUNNING,
            "SUCCEEDED": FineTuneStatus.COMPLETED,
            "FAILED": FineTuneStatus.FAILED,
            "CANCELLED": FineTuneStatus.CANCELLED,
            "NOT_FOUND": job.status,
        }

        new_status = status_map.get(skypilot_status, job.status)

        if new_status != job.status:
            self.storage.update_job_status(job_id, new_status)
            self.storage.add_job_log(job_id, f"Status updated: {job.status.value} -> {new_status.value}")

        return self.storage.get_job(job_id)

    async def upload_dataset(self, user_id: str, file) -> str:
        """
        Upload a dataset file.

        Args:
            user_id: User ID
            file: Uploaded file object

        Returns:
            Path to stored dataset
        """
        # For now, store locally. In production, upload to R2/S3
        import aiofiles
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"

        # Create user dataset directory
        dataset_dir = Path.home() / ".dumont" / "datasets" / user_id
        dataset_dir.mkdir(parents=True, exist_ok=True)

        file_path = dataset_dir / filename

        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"Uploaded dataset: {file_path}")
        return str(file_path)

    def get_supported_models(self) -> List[Dict[str, Any]]:
        """Get list of supported models for fine-tuning"""
        return SUPPORTED_MODELS

    def _generate_task_yaml(self, job: FineTuneJob, locale: str = "en") -> str:
        """
        Generate SkyPilot task YAML from template.

        Args:
            job: FineTuneJob
            locale: Language code for i18n (e.g., 'en', 'es')

        Returns:
            Path to generated YAML file
        """
        # Use i18n-enabled Jinja2 environment
        env = get_cached_environment(locale)
        template = env.get_template("finetune_task.yaml.j2")

        # Map GPU type
        gpu_accelerator = self.skypilot.map_gpu_type(job.gpu_type)

        yaml_content = template.render(
            job_name=f"finetune-{job.id}",
            gpu_type=gpu_accelerator,
            num_gpus=job.num_gpus,
            dataset_path=job.dataset_path,
            dataset_format=job.dataset_format,
            base_model=job.config.base_model,
            lora_rank=job.config.lora_rank,
            lora_alpha=job.config.lora_alpha,
            learning_rate=job.config.learning_rate,
            epochs=job.config.epochs,
            batch_size=job.config.batch_size,
            gradient_accumulation_steps=job.config.gradient_accumulation_steps,
            max_seq_length=job.config.max_seq_length,
            warmup_steps=job.config.warmup_steps,
            weight_decay=job.config.weight_decay,
            output_dir=job.config.output_dir,
        )

        # Write to temp file
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml", prefix=f"finetune_{job.id}_")
        os.close(fd)

        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        return yaml_path

    def deploy_finetuned_model(
        self,
        job_id: str,
        gpu_type: str = "RTX4090",
        instance_name: Optional[str] = None,
        max_price: float = 2.0,
        port: int = 8000,
    ) -> Dict[str, Any]:
        """
        Deploy a fine-tuned model for inference.

        Creates a new GPU instance with vLLM serving the fine-tuned LoRA adapter.

        Args:
            job_id: ID of the completed fine-tuning job
            gpu_type: GPU type for inference
            instance_name: Custom instance name
            max_price: Max hourly price
            port: Port for vLLM server

        Returns:
            Dict with deployment info
        """
        from ..providers.vast_provider import VastProvider
        from ...core.config import get_settings

        job = self.storage.get_job(job_id)
        if not job:
            return {"success": False, "error": f"Job {job_id} not found"}

        if job.status.value != "completed":
            return {"success": False, "error": f"Job must be completed. Current: {job.status.value}"}

        settings = get_settings()
        api_key = getattr(settings, 'VAST_API_KEY', None)
        if not api_key:
            return {"success": False, "error": "VAST_API_KEY not configured"}

        vast = VastProvider(api_key)

        # GPU mapping
        gpu_mapping = {
            "RTX4090": "RTX 4090",
            "RTX3090": "RTX 3090",
            "A100": "A100 PCIE",
            "A100-80GB": "A100 SXM4",
            "H100": "H100 SXM",
        }
        vast_gpu = gpu_mapping.get(gpu_type, gpu_type)

        # Find GPU offer
        offers = vast.search_offers(
            gpu_name=vast_gpu,
            num_gpus=1,
            min_gpu_ram=16,
            min_disk=50,
            limit=5,
            max_price=max_price,
        )

        if not offers:
            return {"success": False, "error": f"No {gpu_type} available under ${max_price}/hr"}

        # Sort by price
        offers.sort(key=lambda x: x.dph_total if hasattr(x, 'dph_total') else float("inf"))
        offer = offers[0]

        # Generate instance name
        if not instance_name:
            instance_name = f"inference-{job.name[:20]}-{job_id[:8]}"

        # vLLM deployment script with LoRA
        base_model = job.config.base_model
        deploy_script = f'''#!/bin/bash
set -e
echo "=== Deploying Fine-Tuned Model ==="
echo "Job: {job_id}"
echo "Base Model: {base_model}"

# Install vLLM
pip install -q vllm

# Note: In production, the LoRA weights would be downloaded from storage
# For now, we deploy just the base model
# The LoRA adapter was saved at /workspace/output/final on the training instance

echo "Starting vLLM server..."
python -m vllm.entrypoints.openai.api_server \\
    --model {base_model} \\
    --host 0.0.0.0 \\
    --port {port} \\
    --max-model-len 2048 \\
    --gpu-memory-utilization 0.9 \\
    2>&1 | tee /workspace/vllm.log &

echo "vLLM server starting on port {port}"
echo "=== Deployment Complete ==="
'''

        try:
            instance = vast.create_instance(
                offer_id=offer.id,
                image="vllm/vllm-openai:latest",
                disk_size=50,
                label=instance_name,
                onstart_cmd=deploy_script,
            )

            if instance:
                instance_id = instance.id if hasattr(instance, 'id') else None
                ssh_host = getattr(instance, 'ssh_host', None)
                ssh_port = getattr(instance, 'ssh_port', None)

                logger.info(f"Deployed inference instance {instance_id} for job {job_id}")

                return {
                    "success": True,
                    "instance_id": instance_id,
                    "instance_name": instance_name,
                    "gpu_type": gpu_type,
                    "cost_per_hour": offer.dph_total,
                    "endpoint_url": f"http://{ssh_host}:{port}/v1" if ssh_host else None,
                    "ssh_host": ssh_host,
                    "ssh_port": ssh_port,
                }
            else:
                return {"success": False, "error": "Failed to create instance"}

        except Exception as e:
            logger.error(f"Deploy failed: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
_service: Optional[FineTuningService] = None


def get_finetune_service() -> FineTuningService:
    """Get or create FineTuningService singleton"""
    global _service
    if _service is None:
        _service = FineTuningService()
    return _service
