"""
Marketplace Module - Pydantic Schemas

Schemas para validacao de request/response da API de marketplace.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class CategoryEnum(str, Enum):
    """Categorias de template"""
    ML_TRAINING = "ml_training"
    INFERENCE = "inference"
    CREATIVE = "creative"
    DEVELOPMENT = "development"


class PricingType(str, Enum):
    """Tipo de precificacao"""
    FREE = "free"
    PREMIUM = "premium"


class TemplateStatus(str, Enum):
    """Status do template"""
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


# ==================== Template Schemas ====================

class TemplateCreate(BaseModel):
    """Schema para criacao de template"""
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    category: CategoryEnum
    pricing_type: PricingType = PricingType.FREE
    price_cents: int = Field(default=0, ge=0)
    tags: Optional[List[str]] = None

    @field_validator('price_cents')
    @classmethod
    def validate_price(cls, v, info):
        """Valida preco baseado no tipo de precificacao"""
        pricing_type = info.data.get('pricing_type')
        if pricing_type == PricingType.PREMIUM and v <= 0:
            raise ValueError('Premium templates must have a price greater than 0')
        if pricing_type == PricingType.FREE and v > 0:
            raise ValueError('Free templates cannot have a price')
        return v


class TemplateUpdate(BaseModel):
    """Schema para atualizacao de template (apenas metadata, nao conteudo)"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = None
    # Nota: pricing_type e price_cents nao podem ser alterados apos publicacao


class TemplateResponse(BaseModel):
    """Schema de resposta para template"""
    id: int
    user_id: str
    name: str
    slug: str
    description: Optional[str]
    short_description: Optional[str]
    category: CategoryEnum
    pricing_type: PricingType
    price_cents: int
    price_usd: float
    status: TemplateStatus
    download_count: int
    average_rating: Optional[float]
    rating_count: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    is_free: bool
    is_published: bool
    # Versao mais recente
    latest_version: Optional[str] = None

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Schema de resposta para lista de templates"""
    templates: List[TemplateResponse]
    total: int
    limit: int
    offset: int


class TemplateDetailResponse(TemplateResponse):
    """Schema de resposta detalhada para template"""
    versions: List["VersionResponse"] = []
    ratings: List["RatingResponse"] = []
    user_has_purchased: bool = False
    user_can_download: bool = False
    creator_name: Optional[str] = None


# ==================== Version Schemas ====================

class VersionCreate(BaseModel):
    """Schema para criacao de versao"""
    version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$')  # Semver: MAJOR.MINOR.PATCH
    changelog: Optional[str] = None


class VersionResponse(BaseModel):
    """Schema de resposta para versao"""
    id: int
    template_id: int
    version: str
    changelog: Optional[str]
    size_bytes: int
    size_mb: float
    is_latest: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Rating Schemas ====================

class RatingCreate(BaseModel):
    """Schema para criacao de avaliacao"""
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = Field(None, max_length=2000)


class RatingResponse(BaseModel):
    """Schema de resposta para avaliacao"""
    id: int
    template_id: int
    user_id: str
    rating: int
    review_text: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Purchase Schemas ====================

class PurchaseRequest(BaseModel):
    """Schema para requisicao de compra"""
    payment_method_id: str  # ID do payment method do Stripe


class PurchaseResponse(BaseModel):
    """Schema de resposta para compra"""
    id: int
    template_id: int
    user_id: str
    amount_paid: int
    status: str
    purchased_at: datetime
    completed_at: Optional[datetime]
    # Para confirmacao no frontend
    client_secret: Optional[str] = None

    class Config:
        from_attributes = True


class PurchaseStatusResponse(BaseModel):
    """Schema de resposta para status de compra"""
    purchased: bool
    purchase_id: Optional[int] = None
    purchased_at: Optional[datetime] = None


# ==================== Download Schemas ====================

class DownloadResponse(BaseModel):
    """Schema de resposta para download"""
    download_url: str
    expires_at: datetime
    version: str
    file_size_bytes: int


# ==================== Creator Dashboard Schemas ====================

class CreatorTemplateStats(BaseModel):
    """Estatisticas de template para dashboard do criador"""
    template_id: int
    name: str
    status: TemplateStatus
    download_count: int
    average_rating: Optional[float]
    rating_count: int
    total_earnings_cents: int
    total_earnings_usd: float


class CreatorDashboardResponse(BaseModel):
    """Resposta do dashboard do criador"""
    templates: List[CreatorTemplateStats]
    total_templates: int
    total_downloads: int
    total_earnings_cents: int
    total_earnings_usd: float
    stripe_account_id: Optional[str] = None
    stripe_onboarding_complete: bool = False


# Forward references
TemplateDetailResponse.model_rebuild()
