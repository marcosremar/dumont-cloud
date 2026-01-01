"""
Vast.ai GPU Provider Implementation
Implements IGpuProvider interface (Dependency Inversion Principle)
"""
import json
import logging
import time
import requests
from typing import List, Optional, Dict, Any, TypeVar, Callable
from datetime import datetime
from functools import wraps

from ...core.exceptions import (
    VastAPIException,
    ServiceUnavailableException,
    NotFoundException,
    InsufficientBalanceException,
    OfferUnavailableException,
    RateLimitException,
    InvalidOfferException,
)
from ...core.constants import VAST_API_URL, VAST_DEFAULT_TIMEOUT
from ...domain.repositories import IGpuProvider
from ...domain.models import GpuOffer, Instance

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 2.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
) -> Callable:
    """
    Decorator for retrying API calls on rate limit (429) and transient errors.
    Uses exponential backoff: delay = min(initial_delay * (backoff_factor ** attempt), max_delay)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if e.response is not None else 0
                    # Retry on rate limit (429) or server errors (5xx)
                    if status_code == 429 or (500 <= status_code < 600):
                        last_exception = e
                        if attempt < max_retries:
                            # Check for Retry-After header
                            retry_after = int(e.response.headers.get("Retry-After", 0)) if e.response else 0
                            wait_time = max(delay, retry_after)
                            logger.warning(
                                f"[VastProvider] {func.__name__} got {status_code}, "
                                f"retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(wait_time)
                            delay = min(delay * backoff_factor, max_delay)
                            continue
                    raise
                except requests.exceptions.RequestException as e:
                    # Retry on connection errors
                    error_str = str(e).lower()
                    if "429" in str(e) or "too many" in error_str or "connection" in error_str or "timeout" in error_str:
                        last_exception = e
                        if attempt < max_retries:
                            logger.warning(
                                f"[VastProvider] {func.__name__} failed ({e}), "
                                f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(delay)
                            delay = min(delay * backoff_factor, max_delay)
                            continue
                    raise

            if last_exception:
                raise last_exception
            return None  # Should not reach here
        return wrapper
    return decorator


class VastProvider(IGpuProvider):
    """
    Vast.ai implementation of IGpuProvider.
    Handles all communication with vast.ai API.
    """

    # Tipos de máquina suportados pelo VAST.ai
    MACHINE_TYPES = ["on-demand", "interruptible", "bid"]

    def __init__(self, api_key: str, api_url: str = VAST_API_URL, timeout: int = VAST_DEFAULT_TIMEOUT):
        """
        Initialize Vast provider

        Args:
            api_key: Vast.ai API key
            api_url: Vast.ai API URL (optional, for testing)
            timeout: Request timeout in seconds
        """
        if not api_key:
            raise ValueError("Vast.ai API key is required")

        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {api_key}"}

    @retry_with_backoff(max_retries=3, initial_delay=2.0, max_delay=30.0)
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: Optional[int] = None,
        raise_for_status: bool = True
    ) -> requests.Response:
        """
        Make HTTP request to VAST.ai API with automatic retry on rate limit and transient errors.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (will be appended to api_url)
            params: Query parameters
            json_data: JSON body data
            timeout: Request timeout (uses self.timeout if not specified)
            raise_for_status: Whether to raise exception on non-2xx responses

        Returns:
            Response object
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            params=params,
            json=json_data,
            timeout=timeout or self.timeout,
        )
        # For rate limiting to work with decorator, we need to raise on 429/5xx
        if response.status_code == 429 or (500 <= response.status_code < 600):
            response.raise_for_status()
        # For other errors, only raise if requested
        if raise_for_status and not response.ok:
            response.raise_for_status()
        return response

    def _handle_vast_error(self, response: requests.Response, context: str = "", offer_id: int = None) -> None:
        """
        Analisa resposta de erro da VAST.ai e lança exceção apropriada.

        Args:
            response: Response object from requests
            context: Contexto da operação (ex: "criar instância")
            offer_id: ID da oferta se aplicável
        """
        status = response.status_code
        try:
            data = response.json()
            error_msg = data.get("error", data.get("msg", str(data)))
        except:
            error_msg = response.text or f"HTTP {status}"

        error_lower = error_msg.lower()

        # 400 Bad Request - múltiplas causas possíveis
        if status == 400:
            if "balance" in error_lower or "credit" in error_lower or "funds" in error_lower:
                raise InsufficientBalanceException()

            if "not available" in error_lower or "no longer" in error_lower:
                reason = "rented" if "rented" in error_lower else ""
                raise OfferUnavailableException(offer_id or 0, reason)

            if "invalid" in error_lower:
                raise InvalidOfferException(error_msg)

            # Oferta não disponível é o caso mais comum de 400
            if offer_id:
                raise OfferUnavailableException(offer_id, error_msg)

            raise VastAPIException(f"Requisição inválida: {error_msg}")

        # 401 Unauthorized
        if status == 401:
            raise VastAPIException("API key inválida ou expirada. Verifique sua chave em cloud.vast.ai")

        # 402 Payment Required
        if status == 402:
            raise InsufficientBalanceException()

        # 403 Forbidden
        if status == 403:
            raise VastAPIException("Acesso negado. Sua conta pode estar suspensa ou a operação não é permitida")

        # 404 Not Found
        if status == 404:
            if offer_id:
                raise OfferUnavailableException(offer_id, "offline")
            raise NotFoundException(f"Recurso não encontrado: {context}")

        # 429 Rate Limit
        if status == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise RateLimitException(retry_after)

        # 500+ Server Errors
        if status >= 500:
            raise ServiceUnavailableException(
                f"VAST.ai está com problemas temporários (HTTP {status}). Tente novamente em alguns minutos"
            )

        # Erro genérico
        raise VastAPIException(f"Erro VAST.ai ({status}): {error_msg}")

    def _diagnose_create_failure(self, offer_id: int, error: Exception) -> str:
        """
        Diagnostica falha na criação de instância e retorna mensagem amigável.
        """
        error_str = str(error).lower()

        # Tentar obter saldo atual
        try:
            balance_info = self.get_balance()
            balance = balance_info.get("credit", 0)
        except:
            balance = None

        diagnostics = []

        if "400" in error_str:
            diagnostics.append("• A oferta pode ter sido alugada por outro usuário")
            diagnostics.append("• O host pode ter saído do ar")
            diagnostics.append("• O preço pode ter mudado")

        if balance is not None:
            if balance < 1:
                diagnostics.insert(0, f"• ⚠️ Saldo baixo: ${balance:.2f}")
            else:
                diagnostics.append(f"• Saldo disponível: ${balance:.2f}")

        if not diagnostics:
            diagnostics.append("• Erro temporário na API VAST.ai")
            diagnostics.append("• Tente novamente em alguns segundos")

        return "\n".join(diagnostics)

    def search_offers(
        self,
        gpu_name: Optional[str] = None,
        num_gpus: int = 1,
        min_gpu_ram: float = 0,
        min_cpu_cores: int = 1,
        min_cpu_ram: float = 1,
        min_disk: float = 50,
        min_inet_down: float = 500,
        max_price: float = 1.0,
        min_cuda: str = "11.0",
        min_reliability: float = 0.0,
        region: Optional[str] = None,
        verified_only: bool = False,
        static_ip: bool = False,
        limit: int = 50,
    ) -> List[GpuOffer]:
        """Search for available GPU offers"""
        logger.debug(f"Searching offers: gpu={gpu_name}, region={region}, max_price={max_price}")

        # Build query for vast.ai API
        query = {
            "rentable": {"eq": True},
            "num_gpus": {"eq": num_gpus},
            "disk_space": {"gte": min_disk},
            "inet_down": {"gte": min_inet_down},
            "dph_total": {"lte": max_price},
        }

        # Add GPU RAM filter if specified
        if min_gpu_ram > 0:
            query["gpu_ram"] = {"gte": min_gpu_ram * 1024}  # Convert GB to MB

        # Add CPU filters if specified
        if min_cpu_cores > 1:
            query["cpu_cores_effective"] = {"gte": min_cpu_cores}

        if min_cpu_ram > 1:
            query["cpu_ram"] = {"gte": min_cpu_ram * 1024}  # Convert GB to MB

        # Add reliability filter if specified
        if min_reliability > 0:
            query["reliability2"] = {"gte": min_reliability}

        if verified_only:
            query["verified"] = {"eq": True}

        if gpu_name:
            query["gpu_name"] = {"eq": gpu_name}

        if static_ip:
            query["static_ip"] = {"eq": True}

        params = {
            "q": json.dumps(query),
            "order": "dph_total",
            "type": "on-demand",
            "limit": limit,
        }

        try:
            resp = self._make_request("GET", "bundles", params=params)
            data = resp.json()
            offers_data = data.get("offers", []) if isinstance(data, dict) else data

            # Filter by region if specified
            if region:
                region_codes = self._get_region_codes(region)
                offers_data = [
                    o for o in offers_data
                    if any(code in str(o.get("geolocation", "")) for code in region_codes)
                ]

            # Convert to domain models
            offers = []
            for offer_data in offers_data:
                try:
                    offers.append(self._parse_offer(offer_data))
                except Exception as e:
                    logger.warning(f"Failed to parse offer: {e}")
                    continue

            logger.debug(f"Found {len(offers)} offers")
            return offers

        except requests.RequestException as e:
            logger.error(f"Failed to search offers: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error searching offers: {e}")
            raise VastAPIException(f"Failed to search offers: {e}")

    def search_offers_by_type(
        self,
        machine_type: str = "on-demand",
        gpu_name: Optional[str] = None,
        num_gpus: int = 1,
        min_gpu_ram: float = 0,
        min_reliability: float = 0.0,
        region: Optional[str] = None,
        verified_only: bool = False,
        max_price: float = 10.0,
        limit: int = 100,
    ) -> List[GpuOffer]:
        """
        Busca ofertas por tipo de máquina (on-demand, interruptible, bid).

        Args:
            machine_type: Tipo de máquina ("on-demand", "interruptible", "bid", ou None para todas)
            gpu_name: Nome específico da GPU (ex: "RTX 4090")
            num_gpus: Quantidade de GPUs por oferta
            min_gpu_ram: RAM mínima de GPU em GB
            min_reliability: Score mínimo de confiabilidade (0-1)
            region: Região ("US", "EU", "ASIA")
            verified_only: Apenas provedores verificados
            max_price: Preço máximo por hora
            limit: Limite de resultados

        Returns:
            Lista de ofertas com campos expandidos de performance
        """
        logger.debug(f"Searching offers by type: type={machine_type}, gpu={gpu_name}, max_price={max_price}")

        # Build query para API VAST.ai
        query = {
            "rentable": {"eq": True},
            "num_gpus": {"eq": num_gpus},
            "dph_total": {"lte": max_price},
        }

        if min_gpu_ram > 0:
            query["gpu_ram"] = {"gte": min_gpu_ram * 1024}  # GB para MB
        if min_reliability > 0:
            query["reliability2"] = {"gte": min_reliability}
        if verified_only:
            query["verified"] = {"eq": True}
        if gpu_name:
            query["gpu_name"] = {"eq": gpu_name}

        params = {
            "q": json.dumps(query),
            "order": "dph_total",
            "limit": limit,
        }

        # Adicionar tipo se especificado
        if machine_type and machine_type != "all":
            params["type"] = machine_type

        try:
            resp = self._make_request("GET", "bundles", params=params)
            data = resp.json()
            offers_data = data.get("offers", []) if isinstance(data, dict) else data

            # Filtrar por região
            if region:
                region_codes = self._get_region_codes(region)
                offers_data = [
                    o for o in offers_data
                    if any(code in str(o.get("geolocation", "")) for code in region_codes)
                ]

            # Converter para domain models com campos expandidos
            offers = []
            for offer_data in offers_data:
                try:
                    offer = self._parse_offer_extended(offer_data, machine_type or "on-demand")
                    offers.append(offer)
                except Exception as e:
                    logger.warning(f"Failed to parse offer: {e}")
                    continue

            logger.debug(f"Found {len(offers)} offers for type={machine_type}")
            return offers

        except requests.RequestException as e:
            logger.error(f"Failed to search offers by type: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error searching offers by type: {e}")
            raise VastAPIException(f"Failed to search offers by type: {e}")

    def fetch_all_market_data(
        self,
        gpus_to_monitor: List[str],
        machine_types: Optional[List[str]] = None,
        max_price: float = 100.0,
        limit_per_query: int = 200,
    ) -> Dict[str, List[GpuOffer]]:
        """
        Busca dados de mercado completos para todas as GPUs e tipos.

        Args:
            gpus_to_monitor: Lista de GPUs para monitorar
            machine_types: Lista de tipos de máquina (padrão: todos)
            max_price: Preço máximo por hora
            limit_per_query: Limite de resultados por query

        Returns:
            Dict agrupado por "gpu_name:machine_type" -> List[GpuOffer]
        """
        machine_types = machine_types or self.MACHINE_TYPES
        all_offers = {}

        for gpu_name in gpus_to_monitor:
            for machine_type in machine_types:
                key = f"{gpu_name}:{machine_type}"
                try:
                    offers = self.search_offers_by_type(
                        machine_type=machine_type,
                        gpu_name=gpu_name,
                        max_price=max_price,
                        limit=limit_per_query,
                    )
                    all_offers[key] = offers
                    logger.debug(f"Fetched {len(offers)} offers for {key}")
                except Exception as e:
                    logger.warning(f"Failed to fetch {key}: {e}")
                    all_offers[key] = []

        total = sum(len(v) for v in all_offers.values())
        logger.info(f"Total market data fetched: {total} offers across {len(all_offers)} GPU/type combinations")
        return all_offers

    def create_instance(
        self,
        offer_id: int,
        image: str,
        disk_size: float,
        label: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        onstart_cmd: Optional[str] = None,
    ) -> Instance:
        """Create a new GPU instance"""
        logger.info(f"Creating instance from offer {offer_id}")

        # Default onstart script
        if not onstart_cmd:
            onstart_cmd = "touch ~/.no_auto_tmux"

        # Parse env_vars to vast.ai format
        extra_env = []
        if env_vars:
            for key, value in env_vars.items():
                if key.startswith("PORT_"):
                    # Port mapping: PORT_8080 -> -p 8080:8080
                    port = key.replace("PORT_", "")
                    extra_env.append([f"-p {port}:{port}", "1"])
                else:
                    extra_env.append([key, value])

        # Check if port 8080 is requested (for VS Code Online/code-server)
        needs_jupyter_mode = False
        if env_vars:
            for key in env_vars.keys():
                if key == "PORT_8080":
                    needs_jupyter_mode = True
                    break

        payload = {
            "client_id": "me",
            "image": image,
            "disk": int(disk_size),
        }

        # Use jupyter runtype to expose port 8080 (for VS Code Online)
        if needs_jupyter_mode:
            payload["runtype"] = "jupyter"
            logger.info("Using jupyter runtype to expose port 8080 for VS Code Online")

        # Só adicionar campos opcionais se tiverem valor
        if onstart_cmd:
            payload["onstart"] = onstart_cmd
        if extra_env:
            payload["extra_env"] = extra_env
        if label:
            payload["label"] = label

        try:
            endpoint = f"asks/{offer_id}/"
            logger.debug(f"create_instance: PUT {self.api_url}/{endpoint}")
            logger.debug(f"create_instance: payload={payload}")

            resp = self._make_request("PUT", endpoint, json_data=payload, raise_for_status=False)

            logger.debug(f"create_instance: status={resp.status_code}, response={resp.text[:200]}")

            # Usar error handler para respostas de erro
            if not resp.ok:
                logger.warning(f"create_instance: Error {resp.status_code} for offer {offer_id}: {resp.text}")
                self._handle_vast_error(resp, "criar instância", offer_id)

            data = resp.json()
            instance_id = data.get("new_contract")

            if not instance_id:
                raise VastAPIException("VAST.ai não retornou ID da instância. A oferta pode ter expirado.")

            logger.info(f"Created instance {instance_id}")

            # Get full instance details
            return self.get_instance(instance_id)

        except (VastAPIException, OfferUnavailableException, InsufficientBalanceException):
            raise  # Re-raise our custom exceptions
        except requests.exceptions.Timeout:
            raise ServiceUnavailableException(
                "Timeout ao conectar com VAST.ai. A API pode estar lenta ou indisponível."
            )
        except requests.exceptions.ConnectionError:
            raise ServiceUnavailableException(
                "Não foi possível conectar à API VAST.ai. Verifique sua conexão com a internet."
            )
        except requests.RequestException as e:
            logger.error(f"Failed to create instance: {e}")
            diagnosis = self._diagnose_create_failure(offer_id, e)
            raise ServiceUnavailableException(
                f"Falha ao criar instância na VAST.ai.\n\nPossíveis causas:\n{diagnosis}"
            )
        except Exception as e:
            logger.error(f"Unexpected error creating instance: {e}")
            raise VastAPIException(f"Erro inesperado ao criar instância: {e}")

    def create_instance_bid(
        self,
        offer_id: int,
        image: str,
        disk_size: float,
        bid_price: float,
        label: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        onstart_cmd: Optional[str] = None,
    ) -> Instance:
        """
        Cria instância via bidding (spot/interruptível).

        Diferente de create_instance que usa preço fixo (asking price),
        este método permite especificar um preço de bid. A instância
        pode ser interrompida se outro usuário fizer um bid maior.

        Args:
            offer_id: ID da oferta no VAST.ai
            image: Imagem Docker a usar
            disk_size: Tamanho do disco em GB
            bid_price: Preço do bid em $/hr (deve ser >= min_bid da oferta)
            label: Label opcional para identificar a instância
            env_vars: Variáveis de ambiente
            onstart_cmd: Comando a executar no início

        Returns:
            Instance: Instância criada

        Raises:
            VastAPIException: Se o bid for rejeitado
            InsufficientBalanceException: Se não houver saldo
        """
        logger.info(f"Creating SPOT instance from offer {offer_id} with bid ${bid_price:.4f}/hr")

        if not onstart_cmd:
            onstart_cmd = "touch ~/.no_auto_tmux"

        extra_env = []
        if env_vars:
            for key, value in env_vars.items():
                if key.startswith("PORT_"):
                    port = key.replace("PORT_", "")
                    extra_env.append([f"-p {port}:{port}", "1"])
                else:
                    extra_env.append([key, value])

        payload = {
            "client_id": "me",
            "image": image,
            "disk": int(disk_size),
            "price": bid_price,  # Preço do bid
            "onstart": onstart_cmd,
            "extra_env": extra_env,
        }

        if label:
            payload["label"] = label

        try:
            # Usa endpoint /bids/ ao invés de /asks/
            resp = self._make_request("PUT", f"bids/{offer_id}/", json_data=payload, raise_for_status=False)

            if not resp.ok:
                self._handle_vast_error(resp, "criar instância spot", offer_id)

            data = resp.json()
            instance_id = data.get("new_contract")

            if not instance_id:
                raise VastAPIException("VAST.ai não retornou ID da instância spot. O bid pode ter sido rejeitado.")

            logger.info(f"Created SPOT instance {instance_id} with bid ${bid_price:.4f}/hr")

            return self.get_instance(instance_id)

        except (VastAPIException, OfferUnavailableException, InsufficientBalanceException):
            raise
        except requests.exceptions.Timeout:
            raise ServiceUnavailableException(
                "Timeout ao conectar com VAST.ai para criar instância spot."
            )
        except requests.exceptions.ConnectionError:
            raise ServiceUnavailableException(
                "Não foi possível conectar à API VAST.ai."
            )
        except Exception as e:
            logger.error(f"Failed to create spot instance: {e}")
            raise VastAPIException(f"Erro ao criar instância spot: {e}")

    def get_interruptible_offers(
        self,
        region: Optional[str] = None,
        gpu_name: Optional[str] = None,
        max_price: float = 1.0,
        min_inet_down: float = 100,
        min_disk: float = 20,
    ) -> List[GpuOffer]:
        """
        Busca ofertas interruptíveis (spot) disponíveis.

        Ofertas interruptíveis são mais baratas mas podem ser
        interrompidas se outro usuário fizer um bid maior.

        Args:
            region: Região desejada (US, EU, ASIA, etc)
            gpu_name: Nome da GPU (RTX 4090, etc)
            max_price: Preço máximo por hora
            min_inet_down: Velocidade mínima de download em Mbps
            min_disk: Espaço mínimo de disco em GB

        Returns:
            Lista de ofertas ordenadas por preço (mais barato primeiro)
        """
        logger.info(f"Searching interruptible offers: region={region}, gpu={gpu_name}, max_price=${max_price}")

        query = {
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "min_bid": {"lte": max_price},
            "inet_down": {"gte": min_inet_down},
            "disk_space": {"gte": min_disk},
        }

        # Filtro de região
        if region and region != "global":
            region_codes = self._get_region_codes(region)
            if region_codes:
                query["geolocation"] = {"in": region_codes}

        # Filtro de GPU
        if gpu_name:
            query["gpu_name"] = {"eq": gpu_name}

        try:
            params = {
                "q": json.dumps(query),
                "order": "min_bid",  # Ordenar por preço (mais barato primeiro)
                "type": "bid",  # Apenas ofertas que aceitam bid
            }
            resp = self._make_request("GET", "bundles/", params=params, raise_for_status=False)

            if not resp.ok:
                logger.warning(f"Failed to fetch interruptible offers: HTTP {resp.status_code}")
                return []

            data = resp.json()
            raw_offers = data.get("offers", [])

            offers = []
            for offer_data in raw_offers:
                try:
                    offer = self._parse_offer(offer_data)
                    offer.machine_type = "interruptible"
                    offer.min_bid = offer_data.get("min_bid", 0)
                    offers.append(offer)
                except Exception as e:
                    logger.debug(f"Failed to parse offer: {e}")
                    continue

            logger.info(f"Found {len(offers)} interruptible offers")
            return offers

        except Exception as e:
            logger.error(f"Error fetching interruptible offers: {e}")
            return []

    def get_instance(self, instance_id: int) -> Instance:
        """Get instance details by ID"""
        try:
            resp = self._make_request("GET", f"instances/{instance_id}/", raise_for_status=False)

            # Handle 404 or empty response
            if resp.status_code == 404:
                raise NotFoundException(f"Instance {instance_id} not found")

            if not resp.ok:
                resp.raise_for_status()
            data = resp.json()

            # vast.ai returns 'instances' as object or list
            instances_data = data.get("instances")
            if isinstance(instances_data, list):
                if not instances_data:
                    raise NotFoundException(f"Instance {instance_id} not found")
                instance_data = instances_data[0]
            elif isinstance(instances_data, dict):
                if not instances_data or not instances_data.get("id"):
                    raise NotFoundException(f"Instance {instance_id} not found")
                instance_data = instances_data
            else:
                instance_data = data
                if not instance_data or not instance_data.get("id"):
                    raise NotFoundException(f"Instance {instance_id} not found")

            return self._parse_instance(instance_data)

        except NotFoundException:
            raise
        except requests.RequestException as e:
            logger.error(f"Failed to get instance {instance_id}: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting instance: {e}")
            raise VastAPIException(f"Failed to get instance: {e}")

    def get_instance_status(self, instance_id: int) -> Dict[str, Any]:
        """Get instance status as dict (compatibility method for ServerlessManager)"""
        try:
            instance = self.get_instance(instance_id)
            return {
                "id": instance.id,
                "actual_status": instance.actual_status,
                "status": instance.status,
                "ssh_host": instance.ssh_host,
                "ssh_port": instance.ssh_port,
                "gpu_name": instance.gpu_name,
                "dph_total": instance.dph_total,
                "public_ipaddr": instance.public_ipaddr,
            }
        except Exception as e:
            logger.error(f"Failed to get instance status {instance_id}: {e}")
            return {"actual_status": "unknown", "error": str(e)}

    def list_instances(self) -> List[Instance]:
        """List all user instances"""
        try:
            resp = self._make_request("GET", "instances/", params={"owner": "me"})
            data = resp.json()
            instances_data = data.get("instances", [])

            instances = []
            for instance_data in instances_data:
                try:
                    instances.append(self._parse_instance(instance_data))
                except Exception as e:
                    logger.warning(f"Failed to parse instance: {e}")
                    continue

            return instances

        except requests.RequestException as e:
            logger.error(f"Failed to list instances: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing instances: {e}")
            raise VastAPIException(f"Failed to list instances: {e}")

    def destroy_instance(self, instance_id: int) -> bool:
        """Destroy an instance"""
        logger.info(f"Destroying instance {instance_id}")
        try:
            resp = self._make_request("DELETE", f"instances/{instance_id}/", raise_for_status=False)
            success = resp.status_code in [200, 204]
            if success:
                logger.info(f"Instance {instance_id} destroyed")
            return success

        except requests.RequestException as e:
            logger.error(f"Failed to destroy instance: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error destroying instance: {e}")
            return False

    def pause_instance(self, instance_id: int) -> bool:
        """
        Pause (stop) an instance.

        VAST.ai uses {"state": "stopped"} to pause instances.
        The intended_status will change to "stopped".
        """
        logger.info(f"Stopping instance {instance_id}")
        try:
            resp = self._make_request(
                "PUT", f"instances/{instance_id}/",
                json_data={"state": "stopped"},
                raise_for_status=False
            )
            success = resp.status_code == 200 and resp.json().get("success", False)
            if success:
                logger.info(f"Instance {instance_id} stop requested")
            else:
                logger.warning(f"Instance {instance_id} stop failed: {resp.text}")
            return success

        except requests.RequestException as e:
            logger.error(f"Failed to stop instance: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error stopping instance: {e}")
            return False

    def resume_instance(self, instance_id: int) -> bool:
        """
        Resume (start) a stopped instance.

        VAST.ai uses {"state": "running"} to start instances.
        The intended_status will change to "running".
        """
        logger.info(f"Starting instance {instance_id}")
        try:
            resp = self._make_request(
                "PUT", f"instances/{instance_id}/",
                json_data={"state": "running"},
                raise_for_status=False
            )
            success = resp.status_code == 200 and resp.json().get("success", False)
            if success:
                logger.info(f"Instance {instance_id} start requested")
            else:
                logger.warning(f"Instance {instance_id} start failed: {resp.text}")
            return success

        except requests.RequestException as e:
            logger.error(f"Failed to start instance: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error starting instance: {e}")
            return False

    def get_instance_metrics(self, instance_id: int) -> Dict[str, Any]:
        """Get real-time metrics for an instance (via SSH)"""
        # This would require SSH access - implement via SSH client
        # For now, return empty metrics
        logger.warning("get_instance_metrics not yet implemented via SSH")
        return {}

    def get_balance(self) -> Dict[str, Any]:
        """Get account balance (not part of IGpuProvider, but useful)"""
        try:
            resp = self._make_request("GET", "users/current/")
            data = resp.json()

            # Preserve negative values - only default to 0 if key is missing or None
            credit_value = data.get("credit")
            if credit_value is None:
                credit_value = 0

            balance_value = data.get("balance")
            if balance_value is None:
                balance_value = 0

            return {
                "credit": credit_value,
                "balance": balance_value,
                "balance_threshold": data.get("balance_threshold") or 0,
                "email": data.get("email", ""),
            }
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return {"error": str(e), "credit": 0}

    # =========================================================================
    # PRÉ-VALIDAÇÕES - Verificar antes de executar operações
    # =========================================================================

    def validate_before_create(self, offer_id: int, min_balance: float = 0.10) -> Dict[str, Any]:
        """
        Valida pré-requisitos antes de criar uma instância.

        Retorna dict com:
            - valid: bool - Se pode prosseguir
            - errors: list - Lista de erros encontrados
            - warnings: list - Lista de avisos
            - balance: float - Saldo atual
            - offer: dict - Dados da oferta (se válida)

        Raises:
            InsufficientBalanceException: Se saldo insuficiente
            OfferUnavailableException: Se oferta não disponível
            ServiceUnavailableException: Se API inacessível
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "balance": 0,
            "offer": None
        }

        # 1. Verificar conectividade com VAST.ai
        try:
            balance_info = self.get_balance()
            if "error" in balance_info:
                result["valid"] = False
                result["errors"].append(f"Não foi possível verificar saldo: {balance_info['error']}")
                raise ServiceUnavailableException("Não foi possível conectar à API VAST.ai")

            result["balance"] = balance_info.get("credit", 0) + balance_info.get("balance", 0)
        except ServiceUnavailableException:
            raise
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Erro ao verificar conectividade: {e}")
            raise ServiceUnavailableException(f"Falha ao conectar com VAST.ai: {e}")

        # 2. Verificar saldo mínimo
        if result["balance"] < min_balance:
            result["valid"] = False
            result["errors"].append(
                f"Saldo insuficiente: ${result['balance']:.2f} (mínimo: ${min_balance:.2f})"
            )
            raise InsufficientBalanceException(required=min_balance, available=result["balance"])

        if result["balance"] < 1.0:
            result["warnings"].append(f"Saldo baixo: ${result['balance']:.2f}")

        # 3. Nota: Não verificamos existência de oferta específica porque:
        #    - A query {"id": {"eq": offer_id}} não funciona consistentemente na API VAST
        #    - Ofertas são muito transientes (podem ser alugadas em segundos)
        #    - A tentativa de criar a instância retornará erro claro se oferta indisponível
        #
        # Apenas adicionamos um aviso que a verificação de oferta foi pulada
        result["warnings"].append(
            f"Verificação de disponibilidade da oferta {offer_id} não realizada. "
            "Se a oferta já foi alugada, a criação falhará com erro claro."
        )
        logger.debug(f"Skipping offer availability check for {offer_id} (VAST.ai API limitation)")

        return result

    def check_api_health(self) -> Dict[str, Any]:
        """
        Verifica saúde da API VAST.ai.

        Retorna:
            - healthy: bool
            - latency_ms: float
            - message: str
        """
        import time as _time

        start = _time.time()
        try:
            resp = requests.get(
                f"{self.api_url}/bundles/",
                params={"q": json.dumps({"rentable": {"eq": True}}), "limit": 1},
                headers=self.headers,
                timeout=5,
            )
            latency = (_time.time() - start) * 1000

            if resp.ok:
                return {
                    "healthy": True,
                    "latency_ms": round(latency, 2),
                    "message": "API VAST.ai operacional"
                }
            else:
                return {
                    "healthy": False,
                    "latency_ms": round(latency, 2),
                    "message": f"API retornou erro: HTTP {resp.status_code}"
                }

        except requests.exceptions.Timeout:
            return {
                "healthy": False,
                "latency_ms": 5000,
                "message": "API VAST.ai não respondeu (timeout)"
            }
        except requests.exceptions.ConnectionError:
            return {
                "healthy": False,
                "latency_ms": 0,
                "message": "Não foi possível conectar à API VAST.ai"
            }
        except Exception as e:
            return {
                "healthy": False,
                "latency_ms": 0,
                "message": f"Erro: {e}"
            }

    # Helper methods

    def _get_region_codes(self, region: str) -> List[str]:
        """Get country codes for a region"""
        regions = {
            "EU": ["ES", "DE", "FR", "NL", "IT", "PL", "CZ", "BG", "UK", "GB",
                   "Spain", "Germany", "France", "Netherlands", "Poland",
                   "Czechia", "Bulgaria", "Sweden", "Norway", "Finland", "SE",
                   "Belgium", "BE", "Austria", "AT", "Switzerland", "CH",
                   "Portugal", "PT", "Ireland", "IE", "Denmark", "DK"],
            "US": ["US", "United States", "CA", "Canada", "North America"],
            "ASIA": ["JP", "Japan", "KR", "Korea", "SG", "Singapore", "TW", "Taiwan",
                     "CN", "China", "Shaanxi", "HK", "Hong Kong", "IN", "India",
                     "TH", "Thailand", "MY", "Malaysia", "ID", "Indonesia"],
        }
        return regions.get(region.upper(), [])

    def _parse_offer(self, data: Dict[str, Any]) -> GpuOffer:
        """Parse offer data from vast.ai API"""
        return GpuOffer(
            id=data.get("id", 0),
            gpu_name=data.get("gpu_name", "Unknown"),
            num_gpus=data.get("num_gpus", 1),
            gpu_ram=data.get("gpu_ram", 0),
            cpu_cores=data.get("cpu_cores", 0),
            cpu_ram=data.get("cpu_ram", 0),
            disk_space=data.get("disk_space", 0),
            inet_down=data.get("inet_down", 0),
            inet_up=data.get("inet_up", 0),
            dph_total=data.get("dph_total", 0),
            geolocation=data.get("geolocation", "Unknown"),
            reliability=data.get("reliability2", 0),
            cuda_version=str(data.get("cuda_max_good", "Unknown")),
            verified=data.get("verified", False),
            static_ip=data.get("static_ip", False),
            storage_cost=data.get("storage_cost"),
            inet_up_cost=data.get("inet_up_cost"),
            inet_down_cost=data.get("inet_down_cost"),
            machine_id=data.get("machine_id"),
            hostname=data.get("hostname"),
        )

    def _parse_offer_extended(self, data: Dict[str, Any], machine_type: str) -> GpuOffer:
        """
        Parse offer data com todos os campos de performance expandidos.

        Args:
            data: Dados brutos da API VAST.ai
            machine_type: Tipo de máquina (on-demand, interruptible, bid)

        Returns:
            GpuOffer com campos de performance preenchidos
        """
        # GPU RAM pode vir em MB ou GB dependendo do endpoint
        gpu_ram_raw = data.get("gpu_ram", 0)
        gpu_ram_gb = gpu_ram_raw / 1024 if gpu_ram_raw > 100 else gpu_ram_raw

        # Extrair métricas de performance
        total_flops = data.get("total_flops", 0)
        dlperf = data.get("dlperf", 0)
        dph = data.get("dph_total", 0)

        # Calcular métricas de custo-benefício
        cost_per_tflops = None
        cost_per_gb_vram = None
        dlperf_per_dphtotal = None

        if total_flops and total_flops > 0 and dph > 0:
            cost_per_tflops = dph / total_flops

        if gpu_ram_gb and gpu_ram_gb > 0 and dph > 0:
            cost_per_gb_vram = dph / gpu_ram_gb

        if dlperf and dlperf > 0 and dph > 0:
            dlperf_per_dphtotal = dlperf / dph

        offer = GpuOffer(
            id=data.get("id", 0),
            gpu_name=data.get("gpu_name", "Unknown"),
            num_gpus=data.get("num_gpus", 1),
            gpu_ram=gpu_ram_gb,
            cpu_cores=data.get("cpu_cores", 0),
            cpu_ram=data.get("cpu_ram", 0) / 1024 if data.get("cpu_ram", 0) > 100 else data.get("cpu_ram", 0),
            disk_space=data.get("disk_space", 0),
            inet_down=data.get("inet_down", 0),
            inet_up=data.get("inet_up", 0),
            dph_total=dph,
            geolocation=data.get("geolocation", "Unknown"),
            reliability=data.get("reliability2", 0),
            cuda_version=str(data.get("cuda_max_good", "Unknown")),
            verified=data.get("verified", False),
            static_ip=data.get("static_ip", False),
            # Custos adicionais
            storage_cost=data.get("storage_cost"),
            inet_up_cost=data.get("inet_up_cost"),
            inet_down_cost=data.get("inet_down_cost"),
            # Identificadores
            machine_id=data.get("machine_id"),
            hostname=data.get("hostname"),
            # Campos de performance (novos)
            total_flops=total_flops,
            dlperf=dlperf,
            dlperf_per_dphtotal=dlperf_per_dphtotal,
            gpu_mem_bw=data.get("gpu_mem_bw"),
            pcie_bw=data.get("pcie_bw"),
            # Tipo de máquina
            machine_type=machine_type,
            min_bid=data.get("min_bid"),
            duration=data.get("duration"),
            # Métricas calculadas
            cost_per_tflops=cost_per_tflops,
            cost_per_gb_vram=cost_per_gb_vram,
        )

        return offer

    def _parse_instance(self, data: Dict[str, Any]) -> Instance:
        """Parse instance data from vast.ai API"""
        # VAST.ai returns ssh_port directly in response
        # See: https://docs.vast.ai/api
        ssh_port = data.get("ssh_port")
        ports = data.get("ports", {})

        # Fallback: try to extract from ports mapping if direct field not available
        if not ssh_port:
            ssh_mapping = ports.get("22/tcp", [{}])
            ssh_port = ssh_mapping[0].get("HostPort") if ssh_mapping else None

        # Parse dates
        start_date = None
        end_date = None
        if data.get("start_date"):
            try:
                start_date = datetime.fromtimestamp(data["start_date"])
            except:
                pass
        if data.get("end_date"):
            try:
                end_date = datetime.fromtimestamp(data["end_date"])
            except:
                pass

        return Instance(
            id=data.get("id", 0),
            status=data.get("intended_status", "unknown"),
            actual_status=data.get("actual_status", "unknown"),
            gpu_name=data.get("gpu_name", "Unknown"),
            num_gpus=data.get("num_gpus", 1),
            gpu_ram=data.get("gpu_ram", 0),
            cpu_cores=data.get("cpu_cores", 0),
            cpu_ram=data.get("cpu_ram", 0),
            disk_space=data.get("disk_space", 0),
            dph_total=data.get("dph_total", 0),
            public_ipaddr=data.get("public_ipaddr"),
            ssh_host=data.get("ssh_host"),
            ssh_port=ssh_port,
            start_date=start_date,
            end_date=end_date,
            image_uuid=data.get("image_uuid"),
            label=data.get("label"),
            ports=ports,
            machine_id=data.get("machine_id"),
            hostname=data.get("hostname"),
            geolocation=data.get("geolocation"),
            reliability=data.get("reliability2"),
            cuda_version=str(data.get("cuda_max_good") or "Unknown"),
        )
