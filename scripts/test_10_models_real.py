#!/usr/bin/env python3
"""
TESTE REAL: Deploy de 10 LLMs no Dumont Cloud usando VAST.ai

Este script faz deploy REAL de 10 modelos leves em GPUs da VAST.ai.
IMPORTANTE: USA CRÉDITOS REAIS!
"""
import httpx
import asyncio
import json
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

API_BASE = "http://localhost:8000"
EMAIL = "test@test.com"
PASSWORD = "test123"

DEPLOYMENT_TIMEOUT = 1200  # 20 min por modelo

@dataclass
class ModelConfig:
    name: str
    model_id: str
    model_type: str
    gpu_type: str
    max_price: float

@dataclass
class TestResult:
    model_name: str
    model_id: str
    deployment_id: Optional[str] = None
    success: bool = False
    time_to_deploy: float = 0
    time_to_running: float = 0
    final_status: str = ""
    error: Optional[str] = None
    price_per_hour: float = 0
    instance_id: Optional[str] = None

    def to_dict(self):
        return asdict(self)


MODELS = [
    ModelConfig("Llama 3.2 1B", "meta-llama/Llama-3.2-1B-Instruct", "llm", "RTX 3060", 0.15),
    ModelConfig("Qwen 0.5B", "Qwen/Qwen2.5-0.5B-Instruct", "llm", "RTX 3060", 0.15),
    ModelConfig("Phi-2", "microsoft/phi-2", "llm", "RTX 3060", 0.15),
    ModelConfig("TinyLlama 1.1B", "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "llm", "RTX 3060", 0.15),
    ModelConfig("Whisper Tiny", "openai/whisper-tiny", "speech", "RTX 3060", 0.15),
    ModelConfig("Whisper Base", "openai/whisper-base", "speech", "RTX 3060", 0.15),
    ModelConfig("SD Turbo", "stabilityai/sd-turbo", "image", "RTX 3060", 0.20),
    ModelConfig("SSD-1B", "segmind/SSD-1B", "image", "RTX 3060", 0.20),
    ModelConfig("MiniLM-L6", "sentence-transformers/all-MiniLM-L6-v2", "embeddings", "RTX 3060", 0.10),
    ModelConfig("BGE Small", "BAAI/bge-small-en-v1.5", "embeddings", "RTX 3060", 0.10),
]


async def test_model_deployment(
    client: httpx.AsyncClient,
    token: str,
    config: ModelConfig,
    model_num: int,
    total: int
) -> TestResult:
    """Test deploy de um modelo"""
    result = TestResult(model_name=config.name, model_id=config.model_id)

    print(f"\n{'='*80}")
    print(f"[{model_num}/{total}] {config.name}")
    print(f"Model: {config.model_id}")
    print(f"Type: {config.model_type} | GPU: {config.gpu_type} | Max: ${config.max_price}/h")
    print(f"{'='*80}\n")

    try:
        # 1. Deploy
        start_time = datetime.utcnow()
        print(f"[1/3] Creating deployment...")
        sys.stdout.flush()

        deploy_resp = await client.post(
            f"{API_BASE}/api/v1/models/deploy",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "model_id": config.model_id,
                "model_type": config.model_type,
                "gpu_type": config.gpu_type,
                "max_price": config.max_price,
                "name": config.name,
            },
            timeout=60,
        )
        deploy_resp.raise_for_status()
        deploy_data = deploy_resp.json()

        result.deployment_id = deploy_data["deployment_id"]
        result.time_to_deploy = (datetime.utcnow() - start_time).total_seconds()

        print(f"  Deployment ID: {result.deployment_id}")
        print(f"  Time: {result.time_to_deploy:.1f}s\n")
        sys.stdout.flush()

        # 2. Wait for running
        print(f"[2/3] Waiting for deployment (timeout: {DEPLOYMENT_TIMEOUT}s)...")
        sys.stdout.flush()

        running_start = datetime.utcnow()
        check_count = 0

        while True:
            await asyncio.sleep(10)
            check_count += 1

            status_resp = await client.get(
                f"{API_BASE}/api/v1/models/{result.deployment_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            status_resp.raise_for_status()
            deployment = status_resp.json()

            status = deployment.get("status")
            progress = deployment.get("progress", 0)
            message = deployment.get("status_message", "")

            elapsed = (datetime.utcnow() - running_start).total_seconds()
            print(f"  [{elapsed:>5.0f}s] Check {check_count:2d}: {status:15s} {progress:>5.1f}% - {message[:60]}")
            sys.stdout.flush()

            if status == "running":
                result.time_to_running = elapsed
                result.final_status = "running"
                result.price_per_hour = deployment.get("dph_total", 0)
                result.instance_id = deployment.get("instance_id")
                print(f"\n  STATUS: RUNNING")
                print(f"  Instance: {result.instance_id}")
                print(f"  Price: ${result.price_per_hour:.4f}/h")
                print(f"  Time to running: {elapsed/60:.1f} min")
                break

            elif status in ["error", "failed"]:
                result.final_status = status
                result.error = message
                raise Exception(f"Deployment failed: {message}")

            if elapsed > DEPLOYMENT_TIMEOUT:
                raise TimeoutError(f"Timeout after {DEPLOYMENT_TIMEOUT}s")

        # 3. Cleanup
        print(f"\n[3/3] Deleting deployment...")
        sys.stdout.flush()

        delete_resp = await client.delete(
            f"{API_BASE}/api/v1/models/{result.deployment_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if delete_resp.status_code == 204:
            print(f"  Deleted: OK")
        else:
            print(f"  Deleted: FAILED (status {delete_resp.status_code})")

        result.success = True

        print(f"\n{'='*80}")
        print(f"SUCCESS: {config.name}")
        print(f"Total time: {result.time_to_running/60:.1f} min")
        print(f"{'='*80}\n")

    except Exception as e:
        result.error = str(e)
        result.final_status = "error"

        print(f"\n{'='*80}")
        print(f"ERROR: {config.name}")
        print(f"Error: {result.error}")
        print(f"{'='*80}\n")

        # Cleanup on error
        if result.deployment_id:
            try:
                await client.delete(
                    f"{API_BASE}/api/v1/models/{result.deployment_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                print(f"Cleaned up deployment after error\n")
            except:
                print(f"WARNING: Failed to cleanup {result.deployment_id}\n")

    sys.stdout.flush()
    return result


async def main():
    print(f"""
{'='*80}
REAL DEPLOYMENT TEST: 10 LLMs on Dumont Cloud
{'='*80}

Models to deploy:
""")

    for i, model in enumerate(MODELS, 1):
        print(f"  {i:2d}. {model.name:25s} ({model.model_type:10s}) - {model.model_id}")

    print(f"\n{'='*80}")
    print(f"API: {API_BASE}")
    print(f"User: {EMAIL}")
    print(f"Timeout per model: {DEPLOYMENT_TIMEOUT}s ({DEPLOYMENT_TIMEOUT/60:.0f} min)")
    print(f"{'='*80}\n")

    # Skip confirmation if running non-interactively
    if sys.stdin.isatty():
        input("Press ENTER to start (or Ctrl+C to cancel)...")
    else:
        print("Running in non-interactive mode, starting immediately...")

    results: List[TestResult] = []

    async with httpx.AsyncClient(timeout=30) as client:
        # Login
        print("\nLogging in...")
        login_resp = await client.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD}
        )
        login_resp.raise_for_status()
        token = login_resp.json()["token"]
        print(f"Login OK\n")

        # Test each model
        for i, model in enumerate(MODELS, 1):
            result = await test_model_deployment(client, token, model, i, len(MODELS))
            results.append(result)

            # Delay between deployments
            if i < len(MODELS):
                delay = 5
                print(f"Waiting {delay}s before next deployment...\n")
                await asyncio.sleep(delay)

    # Final report
    print(f"\n\n{'='*80}")
    print("FINAL REPORT")
    print(f"{'='*80}\n")

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"RESULTS:")
    print(f"  Success: {len(successful)}/{len(results)}")
    print(f"  Failed:  {len(failed)}/{len(results)}\n")

    if successful:
        avg_time = sum(r.time_to_running for r in successful) / len(successful)
        total_time = sum(r.time_to_running for r in successful)
        total_cost = sum((r.time_to_running / 3600) * r.price_per_hour for r in successful)

        print(f"METRICS:")
        print(f"  Total time: {total_time/60:.1f} min")
        print(f"  Average time to running: {avg_time/60:.1f} min")
        print(f"  Estimated total cost: ${total_cost:.4f}\n")

    print(f"DEPLOYMENTS:")
    for r in results:
        status = "OK  " if r.success else "FAIL"
        time_str = f"{r.time_to_running/60:>5.1f}min" if r.time_to_running > 0 else "   N/A"
        print(f"  [{status}] {r.model_name:25s} - {time_str} - {r.final_status}")

    if failed:
        print(f"\nERRORS:")
        for r in failed:
            print(f"  - {r.model_name}: {r.error}")

    # Save report
    report_file = "/Users/marcos/CascadeProjects/dumontcloud/MODEL_DEPLOYMENT_REAL_TEST.json"
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_models": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "results": [r.to_dict() for r in results],
    }

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved: {report_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest cancelled.\n")
        sys.exit(1)
