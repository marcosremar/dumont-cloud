"""
Marketplace Models - Dataclasses para templates de workloads ML
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TemplateCategory(str, Enum):
    """Categoria do template"""
    NOTEBOOK = "notebook"
    IMAGE_GENERATION = "image_generation"
    LLM_INFERENCE = "llm_inference"
    TRAINING = "training"


@dataclass
class TemplateGPURequirements:
    """Requisitos de GPU para um template"""
    min_vram: int  # GB
    recommended_vram: int  # GB
    cuda_version: str = "11.8"

    def is_compatible(self, available_vram: int) -> bool:
        """Verifica se a GPU disponivel e compativel"""
        return available_vram >= self.min_vram

    def is_recommended(self, available_vram: int) -> bool:
        """Verifica se a GPU atende o recomendado"""
        return available_vram >= self.recommended_vram

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_vram": self.min_vram,
            "recommended_vram": self.recommended_vram,
            "cuda_version": self.cuda_version,
        }


@dataclass
class Template:
    """Template pre-configurado para workload ML"""
    id: int
    name: str
    slug: str
    docker_image: str

    # GPU requirements
    gpu_min_vram: int  # GB
    gpu_recommended_vram: int  # GB

    # Container config
    ports: List[int] = field(default_factory=list)
    volumes: List[str] = field(default_factory=list)
    launch_command: str = ""

    # CUDA version
    cuda_version: str = "11.8"

    # Optional metadata
    description: str = ""
    category: TemplateCategory = TemplateCategory.NOTEBOOK
    icon_url: str = ""
    documentation_url: str = ""

    # Environment variables
    env_vars: Dict[str, str] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    # Flags
    is_active: bool = True
    is_verified: bool = False

    @property
    def gpu_requirements(self) -> TemplateGPURequirements:
        """Retorna requisitos de GPU como objeto"""
        return TemplateGPURequirements(
            min_vram=self.gpu_min_vram,
            recommended_vram=self.gpu_recommended_vram,
            cuda_version=self.cuda_version,
        )

    def is_gpu_compatible(self, available_vram: int) -> bool:
        """Verifica se a GPU disponivel e compativel com o template"""
        return available_vram >= self.gpu_min_vram

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "docker_image": self.docker_image,
            "gpu_min_vram": self.gpu_min_vram,
            "gpu_recommended_vram": self.gpu_recommended_vram,
            "cuda_version": self.cuda_version,
            "ports": self.ports,
            "volumes": self.volumes,
            "launch_command": self.launch_command,
            "env_vars": self.env_vars,
            "category": self.category.value,
            "icon_url": self.icon_url,
            "documentation_url": self.documentation_url,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Template":
        """Cria Template a partir de dicionario"""
        # Handle category conversion
        category = data.get("category", "notebook")
        if isinstance(category, str):
            category = TemplateCategory(category)

        # Handle datetime conversion
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        return cls(
            id=data["id"],
            name=data["name"],
            slug=data["slug"],
            docker_image=data["docker_image"],
            gpu_min_vram=data.get("gpu_min_vram", 4),
            gpu_recommended_vram=data.get("gpu_recommended_vram", 8),
            ports=data.get("ports", []),
            volumes=data.get("volumes", []),
            launch_command=data.get("launch_command", ""),
            cuda_version=data.get("cuda_version", "11.8"),
            description=data.get("description", ""),
            category=category,
            icon_url=data.get("icon_url", ""),
            documentation_url=data.get("documentation_url", ""),
            env_vars=data.get("env_vars", {}),
            created_at=created_at,
            updated_at=updated_at,
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
        )
