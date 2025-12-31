"""Schemas para Reports de Economia Compartilháveis."""

from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum


class ReportFormat(str, Enum):
    """Formatos disponíveis para relatórios."""
    twitter = "twitter"
    linkedin = "linkedin"
    generic = "generic"


class MetricsConfig(BaseModel):
    """Configuração de métricas a incluir no relatório."""
    monthly_savings: bool = True
    annual_savings: bool = True
    percentage_saved: bool = True
    provider_comparison: bool = True


class GenerateReportRequest(BaseModel):
    """Request para gerar um relatório compartilhável."""
    format: ReportFormat = Field(
        default=ReportFormat.generic,
        description="Formato do relatório (twitter, linkedin, generic)"
    )
    metrics: MetricsConfig = Field(
        default_factory=MetricsConfig,
        description="Configuração de métricas a exibir"
    )


class GenerateReportResponse(BaseModel):
    """Response após gerar um relatório compartilhável."""
    shareable_id: str = Field(description="ID único para URL compartilhável")
    image_url: Optional[str] = Field(
        default=None,
        description="URL da imagem gerada (preenchida após processamento)"
    )
    format: str = Field(description="Formato do relatório")
    config: Dict[str, bool] = Field(description="Configuração de métricas")
    created_at: datetime = Field(description="Data de criação")


class ReportDataResponse(BaseModel):
    """Response com dados públicos do relatório (para visualização)."""
    shareable_id: str
    format: str
    savings_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    # Nota: Não inclui user_id, email ou outros dados sensíveis
