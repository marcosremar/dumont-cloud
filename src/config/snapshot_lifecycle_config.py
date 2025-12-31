"""
Snapshot Lifecycle Config - Configuracoes de ciclo de vida de snapshots do Dumont Cloud.

Define as politicas de retencao de snapshots:
1. Retencao padrao (default: 7 dias)
2. Keep-forever flag para snapshots permanentes
3. Agendamento de cleanup automatico

O usuario pode configurar retencao global ou por instancia.
"""
import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicyConfig:
    """Configuracao de politica de retencao"""
    enabled: bool = True                          # Retencao habilitada por padrao
    retention_days: int = 7                       # Dias de retencao padrao
    min_snapshots_to_keep: int = 1                # Minimo de snapshots a manter
    max_snapshots_per_instance: int = 100         # Maximo de snapshots por instancia
    delete_on_instance_termination: bool = False  # Deletar snapshots quando instancia termina


@dataclass
class CleanupScheduleConfig:
    """Configuracao do agendamento de cleanup"""
    enabled: bool = True                          # Cleanup automatico habilitado
    schedule_cron: str = "0 2 * * *"              # Executa as 2:00 AM diariamente
    interval_hours: int = 24                      # Intervalo entre execucoes
    batch_size: int = 100                         # Snapshots processados por lote
    dry_run: bool = False                         # Modo dry-run (nao deleta)
    retry_failed: bool = True                     # Retentar deletions falhas
    max_retries: int = 3                          # Maximo de retentativas


@dataclass
class NotificationConfig:
    """Configuracao de notificacoes de cleanup"""
    notify_on_cleanup: bool = True                # Notificar apos cleanup
    notify_on_error: bool = True                  # Notificar em caso de erro
    notify_channels: List[str] = field(
        default_factory=lambda: ["email"]
    )
    include_metrics: bool = True                  # Incluir metricas no relatorio


@dataclass
class SnapshotLifecycleConfig:
    """
    Configuracoes globais de ciclo de vida de snapshots.

    Define as politicas de retencao padrao para todos os snapshots.
    """
    # Retencao padrao em dias (0 ou None = manter indefinidamente)
    default_retention_days: int = 7

    # Configuracoes especificas
    retention: RetentionPolicyConfig = field(default_factory=RetentionPolicyConfig)
    cleanup_schedule: CleanupScheduleConfig = field(default_factory=CleanupScheduleConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)

    # Aplicar automaticamente em novos snapshots
    auto_apply_to_new_snapshots: bool = True

    # Provedores de storage suportados
    supported_providers: List[str] = field(
        default_factory=lambda: ["b2", "r2", "s3"]
    )

    def is_cleanup_enabled(self) -> bool:
        """Verifica se cleanup automatico esta habilitado"""
        return self.retention.enabled and self.cleanup_schedule.enabled

    def get_effective_retention_days(self, override: Optional[int] = None) -> int:
        """
        Retorna o periodo de retencao efetivo.

        Args:
            override: Valor de retencao especifico (sobrescreve padrao)

        Returns:
            Dias de retencao (0 = manter indefinidamente)
        """
        if override is not None and override >= 0:
            return override
        return self.default_retention_days

    def should_keep_forever(self, retention_days: int) -> bool:
        """Verifica se snapshot deve ser mantido indefinidamente"""
        return retention_days == 0

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            'default_retention_days': self.default_retention_days,
            'retention': asdict(self.retention),
            'cleanup_schedule': asdict(self.cleanup_schedule),
            'notifications': asdict(self.notifications),
            'auto_apply_to_new_snapshots': self.auto_apply_to_new_snapshots,
            'supported_providers': self.supported_providers,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SnapshotLifecycleConfig':
        """Cria a partir de dicionario"""
        retention_data = data.get('retention', {})
        cleanup_schedule_data = data.get('cleanup_schedule', {})
        notifications_data = data.get('notifications', {})

        return cls(
            default_retention_days=data.get('default_retention_days', 7),
            retention=RetentionPolicyConfig(**retention_data) if retention_data else RetentionPolicyConfig(),
            cleanup_schedule=CleanupScheduleConfig(**cleanup_schedule_data) if cleanup_schedule_data else CleanupScheduleConfig(),
            notifications=NotificationConfig(**notifications_data) if notifications_data else NotificationConfig(),
            auto_apply_to_new_snapshots=data.get('auto_apply_to_new_snapshots', True),
            supported_providers=data.get('supported_providers', ['b2', 'r2', 's3']),
        )


@dataclass
class InstanceSnapshotConfig:
    """
    Configuracao de snapshots por instancia.

    Permite sobrescrever a configuracao global para instancias especificas.
    """
    instance_id: str                               # ID da instancia
    use_global_settings: bool = True               # Usar configuracao global

    # Se use_global_settings = False, usa estas configs:
    retention_days: Optional[int] = None           # Dias de retencao especificos
    keep_forever: bool = False                     # Manter todos snapshots indefinidamente
    cleanup_enabled: bool = True                   # Cleanup habilitado para esta instancia

    # Estatisticas
    total_snapshots: int = 0
    total_storage_bytes: int = 0
    last_snapshot_at: Optional[str] = None
    last_cleanup_at: Optional[str] = None
    snapshots_deleted_total: int = 0
    storage_freed_total_bytes: int = 0

    def get_effective_retention_days(self, global_config: SnapshotLifecycleConfig) -> int:
        """Retorna os dias de retencao efetivos (considerando global ou local)"""
        if self.use_global_settings:
            return global_config.default_retention_days
        if self.keep_forever:
            return 0  # 0 = manter indefinidamente
        return self.retention_days if self.retention_days is not None else global_config.default_retention_days

    def is_cleanup_enabled(self, global_config: SnapshotLifecycleConfig) -> bool:
        """Verifica se cleanup esta habilitado para esta instancia"""
        if self.use_global_settings:
            return global_config.is_cleanup_enabled()
        return self.cleanup_enabled and not self.keep_forever

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InstanceSnapshotConfig':
        """Cria a partir de dicionario"""
        return cls(
            instance_id=data['instance_id'],
            use_global_settings=data.get('use_global_settings', True),
            retention_days=data.get('retention_days'),
            keep_forever=data.get('keep_forever', False),
            cleanup_enabled=data.get('cleanup_enabled', True),
            total_snapshots=data.get('total_snapshots', 0),
            total_storage_bytes=data.get('total_storage_bytes', 0),
            last_snapshot_at=data.get('last_snapshot_at'),
            last_cleanup_at=data.get('last_cleanup_at'),
            snapshots_deleted_total=data.get('snapshots_deleted_total', 0),
            storage_freed_total_bytes=data.get('storage_freed_total_bytes', 0),
        )


class SnapshotLifecycleManager:
    """
    Gerenciador de configuracoes de ciclo de vida de snapshots.

    Singleton que gerencia:
    - Configuracoes globais de retencao
    - Configuracoes por instancia
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
        self._global_config: SnapshotLifecycleConfig = SnapshotLifecycleConfig()
        self._instance_configs: Dict[str, InstanceSnapshotConfig] = {}
        self._config_file = os.path.expanduser("~/.dumont/snapshot_lifecycle.json")

        self._load_config()
        logger.info("SnapshotLifecycleManager initialized")

    def get_global_config(self) -> SnapshotLifecycleConfig:
        """Retorna configuracao global"""
        return self._global_config

    def update_global_config(self, config: SnapshotLifecycleConfig) -> bool:
        """Atualiza configuracao global"""
        self._global_config = config
        self._save_config()
        logger.info(f"Global snapshot lifecycle config updated: retention={config.default_retention_days} days")
        return True

    def get_instance_config(self, instance_id: str) -> InstanceSnapshotConfig:
        """
        Retorna configuracao de uma instancia.
        Se nao existir, cria uma nova com configuracoes globais.
        """
        if instance_id not in self._instance_configs:
            self._instance_configs[instance_id] = InstanceSnapshotConfig(
                instance_id=instance_id,
                use_global_settings=True
            )
        return self._instance_configs[instance_id]

    def update_instance_config(self, config: InstanceSnapshotConfig) -> bool:
        """Atualiza configuracao de uma instancia"""
        self._instance_configs[config.instance_id] = config
        self._save_config()
        logger.info(f"Instance {config.instance_id} snapshot config updated")
        return True

    def delete_instance_config(self, instance_id: str) -> bool:
        """Remove configuracao de uma instancia"""
        if instance_id in self._instance_configs:
            del self._instance_configs[instance_id]
            self._save_config()
            logger.info(f"Instance {instance_id} snapshot config deleted")
        return True

    def list_instance_configs(self) -> Dict[str, InstanceSnapshotConfig]:
        """Lista todas as configuracoes de instancias"""
        return self._instance_configs.copy()

    def get_effective_config(self, instance_id: str) -> Dict[str, Any]:
        """
        Retorna a configuracao efetiva para uma instancia,
        combinando configuracoes globais e locais.
        """
        instance_config = self.get_instance_config(instance_id)
        global_config = self._global_config

        return {
            'instance_id': instance_id,
            'use_global_settings': instance_config.use_global_settings,
            'effective_retention_days': instance_config.get_effective_retention_days(global_config),
            'cleanup_enabled': instance_config.is_cleanup_enabled(global_config),
            'keep_forever': instance_config.keep_forever if not instance_config.use_global_settings else False,
            'retention': {
                'enabled': global_config.retention.enabled,
                'min_snapshots_to_keep': global_config.retention.min_snapshots_to_keep,
                'max_snapshots_per_instance': global_config.retention.max_snapshots_per_instance,
            },
            'cleanup_schedule': {
                'enabled': global_config.cleanup_schedule.enabled,
                'schedule_cron': global_config.cleanup_schedule.schedule_cron,
                'interval_hours': global_config.cleanup_schedule.interval_hours,
            },
            'stats': {
                'total_snapshots': instance_config.total_snapshots,
                'total_storage_bytes': instance_config.total_storage_bytes,
                'last_snapshot_at': instance_config.last_snapshot_at,
                'last_cleanup_at': instance_config.last_cleanup_at,
                'snapshots_deleted_total': instance_config.snapshots_deleted_total,
                'storage_freed_total_bytes': instance_config.storage_freed_total_bytes,
            }
        }

    def _load_config(self):
        """Carrega configuracoes do disco"""
        if not os.path.exists(self._config_file):
            logger.info("No snapshot lifecycle config file found, using defaults")
            return

        try:
            with open(self._config_file, 'r') as f:
                data = json.load(f)

            # Carregar configuracao global
            if 'global_config' in data:
                self._global_config = SnapshotLifecycleConfig.from_dict(data['global_config'])

            # Carregar configuracoes por instancia
            if 'instance_configs' in data:
                for instance_id, config_data in data['instance_configs'].items():
                    self._instance_configs[instance_id] = InstanceSnapshotConfig.from_dict(config_data)

            logger.info(f"Loaded snapshot lifecycle config: {len(self._instance_configs)} instance configs")

        except Exception as e:
            logger.error(f"Failed to load snapshot lifecycle config: {e}")

    def _save_config(self):
        """Salva configuracoes no disco"""
        os.makedirs(os.path.dirname(self._config_file), exist_ok=True)

        try:
            data = {
                'global_config': self._global_config.to_dict(),
                'instance_configs': {
                    instance_id: config.to_dict()
                    for instance_id, config in self._instance_configs.items()
                }
            }

            with open(self._config_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("Snapshot lifecycle config saved")

        except Exception as e:
            logger.error(f"Failed to save snapshot lifecycle config: {e}")


# Singleton instance
_snapshot_lifecycle_manager: Optional[SnapshotLifecycleManager] = None


def get_snapshot_lifecycle_manager() -> SnapshotLifecycleManager:
    """Retorna a instancia global do SnapshotLifecycleManager"""
    global _snapshot_lifecycle_manager
    if _snapshot_lifecycle_manager is None:
        _snapshot_lifecycle_manager = SnapshotLifecycleManager()
    return _snapshot_lifecycle_manager
