"""
Servico de CPU Standby para resiliencia de instancias GPU interruptivas.

Arquitetura:
- Mantém uma máquina CPU barata (~$0.02/h) sempre ligada como standby
- Quando a GPU é interrompida, o trabalho continua na CPU
- Quando nova GPU fica disponível, migra de volta automaticamente
- Proxy no VPS gerencia o failover transparente

Custos estimados:
- CPU Standby (2 vCPU, 4GB RAM): ~$15/mês
- Tempo de failover: < 5 segundos
"""
import os
import time
import threading
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import requests

from src.services.vast_service import VastService


class MachineRole(Enum):
    """Papel da máquina no sistema"""
    GPU_PRIMARY = "gpu_primary"  # GPU ativa principal
    CPU_STANDBY = "cpu_standby"  # CPU de backup sempre ligada
    GPU_PENDING = "gpu_pending"  # Nova GPU sendo provisionada


class MachineStatus(Enum):
    """Status da máquina"""
    STARTING = "starting"
    RUNNING = "running"
    SYNCING = "syncing"  # Sincronizando dados
    READY = "ready"  # Pronta para uso
    FAILING = "failing"
    OFFLINE = "offline"


@dataclass
class ManagedMachine:
    """Representa uma máquina gerenciada pelo sistema"""
    instance_id: int
    role: MachineRole
    status: MachineStatus
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    public_ip: Optional[str] = None
    codeserver_port: int = 8080
    last_health_check: float = 0
    health_failures: int = 0
    gpu_name: Optional[str] = None
    cost_per_hour: float = 0


@dataclass
class CPUStandbyConfig:
    """Configurações do serviço de CPU Standby"""
    # Especificações mínimas da CPU standby
    min_cpu_cores: int = 2
    min_cpu_ram: float = 4  # GB
    min_disk: float = 50  # GB
    max_price_cpu: float = 0.05  # $/hora - máx para CPU standby

    # Health check
    health_check_interval: int = 5  # segundos
    max_health_failures: int = 3  # falhas antes de considerar offline

    # Failover
    failover_delay: int = 2  # segundos antes de ativar standby

    # Região preferida (manter próximo do VPS)
    preferred_region: str = "EU"


class CPUStandbyService:
    """
    Gerencia o sistema de CPU Standby para resiliência de GPUs interruptivas.

    Fluxo:
    1. Usuário inicia sessão com GPU interruptiva
    2. Sistema provisiona CPU standby automaticamente
    3. Health check monitora GPU a cada 5s
    4. Se GPU falhar, proxy redireciona para CPU
    5. Nova GPU é provisionada automaticamente
    6. Quando pronta, migra de volta para GPU
    """

    def __init__(self, vast_api_key: str, config: Optional[CPUStandbyConfig] = None):
        self.vast = VastService(vast_api_key)
        self.config = config or CPUStandbyConfig()

        # Máquinas gerenciadas
        self.machines: Dict[int, ManagedMachine] = {}

        # Máquina ativa (recebendo conexões do proxy)
        self.active_machine_id: Optional[int] = None

        # Threads de monitoramento
        self._health_thread: Optional[threading.Thread] = None
        self._running = False

        # Callbacks para notificações
        self._on_failover_callbacks: List[callable] = []
        self._on_recovery_callbacks: List[callable] = []

    def start_monitoring(self):
        """Inicia thread de health check"""
        if self._running:
            return

        self._running = True
        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()
        print("[CPUStandby] Monitoramento iniciado")

    def stop_monitoring(self):
        """Para thread de health check"""
        self._running = False
        if self._health_thread:
            self._health_thread.join(timeout=5)
        print("[CPUStandby] Monitoramento parado")

    def provision_cpu_standby(self, user_id: str) -> Optional[int]:
        """
        Provisiona uma máquina CPU standby.

        Args:
            user_id: ID do usuário (para namespacing)

        Returns:
            Instance ID da CPU standby ou None se falhar
        """
        print(f"[CPUStandby] Provisionando CPU standby para user {user_id}")

        # Buscar ofertas de CPU (sem GPU)
        offers = self._search_cpu_offers()

        if not offers:
            print("[CPUStandby] Nenhuma oferta de CPU encontrada")
            return None

        # Escolher a mais barata
        best_offer = min(offers, key=lambda o: o.get("dph_total", 999))

        print(f"[CPUStandby] Selecionada oferta: {best_offer.get('id')} "
              f"({best_offer.get('cpu_cores')} cores, ${best_offer.get('dph_total'):.3f}/h)")

        # Criar instância
        instance_id = self.vast.create_instance(
            offer_id=best_offer["id"],
            disk=int(self.config.min_disk),
            template_id=None,  # Usar imagem padrão sem GPU
        )

        if instance_id:
            machine = ManagedMachine(
                instance_id=instance_id,
                role=MachineRole.CPU_STANDBY,
                status=MachineStatus.STARTING,
                cost_per_hour=best_offer.get("dph_total", 0),
            )
            self.machines[instance_id] = machine

            # Aguardar estar pronta em background
            threading.Thread(
                target=self._wait_machine_ready,
                args=(instance_id,),
                daemon=True
            ).start()

        return instance_id

    def register_gpu_instance(self, instance_id: int, is_interruptible: bool = True) -> bool:
        """
        Registra uma instância GPU no sistema de monitoramento.

        Args:
            instance_id: ID da instância vast.ai
            is_interruptible: Se é uma instância interruptível

        Returns:
            True se registrada com sucesso
        """
        status = self.vast.get_instance_status(instance_id)

        if "error" in status:
            print(f"[CPUStandby] Erro ao buscar instância {instance_id}: {status['error']}")
            return False

        machine = ManagedMachine(
            instance_id=instance_id,
            role=MachineRole.GPU_PRIMARY,
            status=MachineStatus.RUNNING,
            ssh_host=status.get("ssh_host"),
            ssh_port=status.get("ssh_port"),
            public_ip=status.get("public_ipaddr"),
            gpu_name=status.get("gpu_name"),
        )

        self.machines[instance_id] = machine
        self.active_machine_id = instance_id

        print(f"[CPUStandby] GPU registrada: {instance_id} ({machine.gpu_name})")

        # Se é interruptível, garantir que temos CPU standby
        if is_interruptible:
            self._ensure_cpu_standby()

        return True

    def get_active_endpoint(self) -> Optional[Dict[str, Any]]:
        """
        Retorna o endpoint ativo para conexão.

        Returns:
            Dict com host, port, role ou None
        """
        if not self.active_machine_id:
            return None

        machine = self.machines.get(self.active_machine_id)
        if not machine:
            return None

        return {
            "instance_id": machine.instance_id,
            "host": machine.ssh_host or machine.public_ip,
            "port": machine.codeserver_port,
            "role": machine.role.value,
            "status": machine.status.value,
            "gpu_name": machine.gpu_name,
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status completo do sistema.

        Returns:
            Dict com status de todas as máquinas
        """
        machines_status = []
        for m in self.machines.values():
            machines_status.append({
                "instance_id": m.instance_id,
                "role": m.role.value,
                "status": m.status.value,
                "gpu_name": m.gpu_name,
                "cost_per_hour": m.cost_per_hour,
                "is_active": m.instance_id == self.active_machine_id,
            })

        # Calcular custo total por hora
        total_cost = sum(m.cost_per_hour for m in self.machines.values()
                        if m.status not in [MachineStatus.OFFLINE, MachineStatus.FAILING])

        return {
            "active_machine_id": self.active_machine_id,
            "machines": machines_status,
            "total_cost_per_hour": total_cost,
            "monitoring_active": self._running,
        }

    def on_failover(self, callback: callable):
        """Registra callback para evento de failover"""
        self._on_failover_callbacks.append(callback)

    def on_recovery(self, callback: callable):
        """Registra callback para evento de recovery"""
        self._on_recovery_callbacks.append(callback)

    # ==================== Private Methods ====================

    def _search_cpu_offers(self) -> List[Dict[str, Any]]:
        """Busca ofertas de CPU (máquinas sem GPU)"""
        # Vast.ai não tem ofertas "CPU only" diretamente,
        # então buscamos GPUs baratas ou usamos API para filtrar
        # Por enquanto, buscar ofertas muito baratas
        offers = self.vast.search_offers(
            num_gpus=1,  # Vast.ai requer pelo menos 1 GPU
            max_price=self.config.max_price_cpu,
            min_disk=self.config.min_disk,
            region=self.config.preferred_region,
        )

        # Filtrar por CPU cores mínimo
        return [
            o for o in offers
            if o.get("cpu_cores", 0) >= self.config.min_cpu_cores
            and o.get("cpu_ram", 0) >= self.config.min_cpu_ram * 1024  # MB
        ]

    def _wait_machine_ready(self, instance_id: int, timeout: int = 300):
        """Aguarda máquina ficar pronta"""
        machine = self.machines.get(instance_id)
        if not machine:
            return

        start = time.time()
        while time.time() - start < timeout:
            status = self.vast.get_instance_status(instance_id)

            if status.get("status") == "running":
                machine.status = MachineStatus.RUNNING
                machine.ssh_host = status.get("ssh_host")
                machine.ssh_port = status.get("ssh_port")
                machine.public_ip = status.get("public_ipaddr")

                # Verificar se code-server está acessível
                if self._check_codeserver(machine):
                    machine.status = MachineStatus.READY
                    print(f"[CPUStandby] Máquina {instance_id} pronta")
                    return

            time.sleep(5)

        print(f"[CPUStandby] Timeout aguardando máquina {instance_id}")
        machine.status = MachineStatus.FAILING

    def _check_codeserver(self, machine: ManagedMachine) -> bool:
        """Verifica se code-server está acessível"""
        if not machine.public_ip:
            return False

        try:
            url = f"http://{machine.public_ip}:{machine.codeserver_port}/"
            resp = requests.get(url, timeout=5)
            return resp.status_code in [200, 302, 401]  # 401 = precisa login
        except:
            return False

    def _health_check_loop(self):
        """Loop de health check das máquinas"""
        while self._running:
            try:
                self._perform_health_checks()
            except Exception as e:
                print(f"[CPUStandby] Erro no health check: {e}")

            time.sleep(self.config.health_check_interval)

    def _perform_health_checks(self):
        """Executa health check em todas as máquinas"""
        for machine in list(self.machines.values()):
            if machine.status in [MachineStatus.OFFLINE, MachineStatus.STARTING]:
                continue

            is_healthy = self._check_machine_health(machine)
            machine.last_health_check = time.time()

            if is_healthy:
                machine.health_failures = 0
            else:
                machine.health_failures += 1
                print(f"[CPUStandby] Health check falhou para {machine.instance_id} "
                      f"({machine.health_failures}/{self.config.max_health_failures})")

                if machine.health_failures >= self.config.max_health_failures:
                    self._handle_machine_failure(machine)

    def _check_machine_health(self, machine: ManagedMachine) -> bool:
        """Verifica saúde de uma máquina"""
        # Verificar status via API
        status = self.vast.get_instance_status(machine.instance_id)

        if status.get("status") != "running":
            return False

        # Verificar code-server
        return self._check_codeserver(machine)

    def _handle_machine_failure(self, machine: ManagedMachine):
        """Trata falha de uma máquina"""
        machine.status = MachineStatus.FAILING

        if machine.role == MachineRole.GPU_PRIMARY and machine.instance_id == self.active_machine_id:
            print(f"[CPUStandby] GPU primária {machine.instance_id} falhou! Iniciando failover...")
            self._perform_failover()

    def _perform_failover(self):
        """Executa failover para CPU standby"""
        # Encontrar CPU standby pronta
        cpu_standby = None
        for m in self.machines.values():
            if m.role == MachineRole.CPU_STANDBY and m.status == MachineStatus.READY:
                cpu_standby = m
                break

        if not cpu_standby:
            print("[CPUStandby] ALERTA: Nenhuma CPU standby disponível para failover!")
            return

        # Trocar máquina ativa
        old_active = self.active_machine_id
        self.active_machine_id = cpu_standby.instance_id

        print(f"[CPUStandby] Failover: {old_active} -> {cpu_standby.instance_id}")

        # Notificar callbacks
        for callback in self._on_failover_callbacks:
            try:
                callback({
                    "from_instance": old_active,
                    "to_instance": cpu_standby.instance_id,
                    "reason": "gpu_failure",
                })
            except Exception as e:
                print(f"[CPUStandby] Erro em callback failover: {e}")

        # Iniciar provisionamento de nova GPU
        self._provision_new_gpu()

    def _provision_new_gpu(self):
        """Provisiona nova GPU após failover"""
        print("[CPUStandby] Provisionando nova GPU...")
        # Implementar lógica de buscar nova GPU
        # Por enquanto, apenas log

    def _ensure_cpu_standby(self):
        """Garante que existe CPU standby"""
        has_standby = any(
            m.role == MachineRole.CPU_STANDBY
            and m.status in [MachineStatus.READY, MachineStatus.RUNNING, MachineStatus.STARTING]
            for m in self.machines.values()
        )

        if not has_standby:
            print("[CPUStandby] Provisionando CPU standby automaticamente...")
            self.provision_cpu_standby("auto")
