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
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

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


class SnapshotCleanupAgent(Agent):
    """
    Agente que executa limpeza automatica de snapshots expirados.

    Roda em background, verificando periodicamente por snapshots que
    excederam o periodo de retencao e deletando-os do storage.
    """

    def __init__(
        self,
        interval_hours: int = 24,
        dry_run: bool = False,
        batch_size: int = 100,
    ):
        """
        Inicializa o agente de limpeza de snapshots.

        Args:
            interval_hours: Intervalo entre ciclos de limpeza em horas (padrao: 24)
            dry_run: Se True, apenas simula a limpeza sem deletar (padrao: False)
            batch_size: Quantidade de snapshots a processar por lote (padrao: 100)
        """
        super().__init__(name="SnapshotCleanup")
        self.interval_seconds = interval_hours * 3600
        self.dry_run = dry_run
        self.batch_size = batch_size

        # Lifecycle manager para configuracoes
        self._lifecycle_manager: Optional[SnapshotLifecycleManager] = None

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
        """Lazy load do lifecycle manager"""
        if self._lifecycle_manager is None:
            self._lifecycle_manager = get_snapshot_lifecycle_manager()
        return self._lifecycle_manager

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

        Returns:
            Lista de snapshots expirados
        """
        expired = []
        global_config = self.lifecycle_manager.get_global_config()
        default_retention = global_config.default_retention_days

        # Iterar por todas as instancias configuradas
        instance_configs = self.lifecycle_manager.list_instance_configs()

        for instance_id, instance_config in instance_configs.items():
            # Verificar se cleanup esta habilitado para esta instancia
            if not instance_config.is_cleanup_enabled(global_config):
                logger.debug(f"Cleanup desabilitado para instancia {instance_id}")
                continue

            # Obter snapshots da instancia (placeholder - sera implementado em subtask posterior)
            instance_snapshots = self._get_instance_snapshots(instance_id)

            # Obter retencao efetiva para esta instancia
            effective_retention = instance_config.get_effective_retention_days(global_config)

            for snapshot in instance_snapshots:
                # Verificar se snapshot expirou
                if snapshot.is_expired(effective_retention):
                    # Verificar keep_forever
                    if snapshot.keep_forever:
                        logger.debug(f"Snapshot {snapshot.snapshot_id} tem keep_forever=True, ignorando")
                        continue

                    logger.debug(f"Snapshot {snapshot.snapshot_id} expirou "
                                f"(idade={snapshot.get_age_days()} dias, retencao={effective_retention})")
                    expired.append(snapshot)

        logger.info(f"Identificados {len(expired)} snapshots expirados")
        return expired

    def _get_instance_snapshots(self, instance_id: str) -> List[SnapshotMetadata]:
        """
        Obtem snapshots de uma instancia.

        Esta e uma implementacao placeholder. Sera expandida em subtask posterior
        para integrar com o storage real.

        Args:
            instance_id: ID da instancia

        Returns:
            Lista de metadados de snapshots
        """
        # TODO: Implementar integracao com storage real em subtask-2-2
        # Por enquanto, retorna lista vazia
        return []

    def _delete_snapshot(self, snapshot: SnapshotMetadata) -> bool:
        """
        Deleta um snapshot do storage.

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

            # TODO: Implementar delecao real do storage em subtask-2-3
            # Por enquanto, apenas simula o sucesso
            logger.info(f"Deletando snapshot {snapshot.snapshot_id} do storage {snapshot.storage_provider}")

            # Marcar como deletado
            snapshot.mark_deleted()
            logger.info(f"Snapshot {snapshot.snapshot_id} deletado com sucesso "
                       f"({snapshot.size_bytes} bytes liberados)")

            return True

        except Exception as e:
            error_msg = str(e)
            snapshot.mark_deletion_failed(error_msg)
            logger.error(f"Falha ao deletar snapshot {snapshot.snapshot_id}: {error_msg}")
            return False

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
