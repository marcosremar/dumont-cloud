"""
Template Marketplace API endpoints
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])


# =============================================================================
# Response Schemas
# =============================================================================

class TemplateGPURequirementsResponse(BaseModel):
    """GPU requirements for a template"""
    min_vram: int = Field(..., description="Minimum VRAM required in GB")
    recommended_vram: int = Field(..., description="Recommended VRAM in GB")
    cuda_version: str = Field("11.8", description="Required CUDA version")


class TemplateResponse(BaseModel):
    """Template response schema"""
    id: int = Field(..., description="Template ID")
    name: str = Field(..., description="Template display name")
    slug: str = Field(..., description="Template URL slug")
    description: str = Field("", description="Template description")
    docker_image: str = Field(..., description="Docker image to use")
    gpu_min_vram: int = Field(..., description="Minimum GPU VRAM in GB")
    gpu_recommended_vram: int = Field(..., description="Recommended GPU VRAM in GB")
    cuda_version: str = Field("11.8", description="Required CUDA version")
    ports: List[int] = Field(default_factory=list, description="Exposed ports")
    volumes: List[str] = Field(default_factory=list, description="Volume mounts")
    launch_command: str = Field("", description="Container launch command")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    category: str = Field("notebook", description="Template category")
    icon_url: str = Field("", description="Template icon URL")
    documentation_url: str = Field("", description="Documentation URL")
    is_active: bool = Field(True, description="Template is active")
    is_verified: bool = Field(False, description="Template is verified")

    class Config:
        from_attributes = True


class ListTemplatesResponse(BaseModel):
    """List templates response"""
    templates: List[TemplateResponse] = Field(..., description="List of templates")
    count: int = Field(..., description="Number of templates")


# =============================================================================
# Template Service Dependency
# =============================================================================

def get_template_service():
    """Get template service instance"""
    from services.template_service import TemplateService
    return TemplateService()


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=ListTemplatesResponse)
async def list_templates(
    min_vram: Optional[int] = Query(None, description="Filter templates requiring <= this VRAM (GB)"),
    category: Optional[str] = Query(None, description="Filter by category: notebook, image_generation, llm_inference, training"),
    verified_only: bool = Query(False, description="Only return verified templates"),
):
    """
    List all available templates

    Returns all active templates from the marketplace.
    Supports filtering by GPU VRAM requirements and category.

    Query Parameters:
    - min_vram: Filter templates that require <= specified VRAM (in GB)
    - category: Filter by template category
    - verified_only: Only return verified/tested templates
    """
    try:
        service = get_template_service()

        # Get base templates
        if verified_only:
            templates = service.get_verified_templates()
        elif min_vram is not None:
            templates = service.filter_by_vram(min_vram)
        else:
            templates = service.get_all_templates()

        # Apply category filter if specified
        if category:
            from src.modules.marketplace.models import TemplateCategory
            try:
                category_enum = TemplateCategory(category)
                templates = [t for t in templates if t.category == category_enum]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {category}. Valid values: notebook, image_generation, llm_inference, training"
                )

        # Convert to response format
        template_responses = [
            TemplateResponse(
                id=t.id,
                name=t.name,
                slug=t.slug,
                description=t.description,
                docker_image=t.docker_image,
                gpu_min_vram=t.gpu_min_vram,
                gpu_recommended_vram=t.gpu_recommended_vram,
                cuda_version=t.cuda_version,
                ports=t.ports,
                volumes=t.volumes,
                launch_command=t.launch_command,
                env_vars=t.env_vars,
                category=t.category.value if hasattr(t.category, 'value') else str(t.category),
                icon_url=t.icon_url,
                documentation_url=t.documentation_url,
                is_active=t.is_active,
                is_verified=t.is_verified,
            )
            for t in templates
        ]

        return ListTemplatesResponse(
            templates=template_responses,
            count=len(template_responses)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )


@router.get("/{slug}", response_model=TemplateResponse)
async def get_template(slug: str):
    """
    Get template by slug

    Returns detailed information about a specific template.

    Path Parameters:
    - slug: Template slug (e.g., 'jupyter-lab', 'stable-diffusion', 'comfy-ui', 'vllm')
    """
    try:
        service = get_template_service()
        template = service.get_template_by_slug(slug)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{slug}' not found"
            )

        return TemplateResponse(
            id=template.id,
            name=template.name,
            slug=template.slug,
            description=template.description,
            docker_image=template.docker_image,
            gpu_min_vram=template.gpu_min_vram,
            gpu_recommended_vram=template.gpu_recommended_vram,
            cuda_version=template.cuda_version,
            ports=template.ports,
            volumes=template.volumes,
            launch_command=template.launch_command,
            env_vars=template.env_vars,
            category=template.category.value if hasattr(template.category, 'value') else str(template.category),
            icon_url=template.icon_url,
            documentation_url=template.documentation_url,
            is_active=template.is_active,
            is_verified=template.is_verified,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {str(e)}"
        )


@router.get("/{slug}/gpu-requirements", response_model=TemplateGPURequirementsResponse)
async def get_template_gpu_requirements(slug: str):
    """
    Get GPU requirements for a template

    Returns the minimum and recommended GPU specifications for a template.

    Path Parameters:
    - slug: Template slug
    """
    try:
        service = get_template_service()
        template = service.get_template_by_slug(slug)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{slug}' not found"
            )

        return TemplateGPURequirementsResponse(
            min_vram=template.gpu_min_vram,
            recommended_vram=template.gpu_recommended_vram,
            cuda_version=template.cuda_version,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GPU requirements for {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get GPU requirements: {str(e)}"
        )
