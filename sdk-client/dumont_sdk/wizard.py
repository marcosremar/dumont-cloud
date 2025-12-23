"""
Módulo Wizard Deploy.

Estratégia de deploy multi-start com batches de máquinas.
Inicia várias máquinas em paralelo, a primeira que ficar pronta ganha.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DeploySpeed(str, Enum):
    """Velocidade do deploy."""
    FAST = "fast"       # Prioriza velocidade (mais máquinas em paralelo)
    BALANCED = "balanced"  # Equilíbrio entre custo e velocidade
    CHEAP = "cheap"     # Prioriza custo (menos máquinas em paralelo)


class DeployStatus(str, Enum):
    """Status do deploy."""
    PENDING = "pending"
    SEARCHING = "searching"
    CREATING = "creating"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DeployConfig:
    """Configuração do wizard deploy."""
    gpu_name: Optional[str] = None
    num_gpus: int = 1
    min_gpu_ram: float = 8.0
    max_price: float = 2.0
    region: Optional[str] = None
    speed: DeploySpeed = DeploySpeed.FAST
    disk_size: float = 50
    image: str = "pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime"
    label: Optional[str] = None
    setup_codeserver: bool = False
    ports: List[int] = field(default_factory=lambda: [22, 8080])

    # Multi-start settings
    batch_size: int = 5       # Máquinas por batch
    max_batches: int = 3      # Máximo de batches
    batch_timeout: int = 90   # Timeout por batch em segundos


@dataclass
class DeployResult:
    """Resultado do wizard deploy."""
    success: bool
    instance_id: Optional[int] = None
    gpu_name: Optional[str] = None
    public_ip: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_command: Optional[str] = None
    dph_total: float = 0.0
    ready_time: float = 0.0
    machines_tried: int = 0
    machines_destroyed: int = 0
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.success and self.instance_id is not None


class WizardClient:
    """
    Cliente para Wizard Deploy.

    Estratégia multi-start:
    1. Busca ofertas que atendem aos critérios
    2. Cria batch de N máquinas em paralelo
    3. Espera até uma ficar pronta (SSH acessível)
    4. Destrói as outras
    5. Se nenhuma ficou pronta, tenta próximo batch

    Exemplo:
        async with DumontClient(api_key="...") as client:
            result = await client.wizard.deploy(
                gpu_name="RTX 4090",
                max_price=1.5,
                speed="fast"
            )
            print(f"SSH: {result.ssh_command}")
    """

    def __init__(self, base_client):
        self._client = base_client
        self._on_progress: Optional[Callable[[str, Dict], None]] = None

    def on_progress(self, callback: Callable[[str, Dict], None]):
        """
        Registra callback para progresso do deploy.

        Args:
            callback: Função chamada com (status, data)
        """
        self._on_progress = callback

    def _emit_progress(self, status: str, data: Dict):
        """Emite evento de progresso."""
        if self._on_progress:
            try:
                self._on_progress(status, data)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    async def deploy(
        self,
        gpu_name: Optional[str] = None,
        max_price: float = 2.0,
        region: Optional[str] = None,
        speed: str = "fast",
        disk_size: float = 50,
        label: Optional[str] = None,
        batch_size: int = 5,
        max_batches: int = 3,
        timeout_per_batch: int = 90,
    ) -> DeployResult:
        """
        Deploy com estratégia multi-start.

        Args:
            gpu_name: Modelo da GPU (ex: "RTX 4090", "A100")
            max_price: Preço máximo por hora
            region: Região (US, EU, ASIA)
            speed: Velocidade (fast, balanced, cheap)
            disk_size: Tamanho do disco em GB
            label: Label para a instância
            batch_size: Máquinas por batch
            max_batches: Máximo de batches
            timeout_per_batch: Timeout por batch em segundos

        Returns:
            DeployResult com detalhes da máquina ou erro
        """
        config = DeployConfig(
            gpu_name=gpu_name,
            max_price=max_price,
            region=region,
            speed=DeploySpeed(speed) if isinstance(speed, str) else speed,
            disk_size=disk_size,
            label=label,
            batch_size=batch_size,
            max_batches=max_batches,
            batch_timeout=timeout_per_batch,
        )

        return await self._execute_deploy(config)

    async def _execute_deploy(self, config: DeployConfig) -> DeployResult:
        """Executa o deploy multi-start."""
        machines_tried = 0
        machines_destroyed = 0

        # Step 1: Buscar ofertas
        self._emit_progress("searching", {"message": "Buscando ofertas..."})

        try:
            from .instances import InstancesClient
            instances_client = InstancesClient(self._client)

            offers = await instances_client.search_offers(
                gpu_name=config.gpu_name,
                max_price=config.max_price,
                region=config.region,
                min_gpu_ram=config.min_gpu_ram,
                num_gpus=config.num_gpus,
                min_disk=config.disk_size,
                limit=config.batch_size * config.max_batches,
            )

            if not offers:
                return DeployResult(
                    success=False,
                    error="Nenhuma oferta encontrada com os critérios especificados",
                )

            self._emit_progress("found_offers", {
                "count": len(offers),
                "top_offers": [
                    {"gpu": o.gpu_name, "price": o.dph_total}
                    for o in offers[:5]
                ],
            })

        except Exception as e:
            return DeployResult(
                success=False,
                error=f"Erro ao buscar ofertas: {e}",
            )

        # Step 2: Deploy em batches
        import time
        start_time = time.time()

        for batch_num in range(config.max_batches):
            batch_start = batch_num * config.batch_size
            batch_end = batch_start + config.batch_size
            batch_offers = offers[batch_start:batch_end]

            if not batch_offers:
                break

            self._emit_progress("creating", {
                "batch": batch_num + 1,
                "max_batches": config.max_batches,
                "machines": len(batch_offers),
            })

            # Criar máquinas em paralelo
            created_instances = []
            create_tasks = []

            for offer in batch_offers:
                task = instances_client.create(
                    offer_id=offer.id,
                    image=config.image,
                    disk_size=config.disk_size,
                    label=config.label,
                    skip_standby=True,  # Wizard não precisa de standby
                )
                create_tasks.append(task)

            # Aguarda criação
            results = await asyncio.gather(*create_tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Falha ao criar máquina: {result}")
                else:
                    created_instances.append(result)
                    machines_tried += 1

            if not created_instances:
                self._emit_progress("batch_failed", {
                    "batch": batch_num + 1,
                    "reason": "Nenhuma máquina criada",
                })
                continue

            self._emit_progress("waiting", {
                "batch": batch_num + 1,
                "machines": len(created_instances),
                "ids": [inst.id for inst in created_instances],
            })

            # Step 3: Esperar primeira máquina ficar pronta
            winner = await self._wait_for_ready(
                instances_client,
                created_instances,
                timeout=config.batch_timeout,
            )

            if winner:
                # Step 4: Destruir as outras
                for inst in created_instances:
                    if inst.id != winner.id:
                        try:
                            await instances_client.destroy(inst.id, destroy_standby=True)
                            machines_destroyed += 1
                        except Exception as e:
                            logger.warning(f"Falha ao destruir {inst.id}: {e}")

                ready_time = time.time() - start_time

                self._emit_progress("completed", {
                    "instance_id": winner.id,
                    "ready_time": ready_time,
                })

                return DeployResult(
                    success=True,
                    instance_id=winner.id,
                    gpu_name=winner.gpu_name,
                    public_ip=winner.public_ipaddr,
                    ssh_port=winner.ssh_port,
                    ssh_command=winner.ssh_command,
                    dph_total=winner.dph_total,
                    ready_time=ready_time,
                    machines_tried=machines_tried,
                    machines_destroyed=machines_destroyed,
                )

            # Nenhuma ficou pronta, destruir todas e tentar próximo batch
            for inst in created_instances:
                try:
                    await instances_client.destroy(inst.id, destroy_standby=True)
                    machines_destroyed += 1
                except Exception:
                    pass

            self._emit_progress("batch_timeout", {
                "batch": batch_num + 1,
                "destroyed": len(created_instances),
            })

        # Todos os batches falharam
        return DeployResult(
            success=False,
            machines_tried=machines_tried,
            machines_destroyed=machines_destroyed,
            error=f"Nenhuma máquina ficou pronta após {config.max_batches} batches",
        )

    async def _wait_for_ready(
        self,
        instances_client,
        instances: List,
        timeout: int,
    ):
        """
        Espera até uma instância ficar pronta.

        Args:
            instances_client: Cliente de instâncias
            instances: Lista de instâncias criadas
            timeout: Timeout em segundos

        Returns:
            Primeira instância pronta ou None
        """
        import time
        start = time.time()

        while time.time() - start < timeout:
            for inst in instances:
                try:
                    updated = await instances_client.get(inst.id)

                    if updated.is_running and updated.public_ipaddr and updated.ssh_port:
                        # Verifica se SSH está acessível
                        if await self._check_ssh(updated.public_ipaddr, updated.ssh_port):
                            return updated

                except Exception as e:
                    logger.debug(f"Erro ao verificar {inst.id}: {e}")

            await asyncio.sleep(5)

        return None

    async def _check_ssh(self, host: str, port: int, timeout: float = 5.0) -> bool:
        """Verifica se SSH está acessível."""
        import asyncio

        try:
            # Tenta abrir conexão TCP
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def quick_deploy(
        self,
        gpu_name: Optional[str] = None,
        max_price: float = 1.0,
    ) -> DeployResult:
        """
        Deploy rápido com configurações padrão.

        Args:
            gpu_name: Modelo da GPU (opcional)
            max_price: Preço máximo

        Returns:
            DeployResult
        """
        return await self.deploy(
            gpu_name=gpu_name,
            max_price=max_price,
            speed="fast",
            batch_size=5,
            max_batches=2,
            timeout_per_batch=60,
        )
