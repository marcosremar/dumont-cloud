"""
Snapshot Metadata - Metadados de snapshots do Dumont Cloud.

Define o modelo de metadados para snapshots individuais:
- snapshot_id: Identificador unico do snapshot
- keep_forever: Flag para manter snapshot indefinidamente
- retention_days: Dias de retencao (sobrescreve padrao global)
- created_at: Data de criacao do snapshot
- storage_provider: Provedor de storage (b2, r2, s3)
- size_bytes: Tamanho do snapshot em bytes

Metadados sao armazenados em config.json por usuario/instancia.
"""

import enum
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class SnapshotStatus(enum.Enum):
    """Status do snapshot"""
    ACTIVE = "active"                 # Snapshot ativo e disponivel
    PENDING_DELETION = "pending_deletion"  # Marcado para delecao
    DELETED = "deleted"               # Deletado (apenas metadados mantidos)
    FAILED = "failed"                 # Falha na criacao ou delecao
    RESTORING = "restoring"           # Em processo de restauracao


class DeletionReason(enum.Enum):
    """Razao para delecao de snapshot"""
    EXPIRED = "expired"               # Expirou pela politica de retencao
    MANUAL = "manual"                 # Deletado manualmente pelo usuario
    INSTANCE_TERMINATED = "instance_terminated"  # Instancia foi terminada
    STORAGE_LIMIT = "storage_limit"   # Limite de storage atingido
    ERROR = "error"                   # Erro no snapshot


@dataclass
class SnapshotMetadata:
    """
    Metadados de um snapshot individual.

    Armazena informacoes sobre um snapshot especifico, incluindo
    politicas de retencao e status.
    """
    # Identificacao
    snapshot_id: str                           # ID unico do snapshot
    instance_id: str = ""                      # ID da instancia associada
    user_id: str = ""                          # ID do usuario proprietario

    # Politica de retencao
    keep_forever: bool = False                 # Manter indefinidamente
    retention_days: Optional[int] = None       # Dias de retencao (None = usar padrao)

    # Status
    status: SnapshotStatus = SnapshotStatus.ACTIVE

    # Storage
    storage_provider: str = "b2"               # Provedor: b2, r2, s3
    storage_path: str = ""                     # Caminho no storage
    size_bytes: int = 0                        # Tamanho em bytes

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None           # Data de expiracao calculada
    deleted_at: Optional[str] = None           # Data de delecao

    # Metadados de delecao
    deletion_reason: Optional[DeletionReason] = None
    deletion_error: Optional[str] = None       # Mensagem de erro se falhou
    deletion_retries: int = 0                  # Tentativas de delecao

    # Metadados extras
    name: str = ""                             # Nome amigavel do snapshot
    description: str = ""                      # Descricao
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, default_retention_days: int = 7) -> bool:
        """
        Verifica se o snapshot expirou.

        Args:
            default_retention_days: Retencao padrao se nao configurada

        Returns:
            True se o snapshot expirou
        """
        if self.keep_forever:
            return False

        if self.status != SnapshotStatus.ACTIVE:
            return False

        effective_retention = self.get_effective_retention_days(default_retention_days)
        if effective_retention == 0:
            return False  # 0 = manter indefinidamente

        created = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        age_days = (now - created).days

        return age_days >= effective_retention

    def get_effective_retention_days(self, default_retention_days: int = 7) -> int:
        """
        Retorna os dias de retencao efetivos.

        Args:
            default_retention_days: Retencao padrao se nao configurada

        Returns:
            Dias de retencao (0 = manter indefinidamente)
        """
        if self.keep_forever:
            return 0
        if self.retention_days is not None:
            return self.retention_days
        return default_retention_days

    def get_age_days(self) -> int:
        """Retorna a idade do snapshot em dias"""
        created = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        return (now - created).days

    def mark_for_deletion(self, reason: DeletionReason = DeletionReason.EXPIRED):
        """Marca o snapshot para delecao"""
        self.status = SnapshotStatus.PENDING_DELETION
        self.deletion_reason = reason
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_deleted(self):
        """Marca o snapshot como deletado"""
        self.status = SnapshotStatus.DELETED
        self.deleted_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_deletion_failed(self, error: str):
        """Marca falha na delecao"""
        self.status = SnapshotStatus.FAILED
        self.deletion_error = error
        self.deletion_retries += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def update_expiration(self, default_retention_days: int = 7):
        """Atualiza a data de expiracao calculada"""
        effective_retention = self.get_effective_retention_days(default_retention_days)
        if effective_retention == 0:
            self.expires_at = None
            return

        created = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        from datetime import timedelta
        expires = created + timedelta(days=effective_retention)
        self.expires_at = expires.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        data = asdict(self)
        # Converter enums para strings
        if self.status:
            data['status'] = self.status.value
        if self.deletion_reason:
            data['deletion_reason'] = self.deletion_reason.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SnapshotMetadata':
        """Cria a partir de dicionario"""
        # Converter strings de volta para enums
        status = data.get('status', 'active')
        if isinstance(status, str):
            status = SnapshotStatus(status)

        deletion_reason = data.get('deletion_reason')
        if isinstance(deletion_reason, str):
            deletion_reason = DeletionReason(deletion_reason)

        return cls(
            snapshot_id=data['snapshot_id'],
            instance_id=data.get('instance_id', ''),
            user_id=data.get('user_id', ''),
            keep_forever=data.get('keep_forever', False),
            retention_days=data.get('retention_days'),
            status=status,
            storage_provider=data.get('storage_provider', 'b2'),
            storage_path=data.get('storage_path', ''),
            size_bytes=data.get('size_bytes', 0),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            updated_at=data.get('updated_at', datetime.now(timezone.utc).isoformat()),
            expires_at=data.get('expires_at'),
            deleted_at=data.get('deleted_at'),
            deletion_reason=deletion_reason,
            deletion_error=data.get('deletion_error'),
            deletion_retries=data.get('deletion_retries', 0),
            name=data.get('name', ''),
            description=data.get('description', ''),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {}),
        )

    def __repr__(self):
        return f"<SnapshotMetadata {self.snapshot_id} keep_forever={self.keep_forever} status={self.status.value}>"
