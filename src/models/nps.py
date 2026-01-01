"""
Modelos de banco de dados para sistema NPS (Net Promoter Score) e coleta de feedback.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index
from datetime import datetime
from src.config.database import Base


class NPSResponse(Base):
    """Tabela para armazenar respostas de pesquisas NPS."""

    __tablename__ = "nps_responses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)

    # Score e feedback
    score = Column(Integer, nullable=False)  # 0-10 (Detractors: 0-6, Passives: 7-8, Promoters: 9-10)
    comment = Column(Text, nullable=True)  # Comentário opcional do usuário

    # Contexto da pesquisa
    trigger_type = Column(String(50), nullable=False, index=True)  # 'first_deployment', 'monthly', 'issue_resolution'

    # Categorização (calculada com base no score)
    category = Column(String(20), nullable=False)  # 'detractor', 'passive', 'promoter'

    # Flag para follow-up (para detratores)
    needs_followup = Column(Boolean, default=False, index=True)
    followup_completed = Column(Boolean, default=False)
    followup_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Índices compostos para buscas frequentes
    __table_args__ = (
        Index('idx_nps_user_trigger', 'user_id', 'trigger_type'),
        Index('idx_nps_category_date', 'category', 'created_at'),
        Index('idx_nps_followup', 'needs_followup', 'followup_completed'),
    )

    def __repr__(self):
        return f"<NPSResponse(user={self.user_id}, score={self.score}, category={self.category})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'score': self.score,
            'comment': self.comment,
            'trigger_type': self.trigger_type,
            'category': self.category,
            'needs_followup': self.needs_followup,
            'followup_completed': self.followup_completed,
            'followup_notes': self.followup_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def get_category(score: int) -> str:
        """Retorna a categoria NPS baseada no score."""
        if score <= 6:
            return 'detractor'
        elif score <= 8:
            return 'passive'
        else:
            return 'promoter'


class NPSSurveyConfig(Base):
    """Tabela para configuração de pesquisas NPS por tipo de trigger."""

    __tablename__ = "nps_survey_config"

    id = Column(Integer, primary_key=True, index=True)
    trigger_type = Column(String(50), nullable=False, unique=True, index=True)
    # Tipos: 'first_deployment', 'monthly', 'issue_resolution'

    # Configurações
    enabled = Column(Boolean, default=True, nullable=False)
    frequency_days = Column(Integer, default=30, nullable=False)  # Frequência mínima entre surveys

    # Personalização
    title = Column(String(200), nullable=True)  # Título customizado da pesquisa
    description = Column(String(500), nullable=True)  # Descrição/contexto

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<NPSSurveyConfig(trigger={self.trigger_type}, enabled={self.enabled}, frequency={self.frequency_days}d)>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'id': self.id,
            'trigger_type': self.trigger_type,
            'enabled': self.enabled,
            'frequency_days': self.frequency_days,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class NPSUserInteraction(Base):
    """Tabela para rastrear interações do usuário com pesquisas NPS (rate limiting)."""

    __tablename__ = "nps_user_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)

    # Tipo de interação
    interaction_type = Column(String(20), nullable=False, index=True)
    # Tipos: 'shown', 'dismissed', 'submitted'

    # Contexto
    trigger_type = Column(String(50), nullable=False, index=True)

    # Referência à resposta (se foi submitted)
    response_id = Column(Integer, nullable=True)  # FK para nps_responses.id

    # Metadata adicional
    interaction_metadata = Column(String(1000), nullable=True)  # JSON string com dados extras (ex: dismiss reason)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Índices compostos para queries de rate limiting
    __table_args__ = (
        Index('idx_nps_interaction_user_type', 'user_id', 'interaction_type'),
        Index('idx_nps_interaction_user_trigger', 'user_id', 'trigger_type', 'created_at'),
        Index('idx_nps_interaction_date', 'interaction_type', 'created_at'),
    )

    def __repr__(self):
        return f"<NPSUserInteraction(user={self.user_id}, type={self.interaction_type}, trigger={self.trigger_type})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'interaction_type': self.interaction_type,
            'trigger_type': self.trigger_type,
            'response_id': self.response_id,
            'metadata': self.interaction_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
