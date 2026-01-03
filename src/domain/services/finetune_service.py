"""
Fine-Tuning Service - Domain Service (Business Logic)
Orchestrates fine-tuning operations using SkyPilot
"""
import logging
import uuid
import os
import tempfile
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
    Orchestrates operations between SkyPilot provider and storage.
    """

    def __init__(self):
        """Initialize fine-tuning service"""
        self.skypilot = get_skypilot_provider()
        self.vast_finetune = get_vast_finetune_provider()
        self.storage = get_finetune_storage()
        self.template_dir = TEMPLATE_DIR

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

        # Try SkyPilot first, then VAST.ai as fallback
        if self.is_skypilot_available:
            success = self._start_job_skypilot(job)
            if success:
                return True
            # If SkyPilot failed (e.g., no cloud provider configured), try VAST.ai
            job = self.storage.get_job(job_id)  # Refresh job state
            if job and job.status == FineTuneStatus.FAILED and self.is_vast_available:
                self.storage.add_job_log(job_id, "Falling back to VAST.ai backend...")
                self.storage.update_job_status(job_id, FineTuneStatus.QUEUED)
                return self._start_job_vast(job)
            return False
        elif self.is_vast_available:
            return self._start_job_vast(job)
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
        """Start job via VAST.ai directly"""
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

    def list_jobs(self, user_id: str) -> List[FineTuneJob]:
        """
        List all jobs for a user.

        Args:
            user_id: User ID

        Returns:
            List of FineTuneJob
        """
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

        # Cancel SkyPilot job if we have the ID
        if job.skypilot_job_id:
            success = self.skypilot.cancel_job(job.skypilot_job_id)
            if not success:
                logger.warning(f"Failed to cancel SkyPilot job {job.skypilot_job_id}")

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


# Singleton instance
_service: Optional[FineTuningService] = None


def get_finetune_service() -> FineTuningService:
    """Get or create FineTuningService singleton"""
    global _service
    if _service is None:
        _service = FineTuningService()
    return _service
