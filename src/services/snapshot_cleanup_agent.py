"""
Agente de limpeza automatica de snapshots.

Executa limpeza periodica de snapshots expirados:
- Identifica snapshots que excederam o periodo de retencao
- Respeita a flag keep_forever para snapshots permanentes
- Deleta snapshots do storage (B2, R2, S3)
- Registra todas as operacoes em audit log
- Atualiza metricas de cleanup
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Callable, Protocol

from src.services.agent_manager import Agent
from src.config.snapshot_lifecycle_config import (
    SnapshotLifecycleConfig,
    SnapshotLifecycleManager,
    get_snapshot_lifecycle_manager,
)
from src.models.snapshot_metadata import (
    SnapshotMetadata,
    SnapshotStatus,
    DeletionReason,
)

logger = logging.getLogger(__name__)


class StorageProviderProtocol(Protocol):
    """
    Protocolo para provedores de storage.

    Define a interface que provedores de storage (B2, R2, S3) devem implementar.
    Usado para injecao de dependencia e testes.
    """

    def delete_file(self, remote_path: str) -> bool:
        """
        Deleta um arquivo do storage.

        Args:
            remote_path: Caminho remoto do arquivo

        Returns:
            True se deletado com sucesso, False caso contrario
        """
        ...


def get_storage_provider_for_snapshot(
    snapshot: SnapshotMetadata,
) -> Optional[StorageProviderProtocol]:
    """
    Obtem o provider de storage apropriado para um snapshot.

    Usa lazy import para evitar dependencias circulares.

    Args:
        snapshot: Metadados do snapshot

    Returns:
        StorageProvider apropriado ou None se nao configurado
    """
    try:
        from src.storage.storage_provider import (
            StorageConfig,
            create_storage_provider,
        )
        from src.storage.b2_native_provider import B2NativeProvider
        import os

        provider_type = snapshot.storage_provider or "b2"

        # B2 usa provider nativo (mais confiavel)
        if provider_type == "b2":
            config = StorageConfig(
                provider="b2",
                endpoint=os.getenv("B2_ENDPOINT", "https://s3.us-west-004.backblazeb2.com"),
                bucket=os.getenv("B2_BUCKET", ""),
                access_key=os.getenv("B2_KEY_ID", ""),
                secret_key=os.getenv("B2_APPLICATION_KEY", ""),
                region=os.getenv("B2_REGION", "us-west-004"),
            )
            return B2NativeProvider(config)

        # R2, S3, Wasabi usam S5cmd provider
        elif provider_type in ["r2", "s3", "wasabi"]:
            if provider_type == "r2":
                account_id = os.getenv("R2_ACCOUNT_ID", "")
                config = StorageConfig(
                    provider="r2",
                    endpoint=f"https://{account_id}.r2.cloudflarestorage.com",
                    bucket=os.getenv("R2_BUCKET", ""),
                    access_key=os.getenv("R2_ACCESS_KEY", ""),
                    secret_key=os.getenv("R2_SECRET_KEY", ""),
                    region="auto",
                )
            elif provider_type == "wasabi":
                region = os.getenv("WASABI_REGION", "us-east-1")
                config = StorageConfig(
                    provider="wasabi",
                    endpoint=f"https://s3.{region}.wasabisys.com",
                    bucket=os.getenv("WASABI_BUCKET", ""),
                    access_key=os.getenv("WASABI_ACCESS_KEY", ""),
                    secret_key=os.getenv("WASABI_SECRET_KEY", ""),
                    region=region,
                )
            else:  # s3
                region = os.getenv("AWS_REGION", "us-east-1")
                config = StorageConfig(
                    provider="s3",
                    endpoint=f"https://s3.{region}.amazonaws.com",
                    bucket=os.getenv("AWS_BUCKET", ""),
                    access_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
                    secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
                    region=region,
                )
            return create_storage_provider(config)

        else:
            logger.warning(f"Provider de storage desconhecido: {provider_type}")
            return None

    except ImportError as e:
        logger.warning(f"Nao foi possivel importar modulos de storage: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao criar provider de storage: {e}")
        return None


class SnapshotRepository(ABC):
    """
    Interface abstrata para repositorio de snapshots.

    Permite injecao de dependencia para testes e diferentes backends
    de armazenamento de metadados de snapshots.
    """

    @abstractmethod
    def get_all_active_snapshots(self) -> List[SnapshotMetadata]:
        """
        Retorna todos os snapshots ativos.

        Returns:
            Lista de metadados de snapshots ativos
        """
        pass

    @abstractmethod
    def get_snapshots_by_instance(self, instance_id: str) -> List[SnapshotMetadata]:
        """
        Retorna snapshots de uma instancia especifica.

        Args:
            instance_id: ID da instancia

        Returns:
            Lista de metadados de snapshots
        """
        pass

    @abstractmethod
    def update_snapshot(self, snapshot: SnapshotMetadata) -> bool:
        """
        Atualiza metadados de um snapshot.

        Args:
            snapshot: Metadados atualizados

        Returns:
            True se atualizado com sucesso
        """
        pass


class InMemorySnapshotRepository(SnapshotRepository):
    """
    Repositorio de snapshots em memoria.

    Usado para testes e desenvolvimento.
    """

    def __init__(self, snapshots: Optional[List[SnapshotMetadata]] = None):
        self._snapshots: Dict[str, SnapshotMetadata] = {}
        if snapshots:
            for s in snapshots:
                self._snapshots[s.snapshot_id] = s

    def add_snapshot(self, snapshot: SnapshotMetadata) -> None:
        """Adiciona um snapshot ao repositorio."""
        self._snapshots[snapshot.snapshot_id] = snapshot

    def get_all_active_snapshots(self) -> List[SnapshotMetadata]:
        """Retorna todos os snapshots ativos."""
        return [
            s for s in self._snapshots.values()
            if s.status == SnapshotStatus.ACTIVE
        ]

    def get_snapshots_by_instance(self, instance_id: str) -> List[SnapshotMetadata]:
        """Retorna snapshots de uma instancia especifica."""
        return [
            s for s in self._snapshots.values()
            if s.instance_id == instance_id and s.status == SnapshotStatus.ACTIVE
        ]

    def update_snapshot(self, snapshot: SnapshotMetadata) -> bool:
        """Atualiza metadados de um snapshot."""
        if snapshot.snapshot_id in self._snapshots:
            self._snapshots[snapshot.snapshot_id] = snapshot
            return True
        return False

    def get_snapshot(self, snapshot_id: str) -> Optional[SnapshotMetadata]:
        """Retorna um snapshot pelo ID."""
        return self._snapshots.get(snapshot_id)

    def clear(self) -> None:
        """Limpa todos os snapshots."""
        self._snapshots.clear()


class SnapshotCleanupAgent(Agent):
    """
    Agente que executa limpeza automatica de snapshots expirados.

    Roda em background, verificando periodicamente por snapshots que
    excederam o periodo de retencao e deletando-os do storage.
    """

    # Configuracoes de retry para delecao de storage
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_BASE_DELAY = 1.0  # segundos
    DEFAULT_RETRY_MAX_DELAY = 30.0  # segundos

    def __init__(
        self,
        interval_hours: int = 24,
        dry_run: bool = False,
        batch_size: int = 100,
        snapshot_repository: Optional[SnapshotRepository] = None,
        lifecycle_manager: Optional[SnapshotLifecycleManager] = None,
        storage_provider_factory: Optional[Callable[[SnapshotMetadata], Optional[StorageProviderProtocol]]] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
        retry_max_delay: float = DEFAULT_RETRY_MAX_DELAY,
    ):
        """
        Inicializa o agente de limpeza de snapshots.

        Args:
            interval_hours: Intervalo entre ciclos de limpeza em horas (padrao: 24)
            dry_run: Se True, apenas simula a limpeza sem deletar (padrao: False)
            batch_size: Quantidade de snapshots a processar por lote (padrao: 100)
            snapshot_repository: Repositorio de snapshots (injecao de dependencia)
            lifecycle_manager: Manager de lifecycle (injecao de dependencia)
            storage_provider_factory: Factory para criar providers de storage (injecao de dependencia)
            max_retries: Numero maximo de tentativas de delecao (padrao: 3)
            retry_base_delay: Delay base para retry exponencial em segundos (padrao: 1.0)
            retry_max_delay: Delay maximo para retry exponencial em segundos (padrao: 30.0)
        """
        super().__init__(name="SnapshotCleanup")
        self.interval_seconds = interval_hours * 3600
        self.dry_run = dry_run
        self.batch_size = batch_size

        # Injecao de dependencia para repositorio de snapshots
        self._snapshot_repository: Optional[SnapshotRepository] = snapshot_repository

        # Lifecycle manager para configuracoes
        self._lifecycle_manager: Optional[SnapshotLifecycleManager] = lifecycle_manager

        # Factory para criar providers de storage (permite injecao para testes)
        self._storage_provider_factory = storage_provider_factory or get_storage_provider_for_snapshot

        # Configuracoes de retry
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay

        # Estatisticas do ciclo atual
        self.current_cycle_stats: Dict[str, Any] = {
            'snapshots_identified': 0,
            'snapshots_deleted': 0,
            'snapshots_failed': 0,
            'storage_freed_bytes': 0,
            'started_at': None,
            'completed_at': None,
        }

        # Cache de snapshots para cleanup
        self._snapshots_to_cleanup: List[SnapshotMetadata] = []

    @property
    def lifecycle_manager(self) -> SnapshotLifecycleManager:
        """Lazy load do lifecycle manager."""
        if self._lifecycle_manager is None:
            self._lifecycle_manager = get_snapshot_lifecycle_manager()
        return self._lifecycle_manager

    @property
    def snapshot_repository(self) -> Optional[SnapshotRepository]:
        """Retorna o repositorio de snapshots."""
        return self._snapshot_repository

    def set_snapshot_repository(self, repository: SnapshotRepository) -> None:
        """
        Define o repositorio de snapshots.

        Args:
            repository: Repositorio a ser usado
        """
        self._snapshot_repository = repository

    def run(self):
        """Loop principal do agente."""
        logger.info(f"SnapshotCleanupAgent iniciando: intervalo={self.interval_seconds/3600}h, "
                    f"dry_run={self.dry_run}, batch_size={self.batch_size}")

        while self.running:
            try:
                self._cleanup_cycle()
            except Exception as e:
                logger.error(f"Erro no ciclo de limpeza: {e}", exc_info=True)

            if self.running:
                logger.info(f"Proximo ciclo de limpeza em {self.interval_seconds/3600} horas...")
                self.sleep(self.interval_seconds)

    def _cleanup_cycle(self):
        """Executa um ciclo completo de limpeza de snapshots."""
        logger.info("=" * 60)
        logger.info(f"Ciclo de limpeza de snapshots - {datetime.now(timezone.utc).isoformat()}")
        logger.info("=" * 60)

        # Resetar estatisticas do ciclo
        self.current_cycle_stats = {
            'snapshots_identified': 0,
            'snapshots_deleted': 0,
            'snapshots_failed': 0,
            'storage_freed_bytes': 0,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': None,
        }

        # Verificar se cleanup esta habilitado
        global_config = self.lifecycle_manager.get_global_config()
        if not global_config.is_cleanup_enabled():
            logger.info("Cleanup automatico esta desabilitado. Pulando ciclo.")
            return

        # 1. Identificar snapshots expirados
        expired_snapshots = self._identify_expired_snapshots()
        self.current_cycle_stats['snapshots_identified'] = len(expired_snapshots)

        if not expired_snapshots:
            logger.info("Nenhum snapshot expirado encontrado")
            self.current_cycle_stats['completed_at'] = datetime.now(timezone.utc).isoformat()
            return

        logger.info(f"Encontrados {len(expired_snapshots)} snapshots expirados para limpeza")

        # 2. Processar snapshots em lotes
        for i in range(0, len(expired_snapshots), self.batch_size):
            batch = expired_snapshots[i:i + self.batch_size]
            logger.info(f"Processando lote {i//self.batch_size + 1} ({len(batch)} snapshots)")

            for snapshot in batch:
                if not self.running:
                    logger.info("Agente interrompido durante limpeza")
                    break

                try:
                    success = self._delete_snapshot(snapshot)
                    if success:
                        self.current_cycle_stats['snapshots_deleted'] += 1
                        self.current_cycle_stats['storage_freed_bytes'] += snapshot.size_bytes
                    else:
                        self.current_cycle_stats['snapshots_failed'] += 1
                except Exception as e:
                    logger.error(f"Erro ao deletar snapshot {snapshot.snapshot_id}: {e}")
                    self.current_cycle_stats['snapshots_failed'] += 1

        # Finalizar ciclo
        self.current_cycle_stats['completed_at'] = datetime.now(timezone.utc).isoformat()
        self._log_cycle_summary()

    def _identify_expired_snapshots(self) -> List[SnapshotMetadata]:
        """
        Identifica snapshots que expiraram e devem ser deletados.

        Logica de identificacao:
        1. Obtem todos os snapshots ativos do repositorio
        2. Para cada snapshot, verifica se expirou baseado em:
           - keep_forever: Se True, nunca expira
           - retention_days do snapshot (ou da instancia/global)
           - Idade do snapshot (now - created_at)
        3. Retorna lista de snapshots expirados ordenada por idade (mais antigos primeiro)

        Returns:
            Lista de snapshots expirados
        """
        expired: List[SnapshotMetadata] = []

        # Se nao ha repositorio configurado, nao ha snapshots para processar
        if self._snapshot_repository is None:
            logger.warning("Nenhum repositorio de snapshots configurado")
            return expired

        # Obter configuracao global
        global_config = self.lifecycle_manager.get_global_config()
        default_retention = global_config.default_retention_days

        # Obter todos os snapshots ativos do repositorio
        all_snapshots = self._snapshot_repository.get_all_active_snapshots()
        logger.debug(f"Verificando {len(all_snapshots)} snapshots ativos")

        # Cache de configuracoes por instancia para evitar lookups repetidos
        instance_config_cache: Dict[str, Any] = {}

        for snapshot in all_snapshots:
            # 1. Verificar keep_forever - nunca expira
            if snapshot.keep_forever:
                logger.debug(f"Snapshot {snapshot.snapshot_id} tem keep_forever=True, ignorando")
                continue

            # 2. Verificar status - apenas snapshots ACTIVE podem expirar
            if snapshot.status != SnapshotStatus.ACTIVE:
                logger.debug(f"Snapshot {snapshot.snapshot_id} nao esta ativo (status={snapshot.status.value})")
                continue

            # 3. Obter configuracao de retencao efetiva
            effective_retention = self._get_effective_retention_for_snapshot(
                snapshot, global_config, instance_config_cache
            )

            # 4. Verificar se snapshot expirou
            if effective_retention == 0:
                # retention_days=0 significa "manter indefinidamente"
                logger.debug(f"Snapshot {snapshot.snapshot_id} tem retencao=0 (manter indefinidamente)")
                continue

            if snapshot.is_expired(effective_retention):
                age_days = snapshot.get_age_days()
                logger.debug(f"Snapshot {snapshot.snapshot_id} expirou "
                            f"(idade={age_days} dias, retencao={effective_retention} dias)")
                expired.append(snapshot)

        # Ordenar por idade (mais antigos primeiro) para deletar os mais antigos primeiro
        expired.sort(key=lambda s: s.created_at)

        logger.info(f"Identificados {len(expired)} snapshots expirados de {len(all_snapshots)} ativos")
        return expired

    def _get_effective_retention_for_snapshot(
        self,
        snapshot: SnapshotMetadata,
        global_config: SnapshotLifecycleConfig,
        instance_config_cache: Dict[str, Any],
    ) -> int:
        """
        Calcula o periodo de retencao efetivo para um snapshot.

        Ordem de precedencia:
        1. retention_days do snapshot (se definido)
        2. retention_days da instancia (se configurado)
        3. retention_days global (default: 7)

        Args:
            snapshot: Metadados do snapshot
            global_config: Configuracao global
            instance_config_cache: Cache de configuracoes de instancia

        Returns:
            Dias de retencao efetivos (0 = manter indefinidamente)
        """
        # 1. Verificar se snapshot tem retention_days proprio
        if snapshot.retention_days is not None:
            return snapshot.retention_days

        # 2. Verificar configuracao da instancia
        instance_id = snapshot.instance_id
        if instance_id:
            # Usar cache para evitar lookups repetidos
            if instance_id not in instance_config_cache:
                instance_config = self.lifecycle_manager.get_instance_config(instance_id)
                instance_config_cache[instance_id] = {
                    'config': instance_config,
                    'effective_retention': instance_config.get_effective_retention_days(global_config),
                    'cleanup_enabled': instance_config.is_cleanup_enabled(global_config),
                }

            cached = instance_config_cache[instance_id]

            # Verificar se cleanup esta habilitado para esta instancia
            if not cached['cleanup_enabled']:
                logger.debug(f"Cleanup desabilitado para instancia {instance_id}")
                return 0  # 0 = nao deletar

            return cached['effective_retention']

        # 3. Usar retencao global
        return global_config.default_retention_days

    def _get_instance_snapshots(self, instance_id: str) -> List[SnapshotMetadata]:
        """
        Obtem snapshots de uma instancia.

        Args:
            instance_id: ID da instancia

        Returns:
            Lista de metadados de snapshots
        """
        if self._snapshot_repository is None:
            return []
        return self._snapshot_repository.get_snapshots_by_instance(instance_id)

    def _delete_snapshot(self, snapshot: SnapshotMetadata) -> bool:
        """
        Deleta um snapshot do storage.

        Implementa delecao com suporte a multiplos providers (B2, R2, S3)
        e retry com backoff exponencial em caso de falha.

        Args:
            snapshot: Metadados do snapshot a deletar

        Returns:
            True se deletado com sucesso
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Deletaria snapshot {snapshot.snapshot_id} "
                       f"({snapshot.size_bytes} bytes)")
            return True

        try:
            # Marcar para delecao
            snapshot.mark_for_deletion(DeletionReason.EXPIRED)

            # Atualizar repositorio com status pending_deletion
            if self._snapshot_repository:
                self._snapshot_repository.update_snapshot(snapshot)

            # Deletar do storage com retry
            storage_deleted = self._delete_from_storage_with_retry(snapshot)

            if not storage_deleted:
                # Falha na delecao do storage - nao marcar como deletado
                error_msg = f"Falha ao deletar do storage apos {self.max_retries} tentativas"
                snapshot.mark_deletion_failed(error_msg)

                if self._snapshot_repository:
                    self._snapshot_repository.update_snapshot(snapshot)

                logger.error(f"Falha ao deletar snapshot {snapshot.snapshot_id}: {error_msg}")
                return False

            # Marcar como deletado
            snapshot.mark_deleted()

            # Atualizar repositorio com status deleted
            if self._snapshot_repository:
                self._snapshot_repository.update_snapshot(snapshot)

            logger.info(f"Snapshot {snapshot.snapshot_id} deletado com sucesso "
                       f"({snapshot.size_bytes} bytes liberados)")

            return True

        except Exception as e:
            error_msg = str(e)
            snapshot.mark_deletion_failed(error_msg)

            # Atualizar repositorio com status failed
            if self._snapshot_repository:
                self._snapshot_repository.update_snapshot(snapshot)

            logger.error(f"Falha ao deletar snapshot {snapshot.snapshot_id}: {error_msg}")
            return False

    def _delete_from_storage_with_retry(self, snapshot: SnapshotMetadata) -> bool:
        """
        Deleta snapshot do storage com retry e backoff exponencial.

        Args:
            snapshot: Metadados do snapshot a deletar

        Returns:
            True se deletado com sucesso, False apos esgotar retries
        """
        # Obter provider de storage
        provider = self._storage_provider_factory(snapshot)

        if provider is None:
            logger.warning(f"Nenhum provider de storage configurado para {snapshot.storage_provider}")
            # Se nao ha provider, considera como sucesso (snapshot pode estar em storage local)
            return True

        # Construir path do snapshot no storage
        storage_path = self._get_storage_path(snapshot)
        if not storage_path:
            logger.warning(f"Snapshot {snapshot.snapshot_id} nao tem storage_path definido")
            return True

        # Tentar deletar com retry exponencial
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Tentativa {attempt + 1}/{self.max_retries} de deletar "
                            f"{snapshot.snapshot_id} do storage")

                success = provider.delete_file(storage_path)

                if success:
                    logger.info(f"Arquivo {storage_path} deletado do storage "
                               f"{snapshot.storage_provider}")
                    return True
                else:
                    logger.warning(f"Provider retornou False ao deletar {storage_path}")
                    last_error = "Provider returned False"

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Erro ao deletar {storage_path} (tentativa {attempt + 1}): {e}")

            # Calcular delay com backoff exponencial
            if attempt < self.max_retries - 1:
                delay = min(
                    self.retry_base_delay * (2 ** attempt),
                    self.retry_max_delay
                )
                logger.debug(f"Aguardando {delay:.1f}s antes da proxima tentativa")
                time.sleep(delay)

        logger.error(f"Falha ao deletar {storage_path} apos {self.max_retries} tentativas: {last_error}")
        return False

    def _get_storage_path(self, snapshot: SnapshotMetadata) -> Optional[str]:
        """
        Obtem o path do snapshot no storage.

        Args:
            snapshot: Metadados do snapshot

        Returns:
            Path no storage ou None se nao definido
        """
        # Usar storage_path se definido
        if snapshot.storage_path:
            return snapshot.storage_path

        # Fallback: construir path padrao
        if snapshot.instance_id and snapshot.snapshot_id:
            return f"snapshots/{snapshot.instance_id}/{snapshot.snapshot_id}"

        return None

    def _log_cycle_summary(self):
        """Loga resumo do ciclo de limpeza."""
        stats = self.current_cycle_stats
        storage_freed_mb = stats['storage_freed_bytes'] / (1024 * 1024)

        logger.info("=" * 60)
        logger.info("Resumo do ciclo de limpeza:")
        logger.info(f"  - Snapshots identificados: {stats['snapshots_identified']}")
        logger.info(f"  - Snapshots deletados: {stats['snapshots_deleted']}")
        logger.info(f"  - Snapshots com falha: {stats['snapshots_failed']}")
        logger.info(f"  - Storage liberado: {storage_freed_mb:.2f} MB")
        logger.info(f"  - Iniciado em: {stats['started_at']}")
        logger.info(f"  - Concluido em: {stats['completed_at']}")
        logger.info("=" * 60)

    def trigger_manual_cleanup(self, dry_run: Optional[bool] = None) -> Dict[str, Any]:
        """
        Dispara uma limpeza manual fora do ciclo regular.

        Args:
            dry_run: Se True, apenas simula (sobrescreve configuracao do agente)

        Returns:
            Estatisticas do ciclo de limpeza
        """
        original_dry_run = self.dry_run
        if dry_run is not None:
            self.dry_run = dry_run

        try:
            self._cleanup_cycle()
            return self.current_cycle_stats.copy()
        finally:
            self.dry_run = original_dry_run

    def get_cleanup_stats(self) -> Dict[str, Any]:
        """
        Retorna estatisticas do ultimo ciclo de limpeza.

        Returns:
            Estatisticas do ciclo
        """
        return self.current_cycle_stats.copy()

    def set_dry_run(self, enabled: bool):
        """
        Define modo dry-run.

        Args:
            enabled: Se True, apenas simula limpeza
        """
        self.dry_run = enabled
        logger.info(f"Modo dry-run {'habilitado' if enabled else 'desabilitado'}")
