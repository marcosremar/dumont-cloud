"""
Model Image Registry

Maps model types to pre-built Docker images with fixed, tested versions.
Each image contains all dependencies and the server code ready to run.

Usage:
    from src.modules.models.images import get_image_for_model

    config = get_image_for_model("speech")
    # Returns: {
    #     "image": "dumontcloud/whisper:4.40-cuda12.1",
    #     "port": 8001,
    #     "start_cmd": "python /app/whisper_server.py",
    #     ...
    # }
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ImageConfig:
    """Configuration for a model image"""
    image: str
    port: int
    start_cmd: str
    health_endpoint: str = "/health"
    env_vars: Dict[str, str] = None

    def __post_init__(self):
        if self.env_vars is None:
            self.env_vars = {}


# Public Docker images - no login required
# vLLM uses official image, others use public alternatives or fallback to runtime_templates
MODEL_IMAGES: Dict[str, Dict[str, Any]] = {
    "llm": {
        # Use pytorch base + vLLM install at runtime
        # Note: Official vllm/vllm-openai image doesn't have SSH configured for Vast.ai
        "image": "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
        "port": 8000,
        "start_cmd": "",
        "health_endpoint": "/health",
        "env_vars": {"GPU_MEMORY_UTILIZATION": "0.9"},
        "description": "vLLM server for LLMs (Llama, Mistral, Qwen, etc)",
        "min_vram_gb": 8,
        "use_fallback": True,  # Use runtime_templates for now
    },

    "speech": {
        # Use pytorch base + transformers/whisper install at runtime
        # Note: Public whisper images don't have SSH configured for Vast.ai
        "image": "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
        "port": 8001,
        "start_cmd": "",
        "health_endpoint": "/health",
        "env_vars": {},
        "description": "Whisper server for speech-to-text",
        "min_vram_gb": 4,
        "use_fallback": True,  # Use runtime_templates for now
    },

    "image": {
        # Use pytorch base + runtime_templates fallback for now
        "image": "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
        "port": 8002,
        "start_cmd": "",  # Uses fallback to runtime_templates
        "health_endpoint": "/health",
        "env_vars": {},
        "description": "Diffusers server for image generation (SDXL, FLUX)",
        "min_vram_gb": 12,
        "use_fallback": True,  # Signal to use runtime_templates
    },

    "embeddings": {
        # Use pytorch base + runtime_templates fallback for now
        "image": "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
        "port": 8003,
        "start_cmd": "",
        "health_endpoint": "/health",
        "env_vars": {},
        "description": "Sentence-Transformers for text embeddings",
        "min_vram_gb": 2,
        "use_fallback": True,
    },

    "vision": {
        # Use pytorch base + runtime_templates fallback for now
        "image": "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
        "port": 8004,
        "start_cmd": "",
        "health_endpoint": "/health",
        "env_vars": {},
        "description": "Vision-Language models (SmolVLM, LLaVA)",
        "min_vram_gb": 4,
        "use_fallback": True,
    },

    "video": {
        # Use pytorch base + runtime_templates fallback for now
        "image": "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
        "port": 8005,
        "start_cmd": "",
        "health_endpoint": "/health",
        "env_vars": {},
        "description": "Video generation (ModelScope, CogVideoX)",
        "min_vram_gb": 16,
        "use_fallback": True,
    },
}

# Fallback to legacy runtime_templates.py if image not available
FALLBACK_IMAGE = "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime"


def get_image_for_model(model_type: str) -> Dict[str, Any]:
    """
    Get Docker image configuration for a model type.

    Args:
        model_type: One of "llm", "speech", "image", "embeddings", "vision", "video"

    Returns:
        Dict with image, port, start_cmd, health_endpoint, env_vars

    Raises:
        ValueError: If model_type is not supported
    """
    if model_type not in MODEL_IMAGES:
        raise ValueError(
            f"Unknown model type: {model_type}. "
            f"Supported: {list(MODEL_IMAGES.keys())}"
        )

    return MODEL_IMAGES[model_type]


def get_start_command(model_type: str, model_id: str, port: Optional[int] = None) -> str:
    """
    Get the start command for a model, with variables substituted.

    Args:
        model_type: Model type
        model_id: HuggingFace model ID
        port: Override port (optional)

    Returns:
        Command string ready to execute
    """
    config = get_image_for_model(model_type)
    cmd = config["start_cmd"]

    # Substitute variables
    actual_port = port or config["port"]
    cmd = cmd.replace("$MODEL_ID", model_id)
    cmd = cmd.replace("$PORT", str(actual_port))

    return cmd


def get_model_port(model_type: str) -> int:
    """Get default port for a model type"""
    return get_image_for_model(model_type)["port"]


def image_exists(model_type: str) -> bool:
    """Check if pre-built image is available for model type"""
    return model_type in MODEL_IMAGES


def get_fallback_image() -> str:
    """Get fallback base image for legacy runtime_templates flow"""
    return FALLBACK_IMAGE
