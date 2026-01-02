"""
Cliente base do Dumont SDK.

Gerencia autenticação, sessão HTTP e configuração.
"""
import asyncio
import os
import json
import logging
import random
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Type
from dataclasses import dataclass, field

import httpx

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    DumontError,
    ConfigurationError,
    ConnectionError as DumontConnectionError,
    TimeoutError as DumontTimeoutError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

logger = logging.getLogger(__name__)

TOKEN_FILE = Path.home() / ".dumont_token"
CONFIG_FILE = Path.home() / ".dumont_config"

# Default retryable exceptions (network and server errors)
DEFAULT_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    DumontConnectionError,
    DumontTimeoutError,
    ServerError,
)


@dataclass
class RetryConfig:
    """Configuração de retry com exponential backoff."""

    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd
    retryable_exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: DEFAULT_RETRYABLE_EXCEPTIONS
    )
    retry_on_rate_limit: bool = True

    def calculate_delay(self, attempt: int) -> float:
        """
        Calcula o delay para uma tentativa específica.

        Args:
            attempt: Número da tentativa (0-indexed)

        Returns:
            Delay em segundos
        """
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            # Add 0-50% jitter
            delay = delay * (1 + random.random() * 0.5)
        return delay


@dataclass
class ConnectionPoolConfig:
    """Configuração do pool de conexões (Bulkhead pattern)."""
    max_connections: int = 100  # Máximo de conexões totais
    max_keepalive_connections: int = 20  # Conexões keepalive
    keepalive_expiry: float = 5.0  # Segundos antes de expirar conexão idle
    connect_timeout: float = 5.0  # Timeout para estabelecer conexão
    read_timeout: float = 30.0  # Timeout para leitura
    write_timeout: float = 30.0  # Timeout para escrita


@dataclass
class DumontClientConfig:
    """Configuração do cliente Dumont."""
    base_url: str = "https://api.dumontcloud.com"
    api_key: Optional[str] = None
    timeout: float = 30.0

    # LLM Failover settings
    openrouter_api_key: Optional[str] = None
    auto_failover: bool = True

    # Retry settings
    retry: Optional[RetryConfig] = None

    # Connection pool settings (Bulkhead)
    pool: Optional[ConnectionPoolConfig] = None

    @classmethod
    def from_env(cls) -> "DumontClientConfig":
        """Carrega configuração de variáveis de ambiente."""
        return cls(
            base_url=os.getenv("DUMONT_SERVER", "https://api.dumontcloud.com"),
            api_key=os.getenv("DUMONT_API_KEY"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        )


class BaseClient:
    """
    Cliente HTTP base com autenticação.

    Gerencia token JWT, refresh automático e headers.
    Suporta retry automático com exponential backoff.
    """

    def __init__(
        self,
        base_url: str = "https://api.dumontcloud.com",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        retry: Optional[RetryConfig] = None,
        pool: Optional[ConnectionPoolConfig] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retry_config = retry
        self.pool_config = pool
        self._token: Optional[str] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Retorna cliente HTTP reutilizável com pool de conexões."""
        if self._http_client is None or self._http_client.is_closed:
            # Configura limites de conexão (Bulkhead pattern)
            if self.pool_config:
                limits = httpx.Limits(
                    max_connections=self.pool_config.max_connections,
                    max_keepalive_connections=self.pool_config.max_keepalive_connections,
                    keepalive_expiry=self.pool_config.keepalive_expiry,
                )
                timeout = httpx.Timeout(
                    connect=self.pool_config.connect_timeout,
                    read=self.pool_config.read_timeout,
                    write=self.pool_config.write_timeout,
                    pool=5.0,  # Timeout para obter conexão do pool
                )
            else:
                limits = httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                )
                timeout = self.timeout

            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=timeout,
                limits=limits,
            )
        return self._http_client

    async def close(self):
        """Fecha o cliente HTTP."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # =========================================================================
    # Token Management
    # =========================================================================

    def load_token(self) -> Optional[str]:
        """Carrega token salvo do arquivo."""
        if TOKEN_FILE.exists():
            self._token = TOKEN_FILE.read_text().strip()
            return self._token
        return None

    def save_token(self, token: str):
        """Salva token no arquivo."""
        TOKEN_FILE.write_text(token)
        self._token = token

    def clear_token(self):
        """Remove token salvo."""
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        self._token = None

    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers com autenticação."""
        headers = {"Content-Type": "application/json"}

        # Prefere API key, depois token JWT
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        elif not self._token:
            self.load_token()
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

        return headers

    # =========================================================================
    # HTTP Methods
    # =========================================================================

    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determina se deve tentar novamente baseado no erro e tentativa.

        Args:
            error: Exceção que ocorreu
            attempt: Número da tentativa atual (0-indexed)

        Returns:
            True se deve tentar novamente
        """
        if not self.retry_config:
            return False

        if attempt >= self.retry_config.max_retries:
            return False

        # Check if it's a RateLimitError and retry is enabled
        if isinstance(error, RateLimitError):
            return self.retry_config.retry_on_rate_limit

        # Check if the exception type is in the retryable list
        return isinstance(error, self.retry_config.retryable_exceptions)

    async def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Faz request HTTP e retorna resposta JSON.

        Suporta retry automático com exponential backoff quando
        retry_config está configurado.

        Raises:
            AuthenticationError: Se não autenticado (401)
            AuthorizationError: Se não autorizado (403)
            NotFoundError: Se recurso não encontrado (404)
            ValidationError: Se dados inválidos (422)
            RateLimitError: Se rate limit atingido (429)
            ServerError: Se erro do servidor (5xx)
            DumontConnectionError: Se falha de conexão
            DumontTimeoutError: Se timeout
        """
        last_error: Optional[Exception] = None
        max_attempts = (self.retry_config.max_retries + 1) if self.retry_config else 1

        for attempt in range(max_attempts):
            try:
                return await self._do_request(method, path, data, params, timeout)
            except Exception as e:
                last_error = e

                # Check if we should retry
                if not self._should_retry(e, attempt):
                    raise

                # Calculate delay
                if isinstance(e, RateLimitError) and e.retry_after:
                    delay = float(e.retry_after)
                else:
                    delay = self.retry_config.calculate_delay(attempt)

                logger.warning(
                    f"Tentativa {attempt + 1}/{max_attempts} falhou: {e}. "
                    f"Tentando novamente em {delay:.1f}s..."
                )
                await asyncio.sleep(delay)

        # Should never reach here, but just in case
        if last_error:
            raise last_error
        raise DumontError("Erro inesperado durante retry")

    async def _do_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executa a requisição HTTP (sem retry).

        Esta é a implementação interna chamada por _request.
        """
        client = await self._get_client()
        headers = self._get_headers()
        effective_timeout = timeout or self.timeout

        try:
            response = await client.request(
                method=method,
                url=path,
                json=data,
                params=params,
                headers=headers,
                timeout=effective_timeout,
            )

            # Handle specific error codes
            if response.status_code == 401:
                raise AuthenticationError("Não autenticado. Faça login primeiro.")

            if response.status_code == 403:
                raise AuthorizationError(resource=path, action=method)

            if response.status_code == 404:
                raise NotFoundError(resource_type="Resource", path=path)

            if response.status_code == 422:
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", "Dados inválidos")
                    if isinstance(detail, list) and detail:
                        # Pydantic validation error format
                        first_error = detail[0]
                        field = ".".join(str(loc) for loc in first_error.get("loc", []))
                        msg = first_error.get("msg", "Erro de validação")
                        raise ValidationError(message=msg, field=field)
                    raise ValidationError(message=str(detail))
                except json.JSONDecodeError:
                    raise ValidationError(message="Dados inválidos")

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(
                    retry_after=int(retry_after) if retry_after else None
                )

            if response.status_code >= 500:
                try:
                    error_data = response.json()
                    raise ServerError(
                        message=error_data.get("detail", "Erro interno do servidor"),
                        status_code=response.status_code,
                    )
                except json.JSONDecodeError:
                    raise ServerError(
                        message=f"Erro {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    raise DumontError(error_data.get("detail", f"Erro {response.status_code}"))
                except json.JSONDecodeError:
                    raise DumontError(f"Erro {response.status_code}: {response.text}")

            if response.status_code == 204:
                return {"success": True}

            return response.json()

        except httpx.ConnectError as e:
            raise DumontConnectionError(
                host=self.base_url,
                original_error=e,
            )
        except httpx.TimeoutException as e:
            raise DumontTimeoutError(
                operation=f"{method} {path}",
                timeout_seconds=effective_timeout,
                original_error=e,
            )

    async def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """POST request."""
        return await self._request("POST", path, data=data, params=params)

    async def put(self, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """PUT request."""
        return await self._request("PUT", path, data=data)

    async def delete(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """DELETE request."""
        return await self._request("DELETE", path, params=params)

    # =========================================================================
    # Authentication
    # =========================================================================

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Faz login e salva token.

        Args:
            username: Email do usuário
            password: Senha

        Returns:
            Dados do usuário autenticado
        """
        response = await self.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password}
        )

        token = response.get("access_token") or response.get("token")
        if token:
            self.save_token(token)
            logger.info(f"Login successful, token saved to {TOKEN_FILE}")

        return response

    async def logout(self):
        """Faz logout e limpa token."""
        try:
            await self.post("/api/v1/auth/logout")
        finally:
            self.clear_token()
            logger.info("Logged out successfully")

    async def me(self) -> Dict[str, Any]:
        """Retorna dados do usuário autenticado."""
        return await self.get("/api/v1/auth/me")

    async def register(self, email: str, password: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Registra novo usuário.

        Args:
            email: Email do usuário
            password: Senha
            name: Nome (opcional)
        """
        data = {"email": email, "password": password}
        if name:
            data["name"] = name
        return await self.post("/api/v1/auth/register", data=data)
