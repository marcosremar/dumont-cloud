"""
VAST.ai Fine-Tuning Provider
Alternative to SkyPilot for running fine-tuning jobs directly on VAST.ai
"""
import logging
import json
import time
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from .vast_provider import VastProvider
from ...core.config import get_settings

logger = logging.getLogger(__name__)

# Unsloth fine-tuning Docker image (has CUDA, PyTorch, Unsloth pre-installed)
FINETUNE_IMAGE = "unsloth/unsloth:latest"

# Fine-tuning script template - runs entirely on the remote GPU machine
# All dependencies are installed and training happens on VAST.ai
FINETUNE_SCRIPT = """#!/bin/bash
set -e
echo "=== Dumont Cloud Fine-Tuning ==="
echo "Starting at $(date)"

# Create workspace
mkdir -p /workspace/output
cd /workspace

# Install additional dependencies (unsloth image already has most)
echo "Installing dependencies..."
pip install -q datasets trl accelerate bitsandbytes psutil 2>&1 | tail -5

# Create training script
echo "Creating training script..."
cat > train.py << 'TRAINSCRIPT'
import os
import sys
import builtins
import psutil
# Inject psutil into builtins to fix Unsloth compiled cache bug
builtins.psutil = psutil
import torch
print(f"PyTorch: {{torch.__version__}}, CUDA: {{torch.cuda.is_available()}}")
print(f"GPU: {{torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}}")

from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments

# Config
BASE_MODEL = "{base_model}"
MAX_SEQ_LEN = min({max_seq_length}, 2048)  # Limit for memory
LORA_R = {lora_rank}
LORA_ALPHA = {lora_alpha}
EPOCHS = {epochs}
BATCH_SIZE = min({batch_size}, 4)  # Reasonable batch size
LR = {learning_rate}

print(f"Loading model: {{BASE_MODEL}}")
model, tokenizer = FastLanguageModel.from_pretrained(
    BASE_MODEL,
    max_seq_length=MAX_SEQ_LEN,
    load_in_4bit=True,
    dtype=None,
)

print("Applying LoRA...")
model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
)

print("Loading dataset: {dataset_path}")
try:
    dataset = load_dataset("{dataset_path}", split="train[:1000]")
except:
    # Fallback to alpaca dataset
    dataset = load_dataset("yahma/alpaca-cleaned", split="train[:1000]")

def format_prompt(example):
    instruction = example.get("instruction", "")
    input_text = example.get("input", "")
    output = example.get("output", "")
    if input_text:
        text = f"### Instruction:\\n{{instruction}}\\n\\n### Input:\\n{{input_text}}\\n\\n### Response:\\n{{output}}"
    else:
        text = f"### Instruction:\\n{{instruction}}\\n\\n### Response:\\n{{output}}"
    return {{"text": text}}

dataset = dataset.map(format_prompt)
print(f"Dataset size: {{len(dataset)}}")

print("Starting training...")
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LEN,
    args=TrainingArguments(
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=4,
        num_train_epochs=EPOCHS,
        learning_rate=LR,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        output_dir="/workspace/output",
        save_strategy="epoch",
        warmup_ratio=0.03,
        optim="adamw_8bit",
        report_to="none",  # Disable wandb
    ),
)

trainer.train()

print("Saving model...")
model.save_pretrained("/workspace/output/final")
tokenizer.save_pretrained("/workspace/output/final")

print("=== Training Complete! ===")
print(f"Model saved to: /workspace/output/final")
TRAINSCRIPT

# Run training
echo "Starting training..."
python train.py 2>&1 | tee /workspace/training.log

echo "=== Fine-Tuning Complete ==="
echo "Finished at $(date)"
"""


class VastFineTuneProvider:
    """
    VAST.ai provider for fine-tuning jobs.
    Uses VAST.ai directly instead of SkyPilot.
    """

    def __init__(self):
        settings = get_settings()
        # Handle missing VAST_API_KEY gracefully
        self.api_key = getattr(settings, 'VAST_API_KEY', None) or os.environ.get('VAST_API_KEY')
        self.vast = VastProvider(self.api_key) if self.api_key else None
        self._available = None

    @property
    def is_available(self) -> bool:
        """Check if VAST.ai is available"""
        if self._available is None:
            self._available = self._verify_vast()
        return self._available

    def _verify_vast(self) -> bool:
        """Verify VAST.ai API access"""
        if not self.vast:
            logger.warning("VAST API key not configured")
            return False
        try:
            # Try to list offers to verify API access (any GPU with 8GB+)
            offers = self.vast.search_offers(num_gpus=1, limit=1, max_price=10.0, min_gpu_ram=8)
            return len(offers) > 0
        except Exception as e:
            logger.warning(f"VAST.ai not available: {e}")
            return False

    def _find_gpu_offer(self, gpu_type: str) -> Optional[Dict[str, Any]]:
        """Find a suitable GPU offer on VAST.ai"""
        if not self.vast:
            return None

        # GPU mapping to VAST.ai naming convention (with spaces)
        gpu_mapping = {
            "RTX3060": "RTX 3060",
            "RTX3070": "RTX 3070",
            "RTX3080": "RTX 3080",
            "RTX3090": "RTX 3090",
            "RTX4070": "RTX 4070",
            "RTX4080": "RTX 4080",
            "RTX4090": "RTX 4090",
            "RTX5090": "RTX 5090",
            "A100": "A100 PCIE",
            "A100-80GB": "A100 SXM4",
            "H100": "H100 SXM",
            "H200": "H200",
            "L40": "L40",
            "L40S": "L40S",
        }

        vast_gpu = gpu_mapping.get(gpu_type, gpu_type)

        try:
            offers = self.vast.search_offers(
                gpu_name=vast_gpu,
                num_gpus=1,
                min_gpu_ram=12,  # GB - lower for RTX 3090 (24GB) etc
                min_disk=50,  # GB
                limit=5,
                max_price=10.0,  # Max $10/hr
            )

            if offers:
                # Sort by price and return cheapest (offers are GpuOffer objects)
                offers.sort(key=lambda x: x.dph_total if hasattr(x, 'dph_total') else float("inf"))
                offer = offers[0]
                # Convert GpuOffer to dict for compatibility
                return offer.to_dict() if hasattr(offer, 'to_dict') else {
                    "id": offer.id,
                    "gpu_name": offer.gpu_name,
                    "dph_total": offer.dph_total,
                    "gpu_ram": offer.gpu_ram,
                    "disk_space": offer.disk_space,
                }
            return None
        except Exception as e:
            logger.error(f"Error searching GPU offers: {e}")
            return None

    def launch_finetune_job(
        self,
        job_name: str,
        base_model: str,
        dataset_path: str,
        dataset_format: str = "alpaca",
        gpu_type: str = "RTX4090",
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Launch a fine-tuning job on VAST.ai.

        Args:
            job_name: Unique name for the job
            base_model: Model ID (e.g., unsloth/tinyllama-bnb-4bit)
            dataset_path: URL or path to dataset
            dataset_format: alpaca or sharegpt
            gpu_type: GPU type to use
            config: Additional config (lora_rank, epochs, etc.)

        Returns:
            Dict with job info or error
        """
        if not self.is_available:
            return {"success": False, "error": "VAST.ai not available"}

        config = config or {}
        lora_rank = config.get("lora_rank", 16)
        lora_alpha = config.get("lora_alpha", 16)
        epochs = config.get("epochs", 1)
        batch_size = config.get("batch_size", 2)
        learning_rate = config.get("learning_rate", 2e-4)
        max_seq_length = config.get("max_seq_length", 2048)

        logger.info(f"Launching fine-tuning job: {job_name} on {gpu_type}")

        # Find GPU offer
        offer = self._find_gpu_offer(gpu_type)
        if not offer:
            return {"success": False, "error": f"No {gpu_type} available on VAST.ai"}

        # Generate training script
        script = FINETUNE_SCRIPT.format(
            base_model=base_model,
            dataset_path=dataset_path,
            dataset_format=dataset_format,
            lora_rank=lora_rank,
            lora_alpha=lora_alpha,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            max_seq_length=max_seq_length,
        )

        try:
            # Create instance (use correct parameter names)
            instance = self.vast.create_instance(
                offer_id=offer["id"],
                image=FINETUNE_IMAGE,
                disk_size=50,
                label=job_name,
                onstart_cmd=script,
            )

            if instance:
                # Instance is an Instance object, get id from it
                instance_id = instance.id if hasattr(instance, 'id') else instance.get("id") if isinstance(instance, dict) else None
                logger.info(f"Created instance {instance_id} for job {job_name}")
                return {
                    "success": True,
                    "job_id": instance_id,
                    "job_name": job_name,
                    "instance_id": instance_id,
                    "gpu": gpu_type,
                    "offer_id": offer["id"],
                    "cost_per_hour": offer.get("dph_total"),
                }
            else:
                return {"success": False, "error": "Failed to create instance"}

        except Exception as e:
            logger.error(f"Error launching job: {e}")
            return {"success": False, "error": str(e)}

    def get_job_status(self, instance_id: int) -> Dict[str, Any]:
        """Get status of a fine-tuning job"""
        if not self.vast:
            return {"error": "VAST.ai not available"}

        try:
            instance = self.vast.get_instance(instance_id)
            if instance:
                # Instance is an Instance object, access attributes directly
                return {
                    "instance_id": instance_id,
                    "status": getattr(instance, 'actual_status', None) or getattr(instance, 'status', 'unknown'),
                    "ssh_host": getattr(instance, 'ssh_host', None),
                    "ssh_port": getattr(instance, 'ssh_port', None),
                    "gpu": getattr(instance, 'gpu_name', None),
                    "cost_per_hour": getattr(instance, 'dph_total', None),
                }
            return {"error": "Instance not found"}
        except Exception as e:
            return {"error": str(e)}

    def cancel_job(self, instance_id: int) -> bool:
        """Cancel/destroy a fine-tuning job"""
        if not self.vast:
            return False

        try:
            return self.vast.destroy_instance(instance_id)
        except Exception as e:
            logger.error(f"Error cancelling job: {e}")
            return False

    def get_job_logs(self, instance_id: int, tail: int = 100) -> str:
        """Get logs from a job (requires SSH access)"""
        # For now, return a placeholder - SSH log fetching would require more setup
        return f"Logs for instance {instance_id} - SSH access required for full logs"


# Singleton
_vast_finetune_provider: Optional[VastFineTuneProvider] = None


def get_vast_finetune_provider() -> VastFineTuneProvider:
    """Get or create VastFineTuneProvider singleton"""
    global _vast_finetune_provider
    if _vast_finetune_provider is None:
        _vast_finetune_provider = VastFineTuneProvider()
    return _vast_finetune_provider
