"""
Marketplace Module - Template Marketplace

Este modulo gerencia o marketplace de templates da comunidade:
- Templates: Criacao, publicacao e versionamento
- Compras: Processamento via Stripe com revenue split
- Avaliacoes: Sistema de ratings e reviews
- Descoberta: Busca e filtragem por categoria

Uso:
    from src.modules.marketplace import MarketplaceService, Template

    # Criar servico
    service = MarketplaceService(session_factory)

    # Listar templates
    templates = await service.list_templates(category=CategoryEnum.ML_TRAINING)

    # Buscar template
    template = await service.get_template(template_id=1)
"""

from .models import (
    Template,
    TemplateVersion,
    TemplatePurchase,
    TemplateRating,
    CategoryEnum,
    PricingType,
    TemplateStatus,
)

from .schemas import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListResponse,
    TemplateDetailResponse,
    VersionCreate,
    VersionResponse,
    RatingCreate,
    RatingResponse,
    PurchaseRequest,
    PurchaseResponse,
    PurchaseStatusResponse,
    DownloadResponse,
    CreatorTemplateStats,
    CreatorDashboardResponse,
)

from .service import (
    MarketplaceService,
    get_marketplace_service,
)

__all__ = [
    # Models
    "Template",
    "TemplateVersion",
    "TemplatePurchase",
    "TemplateRating",
    "CategoryEnum",
    "PricingType",
    "TemplateStatus",
    # Schemas - Template
    "TemplateCreate",
    "TemplateUpdate",
    "TemplateResponse",
    "TemplateListResponse",
    "TemplateDetailResponse",
    # Schemas - Version
    "VersionCreate",
    "VersionResponse",
    # Schemas - Rating
    "RatingCreate",
    "RatingResponse",
    # Schemas - Purchase
    "PurchaseRequest",
    "PurchaseResponse",
    "PurchaseStatusResponse",
    # Schemas - Download
    "DownloadResponse",
    # Schemas - Dashboard
    "CreatorTemplateStats",
    "CreatorDashboardResponse",
    # Service
    "MarketplaceService",
    "get_marketplace_service",
]
