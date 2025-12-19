"""
Domain model for Fine-Tuning jobs
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class FineTuneStatus(str, Enum):
    """Fine-tuning job status"""
    PENDING = "pending"
    UPLOADING = "uploading"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DatasetSource(str, Enum):
    """Dataset source type"""
    UPLOAD = "upload"
    URL = "url"
    HUGGINGFACE = "huggingface"


@dataclass
class FineTuneConfig:
    """Fine-tuning hyperparameters"""
    base_model: str  # e.g., "unsloth/llama-3-8b-bnb-4bit"
    lora_rank: int = 16
    lora_alpha: int = 16
    learning_rate: float = 2e-4
    epochs: int = 1
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    max_seq_length: int = 2048
    warmup_steps: int = 5
    weight_decay: float = 0.01
    output_dir: str = "/workspace/outputs"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'base_model': self.base_model,
            'lora_rank': self.lora_rank,
            'lora_alpha': self.lora_alpha,
            'learning_rate': self.learning_rate,
            'epochs': self.epochs,
            'batch_size': self.batch_size,
            'gradient_accumulation_steps': self.gradient_accumulation_steps,
            'max_seq_length': self.max_seq_length,
            'warmup_steps': self.warmup_steps,
            'weight_decay': self.weight_decay,
            'output_dir': self.output_dir,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FineTuneConfig":
        """Create from dictionary"""
        return cls(
            base_model=data.get('base_model', 'unsloth/llama-3-8b-bnb-4bit'),
            lora_rank=data.get('lora_rank', 16),
            lora_alpha=data.get('lora_alpha', 16),
            learning_rate=data.get('learning_rate', 2e-4),
            epochs=data.get('epochs', 1),
            batch_size=data.get('batch_size', 2),
            gradient_accumulation_steps=data.get('gradient_accumulation_steps', 4),
            max_seq_length=data.get('max_seq_length', 2048),
            warmup_steps=data.get('warmup_steps', 5),
            weight_decay=data.get('weight_decay', 0.01),
            output_dir=data.get('output_dir', '/workspace/outputs'),
        )


@dataclass
class FineTuneJob:
    """Represents a fine-tuning job"""
    id: str
    user_id: str
    name: str
    status: FineTuneStatus
    config: FineTuneConfig

    # Dataset info
    dataset_source: DatasetSource
    dataset_path: str  # R2 path or URL
    dataset_format: str = "alpaca"  # alpaca, sharegpt, custom

    # SkyPilot job info
    skypilot_job_id: Optional[int] = None
    skypilot_job_name: Optional[str] = None

    # GPU requirements
    gpu_type: str = "A100"
    num_gpus: int = 1

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Progress and metrics
    current_epoch: int = 0
    current_step: int = 0
    total_steps: int = 0
    loss: Optional[float] = None

    # Output
    output_model_path: Optional[str] = None
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'status': self.status.value,
            'config': self.config.to_dict(),
            'dataset_source': self.dataset_source.value,
            'dataset_path': self.dataset_path,
            'dataset_format': self.dataset_format,
            'skypilot_job_id': self.skypilot_job_id,
            'skypilot_job_name': self.skypilot_job_name,
            'gpu_type': self.gpu_type,
            'num_gpus': self.num_gpus,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'current_epoch': self.current_epoch,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'loss': self.loss,
            'output_model_path': self.output_model_path,
            'error_message': self.error_message,
            'logs': self.logs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FineTuneJob":
        """Create from dictionary"""
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            name=data['name'],
            status=FineTuneStatus(data['status']),
            config=FineTuneConfig.from_dict(data.get('config', {})),
            dataset_source=DatasetSource(data['dataset_source']),
            dataset_path=data['dataset_path'],
            dataset_format=data.get('dataset_format', 'alpaca'),
            skypilot_job_id=data.get('skypilot_job_id'),
            skypilot_job_name=data.get('skypilot_job_name'),
            gpu_type=data.get('gpu_type', 'A100'),
            num_gpus=data.get('num_gpus', 1),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            current_epoch=data.get('current_epoch', 0),
            current_step=data.get('current_step', 0),
            total_steps=data.get('total_steps', 0),
            loss=data.get('loss'),
            output_model_path=data.get('output_model_path'),
            error_message=data.get('error_message'),
            logs=data.get('logs', []),
        )

    @property
    def is_running(self) -> bool:
        """Check if job is running"""
        return self.status == FineTuneStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        """Check if job completed successfully"""
        return self.status == FineTuneStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if job failed"""
        return self.status == FineTuneStatus.FAILED

    @property
    def progress_percent(self) -> float:
        """Get progress percentage"""
        if self.total_steps == 0:
            return 0.0
        return (self.current_step / self.total_steps) * 100
