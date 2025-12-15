"""
Service para interacao com a API do vast.ai
"""
import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class GpuOffer:
    """Representa uma oferta de GPU"""
    id: int
    gpu_name: str
    num_gpus: int
    gpu_ram: float
    cpu_cores: int
    cpu_ram: float
    disk_space: float
    inet_down: float
    inet_up: float
    dph_total: float
    geolocation: str
    reliability: float
    cuda_version: str
    verified: bool
    static_ip: bool


class VastService:
    """Service para gerenciar instancias vast.ai"""

    API_URL = "https://console.vast.ai/api/v0"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def search_offers(
        self,
        gpu_name: Optional[str] = None,
        num_gpus: int = 1,
        min_gpu_ram: float = 16,
        min_cpu_cores: int = 8,
        min_cpu_ram: float = 16,
        min_disk: float = 50,
        min_inet_down: float = 500,
        max_price: float = 1.0,
        min_cuda: str = "12.0",
        min_reliability: float = 0.95,
        region: Optional[str] = None,
        verified_only: bool = True,
        static_ip: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Busca ofertas de GPU com filtros"""
        import json

        # Monta query para a API vast.ai
        query = {
            "rentable": {"eq": True},
            "num_gpus": {"eq": num_gpus},
            "gpu_ram": {"gte": min_gpu_ram * 1024},  # MB
            "cpu_cores": {"gte": min_cpu_cores},
            "cpu_ram": {"gte": min_cpu_ram * 1024},  # MB
            "disk_space": {"gte": min_disk},
            "inet_down": {"gte": min_inet_down},
            "dph_total": {"lte": max_price},
            "cuda_max_good": {"gte": float(min_cuda)},
            "reliability2": {"gte": min_reliability},
        }

        if verified_only:
            query["verified"] = {"eq": True}

        if gpu_name:
            query["gpu_name"] = {"eq": gpu_name}

        if static_ip:
            query["static_ip"] = {"eq": True}

        params = {
            "q": json.dumps(query),  # Usar json.dumps para formato correto
            "order": "dph_total",
            "type": "on-demand",
            "limit": limit,
        }

        try:
            resp = requests.get(
                f"{self.API_URL}/bundles",
                params=params,
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            offers = data.get("offers", []) if isinstance(data, dict) else data

            # Filtrar por regiao se especificado
            if region:
                region_codes = self._get_region_codes(region)
                offers = [
                    o for o in offers
                    if any(code in str(o.get("geolocation", "")) for code in region_codes)
                ]

            return offers
        except Exception as e:
            print(f"Erro ao buscar ofertas: {e}")
            return []

    def _get_region_codes(self, region: str) -> List[str]:
        """Retorna codigos de paises para uma regiao"""
        regions = {
            "EU": ["ES", "DE", "FR", "NL", "IT", "PL", "CZ", "BG", "UK", "GB",
                   "Spain", "Germany", "France", "Netherlands", "Poland",
                   "Czechia", "Bulgaria", "Sweden", "Norway", "Finland"],
            "US": ["US", "United States", "CA", "Canada"],
            "ASIA": ["JP", "Japan", "KR", "Korea", "SG", "Singapore", "TW", "Taiwan"],
        }
        return regions.get(region.upper(), [])

    def create_instance(self, offer_id: int, image: str = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime") -> Optional[int]:
        """Cria uma nova instancia"""
        try:
            resp = requests.put(
                f"{self.API_URL}/asks/{offer_id}/",
                json={
                    "client_id": "me",
                    "image": image,
                    "disk": 50,
                    "onstart": "bash",  # Usar bash puro, sem tmux
                },
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("new_contract")
        except Exception as e:
            print(f"Erro ao criar instancia: {e}")
            return None

    def get_instance_status(self, instance_id: int) -> Dict[str, Any]:
        """Retorna status de uma instancia"""
        try:
            resp = requests.get(
                f"{self.API_URL}/instances/{instance_id}/",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            instance = data.get("instances", [{}])[0] if data.get("instances") else data

            return {
                "id": instance.get("id"),
                "status": instance.get("actual_status", "unknown"),
                "ssh_host": instance.get("ssh_host"),
                "ssh_port": instance.get("ssh_port"),
                "gpu_name": instance.get("gpu_name"),
                "num_gpus": instance.get("num_gpus"),
            }
        except Exception as e:
            return {"error": str(e), "status": "error"}

    def destroy_instance(self, instance_id: int) -> bool:
        """Destroi uma instancia"""
        try:
            resp = requests.delete(
                f"{self.API_URL}/instances/{instance_id}/",
                headers=self.headers,
                timeout=30,
            )
            return resp.status_code in [200, 204]
        except Exception as e:
            print(f"Erro ao destruir instancia: {e}")
            return False

    def get_my_instances(self) -> List[Dict[str, Any]]:
        """Lista todas as instancias do usuario"""
        try:
            resp = requests.get(
                f"{self.API_URL}/instances/",
                params={"owner": "me"},
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("instances", [])
        except Exception as e:
            print(f"Erro ao listar instancias: {e}")
            return []
