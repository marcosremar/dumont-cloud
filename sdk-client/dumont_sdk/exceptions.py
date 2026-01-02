"""
Exceções customizadas do Dumont SDK.

Hierarquia:
    DumontError (base)
    ├── NetworkError
    │   ├── ConnectionError
    │   └── TimeoutError
    ├── APIError
    │   ├── AuthenticationError
    │   ├── AuthorizationError
    │   ├── NotFoundError
    │   ├── ValidationError
    │   ├── RateLimitError
    │   └── ServerError
    ├── GPUError
    │   ├── GPUConnectionError
    │   ├── GPUBusyError
    │   └── GPUNotFoundError
    ├── FailoverError
    │   ├── FallbackError
    │   └── FailoverTimeoutError
    └── ConfigurationError
"""
from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Códigos de erro para tratamento programático."""

    # Network errors (1xxx)
    NETWORK_CONNECTION_FAILED = "E1001"
    NETWORK_TIMEOUT = "E1002"
    NETWORK_DNS_FAILED = "E1003"

    # Authentication/Authorization (2xxx)
    AUTH_INVALID_CREDENTIALS = "E2001"
    AUTH_TOKEN_EXPIRED = "E2002"
    AUTH_TOKEN_INVALID = "E2003"
    AUTH_INSUFFICIENT_PERMISSIONS = "E2004"
    AUTH_API_KEY_INVALID = "E2005"

    # API errors (3xxx)
    API_NOT_FOUND = "E3001"
    API_VALIDATION_FAILED = "E3002"
    API_RATE_LIMITED = "E3003"
    API_SERVER_ERROR = "E3004"
    API_BAD_REQUEST = "E3005"
    API_CONFLICT = "E3006"

    # GPU errors (4xxx)
    GPU_CONNECTION_FAILED = "E4001"
    GPU_NOT_FOUND = "E4002"
    GPU_BUSY = "E4003"
    GPU_UNAVAILABLE = "E4004"
    GPU_SSH_FAILED = "E4005"

    # Failover errors (5xxx)
    FAILOVER_ALL_FAILED = "E5001"
    FAILOVER_TIMEOUT = "E5002"
    FAILOVER_NO_PROVIDERS = "E5003"
    FAILOVER_PROVIDER_FAILED = "E5004"

    # Configuration errors (6xxx)
    CONFIG_MISSING_API_KEY = "E6001"
    CONFIG_INVALID_URL = "E6002"
    CONFIG_MISSING_REQUIRED = "E6003"

    # Instance errors (7xxx)
    INSTANCE_NOT_FOUND = "E7001"
    INSTANCE_NOT_RUNNING = "E7002"
    INSTANCE_ALREADY_EXISTS = "E7003"
    INSTANCE_OPERATION_FAILED = "E7004"

    # Snapshot errors (8xxx)
    SNAPSHOT_NOT_FOUND = "E8001"
    SNAPSHOT_CREATION_FAILED = "E8002"
    SNAPSHOT_RESTORE_FAILED = "E8003"


class DumontError(Exception):
    """
    Erro base do Dumont SDK.

    Todos os erros do SDK herdam desta classe, permitindo
    captura genérica de erros do SDK.

    Attributes:
        message: Mensagem de erro legível
        code: Código de erro para tratamento programático
        details: Detalhes adicionais (opcional)
        original_error: Exceção original que causou este erro
    """

    def __init__(
        self,
        message: str,
        code: Optional[ErrorCode] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.original_error = original_error
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Converte erro para dicionário (útil para logging/serialização)."""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
        }
        if self.code:
            result["code"] = self.code.value
        if self.details:
            result["details"] = self.details
        if self.original_error:
            result["original_error"] = str(self.original_error)
        return result


# =============================================================================
# Network Errors
# =============================================================================

class NetworkError(DumontError):
    """Erro de rede base."""
    pass


class ConnectionError(NetworkError):
    """Falha ao conectar com o servidor."""

    def __init__(
        self,
        host: str,
        port: Optional[int] = None,
        original_error: Optional[Exception] = None,
    ):
        self.host = host
        self.port = port
        addr = f"{host}:{port}" if port else host
        super().__init__(
            message=f"Não foi possível conectar a {addr}",
            code=ErrorCode.NETWORK_CONNECTION_FAILED,
            details={"host": host, "port": port},
            original_error=original_error,
        )


class TimeoutError(NetworkError):
    """Timeout na requisição."""

    def __init__(
        self,
        operation: str,
        timeout_seconds: float,
        original_error: Optional[Exception] = None,
    ):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        super().__init__(
            message=f"Timeout de {timeout_seconds}s na operação: {operation}",
            code=ErrorCode.NETWORK_TIMEOUT,
            details={"operation": operation, "timeout_seconds": timeout_seconds},
            original_error=original_error,
        )


# =============================================================================
# API Errors
# =============================================================================

class APIError(DumontError):
    """Erro de API base."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: Optional[ErrorCode] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        self.status_code = status_code
        details = details or {}
        if status_code:
            details["status_code"] = status_code
        super().__init__(
            message=message,
            code=code,
            details=details,
            original_error=original_error,
        )


class AuthenticationError(APIError):
    """Erro de autenticação com a API Dumont."""

    def __init__(
        self,
        message: str = "Não autenticado. Faça login primeiro.",
        code: ErrorCode = ErrorCode.AUTH_INVALID_CREDENTIALS,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            code=code,
            details=details,
        )


class AuthorizationError(APIError):
    """Permissão insuficiente para a operação."""

    def __init__(
        self,
        resource: str,
        action: str,
    ):
        super().__init__(
            message=f"Permissão insuficiente para {action} em {resource}",
            status_code=403,
            code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
            details={"resource": resource, "action": action},
        )


class NotFoundError(APIError):
    """Recurso não encontrado."""

    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        path: Optional[str] = None,
    ):
        if resource_id:
            message = f"{resource_type} não encontrado: {resource_id}"
        elif path:
            message = f"Recurso não encontrado: {path}"
        else:
            message = f"{resource_type} não encontrado"

        super().__init__(
            message=message,
            status_code=404,
            code=ErrorCode.API_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id, "path": path},
        )


class ValidationError(APIError):
    """Erro de validação nos dados enviados."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message=message,
            status_code=422,
            code=ErrorCode.API_VALIDATION_FAILED,
            details=details,
        )


class RateLimitError(APIError):
    """Rate limit atingido."""

    def __init__(
        self,
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        self.retry_after = retry_after
        self.limit = limit

        msg = "Rate limit atingido"
        if retry_after:
            msg += f", tente novamente em {retry_after}s"

        super().__init__(
            message=msg,
            status_code=429,
            code=ErrorCode.API_RATE_LIMITED,
            details={"retry_after": retry_after, "limit": limit},
        )


class ServerError(APIError):
    """Erro interno do servidor."""

    def __init__(
        self,
        message: str = "Erro interno do servidor",
        status_code: int = 500,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            code=ErrorCode.API_SERVER_ERROR,
        )


# =============================================================================
# GPU Errors
# =============================================================================

class GPUError(DumontError):
    """Erro relacionado a GPU base."""
    pass


class GPUConnectionError(GPUError):
    """Falha ao conectar com a GPU primária."""

    def __init__(
        self,
        gpu_url: str,
        instance_id: Optional[int] = None,
        original_error: Optional[Exception] = None,
    ):
        self.gpu_url = gpu_url
        self.instance_id = instance_id
        super().__init__(
            message=f"Falha ao conectar com GPU: {gpu_url}",
            code=ErrorCode.GPU_CONNECTION_FAILED,
            details={"gpu_url": gpu_url, "instance_id": instance_id},
            original_error=original_error,
        )


class GPUNotFoundError(GPUError):
    """GPU não encontrada ou indisponível."""

    def __init__(
        self,
        gpu_name: Optional[str] = None,
        instance_id: Optional[int] = None,
    ):
        if gpu_name:
            message = f"GPU {gpu_name} não encontrada"
        elif instance_id:
            message = f"Instância GPU {instance_id} não encontrada"
        else:
            message = "GPU não encontrada"

        super().__init__(
            message=message,
            code=ErrorCode.GPU_NOT_FOUND,
            details={"gpu_name": gpu_name, "instance_id": instance_id},
        )


class GPUBusyError(GPUError):
    """GPU ocupada ou em uso."""

    def __init__(
        self,
        instance_id: int,
        current_operation: Optional[str] = None,
    ):
        message = f"GPU {instance_id} está ocupada"
        if current_operation:
            message += f" ({current_operation})"

        super().__init__(
            message=message,
            code=ErrorCode.GPU_BUSY,
            details={"instance_id": instance_id, "current_operation": current_operation},
        )


# =============================================================================
# Failover Errors
# =============================================================================

class FailoverError(DumontError):
    """Erro de failover base."""
    pass


class FallbackError(FailoverError):
    """Falha no fallback (OpenRouter ou outro provider)."""

    def __init__(
        self,
        provider: str,
        model: str,
        reason: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        self.provider = provider
        self.model = model
        self.reason = reason

        message = f"Falha no fallback {provider}/{model}"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            code=ErrorCode.FAILOVER_PROVIDER_FAILED,
            details={"provider": provider, "model": model, "reason": reason},
            original_error=original_error,
        )


class FailoverTimeoutError(FailoverError):
    """Timeout durante failover."""

    def __init__(
        self,
        timeout_seconds: float,
        providers_tried: Optional[list] = None,
    ):
        message = f"Timeout de {timeout_seconds}s durante failover"

        super().__init__(
            message=message,
            code=ErrorCode.FAILOVER_TIMEOUT,
            details={
                "timeout_seconds": timeout_seconds,
                "providers_tried": providers_tried or [],
            },
        )


class AllProvidersFailedError(FailoverError):
    """Todos os providers de failover falharam."""

    def __init__(
        self,
        providers_tried: list,
        errors: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            message=f"Todos os providers falharam: {', '.join(providers_tried)}",
            code=ErrorCode.FAILOVER_ALL_FAILED,
            details={"providers_tried": providers_tried, "errors": errors or {}},
        )


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(DumontError):
    """Erro de configuração do SDK."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        code: ErrorCode = ErrorCode.CONFIG_MISSING_REQUIRED,
    ):
        details = {}
        if field:
            details["field"] = field

        super().__init__(
            message=message,
            code=code,
            details=details,
        )


class MissingAPIKeyError(ConfigurationError):
    """API key não configurada."""

    def __init__(self):
        super().__init__(
            message="API key não configurada. Use DUMONT_API_KEY ou passe api_key no construtor.",
            field="api_key",
            code=ErrorCode.CONFIG_MISSING_API_KEY,
        )


# =============================================================================
# Instance Errors
# =============================================================================

class InstanceError(DumontError):
    """Erro relacionado a instâncias."""
    pass


class InstanceNotFoundError(InstanceError):
    """Instância não encontrada."""

    def __init__(self, instance_id: int):
        super().__init__(
            message=f"Instância {instance_id} não encontrada",
            code=ErrorCode.INSTANCE_NOT_FOUND,
            details={"instance_id": instance_id},
        )


class InstanceNotRunningError(InstanceError):
    """Instância não está rodando."""

    def __init__(self, instance_id: int, current_status: Optional[str] = None):
        message = f"Instância {instance_id} não está rodando"
        if current_status:
            message += f" (status atual: {current_status})"

        super().__init__(
            message=message,
            code=ErrorCode.INSTANCE_NOT_RUNNING,
            details={"instance_id": instance_id, "current_status": current_status},
        )


# =============================================================================
# Snapshot Errors
# =============================================================================

class SnapshotError(DumontError):
    """Erro relacionado a snapshots."""
    pass


class SnapshotNotFoundError(SnapshotError):
    """Snapshot não encontrado."""

    def __init__(self, snapshot_id: str):
        super().__init__(
            message=f"Snapshot {snapshot_id} não encontrado",
            code=ErrorCode.SNAPSHOT_NOT_FOUND,
            details={"snapshot_id": snapshot_id},
        )


class SnapshotCreationError(SnapshotError):
    """Falha ao criar snapshot."""

    def __init__(self, instance_id: int, reason: Optional[str] = None):
        message = f"Falha ao criar snapshot da instância {instance_id}"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            code=ErrorCode.SNAPSHOT_CREATION_FAILED,
            details={"instance_id": instance_id, "reason": reason},
        )
