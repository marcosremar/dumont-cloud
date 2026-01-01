"""
Modelos de banco de dados para relatórios compartilháveis.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from src.config.database import Base


class ShareableReport(Base):
    """
    Tabela para armazenar relatórios de economia compartilháveis.

    Permite que usuários gerem relatórios públicos mostrando suas economias
    comparadas com outros provedores de cloud (AWS, GCP, Azure).
    """

    __tablename__ = "shareable_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)

    # ID único para URL compartilhável (nanoid 10-12 chars)
    shareable_id = Column(String(20), unique=True, nullable=False, index=True)

    # Configuração do relatório (métricas selecionadas, formato, etc.)
    # Ex: {"monthly_savings": true, "annual_savings": true, "percentage_saved": true, "provider_comparison": false}
    config = Column(JSON, nullable=False)

    # URL da imagem gerada para compartilhamento social
    image_url = Column(String(500), nullable=True)

    # Formato do relatório (twitter, linkedin, generic)
    format = Column(String(20), nullable=False, default="generic")

    # Dados agregados de economia (snapshot no momento da criação)
    # Ex: {"total_savings": 3500.00, "savings_percentage": 65, "period_months": 6}
    savings_data = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)  # Opcional: expiração do relatório

    # Índices compostos para buscas otimizadas
    __table_args__ = (
        Index('idx_user_shareable_reports', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f"<ShareableReport(id={self.id}, shareable_id={self.shareable_id}, user_id={self.user_id})>"
