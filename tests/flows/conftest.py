"""
Fixtures compartilhadas para testes de fluxo.
Testes REAIS contra a API - sem mocks.
"""
import os
import pytest
import httpx
import time
import functools
from typing import Generator, Optional, Callable, Any
from dataclasses import dataclass


# Configuração
BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@test.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test1234")
VAST_API_KEY = os.environ.get("VAST_API_KEY", "")

# Timeouts
TIMEOUT_SHORT = 30
TIMEOUT_MEDIUM = 120
TIMEOUT_LONG = 600

# Retry config - mais agressivo para rate limits
MAX_RETRIES = 5
RETRY_DELAY = 5  # segundos (começa com 5, depois 10, 20, 40, 80)
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]


def retry_on_rate_limit(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """Decorator para retry em caso de rate limit ou erro temporário"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in RETRY_STATUS_CODES:
                        last_exception = e
                        if attempt < max_retries:
                            wait_time = delay * (2 ** attempt)  # Exponential backoff
                            print(f"  ⏳ Rate limit/erro {e.response.status_code}, retry {attempt + 1}/{max_retries} em {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                    raise
                except Exception as e:
                    raise
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


class RetryClient:
    """Cliente HTTP com retry automático para rate limits"""

    def __init__(self, client: httpx.Client, max_retries: int = MAX_RETRIES):
        self._client = client
        self._max_retries = max_retries

    def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Faz request com retry automático"""
        last_response = None

        for attempt in range(self._max_retries + 1):
            response = getattr(self._client, method)(url, **kwargs)
            last_response = response

            if response.status_code not in RETRY_STATUS_CODES:
                return response

            if attempt < self._max_retries:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"  ⏳ {response.status_code} em {url}, retry {attempt + 1}/{self._max_retries} em {wait_time}s...")
                time.sleep(wait_time)

        return last_response

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self._request_with_retry("get", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self._request_with_retry("post", url, **kwargs)

    def put(self, url: str, **kwargs) -> httpx.Response:
        return self._request_with_retry("put", url, **kwargs)

    def delete(self, url: str, **kwargs) -> httpx.Response:
        return self._request_with_retry("delete", url, **kwargs)

    def patch(self, url: str, **kwargs) -> httpx.Response:
        return self._request_with_retry("patch", url, **kwargs)


@dataclass
class TestContext:
    """Contexto compartilhado entre testes"""
    base_url: str
    token: Optional[str] = None
    user_email: Optional[str] = None
    created_instances: list = None
    created_jobs: list = None
    created_snapshots: list = None

    def __post_init__(self):
        self.created_instances = []
        self.created_jobs = []
        self.created_snapshots = []


@pytest.fixture(scope="session")
def base_url() -> str:
    """URL base da API"""
    return BASE_URL


@pytest.fixture(scope="session", autouse=True)
def reset_test_user_api_key():
    """
    Reseta a API key do usuário de teste para null no início da sessão.
    Isso garante que o sistema use a API key do .env (system key).
    """
    import json
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
    config_path = os.path.abspath(config_path)

    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        # Resetar API key do usuário de teste
        if "users" in config and TEST_EMAIL in config["users"]:
            if config["users"][TEST_EMAIL].get("vast_api_key") != None:
                config["users"][TEST_EMAIL]["vast_api_key"] = None
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)
                print(f"  🔑 API key do {TEST_EMAIL} resetada para null")
    except Exception as e:
        print(f"  ⚠️ Não foi possível resetar API key: {e}")

    yield


@pytest.fixture(scope="session")
def http_client() -> Generator[RetryClient, None, None]:
    """Cliente HTTP para testes com retry automático"""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM) as client:
        yield RetryClient(client, max_retries=MAX_RETRIES)


@pytest.fixture(scope="session")
def auth_token() -> str:
    """Token de autenticação válido"""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_SHORT) as client:
        # Tentar login
        response = client.post(
            "/api/v1/auth/login",
            json={"username": TEST_EMAIL, "password": TEST_PASSWORD}
        )

        if response.status_code == 200:
            return response.json().get("token")

        # Se login falhar, tentar registrar
        response = client.post(
            "/api/v1/auth/register",
            json={"username": TEST_EMAIL, "password": TEST_PASSWORD}
        )

        if response.status_code in [200, 201]:
            return response.json().get("token")

        pytest.fail(f"Não foi possível autenticar: {response.text}")


@pytest.fixture(scope="session")
def auth_headers(auth_token: str) -> dict:
    """Headers com autenticação"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="session")
def authed_client(auth_token: str) -> Generator[RetryClient, None, None]:
    """Cliente HTTP já autenticado com retry automático"""
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, headers=headers) as client:
        yield RetryClient(client, max_retries=MAX_RETRIES)


@pytest.fixture(scope="module")
def test_context(base_url: str, auth_token: str) -> Generator[TestContext, None, None]:
    """Contexto de teste com cleanup automático"""
    ctx = TestContext(base_url=base_url, token=auth_token)

    yield ctx

    # Cleanup: destruir recursos criados
    headers = {"Authorization": f"Bearer {auth_token}"}

    with httpx.Client(base_url=base_url, timeout=TIMEOUT_SHORT, headers=headers) as client:
        # Destruir instâncias
        for instance_id in ctx.created_instances:
            try:
                client.delete(f"/api/instances/{instance_id}")
            except Exception:
                pass

        # Cancelar jobs
        for job_id in ctx.created_jobs:
            try:
                client.post(f"/api/jobs/{job_id}/cancel")
            except Exception:
                pass


# === Helpers ===

def wait_for_status(
    client: httpx.Client,
    url: str,
    target_status: str,
    timeout: int = 300,
    interval: int = 5,
    status_field: str = "status"
) -> dict:
    """Aguarda até que um recurso atinja o status desejado"""
    start = time.time()

    while time.time() - start < timeout:
        response = client.get(url)
        if response.status_code == 200:
            data = response.json()
            current_status = data.get(status_field)

            if current_status == target_status:
                return data

            if current_status in ["failed", "error", "terminated"]:
                pytest.fail(f"Recurso entrou em estado de erro: {current_status}")

        time.sleep(interval)

    pytest.fail(f"Timeout aguardando status '{target_status}' em {url}")


def wait_for_ssh(host: str, port: int, timeout: int = 180) -> bool:
    """Aguarda SSH ficar disponível"""
    import socket

    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(5)

    return False


# === Markers ===

def pytest_configure(config):
    """Registra markers customizados"""
    config.addinivalue_line("markers", "flow1: Deploy de modelos")
    config.addinivalue_line("markers", "flow2: Job GPU")
    config.addinivalue_line("markers", "flow3: Desenvolvimento interativo")
    config.addinivalue_line("markers", "flow4: API Serverless")
    config.addinivalue_line("markers", "flow5: Alta disponibilidade")
    config.addinivalue_line("markers", "flow6: Warm Pool")
    config.addinivalue_line("markers", "flow7: Monitoramento")
    config.addinivalue_line("markers", "flow8: Auth e Settings")
    config.addinivalue_line("markers", "real_gpu: Requer GPU real (custa $$$)")
    config.addinivalue_line("markers", "slow: Teste lento (>1 min)")
    config.addinivalue_line("markers", "destructive: Pode destruir recursos")
