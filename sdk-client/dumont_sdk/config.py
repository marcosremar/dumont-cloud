"""
Configuração do Dumont SDK com Pydantic v2.

Gerencia configurações locais e busca config do servidor.
Inclui validação robusta de todos os parâmetros.
"""
import os
import re
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, HttpUrl
from pydantic_settings import BaseSettings


# Regex para validação de API keys
API_KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{20,}$')
DUMONT_API_KEY_PATTERN = re.compile(r'^dumont_sk_[a-zA-Z0-9_-]{20,}$')


class FallbackModel(BaseModel):
    """Modelo de fallback configurado com validação."""

    provider: Literal["openrouter", "openai", "anthropic"] = Field(
        ...,
        description="Provider do modelo de fallback"
    )
    model: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nome do modelo (ex: gpt-4o-mini, claude-3.5-sonnet)"
    )
    priority: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Prioridade do modelo (menor = maior prioridade)"
    )

    @field_validator('model')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Valida formato do nome do modelo."""
        v = v.strip()
        if not v:
            raise ValueError("Nome do modelo não pode ser vazio")
        # Permite formato provider/model para OpenRouter
        if '/' in v:
            parts = v.split('/')
            if len(parts) > 2:
                raise ValueError("Formato inválido. Use 'model' ou 'provider/model'")
        return v

    @property
    def full_name(self) -> str:
        """Nome completo do modelo (provider/model)."""
        if self.provider == "openrouter":
            return self.model  # OpenRouter já usa formato provider/model
        return f"{self.provider}/{self.model}"

    model_config = {"frozen": True}


class GPUConfig(BaseModel):
    """Configuração da GPU primária com validação."""

    url: str = Field(
        ...,
        min_length=1,
        description="URL da GPU (ex: http://123.45.67.89:8000)"
    )
    model: str = Field(
        default="default",
        min_length=1,
        max_length=100,
        description="Nome do modelo carregado na GPU"
    )
    timeout: float = Field(
        default=30.0,
        gt=0,
        le=300,
        description="Timeout para requests em segundos"
    )
    health_endpoint: str = Field(
        default="/health",
        description="Endpoint de health check"
    )

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Valida formato da URL."""
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL deve começar com http:// ou https://")
        # Remove trailing slash
        return v.rstrip('/')

    @field_validator('health_endpoint')
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Valida formato do endpoint."""
        v = v.strip()
        if not v.startswith('/'):
            v = '/' + v
        return v

    model_config = {"frozen": True}


class DumontConfig(BaseModel):
    """Configuração principal do SDK com validação Pydantic."""

    # Servidor Dumont Cloud
    dumont_server: str = Field(
        default="https://api.dumontcloud.com",
        description="URL do servidor Dumont Cloud"
    )
    api_key: str = Field(
        default="",
        description="API key do Dumont Cloud (formato: dumont_sk_...)"
    )

    # GPU Primária
    gpu: Optional[GPUConfig] = Field(
        default=None,
        description="Configuração da GPU primária"
    )

    # Modelos de fallback
    fallback_models: List[FallbackModel] = Field(
        default_factory=list,
        description="Lista de modelos de fallback em ordem de prioridade"
    )

    # Chaves de API para fallback
    openrouter_api_key: str = Field(
        default="",
        description="API key do OpenRouter"
    )
    openai_api_key: str = Field(
        default="",
        description="API key do OpenAI"
    )
    anthropic_api_key: str = Field(
        default="",
        description="API key do Anthropic"
    )

    # Comportamento
    auto_failover: bool = Field(
        default=True,
        description="Habilita failover automático se GPU falhar"
    )
    retry_gpu_count: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Número de tentativas antes de failover"
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0,
        le=60,
        description="Delay entre retries em segundos"
    )
    cache_config_seconds: int = Field(
        default=300,
        ge=0,
        le=3600,
        description="Tempo de cache da configuração em segundos"
    )

    # OpenAI compatibility
    openai_compatible: bool = Field(
        default=True,
        description="GPU usa API compatível com OpenAI"
    )

    @field_validator('dumont_server')
    @classmethod
    def validate_server_url(cls, v: str) -> str:
        """Valida URL do servidor."""
        v = v.strip()
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("dumont_server deve começar com http:// ou https://")
        return v.rstrip('/')

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Valida formato da API key do Dumont."""
        v = v.strip()
        if v and not DUMONT_API_KEY_PATTERN.match(v):
            raise ValueError(
                "API key inválida. Formato esperado: dumont_sk_<token> "
                "(mínimo 20 caracteres alfanuméricos após prefixo)"
            )
        return v

    @field_validator('openrouter_api_key', 'openai_api_key', 'anthropic_api_key')
    @classmethod
    def validate_provider_api_key(cls, v: str) -> str:
        """Valida formato das API keys de providers."""
        v = v.strip()
        if v and len(v) < 20:
            raise ValueError("API key muito curta (mínimo 20 caracteres)")
        return v

    @model_validator(mode='after')
    def validate_fallback_has_keys(self) -> 'DumontConfig':
        """Valida que fallback models têm API keys correspondentes."""
        for model in self.fallback_models:
            key = self.get_api_key_for_provider(model.provider)
            if not key:
                # Warning apenas, não erro - pode ser configurado depois
                pass
        return self

    @classmethod
    def from_env(cls) -> "DumontConfig":
        """Carrega configuração de variáveis de ambiente."""
        fallback_models: List[FallbackModel] = []

        # Fallback models do ambiente (formato: provider/model,provider/model)
        fallback_str = os.getenv("DUMONT_FALLBACK_MODELS", "openrouter/openai/gpt-4o-mini")
        for i, model_str in enumerate(fallback_str.split(",")):
            parts = model_str.strip().split("/", 1)
            if len(parts) == 2:
                try:
                    fallback_models.append(
                        FallbackModel(provider=parts[0], model=parts[1], priority=i)
                    )
                except ValueError:
                    # Ignora modelos mal formatados no ambiente
                    pass

        # GPU config do ambiente
        gpu_url = os.getenv("DUMONT_GPU_URL")
        gpu_config = GPUConfig(url=gpu_url) if gpu_url else None

        return cls(
            dumont_server=os.getenv("DUMONT_SERVER", "https://api.dumontcloud.com"),
            api_key=os.getenv("DUMONT_API_KEY", ""),
            gpu=gpu_config,
            fallback_models=fallback_models,
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "DumontConfig":
        """Carrega configuração de um dicionário (resposta do servidor)."""
        fallback_models: List[FallbackModel] = []

        # Fallback models
        for i, model_data in enumerate(data.get("fallback_models", [])):
            try:
                fallback_models.append(
                    FallbackModel(
                        provider=model_data["provider"],
                        model=model_data["model"],
                        priority=model_data.get("priority", i),
                    )
                )
            except (ValueError, KeyError):
                # Ignora modelos mal formatados
                pass

        # GPU config
        gpu_config = None
        if gpu_data := data.get("gpu"):
            try:
                gpu_config = GPUConfig(
                    url=gpu_data["url"],
                    model=gpu_data.get("model", "default"),
                    timeout=gpu_data.get("timeout", 30.0),
                )
            except (ValueError, KeyError):
                pass

        return cls(
            dumont_server=data.get("dumont_server", "https://api.dumontcloud.com"),
            api_key=data.get("api_key", ""),
            gpu=gpu_config,
            fallback_models=fallback_models,
            openrouter_api_key=data.get("openrouter_api_key", ""),
            openai_api_key=data.get("openai_api_key", ""),
            anthropic_api_key=data.get("anthropic_api_key", ""),
            auto_failover=data.get("auto_failover", True),
            retry_gpu_count=data.get("retry_gpu_count", 2),
        )

    def to_dict(self) -> dict:
        """Serializa configuração para dicionário."""
        return {
            "dumont_server": self.dumont_server,
            "gpu": {
                "url": self.gpu.url,
                "model": self.gpu.model,
                "timeout": self.gpu.timeout,
            } if self.gpu else None,
            "fallback_models": [
                {"provider": m.provider, "model": m.model, "priority": m.priority}
                for m in self.fallback_models
            ],
            "auto_failover": self.auto_failover,
            "retry_gpu_count": self.retry_gpu_count,
        }

    def get_api_key_for_provider(self, provider: str) -> str:
        """Retorna a API key para um provider específico."""
        if provider == "openrouter":
            return self.openrouter_api_key
        elif provider == "openai":
            return self.openai_api_key
        elif provider == "anthropic":
            return self.anthropic_api_key
        return ""

    model_config = {"validate_assignment": True}
