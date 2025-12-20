"""
Failover Settings - Configuracoes de failover do Dumont Cloud.

Define as estrategias de failover disponiveis:
1. GPU Warm Pool (principal) - Failover em 30-60 segundos
2. CPU Standby (fallback) - Failover em 10-20 minutos

O usuario pode habilitar uma ou ambas estrategias.
"""
import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class FailoverStrategy(str, Enum):
    """Estrategias de failover disponiveis"""
    WARM_POOL = "warm_pool"              # GPU Warm Pool (mesmo host) ~6s
    REGIONAL_VOLUME = "regional_volume"  # Volume Regional + GPU spot ~30-60s
    CPU_STANDBY = "cpu_standby"          # CPU Standby (GCP) ~10-20min
    BOTH = "both"                        # Warm Pool + CPU Standby
    ALL = "all"                          # Todas as estrategias
    DISABLED = "disabled"                # Sem failover


@dataclass
class WarmPoolConfig:
    """Configuracao do GPU Warm Pool"""
    enabled: bool = True                          # Habilitado por padrao
    min_gpus_per_host: int = 2                    # Minimo de GPUs no host
    volume_size_gb: int = 100                     # Tamanho do volume
    auto_provision_standby: bool = True           # Criar GPU standby automaticamente
    fallback_to_cpu_standby: bool = True          # Usar CPU se warm pool falhar
    preferred_gpu_names: List[str] = field(
        default_factory=lambda: ["RTX_4090", "RTX_3090", "A100"]
    )
    health_check_interval_seconds: int = 10       # Intervalo de health check
    failover_timeout_seconds: int = 120           # Timeout do failover
    auto_reprovision_standby: bool = True         # Reprovisionar standby apos failover


@dataclass
class RegionalVolumeConfig:
    """Configuracao do Regional Volume Failover"""
    enabled: bool = True                          # Habilitado por padrao
    volume_size_gb: int = 50                      # Tamanho do volume persistente
    preferred_regions: List[str] = field(
        default_factory=lambda: ["US", "CA", "DE", "PL"]  # Regioes preferidas
    )
    preferred_gpu_names: List[str] = field(
        default_factory=lambda: ["RTX_4090", "RTX_3090", "RTX_4080", "A100"]
    )
    use_spot_instances: bool = True               # Usar instancias spot (mais baratas)
    max_price_per_hour: float = 0.50              # Preco maximo por hora
    min_reliability: float = 0.95                 # Confiabilidade minima do host
    mount_path: str = "/data"                     # Caminho de montagem do volume
    health_check_interval_seconds: int = 10       # Intervalo de health check
    failover_timeout_seconds: int = 120           # Timeout do failover
    auto_provision_volume: bool = True            # Criar volume automaticamente


@dataclass
class CPUStandbyConfig:
    """Configuracao do CPU Standby (GCP)"""
    enabled: bool = True                          # Habilitado por padrao
    gcp_zone: str = "europe-west1-b"              # Zona GCP
    gcp_machine_type: str = "e2-medium"           # Tipo de maquina
    gcp_disk_size_gb: int = 100                   # Tamanho do disco
    gcp_spot: bool = True                         # Usar Spot VM (mais barato)
    sync_interval_seconds: int = 30               # Intervalo de sync
    health_check_interval_seconds: int = 10       # Intervalo de health check
    failover_threshold: int = 3                   # Falhas para acionar failover
    auto_failover: bool = True                    # Failover automatico
    auto_recovery: bool = True                    # Provisionar nova GPU automaticamente
    snapshot_to_cloud: bool = True                # Fazer snapshot para B2/R2


@dataclass
class FailoverSettings:
    """
    Configuracoes globais de failover.

    Define qual estrategia usar por padrao para novas maquinas.
    """
    # Estrategia padrao para novas maquinas
    default_strategy: FailoverStrategy = FailoverStrategy.BOTH

    # Configuracoes especificas de cada estrategia
    warm_pool: WarmPoolConfig = field(default_factory=WarmPoolConfig)
    regional_volume: RegionalVolumeConfig = field(default_factory=RegionalVolumeConfig)
    cpu_standby: CPUStandbyConfig = field(default_factory=CPUStandbyConfig)

    # Aplicar automaticamente em novas maquinas
    auto_apply_to_new_machines: bool = True

    # Notificacoes
    notify_on_failover: bool = True
    notify_channels: List[str] = field(default_factory=lambda: ["email", "slack"])

    def is_warm_pool_enabled(self) -> bool:
        """Verifica se warm pool esta habilitado"""
        return self.default_strategy in [
            FailoverStrategy.WARM_POOL,
            FailoverStrategy.BOTH,
            FailoverStrategy.ALL,
        ] and self.warm_pool.enabled

    def is_regional_volume_enabled(self) -> bool:
        """Verifica se regional volume failover esta habilitado"""
        return self.default_strategy in [
            FailoverStrategy.REGIONAL_VOLUME,
            FailoverStrategy.ALL,
        ] and self.regional_volume.enabled

    def is_cpu_standby_enabled(self) -> bool:
        """Verifica se CPU standby esta habilitado"""
        return self.default_strategy in [
            FailoverStrategy.CPU_STANDBY,
            FailoverStrategy.BOTH,
            FailoverStrategy.ALL,
        ] and self.cpu_standby.enabled

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            'default_strategy': self.default_strategy.value,
            'warm_pool': asdict(self.warm_pool),
            'regional_volume': asdict(self.regional_volume),
            'cpu_standby': asdict(self.cpu_standby),
            'auto_apply_to_new_machines': self.auto_apply_to_new_machines,
            'notify_on_failover': self.notify_on_failover,
            'notify_channels': self.notify_channels,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailoverSettings':
        """Cria a partir de dicionario"""
        warm_pool_data = data.get('warm_pool', {})
        regional_volume_data = data.get('regional_volume', {})
        cpu_standby_data = data.get('cpu_standby', {})

        return cls(
            default_strategy=FailoverStrategy(data.get('default_strategy', 'both')),
            warm_pool=WarmPoolConfig(**warm_pool_data) if warm_pool_data else WarmPoolConfig(),
            regional_volume=RegionalVolumeConfig(**regional_volume_data) if regional_volume_data else RegionalVolumeConfig(),
            cpu_standby=CPUStandbyConfig(**cpu_standby_data) if cpu_standby_data else CPUStandbyConfig(),
            auto_apply_to_new_machines=data.get('auto_apply_to_new_machines', True),
            notify_on_failover=data.get('notify_on_failover', True),
            notify_channels=data.get('notify_channels', ['email', 'slack']),
        )


@dataclass
class MachineFailoverConfig:
    """
    Configuracao de failover por maquina.

    Permite sobrescrever a configuracao global para maquinas especificas.
    """
    machine_id: int                                # ID da maquina (GPU)
    use_global_settings: bool = True               # Usar configuracao global

    # Se use_global_settings = False, usa estas configs:
    strategy: Optional[FailoverStrategy] = None
    warm_pool_enabled: bool = True
    regional_volume_enabled: bool = True
    cpu_standby_enabled: bool = True

    # Estado atual
    warm_pool_active: bool = False
    regional_volume_active: bool = False
    cpu_standby_active: bool = False

    # IDs das instancias de backup
    warm_pool_standby_gpu_id: Optional[int] = None
    warm_pool_volume_id: Optional[int] = None
    regional_volume_id: Optional[int] = None       # ID do volume regional
    regional_volume_region: Optional[str] = None   # Regiao do volume
    cpu_standby_instance_name: Optional[str] = None

    # Estatisticas
    failover_count: int = 0
    last_failover_at: Optional[str] = None
    last_failover_strategy: Optional[str] = None

    def get_effective_strategy(self, global_settings: FailoverSettings) -> FailoverStrategy:
        """Retorna a estrategia efetiva (considerando global ou local)"""
        if self.use_global_settings:
            return global_settings.default_strategy
        return self.strategy or FailoverStrategy.BOTH

    def is_warm_pool_enabled(self, global_settings: FailoverSettings) -> bool:
        """Verifica se warm pool esta habilitado para esta maquina"""
        if self.use_global_settings:
            return global_settings.is_warm_pool_enabled()
        return self.warm_pool_enabled

    def is_cpu_standby_enabled(self, global_settings: FailoverSettings) -> bool:
        """Verifica se CPU standby esta habilitado para esta maquina"""
        if self.use_global_settings:
            return global_settings.is_cpu_standby_enabled()
        return self.cpu_standby_enabled

    def is_regional_volume_enabled(self, global_settings: FailoverSettings) -> bool:
        """Verifica se regional volume failover esta habilitado para esta maquina"""
        if self.use_global_settings:
            return global_settings.is_regional_volume_enabled()
        return self.regional_volume_enabled

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MachineFailoverConfig':
        """Cria a partir de dicionario"""
        strategy = data.get('strategy')
        return cls(
            machine_id=data['machine_id'],
            use_global_settings=data.get('use_global_settings', True),
            strategy=FailoverStrategy(strategy) if strategy else None,
            warm_pool_enabled=data.get('warm_pool_enabled', True),
            regional_volume_enabled=data.get('regional_volume_enabled', True),
            cpu_standby_enabled=data.get('cpu_standby_enabled', True),
            warm_pool_active=data.get('warm_pool_active', False),
            regional_volume_active=data.get('regional_volume_active', False),
            cpu_standby_active=data.get('cpu_standby_active', False),
            warm_pool_standby_gpu_id=data.get('warm_pool_standby_gpu_id'),
            warm_pool_volume_id=data.get('warm_pool_volume_id'),
            regional_volume_id=data.get('regional_volume_id'),
            regional_volume_region=data.get('regional_volume_region'),
            cpu_standby_instance_name=data.get('cpu_standby_instance_name'),
            failover_count=data.get('failover_count', 0),
            last_failover_at=data.get('last_failover_at'),
            last_failover_strategy=data.get('last_failover_strategy'),
        )


class FailoverSettingsManager:
    """
    Gerenciador de configuracoes de failover.

    Singleton que gerencia:
    - Configuracoes globais
    - Configuracoes por maquina
    - Persistencia em disco
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._global_settings: FailoverSettings = FailoverSettings()
        self._machine_configs: Dict[int, MachineFailoverConfig] = {}
        self._config_file = os.path.expanduser("~/.dumont/failover_settings.json")

        self._load_settings()
        logger.info("FailoverSettingsManager initialized")

    def get_global_settings(self) -> FailoverSettings:
        """Retorna configuracoes globais"""
        return self._global_settings

    def update_global_settings(self, settings: FailoverSettings) -> bool:
        """Atualiza configuracoes globais"""
        self._global_settings = settings
        self._save_settings()
        logger.info(f"Global failover settings updated: {settings.default_strategy.value}")
        return True

    def get_machine_config(self, machine_id: int) -> MachineFailoverConfig:
        """
        Retorna configuracao de uma maquina.
        Se nao existir, cria uma nova com configuracoes globais.
        """
        if machine_id not in self._machine_configs:
            self._machine_configs[machine_id] = MachineFailoverConfig(
                machine_id=machine_id,
                use_global_settings=True
            )
        return self._machine_configs[machine_id]

    def update_machine_config(self, config: MachineFailoverConfig) -> bool:
        """Atualiza configuracao de uma maquina"""
        self._machine_configs[config.machine_id] = config
        self._save_settings()
        logger.info(f"Machine {config.machine_id} failover config updated")
        return True

    def delete_machine_config(self, machine_id: int) -> bool:
        """Remove configuracao de uma maquina"""
        if machine_id in self._machine_configs:
            del self._machine_configs[machine_id]
            self._save_settings()
            logger.info(f"Machine {machine_id} failover config deleted")
        return True

    def list_machine_configs(self) -> Dict[int, MachineFailoverConfig]:
        """Lista todas as configuracoes de maquinas"""
        return self._machine_configs.copy()

    def get_effective_config(self, machine_id: int) -> Dict[str, Any]:
        """
        Retorna a configuracao efetiva para uma maquina,
        combinando configuracoes globais e locais.
        """
        machine_config = self.get_machine_config(machine_id)
        global_settings = self._global_settings

        return {
            'machine_id': machine_id,
            'use_global_settings': machine_config.use_global_settings,
            'effective_strategy': machine_config.get_effective_strategy(global_settings).value,
            'warm_pool': {
                'enabled': machine_config.is_warm_pool_enabled(global_settings),
                'active': machine_config.warm_pool_active,
                'standby_gpu_id': machine_config.warm_pool_standby_gpu_id,
                'volume_id': machine_config.warm_pool_volume_id,
                'config': asdict(global_settings.warm_pool) if machine_config.use_global_settings else {
                    'enabled': machine_config.warm_pool_enabled
                }
            },
            'regional_volume': {
                'enabled': machine_config.is_regional_volume_enabled(global_settings),
                'active': machine_config.regional_volume_active,
                'volume_id': machine_config.regional_volume_id,
                'region': machine_config.regional_volume_region,
                'config': asdict(global_settings.regional_volume) if machine_config.use_global_settings else {
                    'enabled': machine_config.regional_volume_enabled
                }
            },
            'cpu_standby': {
                'enabled': machine_config.is_cpu_standby_enabled(global_settings),
                'active': machine_config.cpu_standby_active,
                'instance_name': machine_config.cpu_standby_instance_name,
                'config': asdict(global_settings.cpu_standby) if machine_config.use_global_settings else {
                    'enabled': machine_config.cpu_standby_enabled
                }
            },
            'stats': {
                'failover_count': machine_config.failover_count,
                'last_failover_at': machine_config.last_failover_at,
                'last_failover_strategy': machine_config.last_failover_strategy,
            }
        }

    def _load_settings(self):
        """Carrega configuracoes do disco"""
        if not os.path.exists(self._config_file):
            logger.info("No failover settings file found, using defaults")
            return

        try:
            with open(self._config_file, 'r') as f:
                data = json.load(f)

            # Carregar configuracoes globais
            if 'global_settings' in data:
                self._global_settings = FailoverSettings.from_dict(data['global_settings'])

            # Carregar configuracoes por maquina
            if 'machine_configs' in data:
                for machine_id_str, config_data in data['machine_configs'].items():
                    machine_id = int(machine_id_str)
                    self._machine_configs[machine_id] = MachineFailoverConfig.from_dict(config_data)

            logger.info(f"Loaded failover settings: {len(self._machine_configs)} machine configs")

        except Exception as e:
            logger.error(f"Failed to load failover settings: {e}")

    def _save_settings(self):
        """Salva configuracoes no disco"""
        os.makedirs(os.path.dirname(self._config_file), exist_ok=True)

        try:
            data = {
                'global_settings': self._global_settings.to_dict(),
                'machine_configs': {
                    str(machine_id): config.to_dict()
                    for machine_id, config in self._machine_configs.items()
                }
            }

            with open(self._config_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("Failover settings saved")

        except Exception as e:
            logger.error(f"Failed to save failover settings: {e}")


# Singleton instance
_failover_settings_manager: Optional[FailoverSettingsManager] = None


def get_failover_settings_manager() -> FailoverSettingsManager:
    """Retorna a instancia global do FailoverSettingsManager"""
    global _failover_settings_manager
    if _failover_settings_manager is None:
        _failover_settings_manager = FailoverSettingsManager()
    return _failover_settings_manager
