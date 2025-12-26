from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from ..dependencies import get_current_user_email, get_user_repository
from ....services.gpu.vast import VastService

router = APIRouter()

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
def list_models(
    vast_service: VastService = Depends(get_vast_service_local)
):
    """
    List available Chat Models (LLMs) running on instances.
    Detects instances with exposed Ollama port (11434).
    """
    try:
        # Get all instances
        instances = vast_service.get_my_instances()

        models = []
        for inst in instances:
            # Filter for running instances
            if inst.get("actual_status") == "running" and inst.get("public_ipaddr"):

                # Check ports
                ports = inst.get("ports", {})
                ollama_url = None
                is_ollama = False

                # Check for 11434 mapping
                if ports and "11434/tcp" in ports:
                    mappings = ports["11434/tcp"]
                    if mappings:
                        host_port = mappings[0].get("HostPort")
                        if host_port:
                            ollama_url = f"http://{inst['public_ipaddr']}:{host_port}"
                            is_ollama = True

                if is_ollama:
                     models.append({
                        "id": inst.get("id"),
                        "name": f"{inst.get('gpu_name', 'GPU')} (Instance {inst.get('id')})",
                        "gpu": inst.get("gpu_name"),
                        "status": "online",
                        "ip": inst.get("public_ipaddr"),
                        "ollama_url": ollama_url,
                        "raw_ports": ports
                    })

        return {
            "success": True,
            "models": models,
            "count": len(models)
        }

    except HTTPException:
        # Re-raise HTTP exceptions (like auth errors)
        raise
    except Exception as e:
        import traceback
        error_details = {
            "success": False,
            "error": "Failed to list chat models",
            "message": str(e),
            "details": "Could not fetch instances from Vast.ai. Please check your API key and network connection.",
            "models": []
        }
        print(f"Error listing chat models: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_details
        )
