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
Marketplace Module - Database Models

Modelos para gerenciamento de templates do marketplace:
- Template: Template publicado no marketplace
- TemplateVersion: Versao de um template (imutavel)
- TemplatePurchase: Compra de template premium
- TemplateRating: Avaliacao de template
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Enum, ForeignKey, BigInteger, UniqueConstraint
)
from sqlalchemy.orm import relationship

from src.config.database import Base


class CategoryEnum(enum.Enum):
    """Categorias de template"""
    ML_TRAINING = "ml_training"
    INFERENCE = "inference"
    CREATIVE = "creative"
    DEVELOPMENT = "development"


class PricingType(enum.Enum):
    """Tipo de precificacao do template"""
    FREE = "free"
    PREMIUM = "premium"


class TemplateStatus(enum.Enum):
    """Status do template no marketplace"""
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Template(Base):
    """
    Template publicado no marketplace.

    Templates sao imutaveis apos publicacao - novas versoes
    devem ser criadas para modificacoes.
    """
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificacao
    user_id = Column(String(255), nullable=False, index=True)  # Criador do template
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)  # URL-friendly name
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)

    # Classificacao
    category = Column(Enum(CategoryEnum), nullable=False, index=True)
    tags = Column(Text, nullable=True)  # JSON array of tags

    # Precificacao
    pricing_type = Column(Enum(PricingType), default=PricingType.FREE)
    price_cents = Column(Integer, default=0)  # Preco em centavos USD

    # Status
    status = Column(Enum(TemplateStatus), default=TemplateStatus.PENDING_REVIEW, index=True)
    rejection_reason = Column(Text, nullable=True)

    # Metricas
    download_count = Column(Integer, default=0)
    rating_sum = Column(Integer, default=0)  # Soma das avaliacoes
    rating_count = Column(Integer, default=0)  # Numero de avaliacoes

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    # Relacionamentos
    versions = relationship("TemplateVersion", back_populates="template", lazy="dynamic")
    purchases = relationship("TemplatePurchase", back_populates="template", lazy="dynamic")
    ratings = relationship("TemplateRating", back_populates="template", lazy="dynamic")

    def __repr__(self):
        return f"<Template {self.id}: {self.name} ({self.status.value})>"

    @property
    def price_usd(self) -> float:
        """Preco em USD"""
        return self.price_cents / 100

    @property
    def average_rating(self) -> Optional[float]:
        """Rating medio (1-5)"""
        if self.rating_count == 0:
            return None
        return self.rating_sum / self.rating_count

    @property
    def is_free(self) -> bool:
        """Verifica se template e gratuito"""
        return self.pricing_type == PricingType.FREE

    @property
    def is_published(self) -> bool:
        """Verifica se template esta publicado"""
        return self.status == TemplateStatus.APPROVED


class TemplateVersion(Base):
    """
    Versao de um template.

    Cada versao e imutavel e armazenada separadamente no B2.
    Usa semantic versioning (MAJOR.MINOR.PATCH).
    """
    __tablename__ = "template_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Referencia ao template
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False, index=True)

    # Versao (semver)
    version = Column(String(50), nullable=False)  # Ex: "1.0.0", "2.1.3"
    changelog = Column(Text, nullable=True)

    # Storage
    file_key = Column(String(500), nullable=False)  # Caminho no B2: templates/{user_id}/{template_id}/{version}/template.zip
    size_bytes = Column(BigInteger, default=0)
    checksum = Column(String(64), nullable=True)  # SHA-256

    # Status
    is_latest = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamento
    template = relationship("Template", back_populates="versions")

    def __repr__(self):
        return f"<TemplateVersion {self.id}: template={self.template_id} v{self.version}>"

    @property
    def size_mb(self) -> float:
        """Tamanho em MB"""
        return self.size_bytes / (1024 * 1024)


class TemplatePurchase(Base):
    """
    Registro de compra de template premium.

    Rastreia pagamentos e controla acesso ao download.
    Revenue split: 70% criador, 30% plataforma.
    """
    __tablename__ = "template_purchases"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Referencia ao template e usuario
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)  # Comprador

    # Stripe
    stripe_payment_intent_id = Column(String(255), nullable=True, unique=True)
    stripe_charge_id = Column(String(255), nullable=True)

    # Valores (em centavos USD)
    amount_paid = Column(Integer, nullable=False)  # Valor total pago
    creator_earnings = Column(Integer, nullable=False)  # 70% para criador
    platform_fee = Column(Integer, nullable=False)  # 30% para plataforma

    # Status
    status = Column(String(50), default="pending")  # pending, completed, refunded, failed

    # Timestamps
    purchased_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relacionamento
    template = relationship("Template", back_populates="purchases")

    # Constraint: um usuario so pode comprar um template uma vez
    __table_args__ = (
        UniqueConstraint('template_id', 'user_id', name='uq_template_purchase_user'),
    )

    def __repr__(self):
        return f"<TemplatePurchase {self.id}: template={self.template_id} user={self.user_id}>"


class TemplateRating(Base):
    """
    Avaliacao de template por usuario.

    Apenas usuarios que baixaram/compraram podem avaliar.
    Rating de 1 a 5 estrelas (inteiros).
    """
    __tablename__ = "template_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Referencia ao template e usuario
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    # Avaliacao
    rating = Column(Integer, nullable=False)  # 1-5
    review_text = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento
    template = relationship("Template", back_populates="ratings")

    # Constraint: um usuario so pode avaliar um template uma vez
    __table_args__ = (
        UniqueConstraint('template_id', 'user_id', name='uq_template_rating_user'),
    )

    def __repr__(self):
        return f"<TemplateRating {self.id}: template={self.template_id} rating={self.rating}>"


# Indices adicionais para queries comuns
from sqlalchemy import Index

Index('idx_templates_user_status', Template.user_id, Template.status)
Index('idx_templates_category_status', Template.category, Template.status)
Index('idx_template_versions_template', TemplateVersion.template_id, TemplateVersion.is_latest)
Index('idx_template_purchases_user', TemplatePurchase.user_id)
Index('idx_template_ratings_template', TemplateRating.template_id)
