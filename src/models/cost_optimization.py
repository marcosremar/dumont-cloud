"""
Models for cost optimization and 30-day GPU utilization tracking.

Includes:
- UsageMetrics: Historical GPU utilization data for pattern analysis
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from src.config.database import Base


class UsageMetrics(Base):
    """
    Historical GPU usage metrics for 30-day pattern analysis.
    Used to generate cost optimization recommendations.
    """
    __tablename__ = "usage_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    user_id = Column(String(100), nullable=False, index=True)
    instance_id = Column(String(100), nullable=False, index=True)
    gpu_type = Column(String(100), nullable=False, index=True)

    # Utilization metrics (percentages 0-100)
    gpu_utilization = Column(Float)  # GPU compute utilization %
    memory_utilization = Column(Float)  # GPU memory utilization %

    # Runtime and cost
    runtime_hours = Column(Float, default=0.0)  # Hours of runtime in this period
    cost_usd = Column(Float, default=0.0)  # Cost in USD for this period

    # Flexible extra data storage (JSONB for PostgreSQL)
    extra_data = Column(JSONB)  # {"idle_minutes": 45, "peak_utilization": 98, ...}

    # Timestamp for historical tracking
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Composite index for efficient 30-day queries by user and instance
    __table_args__ = (
        Index('idx_user_instance_timestamp', 'user_id', 'instance_id', 'timestamp'),
        Index('idx_user_gpu_timestamp', 'user_id', 'gpu_type', 'timestamp'),
    )

    def __repr__(self):
        return f"<UsageMetrics(user={self.user_id}, gpu={self.gpu_type}, util={self.gpu_utilization}%)>"
