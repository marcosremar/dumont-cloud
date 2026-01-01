"""
Audit Logger para delecao de snapshots.

Registra todas as operacoes de delecao de snapshots para auditoria,
compliance e troubleshooting:
- timestamp: Data/hora da delecao (UTC)
- snapshot_id: Identificador do snapshot deletado
- user_id: Usuario proprietario do snapshot
- deletion_reason: Motivo da delecao (expired, manual, etc)
- storage_freed_bytes: Espaco liberado em bytes

Logs persistem independentemente dos snapshots deletados.
"""

import enum
import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class AuditEventType(enum.Enum):
    """Tipos de eventos de auditoria"""
    DELETION = "deletion"               # Delecao de snapshot
    DELETION_FAILED = "deletion_failed" # Falha na delecao
    KEEP_FOREVER_SET = "keep_forever_set"       # Flag keep_forever definida
    KEEP_FOREVER_UNSET = "keep_forever_unset"   # Flag keep_forever removida
    RETENTION_CHANGED = "retention_changed"     # Periodo de retencao alterado
    CLEANUP_STARTED = "cleanup_started"         # Ciclo de cleanup iniciado
    CLEANUP_COMPLETED = "cleanup_completed"     # Ciclo de cleanup concluido


class DeletionReason(enum.Enum):
    """Razao para delecao de snapshot (espelhado de snapshot_metadata)"""
    EXPIRED = "expired"               # Expirou pela politica de retencao
    MANUAL = "manual"                 # Deletado manualmente pelo usuario
    INSTANCE_TERMINATED = "instance_terminated"  # Instancia foi terminada
    STORAGE_LIMIT = "storage_limit"   # Limite de storage atingido
    ERROR = "error"                   # Erro no snapshot


@dataclass
class SnapshotDeletionAuditEntry:
    """
    Entrada de auditoria para delecao de snapshot.

    Armazena informacoes detalhadas sobre uma operacao de delecao
    para fins de auditoria e troubleshooting.
    """
    # Identificacao do evento
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType = AuditEventType.DELETION

    # Dados do snapshot
    snapshot_id: str = ""
    instance_id: str = ""
    user_id: str = ""

    # Detalhes da delecao
    deletion_reason: str = ""         # Razao como string para flexibilidade
    storage_freed_bytes: int = 0
    storage_provider: str = ""        # b2, r2, s3, etc

    # Status da operacao
    success: bool = True
    error_message: Optional[str] = None

    # Timestamps (UTC)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Contexto adicional
    cleanup_run_id: Optional[str] = None   # ID do ciclo de cleanup
    retention_days: Optional[int] = None   # Retencao que causou expiracao
    snapshot_age_days: Optional[int] = None # Idade do snapshot ao deletar
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario para serializacao JSON"""
        data = asdict(self)
        # Converter enum para string
        if isinstance(self.event_type, AuditEventType):
            data['event_type'] = self.event_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SnapshotDeletionAuditEntry':
        """Cria a partir de dicionario"""
        # Converter string para enum
        event_type = data.get('event_type', 'deletion')
        if isinstance(event_type, str):
            event_type = AuditEventType(event_type)

        return cls(
            event_id=data.get('event_id', str(uuid.uuid4())),
            event_type=event_type,
            snapshot_id=data.get('snapshot_id', ''),
            instance_id=data.get('instance_id', ''),
            user_id=data.get('user_id', ''),
            deletion_reason=data.get('deletion_reason', ''),
            storage_freed_bytes=data.get('storage_freed_bytes', 0),
            storage_provider=data.get('storage_provider', ''),
            success=data.get('success', True),
            error_message=data.get('error_message'),
            timestamp=data.get('timestamp', datetime.now(timezone.utc).isoformat()),
            cleanup_run_id=data.get('cleanup_run_id'),
            retention_days=data.get('retention_days'),
            snapshot_age_days=data.get('snapshot_age_days'),
            metadata=data.get('metadata', {}),
        )

    def __repr__(self):
        return (f"<SnapshotDeletionAuditEntry {self.event_id[:8]}... "
                f"snapshot={self.snapshot_id} reason={self.deletion_reason} "
                f"success={self.success}>")


class SnapshotAuditLogger:
    """
    Logger de auditoria para operacoes de snapshot.

    Registra todas as operacoes de delecao e alteracoes de configuracao
    em um arquivo JSON persistente para auditoria e troubleshooting.
    """

    DEFAULT_AUDIT_FILE = "snapshot_deletion_audit.json"

    def __init__(
        self,
        audit_file_path: Optional[str] = None,
        max_entries: int = 10000,
    ):
        """
        Inicializa o audit logger.

        Args:
            audit_file_path: Caminho para o arquivo de auditoria.
                            Se None, usa diretorio padrao.
            max_entries: Numero maximo de entradas a manter (FIFO).
        """
        self._audit_file_path = audit_file_path
        self.max_entries = max_entries
        self._entries: List[SnapshotDeletionAuditEntry] = []
        self._loaded = False

        # ID do ciclo de cleanup atual (para correlacao)
        self._current_cleanup_run_id: Optional[str] = None

    @property
    def audit_file_path(self) -> str:
        """Retorna o caminho do arquivo de auditoria."""
        if self._audit_file_path:
            return self._audit_file_path

        # Diretorio padrao: ~/.dumont/audit/
        home_dir = Path.home()
        audit_dir = home_dir / ".dumont" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        return str(audit_dir / self.DEFAULT_AUDIT_FILE)

    def _ensure_loaded(self) -> None:
        """Carrega entradas do arquivo se ainda nao foram carregadas."""
        if self._loaded:
            return

        try:
            if os.path.exists(self.audit_file_path):
                with open(self.audit_file_path, 'r') as f:
                    data = json.load(f)
                    entries_data = data.get('entries', [])
                    self._entries = [
                        SnapshotDeletionAuditEntry.from_dict(e)
                        for e in entries_data
                    ]
                    logger.debug(f"Carregadas {len(self._entries)} entradas de auditoria")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Erro ao carregar arquivo de auditoria: {e}")
            self._entries = []

        self._loaded = True

    def _save(self) -> None:
        """Persiste entradas no arquivo de auditoria."""
        try:
            # Garantir que diretorio existe
            audit_dir = Path(self.audit_file_path).parent
            audit_dir.mkdir(parents=True, exist_ok=True)

            # Aplicar limite maximo
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries:]

            data = {
                'version': '1.0',
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'entry_count': len(self._entries),
                'entries': [e.to_dict() for e in self._entries],
            }

            with open(self.audit_file_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Salvas {len(self._entries)} entradas de auditoria")

        except IOError as e:
            logger.error(f"Erro ao salvar arquivo de auditoria: {e}")

    def log_deletion(
        self,
        snapshot_id: str,
        user_id: str,
        deletion_reason: str,
        storage_freed_bytes: int,
        instance_id: str = "",
        storage_provider: str = "",
        success: bool = True,
        error_message: Optional[str] = None,
        retention_days: Optional[int] = None,
        snapshot_age_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SnapshotDeletionAuditEntry:
        """
        Registra uma delecao de snapshot.

        Args:
            snapshot_id: ID do snapshot deletado
            user_id: ID do usuario proprietario
            deletion_reason: Razao da delecao (expired, manual, etc)
            storage_freed_bytes: Bytes liberados
            instance_id: ID da instancia (opcional)
            storage_provider: Provider de storage (b2, r2, s3)
            success: Se a delecao foi bem sucedida
            error_message: Mensagem de erro se falhou
            retention_days: Dias de retencao que causaram expiracao
            snapshot_age_days: Idade do snapshot ao deletar
            metadata: Metadados adicionais

        Returns:
            Entrada de auditoria criada
        """
        self._ensure_loaded()

        entry = SnapshotDeletionAuditEntry(
            event_type=AuditEventType.DELETION if success else AuditEventType.DELETION_FAILED,
            snapshot_id=snapshot_id,
            instance_id=instance_id,
            user_id=user_id,
            deletion_reason=deletion_reason,
            storage_freed_bytes=storage_freed_bytes,
            storage_provider=storage_provider,
            success=success,
            error_message=error_message,
            cleanup_run_id=self._current_cleanup_run_id,
            retention_days=retention_days,
            snapshot_age_days=snapshot_age_days,
            metadata=metadata or {},
        )

        self._entries.append(entry)
        self._save()

        if success:
            logger.info(
                f"Audit: Snapshot {snapshot_id} deletado "
                f"(user={user_id}, reason={deletion_reason}, "
                f"freed={storage_freed_bytes} bytes)"
            )
        else:
            logger.warning(
                f"Audit: Falha ao deletar snapshot {snapshot_id} "
                f"(user={user_id}, error={error_message})"
            )

        return entry

    def log_cleanup_started(
        self,
        snapshots_to_process: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Registra inicio de um ciclo de cleanup.

        Args:
            snapshots_to_process: Numero de snapshots a processar
            metadata: Metadados adicionais

        Returns:
            ID do ciclo de cleanup para correlacao
        """
        self._ensure_loaded()

        run_id = str(uuid.uuid4())
        self._current_cleanup_run_id = run_id

        entry = SnapshotDeletionAuditEntry(
            event_type=AuditEventType.CLEANUP_STARTED,
            cleanup_run_id=run_id,
            metadata={
                'snapshots_to_process': snapshots_to_process,
                **(metadata or {}),
            },
        )

        self._entries.append(entry)
        self._save()

        logger.info(f"Audit: Ciclo de cleanup iniciado (run_id={run_id[:8]}..., "
                   f"snapshots={snapshots_to_process})")

        return run_id

    def log_cleanup_completed(
        self,
        snapshots_deleted: int = 0,
        snapshots_failed: int = 0,
        storage_freed_bytes: int = 0,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SnapshotDeletionAuditEntry:
        """
        Registra conclusao de um ciclo de cleanup.

        Args:
            snapshots_deleted: Snapshots deletados com sucesso
            snapshots_failed: Snapshots que falharam
            storage_freed_bytes: Total de bytes liberados
            duration_seconds: Duracao do ciclo em segundos
            metadata: Metadados adicionais

        Returns:
            Entrada de auditoria criada
        """
        self._ensure_loaded()

        entry = SnapshotDeletionAuditEntry(
            event_type=AuditEventType.CLEANUP_COMPLETED,
            storage_freed_bytes=storage_freed_bytes,
            success=(snapshots_failed == 0),
            cleanup_run_id=self._current_cleanup_run_id,
            metadata={
                'snapshots_deleted': snapshots_deleted,
                'snapshots_failed': snapshots_failed,
                'duration_seconds': duration_seconds,
                **(metadata or {}),
            },
        )

        self._entries.append(entry)
        self._save()

        # Limpar ID do ciclo
        self._current_cleanup_run_id = None

        logger.info(
            f"Audit: Ciclo de cleanup concluido "
            f"(deleted={snapshots_deleted}, failed={snapshots_failed}, "
            f"freed={storage_freed_bytes} bytes)"
        )

        return entry

    def log_keep_forever_changed(
        self,
        snapshot_id: str,
        user_id: str,
        keep_forever: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SnapshotDeletionAuditEntry:
        """
        Registra alteracao da flag keep_forever.

        Args:
            snapshot_id: ID do snapshot
            user_id: Usuario que fez a alteracao
            keep_forever: Novo valor da flag
            metadata: Metadados adicionais

        Returns:
            Entrada de auditoria criada
        """
        self._ensure_loaded()

        event_type = AuditEventType.KEEP_FOREVER_SET if keep_forever else AuditEventType.KEEP_FOREVER_UNSET

        entry = SnapshotDeletionAuditEntry(
            event_type=event_type,
            snapshot_id=snapshot_id,
            user_id=user_id,
            metadata={
                'keep_forever': keep_forever,
                **(metadata or {}),
            },
        )

        self._entries.append(entry)
        self._save()

        action = "habilitada" if keep_forever else "desabilitada"
        logger.info(f"Audit: Flag keep_forever {action} para snapshot {snapshot_id}")

        return entry

    def log_retention_changed(
        self,
        snapshot_id: str,
        user_id: str,
        old_retention_days: Optional[int],
        new_retention_days: Optional[int],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SnapshotDeletionAuditEntry:
        """
        Registra alteracao do periodo de retencao.

        Args:
            snapshot_id: ID do snapshot
            user_id: Usuario que fez a alteracao
            old_retention_days: Retencao anterior
            new_retention_days: Nova retencao
            metadata: Metadados adicionais

        Returns:
            Entrada de auditoria criada
        """
        self._ensure_loaded()

        entry = SnapshotDeletionAuditEntry(
            event_type=AuditEventType.RETENTION_CHANGED,
            snapshot_id=snapshot_id,
            user_id=user_id,
            retention_days=new_retention_days,
            metadata={
                'old_retention_days': old_retention_days,
                'new_retention_days': new_retention_days,
                **(metadata or {}),
            },
        )

        self._entries.append(entry)
        self._save()

        logger.info(
            f"Audit: Retencao alterada para snapshot {snapshot_id} "
            f"({old_retention_days} -> {new_retention_days} dias)"
        )

        return entry

    def get_entries(
        self,
        limit: int = 100,
        offset: int = 0,
        snapshot_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[SnapshotDeletionAuditEntry]:
        """
        Consulta entradas de auditoria.

        Args:
            limit: Maximo de entradas a retornar
            offset: Offset para paginacao
            snapshot_id: Filtrar por snapshot
            user_id: Filtrar por usuario
            event_type: Filtrar por tipo de evento
            start_date: Data inicial (UTC)
            end_date: Data final (UTC)

        Returns:
            Lista de entradas de auditoria
        """
        self._ensure_loaded()

        # Filtrar entradas
        filtered = self._entries.copy()

        if snapshot_id:
            filtered = [e for e in filtered if e.snapshot_id == snapshot_id]

        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]

        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]

        if start_date:
            start_iso = start_date.isoformat()
            filtered = [e for e in filtered if e.timestamp >= start_iso]

        if end_date:
            end_iso = end_date.isoformat()
            filtered = [e for e in filtered if e.timestamp <= end_iso]

        # Ordenar por timestamp descendente (mais recentes primeiro)
        filtered.sort(key=lambda e: e.timestamp, reverse=True)

        # Aplicar paginacao
        return filtered[offset:offset + limit]

    def get_deletion_count(self, days: int = 30) -> int:
        """
        Retorna contagem de delecoes nos ultimos N dias.

        Args:
            days: Numero de dias a considerar

        Returns:
            Contagem de delecoes
        """
        self._ensure_loaded()

        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        count = sum(
            1 for e in self._entries
            if e.event_type == AuditEventType.DELETION
            and e.timestamp >= cutoff_iso
        )

        return count

    def get_storage_freed_total(self, days: int = 30) -> int:
        """
        Retorna total de storage liberado nos ultimos N dias.

        Args:
            days: Numero de dias a considerar

        Returns:
            Total de bytes liberados
        """
        self._ensure_loaded()

        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        total = sum(
            e.storage_freed_bytes for e in self._entries
            if e.event_type == AuditEventType.DELETION
            and e.success
            and e.timestamp >= cutoff_iso
        )

        return total

    def clear(self) -> None:
        """Limpa todas as entradas de auditoria (para testes)."""
        self._entries = []
        self._loaded = True
        self._save()


# Singleton global do audit logger
_snapshot_audit_logger: Optional[SnapshotAuditLogger] = None


def get_snapshot_audit_logger() -> SnapshotAuditLogger:
    """
    Retorna a instancia global do audit logger.

    Returns:
        SnapshotAuditLogger singleton
    """
    global _snapshot_audit_logger
    if _snapshot_audit_logger is None:
        _snapshot_audit_logger = SnapshotAuditLogger()
    return _snapshot_audit_logger
