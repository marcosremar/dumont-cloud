"""
TensorDock GPU Provider Implementation
Implements IGpuProvider interface for TensorDock serverless GPU.

TensorDock offers serverless GPU with auto-pause functionality:
- Fast mode: <1s cold start
- Economic mode: ~7s cold start
- Spot mode: ~30s cold start
"""
import logging
import os
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

TENSORDOCK_API_URL = "https://marketplace.tensordock.com/api/v0"


class ServerlessMode(str, Enum):
    """TensorDock serverless modes"""
    FAST = "fast"           # <1s cold start, higher cost
    ECONOMIC = "economic"   # ~7s cold start, medium cost
    SPOT = "spot"           # ~30s cold start, lowest cost


@dataclass
class TensorDockInstance:
    """Represents a TensorDock serverless instance"""
    id: str
    name: str
    status: str
    gpu_name: str
    gpu_count: int
    vcpus: int
    ram_gb: float
    storage_gb: float
    ip_address: Optional[str]
    ssh_port: Optional[int]
    hourly_cost: float
    mode: ServerlessMode
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TensorDockOffer:
    """Represents a TensorDock GPU offer"""
    id: str
    gpu_name: str
    gpu_count: int
    vcpus: int
    ram_gb: float
    storage_gb: float
    location: str
    hourly_cost: float
    mode: ServerlessMode
    available: bool


class TensorDockProvider:
    """
    TensorDock serverless GPU provider.

    Supports:
    - List/create/destroy serverless instances
    - Pause/resume (auto-pause on idle)
    - Multiple serverless modes (fast/economic/spot)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_token: Optional[str] = None,
        api_url: str = TENSORDOCK_API_URL,
        timeout: int = 30
    ):
        """
        Initialize TensorDock provider.

        Args:
            api_key: TensorDock Authorization ID (can be from env TENSORDOCK_API_KEY)
            api_token: TensorDock API Token (can be from env TENSORDOCK_API_TOKEN)
            api_url: TensorDock API URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.environ.get("TENSORDOCK_API_KEY")
        self.api_token = api_token or os.environ.get("TENSORDOCK_API_TOKEN")
        self.api_url = api_url
        self.timeout = timeout

        if not self.api_key or not self.api_token:
            logger.warning("TensorDock credentials not configured")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to TensorDock API."""
        url = f"{self.api_url}/{endpoint}"

        # TensorDock uses form data with api_key and api_token
        auth_data = {
            "api_key": self.api_key,
            "api_token": self.api_token,
        }

        if data:
            auth_data.update(data)

        try:
            if method.upper() == "GET":
                response = requests.get(
                    url,
                    params={**auth_data, **(params or {})},
                    timeout=self.timeout
                )
            else:
                response = requests.post(
                    url,
                    data=auth_data,
                    timeout=self.timeout
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"TensorDock API error: {e}")
            raise

    def list_instances(self) -> List[TensorDockInstance]:
        """List all TensorDock instances."""
        try:
            response = self._make_request("GET", "list")
            instances = []

            for vm_id, vm_data in response.get("virtualmachines", {}).items():
                instances.append(TensorDockInstance(
                    id=vm_id,
                    name=vm_data.get("name", f"tensordock-{vm_id}"),
                    status=vm_data.get("status", "unknown"),
                    gpu_name=vm_data.get("gpu_model", "unknown"),
                    gpu_count=vm_data.get("gpu_count", 1),
                    vcpus=vm_data.get("vcpus", 0),
                    ram_gb=vm_data.get("ram", 0),
                    storage_gb=vm_data.get("storage", 0),
                    ip_address=vm_data.get("ip"),
                    ssh_port=vm_data.get("port_forwards", {}).get("22"),
                    hourly_cost=vm_data.get("cost_per_hour", 0),
                    mode=ServerlessMode.ECONOMIC,  # Default mode
                    metadata=vm_data
                ))

            return instances

        except Exception as e:
            logger.error(f"Failed to list TensorDock instances: {e}")
            return []

    def get_instance(self, instance_id: str) -> Optional[TensorDockInstance]:
        """Get a specific instance by ID."""
        instances = self.list_instances()
        for inst in instances:
            if inst.id == instance_id:
                return inst
        return None

    def search_offers(
        self,
        gpu_name: Optional[str] = None,
        min_gpu_ram: float = 0,
        max_price: float = 10.0,
        mode: ServerlessMode = ServerlessMode.ECONOMIC,
        limit: int = 50
    ) -> List[TensorDockOffer]:
        """
        Search for available GPU offers.

        Args:
            gpu_name: Filter by GPU name (e.g., "RTX 4090")
            min_gpu_ram: Minimum GPU RAM in GB
            max_price: Maximum hourly price in USD
            mode: Serverless mode (fast/economic/spot)
            limit: Maximum number of results

        Returns:
            List of available GPU offers
        """
        try:
            # TensorDock hostnodes endpoint
            response = self._make_request("GET", "hostnodes")
            offers = []

            for node_id, node_data in response.get("hostnodes", {}).items():
                specs = node_data.get("specs", {})
                gpu_info = specs.get("gpu", {})

                # Filter by GPU name if specified
                node_gpu_name = gpu_info.get("name", "")
                if gpu_name and gpu_name.lower() not in node_gpu_name.lower():
                    continue

                # Calculate hourly cost based on mode
                base_cost = float(node_data.get("price_per_hour", 0))
                if mode == ServerlessMode.FAST:
                    hourly_cost = base_cost * 1.5  # Premium for fast mode
                elif mode == ServerlessMode.SPOT:
                    hourly_cost = base_cost * 0.5  # Discount for spot
                else:
                    hourly_cost = base_cost

                if hourly_cost > max_price:
                    continue

                offers.append(TensorDockOffer(
                    id=node_id,
                    gpu_name=node_gpu_name,
                    gpu_count=gpu_info.get("count", 1),
                    vcpus=specs.get("cpu", {}).get("count", 0),
                    ram_gb=specs.get("ram", {}).get("gb", 0),
                    storage_gb=specs.get("storage", {}).get("gb", 0),
                    location=node_data.get("location", {}).get("city", "Unknown"),
                    hourly_cost=hourly_cost,
                    mode=mode,
                    available=node_data.get("available", False)
                ))

            # Sort by price and limit
            offers.sort(key=lambda x: x.hourly_cost)
            return offers[:limit]

        except Exception as e:
            logger.error(f"Failed to search TensorDock offers: {e}")
            return []

    def create_instance(
        self,
        hostnode_id: str,
        gpu_count: int = 1,
        vcpus: int = 4,
        ram_gb: int = 16,
        storage_gb: int = 50,
        name: Optional[str] = None,
        image: str = "pytorch/pytorch:latest",
        mode: ServerlessMode = ServerlessMode.ECONOMIC,
        ssh_key: Optional[str] = None
    ) -> Optional[TensorDockInstance]:
        """
        Create a new serverless GPU instance.

        Args:
            hostnode_id: ID of the host node to use
            gpu_count: Number of GPUs
            vcpus: Number of virtual CPUs
            ram_gb: RAM in GB
            storage_gb: Storage in GB
            name: Instance name
            image: Docker image to use
            mode: Serverless mode
            ssh_key: SSH public key for access

        Returns:
            Created instance or None if failed
        """
        try:
            data = {
                "hostnode": hostnode_id,
                "gpu_count": gpu_count,
                "vcpus": vcpus,
                "ram": ram_gb,
                "storage": storage_gb,
                "name": name or f"dumont-serverless-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "operating_system": image,
            }

            if ssh_key:
                data["ssh_key"] = ssh_key

            response = self._make_request("POST", "deploy", data=data)

            if response.get("success"):
                vm_id = response.get("server")
                return TensorDockInstance(
                    id=vm_id,
                    name=data["name"],
                    status="deploying",
                    gpu_name="",  # Will be updated on next list
                    gpu_count=gpu_count,
                    vcpus=vcpus,
                    ram_gb=ram_gb,
                    storage_gb=storage_gb,
                    ip_address=response.get("ip"),
                    ssh_port=response.get("port_forwards", {}).get("22"),
                    hourly_cost=0,  # Will be updated
                    mode=mode,
                    created_at=datetime.now()
                )
            else:
                logger.error(f"Failed to create instance: {response}")
                return None

        except Exception as e:
            logger.error(f"Failed to create TensorDock instance: {e}")
            return None

    def pause_instance(self, instance_id: str) -> bool:
        """
        Pause a serverless instance.
        Keeps disk content for fast resume.
        """
        try:
            response = self._make_request("POST", "stop", data={"server": instance_id})
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Failed to pause instance {instance_id}: {e}")
            return False

    def resume_instance(self, instance_id: str) -> bool:
        """
        Resume a paused instance.
        Cold start time depends on mode (fast/economic/spot).
        """
        try:
            response = self._make_request("POST", "start", data={"server": instance_id})
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Failed to resume instance {instance_id}: {e}")
            return False

    def destroy_instance(self, instance_id: str) -> bool:
        """
        Permanently destroy an instance.
        This deletes all data.
        """
        try:
            response = self._make_request("POST", "delete", data={"server": instance_id})
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Failed to destroy instance {instance_id}: {e}")
            return False

    def get_status(self, instance_id: str) -> Optional[str]:
        """Get instance status."""
        instance = self.get_instance(instance_id)
        return instance.status if instance else None

    def is_configured(self) -> bool:
        """Check if TensorDock credentials are configured."""
        return bool(self.api_key and self.api_token)
