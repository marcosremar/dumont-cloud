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
]
