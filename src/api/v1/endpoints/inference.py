"""
Inference Configuration API - Endpoint para SDK clients.

Este endpoint retorna a configuração de inferência para o SDK client,
incluindo URL da GPU ativa e modelos de fallback.

O tráfego pesado (tokens) vai DIRETO do cliente para GPU/OpenRouter,
este endpoint só retorna a configuração (request leve).
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from ..dependencies import require_auth, get_current_user_email
from ....services.standby.manager import get_standby_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inference", tags=["Inference"])


# =============================================================================
# Schemas
# =============================================================================

class GPUConfigResponse(BaseModel):
    """Configuração da GPU primária."""
    url: str                      # http://gpu-ip:8000
    model: str = "default"        # Nome do modelo carregado
    timeout: float = 30.0         # Timeout para requests
    health_endpoint: str = "/health"


class FallbackModelResponse(BaseModel):
    """Modelo de fallback."""
    provider: str   # "openrouter", "openai", "anthropic"
    model: str      # "gpt-4o-mini", "claude-3.5-sonnet", etc
    priority: int = 0


class InferenceConfigResponse(BaseModel):
    """Configuração completa de inferência para o SDK."""
    # GPU primária (se ativa)
    gpu: Optional[GPUConfigResponse] = None

    # Modelos de fallback (em ordem de prioridade)
    fallback_models: List[FallbackModelResponse] = []

    # API keys (só se configurado para retornar)
    openrouter_api_key: Optional[str] = None

    # Comportamento
    auto_failover: bool = True
    retry_gpu_count: int = 2

    # Metadata
    user_id: str
    instance_id: Optional[int] = None


class UpdateFallbackRequest(BaseModel):
    """Request para atualizar modelos de fallback."""
    fallback_models: List[FallbackModelResponse]


class UpdateGPUUrlRequest(BaseModel):
    """Request para atualizar URL da GPU."""
    instance_id: int
    inference_port: int = 8000
    model_name: str = "default"


# =============================================================================
# In-memory storage (em produção, usar Redis ou DB)
# =============================================================================

# Configuração de fallback por usuário
_user_fallback_config: dict = {}

# URL de inferência por instância
_instance_inference_urls: dict = {}

# Default fallback models
DEFAULT_FALLBACK_MODELS = [
    FallbackModelResponse(provider="openrouter", model="openai/gpt-4o-mini", priority=0),
    FallbackModelResponse(provider="openrouter", model="anthropic/claude-3.5-sonnet", priority=1),
    FallbackModelResponse(provider="openrouter", model="google/gemini-pro-1.5", priority=2),
]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/config", response_model=InferenceConfigResponse)
async def get_inference_config(
    instance_id: Optional[int] = Query(None, description="ID da instância GPU"),
    include_api_key: bool = Query(False, description="Incluir API key do OpenRouter"),
    user_id: str = Depends(get_current_user_email),
):
    """
    Retorna configuração de inferência para o SDK client.

    Este é o ÚNICO request que o SDK faz para o servidor Dumont.
    Retorna URL da GPU ativa e modelos de fallback configurados.

    O SDK então conecta DIRETAMENTE na GPU ou OpenRouter,
    sem passar tráfego pelo servidor Dumont.
    """
    gpu_config = None

    # Se instance_id fornecido, busca URL da GPU
    if instance_id:
        # Verifica se tem URL de inferência configurada
        if instance_id in _instance_inference_urls:
            url_info = _instance_inference_urls[instance_id]
            gpu_config = GPUConfigResponse(
                url=url_info["url"],
                model=url_info.get("model", "default"),
                timeout=url_info.get("timeout", 30.0),
            )
        else:
            # Tenta pegar IP da instância via standby manager
            standby_manager = get_standby_manager()
            association = standby_manager.get_association(instance_id)
            if association:
                gpu_info = association.get("gpu_instance", {})
                if ip := gpu_info.get("ip"):
                    gpu_config = GPUConfigResponse(
                        url=f"http://{ip}:8000",
                        model="default",
                    )

    # Busca fallback models do usuário ou usa default
    fallback_models = _user_fallback_config.get(user_id, DEFAULT_FALLBACK_MODELS)

    # API key (opcional, por segurança)
    openrouter_key = None
    if include_api_key:
        from ....core.config import settings
        openrouter_key = settings.llm.openai_api_key  # Ou chave específica do usuário

    return InferenceConfigResponse(
        gpu=gpu_config,
        fallback_models=fallback_models,
        openrouter_api_key=openrouter_key,
        auto_failover=True,
        retry_gpu_count=2,
        user_id=user_id,
        instance_id=instance_id,
    )


@router.put("/fallback", response_model=InferenceConfigResponse)
async def update_fallback_models(
    request: UpdateFallbackRequest,
    user_id: str = Depends(get_current_user_email),
):
    """
    Atualiza modelos de fallback do usuário.

    Permite configurar quais modelos do OpenRouter usar como fallback,
    e em qual ordem de prioridade.
    """
    # Valida providers suportados
    valid_providers = {"openrouter", "openai", "anthropic"}
    for model in request.fallback_models:
        if model.provider not in valid_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider '{model.provider}' não suportado. Use: {valid_providers}"
            )

    # Ordena por prioridade
    sorted_models = sorted(request.fallback_models, key=lambda x: x.priority)

    # Salva configuração do usuário
    _user_fallback_config[user_id] = sorted_models

    logger.info(f"User {user_id} updated fallback models: {[m.model for m in sorted_models]}")

    return InferenceConfigResponse(
        gpu=None,
        fallback_models=sorted_models,
        auto_failover=True,
        retry_gpu_count=2,
        user_id=user_id,
    )


@router.post("/gpu-url", response_model=InferenceConfigResponse)
async def register_gpu_url(
    request: UpdateGPUUrlRequest,
    user_id: str = Depends(get_current_user_email),
):
    """
    Registra URL de inferência de uma GPU.

    Chamado pelo DumontAgent quando um servidor de inferência
    (vLLM, TGI, Ollama, etc) é iniciado na GPU.
    """
    # Busca IP da instância
    from ....domain.services import InstanceService
    from ....infrastructure.providers.vast_provider import VastAIProvider

    try:
        provider = VastAIProvider()
        instance_service = InstanceService(provider)
        instance = instance_service.get_instance(request.instance_id)

        if not instance.public_ipaddr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance {request.instance_id} não tem IP público"
            )

        inference_url = f"http://{instance.public_ipaddr}:{request.inference_port}"

        _instance_inference_urls[request.instance_id] = {
            "url": inference_url,
            "model": request.model_name,
            "timeout": 30.0,
        }

        logger.info(f"Registered inference URL for instance {request.instance_id}: {inference_url}")

        gpu_config = GPUConfigResponse(
            url=inference_url,
            model=request.model_name,
        )

        fallback_models = _user_fallback_config.get(user_id, DEFAULT_FALLBACK_MODELS)

        return InferenceConfigResponse(
            gpu=gpu_config,
            fallback_models=fallback_models,
            auto_failover=True,
            retry_gpu_count=2,
            user_id=user_id,
            instance_id=request.instance_id,
        )

    except Exception as e:
        logger.error(f"Failed to register GPU URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/gpu-url/{instance_id}")
async def unregister_gpu_url(
    instance_id: int,
    user_id: str = Depends(get_current_user_email),
):
    """
    Remove URL de inferência de uma GPU.

    Chamado quando o servidor de inferência é parado ou a GPU é destruída.
    """
    if instance_id in _instance_inference_urls:
        del _instance_inference_urls[instance_id]
        logger.info(f"Unregistered inference URL for instance {instance_id}")

    return {"success": True, "message": f"Inference URL for {instance_id} removed"}


@router.get("/models")
async def list_available_models():
    """
    Lista modelos disponíveis no OpenRouter.

    Retorna lista de modelos populares para configuração de fallback.
    """
    # Lista curada de modelos populares
    models = [
        # OpenAI via OpenRouter
        {"provider": "openrouter", "model": "openai/gpt-4o", "name": "GPT-4o", "context": 128000},
        {"provider": "openrouter", "model": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "context": 128000},
        {"provider": "openrouter", "model": "openai/gpt-4-turbo", "name": "GPT-4 Turbo", "context": 128000},

        # Anthropic via OpenRouter
        {"provider": "openrouter", "model": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "context": 200000},
        {"provider": "openrouter", "model": "anthropic/claude-3-opus", "name": "Claude 3 Opus", "context": 200000},
        {"provider": "openrouter", "model": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "context": 200000},

        # Google via OpenRouter
        {"provider": "openrouter", "model": "google/gemini-pro-1.5", "name": "Gemini Pro 1.5", "context": 1000000},
        {"provider": "openrouter", "model": "google/gemini-flash-1.5", "name": "Gemini Flash 1.5", "context": 1000000},

        # Open models via OpenRouter
        {"provider": "openrouter", "model": "meta-llama/llama-3.1-70b-instruct", "name": "Llama 3.1 70B", "context": 131072},
        {"provider": "openrouter", "model": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B", "context": 131072},
        {"provider": "openrouter", "model": "mistralai/mixtral-8x7b-instruct", "name": "Mixtral 8x7B", "context": 32768},

        # Direct providers
        {"provider": "openai", "model": "gpt-4o", "name": "GPT-4o (Direct)", "context": 128000},
        {"provider": "openai", "model": "gpt-4o-mini", "name": "GPT-4o Mini (Direct)", "context": 128000},
        {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (Direct)", "context": 200000},
    ]

    return {"models": models}
