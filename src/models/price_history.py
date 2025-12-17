"""
Modelos de banco de dados para histórico de preços.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from datetime import datetime
from src.config.database import Base


class PriceHistory(Base):
    """Tabela para armazenar histórico de preços de GPUs."""

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    gpu_name = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Estatísticas de preço
    min_price = Column(Float, nullable=False)  # Preço mínimo encontrado ($/hora)
    max_price = Column(Float, nullable=False)  # Preço máximo encontrado ($/hora)
    avg_price = Column(Float, nullable=False)  # Preço médio ($/hora)
    median_price = Column(Float, nullable=False)  # Preço mediano ($/hora)

    # Estatísticas de disponibilidade
    total_offers = Column(Integer, nullable=False)  # Total de ofertas disponíveis
    available_gpus = Column(Integer, nullable=False)  # Total de GPUs disponíveis

    # Estatísticas regionais (opcional)
    region_stats = Column(String(5000))  # JSON string com stats por região

    # Índice composto para buscas por GPU e data
    __table_args__ = (
        Index('idx_gpu_timestamp', 'gpu_name', 'timestamp'),
    )

    def __repr__(self):
        return f"<PriceHistory(gpu={self.gpu_name}, timestamp={self.timestamp}, avg_price={self.avg_price})>"


class PriceAlert(Base):
    """Tabela para alertas de mudança de preço."""

    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, index=True)
    gpu_name = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    alert_type = Column(String(50), nullable=False)  # 'price_drop', 'price_spike', 'high_availability'
    previous_value = Column(Float)
    current_value = Column(Float)
    change_percent = Column(Float)
    message = Column(String(500))

    def __repr__(self):
        return f"<PriceAlert(gpu={self.gpu_name}, type={self.alert_type}, change={self.change_percent}%)>"
