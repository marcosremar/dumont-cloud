"""
Fixtures compartilhadas para testes do Dumont SDK.

Inclui rate limiter, client configurado, e fixtures de integração.
"""
import os
import asyncio
import pytest
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path

# Carregar .env se existir
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# Configurações do ambiente de teste
# Podem ser passadas via pytest --api-key=xxx ou variável de ambiente
TEST_API_URL = os.environ.get("DUMONT_TEST_API_URL", "http://localhost:8766")
TEST_API_KEY = os.environ.get("DUMONT_API_KEY", "")
TEST_USERNAME = os.environ.get("DUMONT_TEST_USERNAME", "")
TEST_PASSWORD = os.environ.get("DUMONT_TEST_PASSWORD", "")
TEST_OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")


def pytest_addoption(parser):
    """Adiciona opções de linha de comando para testes."""
    parser.addoption(
        "--api-key",
        action="store",
        default=None,
        help="Dumont API key para testes de integração"
    )
    parser.addoption(
        "--api-url",
        action="store",
        default=None,
        help="URL da API Dumont para testes"
    )
    parser.addoption(
        "--openrouter-key",
        action="store",
        default=None,
        help="OpenRouter API key para testes de LLM"
    )


@pytest.fixture(scope="session")
def api_key(request):
    """API key para testes - via CLI ou env."""
    key = request.config.getoption("--api-key") or TEST_API_KEY
    return key


@pytest.fixture(scope="session")
def api_url(request):
    """URL da API para testes - via CLI ou env."""
    url = request.config.getoption("--api-url") or TEST_API_URL
    return url


@pytest.fixture(scope="session")
def openrouter_key(request):
    """OpenRouter key para testes - via CLI ou env."""
    key = request.config.getoption("--openrouter-key") or TEST_OPENROUTER_KEY
    return key


# =============================================================================
# Rate Limiter (evita sobrecarga da API em testes)
# =============================================================================

class RateLimiter:
    """Rate limiter simples para testes."""

    def __init__(self, requests_per_second: float = 2.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request = 0.0
        self._lock = asyncio.Lock()

    async def wait(self):
        """Aguarda se necessário para respeitar o rate limit."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_request
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_request = time.time()


@pytest.fixture(scope="session")
def rate_limiter():
    """Rate limiter compartilhado entre todos os testes."""
    return RateLimiter(requests_per_second=2.0)


# =============================================================================
# SDK Client Fixtures
# =============================================================================

@pytest.fixture
async def sdk_client(api_key, api_url, openrouter_key):
    """
    Cliente SDK configurado para testes.

    Usa parâmetros CLI ou variáveis de ambiente.
    """
    from dumont_sdk import DumontClient

    client = DumontClient(
        api_key=api_key,
        base_url=api_url,
        openrouter_api_key=openrouter_key,
        auto_fetch_config=False,
    )

    yield client

    await client.close()


@pytest.fixture
async def authenticated_client(sdk_client, rate_limiter):
    """
    Cliente SDK autenticado via login.

    Requer DUMONT_TEST_USERNAME e DUMONT_TEST_PASSWORD.
    """
    if not TEST_USERNAME or not TEST_PASSWORD:
        pytest.skip("Credenciais de teste não configuradas")

    await rate_limiter.wait()
    await sdk_client.login(TEST_USERNAME, TEST_PASSWORD)

    yield sdk_client


@pytest.fixture
async def client_with_api_key(api_key, api_url, openrouter_key):
    """
    Cliente SDK com API key (sem login).

    Requer --api-key ou DUMONT_API_KEY.
    """
    if not api_key:
        pytest.skip("API key não configurada (use --api-key=xxx)")

    from dumont_sdk import DumontClient

    client = DumontClient(
        api_key=api_key,
        base_url=api_url,
        openrouter_api_key=openrouter_key,
        auto_fetch_config=True,
    )

    yield client

    await client.close()


# =============================================================================
# Instance Fixtures
# =============================================================================

@dataclass
class TestInstance:
    """Instância de teste."""
    id: int
    gpu_name: str
    ssh_command: Optional[str] = None
    public_ip: Optional[str] = None
    ssh_port: Optional[int] = None


@pytest.fixture
async def real_instance(client_with_api_key, rate_limiter) -> Optional[TestInstance]:
    """
    Obtém uma instância real rodando para testes de integração.

    Usa a primeira instância running disponível.
    """
    await rate_limiter.wait()

    try:
        instances = await client_with_api_key.instances.list()

        for inst in instances:
            if inst.is_running:
                return TestInstance(
                    id=inst.id,
                    gpu_name=inst.gpu_name,
                    ssh_command=inst.ssh_command,
                    public_ip=inst.public_ipaddr,
                    ssh_port=inst.ssh_port,
                )

        pytest.skip("Nenhuma instância rodando disponível")

    except Exception as e:
        pytest.skip(f"Erro ao obter instâncias: {e}")


# =============================================================================
# GPU Reservation Fixtures - Cria e destrói máquinas para testes
# =============================================================================

# Lista de tipos de GPU para usar em testes paralelos
GPU_TYPES_FOR_TESTS = [
    "RTX 4090",
    "RTX 3090",
    "RTX 4080",
    "RTX 3080",
    "RTX 4070",
    "A100",
    "A10",
    "L40",
]


async def _wait_for_instance_running(
    client,
    instance_id: int,
    timeout: int = 180,
    poll_interval: int = 5
) -> Optional[Any]:
    """
    Aguarda uma instância ficar em estado running.

    Args:
        client: DumontClient
        instance_id: ID da instância
        timeout: Timeout em segundos
        poll_interval: Intervalo entre verificações

    Returns:
        Instance se running, None se timeout
    """
    import time
    start = time.time()

    while time.time() - start < timeout:
        try:
            instance = await client.instances.get(instance_id)
            if instance.is_running and instance.public_ipaddr:
                return instance
        except Exception:
            pass

        await asyncio.sleep(poll_interval)

    return None


@pytest.fixture
async def reserved_gpu_instance(client_with_api_key, rate_limiter):
    """
    Fixture que reserva uma GPU real para o teste.

    1. Busca a oferta mais barata disponível
    2. Cria a instância (tenta múltiplas ofertas se necessário)
    3. Aguarda ficar running
    4. Fornece a instância para o teste
    5. Destrói a instância ao final (cleanup)

    Uso:
        @pytest.mark.requires_instance
        async def test_algo(reserved_gpu_instance):
            instance = reserved_gpu_instance
            # usa instance.id, instance.public_ipaddr, etc
    """
    import uuid

    instance_id = None
    test_instance = None

    try:
        await rate_limiter.wait()

        # Buscar ofertas baratas
        offers = await client_with_api_key.instances.search_offers(
            max_price=1.50,  # Máximo $1.50/hora para testes (aumentado para mais opções)
            limit=20,
        )

        if not offers:
            pytest.skip("Nenhuma oferta GPU disponível para reserva")
            return

        # Ordenar por preço (mais barato primeiro)
        sorted_offers = sorted(offers, key=lambda o: o.dph_total)

        # Tentar criar instância com as ofertas disponíveis
        last_error = None
        max_attempts = min(5, len(sorted_offers))  # Tentar até 5 ofertas diferentes

        for i, offer in enumerate(sorted_offers[:max_attempts]):
            await rate_limiter.wait()

            test_label = f"sdk-test-{uuid.uuid4().hex[:8]}"

            try:
                instance = await client_with_api_key.instances.create(
                    offer_id=offer.id,
                    image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
                    disk_size=20,
                    label=test_label,
                )

                instance_id = instance.id

                # Aguardar ficar running
                running_instance = await _wait_for_instance_running(
                    client_with_api_key,
                    instance_id,
                    timeout=180,
                )

                if running_instance:
                    test_instance = TestInstance(
                        id=running_instance.id,
                        gpu_name=running_instance.gpu_name,
                        ssh_command=running_instance.ssh_command,
                        public_ip=running_instance.public_ipaddr,
                        ssh_port=running_instance.ssh_port,
                    )
                    break  # Sucesso! Sair do loop

                # Instância não ficou running, destruir e tentar próxima
                try:
                    await client_with_api_key.instances.destroy(instance_id)
                except Exception:
                    pass
                instance_id = None

            except Exception as e:
                error_str = str(e).lower()
                last_error = e

                # Detectar erro de crédito insuficiente (fatal - não adianta tentar outras ofertas)
                if "crédito insuficiente" in error_str or "insufficient" in error_str or "402" in str(e):
                    pytest.skip("Crédito insuficiente na conta Vast.ai - adicione crédito em https://vast.ai/billing")
                    return

                # Destruir instância se foi criada
                if instance_id:
                    try:
                        await client_with_api_key.instances.destroy(instance_id)
                    except Exception:
                        pass
                    instance_id = None
                # Continuar tentando próxima oferta
                continue

        if test_instance is None:
            if last_error:
                error_str = str(last_error).lower()
                if "crédito" in error_str or "credit" in error_str:
                    pytest.skip("Crédito insuficiente na conta Vast.ai")
                else:
                    pytest.skip(f"Falha ao criar instância após {max_attempts} tentativas: {last_error}")
            else:
                pytest.skip(f"Nenhuma instância ficou running no timeout após {max_attempts} tentativas")
            return

    except pytest.skip.Exception:
        # Re-raise skip para que pytest o capture
        raise

    except Exception as e:
        # Destruir instância se foi criada
        if instance_id:
            try:
                await client_with_api_key.instances.destroy(instance_id)
            except Exception:
                pass
            instance_id = None

        if "503" in str(e):
            pytest.skip("Servidor indisponível (503)")
        elif "ofertas" in str(e).lower() or "offers" in str(e).lower():
            pytest.skip("Nenhuma oferta disponível")
        else:
            pytest.skip(f"Erro ao reservar GPU: {e}")
        return

    try:
        yield test_instance
    finally:
        # Cleanup: sempre destruir a instância após o teste
        if instance_id:
            try:
                await client_with_api_key.instances.destroy(instance_id)
            except Exception:
                pass  # Ignora erros no cleanup


def _make_gpu_fixture(gpu_type: str, max_price: float = 1.0):
    """
    Factory para criar fixtures de GPU específicas.

    Permite criar fixtures para diferentes tipos de GPU que podem
    rodar em paralelo.
    """

    @pytest.fixture
    async def gpu_fixture(client_with_api_key, rate_limiter):
        instance_id = None

        try:
            await rate_limiter.wait()

            # Buscar ofertas do tipo específico
            offers = await client_with_api_key.instances.search_offers(
                gpu_name=gpu_type,
                max_price=max_price,
                limit=5,
            )

            if not offers:
                pytest.skip(f"Nenhuma oferta {gpu_type} disponível")

            offer = min(offers, key=lambda o: o.dph_total)

            await rate_limiter.wait()

            import uuid
            test_label = f"test-{gpu_type.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"

            instance = await client_with_api_key.instances.create(
                offer_id=offer.id,
                image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
                disk_size=20,
                label=test_label,
            )

            instance_id = instance.id

            running_instance = await _wait_for_instance_running(
                client_with_api_key,
                instance_id,
                timeout=180,
            )

            if not running_instance:
                pytest.skip(f"Instância {gpu_type} não ficou running")

            yield TestInstance(
                id=running_instance.id,
                gpu_name=running_instance.gpu_name,
                ssh_command=running_instance.ssh_command,
                public_ip=running_instance.public_ipaddr,
                ssh_port=running_instance.ssh_port,
            )

        except Exception as e:
            if "503" in str(e):
                pytest.skip("Servidor indisponível")
            else:
                pytest.skip(f"Erro com {gpu_type}: {e}")

        finally:
            if instance_id:
                try:
                    await client_with_api_key.instances.destroy(instance_id)
                except Exception:
                    pass

    return gpu_fixture


# Criar fixtures específicas para cada tipo de GPU
# Isso permite testes paralelos com GPUs diferentes
reserved_rtx4090 = _make_gpu_fixture("RTX 4090", max_price=0.80)
reserved_rtx3090 = _make_gpu_fixture("RTX 3090", max_price=0.60)
reserved_rtx4080 = _make_gpu_fixture("RTX 4080", max_price=0.70)
reserved_rtx3080 = _make_gpu_fixture("RTX 3080", max_price=0.50)
reserved_rtx4070 = _make_gpu_fixture("RTX 4070 Ti", max_price=0.50)
reserved_a100 = _make_gpu_fixture("A100", max_price=2.00)
reserved_a10 = _make_gpu_fixture("A10", max_price=0.40)
reserved_l40 = _make_gpu_fixture("L40", max_price=1.00)


# =============================================================================
# LLM Fixtures
# =============================================================================

@pytest.fixture
async def llm_client():
    """
    Cliente LLM isolado para testes de inferência.
    """
    from dumont_sdk import DumontLLM, DumontConfig

    config = DumontConfig(
        dumont_server=TEST_API_URL,
        api_key=TEST_API_KEY,
        openrouter_api_key=TEST_OPENROUTER_KEY,
    )

    client = DumontLLM(config=config)

    yield client

    await client.close()


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_gpu_response():
    """Resposta mockada de GPU."""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?"
                }
            }
        ],
        "model": "llama3.2",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }
    }


@pytest.fixture
def mock_openrouter_response():
    """Resposta mockada do OpenRouter."""
    return {
        "id": "gen-123",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello from OpenRouter!"
                }
            }
        ],
        "model": "meta-llama/llama-3.2-3b-instruct",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 15,
            "total_tokens": 25,
        }
    }


@pytest.fixture
def mock_instance_data():
    """Dados mockados de instância."""
    return {
        "id": 12345,
        "gpu_name": "RTX 4090",
        "num_gpus": 1,
        "gpu_ram": 24,
        "cpu_cores": 16,
        "ram_gb": 64,
        "disk_gb": 100,
        "status": "running",
        "actual_status": "running",
        "public_ipaddr": "192.168.1.100",
        "ssh_port": 22,
        "ssh_host": "192.168.1.100",
        "dph_total": 0.50,
        "machine_id": 999,
        "label": "test-instance",
    }


@pytest.fixture
def mock_snapshot_data():
    """Dados mockados de snapshot."""
    return {
        "id": "snap-abc123",
        "instance_id": 12345,
        "created_at": "2024-12-17T10:00:00Z",
        "size_bytes": 7516192768,  # ~7GB
        "status": "completed",
        "label": "test-snapshot",
        "paths": ["/workspace"],
    }


@pytest.fixture
def mock_offer_data():
    """Dados mockados de oferta GPU."""
    return {
        "id": 99999,
        "gpu_name": "RTX 4090",
        "num_gpus": 1,
        "gpu_ram": 24,
        "cpu_cores": 32,
        "ram_gb": 128,
        "disk_gb": 500,
        "dph_total": 0.45,
        "geolocation": "US",
        "reliability": 0.98,
    }


def make_test_instance(
    id: int = 12345,
    status: str = "running",
    actual_status: str = "running",
    gpu_name: str = "RTX 4090",
    public_ipaddr: str = "192.168.1.100",
    ssh_port: int = 22,
    **kwargs
):
    """Helper para criar Instance para testes."""
    from dumont_sdk.instances import Instance

    defaults = {
        "id": id,
        "status": status,
        "actual_status": actual_status,
        "gpu_name": gpu_name,
        "num_gpus": 1,
        "gpu_ram": 24,
        "cpu_cores": 16,
        "cpu_ram": 64,
        "disk_space": 100,
        "dph_total": 0.5,
        "public_ipaddr": public_ipaddr,
        "ssh_port": ssh_port,
    }
    defaults.update(kwargs)
    return Instance(**defaults)


def make_test_offer(
    id: int = 99999,
    gpu_name: str = "RTX 4090",
    dph_total: float = 0.45,
    **kwargs
):
    """Helper para criar GPUOffer para testes."""
    from dumont_sdk.instances import GPUOffer

    defaults = {
        "id": id,
        "gpu_name": gpu_name,
        "num_gpus": 1,
        "gpu_ram": 24,
        "cpu_cores": 32,
        "cpu_ram": 128,
        "disk_space": 500,
        "inet_down": 100,
        "inet_up": 100,
        "dph_total": dph_total,
    }
    defaults.update(kwargs)
    return GPUOffer(**defaults)


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configuração do pytest."""
    config.addinivalue_line(
        "markers", "integration: marca testes de integração (requer API real)"
    )
    config.addinivalue_line(
        "markers", "slow: marca testes lentos"
    )
    config.addinivalue_line(
        "markers", "requires_instance: requer instância rodando"
    )


def pytest_collection_modifyitems(config, items):
    """Modifica itens de teste com base em markers."""
    # Skip integration tests se não houver credenciais
    if not TEST_API_KEY:
        skip_integration = pytest.mark.skip(reason="DUMONT_API_KEY não configurada")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
