"""
GPU Reservation Models

Modelos para o sistema de reservas de GPU com descontos e garantia de SLA.
Permite que usuários pré-reservem capacidade de GPU para disponibilidade garantida.
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum,
    Index, ForeignKey
)
from sqlalchemy.orm import relationship

from src.config.database import Base


class ReservationStatus(enum.Enum):
    """
    Status possíveis para uma reserva de GPU.
    """
    PENDING = "pending"      # Reserva criada, aguardando início
    ACTIVE = "active"        # Reserva em uso
    COMPLETED = "completed"  # Reserva finalizada com sucesso
    CANCELLED = "cancelled"  # Reserva cancelada pelo usuário
    FAILED = "failed"        # Falha na alocação do GPU


class Reservation(Base):
    """
    Registro de reserva de GPU.

    Permite que usuários reservem capacidade de GPU antecipadamente
    com desconto de 10-20% sobre o preço spot.
    """
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação do usuário
    user_id = Column(String(100), nullable=False, index=True)

    # Configuração da reserva
    gpu_type = Column(String(100), nullable=False, index=True)  # e.g., "A100", "H100"
    gpu_count = Column(Integer, default=1, nullable=False)

    # Período da reserva (UTC)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)

    # Status da reserva
    status = Column(
        Enum(ReservationStatus),
        default=ReservationStatus.PENDING,
        nullable=False,
        index=True
    )

    # Créditos e desconto
    credits_used = Column(Float, default=0.0, nullable=False)
    credits_refunded = Column(Float, default=0.0, nullable=False)
    discount_rate = Column(Integer, default=15, nullable=False)  # 10-20% discount

    # Preços para referência
    spot_price_per_hour = Column(Float, nullable=True)  # Preço spot no momento da reserva
    reserved_price_per_hour = Column(Float, nullable=True)  # Preço com desconto

    # Instância alocada (quando ativa)
    instance_id = Column(String(100), nullable=True, index=True)
    provider = Column(String(50), nullable=True)  # vast, tensordock, etc

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)  # Quando efetivamente iniciou
    completed_at = Column(DateTime(timezone=True), nullable=True)  # Quando terminou
    cancelled_at = Column(DateTime(timezone=True), nullable=True)  # Quando foi cancelada

    # Metadados
    cancellation_reason = Column(String(500), nullable=True)
    failure_reason = Column(String(500), nullable=True)

    __table_args__ = (
        Index('idx_reservation_user_status', 'user_id', 'status'),
        Index('idx_reservation_gpu_time', 'gpu_type', 'start_time', 'end_time'),
        Index('idx_reservation_time_range', 'start_time', 'end_time'),
        Index('idx_reservation_status_time', 'status', 'start_time'),
    )

    @property
    def duration_hours(self) -> float:
        """Calcula a duração da reserva em horas."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() / 3600
        return 0.0

    @property
    def is_active(self) -> bool:
        """Verifica se a reserva está ativa."""
        return self.status == ReservationStatus.ACTIVE

    @property
    def is_upcoming(self) -> bool:
        """Verifica se a reserva ainda vai começar."""
        if self.status != ReservationStatus.PENDING:
            return False
        return datetime.utcnow() < self.start_time.replace(tzinfo=None) if self.start_time else False

    @property
    def is_cancellable(self) -> bool:
        """Verifica se a reserva pode ser cancelada."""
        return self.status in (ReservationStatus.PENDING, ReservationStatus.ACTIVE)

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "gpu_type": self.gpu_type,
            "gpu_count": self.gpu_count,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value if self.status else None,
            "credits_used": self.credits_used,
            "credits_refunded": self.credits_refunded,
            "discount_rate": self.discount_rate,
            "spot_price_per_hour": self.spot_price_per_hour,
            "reserved_price_per_hour": self.reserved_price_per_hour,
            "instance_id": self.instance_id,
            "provider": self.provider,
            "duration_hours": self.duration_hours,
            "is_active": self.is_active,
            "is_upcoming": self.is_upcoming,
            "is_cancellable": self.is_cancellable,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancellation_reason": self.cancellation_reason,
            "failure_reason": self.failure_reason,
        }

    def __repr__(self):
        status_str = self.status.value if self.status else "unknown"
        return f"<Reservation(id={self.id}, user={self.user_id}, gpu={self.gpu_type}, status={status_str})>"
