"""
Modelo de banco de dados para eventos de ciclo de vida de instâncias.

Este modelo registra TODAS as mudanças de status de instâncias (destroy, pause, resume, create)
com auditoria completa: quem chamou, motivo, timestamp, e contexto adicional.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index, Text
from datetime import datetime
from enum import Enum
from src.config.database import Base


class LifecycleAction(str, Enum):
    """Tipos de ação no ciclo de vida de instâncias."""
    CREATE = "create"
    DESTROY = "destroy"
    PAUSE = "pause"
    RESUME = "resume"
    HIBERNATE = "hibernate"
    WAKE = "wake"
    ERROR = "error"


class CallerSource(str, Enum):
    """Origem da chamada (quem iniciou a ação)."""
    API_USER = "api_user"              # Usuário via API direta
    API_DASHBOARD = "api_dashboard"    # Usuário via dashboard
    AUTO_HIBERNATION = "auto_hibernation"  # Sistema de auto-hibernação
    WARMPOOL_MANAGER = "warmpool_manager"  # Warmpool manager (multi-start)
    WARMPOOL_FAILOVER = "warmpool_failover"  # Failover durante warmpool
    CPU_STANDBY = "cpu_standby"        # CPU Standby service
    SCHEDULED_TASK = "scheduled_task"  # Tarefa agendada (wake/sleep)
    DEPLOY_WIZARD = "deploy_wizard"    # Deploy wizard (cleanup)
    SYSTEM = "system"                  # Sistema genérico
    UNKNOWN = "unknown"                # Origem desconhecida


class InstanceLifecycleEvent(Base):
    """
    Tabela para log de TODOS os eventos de ciclo de vida de instâncias.

    Esta é a fonte da verdade para rastrear quem/quando/por que uma instância
    foi criada, destruída, pausada ou resumida.
    """

    __tablename__ = "instance_lifecycle_events"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação da instância
    instance_id = Column(Integer, nullable=False, index=True)  # Vast.ai instance ID
    instance_label = Column(String(200), nullable=True)  # Label da instância
    user_id = Column(String(100), nullable=False, index=True)  # Email do usuário

    # Ação realizada
    action = Column(String(50), nullable=False, index=True)  # LifecycleAction value
    previous_status = Column(String(50), nullable=True)  # Status antes da ação
    new_status = Column(String(50), nullable=True)  # Status após a ação
    success = Column(Boolean, default=True)  # Se a ação foi bem sucedida

    # Auditoria - QUEM chamou
    caller_source = Column(String(50), nullable=False, index=True)  # CallerSource value
    caller_function = Column(String(200), nullable=True)  # Nome da função que chamou
    caller_module = Column(String(200), nullable=True)  # Módulo/arquivo que chamou
    caller_file_path = Column(String(500), nullable=True)  # Caminho completo do arquivo que chamou
    caller_line_number = Column(Integer, nullable=True)  # Número da linha que chamou

    # Auditoria - POR QUE
    reason = Column(String(500), nullable=False)  # Motivo da ação (obrigatório)
    reason_details = Column(Text, nullable=True)  # Detalhes adicionais do motivo

    # Contexto da instância no momento
    gpu_type = Column(String(100), nullable=True)
    dph_total = Column(Float, nullable=True)  # Preço por hora
    gpu_utilization = Column(Float, nullable=True)  # % de uso da GPU
    ssh_host = Column(String(100), nullable=True)
    ssh_port = Column(Integer, nullable=True)

    # Informações de snapshot (se aplicável)
    snapshot_id = Column(String(200), nullable=True)

    # Metadata adicional (JSON string)
    metadata_json = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Índices compostos para consultas frequentes
    __table_args__ = (
        Index('idx_lifecycle_instance_time', 'instance_id', 'created_at'),
        Index('idx_lifecycle_user_time', 'user_id', 'created_at'),
        Index('idx_lifecycle_action_time', 'action', 'created_at'),
        Index('idx_lifecycle_caller_time', 'caller_source', 'created_at'),
    )

    def __repr__(self):
        return (
            f"<InstanceLifecycleEvent("
            f"instance={self.instance_id}, "
            f"action={self.action}, "
            f"caller={self.caller_source}, "
            f"reason={self.reason[:30]}...)>"
        )

    def to_dict(self):
        """Converte para dicionário para API responses."""
        import json

        metadata = {}
        if self.metadata_json:
            try:
                metadata = json.loads(self.metadata_json)
            except:
                pass

        return {
            'id': self.id,
            'instance_id': self.instance_id,
            'instance_label': self.instance_label,
            'user_id': self.user_id,
            'action': self.action,
            'previous_status': self.previous_status,
            'new_status': self.new_status,
            'success': self.success,
            'caller': {
                'source': self.caller_source,
                'function': self.caller_function,
                'module': self.caller_module,
                'file_path': self.caller_file_path,
                'line_number': self.caller_line_number,
            },
            'reason': self.reason,
            'reason_details': self.reason_details,
            'instance_context': {
                'gpu_type': self.gpu_type,
                'dph_total': self.dph_total,
                'gpu_utilization': self.gpu_utilization,
                'ssh_host': self.ssh_host,
                'ssh_port': self.ssh_port,
            },
            'snapshot_id': self.snapshot_id,
            'metadata': metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
