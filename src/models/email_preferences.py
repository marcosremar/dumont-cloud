"""
Modelos de banco de dados para preferências de email.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index
from datetime import datetime
from src.config.database import Base


class EmailPreference(Base):
    """Tabela para armazenar preferências de email dos usuários."""

    __tablename__ = "email_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)  # Email do usuário

    # Configurações de frequência
    frequency = Column(String(20), default="weekly", nullable=False)  # 'weekly', 'monthly', 'none'
    unsubscribed = Column(Boolean, default=False, nullable=False)

    # Token para unsubscribe seguro
    unsubscribe_token = Column(String(100), unique=True, nullable=True, index=True)

    # Configuração de timezone
    timezone = Column(String(50), default="UTC")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Índices compostos
    __table_args__ = (
        Index('idx_email_frequency', 'frequency', 'unsubscribed'),
    )

    def __repr__(self):
        return f"<EmailPreference(user_id={self.user_id}, frequency={self.frequency}, unsubscribed={self.unsubscribed})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.email,
            'frequency': self.frequency,
            'unsubscribed': self.unsubscribed,
            'timezone': self.timezone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def should_receive_email(self, report_type: str = 'weekly') -> bool:
        """Verifica se o usuário deve receber email do tipo especificado.

        Args:
            report_type: Tipo do relatório ('weekly' ou 'monthly')

        Returns:
            True se o usuário deve receber o email, False caso contrário
        """
        if self.unsubscribed:
            return False

        if self.frequency == 'none':
            return False

        if report_type == 'weekly':
            return self.frequency == 'weekly'

        if report_type == 'monthly':
            return self.frequency in ['weekly', 'monthly']

        return False
