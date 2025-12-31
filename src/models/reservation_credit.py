"""
Reservation Credit Models

Modelo para tracking de créditos de reserva com rollover de 30 dias.
Créditos não utilizados expiram após 30 dias, mas créditos vinculados
a uma reserva ativa não expiram até que a reserva seja concluída.
"""
import enum
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum,
    Index, ForeignKey, Boolean
)

from src.config.database import Base


# Default expiration period in days
CREDIT_EXPIRY_DAYS = 30


class CreditStatus(enum.Enum):
    """
    Status possíveis para um crédito de reserva.
    """
    AVAILABLE = "available"    # Crédito disponível para uso
    LOCKED = "locked"          # Crédito vinculado a uma reserva ativa
    USED = "used"              # Crédito utilizado em uma reserva concluída
    EXPIRED = "expired"        # Crédito expirou (após 30 dias)
    REFUNDED = "refunded"      # Crédito reembolsado de uma reserva cancelada


class CreditTransactionType(enum.Enum):
    """
    Tipos de transações de crédito.
    """
    PURCHASE = "purchase"        # Compra de créditos
    DEDUCTION = "deduction"      # Dedução para reserva
    REFUND = "refund"            # Reembolso de reserva cancelada
    EXPIRATION = "expiration"    # Expiração por tempo
    ADJUSTMENT = "adjustment"    # Ajuste manual


class ReservationCredit(Base):
    """
    Registro de créditos de reserva de GPU.

    Cada registro representa uma quantidade de créditos com data de expiração.
    Os créditos expiram 30 dias após a criação, exceto quando vinculados
    a uma reserva ativa.
    """
    __tablename__ = "reservation_credits"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação do usuário
    user_id = Column(String(100), nullable=False, index=True)

    # Quantidade de créditos
    amount = Column(Float, nullable=False)
    original_amount = Column(Float, nullable=False)  # Valor original antes de deduções

    # Datas de validade
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)  # Quando expirou de fato

    # Status do crédito
    status = Column(
        Enum(CreditStatus),
        default=CreditStatus.AVAILABLE,
        nullable=False,
        index=True
    )

    # Vinculação à reserva (opcional)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=True, index=True)

    # Tipo de transação que originou este crédito
    transaction_type = Column(
        Enum(CreditTransactionType),
        default=CreditTransactionType.PURCHASE,
        nullable=False
    )

    # Referência para crédito pai (em caso de refund/split)
    parent_credit_id = Column(Integer, ForeignKey("reservation_credits.id"), nullable=True)

    # Metadados
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_credit_user_status', 'user_id', 'status'),
        Index('idx_credit_user_expiration', 'user_id', 'expires_at'),
        Index('idx_credit_status_expiration', 'status', 'expires_at'),
        Index('idx_credit_reservation', 'reservation_id'),
    )

    @property
    def is_available(self) -> bool:
        """Verifica se o crédito está disponível para uso."""
        return self.status == CreditStatus.AVAILABLE and self.amount > 0

    @property
    def is_expired(self) -> bool:
        """Verifica se o crédito está expirado."""
        if self.status == CreditStatus.EXPIRED:
            return True
        if self.status == CreditStatus.LOCKED:
            # Créditos vinculados a reservas não expiram
            return False
        if self.expires_at:
            return datetime.utcnow() > self.expires_at.replace(tzinfo=None)
        return False

    @property
    def days_until_expiration(self) -> int:
        """Retorna dias até a expiração."""
        if self.status in (CreditStatus.EXPIRED, CreditStatus.USED):
            return 0
        if self.status == CreditStatus.LOCKED:
            return -1  # Não expira enquanto vinculado
        if self.expires_at:
            delta = self.expires_at.replace(tzinfo=None) - datetime.utcnow()
            return max(0, delta.days)
        return 0

    @classmethod
    def create_purchase(
        cls,
        user_id: str,
        amount: float,
        description: str = None,
        expiry_days: int = CREDIT_EXPIRY_DAYS
    ) -> "ReservationCredit":
        """
        Cria um novo registro de compra de créditos.

        Args:
            user_id: ID do usuário
            amount: Quantidade de créditos
            description: Descrição opcional
            expiry_days: Dias até expiração (padrão: 30)

        Returns:
            Nova instância de ReservationCredit
        """
        now = datetime.utcnow()
        return cls(
            user_id=user_id,
            amount=amount,
            original_amount=amount,
            created_at=now,
            expires_at=now + timedelta(days=expiry_days),
            status=CreditStatus.AVAILABLE,
            transaction_type=CreditTransactionType.PURCHASE,
            description=description or f"Credit purchase of {amount} credits"
        )

    @classmethod
    def create_refund(
        cls,
        user_id: str,
        amount: float,
        reservation_id: int,
        parent_credit_id: int = None,
        expiry_days: int = CREDIT_EXPIRY_DAYS
    ) -> "ReservationCredit":
        """
        Cria um novo registro de reembolso de créditos.

        Args:
            user_id: ID do usuário
            amount: Quantidade de créditos reembolsados
            reservation_id: ID da reserva cancelada
            parent_credit_id: ID do crédito original (opcional)
            expiry_days: Dias até expiração (padrão: 30)

        Returns:
            Nova instância de ReservationCredit
        """
        now = datetime.utcnow()
        return cls(
            user_id=user_id,
            amount=amount,
            original_amount=amount,
            created_at=now,
            expires_at=now + timedelta(days=expiry_days),
            status=CreditStatus.AVAILABLE,
            transaction_type=CreditTransactionType.REFUND,
            reservation_id=reservation_id,
            parent_credit_id=parent_credit_id,
            description=f"Refund from reservation {reservation_id}"
        )

    def lock_for_reservation(self, reservation_id: int) -> None:
        """
        Vincula o crédito a uma reserva.
        Créditos vinculados não expiram até que a reserva seja concluída.

        Args:
            reservation_id: ID da reserva
        """
        if self.status != CreditStatus.AVAILABLE:
            raise ValueError(f"Cannot lock credit with status {self.status.value}")
        self.status = CreditStatus.LOCKED
        self.reservation_id = reservation_id
        self.updated_at = datetime.utcnow()

    def mark_as_used(self) -> None:
        """Marca o crédito como utilizado."""
        self.status = CreditStatus.USED
        self.updated_at = datetime.utcnow()

    def mark_as_expired(self) -> None:
        """Marca o crédito como expirado."""
        if self.status == CreditStatus.LOCKED:
            raise ValueError("Cannot expire locked credit")
        self.status = CreditStatus.EXPIRED
        self.expired_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def release_from_reservation(self) -> None:
        """
        Libera o crédito de uma reserva.
        Usado quando uma reserva é cancelada.
        """
        if self.status != CreditStatus.LOCKED:
            raise ValueError(f"Cannot release credit with status {self.status.value}")
        self.status = CreditStatus.AVAILABLE
        self.reservation_id = None
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "original_amount": self.original_amount,
            "status": self.status.value if self.status else None,
            "transaction_type": self.transaction_type.value if self.transaction_type else None,
            "reservation_id": self.reservation_id,
            "parent_credit_id": self.parent_credit_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "expired_at": self.expired_at.isoformat() if self.expired_at else None,
            "is_available": self.is_available,
            "is_expired": self.is_expired,
            "days_until_expiration": self.days_until_expiration,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        status_str = self.status.value if self.status else "unknown"
        return f"<ReservationCredit(id={self.id}, user={self.user_id}, amount={self.amount}, status={status_str})>"
