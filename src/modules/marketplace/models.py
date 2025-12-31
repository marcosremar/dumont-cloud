"""
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
