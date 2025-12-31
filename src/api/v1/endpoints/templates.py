"""
Template Marketplace API endpoints
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query, Depends, Request
from pydantic import BaseModel, Field

from ..dependencies import get_current_user_email, require_auth, get_user_repository
from ....core.config import get_settings

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


# =============================================================================
# Deployment Schemas
# =============================================================================

class DeployTemplateRequest(BaseModel):
    """Request to deploy a template"""
    offer_id: int = Field(..., description="GPU offer ID from vast.ai")
    disk_size: int = Field(50, description="Disk size in GB", ge=10, le=2000)
    label: Optional[str] = Field(None, description="Optional label for the instance")
    env_overrides: Optional[Dict[str, str]] = Field(None, description="Environment variable overrides")
    skip_validation: bool = Field(False, description="Skip GPU validation (not recommended)")


class DeployTemplateResponse(BaseModel):
    """Response from template deployment"""
    success: bool = Field(..., description="Whether deployment was successful")
    instance_id: Optional[int] = Field(None, description="Created instance ID")
    template_slug: str = Field(..., description="Template that was deployed")
    template_name: str = Field(..., description="Template display name")
    gpu_validation: Optional[Dict[str, Any]] = Field(None, description="GPU validation result")
    message: str = Field(..., description="Status message")
    connection_info: Optional[Dict[str, Any]] = Field(None, description="Connection details when available")


class CompatibleOffersResponse(BaseModel):
    """Response with compatible GPU offers for a template"""
    template_slug: str = Field(..., description="Template slug")
    template_name: str = Field(..., description="Template name")
    min_vram: int = Field(..., description="Minimum VRAM required")
    offers: List[Dict[str, Any]] = Field(..., description="List of compatible GPU offers")
    count: int = Field(..., description="Number of compatible offers")


# =============================================================================
# Deployment Endpoints
# =============================================================================

def get_vast_service_for_user(user_email: str):
    """Get VastService configured with user's API key"""
    from services.vast_service import VastService

    settings = get_settings()
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    # Try user's key first, then fall back to system key from .env
    api_key = (user.vast_api_key if user else None) or settings.vast.api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured. Please update settings."
        )

    return VastService(api_key=api_key)


@router.get("/{slug}/offers", response_model=CompatibleOffersResponse)
async def get_compatible_offers(
    slug: str,
    max_price: float = Query(2.0, description="Maximum price per hour in USD"),
    region: Optional[str] = Query(None, description="Region filter: US, EU, ASIA"),
    num_gpus: int = Query(1, ge=1, le=8, description="Number of GPUs"),
    verified_only: bool = Query(False, description="Only verified hosts"),
    limit: int = Query(20, le=100, description="Maximum results"),
    user_email: str = Depends(get_current_user_email),
):
    """
    Get GPU offers compatible with a template

    Returns available GPU offers that meet the template's requirements.
    Filters automatically by minimum VRAM and CUDA version.

    Path Parameters:
    - slug: Template slug (e.g., 'jupyter-lab', 'stable-diffusion')

    Query Parameters:
    - max_price: Maximum hourly price
    - region: Region filter (US, EU, ASIA)
    - num_gpus: Number of GPUs needed
    - verified_only: Only verified hosts
    - limit: Max results
    """
    try:
        template_service = get_template_service()
        template = template_service.get_template_by_slug(slug)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{slug}' not found"
            )

        vast_service = get_vast_service_for_user(user_email)

        offers = vast_service.search_offers_for_template(
            template=template,
            num_gpus=num_gpus,
            max_price=max_price,
            region=region,
            verified_only=verified_only,
            limit=limit,
        )

        return CompatibleOffersResponse(
            template_slug=template.slug,
            template_name=template.name,
            min_vram=template.gpu_min_vram,
            offers=offers,
            count=len(offers),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting compatible offers for {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get compatible offers: {str(e)}"
        )


@router.post("/{slug}/deploy", response_model=DeployTemplateResponse, status_code=status.HTTP_201_CREATED)
async def deploy_template(
    slug: str,
    request: DeployTemplateRequest,
    http_request: Request,
    user_email: str = Depends(get_current_user_email),
):
    """
    Deploy a template to a GPU instance

    Creates a new GPU instance with the template's Docker image, ports,
    volumes, and launch command configured.

    Path Parameters:
    - slug: Template slug (e.g., 'jupyter-lab', 'stable-diffusion', 'comfy-ui', 'vllm')

    Request Body:
    - offer_id: GPU offer ID from vast.ai (required)
    - disk_size: Disk size in GB (default: 50)
    - label: Optional instance label
    - env_overrides: Environment variables to override
    - skip_validation: Skip GPU validation (not recommended)

    Returns:
    - Instance ID and connection details on success
    - GPU validation warnings if applicable
    """
    import random
    from datetime import datetime

    settings = get_settings()
    demo_param = http_request.query_params.get("demo", "").lower() == "true"
    is_demo = settings.app.demo_mode or demo_param

    try:
        # Get template
        template_service = get_template_service()
        template = template_service.get_template_by_slug(slug)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{slug}' not found"
            )

        # Demo mode: Return simulated deployment
        if is_demo:
            demo_instance_id = random.randint(10000000, 99999999)
            logger.info(f"Demo mode: Simulating deployment of {slug} to offer {request.offer_id}")
            return DeployTemplateResponse(
                success=True,
                instance_id=demo_instance_id,
                template_slug=slug,
                template_name=template.name,
                gpu_validation={
                    "is_compatible": True,
                    "is_recommended": True,
                    "gpu_vram": 24,
                    "required_vram": template.gpu_min_vram,
                    "recommended_vram": template.gpu_recommended_vram,
                    "messages": ["Demo mode: GPU validation simulated"]
                },
                message=f"Demo: Template '{template.name}' deployed successfully",
                connection_info={
                    "ssh_host": "demo.dumontcloud.com",
                    "ssh_port": 22,
                    "public_ip": "demo.dumontcloud.com",
                    "ports": {str(p): p for p in template.ports},
                }
            )

        vast_service = get_vast_service_for_user(user_email)

        # Validate GPU meets template requirements
        # First, get the offer details to validate
        offers = vast_service.search_offers(
            max_price=10.0,  # Wide search
            limit=200,
        )

        # Find the selected offer
        selected_offer = None
        for offer in offers:
            if offer.get("id") == request.offer_id:
                selected_offer = offer
                break

        if not selected_offer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"GPU offer {request.offer_id} not found or no longer available"
            )

        # Validate GPU for template
        gpu_validation = vast_service.validate_gpu_for_template(selected_offer, template)

        if not gpu_validation["is_compatible"] and not request.skip_validation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"GPU does not meet template requirements: {'; '.join(gpu_validation['messages'])}"
            )

        # Create instance from template
        instance_id = vast_service.create_instance_from_template(
            offer_id=request.offer_id,
            template=template,
            disk=request.disk_size,
            env_overrides=request.env_overrides,
        )

        if not instance_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create instance. Please try again."
            )

        logger.info(f"Successfully deployed template {slug} to instance {instance_id}")

        return DeployTemplateResponse(
            success=True,
            instance_id=instance_id,
            template_slug=slug,
            template_name=template.name,
            gpu_validation=gpu_validation,
            message=f"Template '{template.name}' deployment started. Instance {instance_id} is being provisioned.",
            connection_info={
                "status": "provisioning",
                "expected_ports": template.ports,
                "note": "Connection details will be available once instance is running. Poll GET /api/instances/{instance_id} for status."
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying template {slug}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy template: {str(e)}"
        )
