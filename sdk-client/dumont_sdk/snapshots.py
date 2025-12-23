"""
Módulo de gerenciamento de snapshots.

Permite criar, listar, restaurar e deletar snapshots.
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    """Snapshot de uma instância."""
    id: str
    instance_id: Optional[int] = None
    created_at: Optional[str] = None
    size_bytes: int = 0
    status: str = "unknown"
    label: Optional[str] = None
    paths: Optional[List[str]] = None

    @property
    def size_gb(self) -> float:
        """Tamanho em GB."""
        return self.size_bytes / (1024 ** 3)

    @property
    def size_human(self) -> str:
        """Tamanho formatado."""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 ** 2:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 ** 3:
            return f"{self.size_bytes / (1024 ** 2):.1f} MB"
        else:
            return f"{self.size_bytes / (1024 ** 3):.2f} GB"


class SnapshotsClient:
    """
    Cliente para gerenciamento de snapshots.

    Exemplo:
        async with DumontClient(api_key="...") as client:
            # Listar snapshots
            snapshots = await client.snapshots.list()

            # Criar snapshot
            snapshot = await client.snapshots.create(instance_id=12345)

            # Restaurar
            await client.snapshots.restore(snapshot_id="abc123", instance_id=12345)
    """

    def __init__(self, base_client):
        self._client = base_client

    async def list(self, instance_id: Optional[int] = None) -> List[Snapshot]:
        """
        Lista snapshots.

        Args:
            instance_id: Filtrar por instância (opcional)

        Returns:
            Lista de snapshots
        """
        params = {}
        if instance_id:
            params["instance_id"] = instance_id

        response = await self._client.get("/api/v1/snapshots", params=params)
        snapshots_data = response.get("snapshots", [])

        return [
            Snapshot(
                id=snap["id"],
                instance_id=snap.get("instance_id"),
                created_at=snap.get("created_at"),
                size_bytes=snap.get("size_bytes", 0),
                status=snap.get("status", "unknown"),
                label=snap.get("label"),
                paths=snap.get("paths"),
            )
            for snap in snapshots_data
        ]

    async def get(self, snapshot_id: str) -> Snapshot:
        """
        Obtém detalhes de um snapshot.

        Args:
            snapshot_id: ID do snapshot

        Returns:
            Detalhes do snapshot
        """
        snap = await self._client.get(f"/api/v1/snapshots/{snapshot_id}")

        return Snapshot(
            id=snap["id"],
            instance_id=snap.get("instance_id"),
            created_at=snap.get("created_at"),
            size_bytes=snap.get("size_bytes", 0),
            status=snap.get("status", "unknown"),
            label=snap.get("label"),
            paths=snap.get("paths"),
        )

    async def create(
        self,
        instance_id: int,
        paths: Optional[List[str]] = None,
        label: Optional[str] = None,
    ) -> Snapshot:
        """
        Cria um snapshot de uma instância.

        Args:
            instance_id: ID da instância
            paths: Caminhos para incluir (default: /workspace)
            label: Label para o snapshot

        Returns:
            Snapshot criado
        """
        data = {
            "instance_id": instance_id,
        }

        if paths:
            data["paths"] = paths
        if label:
            data["label"] = label

        snap = await self._client.post("/api/v1/snapshots", data=data)

        return Snapshot(
            id=snap["id"],
            instance_id=snap.get("instance_id"),
            created_at=snap.get("created_at"),
            size_bytes=snap.get("size_bytes", 0),
            status=snap.get("status", "creating"),
            label=snap.get("label"),
            paths=snap.get("paths"),
        )

    async def restore(
        self,
        snapshot_id: str,
        instance_id: int,
        target_path: str = "/workspace",
    ) -> Dict[str, Any]:
        """
        Restaura um snapshot em uma instância.

        Args:
            snapshot_id: ID do snapshot
            instance_id: ID da instância de destino
            target_path: Caminho de destino

        Returns:
            Resultado da operação
        """
        data = {
            "snapshot_id": snapshot_id,
            "instance_id": instance_id,
            "target_path": target_path,
        }

        return await self._client.post("/api/v1/snapshots/restore", data=data)

    async def delete(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Deleta um snapshot.

        Args:
            snapshot_id: ID do snapshot

        Returns:
            Resultado da operação
        """
        return await self._client.delete(f"/api/v1/snapshots/{snapshot_id}")

    async def latest(self, instance_id: int) -> Optional[Snapshot]:
        """
        Obtém o snapshot mais recente de uma instância.

        Args:
            instance_id: ID da instância

        Returns:
            Snapshot mais recente ou None
        """
        snapshots = await self.list(instance_id=instance_id)
        if not snapshots:
            return None

        # Ordena por data de criação (mais recente primeiro)
        snapshots.sort(key=lambda s: s.created_at or "", reverse=True)
        return snapshots[0]
