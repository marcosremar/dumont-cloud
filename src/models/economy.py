"""
Modelos de banco de dados para economia e savings tracking.

Este modulo define as tabelas para:
- SavingsHistory: Historico de economia por usuario
- ProviderPricing: Precos de GPU por provider (AWS, GCP, Azure, Dumont)
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index, ForeignKey
from datetime import datetime
from src.config.database import Base


class SavingsHistory(Base):
    """
    Tabela para armazenar snapshots periodicos de economia por usuario.

    Usado pelo Economy Widget para mostrar economia ao longo do tempo
    comparado com AWS, GCP e Azure.
    """

    __tablename__ = "savings_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)

    # Snapshot timestamp
    snapshot_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Comparison provider (AWS, GCP, Azure)
    provider = Column(String(20), nullable=False, default='AWS')

    # Aggregation period
    period_type = Column(String(20), nullable=False, default='daily')  # 'daily', 'weekly', 'monthly'

    # GPU usage details for this period
    gpu_type = Column(String(100), nullable=False)
    hours_used = Column(Float, nullable=False, default=0.0)

    # Cost data
    cost_dumont = Column(Float, nullable=False, default=0.0)
    cost_provider = Column(Float, nullable=False, default=0.0)
    savings_amount = Column(Float, nullable=False, default=0.0)
    savings_percentage = Column(Float, nullable=False, default=0.0)

    # Reference to usage record (optional)
    usage_record_id = Column(Integer, ForeignKey('usage_records.id'), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes compostos para buscas eficientes
    __table_args__ = (
        Index('idx_savings_history_user_provider', 'user_id', 'provider'),
        Index('idx_savings_history_user_period', 'user_id', 'snapshot_date', 'period_type'),
    )

    def __repr__(self):
        return f"<SavingsHistory(user={self.user_id}, provider={self.provider}, savings=${self.savings_amount:.2f})>"

    def to_dict(self):
        """Converte para dicionario para API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'snapshot_date': self.snapshot_date.isoformat() if self.snapshot_date else None,
            'provider': self.provider,
            'period_type': self.period_type,
            'gpu_type': self.gpu_type,
            'hours_used': self.hours_used,
            'cost_dumont': self.cost_dumont,
            'cost_provider': self.cost_provider,
            'savings_amount': self.savings_amount,
            'savings_percentage': self.savings_percentage,
            'usage_record_id': self.usage_record_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ProviderPricing(Base):
    """
    Tabela de precos de GPU por provider para calculos de comparacao.

    Armazena precos horarios de AWS, GCP, Azure e Dumont Cloud para
    diferentes tipos de GPU. Atualizado periodicamente com rates atuais.
    """

    __tablename__ = "provider_pricing"

    id = Column(Integer, primary_key=True, index=True)

    # Provider identification
    provider = Column(String(20), nullable=False, index=True)  # 'AWS', 'GCP', 'Azure', 'Dumont'

    # GPU details
    gpu_type = Column(String(100), nullable=False, index=True)
    gpu_name = Column(String(200), nullable=True)  # Display name (e.g., "NVIDIA A100 80GB")
    vram_gb = Column(Integer, nullable=True)

    # Pricing (per hour in USD)
    price_per_hour = Column(Float, nullable=False)

    # Instance type (for cloud providers)
    instance_type = Column(String(100), nullable=True)  # e.g., 'p4d.24xlarge' for AWS

    # Region (pricing can vary by region)
    region = Column(String(50), default='us-east-1')

    # Pricing type
    pricing_type = Column(String(30), default='on-demand')  # 'on-demand', 'spot', 'reserved'

    # Validity period
    effective_from = Column(DateTime, default=datetime.utcnow, nullable=False)
    effective_until = Column(DateTime, nullable=True)  # NULL means currently active

    # Metadata
    source = Column(String(200), nullable=True)  # Where pricing was sourced from
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)

    # Indexes compostos para buscas eficientes
    __table_args__ = (
        Index('idx_provider_pricing_provider_gpu', 'provider', 'gpu_type'),
        Index('idx_provider_pricing_active', 'is_active'),
    )

    def __repr__(self):
        return f"<ProviderPricing(provider={self.provider}, gpu={self.gpu_type}, price=${self.price_per_hour:.2f}/h)>"

    def to_dict(self):
        """Converte para dicionario para API responses."""
        return {
            'id': self.id,
            'provider': self.provider,
            'gpu_type': self.gpu_type,
            'gpu_name': self.gpu_name,
            'vram_gb': self.vram_gb,
            'price_per_hour': self.price_per_hour,
            'instance_type': self.instance_type,
            'region': self.region,
            'pricing_type': self.pricing_type,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_until': self.effective_until.isoformat() if self.effective_until else None,
            'source': self.source,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'is_active': self.is_active,
        }

    @classmethod
    def get_active_price(cls, session, provider: str, gpu_type: str, region: str = None) -> 'ProviderPricing':
        """
        Busca o preco ativo para um provider/GPU especifico.

        Args:
            session: SQLAlchemy session
            provider: Nome do provider (AWS, GCP, Azure, Dumont)
            gpu_type: Tipo de GPU (RTX 4090, A100, etc.)
            region: Regiao opcional (default usa qualquer regiao)

        Returns:
            ProviderPricing object ou None se nao encontrado
        """
        query = session.query(cls).filter(
            cls.provider == provider,
            cls.gpu_type == gpu_type,
            cls.is_active == True
        )

        if region:
            query = query.filter(cls.region == region)

        return query.first()

    @classmethod
    def get_all_providers_for_gpu(cls, session, gpu_type: str) -> list:
        """
        Busca precos de todos os providers para um tipo de GPU.

        Args:
            session: SQLAlchemy session
            gpu_type: Tipo de GPU (RTX 4090, A100, etc.)

        Returns:
            Lista de ProviderPricing objects
        """
        return session.query(cls).filter(
            cls.gpu_type == gpu_type,
            cls.is_active == True
        ).all()
