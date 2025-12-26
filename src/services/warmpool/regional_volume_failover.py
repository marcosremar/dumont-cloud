"""
Regional Volume Failover - Failover usando volumes regionais VAST.ai.

Estrategia de failover que mantem um volume persistente em uma regiao.
Quando a GPU falha, monta o mesmo volume em uma nova GPU da mesma regiao.

Tempo de recuperacao estimado: ~30-60 segundos
- Volume ja existe (nao precisa copiar dados)
- Montagem via NFS e quase instantanea
- Apenas provisionamento de nova GPU leva tempo
"""
import logging
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import aiohttp

from .volume_service import VolumeService, Volume, VolumeState
from .host_finder import HostFinder, GPUOffer

logger = logging.getLogger(__name__)


class RegionalFailoverState(str, Enum):
    """Estados do Regional Volume Failover"""
    INACTIVE = "inactive"           # Nao configurado
    PROVISIONING = "provisioning"   # Criando volume
    READY = "ready"                 # Volume pronto, aguardando failover
    FAILING_OVER = "failing_over"   # Executando failover
    COMPLETED = "completed"         # Failover concluido
    ERROR = "error"                 # Erro


@dataclass
class RegionalVolumeInfo:
    """Informacoes do volume regional"""
    volume_id: int
    region: str
    size_gb: int
    mount_path: str = "/data"
    state: RegionalFailoverState = RegionalFailoverState.INACTIVE
    current_instance_id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class RegionalFailoverResult:
    """Resultado de um failover regional"""
    success: bool
    volume_id: int
    old_instance_id: Optional[int] = None
    new_instance_id: Optional[int] = None
    new_gpu_name: Optional[str] = None
    region: Optional[str] = None
    failover_time_seconds: float = 0.0
    message: str = ""
    error: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None


class RegionalVolumeFailover:
    """
    Gerencia failover usando volumes regionais VAST.ai.

    Fluxo:
    1. Cria volume persistente em uma regiao
    2. Provisiona GPU e monta o volume
    3. Quando GPU falha, busca nova GPU na mesma regiao
    4. Monta o volume existente na nova GPU
    5. Tempo de recuperacao: ~30-60 segundos
    """

    def __init__(self, vast_api_key: str):
        self.api_key = vast_api_key
        self.api_url = "https://cloud.vast.ai/api/v0"
        self.volume_service = VolumeService(vast_api_key)
        self.host_finder = HostFinder(vast_api_key)

    async def create_regional_volume(
        self,
        region: str,
        size_gb: int = 50,
        name: Optional[str] = None
    ) -> Optional[RegionalVolumeInfo]:
        """
        Cria um volume em uma regiao especifica.

        Args:
            region: Codigo da regiao (ex: "US", "DE", "PL")
            size_gb: Tamanho do volume em GB
            name: Nome opcional do volume

        Returns:
            RegionalVolumeInfo ou None se falhou
        """
        try:
            logger.info(f"Creating regional volume in {region} ({size_gb}GB)")

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                payload = {
                    "size": size_gb,
                    "region": region,
                }

                if name:
                    payload["name"] = name

                async with session.post(
                    f"{self.api_url}/volumes/",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status not in [200, 201]:
                        text = await response.text()
                        logger.error(f"Failed to create volume: {response.status} - {text}")
                        return None

                    data = await response.json()

                    volume_info = RegionalVolumeInfo(
                        volume_id=data.get("id"),
                        region=region,
                        size_gb=size_gb,
                        state=RegionalFailoverState.READY,
                        created_at=data.get("created_at"),
                    )

                    logger.info(f"Created volume {volume_info.volume_id} in region {region}")
                    return volume_info

        except Exception as e:
            logger.error(f"Failed to create regional volume: {e}")
            return None

    async def search_volumes_in_region(self, region: str) -> List[Dict[str, Any]]:
        """
        Busca ofertas de volumes em uma regiao especifica.

        Args:
            region: Codigo da regiao (ex: "US", "CA", "DE")

        Returns:
            Lista de ofertas de volumes
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                params = {
                    "geolocation": region,
                }

                async with session.get(
                    f"{self.api_url}/volumes/search/",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()
                    return data.get("offers", [])

        except Exception as e:
            logger.error(f"Failed to search volumes: {e}")
            return []

    async def find_gpu_in_region(
        self,
        region: str,
        preferred_gpus: Optional[List[str]] = None,
        max_price: Optional[float] = None,
        use_spot: bool = True,
        min_reliability: float = 0.95,
    ) -> Optional[GPUOffer]:
        """
        Busca uma GPU disponivel em uma regiao especifica.

        Args:
            region: Codigo da regiao (ex: "US", "DE", "Texas, US")
            preferred_gpus: Lista de GPUs preferidas
            max_price: Preco maximo por hora
            use_spot: Usar instancias spot
            min_reliability: Confiabilidade minima

        Returns:
            GPUOffer ou None se nao encontrou
        """
        try:
            # Buscar todas as ofertas e filtrar por regiao
            # O VAST.ai retorna geolocation como "Texas, US", "California, US", etc
            # Então fazemos match parcial: "US" casa com "Texas, US"
            all_offers = await self.host_finder.search_offers(
                min_gpus=1,
                max_price=max_price,
                verified=False,  # Incluir todos para mais opcoes
                min_reliability=min_reliability,
            )

            # Filtrar por regiao (match parcial)
            region_upper = region.upper()
            region_offers = [
                o for o in all_offers
                if region_upper in o.geolocation.upper()
            ]

            if not region_offers:
                logger.warning(f"No GPU offers found in region {region}")
                return None

            # Se tiver GPUs preferidas, filtrar por elas
            gpu_names = preferred_gpus or ["RTX_4090", "RTX_3090", "RTX_4080", "RTX_5090", "A100"]

            for gpu_name in gpu_names:
                matching = [o for o in region_offers if gpu_name in o.gpu_name]
                if matching:
                    matching.sort(key=lambda o: o.price_per_hour)
                    logger.info(f"Found {len(matching)} {gpu_name} offers in {region}")
                    return matching[0]

            # Se nenhuma GPU preferida, retornar a mais barata
            region_offers.sort(key=lambda o: o.price_per_hour)
            best = region_offers[0]
            logger.info(f"Found GPU {best.gpu_name} in {region} at ${best.price_per_hour:.3f}/hr")
            return best

        except Exception as e:
            logger.error(f"Failed to find GPU in region: {e}")
            return None

    async def provision_gpu_with_volume(
        self,
        offer_id: int,
        volume_id: int,
        mount_path: str = "/data",
        docker_image: str = "pytorch/pytorch:latest",
        use_spot: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Provisiona uma GPU e anexa um volume existente.

        Args:
            offer_id: ID da oferta de GPU
            volume_id: ID do volume a anexar
            mount_path: Caminho de montagem
            docker_image: Imagem Docker
            use_spot: Usar instancia spot

        Returns:
            Informacoes da instancia ou None
        """
        try:
            logger.info(f"Provisioning GPU offer {offer_id} with volume {volume_id}")

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                payload = {
                    "client_id": "me",
                    "image": docker_image,
                    "disk": 20,
                    "runtype": "ssh",
                    "link_volume": volume_id,
                    "onstart": f"mkdir -p {mount_path}",
                }

                if use_spot:
                    payload["price"] = None  # Usar preco spot

                async with session.put(
                    f"{self.api_url}/asks/{offer_id}/",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status not in [200, 201]:
                        text = await response.text()
                        logger.error(f"Failed to provision GPU: {response.status} - {text}")
                        return None

                    data = await response.json()

                    instance_id = data.get("new_contract")
                    logger.info(f"Provisioned instance {instance_id} with volume {volume_id}")

                    return {
                        "instance_id": instance_id,
                        "volume_id": volume_id,
                        "mount_path": mount_path,
                    }

        except Exception as e:
            logger.error(f"Failed to provision GPU with volume: {e}")
            return None

    async def wait_for_instance_ready(
        self,
        instance_id: int,
        timeout_seconds: int = 120
    ) -> Optional[Dict[str, Any]]:
        """
        Aguarda uma instancia ficar pronta.

        Args:
            instance_id: ID da instancia
            timeout_seconds: Timeout em segundos

        Returns:
            Informacoes da instancia ou None
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }

                    async with session.get(
                        f"{self.api_url}/instances/{instance_id}/",
                        headers=headers
                    ) as response:
                        if response.status != 200:
                            await asyncio.sleep(5)
                            continue

                        data = await response.json()
                        status = data.get("actual_status", "")

                        if status == "running":
                            return {
                                "instance_id": instance_id,
                                "status": status,
                                "ssh_host": data.get("ssh_host"),
                                "ssh_port": data.get("ssh_port"),
                                "gpu_name": data.get("gpu_name"),
                                "num_gpus": data.get("num_gpus"),
                                "geolocation": data.get("geolocation"),
                            }

                        logger.debug(f"Instance {instance_id} status: {status}")

            except Exception as e:
                logger.warning(f"Error checking instance status: {e}")

            await asyncio.sleep(5)

        logger.error(f"Timeout waiting for instance {instance_id}")
        return None

    async def execute_failover(
        self,
        volume_id: int,
        region: str,
        old_instance_id: Optional[int] = None,
        preferred_gpus: Optional[List[str]] = None,
        max_price: Optional[float] = None,
        use_spot: bool = True,
        docker_image: str = "pytorch/pytorch:latest",
        mount_path: str = "/data",
        timeout_seconds: int = 120,
    ) -> RegionalFailoverResult:
        """
        Executa failover para nova GPU na mesma regiao.

        Args:
            volume_id: ID do volume existente
            region: Regiao do volume
            old_instance_id: ID da instancia antiga (sera destruida)
            preferred_gpus: Lista de GPUs preferidas
            max_price: Preco maximo por hora
            use_spot: Usar instancias spot
            docker_image: Imagem Docker
            mount_path: Caminho de montagem
            timeout_seconds: Timeout total

        Returns:
            RegionalFailoverResult
        """
        start_time = time.time()

        logger.info(f"Starting regional failover for volume {volume_id} in {region}")

        try:
            # 1. Buscar GPU disponivel na regiao
            gpu_offer = await self.find_gpu_in_region(
                region=region,
                preferred_gpus=preferred_gpus,
                max_price=max_price,
                use_spot=use_spot,
            )

            if not gpu_offer:
                return RegionalFailoverResult(
                    success=False,
                    volume_id=volume_id,
                    old_instance_id=old_instance_id,
                    message="No GPU available in region",
                    error=f"No GPU found in region {region}",
                )

            logger.info(f"Found GPU: {gpu_offer.gpu_name} at ${gpu_offer.price_per_hour}/hr")

            # 2. Provisionar nova GPU com volume
            provision_result = await self.provision_gpu_with_volume(
                offer_id=gpu_offer.offer_id,
                volume_id=volume_id,
                mount_path=mount_path,
                docker_image=docker_image,
                use_spot=use_spot,
            )

            if not provision_result:
                return RegionalFailoverResult(
                    success=False,
                    volume_id=volume_id,
                    old_instance_id=old_instance_id,
                    message="Failed to provision GPU",
                    error="Provisioning failed",
                )

            new_instance_id = provision_result["instance_id"]
            logger.info(f"Provisioned new instance {new_instance_id}")

            # 3. Aguardar instancia ficar pronta
            instance_info = await self.wait_for_instance_ready(
                instance_id=new_instance_id,
                timeout_seconds=timeout_seconds,
            )

            if not instance_info:
                return RegionalFailoverResult(
                    success=False,
                    volume_id=volume_id,
                    old_instance_id=old_instance_id,
                    new_instance_id=new_instance_id,
                    message="Instance failed to start",
                    error="Timeout waiting for instance",
                )

            # 4. Destruir instancia antiga (se especificada)
            if old_instance_id:
                await self._destroy_instance(old_instance_id)

            failover_time = time.time() - start_time

            return RegionalFailoverResult(
                success=True,
                volume_id=volume_id,
                old_instance_id=old_instance_id,
                new_instance_id=new_instance_id,
                new_gpu_name=instance_info.get("gpu_name"),
                region=instance_info.get("geolocation", region),
                failover_time_seconds=failover_time,
                message=f"Failover completed in {failover_time:.1f}s",
                ssh_host=instance_info.get("ssh_host"),
                ssh_port=instance_info.get("ssh_port"),
            )

        except Exception as e:
            logger.error(f"Failover failed: {e}")
            return RegionalFailoverResult(
                success=False,
                volume_id=volume_id,
                old_instance_id=old_instance_id,
                failover_time_seconds=time.time() - start_time,
                message="Failover failed",
                error=str(e),
            )

    async def _destroy_instance(self, instance_id: int) -> bool:
        """Destroi uma instancia"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.delete(
                    f"{self.api_url}/instances/{instance_id}/",
                    headers=headers
                ) as response:
                    if response.status in [200, 204]:
                        logger.info(f"Destroyed instance {instance_id}")
                        return True
                    return False

        except Exception as e:
            logger.error(f"Failed to destroy instance: {e}")
            return False

    async def get_volume_info(self, volume_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtem informacoes de um volume.

        Args:
            volume_id: ID do volume

        Returns:
            Informacoes do volume ou None
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.get(
                    f"{self.api_url}/volumes/{volume_id}/",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return None

                    return await response.json()

        except Exception as e:
            logger.error(f"Failed to get volume info: {e}")
            return None

    async def list_user_volumes(self) -> List[Dict[str, Any]]:
        """
        Lista todos os volumes do usuario.

        Returns:
            Lista de volumes
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.get(
                    f"{self.api_url}/volumes/",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()
                    return data.get("volumes", data) if isinstance(data, dict) else data

        except Exception as e:
            logger.error(f"Failed to list volumes: {e}")
            return []

    async def delete_volume(self, volume_id: int) -> bool:
        """
        Deleta um volume.

        Args:
            volume_id: ID do volume

        Returns:
            True se deletou com sucesso
        """
        return await self.volume_service.delete_volume(volume_id)

    # Versoes sincronas para conveniencia

    def create_regional_volume_sync(self, **kwargs) -> Optional[RegionalVolumeInfo]:
        """Versao sincrona de create_regional_volume"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.create_regional_volume(**kwargs))
        finally:
            loop.close()

    def execute_failover_sync(self, **kwargs) -> RegionalFailoverResult:
        """Versao sincrona de execute_failover"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.execute_failover(**kwargs))
        finally:
            loop.close()

    def find_gpu_in_region_sync(self, **kwargs) -> Optional[GPUOffer]:
        """Versao sincrona de find_gpu_in_region"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.find_gpu_in_region(**kwargs))
        finally:
            loop.close()

    def list_user_volumes_sync(self) -> List[Dict[str, Any]]:
        """Versao sincrona de list_user_volumes"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.list_user_volumes())
        finally:
            loop.close()


# Singleton instance
_regional_volume_failover: Optional[RegionalVolumeFailover] = None


def get_regional_volume_failover(vast_api_key: Optional[str] = None) -> RegionalVolumeFailover:
    """
    Retorna a instancia global do RegionalVolumeFailover.

    Args:
        vast_api_key: API key do VAST.ai (necessario na primeira chamada)

    Returns:
        RegionalVolumeFailover instance
    """
    global _regional_volume_failover

    if _regional_volume_failover is None:
        if not vast_api_key:
            import os
            vast_api_key = os.environ.get("VAST_API_KEY")

        if not vast_api_key:
            raise ValueError("VAST_API_KEY is required")

        _regional_volume_failover = RegionalVolumeFailover(vast_api_key)

    return _regional_volume_failover
