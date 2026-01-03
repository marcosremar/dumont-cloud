#!/usr/bin/env python3
"""
Teste RÁPIDO de Deploy de 3 LLMs leves no Dumont Cloud

Versão reduzida para validar o fluxo antes de rodar os 10 modelos completos.
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

# Timeouts REDUZIDOS para teste rápido
DEPLOYMENT_CREATE_TIMEOUT = 60  # 1 min
DEPLOYMENT_READY_TIMEOUT = 600  # 10 min (reduzido de 30)
MODEL_TEST_TIMEOUT = 30

# Rate limiting
MAX_RETRIES = 5
INITIAL_BACKOFF = 2


@dataclass
class ModelConfig:
    """Configuração de modelo para deploy"""
    name: str
    model_id: str
    model_type: str
    gpu_type: str
    max_price_per_hour: float


@dataclass
class DeploymentMetrics:
    """Métricas de um deployment"""
    model_name: str
    model_id: str
    model_type: str
    gpu_name: str
    deployment_id: Optional[str] = None
    instance_id: Optional[str] = None

    # Timestamps
    start_time: Optional[datetime] = None
    deployment_created_time: Optional[datetime] = None
    running_time: Optional[datetime] = None
    cleanup_time: Optional[datetime] = None

    # Durations (segundos)
    time_to_create: float = 0
    time_to_running: float = 0
    total_time: float = 0

    # Status
    success: bool = False
    error_message: Optional[str] = None

    # Cost
    price_per_hour: float = 0
    estimated_cost: float = 0

    # Endpoint
    endpoint_url: Optional[str] = None
    status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict with datetime formatting"""
        d = asdict(self)
        for key in ['start_time', 'deployment_created_time', 'running_time', 'cleanup_time']:
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
        print(f"\nFazendo login com {self.email}...")
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": self.email, "password": self.password}
            )
            response.raise_for_status()
            data = response.json()
            # API retorna "token" não "access_token"
            self.token = data.get("token") or data.get("access_token")
            if not self.token:
                raise Exception(f"Token não encontrado na resposta: {data}")
            print(f"Login OK - Token obtido")
        except Exception as e:
            print(f"ERRO no login: {e}")
            raise

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
                    print(f"   Rate limit (429). Aguardando {delay:.1f}s...")
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
            print(f"   Erro ao deletar: {e}")
            return False

    async def wait_for_running(self, deployment_id: str, timeout: int = DEPLOYMENT_READY_TIMEOUT) -> Dict[str, Any]:
        """Aguardar deployment ficar running"""
        start = time.time()
        check_count = 0
        while time.time() - start < timeout:
            deployment = await self.get_deployment(deployment_id)
            status = deployment.get("status")
            progress = deployment.get("progress", 0)
            check_count += 1

            elapsed = time.time() - start
            progress_str = f"{int(progress):3d}%" if progress and isinstance(progress, (int, float)) else "  ?%"
            print(f"   [{elapsed:>5.0f}s] Check {check_count:2d}: {status:12s} - {progress_str} - {deployment.get('status_message', '')[:50]}")

            if status == "running":
                return deployment
            elif status in ["error", "failed"]:
                raise Exception(f"Deployment falhou: {deployment.get('status_message')}")

            await asyncio.sleep(10)  # Check a cada 10s

        raise TimeoutError(f"Timeout aguardando deployment (>{timeout}s)")


# 3 modelos mais leves para teste rápido
MODEL_CONFIGS = [
    ModelConfig(
        name="Qwen 0.5B",
        model_id="Qwen/Qwen2.5-0.5B-Instruct",
        model_type="llm",
        gpu_type="RTX 3060",
        max_price_per_hour=0.15,
    ),
    ModelConfig(
        name="TinyLlama 1.1B",
        model_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        model_type="llm",
        gpu_type="RTX 3060",
        max_price_per_hour=0.15,
    ),
    ModelConfig(
        name="MiniLM Embeddings",
        model_id="sentence-transformers/all-MiniLM-L6-v2",
        model_type="embeddings",
        gpu_type="RTX 3060",
        max_price_per_hour=0.10,
    ),
]


async def deploy_and_test_model(api: DumontAPIClient, config: ModelConfig) -> DeploymentMetrics:
    """Deploy e testar um modelo"""
    metrics = DeploymentMetrics(
        model_name=config.name,
        model_id=config.model_id,
        model_type=config.model_type,
        gpu_name=config.gpu_type,
        start_time=datetime.utcnow(),
    )

    print(f"\n{'='*80}")
    print(f"DEPLOY: {config.name}")
    print(f"Model: {config.model_id}")
    print(f"Type: {config.model_type} | GPU: {config.gpu_type} | Max: ${config.max_price_per_hour}/h")
    print(f"{'='*80}")

    try:
        # 1. Criar deployment
        print("\n[1/3] Criando deployment...")
        deploy_result = await api.deploy_model(config)

        metrics.deployment_id = deploy_result.get("deployment_id")
        metrics.deployment_created_time = datetime.utcnow()
        metrics.time_to_create = (metrics.deployment_created_time - metrics.start_time).total_seconds()

        print(f"   Deployment ID: {metrics.deployment_id}")
        print(f"   Tempo: {metrics.time_to_create:.1f}s")

        # 2. Aguardar ficar running
        print(f"\n[2/3] Aguardando deployment ficar running (timeout: {DEPLOYMENT_READY_TIMEOUT}s)...")
        deployment = await api.wait_for_running(metrics.deployment_id)

        metrics.running_time = datetime.utcnow()
        metrics.time_to_running = (metrics.running_time - metrics.deployment_created_time).total_seconds()
        metrics.instance_id = deployment.get("instance_id")
        metrics.endpoint_url = deployment.get("endpoint_url")
        metrics.price_per_hour = deployment.get("dph_total", 0)
        metrics.status = deployment.get("status")

        print(f"\n   STATUS: RUNNING")
        print(f"   Instance: {metrics.instance_id}")
        print(f"   Endpoint: {metrics.endpoint_url}")
        print(f"   Tempo para running: {metrics.time_to_running:.1f}s ({metrics.time_to_running/60:.1f} min)")
        print(f"   Preço: ${metrics.price_per_hour:.4f}/h")

        # 3. Cleanup - deletar deployment
        print(f"\n[3/3] Deletando deployment...")
        deleted = await api.delete_deployment(metrics.deployment_id)

        metrics.cleanup_time = datetime.utcnow()
        metrics.total_time = (metrics.cleanup_time - metrics.start_time).total_seconds()
        metrics.estimated_cost = (metrics.total_time / 3600) * metrics.price_per_hour

        print(f"   Deletado: {'OK' if deleted else 'FALHOU'}")

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
                print(f"\nTentando deletar deployment após erro...")
                await api.delete_deployment(metrics.deployment_id)
                print(f"   Deletado: OK")
            except Exception as cleanup_error:
                print(f"   AVISO: Não foi possível deletar: {cleanup_error}")

    return metrics


async def main():
    """Main test function"""
    print(f"""
{'='*80}
TESTE RÁPIDO: Deploy de 3 LLMs Leves
{'='*80}

Modelos:
  1. Qwen 2.5 0.5B (LLM)
  2. TinyLlama 1.1B (LLM)
  3. MiniLM-L6-v2 (Embeddings)

API: {API_BASE_URL}
User: {TEST_USER}
{'='*80}
""")

    all_metrics: List[DeploymentMetrics] = []

    async with DumontAPIClient(API_BASE_URL, TEST_USER, TEST_PASSWORD) as api:
        for i, config in enumerate(MODEL_CONFIGS, 1):
            print(f"\n{'#'*80}")
            print(f"# MODELO {i}/{len(MODEL_CONFIGS)}")
            print(f"{'#'*80}")

            metrics = await deploy_and_test_model(api, config)
            all_metrics.append(metrics)

            # Delay entre deploys
            if i < len(MODEL_CONFIGS):
                delay = 5
                print(f"\nAguardando {delay}s antes do próximo deploy...")
                await asyncio.sleep(delay)

    # Relatório final
    print("\n\n")
    print(f"{'='*80}")
    print("RELATÓRIO FINAL")
    print(f"{'='*80}")

    successful = [m for m in all_metrics if m.success]
    failed = [m for m in all_metrics if not m.success]

    print(f"\nRESULTADOS:")
    print(f"  Sucesso: {len(successful)}/{len(all_metrics)}")
    print(f"  Falhas:  {len(failed)}/{len(all_metrics)}")

    if successful:
        total_time = sum(m.total_time for m in successful)
        total_cost = sum(m.estimated_cost for m in successful)
        avg_time = sum(m.time_to_running for m in successful) / len(successful)

        print(f"\nMÉTRICAS:")
        print(f"  Tempo total: {total_time/60:.1f} min")
        print(f"  Custo total: ${total_cost:.4f}")
        print(f"  Tempo médio para running: {avg_time/60:.1f} min")

    print(f"\nDETALHES:")
    for m in all_metrics:
        status = "OK  " if m.success else "ERRO"
        time_str = f"{m.time_to_running/60:.1f}min" if m.time_to_running > 0 else "N/A"
        cost_str = f"${m.estimated_cost:.4f}" if m.estimated_cost > 0 else "$0"
        print(f"  [{status}] {m.model_name:20s} - {time_str:8s} - {cost_str:10s}")

    if failed:
        print(f"\nERROS:")
        for m in failed:
            print(f"  - {m.model_name}: {m.error_message}")

    # Salvar relatório
    report_file = "/Users/marcos/CascadeProjects/dumontcloud/QUICK_MODEL_TEST_REPORT.json"
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_models": len(all_metrics),
        "successful": len(successful),
        "failed": len(failed),
        "deployments": [m.to_dict() for m in all_metrics],
    }

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nRelatório salvo: {report_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTeste cancelado.")
        sys.exit(1)
