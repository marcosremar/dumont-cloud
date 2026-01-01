"""
Modelos para preferencias de regiao do usuario.
"""

from sqlalchemy import Column, Integer, String, DateTime, Index, JSON
from datetime import datetime
from src.config.database import Base


class UserRegionPreference(Base):
    """
    Preferencias de regiao do usuario para provisionamento de GPU.
    Armazena regiao preferida, regioes de fallback e requisitos de residencia de dados.
    """
    __tablename__ = "user_region_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), unique=True, nullable=False, index=True)

    # Regiao preferida
    preferred_region = Column(String(100), nullable=False)

    # Lista de regioes de fallback (ordenada por prioridade)
    # Armazenado como JSON array: ["eu-central", "us-east", "us-west"]
    fallback_regions = Column(JSON, nullable=True)

    # Requisito de residencia de dados (ex: "EU_GDPR", "US_ONLY", null para sem restricao)
    data_residency_requirement = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indices compostos para buscas otimizadas
    __table_args__ = (
        Index('idx_user_region_residency', 'user_id', 'data_residency_requirement'),
    )

    def __repr__(self):
        return f"<UserRegionPreference(user={self.user_id}, region={self.preferred_region})>"

    def to_dict(self):
        """Converte para dicionario para API responses."""
        return {
            'user_id': self.user_id,
            'preferred_region': self.preferred_region,
            'fallback_regions': self.fallback_regions or [],
            'data_residency_requirement': self.data_residency_requirement,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
