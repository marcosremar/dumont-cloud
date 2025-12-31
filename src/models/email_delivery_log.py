"""
Modelos de banco de dados para log de entregas de email.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from datetime import datetime
from src.config.database import Base


class EmailDeliveryLog(Base):
    """Tabela para registrar entregas de emails enviados."""

    __tablename__ = "email_delivery_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=False)  # Email do destinatário

    # Informações do envio
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    email_id = Column(String(100), nullable=True, index=True)  # ID do email no Resend
    report_type = Column(String(20), default="weekly", nullable=False)  # 'weekly', 'monthly'

    # Status de entrega
    status = Column(String(20), default="pending", nullable=False, index=True)  # 'pending', 'sent', 'failed'
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)  # Mensagem de erro em caso de falha

    # Metadados do relatório
    week_start = Column(DateTime, nullable=True)  # Início do período do relatório
    week_end = Column(DateTime, nullable=True)  # Fim do período do relatório

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Índices compostos para consultas comuns
    __table_args__ = (
        Index('idx_user_sent_at', 'user_id', 'sent_at'),
        Index('idx_status_sent_at', 'status', 'sent_at'),
    )

    def __repr__(self):
        return f"<EmailDeliveryLog(user_id={self.user_id}, status={self.status}, sent_at={self.sent_at})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.email,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'email_id': self.email_id,
            'report_type': self.report_type,
            'status': self.status,
            'retry_count': self.retry_count,
            'error_message': self.error_message,
            'week_start': self.week_start.isoformat() if self.week_start else None,
            'week_end': self.week_end.isoformat() if self.week_end else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def mark_sent(self, email_id: str):
        """Marca o email como enviado com sucesso.

        Args:
            email_id: ID do email retornado pelo serviço de envio (Resend)
        """
        self.status = 'sent'
        self.email_id = email_id
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error_message: str, increment_retry: bool = True):
        """Marca o email como falha.

        Args:
            error_message: Mensagem de erro da falha
            increment_retry: Se True, incrementa o contador de retentativas
        """
        self.status = 'failed'
        self.error_message = error_message
        if increment_retry:
            self.retry_count += 1
        self.updated_at = datetime.utcnow()

    def can_retry(self, max_retries: int = 3) -> bool:
        """Verifica se o email pode ser reenviado.

        Args:
            max_retries: Número máximo de tentativas permitidas

        Returns:
            True se ainda pode tentar reenviar, False caso contrário
        """
        return self.status == 'failed' and self.retry_count < max_retries
