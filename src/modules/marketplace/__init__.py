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

# Models will be imported here after subtask-1-2 creates them
# from .models import (
#     Template,
#     TemplateGPURequirements,
# )

# Service will be imported here after subtask-2-1 creates it
# from .service import (
#     TemplateService,
#     get_template_service,
# )

__all__: list[str] = [
    # Future exports will be added as submodules are created:
    # "Template",
    # "TemplateGPURequirements",
    # "TemplateService",
    # "get_template_service",
]
