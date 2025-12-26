"""
Docker Image Registry for Model Deployment

Maps model types to pre-built Docker images with all dependencies installed.
No pip install at runtime = reproducible, fast deploys.
"""

from .registry import (
    MODEL_IMAGES,
    get_image_for_model,
    get_start_command,
    get_model_port,
)

__all__ = [
    "MODEL_IMAGES",
    "get_image_for_model",
    "get_start_command",
    "get_model_port",
]
