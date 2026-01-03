from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
import httpx
import os
from ..dependencies import get_current_user_email, get_user_repository
from ....services.gpu.vast import VastService

router = APIRouter()

# Local Ollama configuration
LOCAL_OLLAMA_URL = os.getenv("LOCAL_OLLAMA_URL", "http://localhost:11434")

async def get_local_ollama_models() -> List[Dict]:
    """Get models from local Ollama instance"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LOCAL_OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("models", []):
                    models.append({
                        "id": f"local-{m['name'].replace(':', '-')}",
                        "name": m["name"],
                        "gpu": "Local CPU/GPU",
                        "status": "online",
                        "ip": "localhost",
                        "ollama_url": LOCAL_OLLAMA_URL,
                        "size_gb": round(m.get("size", 0) / 1e9, 1),
                        "is_local": True
                    })
                return models
    except Exception as e:
        print(f"Local Ollama not available: {e}")
    return []

def get_vast_service_local(
    user_email: str = Depends(get_current_user_email),
    user_repo = Depends(get_user_repository),
) -> VastService:
    user = user_repo.get_user(user_email)
    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Vast.ai API key not configured",
                "message": "Please configure your Vast.ai API key in settings to list chat models",
                "instructions": [
                    "1. Get your API key from https://cloud.vast.ai/account/",
                    "2. Configure it via: POST /api/v1/settings with {\"vast_api_key\": \"your_key\"}",
                    "3. Or set it in your user profile settings"
                ]
            },
        )
    return VastService(api_key=user.vast_api_key)

@router.get("/models")
async def list_models(
    include_local: bool = True
):
    """
    List available Chat Models (LLMs).
    Includes:
    - Local Ollama models (if running)
    - Remote VAST.ai instances with Ollama (if configured)
    """
    models = []

    # 1. Get local Ollama models first (always available for testing)
    if include_local:
        local_models = await get_local_ollama_models()
        models.extend(local_models)

    # 2. Try to get VAST.ai instances (optional, may fail if no API key)
    try:
        vast_api_key = os.getenv("VAST_API_KEY")
        if vast_api_key:
            vast_service = VastService(api_key=vast_api_key)
            instances = vast_service.get_my_instances()

            for inst in instances:
                if inst.get("actual_status") == "running" and inst.get("public_ipaddr"):
                    ports = inst.get("ports", {})
                    ollama_url = None

                    if ports and "11434/tcp" in ports:
                        mappings = ports["11434/tcp"]
                        if mappings:
                            host_port = mappings[0].get("HostPort")
                            if host_port:
                                ollama_url = f"http://{inst['public_ipaddr']}:{host_port}"

                                models.append({
                                    "id": str(inst.get("id")),
                                    "name": f"{inst.get('gpu_name', 'GPU')}",
                                    "gpu": inst.get("gpu_name"),
                                    "status": "online",
                                    "ip": inst.get("public_ipaddr"),
                                    "ollama_url": ollama_url,
                                    "is_local": False
                                })
    except Exception as e:
        print(f"VAST.ai models not available: {e}")

    return {
        "success": True,
        "models": models,
        "count": len(models),
        "has_local": any(m.get("is_local") for m in models),
        "has_remote": any(not m.get("is_local") for m in models)
    }
