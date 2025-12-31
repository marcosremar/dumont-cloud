"""
Modelos para cache de metadados de regiao Vast.ai.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index, Boolean, JSON
from datetime import datetime
from src.config.database import Base


class RegionMetadata(Base):
    """
    Cache de metadados de regiao Vast.ai.
    Armazena informacoes de regiao, geolocalizacao, precos e disponibilidade.
    """
    __tablename__ = "region_metadata"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(String(100), unique=True, nullable=False, index=True)
    region_name = Column(String(200), nullable=False)

    # Dados de geolocalizacao
    continent = Column(String(50), nullable=True)  # ex: "Europe", "North America"
    country = Column(String(100), nullable=True)   # ex: "Germany", "United States"
    country_code = Column(String(10), nullable=True)  # ex: "DE", "US"
    city = Column(String(100), nullable=True)      # ex: "Frankfurt", "New York"
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Dados de compliance (GDPR, etc.)
    compliance_tags = Column(JSON, nullable=True)  # ex: ["EU_GDPR", "HIPAA"]
    is_eu_region = Column(Boolean, default=False, nullable=False)

    # Dados de precos (cache)
    min_price_per_hour = Column(Float, nullable=True)  # Preco minimo ($/hora)
    max_price_per_hour = Column(Float, nullable=True)  # Preco maximo ($/hora)
    avg_price_per_hour = Column(Float, nullable=True)  # Preco medio ($/hora)

    # Dados de disponibilidade
    total_offers = Column(Integer, default=0, nullable=False)  # Total de ofertas disponiveis
    available_gpus = Column(Integer, default=0, nullable=False)  # Total de GPUs disponiveis
    is_available = Column(Boolean, default=True, nullable=False)

    # Metadados adicionais do Vast.ai (flexivel)
    raw_geolocation = Column(String(500), nullable=True)  # String original da API Vast.ai
    extra_metadata = Column(JSON, nullable=True)  # Dados adicionais da API

    # Timestamps para gerenciamento de cache
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Quando o cache expira

    # Indices compostos para buscas otimizadas
    __table_args__ = (
        Index('idx_region_country', 'region_id', 'country_code'),
        Index('idx_region_availability', 'region_id', 'is_available'),
        Index('idx_eu_available', 'is_eu_region', 'is_available'),
    )

    def __repr__(self):
        return f"<RegionMetadata(region={self.region_id}, name={self.region_name}, eu={self.is_eu_region})>"

    def to_dict(self):
        """Converte para dicionario para API responses."""
        return {
            'region_id': self.region_id,
            'region_name': self.region_name,
            'geolocation': {
                'continent': self.continent,
                'country': self.country,
                'country_code': self.country_code,
                'city': self.city,
                'latitude': self.latitude,
                'longitude': self.longitude,
            },
            'compliance': {
                'tags': self.compliance_tags or [],
                'is_eu_region': self.is_eu_region,
            },
            'pricing': {
                'min_price_per_hour': self.min_price_per_hour,
                'max_price_per_hour': self.max_price_per_hour,
                'avg_price_per_hour': self.avg_price_per_hour,
            },
            'availability': {
                'total_offers': self.total_offers,
                'available_gpus': self.available_gpus,
                'is_available': self.is_available,
            },
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }

    def is_cache_valid(self):
        """Verifica se o cache ainda e valido."""
        if self.expires_at is None:
            return True
        return datetime.utcnow() < self.expires_at
