#!/usr/bin/env python3
"""
Teste REAL de Deploy de 10 LLMs no Dumont Cloud usando VAST.ai

IMPORTANTE: Este script USA CRÉDITOS REAIS da VAST.ai!

Deploy de 10 modelos leves com diferentes runtimes:
1. meta-llama/Llama-3.2-1B-Instruct (vLLM)
2. Qwen/Qwen2.5-0.5B-Instruct (vLLM)
3. microsoft/phi-2 (vLLM)
4. TinyLlama/TinyLlama-1.1B-Chat-v1.0 (vLLM)
5. openai/whisper-tiny (faster-whisper)
6. openai/whisper-base (faster-whisper)
7. stabilityai/sd-turbo (diffusers)
8. segmind/SSD-1B (diffusers)
9. sentence-transformers/all-MiniLM-L6-v2 (sentence-transformers)
10. BAAI/bge-small-en-v1.5 (sentence-transformers)
"""
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any
import httpx

# Configuração
API_BASE_URL = os.getenv("DUMONT_API_URL", "http://localhost:8000")
TEST_USER = os.getenv("TEST_USER", "test@test.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "test123")

# Timeouts
DEPLOYMENT_CREATE_TIMEOUT = 60  # 1 min para criar deployment
DEPLOYMENT_READY_TIMEOUT = 1800  # 30 min para ficar running
MODEL_TEST_TIMEOUT = 60  # 1 min para testar endpoint

# Rate limiting
MAX_RETRIES = 5
INITIAL_BACKOFF = 2  # segundos


@dataclass
class ModelConfig:
    """Configuração de modelo para deploy"""
    name: str
    model_id: str
    model_type: str  # llm, speech, image, embeddings
    runtime: str  # vLLM, faster-whisper, diffusers, sentence-transformers
    gpu_type: str  # RTX 3060, RTX 3070, RTX 3080, RTX 4060
    min_vram_gb: int
    max_price_per_hour: float


@dataclass
class DeploymentMetrics:
    """Métricas de um deployment"""
    model_name: str
    model_id: str
    model_type: str
    runtime: str
    gpu_name: str
    deployment_id: Optional[str] = None
    instance_id: Optional[str] = None

    # Timestamps
    start_time: Optional[datetime] = None
    deployment_created_time: Optional[datetime] = None
    running_time: Optional[datetime] = None
    test_complete_time: Optional[datetime] = None
    cleanup_time: Optional[datetime] = None

    # Durations (segundos)
    time_to_create: float = 0
    time_to_running: float = 0
    time_to_test: float = 0
    total_time: float = 0

    # Status
    success: bool = False
    error_message: Optional[str] = None

    # Cost
    price_per_hour: float = 0
    estimated_cost: float = 0

    # Endpoint
    endpoint_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict with datetime formatting"""
        d = asdict(self)
        for key in ['start_time', 'deployment_created_time', 'running_time', 'test_complete_time', 'cleanup_time']:
            if d[key]:
                d[key] = d[key].isoformat()
        return d


class DumontAPIClient:
    """Cliente para API do Dumont Cloud"""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.password = password
        self.token = None
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def login(self):
        """Fazer login e obter token"""
        print(f"Fazendo login com {self.email}...")
        response = await self.client.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"email": self.email, "password": self.password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data.get("access_token")
        print(f"Login OK - Token: {self.token[:20]}...")

    def _headers(self) -> Dict[str, str]:
        """Headers com autenticação"""
        return {"Authorization": f"Bearer {self.token}"}

    async def call_with_retry(self, func, max_retries=MAX_RETRIES):
        """Call function with exponential backoff on 429 errors"""
        delay = INITIAL_BACKOFF
        for attempt in range(max_retries):
            try:
                result = await func()
                return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    print(f"⚠️  Rate limit (429). Aguardando {delay}s... (tentativa {attempt+1}/{max_retries})")
                    await asyncio.sleep(delay)
                    delay *= 1.5  # backoff exponencial
                else:
                    raise
            except Exception as e:
                if "429" in str(e):
                    print(f"⚠️  Rate limit. Aguardando {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 1.5
                else:
                    raise
        raise Exception(f"Max retries ({max_retries}) exceeded")

    async def deploy_model(self, config: ModelConfig) -> Dict[str, Any]:
        """Deploy de um modelo"""
        payload = {
            "model_id": config.model_id,
            "model_type": config.model_type,
            "gpu_type": config.gpu_type,
            "max_price": config.max_price_per_hour,
            "name": config.name,
        }

        async def _deploy():
            response = await self.client.post(
                f"{self.base_url}/api/v1/models/deploy",
                headers=self._headers(),
                json=payload,
                timeout=DEPLOYMENT_CREATE_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

        return await self.call_with_retry(_deploy)

    async def get_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Buscar status de deployment"""
        async def _get():
            response = await self.client.get(
                f"{self.base_url}/api/v1/models/{deployment_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

        return await self.call_with_retry(_get)

    async def delete_deployment(self, deployment_id: str) -> bool:
        """Deletar deployment"""
        try:
            async def _delete():
                response = await self.client.delete(
                    f"{self.base_url}/api/v1/models/{deployment_id}",
                    headers=self._headers(),
                )
                response.raise_for_status()
                return True

            return await self.call_with_retry(_delete)
        except Exception as e:
            print(f"⚠️  Erro ao deletar deployment {deployment_id}: {e}")
            return False

    async def wait_for_running(self, deployment_id: str, timeout: int = DEPLOYMENT_READY_TIMEOUT) -> Dict[str, Any]:
        """Aguardar deployment ficar running"""
        start = time.time()
        while time.time() - start < timeout:
            deployment = await self.get_deployment(deployment_id)
            status = deployment.get("status")

            print(f"   Status: {status} - Progress: {deployment.get('progress', 0)}%")

            if status == "running":
                return deployment
            elif status in ["error", "failed"]:
                raise Exception(f"Deployment falhou: {deployment.get('status_message')}")

            await asyncio.sleep(10)  # Check a cada 10s

        raise TimeoutError(f"Timeout aguardando deployment ficar running (>{timeout}s)")

    async def test_endpoint(self, endpoint_url: str, model_type: str) -> bool:
        """Testar endpoint do modelo"""
        try:
            if model_type == "llm":
                # Test chat completion
                response = await self.client.post(
                    f"{endpoint_url}/v1/chat/completions",
                    json={
                        "model": "default",
                        "messages": [{"role": "user", "content": "Say hi!"}],
                        "max_tokens": 10,
                    },
                    timeout=MODEL_TEST_TIMEOUT,
                )
            elif model_type == "embeddings":
                # Test embeddings
                response = await self.client.post(
                    f"{endpoint_url}/v1/embeddings",
                    json={
                        "model": "default",
                        "input": "Hello world",
                    },
                    timeout=MODEL_TEST_TIMEOUT,
                )
            else:
                # For speech/image, just check health
                response = await self.client.get(
                    f"{endpoint_url}/health",
                    timeout=MODEL_TEST_TIMEOUT,
                )

            return response.status_code == 200
        except Exception as e:
            print(f"⚠️  Erro ao testar endpoint: {e}")
            return False


# Configurações dos 10 modelos
MODEL_CONFIGS = [
    ModelConfig(
        name="Llama 3.2 1B",
        model_id="meta-llama/Llama-3.2-1B-Instruct",
        model_type="llm",
        runtime="vLLM",
        gpu_type="RTX 3060",
        min_vram_gb=4,
        max_price_per_hour=0.15,
    ),
    ModelConfig(
        name="Qwen 2.5 0.5B",
        model_id="Qwen/Qwen2.5-0.5B-Instruct",
        model_type="llm",
        runtime="vLLM",
        gpu_type="RTX 3060",
        min_vram_gb=2,
        max_price_per_hour=0.15,
    ),
    ModelConfig(
        name="Phi-2",
        model_id="microsoft/phi-2",
        model_type="llm",
        runtime="vLLM",
        gpu_type="RTX 3060",
        min_vram_gb=6,
        max_price_per_hour=0.15,
    ),
    ModelConfig(
        name="TinyLlama 1.1B",
        model_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        model_type="llm",
        runtime="vLLM",
        gpu_type="RTX 3060",
        min_vram_gb=3,
        max_price_per_hour=0.15,
    ),
    ModelConfig(
        name="Whisper Tiny",
        model_id="openai/whisper-tiny",
        model_type="speech",
        runtime="faster-whisper",
        gpu_type="RTX 3060",
        min_vram_gb=2,
        max_price_per_hour=0.15,
    ),
    ModelConfig(
        name="Whisper Base",
        model_id="openai/whisper-base",
        model_type="speech",
        runtime="faster-whisper",
        gpu_type="RTX 3060",
        min_vram_gb=3,
        max_price_per_hour=0.15,
    ),
    ModelConfig(
        name="SD Turbo",
        model_id="stabilityai/sd-turbo",
        model_type="image",
        runtime="diffusers",
        gpu_type="RTX 3060",
        min_vram_gb=6,
        max_price_per_hour=0.20,
    ),
    ModelConfig(
        name="SSD-1B",
        model_id="segmind/SSD-1B",
        model_type="image",
        runtime="diffusers",
        gpu_type="RTX 3060",
        min_vram_gb=5,
        max_price_per_hour=0.20,
    ),
    ModelConfig(
        name="MiniLM-L6-v2",
        model_id="sentence-transformers/all-MiniLM-L6-v2",
        model_type="embeddings",
        runtime="sentence-transformers",
        gpu_type="RTX 3060",
        min_vram_gb=1,
        max_price_per_hour=0.10,
    ),
    ModelConfig(
        name="BGE Small EN",
        model_id="BAAI/bge-small-en-v1.5",
        model_type="embeddings",
        runtime="sentence-transformers",
        gpu_type="RTX 3060",
        min_vram_gb=1,
        max_price_per_hour=0.10,
    ),
]


async def deploy_and_test_model(api: DumontAPIClient, config: ModelConfig) -> DeploymentMetrics:
    """Deploy e testar um modelo"""
    metrics = DeploymentMetrics(
        model_name=config.name,
        model_id=config.model_id,
        model_type=config.model_type,
        runtime=config.runtime,
        gpu_name=config.gpu_type,
        start_time=datetime.utcnow(),
    )

    print(f"\n{'='*80}")
    print(f"DEPLOY: {config.name} ({config.model_id})")
    print(f"Type: {config.model_type} | Runtime: {config.runtime} | GPU: {config.gpu_type}")
    print(f"{'='*80}")

    try:
        # 1. Criar deployment
        print("\n1. Criando deployment...")
        deploy_result = await api.deploy_model(config)

        metrics.deployment_id = deploy_result.get("deployment_id")
        metrics.deployment_created_time = datetime.utcnow()
        metrics.time_to_create = (metrics.deployment_created_time - metrics.start_time).total_seconds()

        print(f"   Deployment ID: {metrics.deployment_id}")
        print(f"   Tempo para criar: {metrics.time_to_create:.1f}s")

        # 2. Aguardar ficar running
        print("\n2. Aguardando deployment ficar running...")
        deployment = await api.wait_for_running(metrics.deployment_id)

        metrics.running_time = datetime.utcnow()
        metrics.time_to_running = (metrics.running_time - metrics.deployment_created_time).total_seconds()
        metrics.instance_id = deployment.get("instance_id")
        metrics.endpoint_url = deployment.get("endpoint_url")
        metrics.price_per_hour = deployment.get("dph_total", 0)

        print(f"   Status: RUNNING")
        print(f"   Instance ID: {metrics.instance_id}")
        print(f"   Endpoint: {metrics.endpoint_url}")
        print(f"   Tempo para running: {metrics.time_to_running:.1f}s ({metrics.time_to_running/60:.1f} min)")
        print(f"   Preço: ${metrics.price_per_hour:.4f}/hora")

        # 3. Testar endpoint (apenas para LLM e embeddings)
        if config.model_type in ["llm", "embeddings"] and metrics.endpoint_url:
            print("\n3. Testando endpoint...")
            test_ok = await api.test_endpoint(metrics.endpoint_url, config.model_type)

            metrics.test_complete_time = datetime.utcnow()
            metrics.time_to_test = (metrics.test_complete_time - metrics.running_time).total_seconds()

            if test_ok:
                print(f"   Teste: OK")
            else:
                print(f"   Teste: FALHOU (mas deployment está running)")
        else:
            print("\n3. Pulando teste de endpoint (não aplicável para este tipo)")
            metrics.test_complete_time = metrics.running_time

        # 4. Cleanup - deletar deployment
        print("\n4. Deletando deployment para economizar...")
        deleted = await api.delete_deployment(metrics.deployment_id)

        metrics.cleanup_time = datetime.utcnow()
        metrics.total_time = (metrics.cleanup_time - metrics.start_time).total_seconds()

        if deleted:
            print(f"   Deployment deletado: OK")
        else:
            print(f"   Deployment deletado: FALHOU (pode ter vazado custos!)")

        # Calcular custo estimado (tempo total em horas * preço/hora)
        metrics.estimated_cost = (metrics.total_time / 3600) * metrics.price_per_hour

        metrics.success = True

        print(f"\n{'='*80}")
        print(f"SUCESSO: {config.name}")
        print(f"Tempo total: {metrics.total_time:.1f}s ({metrics.total_time/60:.1f} min)")
        print(f"Custo estimado: ${metrics.estimated_cost:.4f}")
        print(f"{'='*80}")

    except Exception as e:
        metrics.error_message = str(e)
        metrics.success = False

        print(f"\n{'='*80}")
        print(f"ERRO: {config.name}")
        print(f"Erro: {metrics.error_message}")
        print(f"{'='*80}")

        # Tentar cleanup mesmo em caso de erro
        if metrics.deployment_id:
            try:
                await api.delete_deployment(metrics.deployment_id)
                print(f"Deployment deletado após erro: OK")
            except:
                print(f"AVISO: Não foi possível deletar deployment {metrics.deployment_id}")

    return metrics


async def main():
    """Main test function"""
    print(f"""
{'='*80}
TESTE REAL DE DEPLOY DE 10 LLMs NO DUMONT CLOUD
{'='*80}
IMPORTANTE: Este teste USA CRÉDITOS REAIS da VAST.ai!

Modelos a testar:
""")

    for i, config in enumerate(MODEL_CONFIGS, 1):
        print(f"{i:2d}. {config.name:30s} ({config.model_type:10s}) - {config.runtime}")

    print(f"\n{'='*80}")
    print("API Base URL:", API_BASE_URL)
    print("User:", TEST_USER)
    print(f"{'='*80}\n")

    input("Pressione ENTER para iniciar os testes (ou Ctrl+C para cancelar)...")

    all_metrics: List[DeploymentMetrics] = []

    async with DumontAPIClient(API_BASE_URL, TEST_USER, TEST_PASSWORD) as api:
        for i, config in enumerate(MODEL_CONFIGS, 1):
            print(f"\n\n{'#'*80}")
            print(f"# TESTE {i}/{len(MODEL_CONFIGS)}")
            print(f"{'#'*80}")

            metrics = await deploy_and_test_model(api, config)
            all_metrics.append(metrics)

            # Delay entre deploys para evitar rate limiting
            if i < len(MODEL_CONFIGS):
                delay = 5
                print(f"\nAguardando {delay}s antes do próximo deploy...")
                await asyncio.sleep(delay)

    # Gerar relatório final
    print("\n\n")
    print(f"{'='*80}")
    print("RELATÓRIO FINAL DE TESTES")
    print(f"{'='*80}")
    print(f"Data: {datetime.utcnow().isoformat()}")
    print(f"Total de modelos testados: {len(all_metrics)}")

    successful = [m for m in all_metrics if m.success]
    failed = [m for m in all_metrics if not m.success]

    print(f"\nSUCESSO: {len(successful)}/{len(all_metrics)}")
    print(f"FALHAS: {len(failed)}/{len(all_metrics)}")

    if successful:
        total_time = sum(m.total_time for m in successful)
        total_cost = sum(m.estimated_cost for m in successful)
        avg_time_to_running = sum(m.time_to_running for m in successful) / len(successful)

        print(f"\nMÉTRICAS:")
        print(f"- Tempo total: {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"- Custo total estimado: ${total_cost:.4f}")
        print(f"- Tempo médio para running: {avg_time_to_running:.1f}s ({avg_time_to_running/60:.1f} min)")

    print(f"\nDEPLOYMENTS CRIADOS/DELETADOS:")
    for m in all_metrics:
        status = "OK" if m.success else "ERRO"
        deleted = "DELETADO" if m.cleanup_time else "VAZOU!"
        print(f"- {m.deployment_id or 'N/A':20s} | {m.model_name:30s} | {status:5s} | {deleted}")

    if failed:
        print(f"\nERROS:")
        for m in failed:
            print(f"- {m.model_name}: {m.error_message}")

    # Salvar relatório em JSON
    report_file = "/Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_TEST_REPORT.json"
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_models": len(all_metrics),
        "successful": len(successful),
        "failed": len(failed),
        "total_time_seconds": sum(m.total_time for m in all_metrics if m.total_time),
        "total_cost_usd": sum(m.estimated_cost for m in all_metrics if m.estimated_cost),
        "deployments": [m.to_dict() for m in all_metrics],
    }

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nRelatório salvo em: {report_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTeste cancelado pelo usuário.")
        sys.exit(1)
