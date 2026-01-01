"""
Marketplace Module - Template Marketplace for Pre-Configured ML Workloads

Este modulo gerencia templates pre-configurados para workloads de ML:
- Template metadata e configuracoes (GPU requirements, Docker images, ports)
- Catalogo de templates oficiais (JupyterLab, Stable Diffusion, ComfyUI, vLLM)
- One-click deployment com dependencias GPU configuradas

Uso:
    from src.modules.marketplace import (
        Template,
        TemplateService,
        get_template_service,
    )

    service = get_template_service()
    templates = service.get_all_templates()
    deployment = await service.deploy_template(slug="jupyter-lab", gpu_id=123)
"""

# Models
from .models import (
    Template,
    TemplateGPURequirements,
    TemplateCategory,
)

# Service will be imported here after subtask-2-1 creates it
# from .service import (
#     TemplateService,
#     get_template_service,
# )

__all__: list[str] = [
    # Models
    "Template",
    "TemplateGPURequirements",
    "TemplateCategory",
    # Service will be added after subtask-2-1:
    # "TemplateService",
    # "get_template_service",
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
