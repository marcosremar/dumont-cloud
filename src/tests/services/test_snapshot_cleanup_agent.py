"""
Testes do SnapshotCleanupAgent - Dumont Cloud

Testa a logica de identificacao de snapshots expirados:
- Identificacao correta de snapshots que excederam o periodo de retencao
- Respeito a flag keep_forever
- Retencao padrao de 7 dias
- Retencao customizada por snapshot e por instancia
- Tratamento de retention_days=0 como "manter indefinidamente"
- Ordenacao por idade (mais antigos primeiro)
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.services.snapshot_cleanup_agent import (
    SnapshotCleanupAgent,
    SnapshotRepository,
    InMemorySnapshotRepository,
)
from src.models.snapshot_metadata import (
    SnapshotMetadata,
    SnapshotStatus,
    DeletionReason,
)
from src.config.snapshot_lifecycle_config import (
    SnapshotLifecycleConfig,
    SnapshotLifecycleManager,
    InstanceSnapshotConfig,
    RetentionPolicyConfig,
    CleanupScheduleConfig,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_lifecycle_manager():
    """Cria um mock do SnapshotLifecycleManager."""
    manager = Mock(spec=SnapshotLifecycleManager)

    # Configuracao global padrao
    global_config = SnapshotLifecycleConfig(
        default_retention_days=7,
        retention=RetentionPolicyConfig(enabled=True),
        cleanup_schedule=CleanupScheduleConfig(enabled=True),
    )
    manager.get_global_config.return_value = global_config
    manager.list_instance_configs.return_value = {}

    # get_instance_config retorna config padrao
    def get_instance_config(instance_id):
        return InstanceSnapshotConfig(
            instance_id=instance_id,
            use_global_settings=True,
        )
    manager.get_instance_config.side_effect = get_instance_config

    return manager


@pytest.fixture
def snapshot_repository():
    """Cria um repositorio de snapshots em memoria."""
    return InMemorySnapshotRepository()


@pytest.fixture
def cleanup_agent(mock_lifecycle_manager, snapshot_repository):
    """Cria um agente de cleanup com mocks."""
    agent = SnapshotCleanupAgent(
        interval_hours=24,
        dry_run=False,
        batch_size=100,
        snapshot_repository=snapshot_repository,
        lifecycle_manager=mock_lifecycle_manager,
    )
    return agent


def create_snapshot(
    snapshot_id: str,
    age_days: int = 0,
    keep_forever: bool = False,
    retention_days: int = None,
    instance_id: str = "instance-1",
    status: SnapshotStatus = SnapshotStatus.ACTIVE,
    size_bytes: int = 1024 * 1024,  # 1 MB
) -> SnapshotMetadata:
    """Helper para criar snapshots de teste."""
    created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
    return SnapshotMetadata(
        snapshot_id=snapshot_id,
        instance_id=instance_id,
        keep_forever=keep_forever,
        retention_days=retention_days,
        status=status,
        created_at=created_at.isoformat(),
        size_bytes=size_bytes,
        storage_provider="b2",
    )


# ============================================================
# Testes de Identificacao de Snapshots Expirados
# ============================================================

class TestIdentifyExpiredSnapshots:
    """Testes da logica de identificacao de snapshots expirados."""

    def test_identify_expired_snapshots_basic(self, cleanup_agent, snapshot_repository):
        """
        Testa identificacao basica de snapshots expirados.

        Cenario:
        - 1 snapshot com 10 dias (> 7 dias default) - deve expirar
        - 1 snapshot com 3 dias (< 7 dias default) - nao deve expirar
        """
        # Criar snapshots
        old_snapshot = create_snapshot("snap-old", age_days=10)
        new_snapshot = create_snapshot("snap-new", age_days=3)

        snapshot_repository.add_snapshot(old_snapshot)
        snapshot_repository.add_snapshot(new_snapshot)

        # Identificar expirados
        expired = cleanup_agent._identify_expired_snapshots()

        # Verificar
        assert len(expired) == 1
        assert expired[0].snapshot_id == "snap-old"

    def test_identify_expired_snapshots_empty_repository(self, cleanup_agent, snapshot_repository):
        """Testa com repositorio vazio - deve retornar lista vazia."""
        expired = cleanup_agent._identify_expired_snapshots()
        assert len(expired) == 0

    def test_identify_expired_snapshots_no_repository(self, mock_lifecycle_manager):
        """Testa sem repositorio configurado - deve retornar lista vazia."""
        agent = SnapshotCleanupAgent(
            interval_hours=24,
            snapshot_repository=None,
            lifecycle_manager=mock_lifecycle_manager,
        )
        expired = agent._identify_expired_snapshots()
        assert len(expired) == 0

    def test_keep_forever_protection(self, cleanup_agent, snapshot_repository):
        """
        Testa que snapshots com keep_forever=True nunca sao marcados como expirados.

        Cenario:
        - 1 snapshot com 100 dias e keep_forever=True - NAO deve expirar
        - 1 snapshot com 10 dias e keep_forever=False - deve expirar
        """
        # Criar snapshots
        permanent = create_snapshot("snap-permanent", age_days=100, keep_forever=True)
        temporary = create_snapshot("snap-temporary", age_days=10, keep_forever=False)

        snapshot_repository.add_snapshot(permanent)
        snapshot_repository.add_snapshot(temporary)

        # Identificar expirados
        expired = cleanup_agent._identify_expired_snapshots()

        # Verificar que apenas o temporario expirou
        assert len(expired) == 1
        assert expired[0].snapshot_id == "snap-temporary"

        # Verificar que o permanente NAO esta na lista
        assert not any(s.snapshot_id == "snap-permanent" for s in expired)

    def test_default_retention_7days(self, cleanup_agent, snapshot_repository):
        """
        Testa que a retencao padrao e de 7 dias.

        Cenario:
        - Snapshot com 6 dias - NAO deve expirar
        - Snapshot com 7 dias - DEVE expirar (>=7)
        - Snapshot com 8 dias - DEVE expirar
        """
        snap_6days = create_snapshot("snap-6", age_days=6)
        snap_7days = create_snapshot("snap-7", age_days=7)
        snap_8days = create_snapshot("snap-8", age_days=8)

        snapshot_repository.add_snapshot(snap_6days)
        snapshot_repository.add_snapshot(snap_7days)
        snapshot_repository.add_snapshot(snap_8days)

        expired = cleanup_agent._identify_expired_snapshots()

        # Snapshots com 7+ dias devem expirar
        expired_ids = [s.snapshot_id for s in expired]
        assert "snap-6" not in expired_ids
        assert "snap-7" in expired_ids
        assert "snap-8" in expired_ids
        assert len(expired) == 2

    def test_custom_retention_per_snapshot(self, cleanup_agent, snapshot_repository):
        """
        Testa retencao customizada por snapshot.

        Cenario:
        - Snapshot com 5 dias e retention_days=3 - deve expirar (5 > 3)
        - Snapshot com 5 dias e retention_days=10 - NAO deve expirar (5 < 10)
        - Snapshot com 5 dias sem retention_days - NAO deve expirar (5 < 7 default)
        """
        snap_short_retention = create_snapshot("snap-short", age_days=5, retention_days=3)
        snap_long_retention = create_snapshot("snap-long", age_days=5, retention_days=10)
        snap_default_retention = create_snapshot("snap-default", age_days=5)

        snapshot_repository.add_snapshot(snap_short_retention)
        snapshot_repository.add_snapshot(snap_long_retention)
        snapshot_repository.add_snapshot(snap_default_retention)

        expired = cleanup_agent._identify_expired_snapshots()

        # Apenas o snapshot com retencao curta deve expirar
        assert len(expired) == 1
        assert expired[0].snapshot_id == "snap-short"

    def test_zero_day_retention_keeps_forever(self, cleanup_agent, snapshot_repository):
        """
        Testa que retention_days=0 significa "manter indefinidamente".

        Cenario:
        - Snapshot com 1000 dias e retention_days=0 - NAO deve expirar
        """
        ancient_snapshot = create_snapshot("snap-ancient", age_days=1000, retention_days=0)
        snapshot_repository.add_snapshot(ancient_snapshot)

        expired = cleanup_agent._identify_expired_snapshots()

        assert len(expired) == 0

    def test_only_active_snapshots_expire(self, cleanup_agent, snapshot_repository):
        """
        Testa que apenas snapshots com status ACTIVE sao considerados para expiracao.

        Outros status (PENDING_DELETION, DELETED, FAILED) nao devem ser processados.
        """
        active_old = create_snapshot("snap-active", age_days=10, status=SnapshotStatus.ACTIVE)
        pending_old = create_snapshot("snap-pending", age_days=10, status=SnapshotStatus.PENDING_DELETION)
        deleted_old = create_snapshot("snap-deleted", age_days=10, status=SnapshotStatus.DELETED)
        failed_old = create_snapshot("snap-failed", age_days=10, status=SnapshotStatus.FAILED)

        snapshot_repository.add_snapshot(active_old)
        snapshot_repository.add_snapshot(pending_old)
        snapshot_repository.add_snapshot(deleted_old)
        snapshot_repository.add_snapshot(failed_old)

        expired = cleanup_agent._identify_expired_snapshots()

        # Apenas o snapshot ACTIVE deve aparecer (repository ja filtra)
        # Mas o get_all_active_snapshots do InMemorySnapshotRepository ja filtra
        assert len(expired) == 1
        assert expired[0].snapshot_id == "snap-active"

    def test_expired_snapshots_ordered_by_age(self, cleanup_agent, snapshot_repository):
        """
        Testa que snapshots expirados sao ordenados por idade (mais antigos primeiro).

        Isso permite deletar os mais antigos primeiro, liberando mais espaco.
        """
        # Criar snapshots em ordem aleatoria de idade
        snap_15days = create_snapshot("snap-15", age_days=15)
        snap_10days = create_snapshot("snap-10", age_days=10)
        snap_20days = create_snapshot("snap-20", age_days=20)
        snap_8days = create_snapshot("snap-8", age_days=8)

        # Adicionar em ordem aleatoria
        snapshot_repository.add_snapshot(snap_15days)
        snapshot_repository.add_snapshot(snap_10days)
        snapshot_repository.add_snapshot(snap_20days)
        snapshot_repository.add_snapshot(snap_8days)

        expired = cleanup_agent._identify_expired_snapshots()

        # Todos devem expirar (> 7 dias)
        assert len(expired) == 4

        # Devem estar ordenados por idade (mais antigo primeiro)
        # O mais antigo tem created_at menor (data mais antiga)
        assert expired[0].snapshot_id == "snap-20"
        assert expired[1].snapshot_id == "snap-15"
        assert expired[2].snapshot_id == "snap-10"
        assert expired[3].snapshot_id == "snap-8"

    def test_instance_retention_override(
        self, cleanup_agent, snapshot_repository, mock_lifecycle_manager
    ):
        """
        Testa que a retencao por instancia sobrescreve a global.

        Cenario:
        - Instancia "inst-long" com retention_days=30
        - Snapshot de "inst-long" com 20 dias - NAO deve expirar
        - Snapshot de outra instancia com 20 dias - DEVE expirar
        """
        # Configurar instancia com retencao longa
        instance_config = InstanceSnapshotConfig(
            instance_id="inst-long",
            use_global_settings=False,
            retention_days=30,
            cleanup_enabled=True,
        )

        def get_instance_config(instance_id):
            if instance_id == "inst-long":
                return instance_config
            return InstanceSnapshotConfig(
                instance_id=instance_id,
                use_global_settings=True,
            )

        mock_lifecycle_manager.get_instance_config.side_effect = get_instance_config

        # Criar snapshots
        snap_long_instance = create_snapshot("snap-long-inst", age_days=20, instance_id="inst-long")
        snap_normal_instance = create_snapshot("snap-normal-inst", age_days=20, instance_id="inst-normal")

        snapshot_repository.add_snapshot(snap_long_instance)
        snapshot_repository.add_snapshot(snap_normal_instance)

        expired = cleanup_agent._identify_expired_snapshots()

        # Apenas o snapshot da instancia normal deve expirar
        assert len(expired) == 1
        assert expired[0].snapshot_id == "snap-normal-inst"

    def test_cleanup_disabled_for_instance(
        self, cleanup_agent, snapshot_repository, mock_lifecycle_manager
    ):
        """
        Testa que snapshots de instancias com cleanup desabilitado nao sao expirados.
        """
        # Configurar instancia com cleanup desabilitado
        instance_config = InstanceSnapshotConfig(
            instance_id="inst-no-cleanup",
            use_global_settings=False,
            cleanup_enabled=False,
        )

        def get_instance_config(instance_id):
            if instance_id == "inst-no-cleanup":
                return instance_config
            return InstanceSnapshotConfig(
                instance_id=instance_id,
                use_global_settings=True,
            )

        mock_lifecycle_manager.get_instance_config.side_effect = get_instance_config

        # Criar snapshot muito antigo na instancia sem cleanup
        old_snapshot = create_snapshot("snap-no-cleanup", age_days=100, instance_id="inst-no-cleanup")
        snapshot_repository.add_snapshot(old_snapshot)

        expired = cleanup_agent._identify_expired_snapshots()

        # Nenhum snapshot deve expirar
        assert len(expired) == 0


# ============================================================
# Testes do InMemorySnapshotRepository
# ============================================================

class TestInMemorySnapshotRepository:
    """Testes do repositorio em memoria."""

    def test_add_and_get_snapshot(self):
        """Testa adicao e recuperacao de snapshot."""
        repo = InMemorySnapshotRepository()
        snapshot = create_snapshot("snap-1")

        repo.add_snapshot(snapshot)

        result = repo.get_snapshot("snap-1")
        assert result is not None
        assert result.snapshot_id == "snap-1"

    def test_get_all_active_snapshots(self):
        """Testa listagem de todos os snapshots ativos."""
        repo = InMemorySnapshotRepository()

        active1 = create_snapshot("active-1", status=SnapshotStatus.ACTIVE)
        active2 = create_snapshot("active-2", status=SnapshotStatus.ACTIVE)
        deleted = create_snapshot("deleted", status=SnapshotStatus.DELETED)

        repo.add_snapshot(active1)
        repo.add_snapshot(active2)
        repo.add_snapshot(deleted)

        active = repo.get_all_active_snapshots()

        assert len(active) == 2
        ids = [s.snapshot_id for s in active]
        assert "active-1" in ids
        assert "active-2" in ids
        assert "deleted" not in ids

    def test_get_snapshots_by_instance(self):
        """Testa filtragem por instancia."""
        repo = InMemorySnapshotRepository()

        snap_inst1 = create_snapshot("snap-1", instance_id="inst-1")
        snap_inst2 = create_snapshot("snap-2", instance_id="inst-2")

        repo.add_snapshot(snap_inst1)
        repo.add_snapshot(snap_inst2)

        result = repo.get_snapshots_by_instance("inst-1")

        assert len(result) == 1
        assert result[0].snapshot_id == "snap-1"

    def test_update_snapshot(self):
        """Testa atualizacao de snapshot."""
        repo = InMemorySnapshotRepository()
        snapshot = create_snapshot("snap-1")
        repo.add_snapshot(snapshot)

        # Modificar e atualizar
        snapshot.keep_forever = True
        repo.update_snapshot(snapshot)

        # Verificar
        result = repo.get_snapshot("snap-1")
        assert result.keep_forever is True

    def test_clear_repository(self):
        """Testa limpeza do repositorio."""
        repo = InMemorySnapshotRepository()
        repo.add_snapshot(create_snapshot("snap-1"))
        repo.add_snapshot(create_snapshot("snap-2"))

        repo.clear()

        assert len(repo.get_all_active_snapshots()) == 0

    def test_init_with_snapshots(self):
        """Testa inicializacao com lista de snapshots."""
        snapshots = [
            create_snapshot("snap-1"),
            create_snapshot("snap-2"),
        ]

        repo = InMemorySnapshotRepository(snapshots=snapshots)

        assert len(repo.get_all_active_snapshots()) == 2


# ============================================================
# Testes de Integracao do Cleanup Cycle
# ============================================================

class TestCleanupCycleIntegration:
    """Testes de integracao do ciclo de cleanup."""

    def test_cleanup_cycle_updates_stats(self, cleanup_agent, snapshot_repository):
        """Testa que o ciclo de cleanup atualiza as estatisticas."""
        # Adicionar snapshots expirados
        snapshot_repository.add_snapshot(create_snapshot("snap-1", age_days=10, size_bytes=1000))
        snapshot_repository.add_snapshot(create_snapshot("snap-2", age_days=15, size_bytes=2000))

        # Simular que o agente esta rodando (necessario para o ciclo processar)
        cleanup_agent.running = True

        # Executar ciclo
        cleanup_agent._cleanup_cycle()

        stats = cleanup_agent.get_cleanup_stats()

        assert stats['snapshots_identified'] == 2
        assert stats['snapshots_deleted'] == 2
        assert stats['snapshots_failed'] == 0
        assert stats['storage_freed_bytes'] == 3000
        assert stats['started_at'] is not None
        assert stats['completed_at'] is not None

    def test_dry_run_does_not_delete(self, mock_lifecycle_manager, snapshot_repository):
        """Testa que modo dry-run nao deleta snapshots."""
        agent = SnapshotCleanupAgent(
            interval_hours=24,
            dry_run=True,
            snapshot_repository=snapshot_repository,
            lifecycle_manager=mock_lifecycle_manager,
        )
        # Simular que o agente esta rodando
        agent.running = True

        snapshot = create_snapshot("snap-old", age_days=10)
        snapshot_repository.add_snapshot(snapshot)

        # Executar ciclo em dry-run
        agent._cleanup_cycle()

        # Snapshot ainda deve estar ativo (dry-run nao modifica status)
        result = snapshot_repository.get_snapshot("snap-old")
        assert result.status == SnapshotStatus.ACTIVE

    def test_cleanup_updates_repository(self, cleanup_agent, snapshot_repository):
        """Testa que o cleanup atualiza o status no repositorio."""
        snapshot = create_snapshot("snap-to-delete", age_days=10)
        snapshot_repository.add_snapshot(snapshot)

        # Simular que o agente esta rodando
        cleanup_agent.running = True

        # Executar ciclo
        cleanup_agent._cleanup_cycle()

        # Snapshot deve estar marcado como deletado
        result = snapshot_repository.get_snapshot("snap-to-delete")
        assert result.status == SnapshotStatus.DELETED
        assert result.deletion_reason == DeletionReason.EXPIRED


# ============================================================
# Testes de Edge Cases
# ============================================================

class TestEdgeCases:
    """Testes de casos de borda."""

    def test_snapshot_exactly_at_retention_boundary(self, cleanup_agent, snapshot_repository):
        """Testa snapshot exatamente no limite de retencao (7 dias)."""
        # Snapshot com exatamente 7 dias deve expirar (>= 7)
        boundary_snapshot = create_snapshot("snap-boundary", age_days=7)
        snapshot_repository.add_snapshot(boundary_snapshot)

        expired = cleanup_agent._identify_expired_snapshots()

        assert len(expired) == 1
        assert expired[0].snapshot_id == "snap-boundary"

    def test_snapshot_just_before_retention(self, cleanup_agent, snapshot_repository):
        """Testa snapshot 1 dia antes do limite de retencao."""
        # Snapshot com 6 dias NAO deve expirar (< 7)
        almost_expired = create_snapshot("snap-almost", age_days=6)
        snapshot_repository.add_snapshot(almost_expired)

        expired = cleanup_agent._identify_expired_snapshots()

        assert len(expired) == 0

    def test_large_number_of_snapshots(self, cleanup_agent, snapshot_repository):
        """Testa com grande numero de snapshots."""
        # Criar 1000 snapshots
        for i in range(500):
            snapshot_repository.add_snapshot(
                create_snapshot(f"snap-new-{i}", age_days=3)  # Nao expira
            )
        for i in range(500):
            snapshot_repository.add_snapshot(
                create_snapshot(f"snap-old-{i}", age_days=10)  # Expira
            )

        expired = cleanup_agent._identify_expired_snapshots()

        assert len(expired) == 500

    def test_mixed_instances_and_retention(self, cleanup_agent, snapshot_repository, mock_lifecycle_manager):
        """Testa cenario complexo com multiplas instancias e retencoes."""
        # Configurar diferentes retencoes por instancia
        def get_instance_config(instance_id):
            if instance_id == "inst-short":
                return InstanceSnapshotConfig(
                    instance_id=instance_id,
                    use_global_settings=False,
                    retention_days=3,
                    cleanup_enabled=True,
                )
            elif instance_id == "inst-long":
                return InstanceSnapshotConfig(
                    instance_id=instance_id,
                    use_global_settings=False,
                    retention_days=30,
                    cleanup_enabled=True,
                )
            return InstanceSnapshotConfig(
                instance_id=instance_id,
                use_global_settings=True,
            )

        mock_lifecycle_manager.get_instance_config.side_effect = get_instance_config

        # Criar snapshots
        # inst-short: retencao 3 dias
        snapshot_repository.add_snapshot(
            create_snapshot("short-4d", age_days=4, instance_id="inst-short")  # Expira
        )
        snapshot_repository.add_snapshot(
            create_snapshot("short-2d", age_days=2, instance_id="inst-short")  # Nao expira
        )

        # inst-long: retencao 30 dias
        snapshot_repository.add_snapshot(
            create_snapshot("long-20d", age_days=20, instance_id="inst-long")  # Nao expira
        )
        snapshot_repository.add_snapshot(
            create_snapshot("long-35d", age_days=35, instance_id="inst-long")  # Expira
        )

        # inst-default: retencao 7 dias
        snapshot_repository.add_snapshot(
            create_snapshot("default-5d", age_days=5, instance_id="inst-default")  # Nao expira
        )
        snapshot_repository.add_snapshot(
            create_snapshot("default-10d", age_days=10, instance_id="inst-default")  # Expira
        )

        expired = cleanup_agent._identify_expired_snapshots()

        expired_ids = [s.snapshot_id for s in expired]

        # Verificar expirados
        assert "short-4d" in expired_ids
        assert "long-35d" in expired_ids
        assert "default-10d" in expired_ids

        # Verificar nao expirados
        assert "short-2d" not in expired_ids
        assert "long-20d" not in expired_ids
        assert "default-5d" not in expired_ids

        assert len(expired) == 3
