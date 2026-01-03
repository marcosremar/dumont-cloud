from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import os
import httpx
import subprocess
import socket
import time
from ..dependencies import get_current_user_email, get_user_repository
from ....services.gpu.vast import VastService

router = APIRouter()

# NOTE: Local Ollama removed - models must run on remote GPUs only
# This prevents freezing the local machine with heavy inference workloads

# Cache for instance info to avoid repeated API calls
_instance_cache: Dict[str, Dict] = {}

# SSH tunnel management
_ssh_tunnels: Dict[str, Dict] = {}  # instance_id -> {"local_port": int, "process": subprocess.Popen}
_next_local_port = 11500  # Starting port for SSH tunnels


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def _get_or_create_ssh_tunnel(instance_id: str, ssh_host: str, ssh_port: int) -> Optional[int]:
    """Get existing SSH tunnel or create a new one. Returns local port."""
    global _next_local_port

    # Check if we already have a tunnel for this instance
    if instance_id in _ssh_tunnels:
        tunnel_info = _ssh_tunnels[instance_id]
        # Check if tunnel is still alive
        if tunnel_info["process"].poll() is None:
            return tunnel_info["local_port"]
        else:
            # Tunnel died, clean up
            del _ssh_tunnels[instance_id]

    # Create new tunnel
    local_port = _find_free_port()

    try:
        # Start SSH tunnel in background
        # ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no -f -N -L local:localhost:11434 -p ssh_port root@ssh_host
        ssh_key = os.path.expanduser("~/.ssh/id_rsa")

        process = subprocess.Popen(
            [
                "ssh",
                "-i", ssh_key,
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10",
                "-o", "ServerAliveInterval=30",
                "-N",  # No command
                "-L", f"{local_port}:localhost:11434",
                "-p", str(ssh_port),
                f"root@{ssh_host}"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Wait a bit for tunnel to establish
        time.sleep(2)

        # Check if process is still running
        if process.poll() is not None:
            print(f"SSH tunnel failed to start for instance {instance_id}")
            return None

        # Cache the tunnel
        _ssh_tunnels[instance_id] = {
            "local_port": local_port,
            "process": process,
            "ssh_host": ssh_host,
            "ssh_port": ssh_port
        }

        print(f"SSH tunnel created for instance {instance_id}: localhost:{local_port} -> {ssh_host}:{ssh_port}")
        return local_port

    except Exception as e:
        print(f"Error creating SSH tunnel: {e}")
        return None


def _cleanup_tunnel(instance_id: str):
    """Clean up SSH tunnel for an instance."""
    if instance_id in _ssh_tunnels:
        tunnel_info = _ssh_tunnels[instance_id]
        try:
            tunnel_info["process"].terminate()
            tunnel_info["process"].wait(timeout=5)
        except:
            tunnel_info["process"].kill()
        del _ssh_tunnels[instance_id]

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
async def list_models():
    """
    List available Chat Models (LLMs) running on remote GPU instances.
    Discovers models from VAST.ai instances with:
    - Ollama exposed on port 11434
    - vLLM exposed on port 8000

    NOTE: Models must be deployed on remote GPUs, NOT local machine.
    Use the Deploy Wizard to provision a GPU with your preferred runtime.
    """
    models = []

    # Get VAST.ai instances with Ollama or vLLM
    try:
        vast_api_key = os.getenv("VAST_API_KEY")
        if not vast_api_key:
            return {
                "success": True,
                "models": [],
                "count": 0,
                "message": "Configure VAST_API_KEY para listar modelos em GPUs remotas"
            }

        vast_service = VastService(api_key=vast_api_key)
        instances = vast_service.get_my_instances()

        for inst in instances:
            if inst.get("actual_status") == "running" and inst.get("public_ipaddr"):
                ports = inst.get("ports", {})
                public_ip = inst.get("public_ipaddr")
                instance_id = str(inst.get("id"))
                gpu_name = inst.get("gpu_name", "GPU")
                label = inst.get("label", "")

                # Check for Ollama port 11434
                if ports and "11434/tcp" in ports:
                    mappings = ports["11434/tcp"]
                    if mappings:
                        host_port = mappings[0].get("HostPort")
                        if host_port:
                            models.append({
                                "id": instance_id,
                                "name": label or gpu_name,
                                "gpu": gpu_name,
                                "status": "online",
                                "ip": public_ip,
                                "port": host_port,
                                "runtime": "ollama",
                                "api_format": "ollama",
                                "endpoint": f"http://{public_ip}:{host_port}",
                                "ollama_url": f"http://{public_ip}:{host_port}",
                                "price_per_hour": inst.get("dph_total", 0),
                                "instance_id": inst.get("id"),
                                "ssh_host": inst.get("ssh_host"),
                                "ssh_port": inst.get("ssh_port")
                            })

                # Check for vLLM port 8000
                if ports and "8000/tcp" in ports:
                    mappings = ports["8000/tcp"]
                    if mappings:
                        host_port = mappings[0].get("HostPort")
                        if host_port:
                            # Extract model name from label if possible
                            model_name = label.split(":")[-1] if ":" in label else label
                            models.append({
                                "id": f"{instance_id}-vllm",
                                "name": model_name or f"vLLM on {gpu_name}",
                                "gpu": gpu_name,
                                "status": "online",
                                "ip": public_ip,
                                "port": host_port,
                                "runtime": "vllm",
                                "api_format": "openai",
                                "endpoint": f"http://{public_ip}:{host_port}/v1",
                                "vllm_url": f"http://{public_ip}:{host_port}/v1",
                                "price_per_hour": inst.get("dph_total", 0),
                                "instance_id": inst.get("id"),
                                "ssh_host": inst.get("ssh_host"),
                                "ssh_port": inst.get("ssh_port"),
                                "label": label
                            })

    except Exception as e:
        print(f"Error fetching VAST.ai instances: {e}")
        return {
            "success": False,
            "models": [],
            "count": 0,
            "error": str(e)
        }

    # Update cache
    for m in models:
        _instance_cache[m["id"]] = m

    return {
        "success": True,
        "models": models,
        "count": len(models),
        "message": "Use o Deploy Wizard para provisionar GPUs com LLMs" if len(models) == 0 else None
    }


@router.post("/proxy/{instance_id}/chat")
async def proxy_chat(instance_id: str, request: Request):
    """
    Proxy chat requests to remote Ollama instance via SSH tunnel.
    This avoids CORS and firewall issues when frontend calls remote GPU.
    """
    # Get instance info from cache or fetch
    instance = _instance_cache.get(instance_id)

    if not instance:
        # Try to fetch fresh
        await list_models()
        instance = _instance_cache.get(instance_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found"
        )

    # Get SSH connection info
    ssh_host = instance.get("ssh_host")
    ssh_port = instance.get("ssh_port")

    if not ssh_host or not ssh_port:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance does not have SSH connection info"
        )

    # Get or create SSH tunnel
    local_port = _get_or_create_ssh_tunnel(instance_id, ssh_host, int(ssh_port))

    if not local_port:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to establish SSH tunnel to GPU instance"
        )

    # Use localhost URL through SSH tunnel
    ollama_url = f"http://localhost:{local_port}"

    # Get request body
    body = await request.json()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_url}/api/chat",
                json=body,
                headers={"Content-Type": "application/json"}
            )

            return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout connecting to Ollama"
        )
    except Exception as e:
        # If tunnel failed, clean it up and try again next time
        _cleanup_tunnel(instance_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error connecting to Ollama: {str(e)}"
        )


@router.get("/proxy/{instance_id}/tags")
async def proxy_tags(instance_id: str):
    """
    Proxy tags request to check which models are installed on remote Ollama via SSH tunnel.
    """
    instance = _instance_cache.get(instance_id)

    if not instance:
        await list_models()
        instance = _instance_cache.get(instance_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found"
        )

    # Get SSH connection info
    ssh_host = instance.get("ssh_host")
    ssh_port = instance.get("ssh_port")

    if not ssh_host or not ssh_port:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance does not have SSH connection info"
        )

    # Get or create SSH tunnel
    local_port = _get_or_create_ssh_tunnel(instance_id, ssh_host, int(ssh_port))

    if not local_port:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to establish SSH tunnel to GPU instance"
        )

    ollama_url = f"http://localhost:{local_port}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            return response.json()

    except Exception as e:
        _cleanup_tunnel(instance_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error connecting to Ollama: {str(e)}"
        )


# vLLM SSH tunnels (separate from Ollama tunnels, using port 8000)
_vllm_ssh_tunnels: Dict[str, Dict] = {}


def _get_or_create_vllm_ssh_tunnel(instance_id: str, ssh_host: str, ssh_port: int) -> Optional[int]:
    """Get existing SSH tunnel to vLLM (port 8000) or create a new one. Returns local port."""
    # Check if we already have a tunnel for this instance
    if instance_id in _vllm_ssh_tunnels:
        tunnel_info = _vllm_ssh_tunnels[instance_id]
        # Check if tunnel is still alive
        if tunnel_info["process"].poll() is None:
            return tunnel_info["local_port"]
        else:
            # Tunnel died, clean up
            del _vllm_ssh_tunnels[instance_id]

    # Create new tunnel
    local_port = _find_free_port()

    try:
        # Start SSH tunnel in background for vLLM (port 8000)
        ssh_key = os.path.expanduser("~/.ssh/id_rsa")

        process = subprocess.Popen(
            [
                "ssh",
                "-i", ssh_key,
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10",
                "-o", "ServerAliveInterval=30",
                "-N",  # No command
                "-L", f"{local_port}:localhost:8000",  # vLLM port
                "-p", str(ssh_port),
                f"root@{ssh_host}"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Wait a bit for tunnel to establish
        time.sleep(2)

        # Check if process is still running
        if process.poll() is not None:
            print(f"vLLM SSH tunnel failed to start for instance {instance_id}")
            return None

        # Cache the tunnel
        _vllm_ssh_tunnels[instance_id] = {
            "local_port": local_port,
            "process": process,
            "ssh_host": ssh_host,
            "ssh_port": ssh_port
        }

        print(f"vLLM SSH tunnel created for instance {instance_id}: localhost:{local_port} -> {ssh_host}:8000")
        return local_port

    except Exception as e:
        print(f"Error creating vLLM SSH tunnel: {e}")
        return None


def _cleanup_vllm_tunnel(instance_id: str):
    """Clean up vLLM SSH tunnel for an instance."""
    if instance_id in _vllm_ssh_tunnels:
        tunnel_info = _vllm_ssh_tunnels[instance_id]
        try:
            tunnel_info["process"].terminate()
            tunnel_info["process"].wait(timeout=5)
        except:
            tunnel_info["process"].kill()
        del _vllm_ssh_tunnels[instance_id]


@router.get("/proxy/{instance_id}/vllm/models")
async def proxy_vllm_models(instance_id: str):
    """
    Proxy request to list vLLM models (OpenAI format) via SSH tunnel.
    """
    # Remove -vllm suffix if present (from frontend)
    clean_id = instance_id.replace("-vllm", "")
    instance = _instance_cache.get(instance_id) or _instance_cache.get(clean_id)

    if not instance:
        await list_models()
        instance = _instance_cache.get(instance_id) or _instance_cache.get(clean_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found"
        )

    # Get SSH connection info
    ssh_host = instance.get("ssh_host")
    ssh_port = instance.get("ssh_port")

    if not ssh_host or not ssh_port:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance does not have SSH connection info"
        )

    # Get or create SSH tunnel to vLLM
    local_port = _get_or_create_vllm_ssh_tunnel(clean_id, ssh_host, int(ssh_port))

    if not local_port:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to establish SSH tunnel to vLLM instance"
        )

    vllm_url = f"http://localhost:{local_port}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{vllm_url}/v1/models")
            return response.json()

    except Exception as e:
        _cleanup_vllm_tunnel(clean_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error connecting to vLLM: {str(e)}"
        )


@router.post("/proxy/{instance_id}/vllm/chat")
async def proxy_vllm_chat(instance_id: str, request: Request):
    """
    Proxy chat completions to vLLM (OpenAI format) via SSH tunnel.
    """
    # Remove -vllm suffix if present
    clean_id = instance_id.replace("-vllm", "")
    instance = _instance_cache.get(instance_id) or _instance_cache.get(clean_id)

    if not instance:
        await list_models()
        instance = _instance_cache.get(instance_id) or _instance_cache.get(clean_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found"
        )

    # Get SSH connection info
    ssh_host = instance.get("ssh_host")
    ssh_port = instance.get("ssh_port")

    if not ssh_host or not ssh_port:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance does not have SSH connection info"
        )

    # Get or create SSH tunnel to vLLM
    local_port = _get_or_create_vllm_ssh_tunnel(clean_id, ssh_host, int(ssh_port))

    if not local_port:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to establish SSH tunnel to vLLM instance"
        )

    vllm_url = f"http://localhost:{local_port}"

    # Get request body
    body = await request.json()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{vllm_url}/v1/chat/completions",
                json=body,
                headers={"Content-Type": "application/json"}
            )

            return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout connecting to vLLM"
        )
    except Exception as e:
        _cleanup_vllm_tunnel(clean_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error connecting to vLLM: {str(e)}"
        )
