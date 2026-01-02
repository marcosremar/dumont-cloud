"""
Módulo de gerenciamento de instâncias GPU.

Permite listar, criar, pausar, resumir e destruir instâncias.
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GPUOffer:
    """Oferta de GPU disponível."""
    id: int
    gpu_name: str
    num_gpus: int
    gpu_ram: float
    cpu_cores: int
    cpu_ram: float
    disk_space: float
    inet_down: float
    inet_up: float
    dph_total: float  # Dollars per hour
    geolocation: Optional[str] = None
    reliability: float = 0.0
    cuda_version: Optional[str] = None
    verified: bool = False
    static_ip: bool = False


@dataclass
class Instance:
    """Instância GPU."""
    id: int
    status: str
    actual_status: Optional[str] = None
    gpu_name: Optional[str] = None
    num_gpus: int = 1
    gpu_ram: float = 0.0
    cpu_cores: int = 0
    cpu_ram: float = 0.0
    disk_space: float = 0.0
    dph_total: float = 0.0
    public_ipaddr: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    start_date: Optional[str] = None
    label: Optional[str] = None
    ports: Optional[Dict[str, int]] = None
    gpu_util: float = 0.0
    gpu_temp: float = 0.0
    cpu_util: float = 0.0
    ram_used: float = 0.0
    ram_total: float = 0.0
    provider: str = "vast.ai"

    @property
    def ssh_command(self) -> str:
        """Retorna comando SSH para conectar."""
        host = self.public_ipaddr or self.ssh_host
        if host and self.ssh_port:
            return f"ssh -p {self.ssh_port} root@{host}"
        return ""

    @property
    def is_running(self) -> bool:
        """Verifica se está rodando."""
        return (self.actual_status or self.status) == "running"


class InstancesClient:
    """
    Cliente para gerenciamento de instâncias GPU.

    Exemplo:
        async with DumontClient(api_key="...") as client:
            instances = await client.instances.list()
            for inst in instances:
                print(f"{inst.id}: {inst.gpu_name} - {inst.status}")
    """

    def __init__(self, base_client):
        self._client = base_client

    async def list(self) -> List[Instance]:
        """
        Lista todas as instâncias do usuário.

        Returns:
            Lista de instâncias
        """
        response = await self._client.get("/api/v1/instances")
        instances_data = response.get("instances", [])

        return [
            Instance(
                id=inst["id"],
                status=inst.get("status", "unknown"),
                actual_status=inst.get("actual_status"),
                gpu_name=inst.get("gpu_name"),
                num_gpus=inst.get("num_gpus", 1),
                gpu_ram=inst.get("gpu_ram", 0),
                cpu_cores=inst.get("cpu_cores", 0),
                cpu_ram=inst.get("cpu_ram", 0),
                disk_space=inst.get("disk_space", 0),
                dph_total=inst.get("dph_total", 0),
                public_ipaddr=inst.get("public_ipaddr"),
                ssh_host=inst.get("ssh_host"),
                ssh_port=inst.get("ssh_port"),
                start_date=inst.get("start_date"),
                label=inst.get("label"),
                ports=inst.get("ports"),
                gpu_util=inst.get("gpu_util", 0),
                gpu_temp=inst.get("gpu_temp", 0),
                cpu_util=inst.get("cpu_util", 0),
                ram_used=inst.get("ram_used", 0),
                ram_total=inst.get("ram_total", 0),
                provider=inst.get("provider", "vast.ai"),
            )
            for inst in instances_data
        ]

    async def get(self, instance_id: int) -> Instance:
        """
        Obtém detalhes de uma instância.

        Args:
            instance_id: ID da instância

        Returns:
            Detalhes da instância
        """
        inst = await self._client.get(f"/api/v1/instances/{instance_id}")

        return Instance(
            id=inst["id"],
            status=inst.get("status", "unknown"),
            actual_status=inst.get("actual_status"),
            gpu_name=inst.get("gpu_name"),
            num_gpus=inst.get("num_gpus", 1),
            gpu_ram=inst.get("gpu_ram", 0),
            cpu_cores=inst.get("cpu_cores", 0),
            cpu_ram=inst.get("cpu_ram", 0),
            disk_space=inst.get("disk_space", 0),
            dph_total=inst.get("dph_total", 0),
            public_ipaddr=inst.get("public_ipaddr"),
            ssh_host=inst.get("ssh_host"),
            ssh_port=inst.get("ssh_port"),
            start_date=inst.get("start_date"),
            label=inst.get("label"),
            ports=inst.get("ports"),
            gpu_util=inst.get("gpu_util", 0),
            gpu_temp=inst.get("gpu_temp", 0),
            cpu_util=inst.get("cpu_util", 0),
            ram_used=inst.get("ram_used", 0),
            ram_total=inst.get("ram_total", 0),
            provider=inst.get("provider", "vast.ai"),
        )

    async def search_offers(
        self,
        gpu_name: Optional[str] = None,
        num_gpus: int = 1,
        min_gpu_ram: float = 0,
        min_cpu_cores: int = 1,
        min_cpu_ram: float = 1,
        min_disk: float = 50,
        max_price: float = 10.0,
        region: Optional[str] = None,
        min_reliability: float = 0.0,
        verified_only: bool = False,
        limit: int = 50,
    ) -> List[GPUOffer]:
        """
        Busca ofertas de GPU disponíveis.

        Args:
            gpu_name: Modelo da GPU (RTX_4090, A100, etc)
            num_gpus: Número de GPUs
            min_gpu_ram: VRAM mínima em GB
            min_cpu_cores: CPU cores mínimos
            min_cpu_ram: RAM CPU mínima em GB
            min_disk: Disco mínimo em GB
            max_price: Preço máximo por hora
            region: Região (US, EU, ASIA)
            min_reliability: Confiabilidade mínima (0-1)
            verified_only: Apenas hosts verificados
            limit: Máximo de resultados

        Returns:
            Lista de ofertas
        """
        params = {
            "num_gpus": num_gpus,
            "min_gpu_ram": min_gpu_ram,
            "min_cpu_cores": min_cpu_cores,
            "min_cpu_ram": min_cpu_ram,
            "min_disk": min_disk,
            "max_price": max_price,
            "min_reliability": min_reliability,
            "verified_only": verified_only,
            "limit": limit,
        }

        if gpu_name:
            params["gpu_name"] = gpu_name
        if region:
            params["region"] = region

        response = await self._client.get("/api/v1/instances/offers", params=params)
        offers_data = response.get("offers", [])

        return [
            GPUOffer(
                id=offer["id"],
                gpu_name=offer["gpu_name"],
                num_gpus=offer.get("num_gpus", 1),
                gpu_ram=offer.get("gpu_ram", 0),
                cpu_cores=offer.get("cpu_cores", 0),
                cpu_ram=offer.get("cpu_ram", 0),
                disk_space=offer.get("disk_space", 0),
                inet_down=offer.get("inet_down", 0),
                inet_up=offer.get("inet_up", 0),
                dph_total=offer.get("dph_total", 0),
                geolocation=offer.get("geolocation"),
                reliability=offer.get("reliability", 0),
                cuda_version=offer.get("cuda_version"),
                verified=offer.get("verified", False),
                static_ip=offer.get("static_ip", False),
            )
            for offer in offers_data
        ]

    async def create(
        self,
        offer_id: int,
        image: str = "pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime",
        disk_size: float = 50,
        label: Optional[str] = None,
        ports: Optional[List[int]] = None,
        skip_standby: bool = False,
    ) -> Instance:
        """
        Cria uma nova instância.

        Args:
            offer_id: ID da oferta
            image: Imagem Docker
            disk_size: Tamanho do disco em GB
            label: Label para a instância
            ports: Portas para expor
            skip_standby: Não criar CPU standby

        Returns:
            Instância criada
        """
        data = {
            "offer_id": offer_id,
            "image": image,
            "disk_size": disk_size,
            "skip_standby": skip_standby,
        }

        if label:
            data["label"] = label
        if ports:
            data["ports"] = ports

        inst = await self._client.post("/api/v1/instances", data=data)

        return Instance(
            id=inst["id"],
            status=inst.get("status", "loading"),
            actual_status=inst.get("actual_status"),
            gpu_name=inst.get("gpu_name"),
            num_gpus=inst.get("num_gpus", 1),
            gpu_ram=inst.get("gpu_ram", 0),
            cpu_cores=inst.get("cpu_cores", 0),
            cpu_ram=inst.get("cpu_ram", 0),
            disk_space=inst.get("disk_space", 0),
            dph_total=inst.get("dph_total", 0),
            public_ipaddr=inst.get("public_ipaddr"),
            ssh_host=inst.get("ssh_host"),
            ssh_port=inst.get("ssh_port"),
            label=inst.get("label"),
            ports=inst.get("ports"),
        )

    async def destroy(
        self,
        instance_id: int,
        destroy_standby: bool = True,
        reason: str = "user_request",
    ) -> Dict[str, Any]:
        """
        Destrói uma instância.

        Args:
            instance_id: ID da instância
            destroy_standby: Também destruir CPU standby
            reason: Motivo (user_request, gpu_failure, spot_interruption)

        Returns:
            Resultado da operação
        """
        params = {
            "destroy_standby": destroy_standby,
            "reason": reason,
        }
        return await self._client.delete(f"/api/v1/instances/{instance_id}", params=params)

    async def pause(self, instance_id: int) -> Dict[str, Any]:
        """
        Pausa uma instância.

        Args:
            instance_id: ID da instância

        Returns:
            Resultado da operação
        """
        return await self._client.post(f"/api/v1/instances/{instance_id}/pause")

    async def resume(self, instance_id: int) -> Dict[str, Any]:
        """
        Resume uma instância pausada.

        Args:
            instance_id: ID da instância

        Returns:
            Resultado da operação
        """
        return await self._client.post(f"/api/v1/instances/{instance_id}/resume")

    async def wake(
        self,
        instance_id: int,
        gpu_type: Optional[str] = None,
        region: Optional[str] = None,
        max_price: float = 1.0,
        restore_snapshot: bool = True,
    ) -> Dict[str, Any]:
        """
        Acorda uma instância hibernada.

        Provisiona nova GPU e restaura snapshot.

        Args:
            instance_id: ID da instância hibernada
            gpu_type: Tipo de GPU desejado
            region: Região desejada
            max_price: Preço máximo
            restore_snapshot: Restaurar snapshot

        Returns:
            Resultado com new_instance_id
        """
        data = {
            "max_price": max_price,
            "restore_snapshot": restore_snapshot,
        }
        if gpu_type:
            data["gpu_type"] = gpu_type
        if region:
            data["region"] = region

        return await self._client.post(f"/api/v1/instances/{instance_id}/wake", data=data)

    async def sync(
        self,
        instance_id: int,
        source_path: str = "/workspace",
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Sincroniza dados da instância.

        Args:
            instance_id: ID da instância
            source_path: Caminho para sincronizar
            force: Forçar sync mesmo se recente

        Returns:
            Estatísticas do sync
        """
        params = {
            "source_path": source_path,
            "force": force,
        }
        return await self._client.post(f"/api/v1/instances/{instance_id}/sync", params=params)

    async def sync_status(self, instance_id: int) -> Dict[str, Any]:
        """
        Obtém status do sync de uma instância.

        Args:
            instance_id: ID da instância

        Returns:
            Status do sync
        """
        return await self._client.get(f"/api/v1/instances/{instance_id}/sync/status")

    async def migrate(
        self,
        instance_id: int,
        target_type: str,
        gpu_name: Optional[str] = None,
        max_price: float = 2.0,
        region: Optional[str] = None,
        disk_size: int = 100,
        auto_destroy_source: bool = True,
    ) -> Dict[str, Any]:
        """
        Migrate instance between GPU and CPU.

        Creates a snapshot, provisions new instance, restores snapshot,
        and optionally destroys the source instance.

        Args:
            instance_id: ID of the instance to migrate
            target_type: Target type ('gpu' or 'cpu')
            gpu_name: GPU model (required if target_type='gpu')
            max_price: Maximum price per hour
            region: Region filter (US, EU, ASIA)
            disk_size: Disk size in GB
            auto_destroy_source: Destroy source after migration

        Returns:
            Migration result with new_instance_id, snapshot_id, steps_completed
        """
        data = {
            "target_type": target_type,
            "max_price": max_price,
            "disk_size": disk_size,
            "auto_destroy_source": auto_destroy_source,
        }
        if gpu_name:
            data["gpu_name"] = gpu_name
        if region:
            data["region"] = region

        return await self._client.post(f"/api/v1/instances/{instance_id}/migrate", data=data)

    async def migrate_estimate(
        self,
        instance_id: int,
        target_type: str,
        gpu_name: Optional[str] = None,
        max_price: float = 2.0,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get migration estimate.

        Returns estimated cost and availability for migrating an instance.

        Args:
            instance_id: ID of the instance
            target_type: Target type ('gpu' or 'cpu')
            gpu_name: GPU model (required if target_type='gpu')
            max_price: Maximum price per hour
            region: Region filter (US, EU, ASIA)

        Returns:
            Estimate with available, source, target, estimated_time_minutes, offers_available
        """
        data = {
            "target_type": target_type,
            "max_price": max_price,
        }
        if gpu_name:
            data["gpu_name"] = gpu_name
        if region:
            data["region"] = region

        return await self._client.post(f"/api/v1/instances/{instance_id}/migrate/estimate", data=data)
