"""
Snapshot Scheduler - Sistema de snapshots periodicos para Dumont Cloud
Agenda e executa snapshots automaticos de instancias com intervalos configuraveis
"""

import logging
import time
import threading
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError

from config.settings import settings

logger = logging.getLogger(__name__)


class SnapshotStatus(Enum):
    """Status de um snapshot"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SnapshotJobInfo:
    """Informacoes de um job de snapshot agendado"""
    instance_id: str
    interval_minutes: int
    enabled: bool = True
    last_snapshot_at: Optional[float] = None
    next_snapshot_at: Optional[float] = None
    last_status: SnapshotStatus = SnapshotStatus.PENDING
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Converte para dict"""
        return {
            'instance_id': self.instance_id,
            'interval_minutes': self.interval_minutes,
            'enabled': self.enabled,
            'last_snapshot_at': self.last_snapshot_at,
            'last_snapshot_at_iso': datetime.fromtimestamp(self.last_snapshot_at).isoformat() if self.last_snapshot_at else None,
            'next_snapshot_at': self.next_snapshot_at,
            'next_snapshot_at_iso': datetime.fromtimestamp(self.next_snapshot_at).isoformat() if self.next_snapshot_at else None,
            'last_status': self.last_status.value,
            'last_error': self.last_error,
            'consecutive_failures': self.consecutive_failures,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    def is_overdue(self) -> bool:
        """Verifica se snapshot esta atrasado (>2x intervalo)"""
        if not self.last_snapshot_at:
            return False
        elapsed = time.time() - self.last_snapshot_at
        return elapsed > (self.interval_minutes * 60 * 2)


@dataclass
class SnapshotResult:
    """Resultado de uma execucao de snapshot"""
    instance_id: str
    status: SnapshotStatus
    started_at: float
    completed_at: float
    duration_seconds: float
    error: Optional[str] = None
    snapshot_id: Optional[str] = None
    size_bytes: Optional[int] = None

    def to_dict(self) -> dict:
        """Converte para dict"""
        return {
            'instance_id': self.instance_id,
            'status': self.status.value,
            'started_at': self.started_at,
            'started_at_iso': datetime.fromtimestamp(self.started_at).isoformat(),
            'completed_at': self.completed_at,
            'completed_at_iso': datetime.fromtimestamp(self.completed_at).isoformat(),
            'duration_seconds': self.duration_seconds,
            'error': self.error,
            'snapshot_id': self.snapshot_id,
            'size_bytes': self.size_bytes,
        }


class SnapshotScheduler:
    """
    Gerenciador de snapshots periodicos.

    Agenda e executa snapshots automaticos de instancias GPU
    com intervalos configuraveis por instancia.

    Features:
    - Intervalos configuraveis por instancia (5, 15, 30, 60 min)
    - Limite de snapshots concorrentes
    - Retry com backoff em falhas
    - Hooks para metricas e alertas
    - Persistencia de estado (via callbacks)
    """

    # Intervalos validos em minutos
    VALID_INTERVALS = [5, 15, 30, 60]
    MIN_INTERVAL = 5
    MAX_CONSECUTIVE_FAILURES = 5

    def __init__(
        self,
        snapshot_executor: Optional[Callable[[str], SnapshotResult]] = None,
        on_success: Optional[Callable[[SnapshotResult], None]] = None,
        on_failure: Optional[Callable[[SnapshotResult], None]] = None,
        on_state_change: Optional[Callable[[SnapshotJobInfo], None]] = None,
    ):
        """
        Inicializa o scheduler.

        Args:
            snapshot_executor: Funcao que executa o snapshot real (recebe instance_id)
            on_success: Callback chamado apos snapshot bem sucedido
            on_failure: Callback chamado apos falha de snapshot
            on_state_change: Callback chamado quando estado de um job muda
        """
        self._scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,  # Combina execucoes perdidas
                'max_instances': 1,  # Apenas 1 execucao por job
                'misfire_grace_time': 60,  # Tolerancia de 60s para misfires
            }
        )

        self._snapshot_executor = snapshot_executor or self._default_executor
        self._on_success = on_success
        self._on_failure = on_failure
        self._on_state_change = on_state_change

        self._jobs: Dict[str, SnapshotJobInfo] = {}
        self._active_snapshots: Dict[str, bool] = {}
        self._lock = threading.RLock()

        self._max_concurrent = settings.snapshot.max_concurrent
        self._default_interval = settings.snapshot.default_interval_minutes
        self._enabled = settings.snapshot.enabled

        self._running = False
        self._snapshot_history: List[SnapshotResult] = []
        self._max_history = 100

        logger.info("SnapshotScheduler initialized")

    def _default_executor(self, instance_id: str) -> SnapshotResult:
        """
        Executor padrao de snapshot (placeholder).
        Em producao, deve ser substituido por um executor real
        que integra com ResticService.
        """
        start_time = time.time()

        # Placeholder - simula snapshot
        logger.info(f"Executing snapshot for instance {instance_id} (placeholder)")
        time.sleep(0.1)  # Simula operacao

        end_time = time.time()

        return SnapshotResult(
            instance_id=instance_id,
            status=SnapshotStatus.SUCCESS,
            started_at=start_time,
            completed_at=end_time,
            duration_seconds=end_time - start_time,
            snapshot_id=f"snap-{instance_id}-{int(start_time)}",
        )

    def start(self):
        """Inicia o scheduler"""
        if not self._enabled:
            logger.warning("SnapshotScheduler is disabled in settings")
            return

        if self._running:
            logger.warning("SnapshotScheduler already running")
            return

        self._scheduler.start()
        self._running = True
        logger.info("SnapshotScheduler started")

    def stop(self, wait: bool = True):
        """Para o scheduler"""
        if not self._running:
            return

        self._scheduler.shutdown(wait=wait)
        self._running = False
        logger.info("SnapshotScheduler stopped")

    def is_running(self) -> bool:
        """Verifica se scheduler esta rodando"""
        return self._running

    def add_instance(
        self,
        instance_id: str,
        interval_minutes: Optional[int] = None,
        enabled: bool = True,
    ) -> SnapshotJobInfo:
        """
        Adiciona instancia ao scheduler.

        Args:
            instance_id: ID unico da instancia
            interval_minutes: Intervalo entre snapshots (default: settings)
            enabled: Se snapshots estao habilitados

        Returns:
            SnapshotJobInfo com detalhes do job

        Raises:
            ValueError: Se intervalo invalido
        """
        interval = interval_minutes or self._default_interval

        if interval < self.MIN_INTERVAL:
            raise ValueError(f"Interval must be >= {self.MIN_INTERVAL} minutes")

        with self._lock:
            # Remover job existente se houver
            if instance_id in self._jobs:
                self._remove_scheduler_job(instance_id)

            # Criar info do job
            job_info = SnapshotJobInfo(
                instance_id=instance_id,
                interval_minutes=interval,
                enabled=enabled,
            )

            # Adicionar ao scheduler se habilitado
            if enabled and self._running:
                self._add_scheduler_job(job_info)

            self._jobs[instance_id] = job_info

            if self._on_state_change:
                self._on_state_change(job_info)

            logger.info(f"Added instance {instance_id} with {interval}min interval")

            return job_info

    def remove_instance(self, instance_id: str) -> bool:
        """
        Remove instancia do scheduler.

        Args:
            instance_id: ID da instancia

        Returns:
            True se removida, False se nao existia
        """
        with self._lock:
            if instance_id not in self._jobs:
                return False

            self._remove_scheduler_job(instance_id)
            del self._jobs[instance_id]

            logger.info(f"Removed instance {instance_id} from scheduler")
            return True

    def update_instance(
        self,
        instance_id: str,
        interval_minutes: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[SnapshotJobInfo]:
        """
        Atualiza configuracao de uma instancia.

        Args:
            instance_id: ID da instancia
            interval_minutes: Novo intervalo (None = manter atual)
            enabled: Novo estado (None = manter atual)

        Returns:
            SnapshotJobInfo atualizado ou None se instancia nao existe
        """
        with self._lock:
            if instance_id not in self._jobs:
                return None

            job_info = self._jobs[instance_id]
            changed = False

            if interval_minutes is not None:
                if interval_minutes < self.MIN_INTERVAL:
                    raise ValueError(f"Interval must be >= {self.MIN_INTERVAL} minutes")
                if job_info.interval_minutes != interval_minutes:
                    job_info.interval_minutes = interval_minutes
                    changed = True

            if enabled is not None and job_info.enabled != enabled:
                job_info.enabled = enabled
                changed = True

            if changed:
                job_info.updated_at = time.time()

                # Remover e re-adicionar para aplicar mudancas
                self._remove_scheduler_job(instance_id)

                if job_info.enabled and self._running:
                    self._add_scheduler_job(job_info)

                if self._on_state_change:
                    self._on_state_change(job_info)

                logger.info(f"Updated instance {instance_id}: interval={job_info.interval_minutes}min, enabled={job_info.enabled}")

            return job_info

    def get_instance(self, instance_id: str) -> Optional[SnapshotJobInfo]:
        """Retorna info de uma instancia"""
        return self._jobs.get(instance_id)

    def get_all_instances(self) -> Dict[str, SnapshotJobInfo]:
        """Retorna todos os jobs"""
        return dict(self._jobs)

    def get_status(self) -> Dict[str, Any]:
        """Retorna status geral do scheduler"""
        with self._lock:
            active_count = sum(1 for j in self._jobs.values() if j.enabled)
            overdue_count = sum(1 for j in self._jobs.values() if j.is_overdue())

            return {
                'running': self._running,
                'enabled': self._enabled,
                'total_instances': len(self._jobs),
                'active_instances': active_count,
                'overdue_instances': overdue_count,
                'active_snapshots': len(self._active_snapshots),
                'max_concurrent': self._max_concurrent,
                'default_interval_minutes': self._default_interval,
                'history_count': len(self._snapshot_history),
            }

    def trigger_snapshot(self, instance_id: str, force: bool = False) -> Optional[SnapshotResult]:
        """
        Dispara snapshot imediato para uma instancia.

        Args:
            instance_id: ID da instancia
            force: Se True, ignora limite de concorrencia

        Returns:
            SnapshotResult ou None se nao pode executar
        """
        with self._lock:
            if instance_id not in self._jobs:
                logger.warning(f"Instance {instance_id} not registered")
                return None

            job_info = self._jobs[instance_id]

            if not force and not job_info.enabled:
                logger.warning(f"Instance {instance_id} is disabled")
                return None

            # Verificar se ja ha snapshot em andamento para esta instancia
            if instance_id in self._active_snapshots:
                logger.warning(f"Snapshot already in progress for {instance_id}")
                return None

            # Verificar limite de concorrencia
            if not force and len(self._active_snapshots) >= self._max_concurrent:
                logger.warning(f"Max concurrent snapshots reached ({self._max_concurrent})")
                return None

        # Executar snapshot (fora do lock)
        return self._execute_snapshot(instance_id)

    def get_history(self, instance_id: Optional[str] = None, limit: int = 50) -> List[SnapshotResult]:
        """
        Retorna historico de snapshots.

        Args:
            instance_id: Filtrar por instancia (None = todos)
            limit: Numero maximo de resultados

        Returns:
            Lista de SnapshotResult (mais recentes primeiro)
        """
        history = self._snapshot_history

        if instance_id:
            history = [r for r in history if r.instance_id == instance_id]

        return history[-limit:][::-1]

    def _add_scheduler_job(self, job_info: SnapshotJobInfo):
        """Adiciona job ao APScheduler"""
        job_id = f"snapshot_{job_info.instance_id}"

        trigger = IntervalTrigger(minutes=job_info.interval_minutes)

        self._scheduler.add_job(
            self._job_callback,
            trigger=trigger,
            id=job_id,
            args=[job_info.instance_id],
            replace_existing=True,
        )

        # Atualizar next_snapshot_at
        job = self._scheduler.get_job(job_id)
        if job and job.next_run_time:
            job_info.next_snapshot_at = job.next_run_time.timestamp()

        logger.debug(f"Added scheduler job for {job_info.instance_id}")

    def _remove_scheduler_job(self, instance_id: str):
        """Remove job do APScheduler"""
        job_id = f"snapshot_{instance_id}"

        try:
            self._scheduler.remove_job(job_id)
            logger.debug(f"Removed scheduler job for {instance_id}")
        except JobLookupError:
            pass  # Job nao existe, ok

    def _job_callback(self, instance_id: str):
        """Callback executado pelo APScheduler"""
        logger.debug(f"Scheduler triggered snapshot for {instance_id}")
        self._execute_snapshot(instance_id)

    def _execute_snapshot(self, instance_id: str) -> Optional[SnapshotResult]:
        """
        Executa snapshot para uma instancia.

        Gerencia estado, callbacks e historico.
        """
        # Marcar como ativo
        with self._lock:
            if instance_id in self._active_snapshots:
                return None
            self._active_snapshots[instance_id] = True

            job_info = self._jobs.get(instance_id)
            if job_info:
                job_info.last_status = SnapshotStatus.IN_PROGRESS

        result = None

        try:
            logger.info(f"Starting snapshot for {instance_id}")

            # Executar snapshot
            result = self._snapshot_executor(instance_id)

            # Atualizar job info
            with self._lock:
                if job_info:
                    job_info.last_snapshot_at = result.completed_at
                    job_info.last_status = result.status
                    job_info.last_error = result.error
                    job_info.updated_at = time.time()

                    if result.status == SnapshotStatus.SUCCESS:
                        job_info.consecutive_failures = 0
                    else:
                        job_info.consecutive_failures += 1

                    # Atualizar next_snapshot_at
                    job = self._scheduler.get_job(f"snapshot_{instance_id}")
                    if job and job.next_run_time:
                        job_info.next_snapshot_at = job.next_run_time.timestamp()

                    if self._on_state_change:
                        self._on_state_change(job_info)

            # Adicionar ao historico
            self._snapshot_history.append(result)
            if len(self._snapshot_history) > self._max_history:
                self._snapshot_history = self._snapshot_history[-self._max_history:]

            # Callbacks
            if result.status == SnapshotStatus.SUCCESS:
                logger.info(f"Snapshot completed for {instance_id} in {result.duration_seconds:.1f}s")
                if self._on_success:
                    try:
                        self._on_success(result)
                    except Exception as e:
                        logger.error(f"Error in on_success callback: {e}")
            else:
                logger.error(f"Snapshot failed for {instance_id}: {result.error}")
                if self._on_failure:
                    try:
                        self._on_failure(result)
                    except Exception as e:
                        logger.error(f"Error in on_failure callback: {e}")

                # Circuit breaker: desabilitar apos muitas falhas consecutivas
                if job_info and job_info.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    logger.warning(f"Too many consecutive failures for {instance_id}, disabling")
                    self.update_instance(instance_id, enabled=False)

            return result

        except Exception as e:
            logger.exception(f"Exception during snapshot for {instance_id}")

            error_result = SnapshotResult(
                instance_id=instance_id,
                status=SnapshotStatus.FAILED,
                started_at=time.time(),
                completed_at=time.time(),
                duration_seconds=0,
                error=str(e),
            )

            # Atualizar job info
            with self._lock:
                if job_info:
                    job_info.last_status = SnapshotStatus.FAILED
                    job_info.last_error = str(e)
                    job_info.consecutive_failures += 1
                    job_info.updated_at = time.time()

            if self._on_failure:
                try:
                    self._on_failure(error_result)
                except Exception:
                    pass

            return error_result

        finally:
            # Remover dos ativos
            with self._lock:
                self._active_snapshots.pop(instance_id, None)

    def load_from_configs(self, configs: List[Dict[str, Any]]):
        """
        Carrega configuracoes de multiplas instancias.

        Usado para restaurar estado apos restart.

        Args:
            configs: Lista de dicts com instance_id, interval_minutes, enabled
        """
        for config in configs:
            instance_id = config.get('instance_id')
            if not instance_id:
                continue

            interval = config.get('interval_minutes', self._default_interval)
            enabled = config.get('enabled', True)

            try:
                self.add_instance(instance_id, interval, enabled)

                # Restaurar estado se fornecido
                job_info = self._jobs.get(instance_id)
                if job_info:
                    if 'last_snapshot_at' in config:
                        job_info.last_snapshot_at = config['last_snapshot_at']
                    if 'next_snapshot_at' in config:
                        job_info.next_snapshot_at = config['next_snapshot_at']
                    if 'consecutive_failures' in config:
                        job_info.consecutive_failures = config['consecutive_failures']

            except Exception as e:
                logger.error(f"Failed to load config for {instance_id}: {e}")

    def shutdown(self):
        """Encerra o scheduler de forma limpa"""
        self.stop(wait=True)
        logger.info("SnapshotScheduler shutdown complete")


# Singleton instance
_snapshot_scheduler: Optional[SnapshotScheduler] = None


def get_snapshot_scheduler(
    snapshot_executor: Optional[Callable[[str], SnapshotResult]] = None,
    on_success: Optional[Callable[[SnapshotResult], None]] = None,
    on_failure: Optional[Callable[[SnapshotResult], None]] = None,
    on_state_change: Optional[Callable[[SnapshotJobInfo], None]] = None,
) -> SnapshotScheduler:
    """
    Retorna instancia singleton do SnapshotScheduler.

    Args:
        snapshot_executor: Funcao que executa o snapshot real
        on_success: Callback para snapshot bem sucedido
        on_failure: Callback para falha de snapshot
        on_state_change: Callback para mudancas de estado
    """
    global _snapshot_scheduler

    if _snapshot_scheduler is None:
        _snapshot_scheduler = SnapshotScheduler(
            snapshot_executor=snapshot_executor,
            on_success=on_success,
            on_failure=on_failure,
            on_state_change=on_state_change,
        )

    return _snapshot_scheduler


if __name__ == "__main__":
    # Exemplo de uso
    import logging
    logging.basicConfig(level=logging.INFO)

    print("\nTesting SnapshotScheduler...\n")

    # Criar scheduler
    scheduler = SnapshotScheduler()
    scheduler.start()

    # Adicionar instancia
    job = scheduler.add_instance("test-gpu-001", interval_minutes=15)
    print(f"Added job: {job.to_dict()}")

    # Disparar snapshot manual
    result = scheduler.trigger_snapshot("test-gpu-001")
    if result:
        print(f"Snapshot result: {result.to_dict()}")

    # Verificar status
    print(f"\nScheduler status: {scheduler.get_status()}")

    # Cleanup
    scheduler.stop()

    print("\nTest completed!")
