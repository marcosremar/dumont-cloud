"""
Dumont Cloud SDK - Complete Python SDK for GPU Cloud Management

Módulos disponíveis:
- DumontClient: Cliente principal com todos os módulos
- instances: Gerenciamento de instâncias GPU
- snapshots: Backup e restore
- wizard: Deploy multi-start
- models: Instalação de modelos LLM (Ollama)
- standby: CPU Standby e failover
- failover: Failover Orchestrator (multi-strategy)
- metrics: Market Metrics e analytics
- llm: Inferência com failover automático GPU → OpenRouter

Exemplo básico:
    from dumont_sdk import DumontClient

    async with DumontClient(api_key="dumont_sk_...") as client:
        # Listar instâncias
        instances = await client.instances.list()

        # Deploy rápido
        result = await client.wizard.deploy(gpu_name="RTX 4090")

        # Instalar modelo
        await client.models.install(result.instance_id, "llama3.2")

        # Inferência com failover
        response = await client.llm.complete("Olá!")

Exemplo LLM Failover:
    from dumont_sdk import DumontLLM

    client = DumontLLM(api_key="dumont_sk_...")
    response = await client.complete("Olá, mundo!")
    # Se GPU falhar → failover automático para OpenRouter
"""

# Cliente principal
from .dumont_client import DumontClient, Dumont

# LLM com failover
from .client import DumontLLM
from .config import DumontConfig, GPUConfig, FallbackModel

# Módulos individuais
from .instances import InstancesClient, Instance, GPUOffer
from .snapshots import SnapshotsClient, Snapshot
from .wizard import WizardClient, DeployConfig, DeployResult, DeploySpeed
from .models import ModelsClient, InstalledModel, ModelInstallResult
from .standby import (
    StandbyClient,
    StandbyStatus,
    StandbyAssociation,
    PricingEstimate,
    FailoverResult,
)
from .failover import (
    FailoverClient,
    FailoverExecutionResult,
    ReadinessStatus,
    StrategyInfo,
    RegionalVolume,
    RegionalFailoverResult,
)
from .metrics import (
    MetricsClient,
    MarketSnapshot,
    ProviderRanking,
    EfficiencyRanking,
    PricePrediction,
    GpuComparison,
    ComparisonResult,
)
from .settings import (
    SettingsClient,
    UserSettings,
    AccountBalance,
)

# Base client (para extensões)
from .base import BaseClient, RetryConfig, ConnectionPoolConfig

# Circuit Breaker (resilience)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitState,
    get_circuit_breaker,
)

# Exceções
from .exceptions import (
    # Base
    DumontError,
    ErrorCode,
    # Network
    NetworkError,
    ConnectionError,
    TimeoutError,
    # API
    APIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError,
    # GPU
    GPUError,
    GPUConnectionError,
    GPUNotFoundError,
    GPUBusyError,
    # Failover
    FailoverError,
    FallbackError,
    FailoverTimeoutError,
    AllProvidersFailedError,
    # Configuration
    ConfigurationError,
    MissingAPIKeyError,
    # Instance
    InstanceError,
    InstanceNotFoundError,
    InstanceNotRunningError,
    # Snapshot
    SnapshotError,
    SnapshotNotFoundError,
    SnapshotCreationError,
)

__version__ = "0.3.0"
__all__ = [
    # Cliente principal
    "DumontClient",
    "Dumont",

    # LLM
    "DumontLLM",
    "DumontConfig",
    "GPUConfig",
    "FallbackModel",

    # Instâncias
    "InstancesClient",
    "Instance",
    "GPUOffer",

    # Snapshots
    "SnapshotsClient",
    "Snapshot",

    # Wizard
    "WizardClient",
    "DeployConfig",
    "DeployResult",
    "DeploySpeed",

    # Models
    "ModelsClient",
    "InstalledModel",
    "ModelInstallResult",

    # Standby
    "StandbyClient",
    "StandbyStatus",
    "StandbyAssociation",
    "PricingEstimate",
    "FailoverResult",

    # Failover
    "FailoverClient",
    "FailoverExecutionResult",
    "ReadinessStatus",
    "StrategyInfo",
    "RegionalVolume",
    "RegionalFailoverResult",

    # Metrics
    "MetricsClient",
    "MarketSnapshot",
    "ProviderRanking",
    "EfficiencyRanking",
    "PricePrediction",
    "GpuComparison",
    "ComparisonResult",

    # Settings
    "SettingsClient",
    "UserSettings",
    "AccountBalance",

    # Base
    "BaseClient",
    "RetryConfig",
    "ConnectionPoolConfig",

    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitBreakerRegistry",
    "CircuitState",
    "get_circuit_breaker",

    # Exceções - Base
    "DumontError",
    "ErrorCode",
    # Exceções - Network
    "NetworkError",
    "ConnectionError",
    "TimeoutError",
    # Exceções - API
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    # Exceções - GPU
    "GPUError",
    "GPUConnectionError",
    "GPUNotFoundError",
    "GPUBusyError",
    # Exceções - Failover
    "FailoverError",
    "FallbackError",
    "FailoverTimeoutError",
    "AllProvidersFailedError",
    # Exceções - Configuration
    "ConfigurationError",
    "MissingAPIKeyError",
    # Exceções - Instance
    "InstanceError",
    "InstanceNotFoundError",
    "InstanceNotRunningError",
    # Exceções - Snapshot
    "SnapshotError",
    "SnapshotNotFoundError",
    "SnapshotCreationError",
]
