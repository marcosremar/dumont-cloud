"""
Cliente LLM do Dumont Cloud com failover automático.

O cliente tenta conectar primeiro na GPU do usuário.
Se falhar, faz failover para OpenRouter ou outro provider configurado.

IMPORTANTE: O tráfego pesado (tokens) vai DIRETO para GPU ou OpenRouter,
nunca passa pelo servidor Dumont Cloud (evita sobrecarga).
"""
import asyncio
import logging
import time
from typing import Optional, List, Dict, Any, Union, AsyncIterator

import httpx

from .config import DumontConfig, GPUConfig, FallbackModel
from .exceptions import (
    GPUConnectionError,
    FallbackError,
    ConfigurationError,
    AuthenticationError,
)

logger = logging.getLogger(__name__)


class DumontLLM:
    """
    Cliente LLM com failover automático GPU → OpenRouter.

    Exemplo de uso:
        client = DumontLLM(api_key="dumont_sk_...")
        response = await client.complete("Olá, mundo!")

    Ou com config manual:
        config = DumontConfig(
            gpu=GPUConfig(url="http://gpu-ip:8000"),
            fallback_models=[FallbackModel("openrouter", "openai/gpt-4o-mini")],
            openrouter_api_key="sk-or-..."
        )
        client = DumontLLM(config=config)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[DumontConfig] = None,
    ):
        """
        Inicializa o cliente LLM.

        Args:
            api_key: API key do Dumont Cloud (busca config do servidor)
            config: Configuração manual (ignora busca do servidor)
        """
        if config:
            self.config = config
        elif api_key:
            self.config = DumontConfig.from_env()
            self.config.api_key = api_key
        else:
            self.config = DumontConfig.from_env()

        self._config_cached_at: Optional[float] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Retorna cliente HTTP reutilizável."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=60.0)
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
    # Config Management
    # =========================================================================

    async def fetch_config(self, force: bool = False) -> DumontConfig:
        """
        Busca configuração do servidor Dumont Cloud.

        Este é o ÚNICO request que vai para o servidor Dumont.
        Retorna URL da GPU ativa e modelos de fallback configurados.

        Args:
            force: Ignora cache e busca config nova
        """
        # Verifica cache
        if not force and self._config_cached_at:
            age = time.time() - self._config_cached_at
            if age < self.config.cache_config_seconds:
                return self.config

        if not self.config.api_key:
            raise ConfigurationError("API key não configurada")

        client = await self._get_http_client()
        url = f"{self.config.dumont_server}/api/v1/inference/config"

        try:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {self.config.api_key}"}
            )

            if response.status_code == 401:
                raise AuthenticationError("API key inválida")

            response.raise_for_status()
            data = response.json()

            # Atualiza config com dados do servidor
            if gpu_data := data.get("gpu"):
                self.config.gpu = GPUConfig(
                    url=gpu_data["url"],
                    model=gpu_data.get("model", "default"),
                    timeout=gpu_data.get("timeout", 30.0),
                )

            if fallback_data := data.get("fallback_models"):
                self.config.fallback_models = [
                    FallbackModel(
                        provider=m["provider"],
                        model=m["model"],
                        priority=m.get("priority", i)
                    )
                    for i, m in enumerate(fallback_data)
                ]

            # Atualiza API keys se fornecidas pelo servidor
            if key := data.get("openrouter_api_key"):
                self.config.openrouter_api_key = key

            self._config_cached_at = time.time()
            logger.info(f"Config carregada: GPU={self.config.gpu.url if self.config.gpu else 'None'}")
            return self.config

        except httpx.HTTPError as e:
            logger.warning(f"Falha ao buscar config do servidor: {e}")
            # Usa config local se servidor falhar
            return self.config

    # =========================================================================
    # GPU Direct Connection
    # =========================================================================

    async def _call_gpu(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chama a GPU diretamente (API compatível com OpenAI).

        Args:
            messages: Lista de mensagens no formato OpenAI
            **kwargs: Parâmetros adicionais (temperature, max_tokens, etc)

        Returns:
            Resposta no formato OpenAI

        Raises:
            GPUConnectionError: Se não conseguir conectar com a GPU
        """
        if not self.config.gpu:
            raise GPUConnectionError("", Exception("GPU não configurada"))

        gpu = self.config.gpu
        client = await self._get_http_client()
        url = f"{gpu.url}/v1/chat/completions"

        payload = {
            "model": gpu.model,
            "messages": messages,
            **kwargs
        }

        last_error = None
        for attempt in range(self.config.retry_gpu_count):
            try:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=gpu.timeout,
                )
                response.raise_for_status()
                return response.json()

            except Exception as e:
                last_error = e
                logger.warning(f"GPU tentativa {attempt + 1} falhou: {e}")
                if attempt < self.config.retry_gpu_count - 1:
                    await asyncio.sleep(self.config.retry_delay)

        raise GPUConnectionError(gpu.url, last_error)

    async def _check_gpu_health(self) -> bool:
        """Verifica se a GPU está online."""
        if not self.config.gpu:
            return False

        client = await self._get_http_client()
        url = f"{self.config.gpu.url}{self.config.gpu.health_endpoint}"

        try:
            response = await client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    # =========================================================================
    # Fallback Providers (OpenRouter, OpenAI, Anthropic)
    # =========================================================================

    async def _call_openrouter(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chama OpenRouter diretamente.

        Args:
            model: Nome do modelo (ex: "openai/gpt-4o-mini")
            messages: Lista de mensagens
        """
        if not self.config.openrouter_api_key:
            raise ConfigurationError("OpenRouter API key não configurada")

        client = await self._get_http_client()
        url = "https://openrouter.ai/api/v1/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }

        response = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.config.openrouter_api_key}",
                "HTTP-Referer": "https://dumontcloud.com",
                "X-Title": "Dumont Cloud SDK",
            },
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()

    async def _call_openai(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Chama OpenAI diretamente."""
        if not self.config.openai_api_key:
            raise ConfigurationError("OpenAI API key não configurada")

        client = await self._get_http_client()
        url = "https://api.openai.com/v1/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }

        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {self.config.openai_api_key}"},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()

    async def _call_anthropic(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Chama Anthropic diretamente."""
        if not self.config.anthropic_api_key:
            raise ConfigurationError("Anthropic API key não configurada")

        client = await self._get_http_client()
        url = "https://api.anthropic.com/v1/messages"

        # Converte formato OpenAI → Anthropic
        system_msg = None
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append(msg)

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if system_msg:
            payload["system"] = system_msg

        response = await client.post(
            url,
            json=payload,
            headers={
                "x-api-key": self.config.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=60.0,
        )
        response.raise_for_status()

        # Converte resposta Anthropic → formato OpenAI
        data = response.json()
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": data["content"][0]["text"],
                },
                "finish_reason": data.get("stop_reason", "stop"),
            }],
            "model": model,
            "usage": data.get("usage", {}),
        }

    async def _call_fallback(
        self,
        fallback: FallbackModel,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chama um provider de fallback.

        Args:
            fallback: Configuração do modelo de fallback
            messages: Lista de mensagens
        """
        try:
            if fallback.provider == "openrouter":
                return await self._call_openrouter(fallback.model, messages, **kwargs)
            elif fallback.provider == "openai":
                return await self._call_openai(fallback.model, messages, **kwargs)
            elif fallback.provider == "anthropic":
                return await self._call_anthropic(fallback.model, messages, **kwargs)
            else:
                raise ConfigurationError(f"Provider não suportado: {fallback.provider}")
        except Exception as e:
            raise FallbackError(fallback.provider, fallback.model, e)

    # =========================================================================
    # Main API
    # =========================================================================

    async def complete(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera uma resposta do LLM com failover automático.

        Fluxo:
        1. Tenta GPU primária (direto, sem passar pelo servidor Dumont)
        2. Se falhar e auto_failover=True → tenta fallback models em ordem
        3. Retorna resposta no formato OpenAI

        Args:
            prompt: Prompt do usuário (string ou lista de mensagens)
            system: System prompt opcional
            **kwargs: temperature, max_tokens, etc

        Returns:
            Resposta no formato OpenAI:
            {
                "choices": [{"message": {"role": "assistant", "content": "..."}}],
                "model": "...",
                "usage": {...}
            }

        Raises:
            GPUConnectionError: Se GPU falhar e auto_failover=False
            FallbackError: Se todos os fallbacks falharem
        """
        # Normaliza prompt para formato de mensagens
        if isinstance(prompt, str):
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = prompt

        # Busca config se necessário
        if not self.config.gpu and self.config.api_key:
            await self.fetch_config()

        # Tenta GPU primária
        if self.config.gpu:
            try:
                logger.info(f"Tentando GPU: {self.config.gpu.url}")
                result = await self._call_gpu(messages, **kwargs)
                result["_source"] = "gpu"
                result["_gpu_url"] = self.config.gpu.url
                return result
            except GPUConnectionError as e:
                logger.warning(f"GPU falhou: {e}")
                if not self.config.auto_failover:
                    raise

        # Failover para modelos configurados
        if not self.config.fallback_models:
            raise ConfigurationError(
                "GPU não disponível e nenhum modelo de fallback configurado"
            )

        # Ordena por prioridade
        fallbacks = sorted(self.config.fallback_models, key=lambda x: x.priority)

        last_error = None
        for fallback in fallbacks:
            try:
                logger.info(f"Tentando fallback: {fallback.full_name}")
                result = await self._call_fallback(fallback, messages, **kwargs)
                result["_source"] = "fallback"
                result["_fallback_model"] = fallback.full_name
                return result
            except FallbackError as e:
                logger.warning(f"Fallback {fallback.full_name} falhou: {e}")
                last_error = e
                continue

        raise FallbackError(
            "all",
            "all models failed",
            last_error.original_error if last_error else None
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Alias para complete() com lista de mensagens.

        Compatível com API OpenAI.
        """
        return await self.complete(messages, **kwargs)

    def get_content(self, response: Dict[str, Any]) -> str:
        """
        Extrai conteúdo de texto da resposta.

        Args:
            response: Resposta do complete()

        Returns:
            Texto da resposta
        """
        return response["choices"][0]["message"]["content"]

    # =========================================================================
    # Streaming (Opcional)
    # =========================================================================

    async def stream(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Gera resposta em streaming.

        Yields:
            Chunks de texto conforme são gerados

        Nota: Streaming usa mesma lógica de failover.
        """
        # Normaliza prompt
        if isinstance(prompt, str):
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = prompt

        kwargs["stream"] = True

        # Busca config se necessário
        if not self.config.gpu and self.config.api_key:
            await self.fetch_config()

        # Tenta GPU primária com streaming
        if self.config.gpu:
            try:
                async for chunk in self._stream_gpu(messages, **kwargs):
                    yield chunk
                return
            except GPUConnectionError:
                if not self.config.auto_failover:
                    raise

        # Fallback streaming
        fallbacks = sorted(self.config.fallback_models, key=lambda x: x.priority)
        for fallback in fallbacks:
            try:
                async for chunk in self._stream_fallback(fallback, messages, **kwargs):
                    yield chunk
                return
            except FallbackError:
                continue

        raise FallbackError("all", "all models failed")

    async def _stream_gpu(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream da GPU."""
        if not self.config.gpu:
            raise GPUConnectionError("", Exception("GPU não configurada"))

        client = await self._get_http_client()
        url = f"{self.config.gpu.url}/v1/chat/completions"

        payload = {
            "model": self.config.gpu.model,
            "messages": messages,
            **kwargs
        }

        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        return
                    try:
                        import json
                        chunk = json.loads(data)
                        if content := chunk.get("choices", [{}])[0].get("delta", {}).get("content"):
                            yield content
                    except Exception:
                        continue

    async def _stream_fallback(
        self,
        fallback: FallbackModel,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream do fallback (OpenRouter)."""
        if fallback.provider != "openrouter":
            # Por simplicidade, só implementa streaming para OpenRouter
            result = await self._call_fallback(fallback, messages, **kwargs)
            yield self.get_content(result)
            return

        client = await self._get_http_client()
        url = "https://openrouter.ai/api/v1/chat/completions"

        payload = {
            "model": fallback.model,
            "messages": messages,
            **kwargs
        }

        async with client.stream(
            "POST",
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.config.openrouter_api_key}",
                "HTTP-Referer": "https://dumontcloud.com",
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        return
                    try:
                        import json
                        chunk = json.loads(data)
                        if content := chunk.get("choices", [{}])[0].get("delta", {}).get("content"):
                            yield content
                    except Exception:
                        continue
