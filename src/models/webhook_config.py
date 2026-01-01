"""
Modelos de banco de dados para configuracao e logs de webhooks.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index, JSON, ForeignKey, Text
from datetime import datetime
from src.config.database import Base


class WebhookConfig(Base):
    """Tabela para armazenar configuracoes de webhooks dos usuarios."""

    __tablename__ = "webhook_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)

    # Configuracao do webhook
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(JSON, nullable=False)  # ['instance.started', 'instance.stopped', 'snapshot.completed', 'failover.triggered', 'cost.threshold']
    secret = Column(String(100), nullable=True)  # Para assinatura HMAC-SHA256
    enabled = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indices compostos
    __table_args__ = (
        Index('idx_user_webhooks', 'user_id', 'enabled'),
    )

    def __repr__(self):
        return f"<WebhookConfig(id={self.id}, name={self.name}, enabled={self.enabled})>"

    def to_dict(self, include_secret: bool = False):
        """Converte para dicionario para API responses."""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'url': self.url,
            'events': self.events,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        # Secreto e redactado por padrao em respostas GET
        if include_secret:
            result['secret'] = self.secret
        else:
            result['secret'] = '***' if self.secret else None
        return result


class WebhookLog(Base):
    """Tabela para log de entregas de webhooks."""

    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey('webhook_configs.id'), nullable=False, index=True)

    # Detalhes do evento
    event_type = Column(String(50), nullable=False, index=True)
    # Tipos: "instance.started", "instance.stopped", "snapshot.completed", "failover.triggered", "cost.threshold", "test"
    payload = Column(JSON, nullable=False)

    # Resultado da entrega
    status_code = Column(Integer, nullable=True)  # Codigo HTTP retornado
    response = Column(Text, nullable=True)  # Corpo da resposta (truncado se muito grande)
    attempt = Column(Integer, default=1, nullable=False)  # Numero da tentativa (1, 2, 3)
    error = Column(String(500), nullable=True)  # Mensagem de erro se falhou

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indices compostos para buscas comuns
    __table_args__ = (
        Index('idx_webhook_logs', 'webhook_id', 'created_at'),
        Index('idx_webhook_event_type', 'event_type', 'created_at'),
    )

    def __repr__(self):
        return f"<WebhookLog(webhook_id={self.webhook_id}, event={self.event_type}, status={self.status_code}, attempt={self.attempt})>"

    def to_dict(self):
        """Converte para dicionario para API responses."""
        return {
            'id': self.id,
            'webhook_id': self.webhook_id,
            'event_type': self.event_type,
            'payload': self.payload,
            'status_code': self.status_code,
            'response': self.response,
            'attempt': self.attempt,
            'error': self.error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
